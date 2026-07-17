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
Tests for the EGW Library PDF importer, using synthetic PDFs generated with PyMuPDF.
"""
import pytest

from openlp.plugins.egwlibrary.lib.db import EGWLibraryManager, init_schema
from openlp.plugins.egwlibrary.lib.importer import import_book
from openlp.plugins.egwlibrary.lib.pdfimport import EGWPdfError, convert_pdf_book, guess_defaults, join_lines

fitz = pytest.importorskip('fitz')

# Positions matching the signals the parser looks for (see pdfimport module constants):
# markers in the left margin, paragraph starts indented into (85, 105), continuation
# lines flush left, headings > 16pt, running headers above y=70.
MARGIN_X = 40
INDENT_X = 95
FLUSH_X = 72
BODY_SIZE = 11
HEADING_SIZE = 18


@pytest.fixture
def manager():
    """An EGWLibraryManager bound to an in-memory database, bypassing the settings."""
    instance = EGWLibraryManager.__new__(EGWLibraryManager)
    instance.is_dirty = False
    instance.db_url = 'sqlite://'
    instance.session = init_schema('sqlite://')
    instance._has_fts = None
    yield instance
    instance.session.close()


def _make_estate_pdf(path):
    """
    Build a two-chapter PDF in the EGW Estate layout. The chapter 1 heading carries the
    marker [18] and the next marker is [20]: the page break for 19 was swallowed by the
    heading, so chapter 1's body must be attributed to page 19 (the en_DA.pdf quirk).
    """
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((MARGIN_X, 50), 'The Desire of Ages', fontsize=BODY_SIZE)  # running header
    page.insert_text((MARGIN_X, 100), '[18]', fontsize=BODY_SIZE)
    page.insert_text((INDENT_X, 100), 'Chapter 1-God With Us', fontsize=HEADING_SIZE)
    page.insert_text((INDENT_X, 130), 'The opening para-', fontsize=BODY_SIZE)
    page.insert_text((FLUSH_X, 150), 'graph of the book.', fontsize=BODY_SIZE)
    page.insert_text((MARGIN_X, 180), '[20]', fontsize=BODY_SIZE)
    page.insert_text((INDENT_X, 180), 'Second paragraph on page twenty.', fontsize=BODY_SIZE)
    page = doc.new_page()
    page.insert_text((INDENT_X, 100), 'Chapter 2-The Chosen People', fontsize=HEADING_SIZE)
    page.insert_text((MARGIN_X, 130), '[21]', fontsize=BODY_SIZE)
    page.insert_text((INDENT_X, 130), 'The only paragraph of chapter two.', fontsize=BODY_SIZE)
    doc.set_metadata({'title': 'The Desire of Ages (1898)'})
    doc.save(str(path))
    doc.close()


def test_convert_pdf_book(tmp_path):
    """
    Test that an Estate-layout PDF converts into the right chapters, paragraphs and
    citation pages, with metadata guessed from the file name and PDF title.
    """
    # GIVEN: A synthetic Estate PDF named using the egwwritings convention
    pdf_path = tmp_path / 'en_DA.pdf'
    _make_estate_pdf(pdf_path)

    # WHEN: The PDF is converted
    book_data, warnings = convert_pdf_book(pdf_path)

    # THEN: Metadata comes from the file name and PDF title (the year is stripped)
    assert book_data['title'] == 'The Desire of Ages'
    assert book_data['abbreviation'] == 'DA'
    assert book_data['language'] == 'en'
    # THEN: The chapters, paragraph pages and hyphenation repair are correct
    assert [(chapter['number'], chapter['title']) for chapter in book_data['chapters']] == \
        [(1, 'God With Us'), (2, 'The Chosen People')]
    chapter_one = book_data['chapters'][0]
    assert chapter_one['paragraphs'] == [
        # The swallowed page break: body of chapter 1 is page 19, not 18
        {'page': 19, 'text': 'The opening paragraph of the book.'},
        {'page': 20, 'text': 'Second paragraph on page twenty.'},
    ]
    assert book_data['chapters'][1]['paragraphs'] == [
        {'page': 21, 'text': 'The only paragraph of chapter two.'},
    ]
    # THEN: The marker jump is reported as a warning
    assert warnings == ['page markers jump from 18 to 20']


def test_convert_pdf_book_import_round_trip(manager, tmp_path):
    """
    Test that the converted book imports into the library with the right citations.
    """
    # GIVEN: A converted Estate PDF
    pdf_path = tmp_path / 'en_DA.pdf'
    _make_estate_pdf(pdf_path)
    book_data, _ = convert_pdf_book(pdf_path)

    # WHEN: The book dict is imported
    book, paragraph_count = import_book(manager, book_data)

    # THEN: The book and its citation pages are in the library
    assert paragraph_count == 3
    chapters = manager.get_chapters(book.id)
    paragraphs = manager.get_paragraphs_for_chapter(chapters[0].id)
    assert [(p.page, p.para_on_page) for p in paragraphs] == [(19, 1), (20, 1)]


def test_convert_pdf_book_no_chapters(tmp_path):
    """
    Test that a PDF without the Estate chapter structure is rejected with a clear error.
    """
    # GIVEN: A PDF with body text but no chapter headings
    pdf_path = tmp_path / 'notes.pdf'
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((INDENT_X, 100), 'Just some notes, not a book.', fontsize=BODY_SIZE)
    doc.save(str(pdf_path))
    doc.close()

    # WHEN / THEN: Converting raises an EGWPdfError naming the file
    with pytest.raises(EGWPdfError, match='No chapters found in "notes.pdf"'):
        convert_pdf_book(pdf_path)


def test_join_lines_hyphenation():
    """
    Test the hyphenation repair when joining paragraph lines.
    """
    # Typesetter-broken word: hyphen removed
    assert join_lines(['The unfath-', 'omable love.']) == 'The unfathomable love.'
    # Real compound broken at its hyphen: hyphen kept, no space
    assert join_lines(['A life of self-', 'Denial.']) == 'A life of self-Denial.'
    # Em-dash at line end: kept, joined with a space
    assert join_lines(['He said—', 'and went.']) == 'He said— and went.'
    # Plain lines join with spaces
    assert join_lines(['One', 'two.']) == 'One two.'


def test_guess_defaults():
    """
    Test the metadata guesses from PDF title and egwwritings file names.
    """
    assert guess_defaults('en_DA.pdf', 'The Desire of Ages (1898)') == ('The Desire of Ages', 'DA', 'en')
    # No language prefix: abbreviation from the stem, language defaults to en
    assert guess_defaults('GC.pdf', '') == ('', 'GC', 'en')
    # A stem that is not an abbreviation-shaped name yields no abbreviation
    assert guess_defaults('my scanned book.pdf', 'My Book') == ('My Book', '', 'en')


def test_pdf_book_details_dialog(qapp):
    """
    Test that the details dialog pre-fills the guessed metadata and applies edits.
    """
    from PySide6 import QtWidgets

    from openlp.plugins.egwlibrary.lib.pdfimportdialog import PdfBookDetailsDialog

    # GIVEN: A dialog for a converted book with guessed metadata
    book_data = {'title': 'The Desire of Ages', 'abbreviation': 'DA', 'copyright': '', 'language': 'en',
                 'aliases': [], 'chapters': [{'number': 1, 'title': 'God With Us',
                                              'paragraphs': [{'page': 19, 'text': 'Text.'}]}]}
    dialog = PdfBookDetailsDialog(None, 'en_DA.pdf', book_data, ['page markers jump from 18 to 20'])

    # THEN: The fields are pre-filled and OK is available
    assert dialog.title_edit.text() == 'The Desire of Ages'
    assert dialog.abbreviation_edit.text() == 'DA'
    ok_button = dialog.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
    assert ok_button.isEnabled()

    # WHEN: The user clears the abbreviation
    dialog.abbreviation_edit.setText('  ')
    # THEN: OK is disabled until it is filled again
    assert not ok_button.isEnabled()

    # WHEN: The user corrects the metadata
    dialog.abbreviation_edit.setText('DA')
    dialog.copyright_edit.setText('Public domain.')
    dialog.aliases_edit.setText('Desire of Ages, desire , ')
    result = dialog.book_data()

    # THEN: The edits are applied to the book dict, with aliases split and stripped
    assert result['abbreviation'] == 'DA'
    assert result['copyright'] == 'Public domain.'
    assert result['aliases'] == ['Desire of Ages', 'desire']
    assert result['chapters'] is book_data['chapters']
