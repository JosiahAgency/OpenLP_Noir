##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2025 OpenLP Developers                                   #
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
Package to test the openlp.plugins.obs_studio.obs_studio_plugin package.
"""
from unittest.mock import MagicMock, patch
import pytest

from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings
from openlp.core.state import State
from openlp.core.ui.icons import UiIcons
from openlp.plugins.obs_studio.obs_studio_plugin import ObsStudioPlugin


@pytest.fixture
def plugin(qapp, settings: Settings, state: State, registry: Registry):
    """
    Fixture to provide a ObsStudioPlugin instance with mocked dependencies
    """
    with patch(
        "openlp.plugins.obs_studio.lib.message_listener.MessageListener.__init__",
        return_value=None
    ):
        plugin_instance = ObsStudioPlugin()
    return plugin_instance


def test_class_init_defaults(plugin: ObsStudioPlugin):
    """
    Test that the plugin class is instantiated with the correct defaults
    """
    # GIVEN: A ObsStudioPlugin Class
    # WHEN:  the class has been through __init__
    # THEN:
    # icon is set correctly
    assert plugin.icon == UiIcons().obs_studio, "Init icon set to obs_studio icon"
    # weight is -2
    assert plugin.weight == -2, "Init weight set to -2"
    # the obs_studio module is registered active
    assert State().is_module_active('obs_studio') is True, "Init State() is active"


def test_initialise(plugin: ObsStudioPlugin):
    """
    Test that the initialise function can be called and it passes a call along
    to its parent class
    """
    # GIVEN: A ObsStudioPlugin Class
    # WHEN:  initialise has been called on the class
    with patch('openlp.plugins.obs_studio.obs_studio_plugin.ObsStudioPlugin',
               create=True):
        return_value = plugin.initialise()
    # THEN:
    # the function returns and does not fail... it doesn't do much at this point, so this
    # is mainly to improve test coverage
    assert return_value is None, "Initialise was called on the class and it didn't crash"


def test_finalise(plugin: ObsStudioPlugin):
    """
    Test that the finalise function cleans up after the plugin
    """
    # GIVEN: A ObsStudioPlugin Class with a bunch of mocks
    with patch('openlp.plugins.obs_studio.obs_studio_plugin.ObsStudioPlugin',
               create=True):
        plugin.initialise()
    plugin.message_listener.finalise = MagicMock()

    # WHEN: finalise has been called on the class
    plugin.finalise()

    # THEN: it cleans up after itself
    plugin.message_listener.finalise.assert_called_once()


def test_about(plugin: ObsStudioPlugin):
    """
    Test that the finalise function cleans up after the plugin
    """
    # GIVEN: A ObsStudioPlugin Class
    # WHEN: about has been called on the class
    result = plugin.about()

    # THEN: it returns the correct about text
    assert result == '<strong>OBS Studio Plugin</strong><br/>The OBS Studio plugin uses websocket \
messages to control scenes in OBS by using the Advanced Scene Switcher plugin.'
