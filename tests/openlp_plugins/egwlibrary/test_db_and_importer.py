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
Tests for the EGW Library database manager and the JSON importer, using an in-memory
database.
"""
import json

import pytest

from openlp.plugins.egwlibrary.lib.db import EGWLibraryManager, init_schema
from openlp.plugins.egwlibrary.lib.importer import EGWImportError, import_book, import_json_file


BOOK_DATA = {
    'title': 'The Desire of Ages',
    'abbreviation': 'DA',
    'copyright': 'Public domain.',
    'aliases': ['Desire of Ages', 'desire', 'd.a.'],
    'chapters': [
        {
            'number': 1,
            'title': 'God With Us',
            'paragraphs': [
                {'page': 19, 'text': 'First paragraph about the love of God.'},
                {'page': 19, 'text': 'Second paragraph on page nineteen.'},
                {'page': 20, 'text': 'A paragraph about grace on page twenty.'}
            ]
        },
        {
            'number': 2,
            'title': 'The Chosen People',
            'paragraphs': [
                {'page': 27, 'text': 'The opening paragraph of chapter two.'},
                # No page given: carries forward from the previous paragraph
                {'text': 'Another paragraph, still on page twenty seven.'},
                {'page': 28, 'para': 2, 'text': 'Explicit paragraph number on page twenty eight.'}
            ]
        }
    ]
}


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


def test_import_book(manager):
    """
    Test that a book imports with the right structure and paragraph numbering.
    """
    book, count = import_book(manager, BOOK_DATA)
    assert count == 6
    assert book.title == 'The Desire of Ages'
    chapters = manager.get_chapters(book.id)
    assert [chapter.number for chapter in chapters] == [1, 2]
    assert chapters[0].title == 'God With Us'
    paragraphs = manager.get_paragraphs_for_chapter(chapters[1].id)
    # Page carries forward when omitted
    assert [(p.page, p.para_on_page) for p in paragraphs] == [(27, 1), (27, 2), (28, 2)]
    # paragraph_number restarts per chapter
    assert [p.paragraph_number for p in paragraphs] == [1, 2, 3]


def test_alias_lookup(manager):
    """
    Test that the title, the abbreviation and every alias resolve to the book,
    ignoring case and punctuation.
    """
    book, _ = import_book(manager, BOOK_DATA)
    for name in ['DA', 'da', 'D.A.', 'desire', 'The Desire of Ages', 'the desire of ages!']:
        assert manager.get_book_by_alias(name).id == book.id, name
    assert manager.get_book_by_alias('unknown') is None


def test_reference_queries(manager):
    """
    Test the page and citation range queries.
    """
    book, _ = import_book(manager, BOOK_DATA)
    # Single page
    page_19 = manager.get_paragraphs_for_pages(book.id, 19)
    assert [p.para_on_page for p in page_19] == [1, 2]
    # Page range
    assert len(manager.get_paragraphs_for_pages(book.id, 19, 20)) == 3
    # Single citation
    single = manager.get_paragraphs_for_reference(book.id, 19, 2)
    assert len(single) == 1
    assert single[0].text == 'Second paragraph on page nineteen.'
    # Cross-page citation range 19.2-20.1
    cross = manager.get_paragraphs_for_reference(book.id, 19, 2, 20, 1)
    assert [(p.page, p.para_on_page) for p in cross] == [(19, 2), (20, 1)]


def test_text_search_uses_fts(manager):
    """
    Test that the FTS index is available in the in-memory database and finds words.
    """
    book, _ = import_book(manager, BOOK_DATA)
    assert manager.has_fts() is True
    results = manager.text_search('grace')
    assert len(results) == 1
    assert results[0].page == 20
    # All words must match
    assert manager.text_search('grace nineteen') == []
    # Quoting protects against FTS syntax injection
    assert manager.text_search('grace" OR "love') == []


def test_text_search_book_scope(manager):
    """
    Test that a search can be limited to one book.
    """
    book, _ = import_book(manager, BOOK_DATA)
    other, _ = import_book(manager, {
        'title': 'Steps to Christ',
        'abbreviation': 'SC',
        'paragraphs': [{'page': 9, 'text': 'A paragraph about the love of God in another book.'}]
    })
    assert len(manager.text_search('love')) == 2
    assert len(manager.text_search('love', book_id=book.id)) == 1
    assert len(manager.text_search('love', book_id=other.id)) == 1


def test_like_fallback_search(manager):
    """
    Test that the LIKE fallback finds the same paragraphs when FTS is unavailable.
    """
    import_book(manager, BOOK_DATA)
    manager._has_fts = False
    results = manager.text_search('grace')
    assert len(results) == 1
    assert results[0].page == 20


def test_like_fallback_search_orders_by_citation(manager):
    """
    Test that the LIKE fallback keeps results in page/paragraph order.
    """
    book, _ = import_book(manager, {
        'title': 'Ordered Book',
        'abbreviation': 'OB',
        'chapters': [
            {'number': 1, 'title': 'One', 'paragraphs': [
                {'page': 10, 'text': 'match'},
                {'page': 11, 'text': 'match'}
            ]},
            {'number': 2, 'title': 'Two', 'paragraphs': [
                {'page': 12, 'text': 'match'}
            ]}
        ]
    })
    manager._has_fts = False
    results = manager.text_search('match', book_id=book.id)
    assert [(p.page, p.para_on_page) for p in results] == [(10, 1), (11, 1), (12, 1)]


def test_chapterless_book(manager):
    """
    Test that a book without chapters gets a single implicit chapter with number 0.
    """
    book, count = import_book(manager, {
        'title': 'A Tract',
        'abbreviation': 'TR',
        'paragraphs': ['Paragraph one.', 'Paragraph two.']
    })
    assert count == 2
    chapters = manager.get_chapters(book.id)
    assert len(chapters) == 1
    assert chapters[0].number == 0
    assert chapters[0].title == ''


def test_reimport_replaces_book(manager):
    """
    Test that importing a book with an existing abbreviation replaces it.
    """
    import_book(manager, BOOK_DATA)
    replacement = dict(BOOK_DATA, title='The Desire of Ages (revised)')
    book, _ = import_book(manager, replacement)
    books = manager.get_books()
    assert len(books) == 1
    assert books[0].title == 'The Desire of Ages (revised)'
    # The FTS index was cleaned up: no duplicate hits
    assert len(manager.text_search('grace')) == 1
    assert manager.get_book_by_alias('desire').id == book.id


def test_delete_book_cleans_up(manager):
    """
    Test that deleting a book removes its chapters, aliases and search index entries.
    """
    book, _ = import_book(manager, BOOK_DATA)
    assert manager.delete_book(book.id) is True
    assert manager.get_books() == []
    assert manager.get_book_by_alias('DA') is None
    assert manager.text_search('grace') == []


def test_import_validation(manager):
    """
    Test that invalid books are rejected with an EGWImportError.
    """
    with pytest.raises(EGWImportError):
        import_book(manager, {'title': 'No abbreviation'})
    with pytest.raises(EGWImportError):
        import_book(manager, {'title': 'Empty', 'abbreviation': 'E', 'chapters': []})
    with pytest.raises(EGWImportError):
        import_book(manager, {'title': 'Blank', 'abbreviation': 'B', 'paragraphs': [{'text': '   '}]})


def test_import_empty_book_does_not_replace(manager):
    """
    Test that a broken replacement file does not delete the existing book.
    """
    import_book(manager, BOOK_DATA)
    with pytest.raises(EGWImportError):
        import_book(manager, {'title': 'The Desire of Ages', 'abbreviation': 'DA',
                              'paragraphs': [{'text': ''}]})
    assert len(manager.get_books()) == 1
    assert len(manager.text_search('grace')) == 1


def test_import_json_file(manager, tmp_path):
    """
    Test importing from an actual file, with several books in one file.
    """
    file_path = tmp_path / 'library.json'
    file_path.write_text(json.dumps({'books': [
        BOOK_DATA,
        {'title': 'Steps to Christ', 'abbreviation': 'SC',
         'paragraphs': [{'page': 9, 'text': 'A paragraph.'}]}
    ]}), encoding='utf-8')
    results = import_json_file(manager, file_path)
    assert [(book.abbreviation, count) for book, count in results] == [('DA', 6), ('SC', 1)]


def test_import_json_file_invalid(manager, tmp_path):
    """
    Test that an unreadable or non-book JSON file raises a user-visible error.
    """
    file_path = tmp_path / 'broken.json'
    file_path.write_text('this is not json', encoding='utf-8')
    with pytest.raises(EGWImportError):
        import_json_file(manager, file_path)
    file_path.write_text('[1, 2, 3]', encoding='utf-8')
    with pytest.raises(EGWImportError):
        import_json_file(manager, file_path)
