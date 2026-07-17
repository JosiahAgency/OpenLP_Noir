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

This is a thin command line wrapper around the converter that also powers the EGW
Library plugin's built-in PDF import
(:mod:`openlp.plugins.egwlibrary.lib.pdfimport`) — see that module for how the
chapters, paragraphs and citation pages are reconstructed.

Usage::

    python scripts/egw_pdf_to_json.py en_DA.pdf
    python scripts/egw_pdf_to_json.py en_DA.pdf -o da.json --abbreviation DA \\
        --alias "Desire of Ages" --alias desire

Requires PyMuPDF (``pip install PyMuPDF``).
"""
import argparse
import json
import sys
from pathlib import Path

# Allow running as "python scripts/egw_pdf_to_json.py" from a source checkout
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openlp.plugins.egwlibrary.lib.pdfimport import EGWPdfError, convert, guess_defaults  # noqa: E402

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit('This script requires PyMuPDF. Install it with: pip install PyMuPDF')


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
    try:
        chapters, warnings = convert(args.pdf)
    except EGWPdfError as error:
        sys.exit(str(error))
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


# SAMPLE COMMAND TO RUN: python scripts/egw_pdf_to_json.py
# "C:\Users\gjmwa\Downloads\en_GC.pdf" --abbreviation GC --alias "The Great Controversy" --alias steps
if __name__ == '__main__':
    main()
