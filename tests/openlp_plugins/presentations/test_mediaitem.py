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
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, call, patch

from PySide6 import QtCore, QtWidgets

from openlp.core.common import case_insensitive_glob
from openlp.core.lib import ServiceItemContext
from openlp.core.lib.serviceitem import ItemCapabilities
from openlp.plugins.presentations.lib.db import Folder, Item
from openlp.plugins.presentations.lib.mediaitem import PresentationMediaItem


def test_build_file_mask_string(media_item):
    """
    Test the build_file_mask_string() method
    """
    # GIVEN: Different controllers.
    impress_controller = MagicMock()
    impress_controller.enabled.return_value = True
    impress_controller.supports = ['odp']
    impress_controller.also_supports = ['ppt']
    presentation_controller = MagicMock()
    presentation_controller.enabled.return_value = True
    presentation_controller.supports = ['ppt']
    presentation_controller.also_supports = []
    presentation_viewer_controller = MagicMock()
    presentation_viewer_controller.enabled.return_value = False
    pdf_controller = MagicMock()
    pdf_controller.enabled.return_value = True
    pdf_controller.supports = ['pdf']
    pdf_controller.also_supports = ['xps', 'oxps', 'epub', 'cbz', 'fb2']
    # Mock the controllers.
    media_item.controllers = {
        'Impress': impress_controller,
        'Powerpoint': presentation_controller,
        'Powerpoint Viewer': presentation_viewer_controller,
        'Pdf': pdf_controller
    }

    # WHEN: Build the file mask.
    with patch('openlp.plugins.presentations.lib.mediaitem.translate') as mocked_translate:
        mocked_translate.side_effect = lambda module, string_to_translate: string_to_translate
        media_item.build_file_mask_string()

    # THEN: The file mask should be generated correctly with a space before all bar the first.
    assert case_insensitive_glob('odp') in media_item.on_new_file_masks, \
        'The file mask should contain the odp extension'
    assert case_insensitive_glob('ppt') in media_item.on_new_file_masks, \
        'The file mask should contain the ppt extension'
    assert case_insensitive_glob('pdf') in media_item.on_new_file_masks, \
        'The file mask should contain the pdf extension'
    assert case_insensitive_glob('PdF') in media_item.on_new_file_masks, \
        'The file mask should contain the pdf extension'
    assert case_insensitive_glob('xps') in media_item.on_new_file_masks, \
        'The file mask should contain the xps extension'
    assert case_insensitive_glob('oxps') in media_item.on_new_file_masks, \
        'The file mask should contain the oxps extension'
    assert case_insensitive_glob('epub') in media_item.on_new_file_masks, \
        'The file mask should contain the epub extension'
    assert case_insensitive_glob('cbz') in media_item.on_new_file_masks, \
        'The file mask should contain the cbz extension'
    assert case_insensitive_glob('fb2') in media_item.on_new_file_masks, \
        'The file mask should contain the fb2 extension'


def test_clean_up_thumbnails(media_item):
    """
    Test that the clean_up_thumbnails method works as expected when files exist.
    """
    # GIVEN: A mocked controller, and mocked os.path.getmtime
    mocked_disabled_controller = MagicMock()
    mocked_disabled_controller.enabled.return_value = False
    mocked_disabled_supports = PropertyMock()
    type(mocked_disabled_controller).supports = mocked_disabled_supports
    mocked_enabled_controller = MagicMock()
    mocked_enabled_controller.enabled.return_value = True
    mocked_doc = MagicMock(**{'get_thumbnail_path.return_value': Path()})
    mocked_enabled_controller.add_document.return_value = mocked_doc
    mocked_enabled_controller.supports = ['tmp']
    media_item.controllers = {
        'Enabled': mocked_enabled_controller,
        'Disabled': mocked_disabled_controller
    }

    thumb_path = MagicMock(st_mtime=100)
    file_path = MagicMock(st_mtime=400)
    with patch.object(Path, 'stat', side_effect=[thumb_path, file_path]), \
            patch.object(Path, 'exists', return_value=True):
        presentation_file = Path('file.tmp')

        # WHEN: calling clean_up_thumbnails
        media_item.clean_up_thumbnails(presentation_file, True)

    # THEN: doc.presentation_deleted should have been called since the thumbnails mtime will be greater than
    #       the presentation_file's mtime.
    mocked_doc.assert_has_calls([call.get_thumbnail_path(1, True), call.presentation_deleted()], True)
    assert mocked_disabled_supports.call_count == 0


def test_clean_up_thumbnails_missing_file(media_item):
    """
    Test that the clean_up_thumbnails method works as expected when file is missing.
    """
    # GIVEN: A mocked controller, and mocked os.path.exists
    mocked_controller = MagicMock()
    mocked_doc = MagicMock()
    mocked_controller.add_document.return_value = mocked_doc
    mocked_controller.supports = ['tmp']
    media_item.controllers = {
        'Mocked': mocked_controller
    }
    presentation_file = Path('file.tmp')
    with patch.object(Path, 'exists', return_value=False):

        # WHEN: calling clean_up_thumbnails
        media_item.clean_up_thumbnails(presentation_file, True)

    # THEN: doc.presentation_deleted should have been called since the presentation file did not exist.
    mocked_doc.assert_has_calls([call.get_thumbnail_path(1, True), call.presentation_deleted()], True)


def test_generate_slide_data_from_folder(media_item):
    """
    Test that the generate slide data function exits early when the item is a Folder instead of an Item
    """
    # GIVEN: A Folder instance
    media_item.list_view = MagicMock()
    mocked_service_item = MagicMock()
    folder = Folder(id=1, name='Mock folder')
    list_item = QtWidgets.QTreeWidgetItem(None)
    list_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, folder)

    # WHEN: generate_slide_data is called
    result = media_item.generate_slide_data(mocked_service_item, item=list_item)

    # THEN: The result should be false
    assert result is False


