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
Timer plugin.
"""
import logging

from openlp.core.state import State
from openlp.core.common.actions import ActionList
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.registry import Registry
from openlp.core.db.manager import DBManager
from openlp.core.lib import build_icon
from openlp.core.lib.plugin import Plugin, StringContent
from openlp.core.ui.icons import UiIcons
from openlp.plugins.timer.lib.db import TimerItem, init_schema
from openlp.plugins.timer.lib.mediaitem import TimerMediaItem
from openlp.plugins.timer.lib.overlaymanager import TimerOverlayManager
from openlp.plugins.timer.lib.timertab import TimerTab

log = logging.getLogger(__name__)


class TimerPlugin(Plugin):
    """
    Timer plugin with media-manager presets and live overlay controls.
    """
    log.info('Timer Plugin loaded')

    def __init__(self):
        super().__init__('timer', TimerMediaItem, TimerTab)
        self.weight = -1
        self.db_manager = DBManager('timer', init_schema)
        self.icon_path = UiIcons().clock
        self.icon = build_icon(self.icon_path)
        self.overlay_manager = TimerOverlayManager(self)
        Registry().register('timer_manager', self.db_manager)
        Registry().register('timer_overlay_manager', self.overlay_manager)
        State().add_service(self.name, self.weight, is_plugin=True)
        State().update_pre_conditions(self.name, self.check_pre_conditions())

    @staticmethod
    def about():
        return translate('TimerPlugin',
                         '<strong>Timer Plugin</strong><br />The timer plugin provides countdown and count-up timer '
                         'presets for the service and ad-hoc timer overlays for live display.')

    def check_pre_conditions(self):
        return self.db_manager.session is not None

    def initialise(self):
        super().initialise()
        if getattr(self, 'tools_timer_item', None):
            self.tools_timer_item.setVisible(False)
            ActionList.get_instance().remove_action(self.tools_timer_item, UiStrings().Tools)

    def finalise(self):
        self.overlay_manager.stop()
        self.db_manager.finalise()
        super().finalise()
        if getattr(self, 'tools_timer_item', None):
            self.tools_timer_item.setVisible(False)
            ActionList.get_instance().remove_action(self.tools_timer_item, UiStrings().Tools)

    def add_tools_menu_item(self, tools_menu):
        # Timer controls are provided directly in the Timer plugin pane.
        self.tools_timer_item = None

    def uses_theme(self, theme):
        count = 1 if str(self.settings_tab.timer_theme) == theme else 0
        count += len(self.db_manager.get_all_objects(TimerItem, TimerItem.theme_name == theme))
        return count

    def rename_theme(self, old_theme, new_theme):
        if self.settings_tab.timer_theme == old_theme:
            self.settings_tab.timer_theme = new_theme
            self.settings_tab.save()
        timer_items = self.db_manager.get_all_objects(TimerItem, TimerItem.theme_name == old_theme)
        for timer_item in timer_items:
            timer_item.theme_name = new_theme
            self.db_manager.save_object(timer_item)

    def set_plugin_text_strings(self):
        self.text_strings[StringContent.Name] = {
            'singular': translate('TimerPlugin', 'Timer', 'name singular'),
            'plural': translate('TimerPlugin', 'Timers', 'name plural')
        }
        self.text_strings[StringContent.VisibleName] = {
            'title': translate('TimerPlugin', 'Timers', 'container title')
        }
        tooltips = {
            'load': '',
            'import': '',
            'new': translate('TimerPlugin', 'Add a new timer preset.'),
            'edit': translate('TimerPlugin', 'Edit the selected timer preset.'),
            'delete': translate('TimerPlugin', 'Delete the selected timer preset.'),
            'preview': translate('TimerPlugin', 'Preview the selected timer preset.'),
            'live': translate('TimerPlugin', 'Send the selected timer preset live.'),
            'service': translate('TimerPlugin', 'Add the selected timer preset to the service.')
        }
        self.set_plugin_ui_text_strings(tooltips)
