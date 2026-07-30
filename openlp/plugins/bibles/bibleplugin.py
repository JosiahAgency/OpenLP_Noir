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
from openlp.core.ui.icons import UiIcons
from openlp.core.lib.plugin import Plugin, StringContent
from openlp.core.lib.ui import create_action
from openlp.plugins.bibles.lib.biblestab import BiblesTab
from openlp.plugins.bibles.lib.manager import BibleManager
from openlp.plugins.bibles.lib.mediaitem import BibleMediaItem


log = logging.getLogger(__name__)


class BiblePlugin(Plugin):
    """
    The Bible plugin provides a plugin for managing and displaying Bibles.
    """
    log.info('Bible Plugin loaded')

    def __init__(self):
        log.debug('Bible Plugin __init__')
        super(BiblePlugin, self).__init__('bibles', BibleMediaItem, BiblesTab)
        self.weight = -9
        self.icon_path = UiIcons().bible
        self.icon = UiIcons().bible
        self.manager = BibleManager(self)
        State().add_service('bible', self.weight, is_plugin=True)
        State().update_pre_conditions('bible', self.check_pre_conditions())
        log.debug('Bible Plugin __init__ complete')

    def initialise(self):
        """
        Initialise the Bible plugin.
        """
        log.info('bibles Initialising')
        super(BiblePlugin, self).initialise()
        self.import_bible_item.setVisible(True)
        action_list = ActionList.get_instance()
        action_list.add_action(self.import_bible_item, UiStrings().Import)
        # Set to invisible until we can export bibles
        self.export_bible_item.setVisible(False)

    def finalise(self):
        """
        Tidy up on exit
        """
        log.info('Plugin Finalise')
        self.manager.finalise()
        Plugin.finalise(self)
        action_list = ActionList.get_instance()
        action_list.remove_action(self.import_bible_item, UiStrings().Import)
        self.import_bible_item.setVisible(False)
        self.export_bible_item.setVisible(False)
        log.debug('Bible Plugin finalise complete')

    def add_import_menu_item(self, import_menu):
        """
        Add an import menu item

        :param import_menu: The menu to insert the menu item into.
        """
        log.debug('add_import_menu_item')
        self.import_bible_item = create_action(import_menu, 'importBibleItem',
                                               text=translate('BiblesPlugin', '&Bible'), visible=False,
                                               triggers=self.on_bible_import_click)
        import_menu.addAction(self.import_bible_item)

    def add_export_menu_item(self, export_menu):
        """
        Add an export menu item

        :param export_menu: The menu to insert the menu item into.
        """
        log.debug('add_export_menu_item')
        self.export_bible_item = create_action(export_menu, 'exportBibleItem',
                                               text=translate('BiblesPlugin', '&Bible'), visible=False)
        export_menu.addAction(self.export_bible_item)

    def on_bible_import_click(self):
        """
        Show the Bible Import wizard
        """
        log.debug('on_bible_import_click')
        if self.media_item:
            self.media_item.on_import_click()

    @staticmethod
    def about():
        """
        Return the about text for the plugin manager
        """
        about_text = translate('BiblesPlugin', '<strong>Bible Plugin</strong>'
                               '<br />The Bible plugin provides the ability to display Bible '
                               'verses from different sources during the service.')
        return about_text

    def uses_theme(self, theme):
        """
        Called to find out if the bible plugin is currently using a theme.

        :param theme: The theme
        :return: 1 if the theme is being used, otherwise returns 0
        """
        in_use = 1 if str(self.settings_tab.bible_theme) == theme else 0
        log.debug('uses_theme {theme}: {in_use}'.format(theme=theme, in_use=in_use))
        return in_use

    def rename_theme(self, old_theme, new_theme):
        """
        Rename the theme the bible plugin is using, making the plugin use the new name.

        :param old_theme: The name of the theme the plugin should stop using. Unused for this particular plugin.
        :param new_theme:  The new name the plugin should now use.
        :return: None
        """
        log.debug('rename_theme {old} -> {new}'.format(old=old_theme, new=new_theme))
        self.settings_tab.bible_theme = new_theme
        self.settings_tab.save()

    def set_plugin_text_strings(self):
        """
        Called to define all translatable texts of the plugin
        """
        # Name PluginList
        self.text_strings[StringContent.Name] = {
            'singular': translate('BiblesPlugin', 'Bible', 'name singular'),
            'plural': translate('BiblesPlugin', 'Bibles', 'name plural')
        }
        # Name for MediaDockManager, SettingsManager
        self.text_strings[StringContent.VisibleName] = {
            'title': translate('BiblesPlugin', 'Bibles', 'container title')
        }
        # Middle Header Bar
        tooltips = {
            'load': '',
            'import': translate('BiblesPlugin', 'Import a Bible.'),
            'new': translate('BiblesPlugin', 'Add a new Bible.'),
            'edit': translate('BiblesPlugin', 'Edit the selected Bible.'),
            'delete': translate('BiblesPlugin', 'Delete the selected Bible.'),
            'preview': translate('BiblesPlugin', 'Preview the selected Bible.'),
            'live': translate('BiblesPlugin', 'Send the selected Bible live.'),
            'service': translate('BiblesPlugin', 'Add the selected Bible to the service.')
        }
        self.set_plugin_ui_text_strings(tooltips)
