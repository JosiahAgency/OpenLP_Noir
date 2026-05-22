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
This module contains tests for the lib submodule of the Images plugin.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import ANY, MagicMock, patch

import pytest
from PySide6 import QtCore, QtWidgets

from openlp.core.common import case_insensitive_glob
from openlp.core.common.enum import ImageThemeMode
from openlp.core.common.registry import Registry
from openlp.core.db.manager import DBManager
from openlp.core.lib import build_icon, create_thumb
from openlp.core.lib.serviceitem import ItemCapabilities
from openlp.core.widgets.views import TreeWidgetWithDnD
from openlp.plugins.images.lib.mediaitem import ImageMediaItem
from tests.utils.constants import TEST_RESOURCES_PATH


@pytest.fixture
def media_item(registry: Registry, mock_settings: MagicMock):
    """Local test setup"""
    mocked_main_window = MagicMock()
    Registry().register('service_list', MagicMock())
    Registry().register('main_window', mocked_main_window)
    Registry().register('live_controller', MagicMock())
    mocked_plugin = MagicMock()
    with patch('openlp.plugins.images.lib.mediaitem.FolderLibraryItem._setup'), \
            patch('openlp.plugins.images.lib.mediaitem.ImageMediaItem.setup_item'):
        m_item = ImageMediaItem(None, mocked_plugin)
        m_item.settings_section = 'images'
        m_item.list_view = MagicMock()
    return m_item


def test_setup_item(registry: Registry, media_item: ImageMediaItem):
    """Test that setup_item() does the right thing"""
    # GIVEN: An instance of ImageMediaItem with some stuff mocked out
    # WHEN: setup_item is called
    with patch.object(media_item, 'list_view') as mocked_list_view, \
            patch.object(media_item, 'images_go_live') as mocked_images_go_live, \
            patch.object(media_item, 'images_add_to_service') as mocked_images_add_to_service:
        media_item.setup_item()

    # THEN: The correct things should be set and called
    mocked_images_go_live.connect.assert_called_once_with(media_item.go_live_remote)
    mocked_images_add_to_service.connect.assert_called_once_with(media_item.add_to_service_remote)
    assert media_item.quick_preview_allowed is True
    assert media_item.has_search is True
    mocked_list_view.setSelectionMode.assert_called_once_with(QtWidgets.QAbstractItemView.ExtendedSelection)
    assert registry.has_function('live_theme_changed')
    assert registry.has_function('slidecontroller_live_started')
    mocked_list_view.activateDnD.assert_called_once_with()


@patch('openlp.plugins.images.lib.mediaitem.FolderLibraryItem.retranslate_ui')
def test_retranslate_ui(mocked_retranslate_ui: MagicMock, media_item: ImageMediaItem):
    """Test that the retranslate_ui method sets up the strings in the UI"""
    # GIVEN: An insance of ImageMediaItem with some stuff mocked out
    media_item.replace_action = MagicMock()
    media_item.replace_action_context = MagicMock()
    media_item.reset_action = MagicMock()
    media_item.reset_action_context = MagicMock()

    # WHEN: retranslate_ui() is called
    media_item.retranslate_ui()

    # THEN: The UI is translated
    assert media_item.on_new_prompt == 'Select Image(s)'
    # file_formats = get_images_filter()
    # self.on_new_file_masks = '{formats};;{files} (*)'.format(formats=file_formats, files=UiStrings().AllFiles)
    expected_replace_text = 'Replace Background'
    expected_replace_tooltip = 'Replace live background.'
    media_item.replace_action.setText.assert_called_once_with(expected_replace_text)
    media_item.replace_action.setToolTip.assert_called_once_with(expected_replace_tooltip)
    media_item.replace_action_context.setText.assert_called_once_with(expected_replace_text)
    media_item.replace_action_context.setToolTip.assert_called_once_with(expected_replace_tooltip)
    expected_reset_text = 'Reset Background'
    expected_reset_tooltip = 'Reset live background.'
    media_item.reset_action.setText.assert_called_once_with(expected_reset_text)
    media_item.reset_action.setToolTip.assert_called_once_with(expected_reset_tooltip)
    media_item.reset_action_context.setText.assert_called_once_with(expected_reset_text)
    media_item.reset_action_context.setToolTip.assert_called_once_with(expected_reset_tooltip)


