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
Theme-related tests for Timer plugin.
"""
from unittest.mock import MagicMock

from PySide6 import QtCore, QtWidgets

from openlp.core.common.registry import Registry
from openlp.plugins.timer.lib.mediaitem import TimerMediaItem
from openlp.plugins.timer.lib.timertab import TimerTab
from openlp.plugins.timer.timerplugin import TimerPlugin


def test_tab_saves_and_reloads_theme(settings):
    Registry().register('settings_form', MagicMock())
    tab = TimerTab(None, 'timer')
    tab.update_theme_list(['Theme A', 'Theme B'])
    assert tab.timer_theme_combo_box.count() == 3
    tab.timer_theme_combo_box.setCurrentIndex(1)
    tab.on_timer_theme_combo_box_changed()
    tab.save()
    assert settings.value('timer/timer theme') == 'Theme A'
    tab.load()
    assert tab.timer_theme == 'Theme A'
    assert tab.timer_theme_combo_box.currentText() == 'Theme A'


def test_generate_slide_data_prefers_item_theme(settings):
    media_item = TimerMediaItem.__new__(TimerMediaItem)
    media_item.plugin = MagicMock()
    media_item.plugin.settings_tab.timer_theme = 'Plugin Theme'
    media_item.plugin.db_manager = MagicMock()
    timer_item = MagicMock()
    timer_item.id = 1
    timer_item.title = 'Call to worship'
    timer_item.mode = 'countdown'
    timer_item.duration_seconds = 300
    timer_item.theme_name = 'Item Theme'
    media_item.plugin.db_manager.get_object.return_value = timer_item
    media_item.list_view = MagicMock()
    media_item.remote_triggered = None
    item = QtWidgets.QListWidgetItem()
    item.setData(QtCore.Qt.ItemDataRole.UserRole, 1)
    service_item = MagicMock()
    service_item.raw_footer = []
    result = media_item.generate_slide_data(service_item, item=item)
    assert result is True
    assert service_item.theme == 'Item Theme'


def test_generate_slide_data_uses_plugin_theme_when_item_theme_missing(settings):
    media_item = TimerMediaItem.__new__(TimerMediaItem)
    media_item.plugin = MagicMock()
    media_item.plugin.settings_tab.timer_theme = 'Plugin Theme'
    media_item.plugin.db_manager = MagicMock()
    timer_item = MagicMock()
    timer_item.id = 1
    timer_item.title = 'Prayer'
    timer_item.mode = 'countdown'
    timer_item.duration_seconds = 180
    timer_item.theme_name = ''
    media_item.plugin.db_manager.get_object.return_value = timer_item
    media_item.list_view = MagicMock()
    media_item.remote_triggered = None
    item = QtWidgets.QListWidgetItem()
    item.setData(QtCore.Qt.ItemDataRole.UserRole, 1)
    service_item = MagicMock()
    service_item.raw_footer = []
    result = media_item.generate_slide_data(service_item, item=item)
    assert result is True
    assert service_item.theme == 'Plugin Theme'


def test_uses_theme_and_rename_theme(settings):
    plugin = TimerPlugin.__new__(TimerPlugin)
    plugin.settings_tab = MagicMock()
    plugin.settings_tab.timer_theme = 'Timer Theme'
    timer_item = MagicMock()
    timer_item.theme_name = 'Timer Theme'
    plugin.db_manager = MagicMock()
    plugin.db_manager.get_all_objects.side_effect = [[timer_item], [timer_item]]
    assert plugin.uses_theme('Timer Theme') == 2
    plugin.rename_theme('Timer Theme', 'Renamed Theme')
    assert plugin.settings_tab.timer_theme == 'Renamed Theme'
    plugin.settings_tab.save.assert_called_once()
    assert timer_item.theme_name == 'Renamed Theme'

