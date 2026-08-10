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
This module contains tests for the bibleimport module.
"""
import pytest
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from lxml import etree, objectify
from PySide6.QtWidgets import QDialog

from openlp.core.common.i18n import Language
from openlp.core.common.registry import Registry
from openlp.core.lib.exceptions import ValidationError
from openlp.plugins.bibles.lib.bibleimport import BibleImport
from openlp.plugins.bibles.lib.db import BibleDB


@pytest.fixture()
def test_file():
    return BytesIO(
        b'<?xml version="1.0" encoding="UTF-8" ?>\n'
        b'<root>\n'
        b'    <data><div>Test<p>data</p><a>to</a>keep</div></data>\n'
        b'    <data><unsupported>Test<x>data</x><y>to</y>discard</unsupported></data>\n'
        b'</root>'
    )


@pytest.fixture()
def error_message_box(settings):
    Registry().register('main_window', MagicMock())
    m_box = patch('openlp.plugins.bibles.lib.bibleimport.critical_error_message_box')
    yield m_box.start()
    m_box.stop()


@pytest.fixture()
def mocked_open():
    m_open = patch.object(Path, 'open')
    yield m_open.start()
    m_open.stop()


@pytest.fixture()
def mocked_setup():
    s_up = patch('openlp.plugins.bibles.lib.db.BibleDB._setup')
    yield s_up.start()
    s_up.stop()


def test_init_kwargs_none(mocked_setup, registry):
    """
    Test the initialisation of the BibleImport Class when no key word arguments are supplied
    """
    # GIVEN: A patched BibleDB._setup, BibleImport class and mocked parent
    # WHEN: Creating an instance of BibleImport with no key word arguments
    instance = BibleImport(MagicMock())

    # THEN: The file_path attribute should be None
    assert instance.file_path is None
    assert isinstance(instance, BibleDB)


def test_init_kwargs_set(mocked_setup, registry):
    """
    Test the initialisation of the BibleImport Class when supplied with select keyword arguments
    """
    # GIVEN: A patched BibleDB._setup, BibleImport class and mocked parent
    # WHEN: Creating an instance of BibleImport with selected key word arguments
    kwargs = {'file_path': 'bible.xml'}
    instance = BibleImport(MagicMock(), **kwargs)

    # THEN: The file_path keyword should be set to bible.xml
    assert instance.file_path == 'bible.xml'
    assert isinstance(instance, BibleDB)


@patch('openlp.plugins.bibles.forms.LanguageForm')
def test_get_language_canceled(MockedLanguageForm, mocked_setup, registry):
    """
    Test the BibleImport.get_language method when the user rejects the dialog box
    """
    # GIVEN: A mocked LanguageForm with an exec method which returns QtDialog.Rejected and an instance of BibleDB
    # TODO: The integer value of QtDialog.Rejected is 0. Using the enumeration causes a seg fault for some reason
    MockedLanguageForm.return_value.exec.return_value = 0
    instance = BibleImport(MagicMock())
    mocked_wizard = MagicMock()
    instance.wizard = mocked_wizard

    # WHEN: Calling get_language()
    result = instance.get_language('ESV')

    # THEN: get_language() should return False
    MockedLanguageForm.assert_called_once_with(mocked_wizard)
    MockedLanguageForm.return_value.exec.assert_called_once_with('ESV')
    assert result is False, 'get_language() should return False if the user rejects the dialog box'
    assert instance.import_failure is not None
    assert instance.import_failure.code == 'language-selection-cancelled'


@patch.object(BibleDB, 'save_meta')
@patch('openlp.plugins.bibles.forms.LanguageForm')
def test_get_language_accepted(MockedLanguageForm, mocked_save_meta, mocked_setup, registry):
    """
    Test the BibleImport.get_language method when the user accepts the dialog box
    """
    # GIVEN: A mocked LanguageForm with an exec method which returns QtDialog.Accepted an instance of BibleDB and
    #       a combobox with the selected item data as 10
    # The integer value of QtDialog.Accepted is 1. Using the enumeration causes a seg fault for some reason
    MockedLanguageForm.return_value.exec.return_value = 1
    MockedLanguageForm.return_value.language_combo_box.itemData.return_value = 10
    instance = BibleImport(MagicMock())
    mocked_wizard = MagicMock()
    instance.wizard = mocked_wizard

    # WHEN: Calling get_language()
    result = instance.get_language('Bible Name')

    # THEN: get_language() should return the id of the selected language in the combo box
    MockedLanguageForm.assert_called_once_with(mocked_wizard)
    MockedLanguageForm.return_value.exec.assert_called_once_with('Bible Name')
    assert result == 10, 'get_language() should return the id of the language the user has chosen when ' \
        'they accept the dialog box'


@patch('openlp.plugins.bibles.lib.bibleimport.get_language')
@patch.object(BibleImport, 'get_language')
def test_get_language_id_language_found(mocked_db_get_language, mocked_get_language, mocked_setup, registry):
    """
    Test get_language_id() when called with a name found in the languages list
    """
    # GIVEN: A mocked languages.get_language which returns language and an instance of BibleImport
    mocked_get_language.return_value = Language(30, 'English', 'en')
    instance = BibleImport(MagicMock())
    instance.save_meta = MagicMock()

    # WHEN: Calling get_language_id() with a language name and bible name
    result = instance.get_language_id('English', 'KJV')

    # THEN: The id of the language returned from languages.get_language should be returned
    mocked_get_language.assert_called_once_with('English')
    assert mocked_db_get_language.called is False
    instance.save_meta.assert_called_once_with('language_id', 30)
    assert result == 30, 'Result should be 30, was {}'.format(result)


@patch('openlp.plugins.bibles.lib.bibleimport.get_language', return_value=None)
@patch.object(BibleImport, 'get_language', return_value=20)
def test_get_language_id_language_not_found(mocked_db_get_language, mocked_languages_get_language,
                                            mocked_setup, registry):
    """
    Test get_language_id() when called with a name not found in the languages list
    """
    # GIVEN: A mocked languages.get_language which returns language and an instance of BibleImport
    instance = BibleImport(MagicMock())
    instance.save_meta = MagicMock()

    # WHEN: Calling get_language_id() with a language name and bible name
    result = instance.get_language_id('RUS', 'KJV')

    # THEN: The id of the language returned from languages.get_language should be returned
    mocked_languages_get_language.assert_called_once_with('RUS')
    mocked_db_get_language.assert_called_once_with('KJV')
    instance.save_meta.assert_called_once_with('language_id', 20)
    assert result == 20


@patch('openlp.plugins.bibles.lib.bibleimport.get_language', return_value=None)
@patch.object(BibleImport, 'get_language', return_value=40)
@patch.object(BibleImport, 'log_error')
def test_get_language_id_user_choice(mocked_log_error, mocked_db_get_language, mocked_languages_get_language,
                                     mocked_setup, registry):
    """
    Test get_language_id() when the language is not found and the user is asked for the language
    """
    # GIVEN: A mocked languages.get_language which returns None a mocked BibleDB.get_language which returns a
    #       language id.
    instance = BibleImport(MagicMock())
    instance.save_meta = MagicMock()

    # WHEN: Calling get_language_id() with a language name and bible name
    result = instance.get_language_id('English', 'KJV')

    # THEN: The id of the language returned from BibleDB.get_language should be returned
    mocked_languages_get_language.assert_called_once_with('English')
    mocked_db_get_language.assert_called_once_with('KJV')
    assert mocked_log_error.error.called is False
    instance.save_meta.assert_called_once_with('language_id', 40)
    assert result == 40


@patch('openlp.plugins.bibles.lib.bibleimport.get_language', return_value=None)
@patch.object(BibleImport, 'get_language', return_value=None)
@patch.object(BibleImport, 'log_error')
def test_get_language_id_user_choice_rejected(mocked_log_error, mocked_db_get_language,
                                              mocked_languages_get_language, mocked_setup, registry):
    """
    Test get_language_id() when the language is not found and the user rejects the dilaog box
    """
    # GIVEN: A mocked languages.get_language which returns None a mocked BibleDB.get_language which returns a
    #       language id.
    instance = BibleImport(MagicMock())
    instance.save_meta = MagicMock()

    # WHEN: Calling get_language_id() with a language name and bible name
    result = instance.get_language_id('Qwerty', 'KJV')

    # THEN: None should be returned and an error should be logged
    mocked_languages_get_language.assert_called_once_with('Qwerty')
    mocked_db_get_language.assert_called_once_with('KJV')
    mocked_log_error.assert_called_once_with(
        'Language detection failed when importing from "KJV". User aborted language selection.')
    assert instance.save_meta.called is False
    assert result is None


@patch.object(BibleImport, 'log_debug')
@patch('openlp.plugins.bibles.lib.bibleimport.BiblesResourcesDB', **{'get_book.return_value': {'id': 20}})
def test_get_book_ref_id_by_name_get_book(MockBibleResourcesDB, mocked_log_debug, mocked_setup, registry):
    """
    Test get_book_ref_id_by_name when the book is found as a book in BiblesResourcesDB
    """
    # GIVEN: An instance of BibleImport and a mocked BiblesResourcesDB which returns a book id when get_book is
    #        called
    instance = BibleImport(MagicMock())

    # WHEN: Calling get_book_ref_id_by_name
    result = instance.get_book_ref_id_by_name('Gen', 66, 4)

    # THEN: The bible id should be returned
    assert result == 20


@patch.object(BibleImport, 'log_debug')
@patch('openlp.plugins.bibles.lib.bibleimport.BiblesResourcesDB',
       **{'get_book.return_value': None, 'get_alternative_book_name.return_value': 30})
def test_get_book_ref_id_by_name_get_alternative_book_name(MockBibleResourcesDB, mocked_log_debug,
                                                           mocked_setup, registry):
    """
    Test get_book_ref_id_by_name when the book is found as an alternative book in BiblesResourcesDB
    """
    # GIVEN: An instance of BibleImport and a mocked BiblesResourcesDB which returns a book id when
    #        get_alternative_book_name is called
    instance = BibleImport(MagicMock())

    # WHEN: Calling get_book_ref_id_by_name
    result = instance.get_book_ref_id_by_name('Gen', 66, 4)

    # THEN: The bible id should be returned
    assert result == 30


@patch.object(BibleImport, 'log_debug')
@patch('openlp.plugins.bibles.lib.bibleimport.BiblesResourcesDB',
       **{'get_book.return_value': None, 'get_alternative_book_name.return_value': None})
@patch('openlp.plugins.bibles.lib.bibleimport.AlternativeBookNamesDB', **{'get_book_reference_id.return_value': 40})
def test_get_book_ref_id_by_name_get_book_reference_id(MockAlterativeBookNamesDB, MockBibleResourcesDB,
                                                       mocked_log_debug, mocked_setup, registry):
    """
    Test get_book_ref_id_by_name when the book is found as a book in AlternativeBookNamesDB
    """
    # GIVEN: An instance of BibleImport and a mocked AlternativeBookNamesDB which returns a book id when
    #        get_book_reference_id is called
    instance = BibleImport(MagicMock())

    # WHEN: Calling get_book_ref_id_by_name
    result = instance.get_book_ref_id_by_name('Gen', 66, 4)

    # THEN: The bible id should be returned
    assert result == 40


@patch.object(BibleImport, 'log_debug')
@patch.object(BibleImport, 'get_books')
@patch('openlp.plugins.bibles.lib.bibleimport.BiblesResourcesDB',
       **{'get_book.return_value': None, 'get_alternative_book_name.return_value': None})
@patch('openlp.plugins.bibles.lib.bibleimport.AlternativeBookNamesDB',
       **{'get_book_reference_id.return_value': None})
@patch('openlp.plugins.bibles.forms.BookNameForm',
       return_value=MagicMock(**{'exec.return_value': QDialog.DialogCode.Rejected}))
def test_get_book_ref_id_by_name_book_name_form_rejected(MockBookNameForm, MockAlterativeBookNamesDB,
                                                         MockBibleResourcesDB, mocked_get_books, mocked_log_debug,
                                                         mocked_setup, registry):
    """
    Test get_book_ref_id_by_name when the user rejects the BookNameForm
    """
    # GIVEN: An instance of BibleImport and a mocked BookNameForm which simulates a user rejecting the dialog
    instance = BibleImport(MagicMock())

    # WHEN: Calling get_book_ref_id_by_name
    result = instance.get_book_ref_id_by_name('Gen', 66, 4)

    # THEN: None should be returned
    assert result is None


@patch.object(BibleImport, 'log_debug')
@patch.object(BibleImport, 'get_books')
@patch('openlp.plugins.bibles.lib.bibleimport.BiblesResourcesDB',
       **{'get_book.return_value': None, 'get_alternative_book_name.return_value': None})
@patch('openlp.plugins.bibles.lib.bibleimport.AlternativeBookNamesDB',
       **{'get_book_reference_id.return_value': None})
@patch('openlp.plugins.bibles.forms.BookNameForm',
       return_value=MagicMock(**{'exec.return_value': QDialog.DialogCode.Accepted, 'book_id': 50}))
def test_get_book_ref_id_by_name_book_name_form_accepted(MockBookNameForm, MockAlterativeBookNamesDB,
                                                         MockBibleResourcesDB, mocked_get_books, mocked_log_debug,
                                                         mocked_setup, registry):
    """
    Test get_book_ref_id_by_name when the user accepts the BookNameForm
    """
    # GIVEN: An instance of BibleImport and a mocked BookNameForm which simulates a user accepting the dialog
    instance = BibleImport(MagicMock())

    # WHEN: Calling get_book_ref_id_by_name
    result = instance.get_book_ref_id_by_name('Gen', 66, 4)

    # THEN: An alternative book name should be created and a bible id should be returned
    MockAlterativeBookNamesDB.create_alternative_book_name.assert_called_once_with('Gen', 50, 4)
    assert result == 50


@patch('openlp.plugins.bibles.lib.bibleimport.is_zipfile', return_value=True)
def test_is_compressed_compressed(mocked_is_zipfile, mocked_open, mocked_setup, error_message_box):
    """
    Test is_compressed when the 'file' being tested is compressed
    """
    # GIVEN: An instance of BibleImport and a mocked is_zipfile which returns True
    instance = BibleImport(MagicMock())

    # WHEN: Calling is_compressed
    result = instance.is_compressed('file.ext')

    # THEN: Then critical_error_message_box should be called informing the user that the file is compressed and
    #       True should be returned
    error_message_box.assert_called_once_with(
        message='The file "file.ext" you supplied is compressed. You must decompress it before import.')
    assert result is True


@patch('openlp.plugins.bibles.lib.bibleimport.is_zipfile', return_value=False)
def test_is_compressed_not_compressed(mocked_is_zipfile, mocked_open, mocked_setup, error_message_box):
    """
    Test is_compressed when the 'file' being tested is not compressed
    """
    # GIVEN: An instance of BibleImport and a mocked is_zipfile which returns False
    instance = BibleImport(MagicMock())

    # WHEN: Calling is_compressed
    result = instance.is_compressed('file.ext')

    # THEN: False should be returned and critical_error_message_box should not have been called
    assert result is False
    assert error_message_box.called is False


def test_parse_xml_etree(registry, mocked_open, mocked_setup, test_file):
    """
    Test BibleImport.parse_xml() when called with the use_objectify default value
    """
    # GIVEN: A sample "file" to parse and an instance of BibleImport
    mocked_open.return_value = test_file
    instance = BibleImport(MagicMock())
    instance.wizard = MagicMock()

    # WHEN: Calling parse_xml
    result = instance.parse_xml(Path('file.tst'))

    # THEN: The result returned should contain the correct data, and should be an instance of eetree_Element
    assert etree.tostring(result) == b'<root>\n    <data><div>Test<p>data</p><a>to</a>keep</div></data>\n' \
        b'    <data><unsupported>Test<x>data</x><y>to</y>discard</unsupported></data>\n</root>'
    assert isinstance(result, etree._Element)


def test_parse_xml_etree_use_objectify(registry, mocked_open, mocked_setup, test_file):
    """
    Test BibleImport.parse_xml() when called with use_objectify set to True
    """
    # GIVEN: A sample "file" to parse and an instance of BibleImport
    mocked_open.return_value = test_file
    instance = BibleImport(MagicMock())
    instance.wizard = MagicMock()

    # WHEN: Calling parse_xml
    result = instance.parse_xml(Path('file.tst'), use_objectify=True)

    # THEN: The result returned should contain the correct data, and should be an instance of ObjectifiedElement
    assert etree.tostring(result) == b'<root><data><div>Test<p>data</p><a>to</a>keep</div></data>' \
        b'<data><unsupported>Test<x>data</x><y>to</y>discard</unsupported></data></root>'
    assert isinstance(result, objectify.ObjectifiedElement)


def test_parse_xml_elements(registry, mocked_open, mocked_setup, test_file):
    """
    Test BibleImport.parse_xml() when given a tuple of elements to remove
    """
    # GIVEN: A tuple of elements to remove and an instance of BibleImport
    mocked_open.return_value = test_file
    elements = ('unsupported', 'x', 'y')
    instance = BibleImport(MagicMock())
    instance.wizard = MagicMock()

    # WHEN: Calling parse_xml, with a test file
    result = instance.parse_xml(Path('file.tst'), elements=elements)

    # THEN: The result returned should contain the correct data
    assert etree.tostring(result) == \
        b'<root>\n    <data><div>Test<p>data</p><a>to</a>keep</div></data>\n    <data/>\n</root>'


def test_parse_xml_tags(registry, mocked_open, mocked_setup, test_file):
    """
    Test BibleImport.parse_xml() when given a tuple of tags to remove
    """
    # GIVEN: A tuple of tags to remove and an instance of BibleImport
    mocked_open.return_value = test_file
    tags = ('div', 'p', 'a')
    instance = BibleImport(MagicMock())
    instance.wizard = MagicMock()

    # WHEN: Calling parse_xml, with a test file
    result = instance.parse_xml(Path('file.tst'), tags=tags)

    # THEN: The result returned should contain the correct data
    assert etree.tostring(result) == b'<root>\n    <data>Testdatatokeep</data>\n    <data><unsupported>Test' \
        b'<x>data</x><y>to</y>discard</unsupported></data>\n</root>'


def test_parse_xml_elements_tags(registry, mocked_open, mocked_setup, test_file):
    """
    Test BibleImport.parse_xml() when given a tuple of elements and of tags to remove
    """
    # GIVEN: A tuple of elements and of tags to remove and an instance of BibleImport
    mocked_open.return_value = test_file
    elements = ('unsupported', 'x', 'y')
    tags = ('div', 'p', 'a')
    instance = BibleImport(MagicMock())
    instance.wizard = MagicMock()

    # WHEN: Calling parse_xml, with a test file
    result = instance.parse_xml(Path('file.tst'), elements=elements, tags=tags)

    # THEN: The result returned should contain the correct data
    assert etree.tostring(result) == b'<root>\n    <data>Testdatatokeep</data>\n    <data/>\n</root>'


@patch.object(BibleImport, 'log_exception')
def test_parse_xml_file_file_not_found_exception(mocked_log_exception, mocked_open, error_message_box):
    """
    Test that parse_xml handles a FileNotFoundError exception correctly
    """
    # GIVEN: A mocked open which raises a FileNotFoundError and an instance of BibleImporter
    exception = FileNotFoundError()
    exception.filename = 'file.tst'
    exception.strerror = 'No such file or directory'
    mocked_open.side_effect = exception
    with patch('openlp.plugins.bibles.lib.bibleimport.BibleDB._setup'):
        importer = BibleImport(MagicMock(), path='.', name='.', file_path=None)

    # WHEN: Calling parse_xml
    result = importer.parse_xml(Path('file.tst'))

    # THEN: parse_xml should have caught the error, informed the user and returned None
    mocked_log_exception.assert_called_once_with('Opening file.tst failed.')
    error_message_box.assert_called_once_with(
        title='An Error Occured When Opening A File',
        message='The following error occurred when trying to open\nfile.tst:\n\nNo such file or directory')
    assert result is None


@patch.object(BibleImport, 'log_exception')
def test_parse_xml_file_permission_error_exception(mocked_log_exception, mocked_open, error_message_box):
    """
    Test that parse_xml handles a PermissionError exception correctly
    """
    # GIVEN: A mocked open which raises a PermissionError and an instance of BibleImporter
    exception = PermissionError()
    exception.filename = 'file.tst'
    exception.strerror = 'Permission denied'
    mocked_open.side_effect = exception
    with patch('openlp.plugins.bibles.lib.bibleimport.BibleDB._setup'):
        importer = BibleImport(MagicMock(), path='.', name='.', file_path=None)

    # WHEN: Calling parse_xml
    result = importer.parse_xml(Path('file.tst'))

    # THEN: parse_xml should have caught the error, informed the user and returned None
    mocked_log_exception.assert_called_once_with('Opening file.tst failed.')
    error_message_box.assert_called_once_with(
        title='An Error Occured When Opening A File',
        message='The following error occurred when trying to open\nfile.tst:\n\nPermission denied')
    assert result is None


def test_set_current_chapter(settings):
    """
    Test set_current_chapter
    """
    # GIVEN: An instance of BibleImport and a mocked wizard
    importer = BibleImport(MagicMock(), path='.', name='.', file_path=None)
    importer.wizard = MagicMock()

    # WHEN: Calling set_current_chapter
    importer.set_current_chapter('Book_Name', 'Chapter')

    # THEN: Increment_progress_bar should have been called with a text string
    importer.wizard.increment_progress_bar.assert_called_once_with('Importing Book_Name Chapter...')


@patch.object(BibleImport, 'is_compressed', return_value=True)
def test_validate_xml_file_compressed_file(mocked_is_compressed, settings):
    """
    Test that validate_xml_file raises a ValidationError when is_compressed returns True
    """
    # GIVEN: A mocked parse_xml which returns None
    importer = BibleImport(MagicMock(), path='.', name='.', file_path=None)

    # WHEN: Calling is_compressed
    # THEN: ValidationError should be raised, with the message 'Compressed file'
    with pytest.raises(ValidationError) as context:
        importer.validate_xml_file('file.name', 'xbible')
    assert context.value != ValidationError('Compressed file')
    assert importer.import_failure is not None
    assert importer.import_failure.code == 'compressed-file'


@patch.object(BibleImport, 'parse_xml', return_value=None)
@patch.object(BibleImport, 'is_compressed', return_value=False)
def test_validate_xml_file_parse_xml_fails(mocked_is_compressed, mocked_parse_xml, settings):
    """
    Test that validate_xml_file raises a ValidationError when parse_xml returns None
    """
    # GIVEN: A mocked parse_xml which returns None
    importer = BibleImport(MagicMock(), path='.', name='.', file_path=None)

    # WHEN: Calling validate_xml_file
    # THEN: ValidationError should be raised, with the message 'Error when opening file'
    #       the user that an OpenSong bible was found
    with pytest.raises(ValidationError) as context:
        importer.validate_xml_file('file.name', 'xbible')
    assert context.value != ValidationError('Error when opening file')
    assert importer.import_failure is not None
    assert importer.import_failure.code == 'xml-open-failed'


@patch.object(BibleImport, 'parse_xml', return_value=objectify.fromstring('<bible></bible>'))
@patch.object(BibleImport, 'is_compressed', return_value=False)
def test_validate_xml_file_success(mocked_is_compressed, mocked_parse_xml, settings):
    """
    Test that validate_xml_file returns True with valid XML
    """
    # GIVEN: Some test data with an OpenSong Bible "bible" root tag
    importer = BibleImport(MagicMock(), path='.', name='.', file_path=None)

    # WHEN: Calling validate_xml_file
    result = importer.validate_xml_file('file.name', 'bible')

    # THEN: True should be returned
    assert result is True


@patch.object(BibleImport, 'parse_xml', return_value=objectify.fromstring('<bible></bible>'))
@patch.object(BibleImport, 'is_compressed', return_value=False)
def test_validate_xml_file_opensong_root(mocked_is_compressed, mocked_parse_xml, error_message_box):
    """
    Test that validate_xml_file raises a ValidationError with an OpenSong root tag
    """
    # GIVEN: Some test data with an Zefania root tag and an instance of BibleImport
    importer = BibleImport(MagicMock(), path='.', name='.', file_path=None)

    # WHEN: Calling validate_xml_file
    # THEN: ValidationError should be raised, and the critical error message box should was called informing
    #       the user that an OpenSong bible was found
    with pytest.raises(ValidationError) as context:
        importer.validate_xml_file('file.name', 'xbible')
    assert context.value != ValidationError('Invalid xml.')
    error_message_box.assert_called_once_with(
        message='Incorrect Bible file type supplied. This looks like an OpenSong XML bible.')


@patch.object(BibleImport, 'parse_xml')
@patch.object(BibleImport, 'is_compressed', return_value=False)
def test_validate_xml_file_osis_root(mocked_is_compressed, mocked_parse_xml, error_message_box):
    """
    Test that validate_xml_file raises a ValidationError with an OSIS root tag
    """
    # GIVEN: Some test data with an Zefania root tag and an instance of BibleImport
    mocked_parse_xml.return_value = objectify.fromstring(
        '<osis xmlns=\'http://www.bibletechnologies.net/2003/OSIS/namespace\'></osis>')
    importer = BibleImport(MagicMock(), path='.', name='.', file_path=None)

    # WHEN: Calling validate_xml_file
    # THEN: ValidationError should be raised, and the critical error message box should was called informing
    #       the user that an OSIS bible was found
    with pytest.raises(ValidationError) as context:
        importer.validate_xml_file('file.name', 'xbible')
    assert context.value != ValidationError('Invalid xml.')
    error_message_box.assert_called_once_with(
        message='Incorrect Bible file type supplied. This looks like an OSIS XML bible.')


@patch.object(BibleImport, 'parse_xml', return_value=objectify.fromstring('<xmlbible></xmlbible>'))
@patch.object(BibleImport, 'is_compressed', return_value=False)
def test_validate_xml_file_zefania_root(mocked_is_compressed, mocked_parse_xml, error_message_box):
    """
    Test that validate_xml_file raises a ValidationError with an Zefania root tag
    """
    # GIVEN: Some test data with an Zefania root tag and an instance of BibleImport
    importer = BibleImport(MagicMock(), path='.', name='.', file_path=None)

    # WHEN: Calling validate_xml_file
    # THEN: ValidationError should be raised, and the critical error message box should was called informing
    #       the user that an Zefania bible was found
    with pytest.raises(ValidationError) as context:
        importer.validate_xml_file('file.name', 'xbible')
    assert context.value != ValidationError('Invalid xml.')
    error_message_box.assert_called_once_with(
        message='Incorrect Bible file type supplied. This looks like an Zefania XML bible.')


@patch.object(BibleImport, 'parse_xml', return_value=objectify.fromstring('<unknownbible></unknownbible>'))
@patch.object(BibleImport, 'is_compressed', return_value=False)
def test_validate_xml_file_unknown_root(mocked_is_compressed, mocked_parse_xml, error_message_box):
    """
    Test that validate_xml_file raises a ValidationError with an unknown root tag
    """
    # GIVEN: Some test data with an unknown root tag and an instance of BibleImport
    importer = BibleImport(MagicMock(), path='.', name='.', file_path=None)
    # WHEN: Calling validate_xml_file
    # THEN: ValidationError should be raised, and the critical error message box should was called informing
    #       the user that a unknown xml bible was found
    with pytest.raises(ValidationError) as context:
        importer.validate_xml_file('file.name', 'xbible')
    assert context.value != ValidationError('Invalid xml.')
    error_message_box.assert_called_once_with(
        message='Incorrect Bible file type supplied. This looks like an unknown type of XML bible.')