@patch('openlp.plugins.images.lib.mediaitem.FolderLibraryItem.retranslate_ui')
def test_retranslate_ui_file_masks_are_case_insensitive(mocked_retranslate_ui: MagicMock,
                                                        media_item: ImageMediaItem):
    """Test that on_new_file_masks contains case-insensitive glob patterns for common image extensions"""
    # GIVEN: An instance of ImageMediaItem with actions mocked out
    media_item.replace_action = MagicMock()
    media_item.replace_action_context = MagicMock()
    media_item.reset_action = MagicMock()
    media_item.reset_action_context = MagicMock()

    # WHEN: retranslate_ui() is called
    media_item.retranslate_ui()

    # THEN: The file masks should contain case-insensitive glob patterns for common image extensions,
    #       so that files like image.PNG or image.Jpg are not filtered out on case-sensitive filesystems
    assert case_insensitive_glob('png') in media_item.on_new_file_masks, \
        'The file mask should contain a case-insensitive pattern for png'
    assert case_insensitive_glob('jpg') in media_item.on_new_file_masks, \
        'The file mask should contain a case-insensitive pattern for jpg'
    assert case_insensitive_glob('jpeg') in media_item.on_new_file_masks, \
        'The file mask should contain a case-insensitive pattern for jpeg'
    assert case_insensitive_glob('gif') in media_item.on_new_file_masks, \
        'The file mask should contain a case-insensitive pattern for gif'
    assert case_insensitive_glob('bmp') in media_item.on_new_file_masks, \
        'The file mask should contain a case-insensitive pattern for bmp'


@patch('openlp.plugins.images.lib.mediaitem.FolderLibraryItem.required_icons')
def test_required_icons(mocked_required_icons: MagicMock, media_item: ImageMediaItem):
    """Test that the required_icons() method sets up the flags for icons needed"""
    # GIVEN: An insance of ImageMediaItem
    # WHEN: required_icons() is called
    media_item.required_icons()

    # THEN: The correct flags are set
    assert media_item.has_file_icon is True
    assert media_item.has_new_icon is False
    assert media_item.has_edit_icon is False
    assert media_item.add_to_service_item is True


@patch('openlp.plugins.images.lib.mediaitem.create_paths')
@patch('openlp.plugins.images.lib.mediaitem.Item', autospec=True)
def test_initialise(MockItem: MagicMock, mocked_create_paths: MagicMock, media_item: ImageMediaItem):
    """Test that the initialise method does the right things"""
    # GIVEN: An instance of ImageMediaItem and some stuff mocked out
    media_item.list_view = MagicMock(spec=TreeWidgetWithDnD, default_indentation=4)
    media_item.manager = MagicMock(spec=DBManager)
    media_item.manager.get_all_objects.return_value = []
    media_item.load_list = MagicMock()

    # WHEN: initialise() is called
    media_item.initialise()

    # THEN: The correct methods should have been called
    media_item.list_view.clear.assert_called_once_with()
    media_item.list_view.setIconSize.assert_called_once_with(QtCore.QSize(88, 50))
    media_item.list_view.setIndentation.assert_called_once_with(4)
    assert media_item.list_view.allow_internal_dnd is True
    assert media_item.service_path.parts[-1] == 'thumbnails'
    mocked_create_paths.assert_called_once_with(media_item.service_path)
    media_item.manager.get_all_objects.assert_called_once_with(MockItem, order_by_ref=MockItem.file_path)
    media_item.load_list.assert_called_once_with([], is_initial_load=True)


