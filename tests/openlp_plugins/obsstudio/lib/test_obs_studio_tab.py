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
Package to test the openlp.plugins.obs_studio.lib.obs_studio_tab package.
"""
import pytest
from unittest.mock import MagicMock, patch
from PyQt5 import QtCore, QtTest, QtWidgets

from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings
from openlp.core.state import State
from openlp.plugins.obs_studio.obs_studio_plugin import ObsStudioPlugin
from openlp.plugins.obs_studio.lib.obs_studio_tab import ObsStudioTab


@pytest.fixture
def plugin(registry: Registry, settings: Settings, state: State) -> ObsStudioPlugin:
    """
    Fixture to create an ObsStudioPlugin instance
    """
    settings.setValue('obs_studio/host', 'localhost')
    settings.setValue('obs_studio/port', '5544')
    settings.setValue('obs_studio/password', 'incorrect_password')
    return ObsStudioPlugin()


@pytest.fixture
def tab(plugin: ObsStudioPlugin) -> ObsStudioTab:
    """
    Fixture to create an ObsStudioTab instance
    """
    dialog = QtWidgets.QDialog()
    obs_studio_tab = ObsStudioTab(dialog, 'OBS Studio')
    obs_studio_tab.setup_ui()
    obs_studio_tab.retranslate_ui()
    obs_studio_tab.load()
    obs_studio_tab.resizeEvent()
    yield obs_studio_tab
    del obs_studio_tab
    del dialog


@patch('openlp.plugins.obs_studio.lib.obs_studio_tab.QtWidgets.QMessageBox.warning')
def test_incorrect_port(mocked_warning: MagicMock, tab: ObsStudioTab):
    """
    Test that the tab can be created and test button clicked with an incorrect port
    """
    # GIVEN: A ObsStudioTab Class with an incorrect port
    # WHEN: The test button is clicked
    QtTest.QTest.mouseClick(tab.test_button, QtCore.Qt.LeftButton)

    # THEN: The warning messagebox should be called
    mocked_warning.assert_called_once()


def test_save_obs_studio_settings(settings: Settings, tab: ObsStudioTab):
    """
    Test that OBS Studio settings are saved in settings when the save function is called
    """
    # GIVEN: A ObsStudioTab Class
    # WHEN: host, port and password are set to something and the save function is called
    tab.host_line_edit.setText('localhost')
    tab.port_line_edit.setText('4455')
    tab.password_line_edit.setText('correct_password')
    tab.save()
    # THEN: The settings version of host, port and password should reflect the new values
    host = settings.value('obs_studio/host')
    port = settings.value('obs_studio/port')
    password = settings.value('obs_studio/password')
    assert host == 'localhost'
    assert port == 4455
    assert password == 'correct_password'
