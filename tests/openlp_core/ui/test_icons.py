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
Package to test the openlp.core.ui.icons package.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6 import QtGui

from openlp.core.common import Singleton
from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings
from openlp.core.ui.icons import NOIR_ICON_LIST, UiIcons
from openlp.core.ui.style import NOIR_PLUGIN_ALERTS, NOIR_PLUGIN_BIBLES, NOIR_PLUGIN_CUSTOM, \
    NOIR_PLUGIN_IMAGES, NOIR_PLUGIN_LIBRARY, NOIR_PLUGIN_MEDIA, NOIR_PLUGIN_PRESENTATIONS, \
    NOIR_PLUGIN_SONGS


def test_simple_icon(settings: Settings):
    # GIVEN: an basic set of icons
    with patch('openlp.core.ui.icons.UiIcons.__init__', return_value=None):
        icons = UiIcons()
        icon_list = {
            'active': {'icon': 'mdi.human-handsup'}
        }

        icons.load_icons(icon_list)
        # WHEN: I use the icons
        icon_active = UiIcons().active
        # THEN: I should have an icon
        assert isinstance(icon_active, QtGui.QIcon)


@patch('openlp.core.ui.icons.qta')
@patch('openlp.core.ui.icons.build_icon')
@patch('openlp.core.ui.icons.UiIcons.load_icons')
@patch('openlp.core.ui.icons.AppLocation.get_directory')
def test_uiicons_init(mocked_get_directory: MagicMock, mocked_load_icons: MagicMock, mocked_build_icon: MagicMock,
                      mocked_qta: MagicMock, settings: Settings, registry: Registry, request):
    """Test the __init__ method, that it makes the correct calls"""
    # Set up test cleanup
    def remove_singleton():
        del Singleton._instances[UiIcons]

    request.addfinalizer(remove_singleton)

    # GIVEN: A mocked out qta module, and no instances already created
    remove_singleton()
    mocked_get_directory.return_value = Path('openlp')
    expected_dir = str(Path('openlp', 'core', 'ui', 'fonts'))

    # WHEN: A UiIcons instance is created
    icons = UiIcons()

    # THEN: The mocks should have been called correctly
    mocked_qta.load_font.assert_called_once_with('op', 'OpenLP.ttf', 'openlp-charmap.json', directory=expected_dir)
    mocked_qta.set_defaults.assert_called_once_with(**icons._default_icon_colors)
    mocked_load_icons.assert_called_once_with(icons._icon_list)
    mocked_build_icon.assert_called_once_with(':/icon/openlp-logo.svg')


def test_library_icon_is_distinct_from_bible():
    """The EGW Library icon should not share Bible's glyph"""
    # GIVEN/WHEN: the Noir icon list
    # THEN: library and bible use different Phosphor glyphs
    assert NOIR_ICON_LIST['library']['icon'] == 'ph.books'
    assert NOIR_ICON_LIST['library']['icon'] != NOIR_ICON_LIST['bible']['icon']


@pytest.mark.parametrize('icon_key,expected_color', [
    ('alert', NOIR_PLUGIN_ALERTS),
    ('bible', NOIR_PLUGIN_BIBLES),
    ('custom', NOIR_PLUGIN_CUSTOM),
    ('music', NOIR_PLUGIN_SONGS),
    ('presentation', NOIR_PLUGIN_PRESENTATIONS),
    ('picture', NOIR_PLUGIN_IMAGES),
    ('video', NOIR_PLUGIN_MEDIA),
    ('library', NOIR_PLUGIN_LIBRARY),
])
def test_plugin_icons_have_identity_color(icon_key, expected_color):
    """Each plugin's icon should carry its own identity accent in the Noir icon list"""
    # GIVEN/WHEN: the Noir icon list
    # THEN: the icon's attr matches its plugin's identity color
    assert NOIR_ICON_LIST[icon_key]['attr'] == expected_color


def test_legacy_icon_list_has_library_key(settings: Settings, registry: Registry, request):
    """The legacy (non-Noir) icon list must also define 'library', or non-Noir themes break"""
    # GIVEN: a UiIcons instance built with the Noir theme inactive
    def remove_singleton():
        del Singleton._instances[UiIcons]
    request.addfinalizer(remove_singleton)
    if UiIcons in Singleton._instances:
        remove_singleton()

    with patch('openlp.core.ui.icons.is_ui_theme', return_value=False):
        # WHEN: the icons are loaded
        icons = UiIcons()
        # THEN: the library icon resolves without error
        assert isinstance(icons.library, QtGui.QIcon)
