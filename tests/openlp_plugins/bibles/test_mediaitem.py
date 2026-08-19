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
This module contains tests for the lib submodule of the Presentations plugin.
"""
from unittest.mock import MagicMock, call, patch

import pytest
from PySide6 import QtCore, QtWidgets

from openlp.core.common.enum import DisplayStyle, LayoutStyle, ReferencePlacement
from openlp.core.common.registry import Registry
from openlp.core.lib.mediamanageritem import MediaManagerItem
from openlp.core.lib.serviceitem import ItemCapabilities
from openlp.plugins.bibles.lib.mediaitem import VALID_TEXT_SEARCH, BibleMediaItem, BibleSearch, ResultsTab, \
    SearchStatus, SearchTabs, get_reference_separators


@pytest.fixture()
def media_item(mock_settings) -> BibleMediaItem:
    Registry().register('main_window', MagicMock())

    with patch('openlp.plugins.bibles.lib.mediaitem.MediaManagerItem._setup'), \
            patch('openlp.plugins.bibles.lib.mediaitem.BibleMediaItem.setup_item'):
        m_item = BibleMediaItem(None, MagicMock())
    media_item.plugin = MagicMock()
    m_item.results_view_tab = MagicMock()
    return m_item


mocked_book_1 = MagicMock(**{'get_name.return_value': 'Book 1', 'book_reference_id': 1})
mocked_book_2 = MagicMock(**{'get_name.return_value': 'Book 2', 'book_reference_id': 2})
mocked_book_3 = MagicMock(**{'get_name.return_value': 'Book 3', 'book_reference_id': 3})
mocked_book_4 = MagicMock(**{'get_name.return_value': 'Book 4', 'book_reference_id': 4})

book_list_1 = [mocked_book_1, mocked_book_2, mocked_book_3]
book_list_2 = [mocked_book_2, mocked_book_3, mocked_book_4]
mocked_bible_1 = MagicMock(**{'get_books.return_value': book_list_1})
mocked_bible_1.name = 'Bible 1'
mocked_bible_2 = MagicMock(**{'get_books.return_value': book_list_2})
mocked_bible_2.name = 'Bible 2'


@pytest.fixture()
def mocked_timer():
    return patch('openlp.plugins.bibles.lib.mediaitem.QtCore.QTimer').start()


@pytest.fixture()
def mocked_log():
    return patch('openlp.plugins.bibles.lib.mediaitem.log').start()


def test_valid_text_search():
    """
    Test the compiled VALID_TEXT_SEARCH regex expression
    """
    # GIVEN: Some test data and some expected results
    test_data = [('a a a', None), ('a ab a', None), ('a abc a', ((2, 5),)), ('aa 123 aa', ((3, 6),))]
    for data, expected_result in test_data:

        # WHEN: Calling search on the compiled regex expression
        result = VALID_TEXT_SEARCH.search(data)

        # THEN: The expected result should be returned
        if expected_result is None:
            assert result is None, expected_result
        else:
            assert result.regs == expected_result


def test_get_reference_separators():
    """
    Test the module function get_reference_separators
    """
    # GIVEN: A mocked get_reference_separator from the :mod:`openlp.plugins.bibles.lib` module
    with patch('openlp.plugins.bibles.lib.mediaitem.get_reference_separator') as mocked_get_reference_separator:
        # WHEN: Calling get_reference_separators
        result = get_reference_separators()

        # THEN: The result should contain the 'verse', 'range', 'list' keys and get_reference_separator should have
        #       been called with the expected values.
        assert all(key in result for key in ('verse', 'range', 'list')) is True
        mocked_get_reference_separator.assert_has_calls(
            [call('sep_v_display'), call('sep_r_display'), call('sep_l_display')])


def test_bible_search_enum():
    """
    Test that the :class:`BibleSearch` class contains the expected enumerations
    """
    # GIVEN: The BibleSearch class
    # WHEN: Testing its attributes
    # THEN: The BibleSearch class should have the following enumrations
    assert hasattr(BibleSearch, 'Combined')
    assert hasattr(BibleSearch, 'Reference')
    assert hasattr(BibleSearch, 'Text')


def test_bible_media_item_subclass():
    """
    Test that the :class:`BibleMediaItem` class is a subclass of the :class:`MediaManagerItem` class
    """
    # GIVEN: The :class:`BibleMediaItem`
    # WHEN: Checking if it is a subclass of MediaManagerItem
    # THEN: BibleMediaItem should be a subclass of MediaManagerItem
    assert issubclass(BibleMediaItem, MediaManagerItem)


def test_bible_media_item_signals():
    """
    Test that the :class:`BibleMediaItem` class has the expected signals
    """
    # GIVEN: The :class:`BibleMediaItem`
    # THEN:  The :class:`BibleMediaItem` should contain the following Signal's
    assert hasattr(BibleMediaItem, 'bibles_go_live')
    assert hasattr(BibleMediaItem, 'bibles_add_to_service')
    assert isinstance(BibleMediaItem.bibles_go_live, QtCore.Signal)
    assert isinstance(BibleMediaItem.bibles_add_to_service, QtCore.Signal)


def test_media_item_instance(media_item: BibleMediaItem):
    """
    When creating an instance of C test that it is also an instance of
    :class:`MediaManagerItem`
    """
    # GIVEN: An instance of :class:`BibleMediaItem`
    # WEHN: Checking its class
    # THEN: It should be a subclass of :class:`MediaManagerItem`
    assert isinstance(media_item, MediaManagerItem)


def test_setup_item(media_item: BibleMediaItem):
    """
    Test the setup_item method
    """
    # Could have tested the connection of the custom signals, however they're class vairables, and I could not find
    # a way to properly test them.

    # GIVEN: A mocked Registry.register_function method and an instance of BibleMediaItem
    with patch.object(Registry(), 'register_function') as mocked_register_function:
        # WHEN: Calling setup_itme
        media_item.setup_item()

        # THEN: Registry.register_function method should have been called with the reload_bibles method
        mocked_register_function.assert_called_once_with('bibles_load_list', media_item.reload_bibles)


def test_required_icons(media_item: BibleMediaItem):
    """
    Test that all the required icons are set properly.
    """
    # GIVEN: An instance of :class:`BibleMediaItem`
    # WHEN: required_icons is called
    media_item.required_icons()

    # THEN: The correct icons should be set
    assert media_item.has_import_icon is True, 'Check that the icon is as True.'
    assert media_item.has_new_icon is False, 'Check that the icon is called as False.'
    assert media_item.has_edit_icon is True, 'Check that the icon is called as True.'
    assert media_item.has_delete_icon is True, 'Check that the icon is called as True.'
    assert media_item.add_to_service_item is False, 'Check that the icon is called as False'


def test_add_middle_header_bar(media_item: BibleMediaItem):
    """Test that the add_middle_header_bar method adds the correct objects"""
    # GIVEN: An instance of the class BibleMediaItem with some mocked objects
    media_item.page_layout = MagicMock()

    # WHEN: The add_middle_header_bar method is called
    media_item.add_middle_header_bar()

    # THEN: All the items should be added to the middle of the toolbar
    assert media_item.search_tab_bar is not None
    assert media_item.search_tab is not None
    assert media_item.select_tab is not None
    assert media_item.options_tab is not None
    assert media_item.search_button_widget is not None
    assert media_item.results_view_tab is not None
    assert media_item.page_layout.addWidget.call_args_list == [
        call(media_item.search_tab_bar),
        call(media_item.search_tab),
        call(media_item.select_tab),
        call(media_item.options_tab),
        call(media_item.search_button_widget),
        call(media_item.results_view_tab)
    ]


def test_on_focus_search_tab_visible(media_item: BibleMediaItem):
    """
    Test the correct widget gets focus when the BibleMediaItem receives focus
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked out tabs and primary widgets
    media_item.search_tab = MagicMock(**{'isVisible.return_value': True})
    media_item.search_edit = MagicMock()
    media_item.select_tab = MagicMock(**{'isVisible.return_value': False})
    media_item.select_book_combo_box = MagicMock()
    media_item.options_tab = MagicMock(**{'isVisible.return_value': False})
    media_item.version_combo_box = MagicMock()

    # WHEN: Calling on_focus
    media_item.on_focus()

    # THEN: search_edit should now have focus and its text selected
    media_item.search_edit.assert_has_calls([call.setFocus(), call.selectAll()])
    media_item.select_book_combo_box.assert_not_called()
    media_item.version_combo_box.setFocus.assert_not_called()


def test_on_focus_select_tab_visible(media_item: BibleMediaItem):
    """
    Test the correct widget gets focus when the BibleMediaItem receives focus
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked out tabs and primary widgets
    media_item.search_tab = MagicMock(**{'isVisible.return_value': False})
    media_item.search_edit = MagicMock()
    media_item.select_tab = MagicMock(**{'isVisible.return_value': True})
    media_item.select_book_combo_box = MagicMock()
    media_item.options_tab = MagicMock(**{'isVisible.return_value': False})
    media_item.version_combo_box = MagicMock()

    # WHEN: Calling on_focus
    media_item.on_focus()

    # THEN: select_book_combo_box should have focus
    media_item.search_edit.setFocus.assert_not_called()
    media_item.search_edit.selectAll.assert_not_called()
    media_item.select_book_combo_box.setFocus.assert_called_once_with()
    media_item.version_combo_box.setFocus.assert_not_called()


def test_on_focus_options_tab_visible(media_item: BibleMediaItem):
    """
    Test the correct widget gets focus when the BibleMediaItem receives focus
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked out tabs and primary widgets
    media_item.search_tab = MagicMock(**{'isVisible.return_value': False})
    media_item.search_edit = MagicMock()
    media_item.select_tab = MagicMock(**{'isVisible.return_value': False})
    media_item.select_book_combo_box = MagicMock()
    media_item.options_tab = MagicMock(**{'isVisible.return_value': True})
    media_item.version_combo_box = MagicMock()

    # WHEN: Calling on_focus
    media_item.on_focus()

    # THEN: version_combo_box have received focus
    media_item.search_edit.setFocus.assert_not_called()
    media_item.search_edit.selectAll.assert_not_called()
    media_item.select_book_combo_box.setFocus.assert_not_called()
    media_item.version_combo_box.setFocus.assert_called_once_with()


