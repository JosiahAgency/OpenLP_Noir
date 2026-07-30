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
Package to test the openlp.core.widgets.views package.
"""
import os
import pytest
from types import GeneratorType
from unittest.mock import MagicMock, call, patch

from PySide6 import QtGui, QtWidgets

from openlp.core.common.i18n import UiStrings
from openlp.core.common.registry import Registry
from openlp.core.lib.serviceitem import ServiceItem
from openlp.core.widgets.views import ListPreviewWidget, ListWidgetWithDnD, NoirServiceDelegate, \
    NoirSlideDelegate, TreeWidgetWithDnD, handle_mime_data_urls
from openlp.core.ui.icons import UiIcons
from openlp.core.ui.style import NOIR_INK_3, NOIR_INK_4, NOIR_PLUGIN_SONGS, NOIR_VERSE_CHORUS, NOIR_VERSE_VERSE
from tests.utils.osdinteraction import read_service_from_file


@pytest.fixture
def clapperboard(mock_settings):
    return UiIcons().clapperboard


@pytest.fixture
def preview_widget_env():
    """Local test setup"""
    parent_patcher = patch('openlp.core.widgets.views.ListPreviewWidget.parent')
    mocked_parent = parent_patcher.start()
    mocked_parent.width.return_value = 100

    # Mock self.viewport().width()
    viewport_patcher = patch('openlp.core.widgets.views.ListPreviewWidget.viewport')
    mocked_viewport = viewport_patcher.start()
    mocked_viewport_obj = MagicMock()
    mocked_viewport_obj.return_value.width.return_value = 200
    mocked_viewport.return_value = mocked_viewport_obj
    yield mocked_parent, mocked_viewport_obj
    parent_patcher.stop()
    viewport_patcher.stop()


@pytest.fixture()
def mocked_parent():
    """A prepared parent object"""
    parent_obj = QtWidgets.QWidget(None)
    with patch.object(parent_obj, 'width') as mocked_width:
        mocked_width.return_value = 100
        yield parent_obj


@pytest.fixture()
def preview_widget(settings):
    main_window = QtWidgets.QMainWindow()
    Registry().register('main_window', main_window)
    p_widget = ListPreviewWidget(main_window, 2)
    return p_widget


def test_files():
    """
    Test handle_mime_data_urls when the data points to some files.
    """
    # GIVEN: Some mocked objects that return True when is_file is called, and some mocked mime data
    mocked_path_instance_1 = MagicMock(**{'is_file.return_value': True})
    mocked_path_instance_2 = MagicMock(**{'is_file.return_value': True})
    with patch('openlp.core.widgets.views.Path',
               side_effect=[mocked_path_instance_1, mocked_path_instance_2]) as mocked_path:
        mocked_q_url_1 = MagicMock(**{'toLocalFile.return_value': os.path.join('file', 'test', 'path', '1.ext')})
        mocked_q_url_2 = MagicMock(**{'toLocalFile.return_value': os.path.join('file', 'test', 'path', '2.ext')})
        mocked_q_mime_data = MagicMock(**{'urls.return_value': [mocked_q_url_1, mocked_q_url_2]})

        # WHEN: Calling handle_mime_data_urls with the mocked mime data
        result = handle_mime_data_urls(mocked_q_mime_data)

        # THEN: Both mocked Path objects should be returned in the list
        mocked_path.assert_has_calls([call(os.path.join('file', 'test', 'path', '1.ext')),
                                      call(os.path.join('file', 'test', 'path', '2.ext'))])
        assert result == [mocked_path_instance_1, mocked_path_instance_2]


def test_directory():
    """
    Test handle_mime_data_urls when the data points to some directories.
    """
    # GIVEN: Some mocked objects that return True when is_dir is called, and some mocked mime data
    mocked_path_instance_1 = MagicMock()
    mocked_path_instance_2 = MagicMock()
    mocked_path_instance_3 = MagicMock()
    mocked_path_instance_4 = MagicMock(**{'is_file.return_value': False, 'is_directory.return_value': True,
                                          'iterdir.return_value': [mocked_path_instance_1, mocked_path_instance_2]})
    mocked_path_instance_5 = MagicMock(**{'is_file.return_value': False, 'is_directory.return_value': True,
                                          'iterdir.return_value': [mocked_path_instance_3]})
    with patch('openlp.core.widgets.views.Path',
               side_effect=[mocked_path_instance_4, mocked_path_instance_5]) as mocked_path:
        mocked_q_url_1 = MagicMock(**{'toLocalFile.return_value': os.path.join('file', 'test', 'path')})
        mocked_q_url_2 = MagicMock(**{'toLocalFile.return_value': os.path.join('file', 'test', 'path')})
        mocked_q_mime_data = MagicMock(**{'urls.return_value': [mocked_q_url_1, mocked_q_url_2]})

        # WHEN: Calling handle_mime_data_urls with the mocked mime data
        result = handle_mime_data_urls(mocked_q_mime_data)

        # THEN: The three mocked Path file objects should be returned in the list
        mocked_path.assert_has_calls([call(os.path.join('file', 'test', 'path')),
                                      call(os.path.join('file', 'test', 'path'))])
        assert result == [mocked_path_instance_1, mocked_path_instance_2, mocked_path_instance_3]


def test_new_list_preview_widget(mocked_parent: QtWidgets.QWidget, mock_settings: MagicMock):
    """
    Test that creating an instance of ListPreviewWidget works
    """
    # GIVEN: A ListPreviewWidget class with a mocked parent
    # WHEN: An object is created
    list_preview_widget = ListPreviewWidget(mocked_parent, 1)

    # THEN: The object is not None, and the _setup() method was called.
    assert list_preview_widget is not None, 'The ListPreviewWidget object should not be None'
    assert list_preview_widget.screen_ratio == 1, 'Should not be called'


def test_replace_service_item_thumbs(mocked_parent: QtWidgets.QWidget, mock_settings: MagicMock):
    """
    Test that thubmails for different slides are loaded properly in replace_service_item.
    """
    # GIVEN: A setting to adjust "Max height for non-text slides in slide controller",
    #        different ServiceItem(s), an ImageManager, and a ListPreviewWidget.

    # Mock Settings().value('advanced/slide max height')
    mock_settings.value.return_value = 0
    # Mock self.viewport().width()
    mocked_viewport_obj = MagicMock()
    mocked_viewport_obj.return_value.width.return_value = 200
    # Mock Image service item
    mocked_img_service_item = MagicMock()
    mocked_img_service_item.is_text.return_value = False
    mocked_img_service_item.is_media.return_value = False
    mocked_img_service_item.is_command.return_value = False
    mocked_img_service_item.is_capable.return_value = False
    mocked_img_service_item.get_frames.return_value = [{'title': None, 'path': 'TEST1', 'image': 'FAIL'},
                                                       {'title': None, 'path': 'TEST2', 'image': 'FAIL'}]
    # Mock Command service item
    mocked_cmd_service_item = MagicMock()
    mocked_cmd_service_item.is_text.return_value = False
    mocked_cmd_service_item.is_media.return_value = False
    mocked_cmd_service_item.is_command.return_value = True
    mocked_cmd_service_item.is_capable.return_value = True
    mocked_cmd_service_item.get_frames.return_value = [{'title': None, 'path': 'FAIL', 'image': 'TEST3'},
                                                       {'title': None, 'path': 'FAIL', 'image': 'TEST4'}]

    # init ListPreviewWidget and load service item
    list_preview_widget = ListPreviewWidget(mocked_parent, 1)

    # WHEN: replace_service_item is called
    with patch.object(list_preview_widget, 'viewport', mocked_viewport_obj), \
            patch.object(list_preview_widget, 'resizeRowsToContents'), \
            patch.object(list_preview_widget, 'setRowHeight'):
        list_preview_widget.replace_service_item(mocked_img_service_item, 200, 0)
        list_preview_widget.replace_service_item(mocked_cmd_service_item, 200, 0)


def test_replace_recalculate_layout_text(mocked_parent: QtWidgets.QWidget, mock_settings: MagicMock):
    """
    Test if "Max height for non-text slides..." enabled, txt slides unchanged in replace_service_item & __recalc...
    """
    # GIVEN: A setting to adjust "Max height for non-text slides in slide controller",
    #        a text ServiceItem and a ListPreviewWidget.

    # Mock Settings().value('advanced/slide max height')
    mock_settings.value.return_value = 100
    # Mock self.viewport().width()
    mocked_viewport_obj = MagicMock()
    mocked_viewport_obj.return_value.width.return_value = 200
    # Mock text service item
    service_item = MagicMock()
    service_item.is_text.return_value = True
    service_item.get_frames.return_value = [{'title': None, 'text': None, 'verseTag': None},
                                            {'title': None, 'text': None, 'verseTag': None}]
    # init ListPreviewWidget and load service item
    list_preview_widget = ListPreviewWidget(mocked_parent, 1)
    list_preview_widget.replace_service_item(service_item, 200, 0)
    # Change viewport width before forcing a resize
    mocked_viewport_obj.return_value.width.return_value = 400

    # WHEN: __recalculate_layout() is called (via resizeEvent)
    with patch.object(list_preview_widget, 'resizeRowsToContents') as mocked_resize_rows_to_contents, \
            patch.object(list_preview_widget, 'setRowHeight') as mocked_set_row_height, \
            patch.object(list_preview_widget, 'viewport', mocked_viewport_obj):
        list_preview_widget.resizeEvent(None)

    # THEN: setRowHeight() should not be called, while resizeRowsToContents() should be called twice
    #       (once each in __recalculate_layout and replace_service_item)
    assert mocked_resize_rows_to_contents.call_count == 1, 'Should be called'
    assert mocked_set_row_height.call_count == 0, 'Should not be called'


def test_replace_recalculate_layout_img(mocked_parent: QtWidgets.QWidget, mock_settings: MagicMock, clapperboard):
    """
    Test if "Max height for non-text slides..." disabled, img slides unchanged in replace_service_item & __recalc...
    """
    # GIVEN: A setting to adjust "Max height for non-text slides in slide controller",
    #        an image ServiceItem and a ListPreviewWidget.

    # Mock Settings().value('advanced/slide max height')
    mock_settings.value.return_value = 0
    # Mock self.viewport().width()
    mocked_viewport_obj = MagicMock()
    mocked_viewport_obj.return_value.width.return_value = 200
    # Mock image service item
    service_item = MagicMock()
    service_item.is_text.return_value = False
    service_item.is_capable.return_value = False
    service_item.get_frames.return_value = [{'title': None, 'path': None, 'image': clapperboard},
                                            {'title': None, 'path': None, 'image': clapperboard}]
    # init ListPreviewWidget and load service item
    list_preview_widget = ListPreviewWidget(mocked_parent, 1)
    list_preview_widget.replace_service_item(service_item, 200, 0)
    # Change viewport width before forcing a resize
    mocked_viewport_obj.return_value.width.return_value = 400

    # WHEN: __recalculate_layout() is called (via resizeEvent)
    with patch.object(list_preview_widget, 'resizeRowsToContents') as mocked_resize_rows_to_contents, \
            patch.object(list_preview_widget, 'setRowHeight') as mocked_set_row_height, \
            patch.object(list_preview_widget, 'viewport', mocked_viewport_obj):
        list_preview_widget.resizeEvent(None)
        mock_settings.value.return_value = None
        list_preview_widget.resizeEvent(None)

    # THEN: resizeRowsToContents() should not be called, while setRowHeight() should be called
    #       twice for each slide.
    assert mocked_resize_rows_to_contents.call_count == 0, 'Should not be called'
    assert mocked_set_row_height.call_count == 0, 'Should not be called'
    # calls = [call(0, 200), call(1, 200), call(0, 400), call(1, 400), call(0, 400), call(1, 400)]
    # mocked_setRowHeight.assert_has_calls(calls)


def test_replace_recalculate_layout_img_max(mocked_parent: QtWidgets.QWidget, mock_settings: MagicMock, clapperboard):
    """
    Test if "Max height for non-text slides..." enabled, img slides resized in replace_service_item & __recalc...
    """
    # GIVEN: A setting to adjust "Max height for non-text slides in slide controller",
    #        an image ServiceItem and a ListPreviewWidget.

    # Mock Settings().value('advanced/slide max height')
    mock_settings.value.return_value = 100
    # Mock self.viewport().width()
    mocked_viewport_obj = MagicMock()
    mocked_viewport_obj.return_value.width.return_value = 200
    # Mock image service item
    service_item = MagicMock()
    service_item.is_text.return_value = False
    service_item.is_capable.return_value = False
    service_item.get_frames.return_value = [{'title': None, 'path': None, 'image': clapperboard},
                                            {'title': None, 'path': None, 'image': clapperboard}]
    # init ListPreviewWidget and load service item
    list_preview_widget = ListPreviewWidget(mocked_parent, 1)
    list_preview_widget.replace_service_item(service_item, 200, 0)
    # Change viewport width before forcing a resize
    mocked_viewport_obj.return_value.width.return_value = 400

    # WHEN: __recalculate_layout() is called (via resizeEvent)
    with patch.object(list_preview_widget, 'resizeRowsToContents') as mocked_resize_rows_to_contents, \
            patch.object(list_preview_widget, 'setRowHeight') as mocked_set_row_height, \
            patch.object(list_preview_widget, 'viewport', mocked_viewport_obj):
        list_preview_widget.resizeEvent(None)

    # THEN: resizeRowsToContents() should not be called, while setRowHeight() should be called
    #       twice for each slide.
    assert mocked_resize_rows_to_contents.call_count == 0, 'Should not be called'
    assert mocked_set_row_height.call_count == 0, 'Should not be called'
    # calls = [call(0, 100), call(1, 100), call(0, 100), call(1, 100)]
    # mocked_setRowHeight.assert_has_calls(calls)


def test_replace_recalculate_layout_img_auto(mocked_parent: QtWidgets.QWidget, mock_settings: MagicMock, clapperboard):
    """
    Test if "Max height for non-text slides..." auto, img slides resized in replace_service_item & __recalc...
    """
    # GIVEN: A setting to adjust "Max height for non-text slides in slide controller",
    #        an image ServiceItem and a ListPreviewWidget.

    # Mock Settings().value('advanced/slide max height')
    mock_settings.value.return_value = -4
    # Mock self.viewport().width()
    mocked_viewport_obj = MagicMock()
    mocked_viewport_obj.return_value.width.return_value = 200
    mocked_viewport_obj.return_value.height.return_value = 600
    # Mock image service item
    service_item = MagicMock()
    service_item.is_text.return_value = False
    service_item.is_capable.return_value = False
    service_item.get_frames.return_value = [{'title': None, 'path': None, 'image': clapperboard},
                                            {'title': None, 'path': None, 'image': clapperboard}]
    # init ListPreviewWidget and load service item
    list_preview_widget = ListPreviewWidget(mocked_parent, 1)
    list_preview_widget.replace_service_item(service_item, 200, 0)
    # Change viewport width before forcing a resize
    mocked_viewport_obj.return_value.width.return_value = 400

    # WHEN: __recalculate_layout() is called (via screen_size_changed)
    with patch.object(list_preview_widget, 'resizeRowsToContents') as mocked_resize_rows_to_contents, \
            patch.object(list_preview_widget, 'setRowHeight') as mocked_set_row_height, \
            patch.object(list_preview_widget, 'viewport', mocked_viewport_obj):
        list_preview_widget.screen_size_changed(1)
        mocked_viewport_obj.height.return_value = 200
        list_preview_widget.screen_size_changed(1)

    # THEN: resizeRowsToContents() should not be called, while setRowHeight() should be called
    #       twice for each slide.
    assert mocked_resize_rows_to_contents.call_count == 0, 'Should not be called'
    assert mocked_set_row_height.call_count == 0, 'Should not be called'
    # calls = [call(0, 100), call(1, 100), call(0, 150), call(1, 150), call(0, 100), call(1, 100)]
    # mocked_setRowHeight.assert_has_calls(calls)


def test_row_resized_text(mocked_parent: QtWidgets.QWidget, mock_settings: MagicMock):
    """
    Test if "Max height for non-text slides..." enabled, text-based slides not affected in row_resized.
    """
    # GIVEN: A setting to adjust "Max height for non-text slides in slide controller",
    #        a text ServiceItem and a ListPreviewWidget.

    # Mock Settings().value('advanced/slide max height')
    mock_settings.value.return_value = 100
    # Mock self.viewport().width()
    mocked_viewport_obj = MagicMock()
    mocked_viewport_obj.return_value.width.return_value = 200
    # Mock text service item
    service_item = MagicMock()
    service_item.is_text.return_value = True
    service_item.get_frames.return_value = [{'title': None, 'text': None, 'verseTag': None},
                                            {'title': None, 'text': None, 'verseTag': None}]
    # Mock self.cellWidget().children().setMaximumWidth()
    mocked_cell_widget_child = MagicMock()
    mocked_cell_widget = MagicMock()
    mocked_cell_widget.return_value.children.return_value = [None, mocked_cell_widget_child]
    # init ListPreviewWidget and load service item
    list_preview_widget = ListPreviewWidget(mocked_parent, 1)
    list_preview_widget.replace_service_item(service_item, 200, 0)

    # WHEN: row_resized() is called
    with patch.object(list_preview_widget, 'resizeRowsToContents'), \
            patch.object(list_preview_widget, 'setRowHeight'), \
            patch.object(list_preview_widget, 'cellWidget', mocked_cell_widget), \
            patch.object(list_preview_widget, 'viewport', mocked_viewport_obj):
        list_preview_widget.row_resized(0, 100, 150)

    # THEN: self.cellWidget(row, 0).children()[1].setMaximumWidth() should not be called
    assert mocked_cell_widget_child.setMaximumWidth.call_count == 0, 'Should not be called'


def test_row_resized_img(mocked_parent: QtWidgets.QWidget, mock_settings: MagicMock, clapperboard):
    """
    Test if "Max height for non-text slides..." disabled, image-based slides not affected in row_resized.
    """
    # GIVEN: A setting to adjust "Max height for non-text slides in slide controller",
    #        an image ServiceItem and a ListPreviewWidget.

    # Mock Settings().value('advanced/slide max height')
    mock_settings.value.return_value = 0
    # Mock self.viewport().width()
    mocked_viewport_obj = MagicMock()
    mocked_viewport_obj.return_value.width.return_value = 200
    # Mock image service item
    service_item = MagicMock()
    service_item.is_text.return_value = False
    service_item.is_capable.return_value = False
    service_item.get_frames.return_value = [{'title': None, 'path': None, 'image': clapperboard},
                                            {'title': None, 'path': None, 'image': clapperboard}]
    # Mock self.cellWidget().children().setMaximumWidth()
    mocked_cell_widget_child = MagicMock()
    mocked_cell_widget = MagicMock()
    mocked_cell_widget.return_value.children.return_value = [None, mocked_cell_widget_child]
    # init ListPreviewWidget and load service item
    list_preview_widget = ListPreviewWidget(mocked_parent, 1)
    list_preview_widget.replace_service_item(service_item, 200, 0)

    # WHEN: row_resized() is called
    with patch.object(list_preview_widget, 'resizeRowsToContents'), \
            patch.object(list_preview_widget, 'setRowHeight'), \
            patch.object(list_preview_widget, 'cellWidget', mocked_cell_widget), \
            patch.object(list_preview_widget, 'viewport', mocked_viewport_obj):
        list_preview_widget.row_resized(0, 100, 150)
        mock_settings.value.return_value = None
        list_preview_widget.row_resized(0, 100, 150)

    # THEN: self.cellWidget(row, 0).children()[1].setMaximumWidth() should not be called
    assert mocked_cell_widget_child.setMaximumWidth.call_count == 0, 'Should not be called'


def test_row_resized_img_max(mocked_parent: QtWidgets.QWidget, mock_settings: MagicMock, clapperboard):
    """
    Test if "Max height for non-text slides..." enabled, image-based slides are scaled in row_resized.
    """
    # GIVEN: A setting to adjust "Max height for non-text slides in slide controller",
    #        an image ServiceItem and a ListPreviewWidget.

    # Mock Settings().value('advanced/slide max height')
    mock_settings.value.return_value = 100
    # Mock self.viewport().width()
    mock_settings.width.return_value = 200
    # Mock image service item
    service_item = MagicMock()
    service_item.is_text.return_value = False
    service_item.is_capable.return_value = False
    service_item.get_frames.return_value = [{'title': None, 'path': None, 'image': clapperboard},
                                            {'title': None, 'path': None, 'image': clapperboard}]
    # Mock self.cellWidget().children().setMaximumWidth()
    mocked_cell_widget_child = MagicMock()
    mocked_cell_widget = MagicMock()
    mocked_cell_widget.return_value.children.return_value = [None, mocked_cell_widget_child]
    # init ListPreviewWidget and load service item
    list_preview_widget = ListPreviewWidget(mocked_parent, 1)
    list_preview_widget.replace_service_item(service_item, 200, 0)

    # WHEN: row_resized() is called
    with patch.object(list_preview_widget, 'resizeRowsToContents'), \
            patch.object(list_preview_widget, 'setRowHeight'), \
            patch.object(list_preview_widget, 'cellWidget', mocked_cell_widget), \
            patch.object(list_preview_widget, 'viewport'):
        list_preview_widget.row_resized(0, 100, 150)

    # THEN: self.cellWidget(row, 0).children()[1].setMaximumWidth() should be called
    mocked_cell_widget_child.setMaximumWidth.assert_called_once_with(150)


def test_row_resized_setting_changed(mocked_parent: QtWidgets.QWidget, mock_settings: MagicMock, clapperboard):
    """
    Test if "Max height for non-text slides..." enabled while item live, program doesn't crash on row_resized.
    """
    # GIVEN: A setting to adjust "Max height for non-text slides in slide controller",
    #        an image ServiceItem and a ListPreviewWidget.

    # Mock Settings().value('advanced/slide max height')
    mock_settings.value.return_value = 0
    # Mock self.viewport().width()
    mocked_viewport_obj = MagicMock()
    mocked_viewport_obj.return_value.width.return_value = 200
    # Mock image service item
    service_item = MagicMock()
    service_item.is_text.return_value = False
    service_item.is_capable.return_value = False
    service_item.get_frames.return_value = [{'title': None, 'path': None, 'image': clapperboard},
                                            {'title': None, 'path': None, 'image': clapperboard}]
    # Mock self.cellWidget().children()
    mocked_cell_widget = MagicMock()
    mocked_cell_widget.return_value.children.return_value = None
    # init ListPreviewWidget and load service item
    list_preview_widget = ListPreviewWidget(mocked_parent, 1)
    list_preview_widget.replace_service_item(service_item, 200, 0)
    mock_settings.value.return_value = 100

    # WHEN: row_resized() is called
    with patch.object(list_preview_widget, 'resizeRowsToContents'), \
            patch.object(list_preview_widget, 'setRowHeight'), \
            patch.object(list_preview_widget, 'cellWidget', mocked_cell_widget), \
            patch.object(list_preview_widget, 'viewport', mocked_viewport_obj):
        list_preview_widget.row_resized(0, 100, 150)

    # THEN: self.cellWidget(row, 0).children()[1].setMaximumWidth() should fail
    # assert Exception


def test_autoscroll_setting_invalid(mocked_parent: QtWidgets.QWidget, mock_settings: MagicMock):
    """
    Test if 'advanced/autoscrolling' setting None or invalid, that no autoscrolling occurs on change_slide().
    """
    # GIVEN: A setting for autoscrolling and a ListPreviewWidget.
    # Mock Settings().value('advanced/autoscrolling')
    mock_settings.value.return_value = None
    # init ListPreviewWidget and load service item
    list_preview_widget = ListPreviewWidget(mocked_parent, 1)

    # WHEN: change_slide() is called
    with patch.object(list_preview_widget, 'selectRow') as mocked_select_row, \
            patch.object(list_preview_widget, 'scrollToItem') as mocked_scroll_to_item, \
            patch.object(list_preview_widget, 'item') as mocked_item, \
            patch.object(list_preview_widget, 'slide_count') as mocked_slide_count:
        mocked_slide_count.return_value = 1
        mocked_item.return_value = None
        list_preview_widget.change_slide(0)
        mock_settings.value.return_value = 1
        list_preview_widget.change_slide(0)
        mock_settings.value.return_value = {'fail': 1}
        list_preview_widget.change_slide(0)
        mock_settings.value.return_value = {'dist': 1, 'fail': 1}
        list_preview_widget.change_slide(0)
        mock_settings.value.return_value = {'dist': 'fail', 'pos': 1}
        list_preview_widget.change_slide(0)
        mock_settings.value.return_value = {'dist': 1, 'pos': 'fail'}
        list_preview_widget.change_slide(0)

    # THEN: no further functions should be called
    assert mocked_slide_count.call_count == 0, 'Should not be called'
    assert mocked_scroll_to_item.call_count == 0, 'Should not be called'
    assert mocked_select_row.call_count == 0, 'Should not be called'
    assert mocked_item.call_count == 0, 'Should not be called'


def test_autoscroll_dist_bounds(mocked_parent: QtWidgets.QWidget, mock_settings: MagicMock):
    """
    Test if 'advanced/autoscrolling' setting asks to scroll beyond list bounds, that it does not beyond.
    """
    # GIVEN: A setting for autoscrolling and a ListPreviewWidget.
    # Mock Settings().value('advanced/autoscrolling')
    mock_settings.value.return_value = {'dist': -1, 'pos': 1}
    # init ListPreviewWidget and load service item
    list_preview_widget = ListPreviewWidget(mocked_parent, 1)

    with patch.object(list_preview_widget, 'selectRow') as mocked_select_row, \
            patch.object(list_preview_widget, 'scrollToItem') as mocked_scroll_to_item, \
            patch.object(list_preview_widget, 'item') as mocked_item, \
            patch.object(list_preview_widget, 'slide_count') as mocked_slide_count:
        # Mocked returns
        mocked_slide_count.return_value = 1
        mocked_item.return_value = None
        # WHEN: change_slide() is called
        list_preview_widget.change_slide(0)
        mock_settings.value.return_value = {'dist': 1, 'pos': 1}
        list_preview_widget.change_slide(0)

    # THEN: no further functions should be called
    assert mocked_slide_count.call_count == 3, 'Should be called'
    assert mocked_scroll_to_item.call_count == 2, 'Should be called'
    assert mocked_select_row.call_count == 2, 'Should be called'
    assert mocked_item.call_count == 2, 'Should be called'
    mocked_item.assert_has_calls([call(0, 0), call(0, 0)])


def test_autoscroll_normal(mocked_parent: QtWidgets.QWidget, mock_settings: MagicMock):
    """
    Test if 'advanced/autoscrolling' setting valid, autoscrolling called as expected.
    """
    # GIVEN: A setting for autoscrolling and a ListPreviewWidget.
    # Mock Settings().value('advanced/autoscrolling')
    mock_settings.value.return_value = {'dist': -1, 'pos': 1}
    # init ListPreviewWidget and load service item
    list_preview_widget = ListPreviewWidget(mocked_parent, 1)

    with patch.object(list_preview_widget, 'selectRow') as mocked_select_row, \
            patch.object(list_preview_widget, 'scrollToItem') as mocked_scroll_to_item, \
            patch.object(list_preview_widget, 'item') as mocked_item, \
            patch.object(list_preview_widget, 'slide_count') as mocked_slide_count:
        # Mocked returns
        mocked_slide_count.return_value = 3
        mocked_item.return_value = None
        # WHEN: change_slide() is called
        list_preview_widget.change_slide(1)
        mock_settings.value.return_value = {'dist': 0, 'pos': 1}
        list_preview_widget.change_slide(1)
        mock_settings.value.return_value = {'dist': 1, 'pos': 1}
        list_preview_widget.change_slide(1)

    # THEN: no further functions should be called
    assert mocked_slide_count.call_count == 3, 'Should be called'
    assert mocked_scroll_to_item.call_count == 3, 'Should be called'
    assert mocked_select_row.call_count == 3, 'Should be called'
    assert mocked_item.call_count == 3, 'Should be called'
    mocked_item.assert_has_calls([call(0, 0), call(1, 0), call(2, 0)])


def test_treewidgetwithdnd_clear():
    """
    Test the clear method when called without any arguments.
    """
    # GIVEN: An instance of ListWidgetWithDnD
    widget = ListWidgetWithDnD()

    # WHEN: Calling clear with out any arguments
    widget.clear()

    # THEN: The results text should be the standard 'no results' text.
    assert widget.no_results_text == UiStrings().NoResults


def test_clear_search_while_typing():
    """
    Test the clear method when called with the search_while_typing argument set to True
    """
    # GIVEN: An instance of ListWidgetWithDnD
    widget = ListWidgetWithDnD()

    # WHEN: Calling clear with search_while_typing set to True
    widget.clear(search_while_typing=True)

    # THEN: The results text should be the 'short results' text.
    assert widget.no_results_text == UiStrings().ShortResults


def test_showevent_forces_layout_once():
    """
    Test that showEvent forces a relayout the first time the widget becomes visible, to fix rows added while the
    widget was hidden overlapping once shown, but does not force a relayout on subsequent show events.
    """
    # GIVEN: An instance of ListWidgetWithDnD
    widget = ListWidgetWithDnD()
    show_event = QtGui.QShowEvent()
    with patch.object(widget, 'doItemsLayout') as mocked_do_items_layout:

        # WHEN: showEvent fires for the first time
        widget.showEvent(show_event)

        # THEN: A relayout should have been forced, and the flag cleared
        mocked_do_items_layout.assert_called_once()
        assert widget._needs_initial_layout is False

        # WHEN: showEvent fires again
        widget.showEvent(show_event)

        # THEN: No additional relayout should have been forced
        mocked_do_items_layout.assert_called_once()


def test_all_items_no_list_items():
    """
    Test allItems when there are no items in the list widget
    """
    # GIVEN: An instance of ListWidgetWithDnD
    widget = ListWidgetWithDnD()
    with patch.object(widget, 'count', return_value=0), \
            patch.object(widget, 'item', side_effect=lambda x: [][x]):

        # WHEN: Calling allItems
        result = widget.allItems()

        # THEN: An instance of a Generator object should be returned. The generator should not yeild any results
        assert isinstance(result, GeneratorType)
        assert list(result) == []


def test_all_items_list_items():
    """
    Test allItems when the list widget contains some items.
    """
    # GIVEN: An instance of ListWidgetWithDnD
    widget = ListWidgetWithDnD()
    with patch.object(widget, 'count', return_value=2), \
            patch.object(widget, 'item', side_effect=lambda x: [5, 3][x]):

        # WHEN: Calling allItems
        result = widget.allItems()

        # THEN: An instance of a Generator object should be returned. The generator should not yeild any results
        assert isinstance(result, GeneratorType)
        assert list(result) == [5, 3]


def test_paint_event():
    """
    Test the paintEvent method when the list is not empty
    """
    # GIVEN: An instance of ListWidgetWithDnD with a mocked out count methode which returns 1
    #       (i.e the list has an item)
    widget = ListWidgetWithDnD()
    with patch('openlp.core.widgets.views.QtWidgets.QListWidget.paintEvent') as mocked_paint_event, \
            patch.object(widget, 'count', return_value=1), \
            patch.object(widget, 'viewport') as mocked_viewport:
        mocked_event = MagicMock()

        # WHEN: Calling paintEvent
        widget.paintEvent(mocked_event)

        # THEN: The overridden paintEvnet should have been called
        mocked_paint_event.assert_called_once_with(mocked_event)
        assert mocked_viewport.called is False


def test_paint_event_no_items():
    """
    Test the paintEvent method when the list is empty
    """
    # GIVEN: An instance of ListWidgetWithDnD with a mocked out count methode which returns 0
    #       (i.e the list is empty)
    widget = ListWidgetWithDnD()
    mocked_painter_instance = MagicMock()
    mocked_qrect = MagicMock()
    with patch('openlp.core.widgets.views.QtWidgets.QListWidget.paintEvent') as mocked_paint_event, \
            patch.object(widget, 'count', return_value=0), \
            patch.object(widget, 'viewport'), \
            patch('openlp.core.widgets.views.QtGui.QPainter',
                  return_value=mocked_painter_instance) as mocked_qpainter, \
            patch('openlp.core.widgets.views.QtCore.QRect', return_value=mocked_qrect):
        mocked_event = MagicMock()

        # WHEN: Calling paintEvent
        widget.paintEvent(mocked_event)

        # THEN: The overridden paintEvnet should have been called, and some text should be drawn.
        mocked_paint_event.assert_called_once_with(mocked_event)
        mocked_qpainter.assert_called_once_with(widget.viewport())
        mocked_painter_instance.drawText.assert_called_once_with(mocked_qrect, 4100, 'No Search Results')


def test_treewidgetwithdnd_constructor():
    """
    Test the constructor
    """
    # GIVEN: A TreeWidgetWithDnD
    # WHEN: An instance is created
    widget = TreeWidgetWithDnD(name='Test')

    # THEN: It should be initialised correctly
    assert widget.mime_data_text == 'Test'
    assert widget.allow_internal_dnd is False
    assert widget.indentation() == 0
    assert widget.isAnimated() is True


def test_initial_slide_count(preview_widget):
    """
    Test the initial slide count .
    """
    # GIVEN: A new ListPreviewWidget instance.
    # WHEN: No SlideItem has been added yet.
    # THEN: The count of items should be zero.
    assert preview_widget.slide_count() == 0, 'The slide list should be empty.'


def test_initial_slide_number(preview_widget):
    """
    Test the initial current slide number.
    """
    # GIVEN: A new ListPreviewWidget instance.
    # WHEN: No SlideItem has been added yet.
    # THEN: The number of the current item should be -1.
    assert preview_widget.current_slide_number() == -1, 'The slide number should be -1.'


def test_replace_service_item(preview_widget, state_media):
    """
    Test item counts and current number with a service item.
    """
    # GIVEN: A ServiceItem with two frames.
    service_item = ServiceItem(None)
    service = read_service_from_file('serviceitem_image_3.osj')
    with patch('os.path.exists') and patch('openlp.core.lib.serviceitem.sha256_file_hash', new=lambda x: "MockedHash"):
        service_item.set_from_service(service[0])
    # WHEN: Added to the preview widget.
    preview_widget.replace_service_item(service_item, 1, 1)
    # THEN: The slide count and number should fit.
    assert preview_widget.slide_count() == 2, 'The slide count should be 2.'
    assert preview_widget.current_slide_number() == 1, 'The current slide number should  be 1.'


def test_change_slide(preview_widget, state_media):
    """
    Test the change_slide method.
    """
    # GIVEN: A ServiceItem with two frames content.
    service_item = ServiceItem(None)
    service = read_service_from_file('serviceitem_image_3.osj')
    with patch('os.path.exists') and patch('openlp.core.lib.serviceitem.sha256_file_hash', new=lambda x: "MockedHash"):
        service_item.set_from_service(service[0])
    # WHEN: Added to the preview widget and switched to the second frame.
    preview_widget.replace_service_item(service_item, 1, 0)
    preview_widget.change_slide(1)
    # THEN: The current_slide_number should reflect the change.
    assert preview_widget.current_slide_number() == 1, 'The current slide number should  be 1.'


@pytest.mark.parametrize('verse_tag,expected_color', [
    ('V1', NOIR_VERSE_VERSE),
    ('C2', NOIR_VERSE_CHORUS),
    ('O1', None),
    ('4', None),
    (None, None),
    ('', None),
])
def test_noir_slide_delegate_verse_tag_color(verse_tag, expected_color):
    """_verse_tag_color should tint known verse-type letters and fall back to None otherwise"""
    # GIVEN: A NoirSlideDelegate
    delegate = NoirSlideDelegate(QtWidgets.QWidget())

    # WHEN: Asking for the color of a verse tag
    color = delegate._verse_tag_color(verse_tag)

    # THEN: Known verse-type letters resolve to their tint, everything else is None
    assert color == expected_color


@pytest.mark.parametrize('plugin_name,expected_accent', [
    ('songs', NOIR_PLUGIN_SONGS),
    ('unknown_plugin', None),
    (None, None),
])
def test_noir_service_delegate_chip_colors(plugin_name, expected_accent):
    """_chip_colors should tint known plugins and fall back to the neutral chip colors otherwise"""
    # GIVEN: A NoirServiceDelegate
    delegate = NoirServiceDelegate(QtWidgets.QWidget())

    # WHEN: Asking for the chip colors of a plugin
    fill, border = delegate._chip_colors(plugin_name)

    # THEN: A known plugin gets its accent tinted in, otherwise the neutral ink colors are used
    if expected_accent:
        assert fill.name(QtGui.QColor.NameFormat.HexRgb) == expected_accent.lower()
        assert fill.alpha() == 40
        assert border.alpha() == 130
    else:
        assert fill == QtGui.QColor(NOIR_INK_3)
        assert border == QtGui.QColor(NOIR_INK_4)
