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
The :mod:`~openlp.plugins.egwlibrary.lib.pdfimport` module converts an EGW Estate PDF
export (like ``en_DA.pdf`` from egwwritings.org) into the book dict consumed by
:func:`~openlp.plugins.egwlibrary.lib.importer.import_book`.

These PDFs are typeset with LaTeX and carry the *printed* book page numbers as margin
markers like ``[83]``, which mark the line where that printed page starts. Chapters
are headed "Chapter 1—God With Us" in a larger font, and new paragraphs are indented
while continuation lines are flush with the left margin. Those three signals are used
to rebuild chapters and paragraphs with the standard EGW citation pages, so that
"DA 83.2" in OpenLP matches egwwritings.org.

This module deliberately has no OpenLP/Qt imports so that the command line tool
``scripts/egw_pdf_to_json.py`` can reuse it. Errors are raised as :class:`EGWPdfError`
with user-presentable (untranslated) messages. PyMuPDF is imported lazily: the plugin
loads fine without it, and PDF import raises a friendly error instead.
"""
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

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


class EGWPdfError(Exception):
    """
    Raised when a PDF cannot be converted. The exception message is user visible.
    """
    pass


def _get_fitz():
    """
    Import PyMuPDF on demand, so that the plugin works without it installed.
    """
    try:
        import fitz
        return fitz
    except ImportError:
        raise EGWPdfError('PDF import requires the PyMuPDF package. Install it with: pip install PyMuPDF')


def iter_lines(doc):
    """
    Yield one entry per text line of the document, in reading order, skipping the
    running headers: ``(kind, payload)`` where kind is 'marker' (payload: page
    number), 'heading' or 'body' (payload: (text, is_paragraph_start)).

    A page marker sits in the margin on the same line as the body text where the
    printed page starts, so at equal height the marker is ordered first — the page
    number must change before that line's text is processed.
    """
    fitz = _get_fitz()
    # Only the text lines are used, so don't ask mupdf to decode and embed the
    # page images into the dict (slow on scanned pages, and image extraction has
    # been a crash magnet in older PyMuPDF builds).
    flags = getattr(fitz, 'TEXTFLAGS_DICT', None)
    preserve_images = getattr(fitz, 'TEXT_PRESERVE_IMAGES', 0)
    text_kwargs = {}
    if flags is not None:
        text_kwargs['flags'] = flags & ~preserve_images
    for page in doc:
        entries = []
        for block in page.get_text('dict', **text_kwargs)['blocks']:
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
    fitz = _get_fitz()
    doc = fitz.open(str(pdf_path))
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


def convert_pdf_book(pdf_path):
    """
    Convert an EGW Estate PDF into a book dict ready for
    :func:`~openlp.plugins.egwlibrary.lib.importer.import_book`, with the title,
    abbreviation and language guessed from the PDF metadata and file name.

    :param pdf_path: A Path to the PDF.
    :return: (book_data, warnings). The caller should let the user confirm or correct
        the guessed metadata before importing.
    :raises EGWPdfError: When the file cannot be read or contains no chapters.
    """
    fitz = _get_fitz()
    pdf_path = Path(pdf_path)
    try:
        doc = fitz.open(str(pdf_path))
        metadata_title = doc.metadata.get('title', '')
        doc.close()
    except Exception as error:
        raise EGWPdfError('Unable to read "{name}": {error}'.format(name=pdf_path.name, error=error))
    chapters, warnings = convert(pdf_path)
    if not chapters:
        raise EGWPdfError('No chapters found in "{name}". Is this an EGW Estate PDF export?'.format(
            name=pdf_path.name))
    for warning in warnings:
        log.warning('convert_pdf_book %s: %s', pdf_path.name, warning)
    title, abbreviation, language = guess_defaults(pdf_path, metadata_title)
    return {
        'title': title,
        'abbreviation': abbreviation,
        'copyright': '',
        'language': language,
        'aliases': [],
        'chapters': chapters
    }, warnings
