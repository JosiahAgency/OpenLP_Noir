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
The :mod:`~openlp.plugins.egwlibrary.egwlibraryplugin` module contains the Plugin class
for the EGW Library plugin.
"""
import logging

from openlp.core.common.i18n import translate
from openlp.core.common.registry import Registry
from openlp.core.lib import build_icon
from openlp.core.lib.plugin import Plugin, StringContent
from openlp.core.state import State
from openlp.core.ui.icons import UiIcons
from openlp.plugins.egwlibrary.lib.db import EGWLibraryManager
from openlp.plugins.egwlibrary.lib.egwlibrarytab import EGWLibraryTab
from openlp.plugins.egwlibrary.lib.mediaitem import EGWLibraryMediaItem

log = logging.getLogger(__name__)


class EGWLibraryPlugin(Plugin):
    """
    The EGW Library plugin provides a searchable library of the writings of Ellen G.
    White. Books are imported from JSON files; every paragraph is indexed individually
    and can be displayed like a Bible verse or song verse. Searches understand the
    standard EGW citation format, e.g. "DA 83.2" (The Desire of Ages, page 83,
    paragraph 2), as well as chapters ("DA ch 5"), pages ("DA 83-85") and full text.
    """
    log.info('EGW Library Plugin loaded')

    def __init__(self):
        super().__init__('egwlibrary', EGWLibraryMediaItem, EGWLibraryTab)
        self.weight = -2
        self.manager = EGWLibraryManager()
        self.icon_path = UiIcons().book
        self.icon = build_icon(self.icon_path)
        Registry().register('egwlibrary_manager', self.manager)
        # The state service name must match the RegistryBase registration, which is
        # derived from the class name: EGWLibraryPlugin -> "egw_library_plugin".
        State().add_service('egw_library', self.weight, is_plugin=True)
        State().update_pre_conditions('egw_library', self.check_pre_conditions())

    @staticmethod
    def about():
        about_text = translate('EGWLibraryPlugin',
                               '<strong>EGW Library Plugin</strong><br />The EGW Library plugin provides a '
                               'searchable library of the writings of Ellen G. White. Books are imported from '
                               'JSON files and every paragraph can be displayed like a Bible verse, found by '
                               'reference (e.g. "DA 83.2"), by chapter, by page, or with a full text search.')
        return about_text

    def check_pre_conditions(self):
        """
        Check the plugin can run.
        """
        return self.manager.session is not None

    def set_plugin_text_strings(self):
        """
        Called to define all translatable texts of the plugin.
        """
        # Name PluginList
        self.text_strings[StringContent.Name] = {
            'singular': translate('EGWLibraryPlugin', 'EGW Library', 'name singular'),
            'plural': translate('EGWLibraryPlugin', 'EGW Library', 'name plural')
        }
        # Name for MediaDockManager, SettingsManager
        self.text_strings[StringContent.VisibleName] = {
            'title': translate('EGWLibraryPlugin', 'EGW Library', 'container title')
        }
        # Middle Header Bar
        tooltips = {
            'load': translate('EGWLibraryPlugin', 'Load a new EGW book.'),
            'import': translate('EGWLibraryPlugin', 'Import EGW books into the library.'),
            'new': translate('EGWLibraryPlugin', 'Add a new EGW book.'),
            'edit': translate('EGWLibraryPlugin', 'Edit the selected EGW book.'),
            'delete': translate('EGWLibraryPlugin', 'Delete the selected EGW book from the library.'),
            'preview': translate('EGWLibraryPlugin', 'Preview the selected paragraphs.'),
            'live': translate('EGWLibraryPlugin', 'Send the selected paragraphs live.'),
            'service': translate('EGWLibraryPlugin', 'Add the selected paragraphs to the service.')
        }
        self.set_plugin_ui_text_strings(tooltips)

    def finalise(self):
        """
        Time to tidy up on exit.
        """
        log.info('EGW Library Finalising')
        self.manager.finalise()
        Plugin.finalise(self)