def test_config_update_show_second_bible(media_item: BibleMediaItem):
    """
    Test the config update method
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked out settings class with known values
    media_item.settings.value = lambda key: {'bibles/second bibles': True, 'bibles/verse layout style': 0}[key]
    media_item.general_bible_layout = MagicMock()
    media_item.second_combo_box = MagicMock()
    media_item.style_combo_box = MagicMock()

    # WHEN: Calling config_update()
    media_item.config_update()

    # THEN: second_combo_box() should be set visible
    media_item.second_combo_box.setVisible.assert_called_once_with(True)


def test_config_update_hide_second_bible(media_item: BibleMediaItem):
    """
    Test the config update method
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked out settings class with known values
    media_item.settings.value = lambda key: {'bibles/second bibles': False, 'bibles/verse layout style': 0}[key]
    media_item.general_bible_layout = MagicMock()
    media_item.second_combo_box = MagicMock()
    media_item.style_combo_box = MagicMock()

    # WHEN: Calling config_update()
    media_item.config_update()

    # THEN: second_combo_box() should hidden
    media_item.second_combo_box.setVisible.assert_called_once_with(False)


def test_config_update_set_layout_style(media_item: BibleMediaItem):
    """
    Test the config update method
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked out settings class with known values
    media_item.settings.value = lambda key: {'bibles/second bibles': True, 'bibles/verse layout style': 1}[key]
    media_item.general_bible_layout = MagicMock()
    media_item.second_combo_box = MagicMock()
    media_item.style_combo_box = MagicMock()

    # WHEN: Calling config_update()
    media_item.config_update()

    # THEN: style_combo_box should set the currentIndex to 1
    media_item.style_combo_box.setCurrentIndex(1)


def test_initalise(media_item: BibleMediaItem):
    """
    Test the initalise method
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked out settings class with known values
    media_item.settings.value = lambda key: {'bibles/reset to combined quick search': False}[key]
    with patch.object(media_item, 'populate_bible_combo_boxes'), \
            patch.object(media_item, 'config_update'):
        media_item.search_edit = MagicMock()

        # WHEN: Calling initialise()
        media_item.initialise()

        # THEN: The search_edit search types should have been set.
        assert media_item.search_edit.set_search_types.called is True
        assert media_item.search_edit.set_current_search_type.called is False


def test_initalise_reset_search_type(media_item: BibleMediaItem):
    """
    Test the initalise method
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked out settings class with known values
    media_item.settings.value = lambda key: {'bibles/reset to combined quick search': True}[key]
    with patch.object(media_item, 'populate_bible_combo_boxes'), \
            patch.object(media_item, 'config_update'):
        media_item.search_edit = MagicMock()

        # WHEN: Calling initialise()
        media_item.initialise()

        # THEN: The search_edit search types should have been set and that the current search type should be set to
        #       'Combined'
        assert media_item.search_edit.set_search_types.called is True
        media_item.search_edit.set_current_search_type.assert_called_once_with(BibleSearch.Combined)


def test_populate_bible_combo_boxes(media_item: BibleMediaItem):
    """
    Test populate_bible_combo_boxes method
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked out settings class with known values
    bible_1 = MagicMock()
    bible_2 = MagicMock()
    bible_3 = MagicMock()
    media_item.settings.value = lambda key: {'bibles/primary bible': bible_2, 'bibles/second bible': bible_3}[key]
    media_item.version_combo_box = MagicMock()
    media_item.second_combo_box = MagicMock()
    media_item.plugin.manager.get_bibles.return_value = \
        {'Bible 2': bible_2, 'Bible 1': bible_1, 'Bible 3': bible_3}
    with patch('openlp.plugins.bibles.lib.mediaitem.get_locale_key', side_effect=lambda x: x), \
            patch('openlp.plugins.bibles.lib.mediaitem.find_and_set_in_combo_box') as mocked_set_combo_box, \
            patch.object(media_item, 'on_version_combo_box_index_changed'):
        # WHEN: Calling populate_bible_combo_boxes
        media_item.populate_bible_combo_boxes()

        # THEN: The bible combo boxes should be filled with the bible names and data, in a sorted order.
        # Also check the correct combo box has been selected according to the settings
        media_item.version_combo_box.addItem.assert_has_calls(
            [call('Bible 1', bible_1), call('Bible 2', bible_2), call('Bible 3', bible_3)])
        media_item.second_combo_box.addItem.assert_has_calls(
            [call('', None), call('Bible 1', bible_1), call('Bible 2', bible_2), call('Bible 3', bible_3)])
        mocked_set_combo_box.assert_has_calls(
            [call(media_item.version_combo_box, bible_2), call(media_item.second_combo_box, bible_3)])


def test_reload_bibles(media_item: BibleMediaItem):
    """
    Test reload_bibles
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked out settings class with known values
    with patch.object(media_item, 'populate_bible_combo_boxes') as mocked_populate_bible_combo_boxes:
        # WHEN: Calling reload_bibles()
        media_item.reload_bibles()

        # THEN: The manager reload_bibles method should have been called and the bible combo boxes updated
        media_item.plugin.manager.reload_bibles.assert_called_once_with()
        mocked_populate_bible_combo_boxes.assert_called_once_with()


def test_get_common_books_no_second_book(media_item: BibleMediaItem):
    """
    Test get_common_books when called with out a second bible
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and a mocked first bible
    # WHEN: Calling get_common_books with only one bible
    result = media_item.get_common_books(mocked_bible_1)

    # THEN: The book of the bible should be returned
    assert result == book_list_1


def test_get_common_books_second_book(media_item: BibleMediaItem):
    """
    Test get_common_books when called with a second bible
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and two mocked bibles with differing books
    # WHEN: Calling get_common_books with two bibles
    result = media_item.get_common_books(mocked_bible_1, mocked_bible_2)

    # THEN: Only the books contained in both bibles should be returned
    assert result == [mocked_book_2, mocked_book_3]


def test_initialise_advanced_bible_no_bible(media_item: BibleMediaItem):
    """
    Test initialise_advanced_bible when there is no main bible
    """
    # GIVEN: An instance of :class:`MediaManagerItem`
    media_item.select_book_combo_box = MagicMock()
    with patch.object(media_item, 'get_common_books') as mocked_get_common_books:
        # WHEN: Calling initialise_advanced_bible() when there is no main bible
        media_item.bible = None
        result = media_item.initialise_advanced_bible()

        # THEN: initialise_advanced_bible should return with put calling get_common_books
        assert result is None
        mocked_get_common_books.assert_not_called()


def test_initialise_advanced_bible_add_books_with_last_id_found(media_item: BibleMediaItem):
    """
    Test initialise_advanced_bible when the last_id argument is supplied and it is found in the list
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and a mocked_book_combo_box which simulates data being found
    #        in the list
    media_item.select_book_combo_box = MagicMock(**{'findData.return_value': 2})
    with patch.object(media_item, 'get_common_books', return_value=book_list_1), \
            patch.object(media_item, 'on_advanced_book_combo_box'):
        # WHEN: Calling initialise_advanced_bible() with the last_id argument set
        media_item.bible = MagicMock()
        media_item.initialise_advanced_bible(10)

        # THEN: The books should be added to the combo box, and the chosen book should be reselected
        media_item.select_book_combo_box.addItem.assert_has_calls(
            [call('Book 1', 1), call('Book 2', 2), call('Book 3', 3)])
        media_item.select_book_combo_box.setCurrentIndex.assert_called_once_with(2)


def test_initialise_advanced_bible_add_books_with_last_id_not_found(media_item: BibleMediaItem):
    """
    Test initialise_advanced_bible when the last_id argument is supplied and it is not found in the list
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and a mocked_book_combo_box which simulates data not being
    #          found in the list
    media_item.select_book_combo_box = MagicMock(**{'findData.return_value': -1})
    with patch.object(media_item, 'get_common_books', return_value=book_list_1), \
            patch.object(media_item, 'on_advanced_book_combo_box'):
        # WHEN: Calling initialise_advanced_bible() with the last_id argument set
        media_item.bible = MagicMock()
        media_item.initialise_advanced_bible(10)

        # THEN: The books should be added to the combo box, and the first book should be selected
        media_item.select_book_combo_box.addItem.assert_has_calls(
            [call('Book 1', 1), call('Book 2', 2), call('Book 3', 3)])
        media_item.select_book_combo_box.setCurrentIndex.assert_called_once_with(0)


def test_update_auto_completer_search_no_bible(media_item: BibleMediaItem):
    """
    Test update_auto_completer when there is no main bible selected and the search_edit type is
    'BibleSearch.Reference'
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and a mocked search_edit
    mocked_search_edit = MagicMock(**{'current_search_type.return_value': BibleSearch.Reference})
    media_item.search_edit = mocked_search_edit
    media_item.bible = None
    with patch.object(media_item, 'get_common_books') as mocked_get_common_books, \
            patch('openlp.plugins.bibles.lib.mediaitem.set_case_insensitive_completer') \
            as mocked_set_case_insensitive_completer:
        # WHEN: Calling update_auto_completer
        media_item.update_auto_completer()

        # THEN: get_common_books should not have been called. set_case_insensitive_completer should have been called
        #       with an empty list
        mocked_get_common_books.assert_not_called()
        mocked_set_case_insensitive_completer.assert_called_once_with([], mocked_search_edit)


def test_update_auto_completer_search_reference_type(media_item: BibleMediaItem):
    """
    Test update_auto_completer when a main bible is selected and the search_edit type is 'BibleSearch.Reference'
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and a mocked search_edit
    mocked_search_edit = MagicMock(**{'current_search_type.return_value': BibleSearch.Reference})
    media_item.search_edit = mocked_search_edit
    media_item.bible = MagicMock()
    with patch.object(media_item, 'get_common_books', return_value=book_list_1), \
            patch('openlp.plugins.bibles.lib.mediaitem.get_locale_key', side_effect=lambda x: x), \
            patch('openlp.plugins.bibles.lib.mediaitem.set_case_insensitive_completer') \
            as mocked_set_case_insensitive_completer:
        # WHEN: Calling update_auto_completer
        media_item.update_auto_completer()

        # THEN: set_case_insensitive_completer should have been called with the names of the books + space in order
        mocked_set_case_insensitive_completer.assert_called_once_with(
            ['Book 1 ', 'Book 2 ', 'Book 3 '], mocked_search_edit)


def test_update_auto_completer_search_combined_type(media_item: BibleMediaItem):
    """
    Test update_auto_completer when a main bible is selected and the search_edit type is 'BibleSearch.Combined'
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and a mocked search_edit
    mocked_search_edit = MagicMock(**{'current_search_type.return_value': BibleSearch.Combined})
    media_item.search_edit = mocked_search_edit
    media_item.bible = MagicMock()
    with patch.object(media_item, 'get_common_books', return_value=book_list_1), \
            patch('openlp.plugins.bibles.lib.mediaitem.get_locale_key', side_effect=lambda x: x), \
            patch('openlp.plugins.bibles.lib.mediaitem.set_case_insensitive_completer') \
            as mocked_set_case_insensitive_completer:
        # WHEN: Calling update_auto_completer
        media_item.update_auto_completer()

        # THEN: set_case_insensitive_completer should have been called with the names of the books + space in order
        mocked_set_case_insensitive_completer.assert_called_once_with(
            ['Book 1 ', 'Book 2 ', 'Book 3 '], mocked_search_edit)


