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
Test the ThemeForm class and related methods.
"""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from PySide6 import QtCore

from openlp.core.common.registry import Registry
from openlp.core.lib.theme import BackgroundType
from openlp.core.ui.themeform import ThemeForm


def _make_path(s):
    return MagicMock(**{'__str__.return_value': s, 'exists.return_value': True})


THEME_BACKGROUNDS = {
    'solid': [
        ('color', 'background_color', '#ff0')
    ],
    'gradient': [
        ('gradient_type', 'background_direction', 'horizontal'),
        ('gradient_start', 'background_start_color', '#fff'),
        ('gradient_end', 'background_end_color', '#000')
    ],
    'image': [
        ('image_color', 'background_border_color', '#f0f0f0'),
        ('image_path', 'background_source', '/path/to/image.png'),
        ('image_path', 'background_filename', '/path/to/image.png')
    ],
    'video': [
        ('video_color', 'background_border_color', '#222'),
        ('video_path', 'background_source', '/path/to/video.mkv'),
        ('video_path', 'background_filename', '/path/to/video.mkv')
    ],
    'stream': [
        ('stream_color', 'background_border_color', '#222'),
        ('stream_mrl', 'background_source', 'http:/127.0.0.1/stream.mkv'),
        ('stream_mrl', 'background_filename', 'http:/127.0.0.1/stream.mkv')
    ]
}


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_create_theme_wizard(mocked_setup, settings):
    """
    Test creating a ThemeForm instance
    """
    # GIVEN: A ThemeForm class
    # WHEN: An object is created
    # THEN: There should be no problems
    ThemeForm(None)


def test_setup(settings):
    """
    Test the _setup method
    """
    # GIVEN: A ThemeForm instance
    with patch('openlp.core.ui.themeform.ThemeForm._setup'):
        theme_form = ThemeForm(None)
    theme_form.setup_ui = MagicMock()
    theme_form.background_page = MagicMock()
    theme_form.main_area_page = MagicMock()
    theme_form.footer_area_page = MagicMock()
    theme_form.alignment_page = MagicMock()
    theme_form.area_position_page = MagicMock()

    # WHEN: _setup() is called
    theme_form._setup()

    # THEN: The right calls should have been made
    theme_form.setup_ui.assert_called_once_with(theme_form)
    assert theme_form.can_update_theme is True
    assert theme_form.temp_background_filename is None
    theme_form.main_area_page.font_name_changed.connect.assert_any_call(theme_form.calculate_lines)
    theme_form.main_area_page.font_size_changed.connect.assert_any_call(theme_form.calculate_lines)
    theme_form.main_area_page.line_spacing_changed.connect.assert_any_call(theme_form.calculate_lines)
    theme_form.main_area_page.letter_spacing_changed.connect.assert_any_call(theme_form.calculate_lines)
    theme_form.main_area_page.is_outline_enabled_changed.connect.assert_any_call(
        theme_form.on_outline_toggled)
    theme_form.main_area_page.outline_size_changed.connect.assert_any_call(theme_form.calculate_lines)
    theme_form.main_area_page.is_shadow_enabled_changed.connect.assert_any_call(
        theme_form.on_shadow_toggled)
    theme_form.main_area_page.shadow_size_changed.connect.assert_any_call(theme_form.calculate_lines)
    theme_form.footer_area_page.font_name_changed.connect.assert_any_call(theme_form.calculate_lines)
    theme_form.footer_area_page.font_size_changed.connect.assert_any_call(theme_form.calculate_lines)
    theme_form.footer_area_page.wrap_changed.connect.assert_any_call(theme_form.calculate_lines)
    theme_form.footer_area_page.line_spacing_changed.connect.assert_any_call(theme_form.calculate_lines)
    theme_form.footer_area_page.letter_spacing_changed.connect.assert_any_call(theme_form.calculate_lines)
    # The always-on live preview: page-level `changed` signals and the font pages' granular `*_changed`
    # signals should all be wired up to schedule a debounced preview refresh.
    assert isinstance(theme_form.preview_update_timer, QtCore.QTimer)
    assert theme_form.preview_update_timer.isSingleShot()
    assert theme_form.preview_update_timer.interval() == 500
    theme_form.background_page.changed.connect.assert_called_once_with(theme_form.schedule_preview_update)
    theme_form.alignment_page.changed.connect.assert_called_once_with(theme_form.schedule_preview_update)
    theme_form.area_position_page.changed.connect.assert_called_once_with(theme_form.schedule_preview_update)
    for font_page in (theme_form.main_area_page, theme_form.footer_area_page):
        font_page.font_name_changed.connect.assert_any_call(theme_form.schedule_preview_update)
        font_page.font_color_changed.connect.assert_called_once_with(theme_form.schedule_preview_update)
        font_page.is_bold_changed.connect.assert_called_once_with(theme_form.schedule_preview_update)
        font_page.is_italic_changed.connect.assert_called_once_with(theme_form.schedule_preview_update)
        font_page.font_size_changed.connect.assert_any_call(theme_form.schedule_preview_update)
        font_page.wrap_changed.connect.assert_any_call(theme_form.schedule_preview_update)
        font_page.line_spacing_changed.connect.assert_any_call(theme_form.schedule_preview_update)
        font_page.letter_spacing_changed.connect.assert_any_call(theme_form.schedule_preview_update)
        font_page.is_outline_enabled_changed.connect.assert_any_call(theme_form.schedule_preview_update)
        font_page.outline_color_changed.connect.assert_called_once_with(theme_form.schedule_preview_update)
        font_page.outline_size_changed.connect.assert_any_call(theme_form.schedule_preview_update)
        font_page.is_shadow_enabled_changed.connect.assert_any_call(theme_form.schedule_preview_update)
        font_page.shadow_color_changed.connect.assert_called_once_with(theme_form.schedule_preview_update)
        font_page.shadow_size_changed.connect.assert_any_call(theme_form.schedule_preview_update)


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_set_defaults(mocked_setup, settings):
    """
    Test that the right methods are called by the set_defaults() method
    """
    # GIVEN: A ThemeForm instance with mocked methods
    theme_form = ThemeForm(None)
    theme_form.restart = MagicMock()
    theme_form.set_background_page_values = MagicMock()
    theme_form.set_main_area_page_values = MagicMock()
    theme_form.set_footer_area_page_values = MagicMock()
    theme_form.set_alignment_page_values = MagicMock()
    theme_form.set_position_page_values = MagicMock()
    theme_form.set_preview_page_values = MagicMock()

    # WHEN: set_defaults() is called
    theme_form.set_defaults()

    # THEN: all the mocks are called
    theme_form.restart.assert_called_once()
    theme_form.set_background_page_values.assert_called_once()
    theme_form.set_main_area_page_values.assert_called_once()
    theme_form.set_footer_area_page_values.assert_called_once()
    theme_form.set_alignment_page_values.assert_called_once()
    theme_form.set_position_page_values.assert_called_once()
    theme_form.set_preview_page_values.assert_called_once()


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_calculate_lines(mocked_setup, settings):
    """
    Test the calculate_lines() method
    """
    # GIVEN: A ThemeForm instance with some mocked methods
    theme_form = ThemeForm(None)
    theme_form.theme = None
    theme_form.welcome_page = None
    theme_form.currentPage = MagicMock()
    theme_form.update_theme = MagicMock()
    mocked_theme_manager = MagicMock()
    Registry().register('theme_manager', mocked_theme_manager)

    # WHEN: calculate_lines() is called
    theme_form.calculate_lines()

    # THEN: The mocks should have been called correctly
    theme_form.currentPage.assert_called_once()
    theme_form.update_theme.assert_called_once()
    mocked_theme_manager.generate_image.assert_called_once_with(None, True)


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_update_lines_text(mocked_setup, settings):
    """
    Test the update_lines_text() method
    """
    # GIVEN: A ThemeForm instance with some mocked methods
    theme_form = ThemeForm(None)
    theme_form.main_line_count_label = MagicMock()

    # WHEN: calculate_lines() is called
    theme_form.update_lines_text(10)

    # THEN: The mocks should have been called correctly
    theme_form.main_line_count_label.setText.assert_called_once_with('(approximately 10 lines per slide)')


@patch('openlp.core.ui.themeform.QtWidgets.QWizard.resizeEvent')
@patch('openlp.core.ui.themeform.QtGui.QResizeEvent')
@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_resize_event(mocked_setup, MockResizeEvent, mocked_resizeEvent, settings):
    """
    Test that the resizeEvent method handles resizing correctly
    """
    # GIVEN: A ThemeForm instance with a number of mocked methods
    mocked_event = MagicMock()
    MockResizeEvent.return_value = mocked_event
    theme_form = ThemeForm(None)
    theme_form.size = MagicMock(return_value=1920)
    theme_form.preview_area_layout = MagicMock()
    theme_form.preview_box = MagicMock(**{'width.return_value': 300})
    mocked_renderer = MagicMock(**{'width.return_value': 1920, 'height.return_value': 1080})
    Registry().remove('renderer')
    Registry().register('renderer', mocked_renderer)

    # WHEN: resizeEvent() is called
    theme_form.resizeEvent()

    # THEN: The correct calls should have been made
    MockResizeEvent.assert_called_once_with(1920, 1920)
    mocked_resizeEvent.assert_called_once_with(theme_form, mocked_event)
    assert mocked_renderer.width.call_count == 2
    mocked_renderer.height.assert_called_once()
    theme_form.preview_area_layout.set_aspect_ratio.assert_called_once_with(16 / 9)
    theme_form.preview_box.set_scale.assert_called_once_with(float(300 / 1920))


@patch('openlp.core.ui.themeform.QtWidgets.QWizard.resizeEvent')
@patch('openlp.core.ui.themeform.QtGui.QResizeEvent')
@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_resize_event_dbze(mocked_setup, MockResizeEvent, mocked_resizeEvent, settings):
    """
    Test that the resizeEvent method handles a divide by zero exception correctly
    """
    # GIVEN: A ThemeForm instance with a number of mocked methods
    mocked_event = MagicMock()
    MockResizeEvent.return_value = mocked_event
    theme_form = ThemeForm(None)
    theme_form.size = MagicMock(return_value=1920)
    theme_form.preview_area_layout = MagicMock()
    theme_form.preview_box = MagicMock(**{'width.return_value': 300})
    mocked_renderer = MagicMock(**{'width.return_value': 1920, 'height.return_value': 0})
    Registry().remove('renderer')
    Registry().register('renderer', mocked_renderer)

    # WHEN: resizeEvent() is called
    theme_form.resizeEvent()

    # THEN: The correct calls should have been made
    MockResizeEvent.assert_called_once_with(1920, 1920)
    mocked_resizeEvent.assert_called_once_with(theme_form, mocked_event)
    assert mocked_renderer.width.call_count == 2
    mocked_renderer.height.assert_called_once()
    theme_form.preview_area_layout.set_aspect_ratio.assert_called_once_with(1)
    theme_form.preview_box.set_scale.assert_called_once_with(float(300 / 1920))


@patch('openlp.core.ui.themeform.QtWidgets.QMessageBox.critical')
@patch('openlp.core.ui.themeform.is_not_image_file')
@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_validate_current_page_with_image(mocked_setup, mocked_is_not_image_file, mocked_critical, settings):
    """
    Test the validateCurrentPage() method
    """
    # GIVEN: An instance of ThemeForm with some mocks
    theme_form = ThemeForm(None)
    theme_form.background_page = MagicMock(background_type=BackgroundType.to_string(BackgroundType.Image),
                                           image_path=Path('picture.jpg'))
    theme_form.page = MagicMock(return_value=theme_form.background_page)
    mocked_is_not_image_file.return_value = True

    # WHEN: validateCurrentPage() is called
    result = theme_form.validateCurrentPage()

    # THEN: The right methods were called, and the result is False
    mocked_critical.assert_called_once_with(theme_form, 'Background Image Empty',
                                            'You have not selected a background image. '
                                            'Please select one before continuing.')
    assert result is False


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_validate_current_page(mocked_setup, settings):
    """
    Test the validateCurrentPage() method
    """
    # GIVEN: An instance of ThemeForm with some mocks
    theme_form = ThemeForm(None)
    theme_form.background_page = MagicMock()
    theme_form.page = MagicMock()

    # WHEN: validateCurrentPage() is called
    result = theme_form.validateCurrentPage()

    # THEN: The right methods were called, and the result is False
    assert result is True


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_on_current_id_changed_preview(mocked_setup, settings):
    """
    Test the on_current_id_changed() method refreshes the live preview immediately when landing on any
    non-welcome page.
    """
    # GIVEN: An instance of ThemeForm with some mocks
    theme_form = ThemeForm(None)
    theme_form.theme = 'my fake theme'
    theme_form.welcome_page = MagicMock()
    theme_form.area_position_page = MagicMock()
    theme_form.preview_page = MagicMock()
    theme_form.page = MagicMock(return_value=theme_form.preview_page)
    theme_form.update_theme = MagicMock()
    theme_form.preview_box = MagicMock(**{'width.return_value': 300})
    theme_form.preview_area = MagicMock()
    theme_form.preview_area_layout = MagicMock()
    theme_form.resizeEvent = MagicMock()
    theme_form._is_refreshing_preview = False
    theme_form.currentPage = MagicMock(return_value=theme_form.preview_page)
    mocked_renderer = MagicMock(**{'width.return_value': 1920, 'height.return_value': 0})
    Registry().remove('renderer')
    Registry().register('renderer', mocked_renderer)

    # WHEN: on_current_id_changed() is called for any page other than the welcome page
    theme_form.on_current_id_changed(1)

    # THEN: The preview panel should be shown, and the live preview should have been refreshed immediately
    theme_form.preview_area.setVisible.assert_called_once_with(True)
    theme_form.update_theme.assert_called_once()
    theme_form.resizeEvent.assert_called_once()
    theme_form.preview_box.clear_slides.assert_called_once()
    theme_form.preview_box.show.assert_called_once()
    theme_form.preview_box.generate_preview.assert_called_once_with('my fake theme', False, False)


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_on_current_id_changed_welcome_page_skips_refresh(mocked_setup, settings):
    """
    Test that on_current_id_changed() hides the preview panel and does not refresh it when landing on the
    welcome page.
    """
    # GIVEN: An instance of ThemeForm with some mocks, currently on the welcome page
    theme_form = ThemeForm(None)
    theme_form.welcome_page = MagicMock()
    theme_form.page = MagicMock(return_value=theme_form.welcome_page)
    theme_form.preview_area = MagicMock()
    theme_form._refresh_live_preview = MagicMock()

    # WHEN: on_current_id_changed() is called
    theme_form.on_current_id_changed(0)

    # THEN: The preview panel should be hidden and not refreshed
    theme_form.preview_area.setVisible.assert_called_once_with(False)
    theme_form._refresh_live_preview.assert_not_called()


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_schedule_preview_update_starts_timer(mocked_setup, settings):
    """
    Test that schedule_preview_update() (re)starts the debounce timer when not on the welcome page.
    """
    # GIVEN: An instance of ThemeForm not on the welcome page
    theme_form = ThemeForm(None)
    theme_form.welcome_page = MagicMock()
    theme_form.currentPage = MagicMock(return_value=MagicMock())
    theme_form.preview_update_timer = MagicMock()

    # WHEN: schedule_preview_update() is called
    theme_form.schedule_preview_update()

    # THEN: The debounce timer should have been (re)started
    theme_form.preview_update_timer.start.assert_called_once()


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_schedule_preview_update_skips_on_welcome_page(mocked_setup, settings):
    """
    Test that schedule_preview_update() does nothing while on the welcome page.
    """
    # GIVEN: An instance of ThemeForm on the welcome page
    theme_form = ThemeForm(None)
    theme_form.welcome_page = MagicMock()
    theme_form.currentPage = MagicMock(return_value=theme_form.welcome_page)
    theme_form.preview_update_timer = MagicMock()

    # WHEN: schedule_preview_update() is called
    theme_form.schedule_preview_update()

    # THEN: The debounce timer should not have been started
    theme_form.preview_update_timer.start.assert_not_called()


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_refresh_live_preview_reentrancy_guard(mocked_setup, settings):
    """
    Test that _refresh_live_preview() no-ops if it's already in the middle of refreshing.
    """
    # GIVEN: An instance of ThemeForm that is already refreshing the preview
    theme_form = ThemeForm(None)
    theme_form.welcome_page = MagicMock()
    theme_form.currentPage = MagicMock(return_value=MagicMock())
    theme_form._is_refreshing_preview = True
    theme_form.update_theme = MagicMock()

    # WHEN: _refresh_live_preview() is called
    theme_form._refresh_live_preview()

    # THEN: Nothing should have happened
    theme_form.update_theme.assert_not_called()


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_on_outline_toggled(mocked_setup, settings):
    """
    Test the on_outline_toggled() method
    """
    # GIVEN: An instance of ThemeForm with some mocks
    theme_form = ThemeForm(None)
    theme_form.can_update_theme = True
    theme_form.theme = MagicMock()
    theme_form.calculate_lines = MagicMock()

    # WHEN: on_outline_toggled is called
    theme_form.on_outline_toggled(True)

    # THEN: Everything is working right
    assert theme_form.theme.font_main_outline is True
    theme_form.calculate_lines.assert_called_once()


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_on_shadow_toggled(mocked_setup, settings):
    """
    Test the on_shadow_toggled() method
    """
    # GIVEN: An instance of ThemeForm with some mocks
    theme_form = ThemeForm(None)
    theme_form.can_update_theme = True
    theme_form.theme = MagicMock()
    theme_form.calculate_lines = MagicMock()

    # WHEN: on_shadow_toggled is called
    theme_form.on_shadow_toggled(True)

    # THEN: Everything is working right
    assert theme_form.theme.font_main_shadow is True
    theme_form.calculate_lines.assert_called_once()


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_initialise_page_background(mocked_setup, settings):
    """
    Test the initializePage() method with the background page
    """
    # GIVEN: An instance of ThemeForm with some mocks
    theme_form = ThemeForm(None)
    theme_form.background_page = MagicMock()
    theme_form.page = MagicMock(return_value=theme_form.background_page)
    theme_form.set_background_page_values = MagicMock()

    # WHEN: on_shadow_toggled is called
    theme_form.initializePage(0)

    # THEN: Everything is working right
    theme_form.set_background_page_values.assert_called_once()


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_initialise_page_main_area(mocked_setup, settings):
    """
    Test the initializePage() method with the main_area page
    """
    # GIVEN: An instance of ThemeForm with some mocks
    theme_form = ThemeForm(None)
    theme_form.background_page = MagicMock()
    theme_form.main_area_page = MagicMock()
    theme_form.page = MagicMock(return_value=theme_form.main_area_page)
    theme_form.set_main_area_page_values = MagicMock()

    # WHEN: on_shadow_toggled is called
    theme_form.initializePage(0)

    # THEN: Everything is working right
    theme_form.set_main_area_page_values.assert_called_once()


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_initialise_page_footer_area(mocked_setup, settings):
    """
    Test the initializePage() method with the footer_area page
    """
    # GIVEN: An instance of ThemeForm with some mocks
    theme_form = ThemeForm(None)
    theme_form.background_page = MagicMock()
    theme_form.main_area_page = MagicMock()
    theme_form.footer_area_page = MagicMock()
    theme_form.page = MagicMock(return_value=theme_form.footer_area_page)
    theme_form.set_footer_area_page_values = MagicMock()

    # WHEN: on_shadow_toggled is called
    theme_form.initializePage(0)

    # THEN: Everything is working right
    theme_form.set_footer_area_page_values.assert_called_once()


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_initialise_page_alignment(mocked_setup, settings):
    """
    Test the initializePage() method with the alignment page
    """
    # GIVEN: An instance of ThemeForm with some mocks
    theme_form = ThemeForm(None)
    theme_form.background_page = MagicMock()
    theme_form.main_area_page = MagicMock()
    theme_form.footer_area_page = MagicMock()
    theme_form.alignment_page = MagicMock()
    theme_form.page = MagicMock(return_value=theme_form.alignment_page)
    theme_form.set_alignment_page_values = MagicMock()

    # WHEN: on_shadow_toggled is called
    theme_form.initializePage(0)

    # THEN: Everything is working right
    theme_form.set_alignment_page_values.assert_called_once()


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_initialise_page_area_position(mocked_setup, settings):
    """
    Test the initializePage() method with the area_position page
    """
    # GIVEN: An instance of ThemeForm with some mocks
    theme_form = ThemeForm(None)
    theme_form.background_page = MagicMock()
    theme_form.main_area_page = MagicMock()
    theme_form.footer_area_page = MagicMock()
    theme_form.alignment_page = MagicMock()
    theme_form.area_position_page = MagicMock()
    theme_form.page = MagicMock(return_value=theme_form.area_position_page)
    theme_form.set_position_page_values = MagicMock()

    # WHEN: on_shadow_toggled is called
    theme_form.initializePage(0)

    # THEN: Everything is working right
    theme_form.set_position_page_values.assert_called_once()


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_update_theme_static(mocked_setup, settings):
    """
    Test that the update_theme() method correctly sets all the "static" theme variables
    """
    # GIVEN: An instance of a ThemeForm with some mocked out pages which return certain values
    theme_form = ThemeForm(None)
    theme_form.can_update_theme = True
    theme_form.theme = MagicMock()
    theme_form.background_page = MagicMock()
    theme_form.main_area_page = MagicMock(font_name='Montserrat', font_color='#f00', font_size=50, line_spacing=12,
                                          is_outline_enabled=True, outline_color='#00f', outline_size=3,
                                          is_shadow_enabled=True, shadow_color='#111', shadow_size=5, is_bold=True,
                                          is_italic=False, letter_spacing=2)
    theme_form.footer_area_page = MagicMock(font_name='Oxygen', font_color='#fff', font_size=20, wrap=False,
                                            is_bold=False, is_italic=True, line_spacing=2, letter_spacing=-1)
    theme_form.alignment_page = MagicMock(horizontal_align='left', vertical_align='top', is_transition_enabled=True,
                                          transition_type='fade', transition_speed='normal',
                                          transition_direction='horizontal', is_transition_reverse_enabled=False)
    theme_form.area_position_page = MagicMock(use_main_default_location=True, use_footer_default_location=True)

    # WHEN: ThemeForm.update_theme() is called
    theme_form.update_theme()

    # THEN: The theme should be correct
    # Main area
    assert theme_form.theme.font_main_name == 'Montserrat'
    assert theme_form.theme.font_main_color == '#f00'
    assert theme_form.theme.font_main_size == 50
    assert theme_form.theme.font_main_line_adjustment == 12
    assert theme_form.theme.font_main_letter_adjustment == 2
    assert theme_form.theme.font_main_outline is True
    assert theme_form.theme.font_main_outline_color == '#00f'
    assert theme_form.theme.font_main_outline_size == 3
    assert theme_form.theme.font_main_shadow is True
    assert theme_form.theme.font_main_shadow_color == '#111'
    assert theme_form.theme.font_main_shadow_size == 5
    assert theme_form.theme.font_main_bold is True
    assert theme_form.theme.font_main_italics is False
    assert theme_form.theme.font_main_override is False
    theme_form.theme.set_default_header.assert_called_once_with()
    # Footer
    assert theme_form.theme.font_footer_name == 'Oxygen'
    assert theme_form.theme.font_footer_color == '#fff'
    assert theme_form.theme.font_footer_size == 20
    assert theme_form.theme.font_footer_wrap is False
    assert theme_form.theme.font_footer_bold is False
    assert theme_form.theme.font_footer_italics is True
    assert theme_form.theme.font_footer_override is False
    assert theme_form.theme.font_footer_line_adjustment == 2
    assert theme_form.theme.font_footer_letter_adjustment == -1
    theme_form.theme.set_default_footer.assert_called_once_with()
    # Alignment
    assert theme_form.theme.display_horizontal_align == 'left'
    assert theme_form.theme.display_vertical_align == 'top'
    # Transitions
    assert theme_form.theme.display_slide_transition is True
    assert theme_form.theme.display_slide_transition_type == 'fade'
    assert theme_form.theme.display_slide_transition_direction == 'horizontal'
    assert theme_form.theme.display_slide_transition_speed == 'normal'
    assert theme_form.theme.display_slide_transition_reverse is False


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_update_theme_overridden_areas(mocked_setup, settings):
    """
    Test that the update_theme() method correctly sets all the positioning information for a custom position
    """
    # GIVEN: An instance of a ThemeForm with some mocked out pages which return certain values
    theme_form = ThemeForm(None)
    theme_form.can_update_theme = True
    theme_form.theme = MagicMock()
    theme_form.background_page = MagicMock()
    theme_form.main_area_page = MagicMock()
    theme_form.footer_area_page = MagicMock()
    theme_form.alignment_page = MagicMock()
    theme_form.area_position_page = MagicMock(use_main_default_location=False, use_footer_default_location=False,
                                              main_x=20, main_y=50, main_height=900, main_width=1880,
                                              footer_x=20, footer_y=910, footer_height=70, footer_width=1880)

    # WHEN: ThemeForm.update_theme() is called
    theme_form.update_theme()

    # THEN: The theme should be correct
    assert theme_form.theme.font_main_override is True
    assert theme_form.theme.font_main_x == 20
    assert theme_form.theme.font_main_y == 50
    assert theme_form.theme.font_main_height == 900
    assert theme_form.theme.font_main_width == 1880
    assert theme_form.theme.font_footer_override is True
    assert theme_form.theme.font_footer_x == 20
    assert theme_form.theme.font_footer_y == 910
    assert theme_form.theme.font_footer_height == 70
    assert theme_form.theme.font_footer_width == 1880


@pytest.mark.parametrize('background_type', THEME_BACKGROUNDS.keys())
@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_update_theme_background(mocked_setup, background_type, settings):
    """
    Test that the update_theme() method correctly sets all the theme background variables for each background type
    """
    # GIVEN: An instance of a ThemeForm with some mocked out pages which return certain values
    page_props = {page_prop: value for page_prop, _, value in THEME_BACKGROUNDS[background_type]}
    theme_form = ThemeForm(None)
    theme_form.can_update_theme = True
    theme_form.theme = MagicMock()
    theme_form.background_page = MagicMock(background_type=background_type, **page_props)
    theme_form.main_area_page = MagicMock()
    theme_form.footer_area_page = MagicMock()
    theme_form.alignment_page = MagicMock()
    theme_form.area_position_page = MagicMock()

    # WHEN: ThemeForm.update_theme() is called
    theme_form.update_theme()

    # THEN: The theme should be correct
    for _, theme_prop, value in THEME_BACKGROUNDS[background_type]:
        assert getattr(theme_form.theme, theme_prop) == value, f'{theme_prop} should have been {value}'


@pytest.mark.skip('Being a bit problematic right now')
@pytest.mark.parametrize('background_type', THEME_BACKGROUNDS.keys())
@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_set_background_page_values(mocked_setup, background_type, settings):
    """
    Test that the set_background_page_values() method sets the background page values correctly
    """
    # GIVEN: An instance of a ThemeForm with some mocked out pages and a mocked theme with values
    theme_props = {theme_prop: value for _, theme_prop, value in THEME_BACKGROUNDS[background_type]}
    theme_form = ThemeForm(None)
    theme_form.theme = MagicMock(background_type=background_type, **theme_props)
    theme_form.background_page = MagicMock()
    theme_form.main_area_page = MagicMock()
    theme_form.footer_area_page = MagicMock()
    theme_form.alignment_page = MagicMock()
    theme_form.area_position_page = MagicMock()

    # WHEN: set_background_page_values() is called
    theme_form.set_background_page_values()

    # THEN: The correct values are set on the page
    for page_prop, _, value in THEME_BACKGROUNDS[background_type]:
        assert getattr(theme_form.background_page, page_prop) == value, (
            f'{page_prop} should have been {value} but was {getattr(theme_form.background_page, page_prop)}'
        )


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_set_background_page_values_does_not_leak_stale_colors(mocked_setup, settings):
    """
    Test that set_background_page_values() resets *all* background-type fields (solid color, gradient
    colors, image/video/stream border colors) every time, not just the ones belonging to the theme's
    current background type. The background page's widgets are shared across every Add/Edit Theme
    invocation, so previously this left colors from a completely different, previously-edited theme
    behind - causing a newly created theme to show/save the wrong color (regression test).
    """
    # GIVEN: A ThemeForm whose background page still holds "solid: red" values from editing a previous
    # theme, and a brand new theme that only cares about the gradient colors
    theme_form = ThemeForm(None)
    theme_form.background_page = MagicMock(color='#ff0000')
    theme_form.main_area_page = MagicMock()
    theme_form.footer_area_page = MagicMock()
    theme_form.alignment_page = MagicMock()
    theme_form.area_position_page = MagicMock()
    theme_form.theme = MagicMock(
        background_type='gradient', background_color='#000000', background_start_color='#111111',
        background_end_color='#222222', background_direction='vertical', background_border_color='#333333',
        background_source=None, background_filename=None)

    # WHEN: set_background_page_values() is called for the new theme
    theme_form.set_background_page_values()

    # THEN: every color field is refreshed from the new theme, including the ones for background types
    # other than "gradient" - the stale "red" solid color must not survive
    assert theme_form.background_page.color == '#000000'
    assert theme_form.background_page.gradient_start == '#111111'
    assert theme_form.background_page.gradient_end == '#222222'
    assert theme_form.background_page.image_color == '#333333'
    assert theme_form.background_page.video_color == '#333333'
    assert theme_form.background_page.stream_color == '#333333'


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_set_background_page_values_image_theme_does_not_crash_stream_mrl(mocked_setup, settings):
    """
    Test that set_background_page_values() doesn't crash for an image/video theme. background_source is a
    Path in that case, and the stream MRL field is a plain QLineEdit that only accepts strings - previously
    unconditionally assigning background_source to stream_mrl raised a TypeError for non-stream themes
    (regression test).
    """
    # GIVEN: A theme with an image background (background_source is a Path, not a str)
    theme_form = ThemeForm(None)
    theme_form.background_page = MagicMock()
    theme_form.main_area_page = MagicMock()
    theme_form.footer_area_page = MagicMock()
    theme_form.alignment_page = MagicMock()
    theme_form.area_position_page = MagicMock()
    theme_form.theme = MagicMock(
        background_type='image', background_color='#000000', background_start_color='#111111',
        background_end_color='#222222', background_direction='vertical', background_border_color='#333333',
        background_source=Path('/path/to/image.png'), background_filename=Path('/path/to/image.png'))

    # WHEN: set_background_page_values() is called - THEN: it doesn't raise
    theme_form.set_background_page_values()

    # AND: the stream MRL field is cleared rather than being handed a Path
    assert theme_form.background_page.stream_mrl == ''



@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_update_theme_cannot_update(mocked_setup, settings):
    """
    Test that the update_theme() method skips out early when the theme cannot be updated
    """
    # GIVEN: An instance of a ThemeForm with some mocked out pages which return certain values
    theme_form = ThemeForm(None)
    theme_form.can_update_theme = False

    # WHEN: ThemeForm.update_theme() is called
    theme_form.update_theme()

    # THEN: The theme should be correct
    # TODO: Figure out a way to check this


@patch('openlp.core.ui.themeform.ThemeForm._setup')
def test_accept_strips_theme_name(mocked_setup, settings):
    """
    Test that accept() strips surrounding whitespace from the theme name.
    """
    # GIVEN: A theme with extra spaces in the entered name
    theme_form = ThemeForm(None)
    theme_form.theme = MagicMock(background_type='solid')
    theme_form.theme_name_edit = MagicMock(**{'text.return_value': '  My Theme  '})
    theme_form.path = Path('/tmp/themes')
    theme_form.preview_box = MagicMock(**{'generate_preview.return_value': MagicMock()})
    mocked_theme_manager = MagicMock()
    mocked_theme_manager.check_if_theme_exists.return_value = True
    Registry().register('theme_manager', mocked_theme_manager)
    theme_form.edit_mode = False

    # WHEN: accept is called
    with patch('openlp.core.ui.themeform.QtWidgets.QDialog.accept'):
        theme_form.accept()

    # THEN: Name should be stripped before saving
    assert theme_form.theme.theme_name == 'My Theme'
    # AND: The final preview is a freshly-settled render of the finished theme, not a bare grab() of
    # whatever the debounced live preview last happened to display
    theme_form.preview_box.generate_preview.assert_called_once_with(theme_form.theme, False, True)
