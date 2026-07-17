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
Package to test the openlp.core.display.window package.
"""
import sys
import time
import pytest
from pathlib import Path

from unittest.mock import MagicMock, patch

from PySide6 import QtCore

from openlp.core.common.enum import ServiceItemType
from openlp.core.common.platform import is_win
from openlp.core.common.registry import Registry
from openlp.core.display.screens import Screen
from openlp.core.display.window import TRANSITION_END_EVENT_NAME, DisplayWindow, DisplayWatcher
from openlp.core.lib.theme import Theme
from openlp.core.ui import HideMode

# Mock QtWebEngineCore
sys.modules['PySide6.QtWebEngineCore'] = MagicMock()


@pytest.fixture
def mock_geometry():
    mocked_screen = MagicMock()
    mocked_screen.display_geometry = QtCore.QRect(10, 20, 400, 600)
    mocked_screenlist = MagicMock()
    mocked_screenlist.current = mocked_screen
    screenlist_patcher = patch('openlp.core.lib.theme.ScreenList', return_value=mocked_screenlist)
    screenlist_patcher.start()
    yield
    screenlist_patcher.stop()


@pytest.fixture
def display_window_env():
    box_layout_patcher = patch('openlp.core.display.window.QtWidgets.QVBoxLayout')
    web_view_patcher = patch('openlp.core.display.webengine.WebEngineView')
    web_view_schemes_patcher = patch('openlp.core.display.webengine.WebViewSchemes')
    box_layout_patcher.start()
    web_view_patcher.start()
    web_view_schemes_patcher.start()
    yield
    box_layout_patcher.stop()
    web_view_patcher.stop()
    web_view_schemes_patcher.stop()


def test_x11_override_on(display_window_env, mock_settings):
    """
    Test that the x11 override option bit is set
    """
    # GIVEN: x11 bypass is on
    mock_settings.value.return_value = True

    # WHEN: A DisplayWindow is generated
    display_window = DisplayWindow()

    # THEN: The x11 override flag should be set
    x11_bit = display_window.windowFlags() & QtCore.Qt.WindowType.X11BypassWindowManagerHint
    assert x11_bit == QtCore.Qt.WindowType.X11BypassWindowManagerHint


def test_x11_override_off(display_window_env, mock_settings):
    """
    Test that the x11 override option bit is not set when setting if off
    """
    # GIVEN: x11 bypass is off
    mock_settings.value.return_value = False

    # WHEN: A DisplayWindow is generated
    display_window = DisplayWindow()

    # THEN: The x11 override flag should not be set
    x11_bit = display_window.windowFlags() & QtCore.Qt.WindowType.X11BypassWindowManagerHint
    assert x11_bit != QtCore.Qt.WindowType.X11BypassWindowManagerHint


@patch('openlp.core.display.window.is_macosx')
def test_macos_toolwindow_attribute_set(mocked_is_macosx, mock_settings, display_window_env):
    """
    Test that on macOS, the Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow attribute is set
    """
    # GIVEN: We're on macOS
    mocked_is_macosx.return_value = True

    # WHEN: A DisplayWindow is created
    display_window = DisplayWindow()

    # THEN: The attribute is set
    assert display_window.testAttribute(QtCore.Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow) is True


@patch('openlp.core.display.window.is_macosx')
def test_not_macos_toolwindow_attribute_set(mocked_is_macosx, mock_settings, display_window_env):
    """
    Test that on systems other than macOS, the Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow attribute is NOT set
    """
    # GIVEN: We're on macOS
    mocked_is_macosx.return_value = False

    # WHEN: A DisplayWindow is created
    display_window = DisplayWindow()

    # THEN: The attribute is set
    assert display_window.testAttribute(QtCore.Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow) is False


@pytest.mark.skip(reason="Currently broken due to migration to Hatch")
@patch.object(DisplayWindow, 'show')
def test_not_shown_if_start_hidden_is_set(mocked_show, display_window_env, mock_settings):
    """
    Tests if DisplayWindow's .show() method is not called on constructor if constructed with start_hidden=True
    """

    # GIVEN: A mocked DisplayWindow's show method, a fake screen and relevant settings
    settings = {
        'advanced/x11 bypass wm': False,
        'core/display on monitor': True
    }
    mock_settings.value.side_effect = lambda key: settings[key]
    screen = Screen(1, QtCore.QRect(0, 0, 800, 600), is_display=True)

    # WHEN: A DisplayWindow is created with start_hidden=True
    DisplayWindow(screen=screen, start_hidden=True)

    # THEN: Window is not shown
    mocked_show.assert_not_called()


@pytest.mark.skip(reason="Currently broken due to migration to Hatch")
@patch.object(DisplayWindow, 'showFullScreen')
def test_shown_if_start_hidden_is_not_set(mocked_show_fullscreen, display_window_env, mock_settings):
    """
    Tests if DisplayWindow's .show() method is called on constructor if constructed with start_hidden=False
    """

    # GIVEN: A mocked DisplayWindow's show method, a fake screen and relevant settings
    settings = {
        'advanced/x11 bypass wm': False,
        'core/display on monitor': True
    }
    mock_settings.value.side_effect = lambda key: settings[key]
    screen = Screen(1, QtCore.QRect(0, 0, 800, 600), is_display=True)

    # WHEN: A DisplayWindow is created with start_hidden=True
    DisplayWindow(screen=screen, start_hidden=False)

    # THEN: Window is shown
    mocked_show_fullscreen.assert_called()


@pytest.mark.skip(reason="Currently broken due to migration to Hatch")
@patch.object(DisplayWindow, 'show')
def test_shown_if_start_hidden_is_not_set_custom_geometry(mocked_show, display_window_env, mock_settings):
    """
    Tests if DisplayWindow's .show() method is called on constructor if constructed with start_hidden=False
    """

    # GIVEN: A mocked DisplayWindow's show method, a fake screen and relevant settings
    settings = {
        'advanced/x11 bypass wm': False,
        'core/display on monitor': True
    }
    mock_settings.value.side_effect = lambda key: settings[key]
    screen = Screen(1, QtCore.QRect(0, 0, 800, 600), QtCore.QRect(0, 0, 700, 600), is_display=True)

    # WHEN: A DisplayWindow is created with start_hidden=True
    DisplayWindow(screen=screen, start_hidden=False)

    # THEN: Window is shown
    mocked_show.assert_called()


def test_set_scale_not_initialised(display_window_env, mock_settings):
    """
    Test that the scale js is not run if the page is not initialised
    """
    # GIVEN: A display window not yet initialised
    display_window = DisplayWindow()
    display_window._is_initialised = False
    display_window.run_in_display = MagicMock()

    # WHEN: set scale is run
    display_window.set_scale(0.5)

    # THEN: javascript should not be run
    display_window.run_in_display.assert_not_called()


def test_set_scale_initialised(display_window_env, mock_settings):
    """
    Test that the scale js is run if the page is initialised
    """
    # GIVEN: A initialised display window
    display_window = DisplayWindow()
    display_window._is_initialised = True
    display_window.run_in_display = MagicMock()

    # WHEN: set scale is run
    display_window.set_scale(0.5)

    # THEN: javascript should not be run
    display_window.run_in_display.assert_called_once_with('setScale', 50.0)


@pytest.mark.skip(reason="Currently broken due to migration to Hatch")
def test_set_display_custom_url_works_http(registry, display_window_env, mock_settings):
    """
    Test that setting a display custom url works with HTTP path
    """
    # GIVEN: A mocked set_url and a custom display path
    test_path = 'http://localhost:4200?testing=true'
    registry.register('display_custom_url', test_path)

    with patch('openlp.core.display.window.DisplayWindow.set_url') as mocked_set_url, \
         patch('openlp.core.display.window.QtCore.QUrl') as mocked_qurl:
        mocked_qurl.side_effect = lambda input: input
        # WHEN: creating a DisplayWindow
        DisplayWindow()

        # THEN: URL should be set with the custom path
        mocked_set_url.assert_called_once_with(test_path)


def test_set_startup_screen(display_window_env, mock_settings):
    """
    Test that the startup screen get set correctly
    """
    # GIVEN: A display window and mocked settings with logo path
    display_window = DisplayWindow()
    display_window._is_initialised = True
    display_window.run_in_display = MagicMock()

    if is_win():
        image_path = 'c:/my/image.png'
        expect_image_path = '/' + image_path
    else:
        image_path = '/my/image.png'
        expect_image_path = image_path
    display_window.openlp_splash_screen_path = Path('/default/splash_screen.png')
    settings = {
        'core/logo background color': 'red',
        'core/logo file': Path(image_path),
        'core/logo hide on startup': False
    }
    mock_settings.value.side_effect = lambda key: settings[key]

    # WHEN: set_startup_screen is run
    display_window.set_startup_screen()

    # THEN: javascript should be run
    display_window.run_in_display.assert_called_once_with('setStartupSplashScreen', "red",
                                                          "openlp-library://local-file/{path}"
                                                          .format(path=expect_image_path))


def test_set_startup_screen_default_image(display_window_env, mock_settings):
    """
    Test that the startup screen get set correctly
    """
    # GIVEN: A display window and mocked settings with logo path
    display_window = DisplayWindow()
    display_window._is_initialised = True
    display_window.run_in_display = MagicMock()
    splash_screen_path = 'openlp://display/openlp-splash-screen.png'
    expect_splash_screen_path = splash_screen_path
    display_window.openlp_splash_screen_path = splash_screen_path
    settings = {
        'core/logo background color': 'blue',
        'core/logo file': Path(':/graphics/openlp-splash-screen.png'),
        'core/logo hide on startup': False
    }
    mock_settings.value.side_effect = lambda key: settings[key]

    # WHEN: set_startup_screen is run
    display_window.set_startup_screen()

    # THEN: javascript should be run
    display_window.run_in_display.assert_called_with('setStartupSplashScreen', 'blue',
                                                     "{path}".format(path=expect_splash_screen_path))


def test_set_startup_screen_missing(display_window_env, mock_settings):
    """
    Test that the startup screen get set correctly
    """
    # GIVEN: A display window and mocked settings with logo path missing
    display_window = DisplayWindow()
    display_window._is_initialised = True
    display_window.run_in_display = MagicMock()
    display_window.openlp_splash_screen_path = Path('/default/splash_screen.png')
    settings = {
        'core/logo background color': 'green',
        'core/logo file': None,
        'core/logo hide on startup': False
    }
    mock_settings.value.side_effect = lambda key: settings[key]

    # WHEN: set_startup_screen is run
    display_window.set_startup_screen()

    # THEN: javascript should be run
    display_window.run_in_display.assert_called_with('setStartupSplashScreen', 'green', '')


def test_set_startup_screen_hide(display_window_env, mock_settings):
    """
    Test that the startup screen get set correctly
    """
    # GIVEN: A display window and mocked settings with hide logo true
    display_window = DisplayWindow()
    display_window._is_initialised = True
    display_window.run_in_display = MagicMock()
    display_window.openlp_splash_screen_path = Path('/default/splash_screen.png')
    settings = {
        'core/logo background color': 'orange',
        'core/logo file': Path('/my/image.png'),
        'core/logo hide on startup': True
    }
    mock_settings.value.side_effect = lambda key: settings[key]

    # WHEN: set_startup_screen is run
    display_window.set_startup_screen()

    # THEN: javascript should be run
    display_window.run_in_display.assert_called_once_with('setStartupSplashScreen', 'orange', '')


def test_after_loaded(display_window_env, mock_settings, registry):
    """
    Test the correct steps are taken when the webview is loaded
    """
    # GIVEN: An initialised display window and settings for item transitions and hide mouse returns true
    display_window = DisplayWindow()
    display_window.is_display = True
    mock_settings.value.return_value = True
    display_window.scale = 2
    display_window._is_initialised = True
    display_window.run_in_display = MagicMock()
    display_window.set_scale = MagicMock()
    display_window.set_startup_screen = MagicMock()

    # WHEN: after_loaded is run
    display_window.after_loaded()

    # THEN: The following functions should have been called
    display_window.run_in_display.assert_called_once_with('init', {'isDisplay': True,
                                                                   'doItemTransitions': True,
                                                                   'slideNumbersInFooter': True,
                                                                   'hideMouse': True,
                                                                   'displayTitle': None})
    display_window.set_scale.assert_called_once_with(2)
    display_window.set_startup_screen.assert_called_once()


def test_after_loaded_hide_mouse_not_display(display_window_env, mock_settings):
    """
    Test the mouse is showing even if the `hide mouse` setting is set while is_display=false
    """
    # GIVEN: An initialised display window and settings for item transitions and hide mouse returns true
    display_window = DisplayWindow()
    display_window.is_display = False
    mock_settings.value.return_value = True
    display_window.scale = 2
    display_window._is_initialised = True
    display_window.run_in_display = MagicMock()
    display_window.set_scale = MagicMock()
    display_window.set_startup_screen = MagicMock()

    # WHEN: after_loaded is run
    display_window.after_loaded()

    # THEN: Display.init should be called where is_display=false, do_item_transitions=true, show_mouse=false
    display_window.run_in_display.assert_called_once_with('init', {'isDisplay': False,
                                                                   'doItemTransitions': True,
                                                                   'slideNumbersInFooter': True,
                                                                   'hideMouse': False,
                                                                   'displayTitle': None})


def test_after_loaded_callback(display_window_env, mock_settings, registry):
    """
    Test if the __ is loaded on after_loaded() method correctly
    """
    # GIVEN: An initialised display window and settings for item transitions and hide mouse returns true
    mocked_after_loaded_callback = MagicMock()
    display_window = DisplayWindow(after_loaded_callback=mocked_after_loaded_callback)
    display_window.is_display = True
    mock_settings.value.return_value = True
    display_window._is_initialised = True
    display_window.run_in_display = MagicMock()
    display_window.set_scale = MagicMock()
    display_window.set_startup_screen = MagicMock()

    # WHEN: after_loaded is run
    display_window.after_loaded()

    # THEN: The after_loaded_callback should be called
    mocked_after_loaded_callback.assert_called_once()


@patch('openlp.core.display.window.wait_for')
def test_run_in_display_no_sync_no_wait(mocked_wait_for, display_window_env, mock_settings):
    """
    test a script is run on the webview
    """
    # GIVEN: A (fake) webengine page on a loaded display page
    display_window = DisplayWindow()
    display_window._is_page_loaded = True
    webengine_page = MagicMock()
    display_window.webview.page = MagicMock(return_value=webengine_page)

    # WHEN: javascript is requested to run
    display_window._run_javascript('javascript to execute')

    # THEN: javascript should be run with no delay
    webengine_page.runJavaScript.assert_called_once_with('javascript to execute')
    assert mocked_wait_for.call_count == 1, 'wait_for should have only been called once'


def test_run_javascript_queued_before_page_loaded(display_window_env, mock_settings):
    """
    Test that javascript requested before the page has loaded is queued instead of being
    injected into the page (which would throw "ReferenceError: requestAction is not defined")
    """
    # GIVEN: A display window whose page has not finished loading
    display_window = DisplayWindow()
    webengine_page = MagicMock()
    display_window.webview.page = MagicMock(return_value=webengine_page)
    assert display_window._is_page_loaded is False

    # WHEN: javascript is requested to run asynchronously
    display_window._run_javascript('requestAction(\'show\')')

    # THEN: The script should be queued, not run
    webengine_page.runJavaScript.assert_not_called()
    assert display_window._pending_javascript == ['requestAction(\'show\')']


def test_after_loaded_runs_queued_javascript(display_window_env, mock_settings, registry):
    """
    Test that scripts queued before the page loaded are run by after_loaded
    """
    # GIVEN: A display window with a queued script
    display_window = DisplayWindow()
    display_window.is_display = True
    mock_settings.value.return_value = True
    display_window._is_initialised = True
    display_window.run_in_display = MagicMock()
    display_window.set_scale = MagicMock()
    display_window.set_startup_screen = MagicMock()
    display_window._run_javascript = MagicMock()
    display_window._pending_javascript = ['requestAction(\'show\')']

    # WHEN: after_loaded is run
    display_window.after_loaded()

    # THEN: The page should be marked as loaded and the queued script should have been run
    assert display_window._is_page_loaded is True
    display_window._run_javascript.assert_called_once_with('requestAction(\'show\')')
    assert display_window._pending_javascript == []


@patch('openlp.core.display.window.wait_for')
def test_run_in_display_sync_no_wait(mocked_wait_for, display_window_env, mock_settings):
    """
    test a synced script is run on the webview and immediately returns a result
    """
    # GIVEN: A (fake) webengine page with a js callback fn
    mocked_wait_for.return_value = True
    display_window = DisplayWindow()
    display_window._is_page_loaded = True
    display_window.webview = MagicMock()
    webengine_page = MagicMock()

    def post_js_result(script: str):
        """A mock method to call the handle_javascript_result() method when the script is run"""
        display_window.handle_javascript_result(1234)

    webengine_page.runJavaScript.side_effect = post_js_result
    display_window.webview.page.return_value = webengine_page

    # WHEN: javascript is requested to run, and the JS returns a result
    result = display_window._run_javascript('javascript to execute', True)

    # THEN: javascript should be run with no delay and return with the correct result
    assert result == 1234
    webengine_page.runJavaScript.assert_called_once()


@patch('openlp.core.display.window.is_win')
def test_fix_font_bold_windows(mocked_is_win, display_window_env, mock_settings):
    """
    Test that on Windows, fonts that end with "Bold" are handled
    """
    # GIVEN: A display window and a font name
    mocked_is_win.return_value = True
    display_window = DisplayWindow()
    display_window.is_display = True
    display_window.run_in_display = MagicMock()
    font_name = 'Arial Rounded MT Bold'

    # WHEN: The font is processed
    result = display_window._fix_font_name(font_name)

    # Then the font name should be fixed
    assert result == 'Arial Rounded MT'


@patch('openlp.core.display.window.is_win')
def test_fix_font_bold_not_windows(mocked_is_win, display_window_env, mock_settings):
    """
    Test that on NOT Windows, fonts that end with "Bold" are ignored
    """
    # GIVEN: A display window and a font name
    mocked_is_win.return_value = False
    display_window = DisplayWindow()
    display_window.is_display = True
    display_window.run_in_display = MagicMock()
    font_name = 'Arial Rounded MT Bold'

    # WHEN: The font is processed
    result = display_window._fix_font_name(font_name)

    # Then the font name should be fixed
    assert result == 'Arial Rounded MT Bold'


@patch('openlp.core.display.window.is_win')
def test_fix_font_foundry(mocked_is_win, display_window_env, mock_settings):
    """
    Test that a font with a foundry name in it has the foundry removed
    """
    # GIVEN: A display window and a font name
    mocked_is_win.return_value = False
    display_window = DisplayWindow()
    display_window.is_display = True
    display_window.run_in_display = MagicMock()
    font_name = 'CMG Sans [Foundry]'

    # WHEN: The font is processed
    result = display_window._fix_font_name(font_name)

    # Then the font name should be fixed
    assert result == 'CMG Sans'


def test_set_theme_is_display_video(display_window_env, mock_settings, mock_geometry):
    """
    Test the set_theme function
    """
    # GIVEN: A display window and a video theme
    display_window = DisplayWindow()
    display_window.is_display = True
    display_window.run_in_display = MagicMock()
    theme = Theme()
    theme.background_type = 'video'
    result_theme = Theme()
    result_theme.background_type = 'transparent'
    result_theme = result_theme.export_theme(is_js=True)

    # WHEN: The set theme function is called
    display_window.set_theme(theme, is_sync=False, service_item_type=ServiceItemType.Text)

    # THEN: The final theme should be transparent
    display_window.run_in_display.assert_called_once_with('setTheme', raw_parameters=result_theme, is_sync=False)


def test_set_theme_not_display_video(display_window_env, mock_settings, mock_geometry):
    """
    Test the set_theme function
    """
    # GIVEN: A display window and a video theme
    display_window = DisplayWindow()
    display_window.is_display = False
    display_window.run_in_display = MagicMock()
    theme = Theme()
    theme.background_type = 'video'
    theme.background_border_color = 'border_colour'
    result_theme = Theme()
    result_theme.background_type = 'solid'
    result_theme.background_border_color = 'border_colour'
    result_theme.background_start_color = 'border_colour'
    result_theme.background_end_color = 'border_colour'
    result_theme.background_main_color = 'border_colour'
    result_theme.background_footer_color = 'border_colour'
    result_theme.background_color = 'border_colour'
    result_theme = result_theme.export_theme(is_js=True)

    # WHEN: The set theme function is called
    display_window.set_theme(theme, is_sync=False, service_item_type=False)

    # THEN: The final theme should use 'border_colour' for it's colour values
    display_window.run_in_display.assert_called_once_with('setTheme', raw_parameters=result_theme, is_sync=False)


def test_set_theme_not_display_live(display_window_env, mock_settings, mock_geometry):
    """
    Test the set_theme function
    """
    # GIVEN: A display window and a video theme
    display_window = DisplayWindow()
    display_window.is_display = False
    display_window.run_in_display = MagicMock()
    theme = Theme()
    theme.background_type = 'live'
    result_theme = Theme()
    result_theme.background_type = 'solid'
    result_theme.background_start_color = '#590909'
    result_theme.background_end_color = '#590909'
    result_theme.background_main_color = '#090909'
    result_theme.background_footer_color = '#090909'
    result_theme = result_theme.export_theme(is_js=True)

    # WHEN: The set theme function is called
    display_window.set_theme(theme, is_sync=False, service_item_type=False)

    # THEN: The final theme should use the preset colour values
    display_window.run_in_display.assert_called_once_with('setTheme', raw_parameters=result_theme, is_sync=False)


@patch('openlp.core.display.window.Registry.execute')
@patch('openlp.core.display.window.ScreenList')
def test_show_display(mocked_screenlist: MagicMock, mocked_registry_execute: MagicMock, display_window_env,
                      mock_settings: MagicMock, registry: Registry):
    """
    Test show_display function
    """
    # GIVEN: Display window as the active display
    display_window = DisplayWindow()
    display_window.is_display = True
    display_window.isHidden = MagicMock(return_value=True)
    display_window.setVisible = MagicMock()
    display_window.run_in_display = MagicMock()
    mocked_screenlist.screens = [1, 2]

    # WHEN: Show display is run
    display_window.show_display()

    # THEN: Should show the display and set the hide mode to none
    display_window.setVisible.assert_called_once_with(True)
    display_window.run_in_display.assert_called_once_with('show')


@patch('openlp.core.display.window.ScreenList')
def test_show_display_no_display(mocked_screenlist, display_window_env, mock_settings):
    """
    Test show_display function when no displays are available
    """
    # GIVEN: A Display window, one screen and core/display on monitor disabled
    display_window = DisplayWindow()
    display_window.run_in_display = MagicMock()
    display_window.is_display = True
    mocked_screenlist.return_value = [1]
    mock_settings.value.return_value = False

    # WHEN: Show display is run
    display_window.show_display()

    # THEN: Shouldn't run the js show fn
    assert display_window.run_in_display.call_count == 0


def test_hide_display_to_screen(display_window_env, mock_settings):
    """
    Test hide to screen in the hide_display function
    """
    # GIVEN: Display window and setting advanced/disable transparent display = False
    display_window = DisplayWindow()
    display_window.run_in_display = MagicMock()
    display_window.setVisible = MagicMock()
    mock_settings.value.return_value = False

    # WHEN: Hide display is run with no mode (should default to Screen)
    display_window.hide_display()

    # THEN: Should hide the display with the js transparency function (not setVisible)
    display_window.setVisible.call_count == 0
    display_window.run_in_display.assert_called_once_with('toTransparent')


def test_hide_display_to_blank(display_window_env, mock_settings):
    """
    Test hide to screen in the hide_display function
    """
    # GIVEN: Display window and setting advanced/disable transparent display = False
    display_window = DisplayWindow()
    display_window.run_in_display = MagicMock()
    mock_settings.value.return_value = False

    # WHEN: Hide display is run with HideMode.Blank
    display_window.hide_display(HideMode.Blank)

    # THEN: Should run the correct javascript on the display and set the hide mode
    display_window.run_in_display.assert_called_once_with('toBlack')


def test_hide_display_to_theme(display_window_env, mock_settings):
    """
    Test hide to screen in the hide_display function
    """
    # GIVEN: Display window and setting advanced/disable transparent display = False
    display_window = DisplayWindow()
    display_window.run_in_display = MagicMock()
    mock_settings.value.return_value = False

    # WHEN: Hide display is run with HideMode.Theme
    display_window.hide_display(HideMode.Theme)

    # THEN: Should run the correct javascript on the display and set the hide mode
    display_window.run_in_display.assert_called_once_with('toTheme')


def test_hide_display_to_transparent(display_window_env, mock_settings):
    """
    Test hide to screen in the hide_display function
    """
    # GIVEN: Display window and setting advanced/disable transparent display = False
    display_window = DisplayWindow()
    display_window.run_in_display = MagicMock()
    display_window.setVisible = MagicMock()
    mock_settings.value.return_value = False

    # WHEN: Hide display is run with HideMode.Screen
    display_window.hide_display(HideMode.Screen)

    # THEN: Should run the correct javascript on the display and not set the visiblity
    display_window.run_in_display.assert_called_once_with('toTransparent')
    assert display_window.setVisible.call_count == 0


def test_display_watcher_dispatches_registered_event(display_window_env, mock_settings):
    """
    Test that the display watcher dispatches events to the registered listeners
    """
    # GIVEN: Display window and a dummy event
    event_name = 'dummy_event'
    event_listener = MagicMock()
    display_window = DisplayWindow()
    display_window.display_watcher.register_event_listener(event_name, event_listener)

    # WHEN: Event is dispatched
    display_window.display_watcher.dispatchEvent(event_name, {})

    # THEN: Events should be called
    event_listener.assert_called_once()


def test_display_watcher_dispatches_permanent_registered_event(display_window_env, mock_settings):
    """
    Test that the display watcher dispatches events to the permanent registered listeners
    """
    # GIVEN: Display window and a dummy event
    event_name = 'dummy_event'
    event_listener = MagicMock()
    display_window = DisplayWindow()
    display_window.display_watcher.register_event_listener(event_name, event_listener, True)

    # WHEN: Event is dispatched
    display_window.display_watcher.dispatchEvent(event_name, {})

    # THEN: Events should be called
    event_listener.assert_called_once()


def test_display_watcher_dispatches_transient_and_permanent_registered_event(display_window_env, mock_settings):
    """
    Test that the display watcher dispatches events to both transient and permanent registered listeners
    """
    # GIVEN: Display window and a dummy event
    event_name = 'dummy_event'
    event_listener = MagicMock()
    event_listener_permanent = MagicMock()
    display_window = DisplayWindow()
    display_window.display_watcher.register_event_listener(event_name, event_listener, True)
    display_window.display_watcher.register_event_listener(event_name, event_listener_permanent, False)

    # WHEN: Event is dispatched
    display_window.display_watcher.dispatchEvent(event_name, {})

    # THEN: Events should be called
    event_listener.assert_called_once()
    event_listener_permanent.assert_called_once()


def test_display_watcher_unregisters_registered_event(display_window_env, mock_settings):
    """
    Test that the display watcher unregisters registered listeners
    """
    # GIVEN: Display window and a dummy event that is unregistered later
    event_name = 'dummy_event'
    event_listener = MagicMock()
    display_window = DisplayWindow()
    display_window.display_watcher.register_event_listener(event_name, event_listener)
    display_window.display_watcher.unregister_event_listener(event_name)

    # WHEN: Event is dispatched
    display_window.display_watcher.dispatchEvent(event_name, {})

    # THEN: Events should not be called
    event_listener.assert_not_called()


def test_display_watcher_unregisters_registered_permanent_event(display_window_env, mock_settings):
    """
    Test that the display watcher unregisters registered permanent listeners
    """
    # GIVEN: Display window and a dummy event that is unregistered later
    event_name = 'dummy_event'
    event_listener = MagicMock()
    display_window = DisplayWindow()
    display_window.display_watcher.register_event_listener(event_name, event_listener, True)
    display_window.display_watcher.unregister_event_listener(event_name)

    # WHEN: Event is dispatched
    display_window.display_watcher.dispatchEvent(event_name, {})

    # THEN: Events should not be called
    event_listener.assert_not_called()


def test_display_watcher_unregisters_registered_permanent_and_transient_event(display_window_env, mock_settings):
    """
    Test that the display watcher unregisters registered listeners, both permanent and transient
    """
    # GIVEN: Display window and a dummy event that is unregistered later
    event_name = 'dummy_event'
    event_listener = MagicMock()
    event_listener_permanent = MagicMock()
    display_window = DisplayWindow()
    display_window.display_watcher.register_event_listener(event_name, event_listener)
    display_window.display_watcher.register_event_listener(event_name, event_listener_permanent, False)
    display_window.display_watcher.unregister_event_listener(event_name)
    display_window.display_watcher.unregister_event_listener(event_name, False)

    # WHEN: Event is dispatched
    display_window.display_watcher.dispatchEvent(event_name, {})

    # THEN: Events should not be called
    event_listener.assert_not_called()
    event_listener_permanent.assert_not_called()


def test_display_watcher_generates_event_names(display_window_env, mock_settings):
    """
    Test that the display watcher generate unique event names
    """
    # GIVEN: Display window
    display_window = DisplayWindow()

    # WHEN: Getting unique event names
    first_event_name = display_window.display_watcher.get_unique_event_name()
    second_event_name = display_window.display_watcher.get_unique_event_name()

    # THEN: Event names should be different
    assert first_event_name != second_event_name


def test_hide_transparent_to_screen(display_window_env, mock_settings):
    """
    Test that when going transparent, and the disable transparent setting is enabled,
    the screen mode should be used.
    """
    # GIVEN: Display window, setting advanced/disable transparent display = True and mocked run_in_display
    display_window = DisplayWindow()
    display_window.setVisible = MagicMock()
    has_ran_event = False

    def set_has_ran_event(_):
        nonlocal has_ran_event
        has_ran_event = True

    def on_dispatch_event(*args, **kwargs):
        display_window.display_watcher.register_event_listener(TRANSITION_END_EVENT_NAME, set_has_ran_event, False)
        display_window.display_watcher.dispatchEvent(TRANSITION_END_EVENT_NAME, {})

    display_window.run_in_display = MagicMock(side_effect=on_dispatch_event)
    mock_settings.value.return_value = True

    # WHEN: Hide display is run with HideMode.Screen
    display_window.hide_display(HideMode.Screen)

    # THEN: Should run setVisible(False)
    elapsed_time = 0
    while not has_ran_event:
        time.sleep(0.05)
        elapsed_time += 0.05
        if elapsed_time > 1:
            break
    assert has_ran_event is True
    display_window.setVisible.assert_called_once_with(False)


@patch('openlp.core.display.window.ScreenList')
def test_hide_display_no_display(mocked_screenlist, display_window_env, mock_settings):
    """
    Test show_display function when no displays are available
    """
    # GIVEN: A Display window, one screen and core/display on monitor disabled
    display_window = DisplayWindow()
    display_window.hide_mode = None
    display_window.is_display = True
    mocked_screenlist.return_value = [1]
    mock_settings.value.return_value = False

    # WHEN: Hide display is run
    display_window.hide_display(HideMode.Screen)

    # THEN: Hide mode should still be none
    assert display_window.hide_mode is None


def test_display_watcher_set_initialised():
    """
    Test that the initialised signal is emitted
    """
    # GIVEN: A DisplayWatcher instance
    display_watcher = DisplayWatcher(None)

    # WHEN: setInitialised is called
    with patch.object(display_watcher, 'initialised') as mocked_initialised:
        display_watcher.setInitialised(True)

        # THEN: initialised should have been emitted
        mocked_initialised.emit.assert_called_once_with(True)


def test_display_watcher_please_repaint(display_window_env, mock_settings):
    """
    Test that the repaint is initiated
    """
    # GIVEN: A DisplayWindow instance with mocked out webview
    display_window = DisplayWindow()
    display_window.webview = MagicMock()

    # WHEN: pleaseRepaint is called on the DisplayWatcher
    display_window.display_watcher.pleaseRepaint()

    # THEN: Qt update for the webview should have been triggered
    assert display_window.webview.update.call_count == 1


def test_close_event_ignores_event(display_window_env, mock_settings):
    """
    Test that when the window receives a close event, it ignores it
    """
    # GIVEN: A DisplayWindow instance and a mocked event
    display_window = DisplayWindow()
    mocked_event = MagicMock()

    # WHEN: The closeEvent() method is called
    display_window.closeEvent(mocked_event)

    # THEN: The event should have been ignored
    mocked_event.ignore.assert_called_once()


def test_close_event_accepts_event_manual_close(display_window_env, mock_settings):
    """
    Test that when the window receives a close event due to manually being closed, it accepts it
    """
    # GIVEN: A DisplayWindow instance and a mocked event
    display_window = DisplayWindow()
    mocked_event = MagicMock()

    # WHEN: The closeEvent() method is called
    display_window._is_manual_close = True
    display_window.closeEvent(mocked_event)

    # THEN: The event should have been ignored
    assert mocked_event.ignore.called is False


def test_run_in_display_run(display_window_env, mock_settings):
    """
    Test that when run_in_display is called
    """
    # GIVEN: A DisplayWindow instance and a mocked _run_javascript
    display_window = DisplayWindow()
    display_window._run_javascript = MagicMock()

    # WHEN: The run_is_display is called
    display_window.run_in_display('test_event')

    # THEN: The event should be called
    display_window._run_javascript.assert_called_once_with('requestAction(\'test_event\')', False)


def test_run_in_display_honors_is_sync(display_window_env, mock_settings):
    """
    Test that when run_in_display honors is_sync flag
    """
    # GIVEN: A DisplayWindow instance and a mocked _run_javascript
    display_window = DisplayWindow()
    display_window._run_javascript = MagicMock()

    # WHEN: The run_is_display is called
    display_window.run_in_display('test_event', is_sync=True)

    # THEN: The event should be called
    display_window._run_javascript.assert_called_once_with('requestAction(\'test_event\')', True)


def test_run_in_display_honors_raw_parameters(display_window_env, mock_settings):
    """
    Test that when run_in_display honors raw_parameters parameters
    """
    # GIVEN: A DisplayWindow instance and a mocked _run_javascript
    display_window = DisplayWindow()
    display_window._run_javascript = MagicMock()

    # WHEN: The run_is_display is called
    display_window.run_in_display('test_event', raw_parameters='a test: testing')

    # THEN: The event should be called
    display_window._run_javascript.assert_called_once_with('requestAction(\'test_event\', a test: testing)', False)


def test_run_in_display_honors_return_event_name(display_window_env, mock_settings):
    """
    Test that when run_in_display honors return_event_name parameter
    """
    # GIVEN: A DisplayWindow instance and a mocked _run_javascript
    display_window = DisplayWindow()
    display_window._run_javascript = MagicMock()

    # WHEN: The run_is_display is called
    display_window.run_in_display('test_event', return_event_name='test_event')

    # THEN: The event should be called
    display_window._run_javascript.assert_called_once_with('requestActionAsync(\'test_event\', \'test_event\')', False)


def test_run_in_display_dumps_json(display_window_env, mock_settings):
    """
    Test that when run_in_display is called with parameters, each of it will be dumped as a JSON string
    """
    # GIVEN: A DisplayWindow instance and a mocked _run_javascript
    display_window = DisplayWindow()
    display_window._run_javascript = MagicMock()

    # WHEN: The run_is_display is called
    display_window.run_in_display('test_event', 1.23, 'a "string', [1, 2, 'test'], {"test1": "test2"})

    # THEN: The parameters should be correctly converted to JSON
    display_window._run_javascript.assert_called_once_with('requestAction(\'test_event\', 1.23, "a \\"string\", '
                                                           '[1, 2, "test"], {"test1": "test2"})', False)