def test_on_import_click_no_import_wizard_attr(media_item: BibleMediaItem):
    """
    Test on_import_click when media_item does not have the `import_wizard` attribute. And the wizard was canceled.
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and a mocked BibleImportForm
    mocked_bible_import_form_instance = MagicMock(**{'exec.return_value': False})
    with patch('openlp.plugins.bibles.lib.mediaitem.BibleImportForm',
               return_value=mocked_bible_import_form_instance) as mocked_bible_import_form, \
            patch.object(media_item, 'reload_bibles') as mocked_reload_bibles:
        # WHEN: Calling on_import_click
        media_item.on_import_click()

        # THEN: BibleImport wizard should have been instianed and reload_bibles should not have been called
        assert mocked_bible_import_form.called is True
        assert mocked_reload_bibles.called is False


def test_on_import_click_wizard_not_canceled(media_item: BibleMediaItem):
    """
    Test on_import_click when the media item has the import_wizard attr set and wizard completes sucessfully.
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and a mocked import_wizard
    mocked_import_wizard = MagicMock(**{'exec.return_value': True})
    media_item.import_wizard = mocked_import_wizard

    with patch.object(media_item, 'reload_bibles') as mocked_reload_bibles:
        # WHEN: Calling on_import_click
        media_item.on_import_click()

        # THEN: BibleImport wizard should have been instianted and reload_bibles should not have been called
        assert mocked_import_wizard.called is False
        assert mocked_reload_bibles.called is True


def test_on_edit_click_no_bible(media_item: BibleMediaItem):
    """
    Test on_edit_click when there is no main bible selected
    """
    # GIVEN: An instance of :class:`MediaManagerItem`
    with patch('openlp.plugins.bibles.lib.mediaitem.EditBibleForm') as mocked_edit_bible_form:
        # WHEN: A main bible is not selected and on_edit_click is called
        media_item.bible = None
        media_item.on_edit_click()

        # THEN: EditBibleForm should not have been instianted
        assert mocked_edit_bible_form.called is False


def test_on_edit_click_user_cancel_edit_form(media_item: BibleMediaItem):
    """
    Test on_edit_click when the user cancels the EditBibleForm
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and a mocked EditBibleForm which returns False when exec is
    #        called
    media_item.bible = MagicMock()
    mocked_edit_bible_form_instance = MagicMock(**{'exec.return_value': False})
    with patch('openlp.plugins.bibles.lib.mediaitem.EditBibleForm', return_value=mocked_edit_bible_form_instance) \
            as mocked_edit_bible_form, \
            patch.object(media_item, 'reload_bibles') as mocked_reload_bibles:
        # WHEN: on_edit_click is called, and the user cancels the EditBibleForm
        media_item.on_edit_click()

        # THEN: EditBibleForm should have been been instianted but reload_bibles should not have been called
        assert mocked_edit_bible_form.called is True
        assert mocked_reload_bibles.called is False


def test_on_edit_click_user_accepts_edit_form(media_item: BibleMediaItem):
    """
    Test on_edit_click when the user accepts the EditBibleForm
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and a mocked EditBibleForm which returns True when exec is
    #        called
    media_item.bible = MagicMock()
    mocked_edit_bible_form_instance = MagicMock(**{'exec.return_value': True})
    with patch('openlp.plugins.bibles.lib.mediaitem.EditBibleForm',
               return_value=mocked_edit_bible_form_instance) \
            as mocked_edit_bible_form, \
            patch.object(media_item, 'reload_bibles') as mocked_reload_bibles:
        # WHEN: on_edit_click is called, and the user accpets the EditBibleForm
        media_item.on_edit_click()

        # THEN: EditBibleForm should have been been instianted and reload_bibles should have been called
        assert mocked_edit_bible_form.called is True
        assert mocked_reload_bibles.called is True


def test_on_delete_click_no_bible(media_item: BibleMediaItem):
    """
    Test on_delete_click when there is no main bible selected
    """
    # GIVEN: An instance of :class:`MediaManagerItem`
    with patch('openlp.plugins.bibles.lib.mediaitem.QtWidgets.QMessageBox') as mocked_qmessage_box:
        # WHEN: A main bible is not selected and on_delete_click is called
        media_item.bible = None
        media_item.on_delete_click()

        # THEN: QMessageBox.question should not have been called
        assert mocked_qmessage_box.question.called is False


def test_on_delete_click_response_no(media_item: BibleMediaItem):
    """
    Test on_delete_click when the user selects no from the message box
    """
    # GIVEN: An instance of :class:`MediaManagerItem`
    # and a QMessageBox which reutrns QtWidgets.QMessageBox.StandardButton.No
    media_item.bible = MagicMock()
    with patch('openlp.plugins.bibles.lib.mediaitem.QtWidgets.QMessageBox.question',
               return_value=QtWidgets.QMessageBox.StandardButton.No) as mocked_qmessage_box:
        # WHEN: on_delete_click is called
        media_item.on_delete_click()

        # THEN: QMessageBox.question should have been called, but the delete_bible should not have been called
        assert mocked_qmessage_box.called is True
        assert media_item.plugin.manager.delete_bible.called is False


def test_on_delete_click_response_yes(media_item: BibleMediaItem):
    """
    Test on_delete_click when the user selects yes from the message box
    """
    # GIVEN: An instance of :class:`MediaManagerItem`
    # and a QMessageBox which reutrns QtWidgets.QMessageBox.StandardButton.Yes
    media_item.bible = MagicMock()
    with patch('openlp.plugins.bibles.lib.mediaitem.QtWidgets.QMessageBox.question',
               return_value=QtWidgets.QMessageBox.StandardButton.Yes) as mocked_qmessage_box, \
            patch.object(media_item, 'reload_bibles'):
        # WHEN: on_delete_click is called
        media_item.on_delete_click()

        # THEN: QMessageBox.question should and delete_bible should not have been called
        assert mocked_qmessage_box.called is True
        assert media_item.plugin.manager.delete_bible.called is True


@pytest.mark.parametrize('index, btn_enabled, search_visible, select_visible, options_visible',
                         [(SearchTabs.Search, True, True, False, False),
                          (SearchTabs.Select, True, False, True, False),
                          (SearchTabs.Options, False, False, False, True)])
def test_on_search_tab_bar_current_changed(media_item: BibleMediaItem, index: int, btn_enabled: bool,
                                           search_visible: bool, select_visible: bool, options_visible: bool):
    """
    Test on_search_tab_bar_current_changed when each tab is selected
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked out search_tab and select_tab
    media_item.search_tab = MagicMock()
    media_item.select_tab = MagicMock()
    media_item.options_tab = MagicMock()
    media_item.search_button = MagicMock()
    media_item.on_focus = MagicMock()

    # WHEN: The search_tab has been selected
    media_item.on_search_tab_bar_current_changed(index)

    # THEN: The search_button should be enabled, search_tab should be setVisible and select_tab should be hidden
    media_item.search_button.setEnabled.assert_called_once_with(btn_enabled)
    media_item.search_tab.setVisible.assert_called_once_with(search_visible)
    media_item.select_tab.setVisible.assert_called_once_with(select_visible)
    media_item.options_tab.setVisible.assert_called_once_with(options_visible)
    media_item.on_focus.assert_called_once_with()


@pytest.mark.parametrize('index, widget_name', [(ResultsTab.Saved, 'saved_results'),
                                                (ResultsTab.Search, 'current_results')])
def test_on_results_view_tab_current_changed_saved(media_item: BibleMediaItem, index: int, widget_name: str):
    """Test that the 'on_results_view_tab_current_changed' method updates the correct list widget"""
    # GIVEN: A BibleMediaItem with a list widget
    list_widget = getattr(media_item, widget_name)
    media_item.add_built_results_to_list_widget = MagicMock()

    # WHEN: The list is updated
    media_item.on_results_view_tab_current_changed(index)

    # THEN: The correct list should have been populated
    media_item.add_built_results_to_list_widget.assert_called_once_with(list_widget)


def test_on_book_order_button_toggled_checked(media_item: BibleMediaItem):
    """
    Test that 'on_book_order_button_toggled' changes the order of the book list
    """
    media_item.select_book_combo_box = MagicMock()

    # WHEN: When the book_order_button is checked
    media_item.on_book_order_button_toggled(True)

    # THEN: The select_book_combo_box model should have been sorted
    media_item.select_book_combo_box.model().sort.assert_called_once_with(0)


def test_on_book_order_button_toggled_un_checked(media_item: BibleMediaItem):
    """
    Test that 'on_book_order_button_toggled' changes the order of the book list
    """
    media_item.select_book_combo_box = MagicMock()

    # WHEN: When the book_order_button is un-checked
    media_item.on_book_order_button_toggled(False)

    # THEN: The select_book_combo_box model sort should have been reset
    media_item.select_book_combo_box.model().sort.assert_called_once_with(-1)


def test_on_clear_button_clicked(media_item: BibleMediaItem):
    """
    Test on_clear_button_clicked when the search tab is selected
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked out search_tab and select_tab and a mocked out
    #        list_view and search_edit
    media_item.list_view = MagicMock(**{'selectedItems.return_value': ['Some', 'Results']})
    media_item.results_view_tab = MagicMock(**{'currentIndex.return_value': ResultsTab.Search})
    with patch.object(media_item, 'on_results_view_tab_total_update'):
        # WHEN: Calling on_clear_button_clicked
        media_item.on_clear_button_clicked()

        # THEN: The list_view and the search_edit should be cleared
        assert media_item.current_results == []
        assert media_item.list_view.takeItem.call_count == 2
        media_item.list_view.row.assert_has_calls([call('Some'), call('Results')])


