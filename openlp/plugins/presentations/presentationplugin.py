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
The :mod:`openlp.plugins.presentations.presentationplugin` module provides the ability for OpenLP to display
presentations from a variety of document formats.
"""
import logging
import os
from pathlib import Path

from openlp.core.common import extension_loader, sha256_file_hash
from openlp.core.common.applocation import AppLocation
from openlp.core.common.i18n import translate
from openlp.core.lib import build_icon
from openlp.core.db.manager import DBManager
from openlp.core.lib.plugin import Plugin, StringContent
from openlp.core.state import State
from openlp.core.ui.icons import UiIcons

from openlp.plugins.presentations.lib.db import Item, init_schema
from openlp.plugins.presentations.lib.presentationcontroller import PresentationController
from openlp.plugins.presentations.lib.mediaitem import PresentationMediaItem
from openlp.plugins.presentations.lib.presentationtab import PresentationTab


log = logging.getLogger(__name__)


class PresentationPlugin(Plugin):
    """
    This plugin allowed a Presentation to be opened, controlled and displayed on the output display. The plugin controls
    third party applications such as OpenOffice.org Impress, and Microsoft PowerPoint.
    """
    log = logging.getLogger('PresentationPlugin')

    def __init__(self):
        """
        PluginPresentation constructor.
        """
        super().__init__('presentations', PresentationMediaItem)
        self.manager = DBManager(plugin_name='presentations', init_schema=init_schema)
        self.weight = -8
        self.icon_path = UiIcons().presentation
        self.icon = build_icon(self.icon_path)
        self.controllers = {}
        self.dnd_id = 'Presentations'
        State().add_service('presentation', self.weight, is_plugin=True)
        State().update_pre_conditions('presentation', self.check_pre_conditions())

    def create_settings_tab(self, parent):
        """
        Create the settings Tab.
        :param parent: parent UI Element
        """
        visible_name = self.get_string(StringContent.VisibleName)
        self.settings_tab = PresentationTab(parent, self.name, visible_name['title'], self.controllers, self.icon_path)

    def initialise(self):
        """
        Initialise the plugin. Determine which controllers are enabled are start their processes.
        """
        log.info('Presentations Initialising')
        # Migrate each file
        presentation_paths = self.settings.value('presentations/presentations files') or []
        for presentation_path in presentation_paths:
            # Typecast to Path object
            path = Path(presentation_path)
            # check to see if the file exists before trying to process it.
            if not path.exists():
                continue
            item = Item(name=path.name, file_path=str(path))
            self.media_item.clean_up_thumbnails(path, clean_for_update=True)
            item.file_hash = sha256_file_hash(path)
            self.manager.save_object(item)
        self.settings.remove('presentations/presentations files')
        super().initialise()
        for controller in self.controllers:
            if self.controllers[controller].enabled():
                try:
                    self.controllers[controller].start_process()
                except Exception:
                    log.exception('Failed to start controller process')
                    self.controllers[controller].available = False
        self.media_item.build_file_mask_string()

    def finalise(self):
        """
        Finalise the plugin. Ask all the enabled presentation applications to close down their applications and release
        resources.
        """
        log.info('Plugin Finalise')
        # Ask each controller to tidy up.
        for key in self.controllers:
            controller = self.controllers[key]
            if controller.enabled():
                controller.kill()
        super(PresentationPlugin, self).finalise()

    def create_media_manager_item(self):
        """
        Create the Media Manager List.
        """
        self.media_item = PresentationMediaItem(self.main_window.media_dock_manager.media_dock, self, self.controllers)

    def register_controllers(self, controller):
        """
        Register each presentation controller (Impress, PPT etc) and store for later use.
        :param controller: controller to register
        """
        self.controllers[controller.name] = controller

    def check_pre_conditions(self):
        """
        Check to see if we have any presentation software available. If not do not install the plugin.
        """
        log.debug('check_pre_conditions')
        controller_dir = os.path.join('plugins', 'presentations', 'lib')
        # Find all files that do not begin with '.' (lp:#1738047) and end with controller.py
        glob_pattern = os.path.join(controller_dir, '[!.]*controller.py')
        extension_loader(AppLocation.get_directory(AppLocation.AppDir), glob_pattern, ['presentationcontroller.py'])
        controller_classes = PresentationController.__subclasses__()
        for controller_class in controller_classes:
            # Don't use classes marked as base
            if hasattr(controller_class, 'base_class') and controller_class.base_class:
                controller_classes.extend(controller_class.__subclasses__())
                continue
            controller = controller_class(self)
            self.register_controllers(controller)
        return bool(self.controllers)

    @staticmethod
    def about():
        """
        Return information about this plugin.
        """
        about_text = translate('PresentationPlugin', '<strong>Presentation '
                               'Plugin</strong><br />The presentation plugin provides the '
                               'ability to show presentations using a number of different '
                               'programs. The choice of available presentation programs is '
                               'available to the user in a drop down box.')
        return about_text

    def set_plugin_text_strings(self):
        """
        Called to define all translatable texts of the plugin.
        """
        # Name PluginList
        self.text_strings[StringContent.Name] = {
            'singular': translate('PresentationPlugin', 'Presentation', 'name singular'),
            'plural': translate('PresentationPlugin', 'Presentations', 'name plural')
        }
        # Name for MediaDockManager, SettingsManager
        self.text_strings[StringContent.VisibleName] = {
            'title': translate('PresentationPlugin', 'Presentations', 'container title')
        }
        # Middle Header Bar
        tooltips = {
            'load': translate('PresentationPlugin', 'Load a new presentation.'),
            'import': '',
            'new': '',
            'edit': '',
            'delete': translate('PresentationPlugin', 'Delete the selected presentation.'),
            'preview': translate('PresentationPlugin', 'Preview the selected presentation.'),
            'live': translate('PresentationPlugin', 'Send the selected presentation live.'),
            'service': translate('PresentationPlugin', 'Add the selected presentation to the service.')
        }
        self.set_plugin_ui_text_strings(tooltips)