def test_on_reset_click(media_item: ImageMediaItem):
    """
    Test that on_reset_click() actually resets the background
    """
    # GIVEN: A mocked version of reset_action
    media_item.reset_action = MagicMock()
    media_item.reset_action_context = MagicMock()

    # WHEN: on_reset_click is called
    media_item.on_reset_click()

    # THEN: the reset_action should be set invisible, and the image should be reset
    media_item.reset_action.setVisible.assert_called_with(False)
    media_item.reset_action_context.setVisible.assert_called_with(False)
    media_item.live_controller.reload_theme.assert_called_with()


def test_on_display_changed(media_item):
    """
    Test that on_display_changed() hides the reset background button
    """
    # GIVEN: A mocked version of reset_action
    media_item.reset_action = MagicMock()
    media_item.reset_action_context = MagicMock()

    # WHEN: on_display_changed is called
    media_item.on_display_changed()

    # THEN: the reset_action should be set invisible
    media_item.reset_action.setVisible.assert_called_with(False)
    media_item.reset_action_context.setVisible.assert_called_with(False)


def test_generate_slide_data_default_theme(media_item):
    """
    Test that the generated service item provides the corect theme
    """
    # GIVEN: A mocked service item and settings
    mocked_service_item = MagicMock()
    media_item.list_view = MagicMock()
    Registry().get('settings').value.side_effect = [ImageThemeMode.Black]

    # WHEN: generate_slide_data is called
    media_item.generate_slide_data(mocked_service_item)

    # THEN: The service item should force the theme, and use the default theme
    mocked_service_item.add_capability.assert_any_call(ItemCapabilities.ProvidesOwnTheme)
    assert mocked_service_item.theme == -1


def test_generate_slide_data_custom_theme(media_item):
    """
    Test that the generated service item provides the corect theme
    """
    # GIVEN: A mocked service item and settings
    mocked_service_item = MagicMock()
    media_item.list_view = MagicMock()
    Registry().get('settings').value.side_effect = [ImageThemeMode.CustomTheme, 'theme_name']

    # WHEN: generate_slide_data is called
    media_item.generate_slide_data(mocked_service_item)

    # THEN: The service item should force the theme, and use the theme in the settings
    mocked_service_item.add_capability.assert_any_call(ItemCapabilities.ProvidesOwnTheme)
    assert mocked_service_item.theme == 'theme_name'


@patch('openlp.plugins.images.lib.mediaitem.check_item_selected')
@patch('openlp.plugins.images.lib.mediaitem.isinstance')
@patch('openlp.plugins.images.lib.mediaitem.Path.exists')
def test_on_replace_click(mocked_exists, mocked_isinstance, mocked_check_item_selected, media_item):
    """
    Test that on_replace_click() actually sets the background
    """
    # GIVEN: A mocked version of reset_action, and a (faked) existing selected image file
    media_item.reset_action = MagicMock()
    media_item.reset_action_context = MagicMock()
    media_item.list_view = MagicMock()
    mocked_check_item_selected.return_value = True
    mocked_isinstance.return_value = True
    mocked_exists.return_value = True

    # WHEN: on_replace_click is called
    media_item.on_replace_click()

    # THEN: the reset_action should be set visible, and the image should be set
    media_item.reset_action.setVisible.assert_called_with(True)
    media_item.reset_action_context.setVisible.assert_called_with(True)
    media_item.live_controller.set_background_image.assert_called_with(ANY)


def test_generate_thumbnail_path_hash(media_item):
    """
    Test that the thumbnail path is correctly generated with the file hash
    """
    # GIVEN: A media item and an Image object
    mocked_image = MagicMock(file_path=Path('myimage.jpg'), file_hash='c3986a0bd8e1ec9da406df142950c67e7d435410')
    media_item.service_path = Path('.')

    # WHEN: generate_thumbnail_path() is called
    result = media_item.generate_thumbnail_path(mocked_image)

    # THEN: The path should be correct
    assert result == Path('.') / 'c3986a0bd8e1ec9da406df142950c67e7d435410.jpg'