def test_on_save_results_button_clicked(media_item: BibleMediaItem):
    """
    Test that "on_save_results_button_clicked" saves the results.
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and a mocked list_view
    result_1 = MagicMock(**{'data.return_value': 'R1'})
    result_2 = MagicMock(**{'data.return_value': 'R2'})
    result_3 = MagicMock(**{'data.return_value': 'R3'})
    media_item.list_view = MagicMock(**{'selectedItems.return_value': [result_1, result_2, result_3]})

    with patch.object(media_item, 'on_results_view_tab_total_update') as \
            mocked_on_results_view_tab_total_update:
        # WHEN: When the save_results_button is clicked
        media_item.on_save_results_button_clicked()

        # THEN: The selected results in the list_view should be added to the 'saved_results' list. And the saved_tab
        #       total should be updated.
        assert media_item.saved_results == ['R1', 'R2', 'R3']
        mocked_on_results_view_tab_total_update.assert_called_once_with(ResultsTab.Saved)


def test_on_style_combo_box_changed(media_item: BibleMediaItem):
    """
    Test on_style_combo_box_index_changed
    """
    # GIVEN: An instance of :class:`MediaManagerItem` a mocked media_item.settings
    media_item.settings_tab = MagicMock()

    # WHEN: Calling on_style_combo_box_index_changed
    media_item.on_style_combo_box_index_changed(2)

    # THEN: The layout_style setting should have been set
    assert media_item.settings_tab.layout_style == 2


def test_on_version_combo_box_index_changed_no_bible(media_item: BibleMediaItem):
    """
    Test on_version_combo_box_index_changed when there is no main bible.
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked media_item.settings and select_book_combo_box
    media_item.version_combo_box = MagicMock(**{'currentData.return_value': None})
    media_item.select_book_combo_box = MagicMock()
    with patch.object(media_item, 'initialise_advanced_bible'):
        # WHEN: Calling on_version_combo_box_index_changed
        media_item.on_version_combo_box_index_changed()

        # THEN: The version should be saved to settings and the 'select tab' should be initialised
        assert media_item.initialise_advanced_bible.called is True


def test_on_version_combo_box_index_changed_bible_selected(media_item: BibleMediaItem):
    """
    Test on_version_combo_box_index_changed when a bible has been selected.
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked media_item.settings and select_book_combo_box
    mocked_bible_db = MagicMock()
    mocked_bible_db.name = 'ABC'
    media_item.version_combo_box = MagicMock(**{'currentData.return_value': mocked_bible_db})
    media_item.select_book_combo_box = MagicMock()
    with patch.object(media_item, 'initialise_advanced_bible'):
        # WHEN: Calling on_version_combo_box_index_changed
        media_item.on_version_combo_box_index_changed()

        # THEN: The version should be saved to settings and the 'select tab' should be initialised
        assert media_item.initialise_advanced_bible.called is True


def test_on_second_combo_box_index_changed_mode_not_changed(media_item: BibleMediaItem):
    """
    Test on_second_combo_box_index_changed when the user does not change from dual mode
    results and the user chooses no to the message box
    """
    # GIVEN: An instance of :class:`MediaManagerItem`
    media_item.list_view = MagicMock(**{'count.return_value': 5})
    media_item.style_combo_box = MagicMock()
    media_item.select_book_combo_box = MagicMock()
    with patch.object(media_item, 'initialise_advanced_bible'), \
            patch('openlp.plugins.bibles.lib.mediaitem.critical_error_message_box') \
            as mocked_critical_error_message_box:
        # WHEN: The previously selected bible is one bible and the new selection is another bible
        media_item.second_bible = mocked_bible_1
        media_item.second_combo_box = MagicMock(**{'currentData.return_value': mocked_bible_2})
        media_item.on_second_combo_box_index_changed(5)

        # THEN: The new bible should now be the current bible
        assert mocked_critical_error_message_box.called is False
        media_item.style_combo_box.setEnabled.assert_called_once_with(False)
        assert media_item.second_bible == mocked_bible_2
        media_item.settings.setValue.assert_called_once_with('bibles/second bible', 'Bible 2')


def test_on_second_combo_box_index_changed_single_to_dual_user_abort(media_item: BibleMediaItem):
    """
    Test on_second_combo_box_index_changed when the user changes from single to dual bible mode, there are search
    results and the user chooses no to the message box
    """
    # GIVEN: An instance of :class:`MediaManagerItem`
    media_item.list_view = MagicMock(**{'count.return_value': 5})
    media_item.style_combo_box = MagicMock()
    media_item.select_book_combo_box = MagicMock()
    with patch.object(media_item, 'initialise_advanced_bible'), \
            patch('openlp.plugins.bibles.lib.mediaitem.critical_error_message_box',
                  return_value=QtWidgets.QMessageBox.StandardButton.No) as mocked_critical_error_message_box:
        # WHEN: The previously selected bible is None and the new selection is a bible and the user selects yes
        #       to the dialog box
        media_item.second_bible = None
        media_item.second_combo_box = MagicMock(**{'currentData.return_value': mocked_bible_1})
        media_item.saved_results = ['saved_results']
        media_item.on_second_combo_box_index_changed(5)

        # THEN: The list_view should be cleared and the currently selected bible should not be changed
        assert mocked_critical_error_message_box.called is True
        assert media_item.second_combo_box.setCurrentIndex.called is True
        assert media_item.style_combo_box.setEnabled.called is False
        assert media_item.second_bible is None
        media_item.settings.setValue.assert_not_called()


def test_on_second_combo_box_index_changed_single_to_dual(media_item: BibleMediaItem):
    """
    Test on_second_combo_box_index_changed when the user changes from single to dual bible mode, there are search
    results and the user chooses yes to the message box
    """
    # GIVEN: An instance of :class:`MediaManagerItem`
    media_item.list_view = MagicMock(**{'count.return_value': 5})
    media_item.style_combo_box = MagicMock()
    media_item.select_book_combo_box = MagicMock()
    media_item.search_results = ['list', 'of', 'results']
    with patch.object(media_item, 'initialise_advanced_bible') as mocked_initialise_advanced_bible, \
            patch.object(media_item, 'display_results'), \
            patch('openlp.plugins.bibles.lib.mediaitem.critical_error_message_box',
                  return_value=QtWidgets.QMessageBox.StandardButton.Yes) as mocked_critical_error_message_box:
        # WHEN: The previously selected bible is None and the new selection is a bible and the user selects yes
        #       to the dialog box
        media_item.second_bible = None
        media_item.second_combo_box = MagicMock(**{'currentData.return_value': mocked_bible_1})
        media_item.saved_results = ['saved_results']
        media_item.on_second_combo_box_index_changed(5)

        # THEN: The selected bible should be set as the current bible
        assert mocked_critical_error_message_box.called is True
        media_item.style_combo_box.setEnabled.assert_called_once_with(False)
        assert mocked_initialise_advanced_bible.called is True
        assert media_item.second_bible == mocked_bible_1
        media_item.settings.setValue.assert_called_once_with('bibles/second bible', 'Bible 1')


def test_on_second_combo_box_index_changed_dual_to_single(media_item: BibleMediaItem):
    """
    Test on_second_combo_box_index_changed when the user changes from dual to single bible mode, there are search
    results and the user chooses yes to the message box
    """
    # GIVEN: An instance of :class:`MediaManagerItem`
    media_item.list_view = MagicMock(**{'count.return_value': 5})
    media_item.style_combo_box = MagicMock()
    media_item.select_book_combo_box = MagicMock()
    media_item.search_results = ['list', 'of', 'results']
    with patch.object(media_item, 'initialise_advanced_bible') as mocked_initialise_advanced_bible, \
            patch.object(media_item, 'display_results'), \
            patch('openlp.plugins.bibles.lib.mediaitem.critical_error_message_box',
                  return_value=QtWidgets.QMessageBox.StandardButton.Yes) as mocked_critical_error_message_box:
        # WHEN: The previously is a bible new selection is None and the user selects yes
        #       to the dialog box
        media_item.second_bible = mocked_bible_1
        media_item.second_combo_box = MagicMock(**{'currentData.return_value': None})
        media_item.saved_results = ['saved_results']
        media_item.on_second_combo_box_index_changed(0)

        # THEN: The selected bible should be set as the current bible
        assert mocked_critical_error_message_box.called is True
        media_item.style_combo_box.setEnabled.assert_called_once_with(True)
        assert mocked_initialise_advanced_bible.called is False
        assert media_item.second_bible is None
        media_item.settings.setValue.assert_called_once_with('bibles/second bible', None)


def test_on_advanced_book_combo_box(media_item: BibleMediaItem):
    """
    Test on_advanced_book_combo_box when the book returns 0 for the verse count.
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and a mocked get_verse_count_by_book_ref_id which returns 0
    media_item.select_book_combo_box = MagicMock(**{'currentData.return_value': 2})
    media_item.bible = mocked_bible_1
    media_item.plugin.manager.get_verse_count_by_book_ref_id.return_value = 0
    media_item.search_button = MagicMock()
    with patch('openlp.plugins.bibles.lib.mediaitem.critical_error_message_box') \
            as mocked_critical_error_message_box:
        # WHEN: Calling on_advanced_book_combo_box
        media_item.on_advanced_book_combo_box()

        # THEN: The user should be informed  that the bible cannot be used and the search button should be disabled
        media_item.plugin.manager.get_book_by_id.assert_called_once_with('Bible 1', 2)
        media_item.search_button.setEnabled.assert_called_once_with(False)
        assert mocked_critical_error_message_box.called is True


def test_on_advanced_book_combo_box_no_selection(media_item: BibleMediaItem):
    """
    Test on_advanced_book_combo_box when there is nothing selected
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and a mocked manager
    media_item.select_book_combo_box = MagicMock(**{'currentData.return_value': None})

    # WHEN: Calling on_advanced_book_combo_box
    media_item.on_advanced_book_combo_box()

    # THEN: The method should exit early, and no query made
    assert media_item.plugin.manager.get_book_by_id.call_count == 0


def test_on_advanced_book_combo_box_set_up_comboboxes(media_item: BibleMediaItem):
    """
    Test on_advanced_book_combo_box when the book returns 6 for the verse count.
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and a mocked get_verse_count_by_book_ref_id which returns 6
    media_item.from_chapter = 0
    media_item.to_chapter = 0
    media_item.from_verse = 0
    media_item.to_verse = 0
    media_item.select_book_combo_box = MagicMock(**{'currentData.return_value': 2})
    media_item.bible = mocked_bible_1
    media_item.plugin.manager.get_verse_count_by_book_ref_id.return_value = 6
    media_item.select_tab = MagicMock(**{'isVisible.return_value': True})
    media_item.search_button = MagicMock()
    with patch.object(media_item, 'adjust_combo_box') as mocked_adjust_combo_box:
        # WHEN: Calling on_advanced_book_combo_box
        media_item.on_advanced_book_combo_box()

        # THEN: The verse selection combobox's should be set up
        media_item.plugin.manager.get_book_by_id.assert_called_once_with('Bible 1', 2)
        media_item.search_button.setEnabled.assert_called_once_with(True)
        assert mocked_adjust_combo_box.call_count == 4


