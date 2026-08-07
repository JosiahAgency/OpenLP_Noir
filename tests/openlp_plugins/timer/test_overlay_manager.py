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
Tests for timer live-slide runtime.
"""
from unittest.mock import MagicMock

from openlp.plugins.timer.lib.overlaymanager import TimerOverlayManager
from openlp.plugins.timer.lib import TimerMode


def test_countdown_updates_live_timer_slide(registry):
    plugin = MagicMock()
    plugin.name = 'timer'
    manager = TimerOverlayManager(plugin)
    live_controller = MagicMock()
    live_controller.service_item = MagicMock()
    live_controller.service_item.name = 'timer'
    live_controller.displays = [MagicMock()]
    registry.register('live_controller', live_controller)
    manager.start(TimerMode.Countdown.value, 1)
    manager._on_tick()
    assert manager.current_seconds == 0
    manager.live_controller.preview_display.load_verses.assert_called()
    manager.live_controller.displays[0].load_verses.assert_called()


def test_start_for_service_item_uses_service_data(registry):
    plugin = MagicMock()
    plugin.name = 'timer'
    manager = TimerOverlayManager(plugin)
    live_controller = MagicMock()
    live_controller.service_item = MagicMock()
    live_controller.service_item.name = 'timer'
    live_controller.displays = []
    registry.register('live_controller', live_controller)
    service_item = MagicMock()
    service_item.data_string = {'timer': {'mode': 'countup', 'duration_seconds': 75}}

    manager.start_for_service_item(service_item)

    assert manager.mode == 'countup'
    assert manager.initial_seconds == 75
