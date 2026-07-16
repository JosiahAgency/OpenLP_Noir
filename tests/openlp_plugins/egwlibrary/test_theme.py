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
Tests for the plugin-level theme selection of the EGW Library plugin.
"""
from unittest.mock import MagicMock

from PySide6 import QtCore, QtWidgets

from openlp.core.common.registry import Registry
from openlp.plugins.egwlibrary.egwlibraryplugin import EGWLibraryPlugin
from openlp.plugins.egwlibrary.lib.egwlibrarytab import EGWLibraryTab
from openlp.plugins.egwlibrary.lib.mediaitem import EGWLibraryMediaItem


def test_tab_saves_and_reloads_theme(settings):
    """
    The settings tab should list the available themes and persist the selected one.
    """
    # GIVEN: A settings tab which has received the theme list from the ThemeManager
    Registry().register('settings_form', MagicMock())
    tab = EGWLibraryTab(None, 'egwlibrary')
    tab.update_theme_list(['Theme A', 'Theme B'])
    assert tab.egw_theme_combo_box.count() == 3

    # WHEN: The user selects a theme and the tab is saved
    tab.egw_theme_combo_box.setCurrentIndex(1)
    tab.on_egw_theme_combo_box_changed()
    tab.save()

    # THEN: The setting is persisted and restored on the next load
    assert settings.value('egwlibrary/egw theme') == 'Theme A'
    tab.load()
    assert tab.egw_theme == 'Theme A'
    assert tab.egw_theme_combo_box.currentText() == 'Theme A'


def test_generate_slide_data_applies_theme(settings):
    """
    generate_slide_data should stamp the configured theme onto the service item.
    """
    # GIVEN: A media item whose settings tab has a theme configured
    media_item = EGWLibraryMediaItem.__new__(EGWLibraryMediaItem)
    media_item.plugin = MagicMock()
    media_item.plugin.settings_tab.egw_theme = 'EGW Theme'
    media_item.manager = MagicMock()
    media_item.list_view = MagicMock()
    item = QtWidgets.QListWidgetItem()
    item.setData(QtCore.Qt.ItemDataRole.UserRole, {
        'type': 'paragraph', 'abbreviation': 'DA', 'reference': 'DA 83.2',
        'text': 'Sample text', 'book_title': 'The Desire of Ages', 'copyright': ''
    })
    service_item = MagicMock()
    service_item.raw_footer = []

    # WHEN: The slide data is generated
    result = media_item.generate_slide_data(service_item, item=[item])

    # THEN: The service item uses the configured theme
    assert result is True
    assert service_item.theme == 'EGW Theme'


def test_generate_slide_data_without_theme(settings):
    """
    Without a configured theme the service item theme should be left untouched.
    """
    # GIVEN: A media item whose settings tab has no theme configured
    media_item = EGWLibraryMediaItem.__new__(EGWLibraryMediaItem)
    media_item.plugin = MagicMock()
    media_item.plugin.settings_tab.egw_theme = ''
    media_item.manager = MagicMock()
    media_item.list_view = MagicMock()
    item = QtWidgets.QListWidgetItem()
    item.setData(QtCore.Qt.ItemDataRole.UserRole, {
        'type': 'paragraph', 'abbreviation': 'DA', 'reference': 'DA 83.2',
        'text': 'Sample text', 'book_title': 'The Desire of Ages', 'copyright': ''
    })
    service_item = MagicMock()
    service_item.raw_footer = []
    del service_item.theme

    # WHEN: The slide data is generated
    result = media_item.generate_slide_data(service_item, item=[item])

    # THEN: No theme was assigned to the service item
    assert result is True
    assert not hasattr(service_item, 'theme')


def test_uses_theme_and_rename_theme(settings):
    """
    uses_theme and rename_theme should mirror the Bible plugin behaviour.
    """
    # GIVEN: A plugin with a configured theme
    plugin = EGWLibraryPlugin.__new__(EGWLibraryPlugin)
    plugin.settings_tab = MagicMock()
    plugin.settings_tab.egw_theme = 'EGW Theme'

    # THEN: uses_theme reports the configured theme only
    assert plugin.uses_theme('EGW Theme') == 1
    assert plugin.uses_theme('Other Theme') == 0

    # WHEN: The theme is renamed
    plugin.rename_theme('EGW Theme', 'New Theme')

    # THEN: The tab is updated and saved
    assert plugin.settings_tab.egw_theme == 'New Theme'
    plugin.settings_tab.save.assert_called_once()