def test_on_from_chapter_activated_invalid_to_chapter(media_item: BibleMediaItem):
    """
    Test on_from_chapter_activated when the to_chapter is less than the from_chapter
    """
    # GIVEN: An instance of :class:`MediaManagerItem`, some mocked comboboxes with test data
    media_item.chapter_count = 25
    media_item.bible = mocked_bible_1
    media_item.select_book_combo_box = MagicMock()
    media_item.from_chapter = MagicMock(**{'currentData.return_value': 10})
    media_item.to_chapter = MagicMock(**{'currentData.return_value': 5})
    media_item.from_verse = MagicMock()
    media_item.to_verse = MagicMock()
    media_item.plugin.manager.get_verse_count_by_book_ref_id.return_value = 20
    with patch.object(media_item, 'adjust_combo_box') as mocked_adjust_combo_box:
        # WHEN: Calling on_from_chapter_activated
        media_item.on_from_chapter_activated()

        # THEN: The to_verse and to_chapter comboboxes should be updated appropriately
        assert mocked_adjust_combo_box.call_args_list == [
            call(1, 20, media_item.from_verse), call(1, 20, media_item.to_verse, False),
            call(10, 25, media_item.to_chapter, False)]


def test_on_from_chapter_activated_same_chapter(media_item: BibleMediaItem):
    """
    Test on_from_chapter_activated when the to_chapter is the same as from_chapter
    """
    # GIVEN: An instance of :class:`MediaManagerItem`, some mocked comboboxes with test data
    media_item.chapter_count = 25
    media_item.bible = mocked_bible_1
    media_item.select_book_combo_box = MagicMock()
    media_item.from_chapter = MagicMock(**{'currentData.return_value': 5})
    media_item.to_chapter = MagicMock(**{'currentData.return_value': 5})
    media_item.from_verse = MagicMock()
    media_item.to_verse = MagicMock()
    media_item.plugin.manager.get_verse_count_by_book_ref_id.return_value = 20
    with patch.object(media_item, 'adjust_combo_box') as mocked_adjust_combo_box:
        # WHEN: Calling on_from_chapter_activated
        media_item.on_from_chapter_activated()

        # THEN: The to_verse and to_chapter comboboxes should be updated appropriately
        assert mocked_adjust_combo_box.call_args_list == [
            call(1, 20, media_item.from_verse), call(1, 20, media_item.to_verse, True),
            call(5, 25, media_item.to_chapter, False)]


def test_on_from_chapter_activated_lower_chapter(media_item: BibleMediaItem):
    """
    Test on_from_chapter_activated when the to_chapter is greater than the from_chapter
    """
    # GIVEN: An instance of :class:`MediaManagerItem`, some mocked comboboxes with test data
    media_item.chapter_count = 25
    media_item.bible = mocked_bible_1
    media_item.select_book_combo_box = MagicMock()
    media_item.from_chapter = MagicMock(**{'currentData.return_value': 5})
    media_item.to_chapter = MagicMock(**{'currentData.return_value': 7})
    media_item.from_verse = MagicMock()
    media_item.to_verse = MagicMock()
    media_item.plugin.manager.get_verse_count_by_book_ref_id.return_value = 20
    with patch.object(media_item, 'adjust_combo_box') as mocked_adjust_combo_box:
        # WHEN: Calling on_from_chapter_activated
        media_item.on_from_chapter_activated()

        # THEN: The to_verse and to_chapter comboboxes should be updated appropriately
        assert mocked_adjust_combo_box.call_args_list == [
            call(1, 20, media_item.from_verse), call(5, 25, media_item.to_chapter, True)]


def test_on_from_verse(media_item: BibleMediaItem):
    """
    Test on_from_verse when the to_chapter is not equal to the from_chapter
    """
    # GIVEN: An instance of :class:`MediaManagerItem`, some mocked comboboxes with test data
    media_item.select_book_combo_box = MagicMock()
    media_item.from_chapter = MagicMock(**{'currentData.return_value': 2})
    media_item.to_chapter = MagicMock(**{'currentData.return_value': 5})

    # WHEN: Calling on_from_verse
    media_item.on_from_verse()

    # THEN: select_book_combo_box.currentData should nto be called
    assert media_item.select_book_combo_box.currentData.called is False


def test_on_from_verse_equal(media_item: BibleMediaItem):
    """
    Test on_from_verse when the to_chapter is equal to the from_chapter
    """
    # GIVEN: An instance of :class:`MediaManagerItem`, some mocked comboboxes with test data
    media_item.bible = mocked_bible_1
    media_item.select_book_combo_box = MagicMock()
    media_item.from_chapter = MagicMock(**{'currentData.return_value': 5})
    media_item.to_chapter = MagicMock(**{'currentData.return_value': 5})
    media_item.from_verse = MagicMock(**{'currentData.return_value': 7})
    media_item.to_verse = MagicMock()
    media_item.plugin.manager.get_verse_count_by_book_ref_id.return_value = 20
    with patch.object(media_item, 'adjust_combo_box') as mocked_adjust_combo_box:
        # WHEN: Calling on_from_verse
        media_item.on_from_verse()

        # THEN: The to_verse should have been updated
        mocked_adjust_combo_box.assert_called_once_with(7, 20, media_item.to_verse, True)


def test_on_to_chapter_same_chapter_from_greater_than(media_item: BibleMediaItem):
    """
    Test on_to_chapter when the to_chapter is equal to the from_chapter and the from_verse is greater than the
    to_verse
    """
    # GIVEN: An instance of :class:`MediaManagerItem`, some mocked comboboxes with test data
    media_item.bible = mocked_bible_1
    media_item.select_book_combo_box = MagicMock()
    media_item.from_chapter = MagicMock(**{'currentData.return_value': 5})
    media_item.to_chapter = MagicMock(**{'currentData.return_value': 5})
    media_item.from_verse = MagicMock(**{'currentData.return_value': 10})
    media_item.to_verse = MagicMock(**{'currentData.return_value': 7})
    media_item.plugin.manager.get_verse_count_by_book_ref_id.return_value = 20
    with patch.object(media_item, 'adjust_combo_box') as mocked_adjust_combo_box:
        # WHEN: Calling on_tp_chapter
        media_item.on_to_chapter()

        # THEN: The to_verse should have been updated
        mocked_adjust_combo_box.assert_called_once_with(10, 20, media_item.to_verse)


def test_on_from_verse_chapters_not_equal(media_item: BibleMediaItem):
    """
    Test on_from_verse when the to_chapter is not equal to the from_chapter
    """
    # GIVEN: An instance of :class:`MediaManagerItem`, some mocked comboboxes with test data
    media_item.bible = mocked_bible_1
    media_item.select_book_combo_box = MagicMock()
    media_item.from_chapter = MagicMock(**{'currentData.return_value': 7})
    media_item.to_chapter = MagicMock(**{'currentData.return_value': 5})
    media_item.from_verse = MagicMock(**{'currentData.return_value': 10})
    media_item.to_verse = MagicMock(**{'currentData.return_value': 7})
    media_item.plugin.manager.get_verse_count_by_book_ref_id.return_value = 20
    with patch.object(media_item, 'adjust_combo_box') as mocked_adjust_combo_box:
        # WHEN: Calling on_from_chapter_activated
        media_item.on_to_chapter()

        # THEN: The to_verse should have been updated
        mocked_adjust_combo_box.assert_called_once_with(1, 20, media_item.to_verse)


def test_on_from_verse_from_verse_less_than(media_item: BibleMediaItem):
    """
    Test on_from_verse when the to_chapter is equal to the from_chapter and from_verse is less than to_verse
    """
    # GIVEN: An instance of :class:`MediaManagerItem`, some mocked comboboxes with test data
    media_item.bible = mocked_bible_1
    media_item.select_book_combo_box = MagicMock()
    media_item.from_chapter = MagicMock(**{'currentData.return_value': 5})
    media_item.to_chapter = MagicMock(**{'currentData.return_value': 5})
    media_item.from_verse = MagicMock(**{'currentData.return_value': 6})
    media_item.to_verse = MagicMock(**{'currentData.return_value': 7})
    media_item.plugin.manager.get_verse_count_by_book_ref_id.return_value = 20
    with patch.object(media_item, 'adjust_combo_box') as mocked_adjust_combo_box:
        # WHEN: Calling on_from_chapter_activated
        media_item.on_to_chapter()

        # THEN: The to_verse should have been updated
        mocked_adjust_combo_box.assert_called_once_with(1, 20, media_item.to_verse)


def test_adjust_combo_box_no_restore(media_item: BibleMediaItem):
    """
    Test adjust_combo_box  when being used with out the restore function
    """
    # GIVEN: An instance of :class:`MediaManagerItem`
    mocked_combo_box = MagicMock()

    # WHEN: Calling adjust_combo_box with out setting the kwarg `restore`
    media_item.adjust_combo_box(10, 13, mocked_combo_box)

    # THEN: The combo_box should be cleared, and new items added
    mocked_combo_box.clear.assert_called_once_with()
    assert mocked_combo_box.addItem.call_args_list == \
           [call('10', 10), call('11', 11), call('12', 12), call('13', 13)]


def test_adjust_combo_box_restore_found(media_item: BibleMediaItem):
    """
    Test adjust_combo_box  when being used with out the restore function
    """
    # GIVEN: An instance of :class:`MediaManagerItem`, with the 2nd item '12' selected
    mocked_combo_box = MagicMock(**{'currentData.return_value': 12, 'findData.return_value': 2})

    # WHEN: Calling adjust_combo_box with the kwarg `restore` set to True
    media_item.adjust_combo_box(10, 13, mocked_combo_box, True)

    # THEN: The combo_box should be cleared, and new items added. Finally the previously selected item should be
    #       reselected
    mocked_combo_box.clear.assert_called_once_with()
    assert mocked_combo_box.addItem.call_args_list == \
           [call('10', 10), call('11', 11), call('12', 12), call('13', 13)]
    mocked_combo_box.setCurrentIndex.assert_called_once_with(2)


