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
This module contains tests for the plugin class Presentation plugin.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

from openlp.plugins.presentations.presentationplugin import PresentationPlugin
from openlp.plugins.presentations.lib.presentationtab import PresentationTab


TEST_RESOURCES_PATH = Path(__file__) / '..' / '..' / '..' / 'resources'


def test_plugin_about():
    result = PresentationPlugin.about()

    assert result == (
        '<strong>Presentation '
        'Plugin</strong><br />The presentation plugin provides the '
        'ability to show presentations using a number of different '
        'programs. The choice of available presentation programs is '
        'available to the user in a drop down box.'
    )


@patch('openlp.core.common.applocation.create_paths')
@patch('openlp.plugins.presentations.lib.presentationcontroller.create_paths')
@patch('openlp.plugins.presentations.lib.presentationcontroller.PresentationController.is_available')
def test_create_settings_tab(mocked_pres_ctrl_is_available, mocked_create_paths1, mocked_create_paths2, qapp, state,
                             registry, settings):
    """Test creating the settings tab"""
    # GIVEN: A Presentations plugin and mocked PresentationController.is_available
    presentations_plugin = PresentationPlugin()
    mocked_pres_ctrl_is_available.return_value = True

    # WHEN: create_settings_tab is run
    presentations_plugin.create_settings_tab(None)

    # THEN: A settings tab should have been created
    assert isinstance(presentations_plugin.settings_tab, PresentationTab)


@patch('openlp.core.common.applocation.create_paths')
@patch('openlp.plugins.presentations.lib.presentationcontroller.create_paths')
@patch('openlp.plugins.presentations.presentationplugin.DBManager')
def test_initialise(MockedManager, mocked_create_paths1, mocked_create_paths2, state, registry, mock_settings):
    """Test that initialising the plugin works correctly"""
    # GIVEN: Some initial values needed for intialisation and a presentations plugin
    mock_settings.setValue.side_effect = [None, [str(TEST_RESOURCES_PATH / 'presentations' / 'test.ppt')]]
    mocked_main_window = MagicMock()
    registry.register('main_window', mocked_main_window)
    presentations_plugin = PresentationPlugin()
    presentations_plugin.media_item = MagicMock()

    # WHEN: initialise() is called
    presentations_plugin.initialise()

    # THEN: Nothing should break, and everything should be called
    mock_settings.remove.assert_called_once_with('presentations/presentations files')
