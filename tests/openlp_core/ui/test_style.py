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
Package to test the :mod:`~openlp.core.ui.style` module.
"""
from unittest.mock import MagicMock, patch, call

import pytest

from openlp.core.ui.style import MEDIA_MANAGER_STYLE, NOIR_LIGHT_MEDIA_MANAGER_STYLE, NOIR_LIGHT_STYLESHEET, \
    NOIR_MEDIA_MANAGER_STYLE, NOIR_STYLESHEET, UiThemes, WIN_REPAIR_STYLESHEET, \
    get_alternate_rows_repair_stylesheet, get_application_stylesheet, get_library_stylesheet, has_ui_theme, \
    is_ui_theme_dark, set_default_theme
import openlp.core.ui.style


@pytest.mark.skipif(not hasattr(openlp.core.ui.style, 'qdarkstyle'), reason='qdarkstyle is not installed')
@patch('openlp.core.ui.style.HAS_DARK_THEME', True)
@patch('openlp.core.ui.style.qdarkstyle')
def test_get_application_stylesheet_qdarkstyle(mocked_qdarkstyle, mock_settings):
    """Test that the QDarkStyle stylesheet is returned when available and enabled"""
    # GIVEN: Theme is QDarkStyle
    mock_settings.value.return_value = UiThemes.QDarkStyle
    mocked_qdarkstyle.load_stylesheet_pyqt.return_value = '//dark_style//'

    # WHEN: get_application_stylesheet() is called
    result = get_application_stylesheet()

    # THEN: the result should be QDarkStyle stylesheet
    assert '//dark_style//' in result


@pytest.mark.skipif(not hasattr(openlp.core.ui.style, 'qdarkstyle'), reason='qdarkstyle is not installed')
@patch('openlp.core.ui.style.HAS_DARK_THEME', True)
def test_has_ui_theme_qdarkstyle_true_when_available(mock_settings):
    """Test that the QDarkStyle UI theme exists when qdarkstyle is available """
    # GIVEN: Theme is QDarkStyle
    mock_settings.value.return_value = UiThemes.QDarkStyle

    # WHEN: has_ui_theme() is called
    result = has_ui_theme(UiThemes.QDarkStyle)

    # THEN: the result should be true
    assert result is True


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
def test_has_ui_theme_qdarkstyle_false_when_unavailable(mock_settings):
    """Test that the QDarkStyle UI theme not exists when qdarkstyle is not available """
    # GIVEN: Theme is QDarkStyle
    mock_settings.value.return_value = UiThemes.QDarkStyle

    # WHEN: has_ui_theme() is called
    result = has_ui_theme(UiThemes.QDarkStyle)

    # THEN: the result should be false
    assert result is False


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
@patch('openlp.core.ui.style.is_win')
@patch('openlp.core.app.QtWidgets.QApplication.palette')
def test_get_application_stylesheet_not_alternate_rows(mocked_palette, mocked_is_win, mock_settings):
    """Test that the alternate rows stylesheet is returned when enabled in settings"""
    def settings_values(key):
        if key == 'advanced/ui_theme_name':
            return UiThemes.DefaultLight
        else:
            return False

    # GIVEN: We're not on Windows and UI theme is not QDarkStyle
    mocked_is_win.return_value = False
    mock_settings.value = MagicMock(side_effect=settings_values)
    mocked_palette.return_value.color.return_value.name.return_value = 'color'

    # WHEN: get_application_stylesheet() is called
    result = get_application_stylesheet()

    # THEN: result should match non-alternate-rows
    mock_settings.value.assert_has_calls([call('advanced/ui_theme_name'), call('advanced/alternate rows')])
    assert get_alternate_rows_repair_stylesheet('color') in result


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
@patch('openlp.core.ui.style.is_win')
def test_get_application_stylesheet_win_repair(mocked_is_win, mock_settings):
    """Test that the Windows repair stylesheet is returned when on Windows"""
    def settings_values(key):
        if key == 'advanced/ui_theme_name':
            return UiThemes.DefaultLight
        else:
            return True

    # GIVEN: We're on Windows and Theme is not QDarkStyle
    mocked_is_win.return_value = True
    mock_settings.value = MagicMock(side_effect=settings_values)

    # WHEN: get_application_stylesheet() is called
    result = get_application_stylesheet()

    # THEN: result should return Windows repair stylesheet
    mock_settings.value.assert_has_calls([call('advanced/ui_theme_name'), call('advanced/alternate rows')])
    assert WIN_REPAIR_STYLESHEET in result


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
@patch('openlp.core.ui.style.is_win')
def test_get_application_stylesheet_not_win_repair(mocked_is_win, mock_settings):
    """Test that the Windows repair stylesheet is not returned when not in Windows"""
    def settings_values(key):
        if key == 'advanced/ui_theme_name':
            return UiThemes.DefaultLight
        else:
            return True

    # GIVEN: We're on Windows and Theme is not QDarkStyle
    mocked_is_win.return_value = False
    mock_settings.value = MagicMock(side_effect=settings_values)

    # WHEN: get_application_stylesheet() is called
    result = get_application_stylesheet()

    # THEN: result should not return Windows repair stylesheet
    mock_settings.value.assert_has_calls([call('advanced/ui_theme_name'), call('advanced/alternate rows')])
    assert result != WIN_REPAIR_STYLESHEET


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
def test_get_library_stylesheet_automatic_ui_theme(mock_settings):
    """Test that the media manager stylesheet is returned for Automatic UI theme"""
    # GIVEN: UI theme is Automatic
    mock_settings.value.return_value = UiThemes.Automatic

    # WHEN: get_library_stylesheet() is called
    result = get_library_stylesheet()

    # THEN: the correct stylesheet should be returned
    assert result == MEDIA_MANAGER_STYLE


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
def test_get_library_stylesheet_defaultlight_ui_theme(mock_settings):
    """Test that the media manager stylesheet is returned for Default Light UI theme"""
    # GIVEN: UI theme is DefaultLight
    mock_settings.value.return_value = UiThemes.DefaultLight

    # WHEN: get_library_stylesheet() is called
    result = get_library_stylesheet()

    # THEN: the correct stylesheet should be returned
    assert result == MEDIA_MANAGER_STYLE


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
def test_get_library_stylesheet_defaultdark_ui_theme(mock_settings):
    """Test that the media manager stylesheet is returned for Default Dark UI theme"""
    # GIVEN: UI theme is DefaultDark
    mock_settings.value.return_value = UiThemes.DefaultDark

    # WHEN: get_library_stylesheet() is called
    result = get_library_stylesheet()

    # THEN: the correct stylesheet should be returned
    assert result == MEDIA_MANAGER_STYLE


@pytest.mark.skipif(not hasattr(openlp.core.ui.style, 'qdarkstyle'), reason='qdarkstyle is not installed')
@patch('openlp.core.ui.style.HAS_DARK_THEME', True)
def test_get_library_stylesheet_qdarktheme_ui_theme(mock_settings):
    """Test that the media manager stylesheet is not returned for QDarkStyle UI theme"""
    # GIVEN: UI theme is QDarkStyle
    mock_settings.value.return_value = UiThemes.QDarkStyle

    # WHEN: get_library_stylesheet() is called
    result = get_library_stylesheet()

    # THEN: The correct stylesheet should be returned
    assert result == ''


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
def test_get_library_stylesheet_noir_ui_theme(mock_settings):
    """Test that the Noir media manager stylesheet is returned for the Noir UI theme"""
    # GIVEN: UI theme is Noir
    mock_settings.value.return_value = UiThemes.Noir

    # WHEN: get_library_stylesheet() is called
    result = get_library_stylesheet()

    # THEN: the Noir stylesheet should be returned
    assert result == NOIR_MEDIA_MANAGER_STYLE


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
def test_get_library_stylesheet_noir_light_ui_theme(mock_settings):
    """Test that the Noir Light media manager stylesheet is returned for the Noir Light UI theme"""
    mock_settings.value.return_value = UiThemes.NoirLight
    result = get_library_stylesheet()
    assert result == NOIR_LIGHT_MEDIA_MANAGER_STYLE


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
@patch('openlp.core.ui.style.is_win')
def test_get_application_stylesheet_noir(mocked_is_win, mock_settings):
    """Test that the Noir stylesheet is included when the Noir UI theme is enabled"""
    def settings_values(key):
        if key == 'advanced/ui_theme_name':
            return UiThemes.Noir
        else:
            return True

    # GIVEN: UI theme is Noir
    mocked_is_win.return_value = False
    mock_settings.value = MagicMock(side_effect=settings_values)

    # WHEN: get_application_stylesheet() is called
    result = get_application_stylesheet()

    # THEN: the result should contain the Noir stylesheet
    assert NOIR_STYLESHEET in result


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
@patch('openlp.core.ui.style.is_win')
def test_get_application_stylesheet_noir_light(mocked_is_win, mock_settings):
    """Test that the Noir Light stylesheet is included when Noir Light is enabled"""
    def settings_values(key):
        if key == 'advanced/ui_theme_name':
            return UiThemes.NoirLight
        return True

    mocked_is_win.return_value = False
    mock_settings.value = MagicMock(side_effect=settings_values)

    result = get_application_stylesheet()

    assert NOIR_LIGHT_STYLESHEET in result


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
@patch('openlp.core.ui.style.is_system_darkmode')
def test_is_ui_theme_automatic_dark_when_system_dark(mocked_is_system_darkmode, mock_settings):
    """Test that the Automatic UI Theme is Dark on System Dark Theme"""
    # GIVEN: UI theme is Automatic and System Theme is Dark
    mock_settings.value.return_value = UiThemes.Automatic
    mocked_is_system_darkmode.return_value = True

    # WHEN: is_ui_theme_dark() is called
    result = is_ui_theme_dark()

    # THEN: the result should be true
    assert result is True


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
@patch('openlp.core.ui.style.is_system_darkmode')
def test_is_ui_theme_dark_automatic_light_when_system_light(mocked_is_system_darkmode, mock_settings):
    """Test that the Automatic UI Theme is not Dark on System Light Theme"""
    # GIVEN: UI theme is Automatic and System Theme is Light
    mocked_is_system_darkmode.return_value = False
    mock_settings.value.return_value = UiThemes.Automatic

    # WHEN: is_ui_theme_dark() is called
    result = is_ui_theme_dark()

    # THEN: the result should be false
    assert result is False


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
def test_is_ui_theme_dark_defaultlight_not_dark(mock_settings):
    """Test that the DefaultLight UI Theme is not Dark"""
    # GIVEN: UI theme is DefaultLight
    mock_settings.value.return_value = UiThemes.DefaultLight

    # WHEN: is_ui_theme_dark() is called
    result = is_ui_theme_dark()

    # THEN: the result should be false
    assert result is False


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
def test_is_ui_theme_dark_defaultdark_dark(mock_settings):
    """Test that the DefaultDark UI Theme is Dark"""
    # GIVEN: UI theme is DefaultDark
    mock_settings.value.return_value = UiThemes.DefaultDark

    # WHEN: is_ui_theme_dark() is called
    result = is_ui_theme_dark()

    # THEN: the result should be true
    assert result is True


@pytest.mark.skipif(not hasattr(openlp.core.ui.style, 'qdarkstyle'), reason='qdarkstyle is not installed')
@patch('openlp.core.ui.style.HAS_DARK_THEME', True)
def test_is_ui_theme_dark_qdarkstyle_dark(mock_settings):
    """Test that the QDarkStyle UI Theme is Dark"""
    # GIVEN: UI theme is DefaultDark
    mock_settings.value.return_value = UiThemes.QDarkStyle

    # WHEN: is_ui_theme_dark() is called
    result = is_ui_theme_dark()

    # THEN: the result should be true
    assert result is True


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
def test_is_ui_theme_dark_noir_dark(mock_settings):
    """Test that the Noir UI Theme is Dark"""
    # GIVEN: UI theme is Noir
    mock_settings.value.return_value = UiThemes.Noir

    # WHEN: is_ui_theme_dark() is called
    result = is_ui_theme_dark()

    # THEN: the result should be true
    assert result is True


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
def test_is_ui_theme_dark_noir_light_not_dark(mock_settings):
    """Test that the Noir Light UI Theme is not Dark"""
    mock_settings.value.return_value = UiThemes.NoirLight
    result = is_ui_theme_dark()
    assert result is False


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
def test_set_default_theme_noir_theme_sets_palette(mock_settings):
    """Test that the set_default_theme sets App Palette for the Noir UI theme"""
    # GIVEN: UI theme is Noir
    mock_settings.value.return_value = UiThemes.Noir
    mock_app = MagicMock()

    # WHEN: set_default_theme() is called
    set_default_theme(mock_app)

    # THEN: app palette should be changed and the Fusion style applied
    mock_app.setPalette.assert_called_once()
    mock_app.setStyle.assert_called_once_with('Fusion')


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
@patch('openlp.core.ui.style.set_noir_palette')
def test_set_default_theme_noir_theme_calls_set_noir_palette(mock_set_noir_palette, mock_settings):
    """Test that the set_default_theme calls set_noir_palette for the Noir UI theme"""
    # GIVEN: UI theme is Noir
    mock_settings.value.return_value = UiThemes.Noir
    mock_app = MagicMock()

    # WHEN: set_default_theme() is called
    set_default_theme(mock_app)

    # THEN: set_noir_palette should be called
    mock_set_noir_palette.assert_called_once()


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
@patch('openlp.core.ui.style.set_noir_light_palette')
def test_set_default_theme_noir_light_theme_calls_set_noir_light_palette(mock_set_noir_light_palette, mock_settings):
    """Test that the set_default_theme calls set_noir_light_palette for the Noir Light UI theme"""
    mock_settings.value.return_value = UiThemes.NoirLight
    mock_app = MagicMock()
    set_default_theme(mock_app)
    mock_set_noir_light_palette.assert_called_once()


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
def test_set_default_theme_defaultdark_theme_sets_palette(mock_settings):
    """Test that the set_default_theme sets App Palette for DefaultDark UI theme"""
    # GIVEN: UI theme is DefaultDark
    mock_settings.value.return_value = UiThemes.DefaultDark
    mock_app = MagicMock()

    # WHEN: set_default_theme() is called
    set_default_theme(mock_app)

    # THEN: app palette should be changed
    mock_app.setPalette.assert_called_once()


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
@patch('openlp.core.ui.style.is_system_darkmode')
def test_set_default_theme_automatic_theme_system_dark_sets_palette(mocked_is_system_darkmode, mock_settings):
    """Test that the set_default_theme sets App Palette for Automatic UI theme on System with Dark Theme"""
    # GIVEN: UI theme is Automatic on System with Dark Theme
    mock_settings.value.return_value = UiThemes.Automatic
    mocked_is_system_darkmode.return_value = True
    mock_app = MagicMock()

    # WHEN: set_default_theme() is called
    set_default_theme(mock_app)

    # THEN: app palette should be changed
    mock_app.setPalette.assert_called_once()


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
@patch('openlp.core.ui.style.set_default_darkmode')
def test_set_default_theme_defaultdark_theme_calls_set_default_darkmode(mock_set_default_darkmode, mock_settings):
    """Test that the set_default_theme calls set_default_darkmode for DefaultDark UI theme"""
    # GIVEN: UI theme is DefaultDark
    mock_settings.value.return_value = UiThemes.DefaultDark
    mock_app = MagicMock()

    # WHEN: set_default_theme() is called
    set_default_theme(mock_app)

    # THEN: set_default_darkmode should be changed
    mock_set_default_darkmode.assert_called_once()


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
@patch('openlp.core.ui.style.set_default_darkmode')
@patch('openlp.core.ui.style.is_system_darkmode')
def test_set_default_theme_automatic_theme_calls_set_default_darkmode(mock_is_system_darkmode,
                                                                      mock_set_default_darkmode, mock_settings):
    """Test that the set_default_theme calls set_default_darkmode for Automatic UI theme on system dark theme"""
    # GIVEN: UI theme is Automatic and System is using Dark Theme
    mock_settings.value.return_value = UiThemes.Automatic
    mock_app = MagicMock()
    mock_is_system_darkmode.return_value = True

    # WHEN: set_default_theme() is called
    set_default_theme(mock_app)

    # THEN: set_default_darkmode should be changed
    mock_set_default_darkmode.assert_called_once()


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
@patch('openlp.core.ui.style.is_system_darkmode')
def test_set_default_theme_automatic_theme_system_light_not_sets_palette(mocked_is_system_darkmode, mock_settings):
    """Test that the set_default_theme doesnt't set App Palette for Automatic UI theme on System Light Theme"""
    # GIVEN: UI theme is Automatic with System Light Theme
    mock_settings.value.return_value = UiThemes.Automatic
    mocked_is_system_darkmode.return_value = False
    mock_app = MagicMock()

    # WHEN: set_default_theme() is called
    set_default_theme(mock_app)

    # THEN: app palette should not be changed
    mock_app.setPalette.assert_not_called()


@patch('openlp.core.ui.style.HAS_DARK_THEME', False)
@patch('openlp.core.ui.style.set_default_lightmode')
def test_set_default_theme_defaultlight_theme_calls_set_default_lightmode(mock_set_default_lightmode, mock_settings):
    """Test that the set_default_theme calls set_default_darkmode for DefaultLight UI theme"""
    # GIVEN: UI theme is DefaultLight
    mock_settings.value.return_value = UiThemes.DefaultLight
    mock_app = MagicMock()

    # WHEN: set_default_theme() is called
    set_default_theme(mock_app)

    # THEN: set_default_darkmode should be changed
    mock_set_default_lightmode.assert_called_once()
