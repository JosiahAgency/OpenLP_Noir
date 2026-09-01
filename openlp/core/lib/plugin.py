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
Provide the generic plugin functionality for OpenLP plugins.
"""
import logging

from openlp.core.common.enum import PluginStatus
from openlp.core.common.i18n import UiStrings
from openlp.core.common.mixins import RegistryProperties
from openlp.core.common.registry import Registry, RegistryBase
from openlp.core.version import get_version


log = logging.getLogger(__name__)


class StringContent(object):
    """
    Provide standard strings for objects to use.
    """
    Name = 'name'
    Import = 'import'
    Load = 'load'
    New = 'new'
    Edit = 'edit'
    Delete = 'delete'
    Preview = 'preview'
    Live = 'live'
    Service = 'service'
    VisibleName = 'visible_name'


class Plugin(RegistryBase, RegistryProperties):
    """
    Base class for openlp plugins to inherit from.

    **Basic Attributes**

    ``name``
        The name that should appear in the plugins list.

    ``version``
        The version number of this iteration of the plugin.

    ``icon``
        An instance of QIcon, which holds an icon for this plugin.

    ``log``
        A log object used to log debugging messages. This is pre-instantiated.

    ``weight``
        A numerical value used to order the plugins.

    **Hook Functions**

    ``check_pre_conditions()``
        Provides the Plugin with a handle to check if it can be loaded.

    ``create_media_manager_item()``
        Creates a new instance of MediaManagerItem to be used in the Media
        Manager.

    ``add_import_menu_item(import_menu)``
        Add an item to the Import menu.

    ``add_export_menu_item(export_menu)``
        Add an item to the Export menu.

    ``create_settings_tab()``
        Creates a new instance of SettingsTabItem to be used in the Settings
        dialog.

    ``add_to_menu(menubar)``
        A method to add a menu item to anywhere in the menu, given the menu bar.

    ``handle_event(event)``
        A method use to handle events, given an Event object.

    ``about()``
        Used in the plugin manager, when a person clicks on the 'About' button.

    """
    log.info('loaded')

    def __init__(self, name, media_item_class=None, settings_tab_class=None, version=None):
        """
        This is the constructor for the plugin object. This provides an easy way for descendant plugins to populate
         common data. This method *must*

        be overridden, like so::

            class MyPlugin(Plugin):
                def __init__(self):
                    super(MyPlugin, self).__init__('MyPlugin', version='0.1')

        :param name: Defaults to *None*. The name of the plugin.
        :param media_item_class: The class name of the plugin's media item.
        :param settings_tab_class: The class name of the plugin's settings tab.
        :param version: Defaults to *None*, which means that the same version number is used as OpenLP's version number.
        """
        log.debug('Plugin {plugin} initialised'.format(plugin=name))
        super(Plugin, self).__init__()
        self.name = name
        self.text_strings = {}
        self.set_plugin_text_strings()
        self.name_strings = self.text_strings[StringContent.Name]
        self.icon = None
        self.media_item_class = media_item_class
        self.settings_tab_class = settings_tab_class
        self.settings_tab = None
        self.media_item = None
        self.weight = 0
        self.status = PluginStatus.Inactive
        Registry().register_function('{name}_add_service_item'.format(name=self.name), self.process_add_service_event)
        Registry().register_function('{name}_config_updated'.format(name=self.name), self.config_update)
        Registry().register_function('{name}_visible_name'.format(name=self.name), self.get_visible_name)
        self._setup(version)

    def _setup(self, version):
        """
        Run some initial setup. This method is separate from __init__ in order to mock it out in tests.

        :param version: Defaults to *None*, which means that the same version number is used as OpenLP's version number.
        :rtype: None
        """
        if version:
            self.version = version
        else:
            self.version = get_version()['version']

    def check_pre_conditions(self):
        """
        Provides the Plugin with a handle to check if it can be loaded.
        Failing Preconditions does not stop a settings Tab being created

        Returns ``True`` or ``False``.
        """
        return True

    def set_status(self):
        """
        Sets the status of the plugin
        """
        self.status = self.settings.value(f'{self.name}/status')

    def toggle_status(self, new_status):
        """
        Changes the status of the plugin and remembers it
        """
        self.status = new_status
        self.settings.setValue(f'{self.name}/status', self.status)
        if new_status == PluginStatus.Active:
            self.initialise()
        elif new_status == PluginStatus.Inactive:
            self.finalise()

    def is_active(self):
        """
        Indicates if the plugin is active

        Returns True or False.
        """
        return self.status == PluginStatus.Active

    def create_media_manager_item(self):
        """
        Construct a MediaManagerItem object with all the buttons and things
        you need, and return it for integration into OpenLP.
        """
        if self.media_item_class:
            self.media_item = self.media_item_class(self.main_window.media_dock_manager.media_dock, self)

    def upgrade_settings(self, settings):
        """
        Upgrade the settings of this plugin.

        :param settings: The Settings object containing the old settings.
        """
        pass

    def add_import_menu_item(self, import_menu):
        """
        Create a menu item and add it to the "Import" menu.

        :param import_menu: The Import menu.
        """
        pass

    def add_export_menu_item(self, export_menu):
        """
        Create a menu item and add it to the "Export" menu.

        :param export_menu: The Export menu
        """
        pass

    def add_tools_menu_item(self, tools_menu):
        """
        Create a menu item and add it to the "Tools" menu.

        :param tools_menu: The Tools menu
        """
        pass

    def create_settings_tab(self, parent):
        """
        Create a tab for the settings window to display the configurable options
        for this plugin to the user.
        """
        if self.settings_tab_class:
            self.settings_tab = self.settings_tab_class(parent, self.name,
                                                        self.get_string(StringContent.VisibleName)['title'],
                                                        self.icon_path)

    def add_to_menu(self, menubar):
        """
        Add menu items to the menu, given the menubar.

        :param menubar: The application's menu bar.
        """
        pass

    def process_add_service_event(self, replace=False):
        """
        Generic Drag and drop handler triggered from service_manager.
        """
        log.debug('process_add_service_event event called for plugin {name}'.format(name=self.name))
        if replace:
            self.media_item.on_add_edit_click()
        else:
            self.media_item.on_add_click()

    @staticmethod
    def about():
        """
        Show a dialog when the user clicks on the 'About' button in the plugin manager.
        """
        raise NotImplementedError('Plugin.about needs to be defined by the plugin')

    def initialise(self):
        """
        Called by the plugin Manager to initialise anything it needs.
        """
        if self.media_item:
            self.media_item.initialise()
            self.main_window.media_dock_manager.add_item_to_dock(self.media_item)

    def finalise(self):
        """
        Called by the plugin Manager to cleanup things.
        """
        if self.media_item:
            self.main_window.media_dock_manager.remove_dock(self.media_item)

    def app_startup(self):
        """
        Perform tasks on application startup
        """
        pass

    def uses_theme(self, theme):
        """
        Called to find out if a plugin is currently using a theme.

        Returns True if the theme is being used, otherwise returns False.
        """
        return False

    def rename_theme(self, old_theme, new_theme):
        """
        Renames a theme a plugin is using making the plugin use the new name.

        :param old_theme:  The name of the theme the plugin should stop using.
        :param new_theme: The new name the plugin should now use
        """
        pass

    def get_string(self, name):
        """
        Encapsulate access of plugins translated text strings
        """
        return self.text_strings[name]

    def set_plugin_text_strings(self):
        pass

    def set_plugin_ui_text_strings(self, tooltips):
        """
        Called to define all translatable texts of the plugin

        :param tooltips:
        """
        # Load Action
        self.__set_name_text_string(StringContent.Load, UiStrings().Load, tooltips['load'])
        # Import Action
        self.__set_name_text_string(StringContent.Import, UiStrings().Import, tooltips['import'])
        # New Action
        self.__set_name_text_string(StringContent.New, UiStrings().Add, tooltips['new'])
        # Edit Action
        self.__set_name_text_string(StringContent.Edit, UiStrings().Edit, tooltips['edit'])
        # Delete Action
        self.__set_name_text_string(StringContent.Delete, UiStrings().Delete, tooltips['delete'])
        # Preview Action
        self.__set_name_text_string(StringContent.Preview, UiStrings().Preview, tooltips['preview'])
        # Send Live Action
        self.__set_name_text_string(StringContent.Live, UiStrings().Live, tooltips['live'])
        # Add to Service Action
        self.__set_name_text_string(StringContent.Service, UiStrings().Service, tooltips['service'])

    def __set_name_text_string(self, name, title, tooltip):
        """
        Utility method for creating a plugin's text_strings. This method makes use of the singular name of the
        plugin object so must only be called after this has been set.
        """
        self.text_strings[name] = {'title': title, 'tooltip': tooltip}

    def config_update(self):
        """
        Called when Config is changed to restart values dependent on configuration.
        """
        log.info('config update processed')
        if self.media_item:
            self.media_item.config_update()

    def new_service_created(self):
        """
        The plugin's needs to handle a new song creation
        """
        pass

    def get_visible_name(self):
        """
        Returns the plugins visible name
        """
        return str(self.get_string(StringContent.VisibleName)['title'])
