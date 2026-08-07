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
Tests for timer media item controls.
"""
from unittest.mock import MagicMock

from openlp.plugins.timer.lib.mediaitem import TimerMediaItem


def test_start_timer_uses_selected_preset():
    media_item = TimerMediaItem.__new__(TimerMediaItem)
    media_item.plugin = MagicMock()
    media_item.list_view = MagicMock()
    media_item.list_view.selectedIndexes.return_value = [MagicMock()]
    list_item = MagicMock()
    list_item.data.return_value = 1
    media_item.list_view.currentItem.return_value = list_item
    timer_item = MagicMock()
    timer_item.mode = 'countdown'
    timer_item.duration_seconds = 300
    media_item.plugin.db_manager.get_object.return_value = timer_item

    media_item.go_live = MagicMock()
    media_item.on_start_timer_click()

    media_item.go_live.assert_called_once()


def test_overlay_control_buttons_call_manager():
    media_item = TimerMediaItem.__new__(TimerMediaItem)
    media_item.plugin = MagicMock()

    media_item.on_pause_timer_click()
    media_item.on_resume_timer_click()
    media_item.on_reset_timer_click()
    media_item.on_stop_timer_click()

    media_item.plugin.overlay_manager.pause.assert_called_once()
    media_item.plugin.overlay_manager.resume.assert_called_once()
    media_item.plugin.overlay_manager.reset.assert_called_once()
    media_item.plugin.overlay_manager.stop.assert_called_once()


def test_live_started_event_starts_runtime_for_timer_items():
    media_item = TimerMediaItem.__new__(TimerMediaItem)
    media_item.plugin = MagicMock()
    media_item.plugin.name = 'timer'
    service_item = MagicMock()
    service_item.name = 'timer'
    service_item.data_string = {'timer': {'mode': 'countdown', 'duration_seconds': 90}}

    media_item.on_live_item_started([service_item])

    media_item.plugin.overlay_manager.start_for_service_item.assert_called_once_with(service_item)


def test_live_started_event_stops_runtime_for_non_timer_items():
    media_item = TimerMediaItem.__new__(TimerMediaItem)
    media_item.plugin = MagicMock()
    media_item.plugin.name = 'timer'
    service_item = MagicMock()
    service_item.name = 'songs'
    service_item.data_string = {}

    media_item.on_live_item_started([service_item])

    media_item.plugin.overlay_manager.stop.assert_called_once()