def test_adjust_combo_box_restore_not_found(media_item: BibleMediaItem):
    """
    Test adjust_combo_box  when being used with out the restore function when the selected item is not available
    after the combobox has been updated
    """
    # GIVEN: An instance of :class:`MediaManagerItem`, with the 2nd item '12' selected
    mocked_combo_box = MagicMock(**{'currentData.return_value': 9, 'findData.return_value': -1})

    # WHEN: Calling adjust_combo_box with the kwarg `restore` set to True
    media_item.adjust_combo_box(10, 13, mocked_combo_box, True)

    # THEN: The combo_box should be cleared, and new items added. Finally the first item should be selected
    mocked_combo_box.clear.assert_called_once_with()
    assert mocked_combo_box.addItem.call_args_list == \
           [call('10', 10), call('11', 11), call('12', 12), call('13', 13)]
    mocked_combo_box.setCurrentIndex.assert_called_once_with(0)


def test_on_search_button_no_bible(media_item: BibleMediaItem):
    """
    Test on_search_button_clicked when there is no bible selected
    """
    # GIVEN: An instance of :class:`MediaManagerItem`
    # WHEN calling on_search_button_clicked and there is no selected bible
    media_item.bible = None
    media_item.on_search_button_clicked()

    # THEN: The user should be informed that there are no bibles selected
    assert Registry().get('main_window').information_message.call_count == 1


def test_on_search_button_search_tab(media_item: BibleMediaItem):
    """
    Test on_search_button_clicked when the `Search` tab is selected
    """
    # GIVEN: An instance of :class:`MediaManagerItem`, and a mocked text_search method
    media_item.bible = mocked_bible_1
    media_item.search_button = MagicMock()
    media_item.search_tab = MagicMock(**{'isVisible.return_value': True})
    with patch.object(media_item, 'text_search') as mocked_text_search:
        # WHEN: Calling on_search_button_clicked and the 'Search' tab is selected
        media_item.on_search_button_clicked()

        # THEN: The text_search method should have been called
        mocked_text_search.assert_called_once_with()


def test_on_search_button_select_tab(media_item: BibleMediaItem):
    """
    Test on_search_button_clicked when the `Select` tab is selected
    """
    # GIVEN: An instance of :class:`MediaManagerItem`, and a mocked select_search method
    media_item.bible = mocked_bible_1
    media_item.search_button = MagicMock()
    media_item.search_tab = MagicMock(**{'isVisible.return_value': False})
    media_item.select_tab = MagicMock(**{'isVisible.return_value': True})
    with patch.object(media_item, 'select_search') as mocked_select_search:
        # WHEN: Calling on_search_button_clicked and the 'Select' tab is selected
        media_item.on_search_button_clicked()

        # THEN: The text_search method should have been called
        mocked_select_search.assert_called_once_with()


def test_select_search_single_bible(media_item: BibleMediaItem):
    """
    Test select_search when only one bible is selected
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked plugin.manager.get_verses
    media_item.select_book_combo_box = MagicMock()
    media_item.from_chapter = MagicMock()
    media_item.from_verse = MagicMock()
    media_item.to_chapter = MagicMock()
    media_item.to_verse = MagicMock()
    with patch.object(media_item, 'display_results') as mocked_display_results:
        # WHEN: Calling select_search and there is only one bible selected
        media_item.bible = mocked_bible_1
        media_item.second_bible = None
        media_item.select_search()

        # THEN: reference_search should only be called once
        assert media_item.plugin.manager.get_verses.call_count == 1
        mocked_display_results.assert_called_once_with()


def test_select_search_dual_bibles(media_item: BibleMediaItem):
    """
    Test select_search when two bibles are selected
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked_reference_search
    media_item.select_book_combo_box = MagicMock()
    media_item.from_chapter = MagicMock()
    media_item.from_verse = MagicMock()
    media_item.to_chapter = MagicMock()
    media_item.to_verse = MagicMock()
    with patch.object(media_item, 'display_results') as mocked_display_results:
        # WHEN: Calling select_search and there are two bibles selected
        media_item.bible = mocked_bible_1
        media_item.second_bible = mocked_bible_2
        media_item.select_search()

        # THEN: reference_search should be called twice
        assert media_item.plugin.manager.get_verses.call_count == 2
        mocked_display_results.assert_called_once_with()


def test_text_reference_search_single_bible(media_item: BibleMediaItem):
    """
    Test text_reference_search when only one bible is selected
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked plugin.manager.get_verses
    with patch.object(media_item, 'display_results') as mocked_display_results:
        # WHEN: Calling text_reference_search with only one bible selected
        media_item.bible = mocked_bible_1
        media_item.second_bible = None
        media_item.text_reference_search('Search Text')

        # THEN: reference_search should only be called once
        assert media_item.plugin.manager.get_verses.call_count == 1
        mocked_display_results.assert_called_once_with()

        def text_reference_search(self, search_text, search_while_type=False):
            """
            We are doing a 'Reference Search'.
            This search is called on def text_search by Reference and Combined Searches.
            """
            verse_refs = self.plugin.manager.parse_ref(self.bible.name, search_text)
            self.search_results = self.reference_search(verse_refs, self.bible)
            if self.second_bible and self.search_results:
                self.second_search_results = self.reference_search(verse_refs, self.second_bible)
            self.display_results()


def test_text_reference_search_dual_bible_no_results(media_item: BibleMediaItem):
    """
    Test text_reference_search when two bible are selected, but the search of the first bible does not return any
    results
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked plugin.manager.get_verses
    # WHEN: Calling text_reference_search with two bibles selected, but no results are found in the first bible
    with patch.object(media_item, 'display_results') as mocked_display_results:
        media_item.plugin.manager.get_verses.return_value = []
        media_item.bible = mocked_bible_1
        media_item.second_bible = mocked_bible_2
        media_item.text_reference_search('Search Text')

        # THEN: reference_search should only be called once
        assert media_item.plugin.manager.get_verses.call_count == 1
        mocked_display_results.assert_called_once_with()


def test_text_reference_search_dual_bible(media_item: BibleMediaItem):
    """
    Test text_reference_search when two bible are selected
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and mocked plugin.manager.get_verses
    with patch.object(media_item, 'display_results') as mocked_display_results:
        media_item.bible = mocked_bible_1
        media_item.second_bible = mocked_bible_2
        media_item.search_results = ''
        media_item.second_search_results = ''
        media_item.plugin.manager.get_verses.side_effect = lambda x, y, z: x

        # WHEN: Calling text_reference_search with two bibles selected
        media_item.text_reference_search('Search Text')

        # THEN: reference_search should be called twice
        assert media_item.plugin.manager.get_verses.call_count == 2
        assert media_item.search_results == 'Bible 1'
        assert media_item.second_search_results == 'Bible 2'
        mocked_display_results.assert_called_once_with()


def test_on_text_search_single_bible(media_item: BibleMediaItem):
    """
    Test on_text_search when only one bible is selected
    """
    # GIVEN: An instance of :class:`MediaManagerItem`
    media_item.bible = mocked_bible_1
    media_item.second_bible = None

    # WHEN: Calling on_text_search and plugin.manager.verse_search returns a list of results
    media_item.plugin.manager.verse_search.return_value = ['results', 'list']
    with patch.object(media_item, 'display_results') as mocked_display_results:
        media_item.on_text_search('Search Text')

        # THEN: The search results should be the same as those returned by plugin.manager.verse_search
        assert media_item.search_results == ['results', 'list']
        mocked_display_results.assert_called_once_with()


def test_on_text_search_no_results(media_item: BibleMediaItem):
    """
    Test on_text_search when the search of the first bible does not return any results
    """
    # GIVEN: An instance of :class:`MediaManagerItem`
    media_item.bible = mocked_bible_1
    media_item.second_bible = mocked_bible_2

    # WHEN: Calling on_text_search and plugin.manager.verse_search returns an empty list
    media_item.plugin.manager.verse_search.return_value = []
    with patch.object(media_item, 'display_results') as mocked_display_results:
        media_item.on_text_search('Search Text')

        # THEN: The search results should be an empty list
        assert media_item.search_results == []
        mocked_display_results.assert_called_once_with()


def test_on_text_search_all_results_in_both_books(media_item, mocked_log):
    """
    Test on_text_search when all of the results from the first bible are found in the second
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and some test data
    mocked_verse_1 = MagicMock(**{'book.book_reference_id': 1, 'chapter': 2, 'verse': 3})
    mocked_verse_1a = MagicMock(**{'book.book_reference_id': 1, 'chapter': 2, 'verse': 3})
    mocked_verse_2 = MagicMock(**{'book.book_reference_id': 4, 'chapter': 5, 'verse': 6})
    mocked_verse_2a = MagicMock(**{'book.book_reference_id': 4, 'chapter': 5, 'verse': 6})
    media_item.bible = mocked_bible_1
    media_item.second_bible = mocked_bible_2
    media_item.second_search_results = []
    media_item.second_bible.get_verses.reset_mock()

    # WHEN: Calling on_text_search and plugin.manager.verse_search returns a list of search results
    media_item.plugin.manager.verse_search.return_value = [mocked_verse_1, mocked_verse_2]
    media_item.second_bible.get_verses.return_value = [mocked_verse_1a, mocked_verse_2a]
    with patch.object(media_item, 'display_results') as mocked_display_results:
        media_item.on_text_search('Search Text')

        # THEN: The search results for both bibles should be returned
        assert media_item.search_results == [mocked_verse_1, mocked_verse_2]
        assert media_item.second_search_results == [mocked_verse_1a, mocked_verse_2a]
        media_item.second_bible.get_verses.assert_called_once_with([(1, 2, 3, 3), (4, 5, 6, 6)], False)
        not_found_calls = [call for call in mocked_log.debug.call_args_list
                           if 'not found in Second Bible' in call.args[0]]
        assert not_found_calls == []
        assert Registry().get('main_window').information_message.called is False
        mocked_display_results.assert_called_once_with()


