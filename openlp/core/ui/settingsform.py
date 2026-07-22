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
The :mod:`settingsform` provides a user interface for the OpenLP settings
"""
import logging

from PySide6 import QtCore, QtWidgets, QtGui

from openlp.core.state import State
from openlp.core.api.tab import ApiTab
from openlp.core.common.mixins import RegistryProperties
from openlp.core.common.registry import Registry
from openlp.core.lib import build_icon
from openlp.core.projectors.tab import ProjectorTab
from openlp.core.ui.advancedtab import AdvancedTab
from openlp.core.ui.generaltab import GeneralTab
from openlp.core.ui.servicetab import ServiceTab
from openlp.core.ui.screenstab import ScreensTab
from openlp.core.ui.themestab import ThemesTab
from openlp.core.ui.media.mediatab import MediaTab
from openlp.core.ui.settingsdialog import Ui_SettingsDialog


log = logging.getLogger(__name__)


class SettingsForm(QtWidgets.QDialog, Ui_SettingsDialog, RegistryProperties):
    """
    Provide the form to manipulate the settings for OpenLP
    """
    def __init__(self, parent=None):
        """
        Initialise the settings form
        """
        Registry().register('settings_form', self)
        Registry().register_function('bootstrap_post_set_up', self.bootstrap_post_set_up)
        super(SettingsForm, self).__init__(parent,
                                           QtCore.Qt.WindowType.WindowSystemMenuHint |
                                           QtCore.Qt.WindowType.WindowTitleHint |
                                           QtCore.Qt.WindowType.WindowCloseButtonHint)
        self.processes = []
        self.setup_ui(self)
        self.setting_list_widget.currentRowChanged.connect(self.list_item_changed)
        self.general_tab = None
        self.service_tab = None
        self.themes_tab = None
        self.player_tab = None
        self.projector_tab = None
        self.advanced_tab = None
        self.api_tab = None

    def exec(self, starting_tab_name=None):
        """
        Execute the form
        """
        # load all the widgets
        self.setting_list_widget.blockSignals(True)
        self.setting_list_widget.clear()
        while self.stacked_layout.count():
            # take at 0 and the rest shuffle up.
            self.stacked_layout.takeAt(0)
        self.insert_tab(self.general_tab)
        self.insert_tab(self.service_tab)
        self.insert_tab(self.advanced_tab)
        self.insert_tab(self.screens_tab)
        self.insert_tab(self.themes_tab)
        self.insert_tab(self.player_tab)
        self.insert_tab(self.projector_tab)
        self.insert_tab(self.api_tab)
        for plugin in State().list_plugins():
            if plugin.settings_tab:
                self.insert_tab(plugin.settings_tab, plugin.is_active())
        self.setting_list_widget.blockSignals(False)
        starting_tab_row = 0
        for index in range(self.setting_list_widget.count()):
            item = self.setting_list_widget.item(index)
            if item.text() == starting_tab_name:
                starting_tab_row = index
                break
        self.setting_list_widget.setCurrentRow(starting_tab_row)
        return QtWidgets.QDialog.exec(self)

    def insert_tab(self, tab_widget, is_visible=True):
        """
        Add a tab to the form at a specific location

        :param tab_widget: The widget to add
        :param is_visible: If this tab should be visible
        """
        log.debug('Inserting {text} tab'.format(text=tab_widget.tab_title))
        # add the tab to get it to display in the correct part of the screen
        self.stacked_layout.addWidget(tab_widget)
        if is_visible:
            list_item = QtWidgets.QListWidgetItem(build_icon(tab_widget.icon_path), tab_widget.tab_title_visible)
            list_item.setData(QtCore.Qt.ItemDataRole.UserRole, tab_widget.tab_title)
            self.setting_list_widget.addItem(list_item)
            tab_widget.load()

    def accept(self):
        """
        Process the form saving the settings
        """
        log.debug('Processing settings exit')
        # We add all the forms into the stacked layout, even if the plugin is inactive,
        # but we don't add the item to the list on the side if the plugin is inactive,
        # so loop through the list items, and then find the tab for that item.
        for item_index in range(self.setting_list_widget.count()):
            # Get the list item
            list_item = self.setting_list_widget.item(item_index)
            if not list_item:
                continue
            # Now figure out if there's a tab for it, and save the tab.
            plugin_name = list_item.data(QtCore.Qt.ItemDataRole.UserRole)
            for tab_index in range(self.stacked_layout.count()):
                tab_widget = self.stacked_layout.widget(tab_index)
                if tab_widget.tab_title == plugin_name:
                    tab_widget.save()
        # Now lets process all the post save handlers
        while self.processes:
            process = self.processes.pop(0)
            if isinstance(process, tuple):
                Registry().execute(process[0], *process[1:])
            else:
                Registry().execute(process)
        return QtWidgets.QDialog.accept(self)

    def reject(self):
        """
        Process the form saving the settings
        """
        self.processes = []
        # Same as accept(), we need to loop over the visible tabs, and skip the inactive ones
        for item_index in range(self.setting_list_widget.count()):
            # Get the list item
            list_item = self.setting_list_widget.item(item_index)
            if not list_item:
                continue
            # Now figure out if there's a tab for it, and save the tab.
            plugin_name = list_item.data(QtCore.Qt.ItemDataRole.UserRole)
            for tab_index in range(self.stacked_layout.count()):
                tab_widget = self.stacked_layout.widget(tab_index)
                if tab_widget.tab_title == plugin_name:
                    tab_widget.cancel()
        return QtWidgets.QDialog.reject(self)

    def bootstrap_post_set_up(self):
        """
        Run any post-setup code for the tabs on the form
        """
        try:
            self.general_tab = GeneralTab(self)
            self.service_tab = ServiceTab(self)
            self.themes_tab = ThemesTab(self)
            self.projector_tab = ProjectorTab(self)
            self.advanced_tab = AdvancedTab(self)
            self.player_tab = MediaTab(self)
            self.api_tab = ApiTab(self)
            self.screens_tab = ScreensTab(self)
        except Exception as e:
            print(e)
        self.general_tab.post_set_up()
        self.themes_tab.post_set_up()
        self.advanced_tab.post_set_up()
        self.player_tab.post_set_up()
        self.api_tab.post_set_up()
        for plugin in State().list_plugins():
            if plugin.settings_tab:
                plugin.settings_tab.post_set_up()

    def list_item_changed(self, item_index):
        """
        A different settings tab is selected

        :param item_index: The index of the item that was selected
        """
        # Get the item we clicked on
        list_item = self.setting_list_widget.item(item_index)
        # Quick exit to the left if the item doesn't exist (maybe -1?)
        if not list_item:
            return
        # Loop through the list of tabs in the stacked layout
        for tab_index in range(self.stacked_layout.count()):
            # Get the widget
            tab_widget = self.stacked_layout.itemAt(tab_index).widget()
            # Check that the title of the tab (i.e. plugin name) is the same as the data in the list item
            if tab_widget.tab_title == list_item.data(QtCore.Qt.ItemDataRole.UserRole):
                # Make the matching tab visible
                tab_widget.tab_visited = True
                self.stacked_layout.setCurrentIndex(tab_index)
                self.stacked_layout.currentWidget().tab_visible()

    def register_post_process(self, function, *args):
        """
        Register for updates to be done on save removing duplicate functions

        :param function: The event name or function to be called
        :param args: Optional arguments to pass to the event handler
        """
        if args:
            process_tuple = (function,) + args
            if process_tuple not in self.processes:
                self.processes.append(process_tuple)
        else:
            if function not in self.processes:
                self.processes.append(function)

    def provide_help(self):
        """
        Provide help within the form by opening the appropriate page of the openlp manual in the user's browser
        """
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://manual.openlp.org/configure.html"))
