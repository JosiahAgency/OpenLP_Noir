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

import logging

from openlp.core.state import State
from openlp.core.common.actions import ActionList
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.db.manager import DBManager
from openlp.core.lib.plugin import Plugin, StringContent
from openlp.core.lib.theme import VerticalType
from openlp.core.lib.ui import create_action
from openlp.core.ui.icons import UiIcons
from openlp.plugins.alerts.forms.alertform import AlertForm
from openlp.plugins.alerts.lib.alertsmanager import AlertsManager
from openlp.plugins.alerts.lib.alertstab import AlertsTab
from openlp.plugins.alerts.lib.db import init_schema


log = logging.getLogger(__name__)

JAVASCRIPT = """
    function show_alert(alerttext, position){
        var text = document.getElementById('alert');
        text.innerHTML = alerttext;
        if(alerttext == '') {
            text.style.visibility = 'hidden';
            return 0;
        }
        if(position == ''){
            position = getComputedStyle(text, '').verticalAlign;
        }
        switch(position)
        {
            case 'top':
                text.style.top = '0px';
                break;
            case 'middle':
                text.style.top = ((window.innerHeight - text.clientHeight) / 2)
                    + 'px';
                break;
            case 'bottom':
                text.style.top = (window.innerHeight - text.clientHeight)
                    + 'px';
                break;
        }
        text.style.visibility = 'visible';
        return text.clientHeight;
    }

    function update_css(align, font, size, color, bgcolor){
        var text = document.getElementById('alert');
        text.style.fontSize = size + "pt";
        text.style.fontFamily = font;
        text.style.color = color;
        text.style.backgroundColor = bgcolor;
        switch(align)
        {
            case 'top':
                text.style.top = '0px';
                break;
            case 'middle':
                text.style.top = ((window.innerHeight - text.clientHeight) / 2)
                    + 'px';
                break;
            case 'bottom':
                text.style.top = (window.innerHeight - text.clientHeight)
                    + 'px';
                break;
        }
    }
"""
CSS = """
    #alert {{
        position: absolute;
        left: 0px;
        top: 0px;
        z-index: 10;
        width: 100%;
        vertical-align: {vertical_align};
        font-family: {font_family};
        font-size: {font_size:d}pt;
        color: {color};
        background-color: {background_color};
        word-wrap: break-word;
    }}
"""

HTML = """
    <div id="alert" style="visibility:hidden"></div>
"""


class AlertsPlugin(Plugin):
    """
    The Alerts Plugin Class
    """
    log.info('Alerts Plugin loaded')

    def __init__(self):
        """
        Class __init__ method
        """
        super(AlertsPlugin, self).__init__('alerts', settings_tab_class=AlertsTab)
        self.weight = -3
        self.icon_path = UiIcons().alert
        self.icon = self.icon_path
        AlertsManager(self)
        self.manager = DBManager('alerts', init_schema)
        self.alert_form = AlertForm(self)
        State().add_service(self.name, self.weight, is_plugin=True)
        State().update_pre_conditions(self.name, self.check_pre_conditions())

    def initialise(self):
        """
        Initialise plugin
        """
        log.info('Alerts Initialising')
        super(AlertsPlugin, self).initialise()
        self.tools_alert_item.setVisible(True)
        action_list = ActionList.get_instance()
        action_list.add_action(self.tools_alert_item, UiStrings().Tools)

    def finalise(self):
        """
        Tidy up on exit
        """
        log.info('Alerts Finalising')
        self.manager.finalise()
        super(AlertsPlugin, self).finalise()
        self.tools_alert_item.setVisible(False)
        action_list = ActionList.get_instance()
        action_list.remove_action(self.tools_alert_item, 'Tools')

    def add_tools_menu_item(self, tools_menu):
        """
        Give the alerts plugin the opportunity to add items to the **Tools** menu.

        :param tools_menu: The actual **Tools** menu item, so that your actions can use it as their parent.
        """
        log.info('add tools menu')
        self.tools_alert_item = create_action(tools_menu, 'toolsAlertItem',
                                              text=translate('AlertsPlugin', '&Alert'),
                                              icon=UiIcons().alert,
                                              statustip=translate('AlertsPlugin', 'Show an alert message.'),
                                              visible=False, can_shortcuts=True, triggers=self.on_alerts_trigger)
        self.main_window.tools_menu.addAction(self.tools_alert_item)
        # Also expose the alert action at the top level of the menu bar, before Help, for quick
        # access during a live service. The same action backs both entries, so visibility and
        # shortcuts stay in sync.
        self.main_window.menu_bar.insertAction(self.main_window.help_menu.menuAction(), self.tools_alert_item)

    def toggle_alerts_state(self):
        """
        Switch the alerts state
        """
        self.alerts_active = not self.alerts_active
        self.settings.setValue('alerts/active', self.alerts_active)

    def on_alerts_trigger(self):
        """
        Start of the Alerts dialog triggered from the main menu.
        """
        self.alert_form.load_list()
        self.alert_form.exec()

    @staticmethod
    def about():
        """
        Plugin Alerts about method

        :return: text
        """
        about_text = translate('AlertsPlugin', '<strong>Alerts Plugin</strong>'
                               '<br />The alert plugin controls the displaying of alerts on the display screen.')
        return about_text

    def set_plugin_text_strings(self):
        """
        Called to define all translatable texts of the plugin
        """
        # Name PluginList
        self.text_strings[StringContent.Name] = {
            'singular': translate('AlertsPlugin', 'Alert', 'name singular'),
            'plural': translate('AlertsPlugin', 'Alerts', 'name plural')
        }
        # Name for MediaDockManager, SettingsManager
        self.text_strings[StringContent.VisibleName] = {
            'title': translate('AlertsPlugin', 'Alerts', 'container title')
        }

    @staticmethod
    def get_display_javascript():
        """
        Add Javascript to the main display.
        """
        return JAVASCRIPT

    def get_display_css(self):
        """
        Add CSS to the main display.
        """
        align = VerticalType.Names[self.settings_tab.location]
        return CSS.format(vertical_align=align,
                          font_family=self.settings_tab.font_face,
                          font_size=self.settings_tab.font_size,
                          color=self.settings_tab.font_color,
                          background_color=self.settings_tab.background_color)

    @staticmethod
    def get_display_html():
        """
        Add HTML to the main display.
        """
        return HTML

    def refresh_css(self, frame):
        """
        Trigger an update of the CSS in the main display.

        :param frame: The Web frame holding the page.
        """
        align = VerticalType.Names[self.settings_tab.location]
        frame.runJavaScript('update_css("{align}", "{face}", "{size}", "{color}", '
                            '"{background}")'.format(align=align,
                                                     face=self.settings_tab.font_face,
                                                     size=self.settings_tab.font_size,
                                                     color=self.settings_tab.font_color,
                                                     background=self.settings_tab.background_color))