def test_on_text_search_not_all_results_in_both_books(media_item, mocked_log):
    """
    Test on_text_search when not all of the results from the first bible are found in the second
    """
    # GIVEN: An instance of :class:`MediaManagerItem` and some test data
    mocked_verse_1 = MagicMock(**{'book.book_reference_id': 1, 'chapter': 2, 'verse': 3})
    mocked_verse_1a = MagicMock(**{'book.book_reference_id': 1, 'chapter': 2, 'verse': 3})
    mocked_verse_2 = MagicMock(**{'book.book_reference_id': 4, 'chapter': 5, 'verse': 6})
    mocked_verse_3 = MagicMock(**{'book.book_reference_id': 7, 'chapter': 8, 'verse': 9})
    media_item.bible = mocked_bible_1
    media_item.second_bible = mocked_bible_2
    media_item.second_search_results = []
    media_item.second_bible.get_verses.reset_mock()

    # WHEN: Calling on_text_search and not all results are found in the second bible
    media_item.plugin.manager.verse_search.return_value = [mocked_verse_1, mocked_verse_2, mocked_verse_3]
    media_item.second_bible.get_verses.return_value = [mocked_verse_1a]
    with patch.object(media_item, 'display_results') as mocked_display_results:
        media_item.on_text_search('Search Text')

        # THEN: The search results included in  both bibles should be returned and the user should be notified of
        #       the missing verses
        assert media_item.search_results == [mocked_verse_1]
        assert media_item.second_search_results == [mocked_verse_1a]
        media_item.second_bible.get_verses.assert_called_once_with([(1, 2, 3, 3), (4, 5, 6, 6), (7, 8, 9, 9)], False)
        not_found_calls = [call for call in mocked_log.debug.call_args_list
                           if 'not found in Second Bible' in call.args[0]]
        assert len(not_found_calls) == 2
        assert Registry().get('main_window').information_message.called is True
        mocked_display_results.assert_called_once_with()


def test_on_search_edit_text_changed_search_while_typing_disabled(media_item, mocked_timer):
    """
    Test on_search_edit_text_changed when 'search while typing' is disabled
    """
    # GIVEN: An instance of BibleMediaItem and mocked Settings which returns False when the value
    #       'bibles/is search while typing enabled' is requested
    Registry().get('settings').setValue('bibles/is search while typing enabled', False)
    media_item.search_timer = mocked_timer
    mocked_timer.isActive.return_value = False

    # WHEN: Calling on_search_edit_text_changed
    media_item.on_search_edit_text_changed()

    # THEN: The method should not have checked if the timer is active
    assert media_item.search_timer.isActive.called is False


def test_on_search_edit_text_changed_search_while_typing_enabled(media_item, mocked_timer):
    """
    Test on_search_edit_text_changed when 'search while typing' is enabled
    """
    # GIVEN: An instance of BibleMediaItem and mocked Settings which returns True when the value
    #       'bibles/is search while typing enabled' is requested
    Registry().get('settings').setValue('bibles/is search while typing enabled', True)
    media_item.search_timer = mocked_timer
    media_item.search_timer.isActive.return_value = False
    media_item.bible = mocked_bible_1
    media_item.bible.is_web_bible = False

    # WHEN: Calling on_search_edit_text_changed
    media_item.on_search_edit_text_changed()

    # THEN: The method should start the search_timer
    media_item.search_timer.isActive.assert_called_once_with()
    media_item.search_timer.start.assert_called_once_with()


def test_on_search_timer_timeout(media_item: BibleMediaItem):
    """
    Test on_search_timer_timeout
    """
    # GIVEN: An instance of BibleMediaItem
    with patch.object(media_item, 'text_search') as mocked_text_search:
        # WHEN: Calling on_search_timer_timeout
        media_item.on_search_timer_timeout()

        # THEN: The search_status should be set to SearchAsYouType and text_search should have been called
        assert media_item.search_status == SearchStatus.SearchAsYouType
        mocked_text_search.assert_called_once_with()


def test_display_results_no_results(media_item: BibleMediaItem):
    """
    Test the display_results method when there are no items to display
    """
    # GIVEN: An instance of BibleMediaItem and a mocked build_display_results which returns an empty list
    media_item.list_view = MagicMock()
    media_item.bible = mocked_bible_1
    media_item.second_bible = mocked_bible_2
    media_item.search_results = []

    with patch.object(media_item, 'build_display_results', return_value=[]):
        # WHEN: Calling display_results with True
        media_item.display_results()

        # THEN: No items should be added to the list
        assert media_item.list_view.addItem.called is False


def test_display_results_results(media_item: BibleMediaItem):
    """
    Test the display_results method when there are items to display
    """
    # GIVEN: An instance of BibleMediaItem and a mocked build_display_results which returns a list of results
    with patch.object(media_item, 'build_display_results', return_value=[
        {'item_title': 'Title 1'}, {'item_title': 'Title 2'}]), \
            patch.object(media_item, 'add_built_results_to_list_widget') as \
            mocked_add_built_results_to_list_widget:
        media_item.search_results = ['results']
        media_item.list_view = MagicMock()

        # WHEN: Calling display_results
        media_item.display_results()

        # THEN: addItem should have been with the display items
        mocked_add_built_results_to_list_widget.assert_called_once_with(
            [{'item_title': 'Title 1'}, {'item_title': 'Title 2'}])


def test_search_options(media_item: BibleMediaItem):
    """
    Test that the bible search options are returned
    """
    # GIVEN: An instance of BibleMediaItem, and mocked primary bible setting
    media_item.plugin.manager.get_bibles.return_value = MagicMock(keys=MagicMock(return_value=['a', 'b', 'c']))
    media_item.settings.value = lambda key: {'bibles/primary bible': 'b'}[key]

    # WHEN: calling search_options
    result = media_item.search_options()

    # THEN: result should be correct
    assert result == [{'name': 'primary bible', 'list': ['a', 'b', 'c'], 'selected': 'b'}]


def test_set_search_option(media_item: BibleMediaItem):
    """
    Test that the bible set search option function works
    """
    # GIVEN: An instance of BibleMediaItem, with a mocked get_bibles and a mocked populate_bible_combo_boxes function
    media_item.plugin.manager.get_bibles.return_value = MagicMock(keys=MagicMock(return_value=['a', 'b', 'c']))
    populate_bible_combo_boxes = MagicMock()
    Registry().remove_function('populate_bible_combo_boxes', media_item.populate_bible_combo_boxes)
    Registry().register_function('populate_bible_combo_boxes', populate_bible_combo_boxes)

    # WHEN: calling set_search_option
    result = media_item.set_search_option('primary bible', 'c')

    # THEN: result should be correct and the new bible set, and combo boxes updated
    assert result is True
    media_item.settings.setValue.assert_called_once_with('bibles/primary bible', 'c')
    populate_bible_combo_boxes.assert_called_once()


def test_set_search_option_invalid_option(media_item: BibleMediaItem):
    """
    Test that the bible set search option function rejects when using non existing option
    """
    # GIVEN: An instance of BibleMediaItem, with a mocked get_bibles and a mocked populate_bible_combo_boxes function
    media_item.plugin.manager.get_bibles.return_value = MagicMock(keys=MagicMock(return_value=['a', 'b', 'c']))
    populate_bible_combo_boxes = MagicMock()
    Registry().remove_function('populate_bible_combo_boxes', media_item.populate_bible_combo_boxes)
    Registry().register_function('populate_bible_combo_boxes', populate_bible_combo_boxes)

    # WHEN: calling set_search_option with invalid option
    result = media_item.set_search_option('not an option', 'a')

    # THEN: result should be False and nothing set, and combo boxes not updated
    assert result is False
    media_item.settings.setValue.assert_not_called()
    populate_bible_combo_boxes.assert_not_called()


def test_set_search_option_invalid_value(media_item: BibleMediaItem):
    """
    Test that the bible set search option function rejects when using non existing value
    """
    # GIVEN: An instance of BibleMediaItem, with a mocked get_bibles and a mocked populate_bible_combo_boxes function
    media_item.plugin.manager.get_bibles.return_value = MagicMock(keys=MagicMock(return_value=['a', 'b', 'c']))
    populate_bible_combo_boxes = MagicMock()
    Registry().remove_function('populate_bible_combo_boxes', media_item.populate_bible_combo_boxes)
    Registry().register_function('populate_bible_combo_boxes', populate_bible_combo_boxes)

    # WHEN: calling set_search_option with invalid value
    result = media_item.set_search_option('primary bible', 'not a value')

    # THEN: result should be False and nothing set, and combo boxes not updated
    assert result is False
    media_item.settings.setValue.assert_not_called()
    populate_bible_combo_boxes.assert_not_called()


def test_generate_slide_data_data_string(media_item: BibleMediaItem):
    """
    Test that the generated_slide_data provides data values for the api
    """
    # GIVEN: Mocked service item and some pretend bible slide data
    mocked_service_item = MagicMock()
    slide_data = {
        'book': 'Matthew',
        'book_abbreviation': 'Matt',
        'chapter': '1',
        'verse': '2',
        'version': 'Bible version 104',
        'copyright': 'copywrong',
        'permissions': 'all the permissions',
        'second_bible': 'Second bible thing',
        'second_copyright': 'copywrite',
        'second_permissions': 'no use allowed',
        'second_version': 'Bible version 4567',
        'text': 'text from matthew 1:2',
        'second_text': 'different text from matthew 1:2'
    }
    mocked_items = [MagicMock(**{'data.return_value': slide_data})]
    media_item.format_verse = MagicMock()
    media_item.settings_tab = MagicMock()

    # WHEN: Called generate_slide_data
    media_item.generate_slide_data(mocked_service_item, item=mocked_items)

    # THEN: both primary and secondary bible info should be included in the returned service item data string
    assert mocked_service_item.data_string == {
        'bibles': [
            {
                'version': 'Bible version 104',
                'copyright': 'copywrong',
                'permissions': 'all the permissions'
            },
            {
                'version': 'Bible version 4567',
                'copyright': 'copywrite',
                'permissions': 'no use allowed'
            }
        ]
    }


def test_generate_slide_data_data_string_one_bible(media_item: BibleMediaItem):
    """
    Test that the generated_slide_data provides data values for the api
    """
    # GIVEN: Mocked service item and some pretend bible slide data
    mocked_service_item = MagicMock()
    slide_data = {
        'book': 'Matthew',
        'book_abbreviation': 'Matt',
        'chapter': '1',
        'verse': '2',
        'version': 'Bible version 104',
        'copyright': 'copywrong',
        'permissions': 'all the permissions',
        'second_bible': '',
        'text': 'text from matthew 1:2'
    }
    mocked_items = [MagicMock(**{'data.return_value': slide_data})]
    media_item.format_verse = MagicMock()
    media_item.settings_tab = MagicMock()

    # WHEN: Called generate_slide_data
    media_item.generate_slide_data(mocked_service_item, item=mocked_items)

    # THEN: both primary and secondary bible info should be included in the returned service item data string
    assert mocked_service_item.data_string == {
        'bibles': [
            {
                'version': 'Bible version 104',
                'copyright': 'copywrong',
                'permissions': 'all the permissions'
            }
        ]
    }


