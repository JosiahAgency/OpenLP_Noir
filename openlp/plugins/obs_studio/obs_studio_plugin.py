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
The :mod:`~openlp.plugins.obs_studio.obs_studio_plugin` module contains
the Plugin class for the OBS Studio plugin.
"""
import logging
from typing import Optional, Required

from openlp.core.common.i18n import translate
from openlp.core.lib.plugin import Plugin, StringContent
from openlp.core.state import State
from openlp.core.ui.icons import UiIcons
from openlp.plugins.obs_studio.lib.message_listener import MessageListener
from openlp.plugins.obs_studio.lib.obs_studio_tab import ObsStudioTab

log = logging.getLogger(__name__)


class ObsStudioPlugin(Plugin):
    """
    This plugin enables the user to control scenes in OBS Studio.
    """
    log.info('OBS Studio Plugin loaded')

    def __init__(self):
        """
        Create and set up the OBS Studio plugin.
        """
        super().__init__('obs_studio', settings_tab_class=ObsStudioTab)
        self.icon = UiIcons().obs_studio
        self.icon_path = self.icon
        self.weight = -2
        self.host: Required[str] = None
        self.port: Required[int] = None
        self.password: Optional[str] = None
        State().add_service('obs_studio', self.weight, is_plugin=True)
        State().update_pre_conditions('obs_studio', self.check_pre_conditions())
        self.host = self.settings.value('obs_studio/host')
        self.port = int(self.settings.value('obs_studio/port'))
        self.password = self.settings.value('obs_studio/password')
        self.message_listener = MessageListener(self.host, self.port, self.password)

    def initialise(self):
        """
        Initialise the plugin
        """
        log.info('OBS Studio Plugin Initialising')
        super().initialise()
        self.message_listener.is_active = self.is_active()

    def set_plugin_text_strings(self):
        """
        Called to define all translatable texts of the plugin
        """
        # Name PluginList
        self.text_strings[StringContent.Name] = {
            'singular': translate('ObsStudioPlugin', 'OBS Studio',
                                  'name singular'),
            'plural': translate('ObsStudioPlugin', 'OBS Studio',
                                'name plural')
        }
        # Name for MediaDockManager, SettingsManager
        self.text_strings[StringContent.VisibleName] = {
            'title': translate('ObsStudioPlugin', 'OBS Studio',
                               'container title')
        }
        # Middle Header Bar
        tooltips = {
            'load': '',
            'import': '',
            'new': '',
            'edit': '',
            'delete': '',
            'preview': '',
            'live': '',
            'service': '',
        }
        self.set_plugin_ui_text_strings(tooltips)

    @staticmethod
    def about():
        """
        Provides information for the plugin manager to display.

        :return: A translatable string with some basic information about the
        OBS Studio plugin
        """
        return '<strong>OBS Studio Plugin</strong><br/>The OBS Studio plugin uses websocket \
messages to control scenes in OBS by using the Advanced Scene Switcher plugin.'

    def finalise(self):
        """
        Tidy up on exit.
        """
        log.info('OBS Studio Plugin Finalising')
        self.message_listener.is_active = self.is_active()
        self.message_listener.finalise()
        super().finalise()