def test_generate_thumbnail_path_filename(media_item):
    """
    Test that the thumbnail path is correctly generated with the file name
    """
    # GIVEN: A media item and an Image object
    mocked_image = MagicMock(file_path=Path('myimage.jpg'), file_hash=None)
    media_item.service_path = Path('.')

    # WHEN: generate_thumbnail_path() is called
    result = media_item.generate_thumbnail_path(mocked_image)

    # THEN: The path should be correct
    assert result == Path('.') / 'myimage.jpg'


@patch('openlp.plugins.images.lib.mediaitem.create_thumb')
def test_load_item_file_not_exist(mocked_create_thumb: MagicMock, media_item: ImageMediaItem):
    """Test the load_item method when the file does not exist"""
    # GIVEN: A media item and an Item to load
    item = MagicMock(file_path=Path('myimage.jpg'), file_hash=None)

    # WHEN load_item() is called with the Item
    result = media_item.load_item(item)

    # THEN: A QTreeWidgetItem with a "delete" icon should be returned
    assert isinstance(result, QtWidgets.QTreeWidgetItem)
    assert result.text(0) == 'myimage.jpg'
    mocked_create_thumb.assert_not_called()


@patch('openlp.plugins.images.lib.mediaitem.validate_thumb')
@patch('openlp.plugins.images.lib.mediaitem.create_thumb', wraps=create_thumb)
@patch('openlp.plugins.images.lib.mediaitem.build_icon', wraps=build_icon)
def test_load_item_valid_thumbnail(mocked_build_icon: MagicMock, mocked_create_thumb: MagicMock,
                                   mocked_validate_thumb: MagicMock, media_item: ImageMediaItem, registry: Registry):
    """Test the load_item method with an existing thumbnail"""
    # GIVEN: A media item and an Item to load
    media_item.service_path = Path(TEST_RESOURCES_PATH) / 'images'
    mocked_validate_thumb.return_value = True
    image_path = Path(TEST_RESOURCES_PATH) / 'images' / 'tractor.jpg'
    item = MagicMock(file_path=image_path, file_hash=None)

    # WHEN load_item() is called with the Item
    result = media_item.load_item(item)

    # THEN: A QTreeWidgetItem with a "delete" icon should be returned
    assert isinstance(result, QtWidgets.QTreeWidgetItem)
    assert result.text(0) == 'tractor.jpg'
    assert result.toolTip(0) == str(image_path)
    mocked_create_thumb.assert_not_called()
    mocked_build_icon.assert_called_once_with(image_path)


@patch('openlp.plugins.images.lib.mediaitem.validate_thumb')
@patch('openlp.plugins.images.lib.mediaitem.create_thumb', wraps=create_thumb)
def test_load_item_missing_thumbnail(mocked_create_thumb: MagicMock, mocked_validate_thumb: MagicMock,
                                     media_item: ImageMediaItem, registry: Registry):
    """Test the load_item method with no valid thumbnails"""
    # GIVEN: A media item and an Item to load
    with TemporaryDirectory() as tmpdir:
        media_item.service_path = Path(tmpdir)
        mocked_validate_thumb.return_value = False
        image_path = Path(TEST_RESOURCES_PATH) / 'images' / 'tractor.jpg'
        item = MagicMock(file_path=image_path, file_hash=None)
        registry.get('settings').value.return_value = 400

        # WHEN load_item() is called with the Item
        result = media_item.load_item(item)

        # THEN: A QTreeWidgetItem with a "delete" icon should be returned
        assert isinstance(result, QtWidgets.QTreeWidgetItem)
        assert result.text(0) == 'tractor.jpg'
        assert result.toolTip(0) == str(image_path)
        mocked_create_thumb.assert_called_once_with(image_path, Path(tmpdir, 'tractor.jpg'), size=QtCore.QSize(-1, 400))