def test_generate_slide_data_whole_verse_continuous_can_word_split(media_item: BibleMediaItem):
    """
    Test that WholeVerseContinuous Bible items advertise word splitting to the renderer.
    """
    # GIVEN: A single-bible WholeVerseContinuous item
    mocked_service_item = MagicMock()
    slide_data = {
        'book': 'Matthew',
        'book_abbreviation': 'Matt',
        'chapter': '1',
        'verse': '2',
        'version': 'Bible version 104',
        'copyright': 'copywrong',
        'permissions': 'all the permissions',
        'second_bible': '',
        'text': 'text from matthew 1:2'
    }
    mocked_items = [MagicMock(**{'data.return_value': slide_data})]
    media_item.format_verse = MagicMock(return_value='')
    media_item.settings_tab = MagicMock(layout_style=LayoutStyle.WholeVerseContinuous, bible_theme='')

    # WHEN: generate_slide_data is called
    media_item.generate_slide_data(mocked_service_item, item=mocked_items)

    # THEN: the renderer-facing capabilities should include both NoLineBreaks and CanWordSplit
    mocked_service_item.add_capability.assert_any_call(ItemCapabilities.NoLineBreaks)
    mocked_service_item.add_capability.assert_any_call(ItemCapabilities.CanWordSplit)


def _create_mocked_footer_slide_items():
    slide_data = {
        'book': 'Matthew',
        'book_abbreviation': 'Matt',
        'chapter': '1',
        'verse': '2',
        'version': 'Bible version 104',
        'copyright': 'copywrong',
        'permissions': 'all the permissions',
        'second_bible': '',
        'text': 'text from matthew 1:2'
    }
    return [MagicMock(**{'data.return_value': slide_data})]


def test_generate_slide_data_footer_reference_only(media_item: BibleMediaItem):
    """
    Test that only the verse reference is added to the footer when version, copyright and permission are disabled
    """
    # GIVEN: A mocked service item and settings which only show the reference in the footer
    mocked_service_item = MagicMock()
    mocked_service_item.raw_footer = []
    media_item.format_verse = MagicMock(return_value='')
    media_item.settings_tab = MagicMock(bible_theme='', show_reference_in_footer=True,
                                        show_version_in_footer=False, show_copyright_in_footer=False,
                                        show_permission_in_footer=False,
                                        reference_placement=ReferencePlacement.Footer)

    # WHEN: generate_slide_data is called
    media_item.generate_slide_data(mocked_service_item, item=_create_mocked_footer_slide_items())

    # THEN: the footer should only contain the verse reference, and the slide text should not contain an
    #       inline reference marker (reference_placement defaults to Footer)
    assert len(mocked_service_item.raw_footer) == 1
    assert 'Matthew' in mocked_service_item.raw_footer[0]
    assert 'Bible version 104' not in mocked_service_item.raw_footer[0]
    slide_text = mocked_service_item.add_from_text.call_args_list[0].args[0]
    assert 'Matt' not in slide_text


def test_generate_slide_data_footer_version_only(media_item: BibleMediaItem):
    """
    Test that only the version name is added to the footer when reference, copyright and permission are disabled
    """
    # GIVEN: A mocked service item and settings which only show the version name in the footer
    mocked_service_item = MagicMock()
    mocked_service_item.raw_footer = []
    media_item.format_verse = MagicMock(return_value='')
    media_item.settings_tab = MagicMock(bible_theme='', show_reference_in_footer=False,
                                        show_version_in_footer=True, show_copyright_in_footer=False,
                                        show_permission_in_footer=False)

    # WHEN: generate_slide_data is called
    media_item.generate_slide_data(mocked_service_item, item=_create_mocked_footer_slide_items())

    # THEN: the footer should only contain the version name
    assert mocked_service_item.raw_footer == ['Bible version 104']


def test_generate_slide_data_footer_all_disabled(media_item: BibleMediaItem):
    """
    Test that the footer stays empty when all footer options are disabled
    """
    # GIVEN: A mocked service item and settings which show nothing in the footer
    mocked_service_item = MagicMock()
    mocked_service_item.raw_footer = []
    media_item.format_verse = MagicMock(return_value='')
    media_item.settings_tab = MagicMock(bible_theme='', show_reference_in_footer=False,
                                        show_version_in_footer=False, show_copyright_in_footer=False,
                                        show_permission_in_footer=False)

    # WHEN: generate_slide_data is called
    media_item.generate_slide_data(mocked_service_item, item=_create_mocked_footer_slide_items())

    # THEN: the footer should be empty
    assert mocked_service_item.raw_footer == []


def test_generate_slide_data_reference_inline(media_item: BibleMediaItem):
    """
    Test that the short reference is appended inline after the verse text, and suppressed from the footer,
    when reference placement is Inline -- even though the "show reference in footer" checkbox is still on
    (placement and the checkbox are independent axes)
    """
    # GIVEN: A mocked service item and settings with reference placement set to Inline
    mocked_service_item = MagicMock()
    mocked_service_item.raw_footer = []
    media_item.format_verse = MagicMock(return_value='')
    media_item.settings_tab = MagicMock(bible_theme='', layout_style=LayoutStyle.VersePerSlide,
                                        show_reference_in_footer=True, show_version_in_footer=False,
                                        show_copyright_in_footer=False, show_permission_in_footer=False,
                                        reference_placement=ReferencePlacement.Inline)

    # WHEN: generate_slide_data is called
    with patch('openlp.plugins.bibles.lib.mediaitem.get_reference_separators',
               return_value={'verse': ':', 'range': '-', 'list': ','}):
        media_item.generate_slide_data(mocked_service_item, item=_create_mocked_footer_slide_items())

    # THEN: the footer should stay empty, and the slide text should contain the short inline reference
    assert mocked_service_item.raw_footer == []
    slide_text = mocked_service_item.add_from_text.call_args_list[0].args[0]
    assert 'Matt' in slide_text
    assert '1:2' in slide_text
    assert 'text from matthew 1:2' in slide_text
    assert '{su}' not in slide_text
    assert '{/su}' not in slide_text


@pytest.mark.parametrize('layout_style', [
    LayoutStyle.VersePerSlide, LayoutStyle.VersePerLine, LayoutStyle.Continuous, LayoutStyle.WholeVerseContinuous
])
def test_generate_slide_data_reference_inline_all_layout_styles(media_item: BibleMediaItem, layout_style):
    """
    Test that an inline reference is appended after every verse regardless of layout style, since for
    VersePerLine/Continuous/WholeVerseContinuous multiple verses can share a single raw slide that gets
    re-paginated later by the renderer -- so the reference can't be added once per finalised slide.
    """
    # GIVEN: Two mocked verses and settings with reference placement set to Inline
    mocked_service_item = MagicMock()
    mocked_service_item.raw_footer = []
    slide_data_1 = {
        'book': 'Matthew', 'book_abbreviation': 'Matt', 'chapter': 1, 'verse': 1,
        'version': 'Bible version 104', 'copyright': 'copywrong', 'permissions': 'all the permissions',
        'second_bible': '', 'text': 'verse one text'
    }
    slide_data_2 = {
        'book': 'Matthew', 'book_abbreviation': 'Matt', 'chapter': 1, 'verse': 2,
        'version': 'Bible version 104', 'copyright': 'copywrong', 'permissions': 'all the permissions',
        'second_bible': '', 'text': 'verse two text'
    }
    mocked_items = [MagicMock(**{'data.return_value': slide_data_1}),
                    MagicMock(**{'data.return_value': slide_data_2})]
    media_item.format_verse = MagicMock(return_value='')
    media_item.settings_tab = MagicMock(bible_theme='', layout_style=layout_style,
                                        show_reference_in_footer=False, show_version_in_footer=False,
                                        show_copyright_in_footer=False, show_permission_in_footer=False,
                                        reference_placement=ReferencePlacement.Inline)

    # WHEN: generate_slide_data is called
    with patch('openlp.plugins.bibles.lib.mediaitem.get_reference_separators',
               return_value={'verse': ':', 'range': '-', 'list': ','}):
        media_item.generate_slide_data(mocked_service_item, item=mocked_items)

    # THEN: a reference marker should appear once per verse, across however many slides were generated
    all_text = ' '.join(call.args[0] for call in mocked_service_item.add_from_text.call_args_list)
    assert all_text.count('Matt') == 2
    assert '1:1' in all_text
    assert '1:2' in all_text
    assert '{su}' not in all_text
    assert '{/su}' not in all_text


def test_format_verse_outputs_normal_size_text(media_item: BibleMediaItem):
    """
    Test that verse numbers are emitted without superscript formatting tags.
    """
    # GIVEN: Verse display enabled with no brackets
    media_item.settings_tab = MagicMock(is_verse_number_visible=True, show_new_chapters=False,
                                        display_style=DisplayStyle.NoBrackets)

    # WHEN: Formatting the verse prefix
    with patch('openlp.plugins.bibles.lib.mediaitem.get_reference_separators',
               return_value={'verse': ':', 'range': '-', 'list': ','}):
        verse_text = media_item.format_verse(old_chapter=1, chapter=1, verse=2)

    # THEN: The output should be normal-size text plus non-breaking trailing space
    assert verse_text == '1:2&nbsp;'
    assert '{su}' not in verse_text
    assert '{/su}' not in verse_text


def test_format_verse_reference_inline_outputs_normal_size_text(media_item: BibleMediaItem):
    """
    Test that inline references are emitted without superscript formatting tags.
    """
    # GIVEN: Inline reference placement
    media_item.settings_tab = MagicMock(reference_placement=ReferencePlacement.Inline)

    # WHEN: Formatting the inline reference
    with patch('openlp.plugins.bibles.lib.mediaitem.get_reference_separators',
               return_value={'verse': ':', 'range': '-', 'list': ','}):
        reference_text = media_item.format_verse_reference('Matt', 1, 2)

    # THEN: The output should be normal-size text and keep non-breaking spaces
    assert reference_text == '&nbsp;Matt&nbsp;1:2'
    assert '{su}' not in reference_text
    assert '{/su}' not in reference_text
