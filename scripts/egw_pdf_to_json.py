# -*- coding: utf-8 -*-

##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2008 OpenLP Developers                                   #
# ---------------------------------------------------------------------- #
# This program is free software: you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by   #
# the Free Software Foundation, either version 3 of the License, or      #
# (at your option) any later version.                                    #
#                                                                        #
# This program is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of         #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
# GNU General Public License for more details.                           #
#                                                                        #
# You should have received a copy of the GNU General Public License      #
# along with this program.  If not, see <https://www.gnu.org/licenses/>. #
##########################################################################
"""
Convert an EGW Estate PDF export (like ``en_DA.pdf`` from egwwritings.org) into the
JSON import format of the OpenLP EGW Library plugin.

These PDFs are typeset with LaTeX and carry the *printed* book page numbers as margin
markers like ``[83]``, which mark the line where that printed page starts. Chapters
are headed "Chapter 1—God With Us" in a larger font, and new paragraphs are indented
while continuation lines are flush with the left margin. This script uses those three
signals to rebuild chapters and paragraphs with the standard EGW citation pages, so
that "DA 83.2" in OpenLP matches egwwritings.org.

Usage::

    python scripts/egw_pdf_to_json.py en_DA.pdf
    python scripts/egw_pdf_to_json.py en_DA.pdf -o da.json --abbreviation DA \\
        --alias "Desire of Ages" --alias desire

Requires PyMuPDF (``pip install PyMuPDF``).
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit('This script requires PyMuPDF. Install it with: pip install PyMuPDF')


# A margin page marker like "[83]": the printed page 83 starts at this line.
MARKER_PATTERN = re.compile(r'^\[(\d+)\]$')
# A chapter heading like "Chapter 1—God With Us" (the dash varies).
CHAPTER_PATTERN = re.compile(r'^Chapter\s+(\d+)\s*[—–-]\s*(.*)$')
# Font size above which a line counts as a heading. Body text is ~14.2-14.5pt,
# chapter headings ~17.2pt in the EGW Estate PDFs.
HEADING_SIZE = 16.0
# Horizontal band (in points) in which the first line of an indented paragraph starts.
PARAGRAPH_INDENT = (85.0, 105.0)
# Lines above this y position are running headers (title / printed page number).
HEADER_Y = 70.0


def iter_lines(doc):
    """
    Yield one entry per text line of the document, in reading order, skipping the
    running headers: ``(kind, payload)`` where kind is 'marker' (payload: page
    number), 'heading' or 'body' (payload: (text, is_paragraph_start)).

    A page marker sits in the margin on the same line as the body text where the
    printed page starts, so at equal height the marker is ordered first — the page
    number must change before that line's text is processed.
    """
    for page in doc:
        entries = []
        for block in page.get_text('dict')['blocks']:
            if block['type'] != 0:
                continue
            for line in block['lines']:
                text = ' '.join(span['text'] for span in line['spans']).strip()
                text = re.sub(r'\s+', ' ', text)
                if not text:
                    continue
                x = line['spans'][0]['origin'][0]
                y = line['spans'][0]['origin'][1]
                size = max(span['size'] for span in line['spans'])
                if y < HEADER_Y:
                    continue
                marker = MARKER_PATTERN.match(text)
                if marker:
                    entries.append((round(y, 1), 0, x, 'marker', int(marker.group(1))))
                elif size > HEADING_SIZE:
                    entries.append((round(y, 1), 1, x, 'heading', text))
                else:
                    is_start = PARAGRAPH_INDENT[0] <= x <= PARAGRAPH_INDENT[1]
                    entries.append((round(y, 1), 1, x, 'body', (text, is_start)))
        for _, _, _, kind, payload in sorted(entries):
            yield kind, payload


def join_lines(lines):
    """
    Join the lines of a paragraph into one string, undoing end-of-line hyphenation.
    A trailing "-" is dropped when the next line continues in lowercase (a word that
    was broken by the typesetter); it is kept when the next fragment is capitalised
    (almost always a real compound like "self-denial" broken at its hyphen).
    """
    text = ''
    for line in lines:
        if not text:
            text = line
        elif text.endswith('-') and not text.endswith('—') and line[:1].islower():
            text = text[:-1] + line
        elif text.endswith('-') and not text.endswith('—'):
            text = text + line
        else:
            text = text + ' ' + line
    return text.strip()


def convert(pdf_path, expect_gap_at_headings=True):
    """
    Extract the chapters from the PDF.

    :param pdf_path: Path of the EGW Estate PDF.
    :param expect_gap_at_headings: Repair swallowed page breaks at chapter headings
        (see below).
    :return: (chapters, warnings) where chapters is a list of
        {'number', 'title', 'paragraphs': [{'page', 'text'}]} dicts.
    """
    doc = fitz.open(pdf_path)
    events = list(iter_lines(doc))
    # Pre-scan the marker sequence. When a marker at a chapter heading is followed by
    # a marker that skips a number (e.g. [18] at the heading, then [20]), the break for
    # the skipped page fell exactly on the start of the chapter body and was swallowed
    # by the typesetting. The body paragraphs before the next marker belong to the
    # skipped page: in en_DA.pdf the chapter 1 heading carries [18] but its first
    # paragraph is the famous DA 19.1.
    marker_values = [payload for kind, payload in events if kind == 'marker']
    warnings = []
    for previous, current in zip(marker_values, marker_values[1:]):
        if current != previous + 1:
            warnings.append('page markers jump from {a} to {b}'.format(a=previous, b=current))

    chapters = []
    chapter = None
    paragraph_lines = []
    paragraph_page = 0
    current_page = 0
    marker_index = -1
    pending_heading = None
    bump_after_heading = False

    def flush_paragraph():
        nonlocal paragraph_lines
        if chapter is not None and paragraph_lines:
            text = join_lines(paragraph_lines)
            if text:
                chapter['paragraphs'].append({'page': paragraph_page, 'text': text})
        paragraph_lines = []

    def flush_heading():
        nonlocal pending_heading, chapter, current_page, bump_after_heading
        if pending_heading is None:
            return
        match = CHAPTER_PATTERN.match(pending_heading)
        if match:
            chapter = {'number': int(match.group(1)), 'title': match.group(2).strip(), 'paragraphs': []}
            chapters.append(chapter)
            if bump_after_heading:
                # The swallowed page break: the chapter body starts on the page that
                # is missing from the marker sequence.
                current_page += 1
                bump_after_heading = False
        elif chapters:
            # A heading after the chapters started that is not a chapter: appendix,
            # index, etc. Stop collecting rather than misfile its text.
            warnings.append('stopped at unrecognised heading: {h!r}'.format(h=pending_heading))
            chapter = None
        pending_heading = None

    for kind, payload in events:
        if kind == 'marker':
            marker_index += 1
            current_page = payload
            bump_after_heading = False
            if expect_gap_at_headings and marker_index + 1 < len(marker_values) \
                    and marker_values[marker_index + 1] == payload + 2:
                # The next marker skips a page: if a chapter heading follows before
                # that marker, the skipped page starts at the chapter body.
                bump_after_heading = True
        elif kind == 'heading':
            flush_paragraph()
            if pending_heading is not None:
                # Continuation line of a long two-line chapter title
                pending_heading = pending_heading + ' ' + payload
            else:
                pending_heading = payload
        else:
            text, is_start = payload
            if pending_heading is not None:
                flush_heading()
            if chapter is None:
                continue
            if is_start:
                flush_paragraph()
                paragraph_page = current_page
            elif not paragraph_lines:
                # Body text before the first indented paragraph of a chapter (rare:
                # an opening block quote). Treat it as a paragraph of its own.
                paragraph_page = current_page
            paragraph_lines.append(text)
    flush_paragraph()
    doc.close()
    return chapters, warnings


def guess_defaults(pdf_path, doc_title):
    """
    Guess the book title, abbreviation and language from the PDF metadata and the
    egwwritings file naming convention (e.g. "en_DA.pdf").
    """
    title = re.sub(r'\s*\(\d{4}\)\s*$', '', doc_title or '').strip()
    abbreviation = ''
    language = 'en'
    match = re.match(r'^(?:([a-z]{2,3})_)?([A-Za-z0-9]{1,10})$', Path(pdf_path).stem)
    if match:
        if match.group(1):
            language = match.group(1)
        abbreviation = match.group(2)
    return title, abbreviation, language


def main():
    parser = argparse.ArgumentParser(
        description='Convert an EGW Estate PDF into the OpenLP EGW Library JSON import format.')
    parser.add_argument('pdf', type=Path, help='the PDF to convert, e.g. en_DA.pdf')
    parser.add_argument('-o', '--output', type=Path, default=None,
                        help='output JSON file (default: next to the PDF)')
    parser.add_argument('--title', default=None, help='book title (default: from the PDF metadata)')
    parser.add_argument('--abbreviation', default=None,
                        help='citation abbreviation, e.g. DA (default: from the file name)')
    parser.add_argument('--language', default=None, help='language code (default: from the file name, else en)')
    parser.add_argument('--copyright', dest='copyright_text', default='',
                        help='copyright/attribution line shown in the footer')
    parser.add_argument('--alias', action='append', default=[],
                        help='extra search alias for the book; may be given multiple times')
    args = parser.parse_args()

    if not args.pdf.is_file():
        sys.exit('File not found: {path}'.format(path=args.pdf))
    doc = fitz.open(args.pdf)
    metadata_title = doc.metadata.get('title', '')
    doc.close()
    guessed_title, guessed_abbreviation, guessed_language = guess_defaults(args.pdf, metadata_title)
    title = args.title or guessed_title
    abbreviation = args.abbreviation or guessed_abbreviation
    language = args.language or guessed_language
    if not title or not abbreviation:
        sys.exit('Could not guess the {what}; please pass {flag}'.format(
            what='title' if not title else 'abbreviation',
            flag='--title' if not title else '--abbreviation'))

    print('Converting {pdf} — "{title}" ({abbr}, {lang})'.format(
        pdf=args.pdf.name, title=title, abbr=abbreviation, lang=language))
    chapters, warnings = convert(args.pdf)
    if not chapters:
        sys.exit('No chapters found. Is this an EGW Estate PDF export?')
    for warning in warnings:
        print('  warning:', warning)

    book = {
        'title': title,
        'abbreviation': abbreviation,
        'copyright': args.copyright_text,
        'language': language,
        'aliases': args.alias,
        'chapters': chapters
    }
    output_path = args.output or args.pdf.with_suffix('.json')
    output_path.write_text(json.dumps({'book': book}, ensure_ascii=False, indent=1), encoding='utf-8')

    paragraph_count = sum(len(chapter['paragraphs']) for chapter in chapters)
    pages = [paragraph['page'] for chapter in chapters for paragraph in chapter['paragraphs']]
    print('Wrote {out}: {chapters} chapters, {paragraphs} paragraphs, pages {first}-{last}'.format(
        out=output_path, chapters=len(chapters), paragraphs=paragraph_count,
        first=min(pages), last=max(pages)))
    first = chapters[0]['paragraphs'][0]
    print('First paragraph ({abbr} {page}.1): {text}...'.format(
        abbr=abbreviation, page=first['page'], text=first['text'][:70]))


if __name__ == '__main__':
    main()
