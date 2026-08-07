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
Live overlay timer runtime.
"""
from PySide6 import QtCore

from openlp.core.common.mixins import RegistryProperties
from openlp.plugins.timer.lib import TimerMode, format_seconds


class TimerOverlayManager(QtCore.QObject, RegistryProperties):
    """
    Owns countdown/count-up state and pushes text updates to the live timer slide.
    """
    timer_updated = QtCore.Signal(str)

    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self.mode = TimerMode.Countdown.value
        self.current_seconds = 0
        self.initial_seconds = 0
        self.is_running = False
        self.is_paused = False
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)
        self.active_service_item = None

    def start_for_service_item(self, service_item):
        """
        Start runtime from a timer service item's data payload.
        """
        timer_data = (service_item.data_string or {}).get('timer', {})
        self.active_service_item = service_item
        self.start(timer_data.get('mode', TimerMode.Countdown.value), timer_data.get('duration_seconds', 0))

    def _is_timer_live(self):
        if not self.live_controller or not self.live_controller.service_item:
            return False
        return self.live_controller.service_item.name == self.plugin.name

    def _push_text_update(self):
        if not self._is_timer_live():
            return
        text = format_seconds(self.current_seconds)
        slides = [{'verse': '1', 'text': text, 'footer': ''}]
        self.live_controller.preview_display.load_verses(slides)
        for display in self.live_controller.displays:
            display.load_verses(slides)

    def start(self, mode, duration_seconds):
        mode = mode or TimerMode.Countdown.value
        duration_seconds = max(0, int(duration_seconds))
        self.mode = mode
        self.initial_seconds = duration_seconds
        self.current_seconds = duration_seconds if mode == TimerMode.Countdown.value else 0
        self.is_running = True
        self.is_paused = False
        self._push_text_update()
        self._timer.start()
        self.timer_updated.emit(format_seconds(self.current_seconds))

    def pause(self):
        if not self.is_running:
            return
        self._timer.stop()
        self.is_paused = True
        self.is_running = False
        self.timer_updated.emit(format_seconds(self.current_seconds))

    def resume(self):
        if not self.is_paused:
            return
        self._timer.start()
        self.is_paused = False
        self.is_running = True
        self.timer_updated.emit(format_seconds(self.current_seconds))

    def reset(self):
        self.current_seconds = self.initial_seconds if self.mode == TimerMode.Countdown.value else 0
        self._push_text_update()
        self.timer_updated.emit(format_seconds(self.current_seconds))

    def stop(self):
        self._timer.stop()
        self.is_running = False
        self.is_paused = False
        self.active_service_item = None
        self.timer_updated.emit(format_seconds(self.current_seconds))

    def _on_tick(self):
        if self.mode == TimerMode.Countdown.value:
            if self.current_seconds > 0:
                self.current_seconds -= 1
            if self.current_seconds <= 0:
                self.current_seconds = 0
                self._timer.stop()
                self.is_running = False
                self.is_paused = False
                self._push_text_update()
                self.timer_updated.emit(format_seconds(self.current_seconds))
                return
        else:
            self.current_seconds += 1
        self._push_text_update()
        self.timer_updated.emit(format_seconds(self.current_seconds))