def test_generate_slide_data_from_list_view(media_item):
    """
    Test that the generate slide data function exits early when there are more than 1 items selected
    """
    # GIVEN: A Folder instance
    mocked_service_item = MagicMock()
    list_item = QtWidgets.QTreeWidgetItem(None)
    media_item.list_view = MagicMock(selectedItems=MagicMock(return_value=[list_item, list_item]))

    # WHEN: generate_slide_data is called
    result = media_item.generate_slide_data(mocked_service_item)

    # THEN: The result should be false
    assert result is False


def test_generate_slide_data_with_file_path_from_item(media_item):
    """
    Test that the generate slide data function exits early when there is no display type combobox text
    """
    # GIVEN: A Folder instance
    media_item.list_view = MagicMock()
    media_item.display_type_combo_box = MagicMock(currentText=MagicMock(return_value=''))
    mocked_service_item = MagicMock()
    item = Item(id=1, file_path='path/to/presentation.odp')
    list_item = QtWidgets.QTreeWidgetItem(None)
    list_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, item)

    # WHEN: generate_slide_data is called
    result = media_item.generate_slide_data(mocked_service_item, item=list_item)

    # THEN: The result should be false
    assert result is False


def test_generate_slide_data_from_pdf(media_item):
    """
    Test that the generate slide data function makes the correct ajustments to a pdf service item.
    """
    # GIVEN: A mocked pdf service item
    media_item.list_view = MagicMock()
    media_item.display_type_combo_box = MagicMock()
    mocked_service_item = MagicMock()

    # WHEN: generate_slide_data is called
    media_item.generate_slide_data(mocked_service_item, context=ServiceItemContext.Live, file_path=Path('test.pdf'))

    # THEN: Should be categorized as images and overrides the theme
    assert mocked_service_item.name == 'images'
    mocked_service_item.add_capability.assert_any_call(ItemCapabilities.ProvidesOwnTheme)


@patch('openlp.core.lib.ui.Registry')
def test_generate_slide_data_with_nonexistent_path(MockRegistry, media_item):
    """
    Test that the generate slide data function shows the right error for non-existent paths.
    """
    # GIVEN: A mocked pdf service item
    media_item.list_view = MagicMock()
    media_item.display_type_combo_box = MagicMock()
    mocked_service_item = MagicMock()

    # WHEN: generate_slide_data is called with a file_path that doesn't really exist
    success = media_item.generate_slide_data(
            mocked_service_item,
            item=mocked_service_item,
            context=ServiceItemContext.Live,
            file_path=Path('test.pdf')
    )

    # THEN: a error message box should appear telling the user that the path doesn't exist
    MockRegistry.return_value.get.return_value.error_message.assert_called_once_with(
            'Missing Presentation',
            'The presentation test.pdf no longer exists.'
    )

    # THEN: The slide data could not be generated.
    assert success is False, 'The slide data could not be generated'


@patch('openlp.core.lib.ui.Registry')
def test_generate_slide_data_with_inaccessible_path(MockRegistry, media_item):
    """
    Test that the generate slide data function shows the right error for inaccessible paths.
    """
    # GIVEN: A mocked pdf service item
    media_item.list_view = MagicMock()
    media_item.display_type_combo_box = MagicMock()
    mocked_service_item = MagicMock()

    with patch('openlp.plugins.presentations.lib.mediaitem.Path') as mocked_path:
        # GIVEN: A fake file which "exists" cannot be read - so it's inaccessible
        mocked_path.exists.return_value = True
        file_path = mocked_path('test.pdf')

        # WHEN: generate_slide_data is called with a file_path that can't be read
        success = media_item.generate_slide_data(
                mocked_service_item,
                item=mocked_service_item,
                context=ServiceItemContext.Live,
                file_path=file_path
        )

        # THEN: a error message box should appear telling the user that the path doesn't exist
        MockRegistry.return_value.get.return_value.error_message.assert_called_once_with(
                'Missing Presentation',
                f'The presentation {file_path} is inaccessible.'
        )

        # THEN: The slide data could not be generated.
        assert success is False, 'The slide data could not be generated'


@patch('openlp.plugins.presentations.lib.mediaitem.FolderLibraryItem._setup')
@patch('openlp.plugins.presentations.lib.mediaitem.PresentationMediaItem.setup_item')
def test_search_found(mock_setup, mock_item, registry):
    """
    Test that the search method works correctly
    """
    # GIVEN: The Mediaitem set up a list of presentations
    media_item = PresentationMediaItem(None, MagicMock(), None)
    media_item.manager = MagicMock()
    media_item.manager.get_all_objects.return_value = [MagicMock(file_path='test.odp')]

    # WHEN: Retrieving the test file
    result = media_item.search('test.odp', False)

    # THEN: a file should be found
    assert result == [['test.odp', 'test.odp']], 'The result file contain the file name'


@patch('openlp.plugins.presentations.lib.mediaitem.FolderLibraryItem._setup')
@patch('openlp.plugins.presentations.lib.mediaitem.PresentationMediaItem.setup_item')
def test_search_not_found(mock_setup, mock_item, registry):
    """
    Test that the search doesn't find anything
    """
    # GIVEN: The Mediaitem set up a list of media
    media_item = PresentationMediaItem(None, MagicMock(), None)
    media_item.manager = MagicMock()
    media_item.manager.get_all_objects.return_value = []

    # WHEN: Retrieving the test file
    result = media_item.search('test.pptx', False)

    # THEN: a file should be found
    assert result == [], 'The result file should be empty'
