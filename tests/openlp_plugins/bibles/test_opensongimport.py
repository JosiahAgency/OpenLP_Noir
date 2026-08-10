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
This module contains tests for the OpenSong Bible importer.
"""
import pytest
from unittest.mock import MagicMock, call, patch

from lxml import objectify

from openlp.plugins.bibles.lib.bibleimport import BibleImport
from openlp.plugins.bibles.lib.importers.opensong import OpenSongBible, get_text, parse_chapter_number
from tests.utils import load_external_result_data
from tests.utils.constants import RESOURCE_PATH


TEST_PATH = RESOURCE_PATH / 'bibles'


@pytest.fixture
def manager():
    db_man = patch('openlp.plugins.bibles.lib.db.DBManager')
    yield db_man.start()
    db_man.stop()


@pytest.fixture
def mocked_find_and_create_book():
    facb = patch.object(BibleImport, 'find_and_create_book')
    yield facb.start()
    facb.stop()


def test_create_importer(manager: MagicMock, mock_settings: MagicMock):
    """
    Test creating an instance of the OpenSong file importer
    """
    # GIVEN: A mocked out "manager"
    mocked_manager = MagicMock()

    # WHEN: An importer object is created
    importer = OpenSongBible(mocked_manager, path='.', name='.', file_path=None)

    # THEN: The importer should be an instance of BibleDB
    assert isinstance(importer, BibleImport)


def test_get_text_no_text(manager, mock_settings):
    """
    Test that get_text handles elements containing text in a combination of text and tail attributes
    """
    # GIVEN: Some test data which contains an empty element and an instance of OpenSongBible
    test_data = objectify.fromstring('<element></element>')

    # WHEN: Calling get_text
    result = get_text(test_data)

    # THEN: A blank string should be returned
    assert result == ''


def test_get_text_text(manager, mock_settings):
    """
    Test that get_text handles elements containing text in a combination of text and tail attributes
    """
    # GIVEN: Some test data which contains all possible permutation of text and tail text possible and an instance
    #        of OpenSongBible
    test_data = objectify.fromstring('<element>Element text '
                                     '<sub_text_tail>sub_text_tail text </sub_text_tail>sub_text_tail tail '
                                     '<sub_text>sub_text text </sub_text>'
                                     '<sub_tail></sub_tail>sub_tail tail</element>')

    # WHEN: Calling get_text
    result = get_text(test_data)

    # THEN: The text returned should be as expected
    assert result == 'Element text sub_text_tail text sub_text_tail tail sub_text text sub_tail tail'


def test_parse_chapter_number(manager, mock_settings):
    """
    Test parse_chapter_number when supplied with chapter number and an instance of OpenSongBible
    """
    # GIVEN: The number 10 represented as a string
    # WHEN: Calling parse_chapter_nnumber
    result = parse_chapter_number('10', 0)

    # THEN: The 10 should be returned as an Int
    assert result == 10


def test_parse_chapter_number_empty_attribute(manager, mock_settings):
    """
    Testparse_chapter_number when the chapter number is an empty string. (Bug #1074727)
    """
    # GIVEN: An empty string, and the previous chapter number set as 12  and an instance of OpenSongBible
    # WHEN: Calling parse_chapter_number
    result = parse_chapter_number('', 12)

    # THEN: parse_chapter_number should increment the previous verse number
    assert result == 13


def test_parse_verse_number_valid_verse_no(manager, mock_settings):
    """
    Test parse_verse_number when supplied with a valid verse number
    """
    # GIVEN: An instance of OpenSongBible, the number 15 represented as a string and an instance of OpenSongBible
    importer = OpenSongBible(MagicMock(), path='.', name='.', file_path=None)

    # WHEN: Calling parse_verse_number
    result = importer.parse_verse_number('15', 0)

    # THEN: parse_verse_number should return the verse number
    assert result == 15


def test_parse_verse_number_verse_range(manager, mock_settings):
    """
    Test parse_verse_number when supplied with a verse range
    """
    # GIVEN: An instance of OpenSongBible, and the range 24-26 represented as a string
    importer = OpenSongBible(MagicMock(), path='.', name='.', file_path=None)

    # WHEN: Calling parse_verse_number
    result = importer.parse_verse_number('24-26', 0)

    # THEN: parse_verse_number should return the first verse number in the range
    assert result == 24


def test_parse_verse_number_invalid_verse_no(manager, mock_settings):
    """
    Test parse_verse_number when supplied with a invalid verse number
    """
    # GIVEN: An instance of OpenSongBible, a non numeric string represented as a string
    importer = OpenSongBible(MagicMock(), path='.', name='.', file_path=None)

    # WHEN: Calling parse_verse_number
    result = importer.parse_verse_number('invalid', 41)

    # THEN: parse_verse_number should increment the previous verse number
    assert result == 42


def test_parse_verse_number_empty_attribute(manager, mock_settings):
    """
    Test parse_verse_number when the verse number is an empty string. (Bug #1074727)
    """
    # GIVEN: An instance of OpenSongBible, an empty string, and the previous verse number set as 14
    importer = OpenSongBible(MagicMock(), path='.', name='.', file_path=None)
    # WHEN: Calling parse_verse_number
    result = importer.parse_verse_number('', 14)

    # THEN: parse_verse_number should increment the previous verse number
    assert result == 15


def test_parse_verse_number_invalid_type(manager, mock_settings):
    """
    Test parse_verse_number when the verse number is an invalid type)
    """
    with patch.object(OpenSongBible, 'log_warning')as mocked_log_warning:
        # GIVEN: An instance of OpenSongBible, a Tuple, and the previous verse number set as 12
        importer = OpenSongBible(MagicMock(), path='.', name='.', file_path=None)

        # WHEN: Calling parse_verse_number
        result = importer.parse_verse_number((1, 2, 3), 12)

        # THEN: parse_verse_number should log the verse number it was called with increment the previous verse
        #       number
        mocked_log_warning.assert_called_once_with('Illegal verse number: (1, 2, 3)')
        assert result == 13


def test_process_books_stop_import(manager, mocked_find_and_create_book, mock_settings):
    """
    Test process_books when stop_import is set to True
    """
    # GIVEN: An instance of OpenSongBible
    importer = OpenSongBible(MagicMock(), path='.', name='.', file_path=None)

    # WHEN: stop_import_flag is set to True
    importer.stop_import_flag = True
    importer.process_books(['Book'])

    # THEN: find_and_create_book should not have been called
    assert mocked_find_and_create_book.called is False


def test_process_books_completes(manager, mocked_find_and_create_book, mock_settings):
    """
    Test process_books when it processes all books
    """
    # GIVEN: An instance of OpenSongBible Importer and two mocked books
    mocked_find_and_create_book.side_effect = ['db_book1', 'db_book2']
    with patch.object(OpenSongBible, 'process_chapters') as mocked_process_chapters:
        importer = OpenSongBible(MagicMock(), path='.', name='.', file_path=None)

        book1 = MagicMock()
        book1.attrib = {'n': 'Name1'}
        book1.c = 'Chapter1'
        book2 = MagicMock()
        book2.attrib = {'n': 'Name2'}
        book2.c = 'Chapter2'
        importer.language_id = 10
        importer.session = MagicMock()
        importer.stop_import_flag = False

        # WHEN: Calling process_books with the two books
        importer.process_books([book1, book2])

        # THEN: find_and_create_book and process_books should be called with the details from the mocked books
        assert mocked_find_and_create_book.call_args_list == [call('Name1', 2, 10), call('Name2', 2, 10)]
        assert mocked_process_chapters.call_args_list == \
            [call('db_book1', 'Chapter1'), call('db_book2', 'Chapter2')]
        assert importer.session.commit.call_count == 2


def test_process_chapters_stop_import(manager, mock_settings):
    """
    Test process_chapters when stop_import is set to True
    """
    # GIVEN: An isntance of OpenSongBible
    importer = OpenSongBible(MagicMock(), path='.', name='.', file_path=None)
    importer.parse_chapter_number = MagicMock()

    # WHEN: stop_import_flag is set to True
    importer.stop_import_flag = True
    importer.process_chapters('Book', ['Chapter1'])

    # THEN: importer.parse_chapter_number not have been called
    assert importer.parse_chapter_number.called is False


@patch('openlp.plugins.bibles.lib.importers.opensong.parse_chapter_number', **{'side_effect': [1, 2]})
def test_process_chapters_completes(mocked_parse_chapter_number, manager, mock_settings):
    """
    Test process_chapters when it completes
    """
    # GIVEN: An instance of OpenSongBible
    importer = OpenSongBible(MagicMock(), path='.', name='.', file_path=None)
    importer.wizard = MagicMock()

    # WHEN: called with some valid data
    book = MagicMock()
    book.name = "Book"
    chapter1 = MagicMock()
    chapter1.attrib = {'n': '1'}
    chapter1.c = 'Chapter1'
    chapter1.v = ['Chapter1 Verses']
    chapter2 = MagicMock()
    chapter2.attrib = {'n': '2'}
    chapter2.c = 'Chapter2'
    chapter2.v = ['Chapter2 Verses']

    importer.process_verses = MagicMock()
    importer.stop_import_flag = False
    importer.process_chapters(book, [chapter1, chapter2])

    # THEN: parse_chapter_number, process_verses and increment_process_bar should have been called
    assert mocked_parse_chapter_number.call_args_list == [call('1', 0), call('2', 1)]
    assert importer.process_verses.call_args_list == \
        [call(book, 1, ['Chapter1 Verses']), call(book, 2, ['Chapter2 Verses'])]
    assert importer.wizard.increment_progress_bar.call_args_list == [call('Importing Book 1...'),
                                                                     call('Importing Book 2...')]


def test_process_verses_stop_import(manager, mock_settings):
    """
    Test process_verses when stop_import is set to True
    """
    # GIVEN: An isntance of OpenSongBible
    importer = OpenSongBible(MagicMock(), path='.', name='.', file_path=None)
    importer.parse_verse_number = MagicMock()

    # WHEN: stop_import_flag is set to True
    importer.stop_import_flag = True
    importer.process_verses('Book', 1, 'Verses')

    # THEN: importer.parse_verse_number not have been called
    assert importer.parse_verse_number.called is False


def test_process_verses_completes(manager, mock_settings):
    """
    Test process_verses when it completes
    """
    with patch('openlp.plugins.bibles.lib.importers.opensong.get_text',
               **{'side_effect': ['Verse1 Text', 'Verse2 Text']}) as mocked_get_text, \
            patch.object(OpenSongBible, 'parse_verse_number',
                         **{'side_effect': [1, 2]}) as mocked_parse_verse_number:
        # GIVEN: An instance of OpenSongBible
        importer = OpenSongBible(MagicMock(), path='.', name='.', file_path=None)
        importer.wizard = MagicMock()

        # WHEN: called with some valid data
        book = MagicMock()
        book.id = 1
        verse1 = MagicMock()
        verse1.attrib = {'n': '1'}
        verse1.c = 'Chapter1'
        verse1.v = ['Chapter1 Verses']
        verse2 = MagicMock()
        verse2.attrib = {'n': '2'}
        verse2.c = 'Chapter2'
        verse2.v = ['Chapter2 Verses']

        importer.create_verse = MagicMock()
        importer.stop_import_flag = False
        importer.process_verses(book, 1, [verse1, verse2])

        # THEN: parse_chapter_number, process_verses and increment_process_bar should have been called
        assert mocked_parse_verse_number.call_args_list == [call('1', 0), call('2', 1)]
        assert mocked_get_text.call_args_list == [call(verse1), call(verse2)]
        assert importer.create_verse.call_args_list == \
            [call(1, 1, 1, 'Verse1 Text'), call(1, 1, 2, 'Verse2 Text')]


def test_do_import_parse_xml_fails(manager, mock_settings):
    """
    Test do_import when parse_xml fails (returns None)
    """
    # GIVEN: An instance of OpenSongBible and a mocked parse_xml which returns False
    with patch.object(OpenSongBible, 'log_debug'), \
            patch.object(OpenSongBible, 'validate_xml_file'), \
            patch.object(OpenSongBible, 'parse_xml', return_value=None), \
            patch.object(OpenSongBible, 'get_language_id') as mocked_language_id:
        importer = OpenSongBible(MagicMock(), path='.', name='.', file_path=None)

        # WHEN: Calling do_import
        result = importer.do_import()

        # THEN: do_import should return False and get_language_id should have not been called
        assert result is False
        assert mocked_language_id.called is False


def test_do_import_no_language(manager, mock_settings):
    """
    Test do_import when the user cancels the language selection dialog
    """
    # GIVEN: An instance of OpenSongBible and a mocked get_language which returns False
    with patch.object(OpenSongBible, 'log_debug'), \
            patch.object(OpenSongBible, 'validate_xml_file'), \
            patch.object(OpenSongBible, 'parse_xml'), \
            patch.object(OpenSongBible, 'get_language_id', return_value=False), \
            patch.object(OpenSongBible, 'process_books') as mocked_process_books:
        importer = OpenSongBible(MagicMock(), path='.', name='.', file_path=None)

        # WHEN: Calling do_import
        result = importer.do_import()

        # THEN: do_import should return False and process_books should have not been called
        assert result is False
        assert mocked_process_books.called is False


def test_do_import_completes(manager, mock_settings):
    """
    Test do_import when it completes successfully
    """
    # GIVEN: An instance of OpenSongBible
    with patch.object(OpenSongBible, 'log_debug'), \
            patch.object(OpenSongBible, 'validate_xml_file'), \
            patch.object(OpenSongBible, 'parse_xml') as mocked_parse_xml, \
            patch.object(OpenSongBible, 'get_language_id', return_value=10), \
            patch.object(OpenSongBible, 'process_books'):
        mocked_parse_xml.return_value = MagicMock(b=[MagicMock()])
        importer = OpenSongBible(MagicMock(), path='.', name='.', file_path=None)

        # WHEN: Calling do_import
        result = importer.do_import()

        # THEN: do_import should return True
        assert result is True


def test_file_import(manager, mock_settings):
    """
    Test the actual import of OpenSong Bible file
    """
    # GIVEN: Test files with a mocked out "manager", "import_wizard", and mocked functions
    #       get_book_ref_id_by_name, create_verse, create_book, session and get_language.
    test_data = load_external_result_data(TEST_PATH / 'dk1933.json')
    bible_file = 'opensong-dk1933.xml'
    with patch('openlp.plugins.bibles.lib.importers.opensong.OpenSongBible.application'):
        mocked_manager = MagicMock()
        mocked_import_wizard = MagicMock()
        importer = OpenSongBible(mocked_manager, path='.', name='.', file_path=None)
        importer.wizard = mocked_import_wizard
        importer.get_book_ref_id_by_name = MagicMock()
        importer.create_verse = MagicMock()
        importer.create_book = MagicMock()
        importer.session = MagicMock()
        importer.get_language = MagicMock()
        importer.get_language.return_value = 'Danish'
        importer.get_language_id = MagicMock()
        importer.get_language_id.return_value = 'dk'

        # WHEN: Importing bible file
        importer.file_path = TEST_PATH / bible_file
        importer.do_import()

        # THEN: The create_verse() method should have been called with each verse in the file.
        assert importer.create_verse.called is True
        for verse_tag, verse_text in test_data['verses']:
            importer.create_verse.assert_any_call(importer.create_book().id, 1, int(verse_tag), verse_text)
