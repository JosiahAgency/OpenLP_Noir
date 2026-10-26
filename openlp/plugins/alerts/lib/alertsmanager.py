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
The :mod:`~openlp.plugins.alerts.lib.alertsmanager` module contains the alert
engine: the priority queue (with preemption for critical alerts), the display
timing, and the scheduler which fires stored alerts inside their start/end
window and on their repeat interval.
"""
import itertools
import json
from datetime import datetime, timedelta

from PySide6 import QtCore

from openlp.core.common.mixins import LogMixin, RegistryProperties
from openlp.core.common.registry import Registry, RegistryBase
from openlp.core.display.screens import ScreenList
from openlp.plugins.alerts.lib.db import AlertItem
from openlp.plugins.alerts.lib.presets import (AlertPriority, PRIORITY_BEHAVIOUR, resolve_alert_settings,
                                               resolve_template_style)

#: How often the scheduler looks for due alerts, in milliseconds.
SCHEDULER_INTERVAL = 15000
#: Extra time allowed for the exit animation before the next alert shows, ms.
EXIT_ANIMATION_BUFFER = 150


class AlertsManager(QtCore.QObject, RegistryBase, LogMixin, RegistryProperties):
    """
    AlertsManager manages the alert queue, display timing and scheduling.
    """
    alerts_text = QtCore.Signal(list)
    queue_changed = QtCore.Signal()

    def __init__(self, parent):
        super(AlertsManager, self).__init__()
        self.plugin = parent
        self._queue = []
        self._current = None
        self._last = None
        self._pending = None
        self._ids = itertools.count(1)
        self._hide_timer = QtCore.QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._finish_current_alert)
        self._scheduler_timer = QtCore.QTimer(self)
        self._scheduler_timer.setInterval(SCHEDULER_INTERVAL)
        self._scheduler_timer.timeout.connect(self.check_schedules)
        Registry().register_function('alerts_text', self.alert_text)
        self.alerts_text.connect(self.alert_text)

    def start_scheduler(self):
        """
        Start the timer which fires scheduled alerts. Called once the plugin
        (and its database) is initialised.
        """
        if not self._scheduler_timer.isActive():
            self._scheduler_timer.start()

    def stop_scheduler(self):
        """
        Stop firing scheduled alerts, e.g. when the plugin is finalised.
        """
        self._scheduler_timer.stop()

    def alert_text(self, message):
        """
        Called via a alerts_text event, e.g. from the web remote. Message is a
        single element array containing text.

        :param message: The message text to be displayed
        """
        if message:
            text = message[0]
            # remove line breaks as these crash javascript code on display
            while '\n' in text:
                text = text.replace('\n', ' ')
            self.display_alert(text, AlertPriority.Notice)

    def _safe_display(self, method, *args):
        """Call a live display method without letting a failure corrupt the queue state."""
        try:
            getattr(self.live_controller.display, method)(*args)
        except Exception:
            self.log_exception(f'Alert display class "{method}" failed')

    def _has_source(self, source):
        return any(alert and alert.get('source') == source for alert in [self._current, self._pending, *self._queue])

    def display_alert(self, text='', priority=AlertPriority.Info, style=None, source=None):
        """
        Called from the Alert form (or the scheduler) to display an alert.

        The alert joins the queue according to its priority: Info and Notice
        wait their turn, Important jumps ahead of anything less urgent, and
        Critical interrupts whatever is showing (which is then re-queued).

        :param text: The text to display
        :param priority: The AlertPriority of the alert, used for queue ordering
        :param style: The resolved style dict to display with. If not given,
            falls back to the priority's current global default preset (this
            is the path used by bare-text alerts, e.g. from the web remote).
        """
        self.log_debug(f'display alert called "{text}"')
        if not text:
            return
        if len(ScreenList()) == 1 and not self.settings.value('core/display on monitor'):
            return
        priority = AlertPriority(priority)
        if style is None:
            style = resolve_alert_settings(self.settings, priority)
        alert = {'id': next(self._ids), 'text': text, 'priority': priority, 'style': style, 'source': source}
        behaviour = PRIORITY_BEHAVIOUR[priority]
        if self._current is None:
            self._show_alert(alert)
        elif behaviour == 'preempt':
            self._preempt(alert)
        elif behaviour == 'front':
            # Ahead of anything less urgent, behind equal or higher priorities
            position = 0
            while position < len(self._queue) and self._queue[position]['priority'] >= priority:
                position += 1
            self._queue.insert(position, alert)
            self.queue_changed.emit()
        else:
            self._queue.append(alert)
            self.queue_changed.emit()

    def _show_alert(self, alert):
        """
        Push an alert to the display and start its hide timer.

        :param alert: dict with ``text``, ``priority`` and ``style``
        """
        settings = alert['style']
        duration = settings['timeout']
        if settings['scroll']:
            duration = settings['timeout'] * max(1, int(settings['repeat']))
        duration_ms = int(duration * 1000) + 2 * int(settings['animationSpeed'])
        self._current = alert
        self._last = alert
        self._hide_timer.start(duration_ms)
        self._safe_display('alert', alert['text'], json.dumps(settings))
        self.queue_changed.emit()

    def _finish_current_alert(self):
        """
        The current alert's time is up: hide it and, once the exit animation
        has had time to play, show the next alert in the queue.
        """
        finished = self._current
        self._current = None
        self._safe_display('hide_alert')
        if self._queue:
            next_alert = self._queue.pop(0)
            self._pending = next_alert
            exit_speed = int(finished['style']['animationSpeed']) if finished else 0
            exit_delay = EXIT_ANIMATION_BUFFER + exit_speed
            QtCore.QTimer.singleShot(exit_delay, lambda: self._resume_with(next_alert))
        self.queue_changed.emit()

    def _resume_with(self, alert):
        """
        Show a queued alert, unless something (e.g. a preempting critical
        alert) has taken the display in the meantime.
        """
        if alert is not self._pending:
            return
        self._pending = None
        if self._current is None:
            self._show_alert(alert)
        else:
            self._queue.insert(0, alert)
            self.queue_changed.emit()

    def check_schedules(self):
        """
        Fire any scheduled alerts that are due. An alert is due when it is
        enabled, the current time is inside its start/end window, and either
        it has never fired or its repeat interval has elapsed since the last
        firing. Alerts whose window has closed are disabled.
        """
        manager = getattr(self.plugin, 'manager', None)
        if manager is None:
            return
        now = datetime.now()
        alerts = manager.get_all_objects(AlertItem, AlertItem.scheduled.is_(True))
        for item in alerts:
            if not item.enabled:
                continue
            if item.end_time and now > item.end_time:
                item.enabled = False
                manager.save_object(item)
                continue
            if item.start_time and now < item.start_time:
                continue
            due = item.last_fired is None or (
                    item.repeat_minutes > 0 and now >= item.last_fired + timedelta(minutes=item.repeat_minutes))
            if not due:
                continue
            if self._has_source(item.id):
                continue
            style = resolve_template_style(item, self.settings)
            self.display_alert(item.text, AlertPriority(item.priority), style=style, source=item.id)
            item.last_fired = now
            if item.repeat_minutes == 0:
                # One-shot alert: it has done its job
                item.enabled = False
            manager.save_object(item)

    def _preempt(self, alert):
        """Show ``alert`` now; whatever was showing goes back to the front of the queue."""
        if self._current is not None:
            self._hide_timer.stop()
            self._queue.insert(0, self._current)
        self._show_alert(alert)

    def get_state(self):
        """
                Snapshot for views.
                :return: dict with ``current`` (alert or None), ``last``, ``remaining_ms`` and ``queue`` (list).
                """
        current = self._current or self._pending
        remaining = self._hide_timer.remainingTime() if self._current else 0
        return {'current': current, 'last': self._last, 'remaining_ms': max(0, remaining), 'queue': list(self._queue)}

    def stop_current(self, clear_queue=False):
        """
        Stop the alert on screen. The next queued alert (if any) then shows,
        unless ``clear_queue`` is set, which stops everything
        """
        if clear_queue:
            self._queue.clear()
        if self._current is None:
            self._pending = None
            self.queue_changed.emit()
            return
        self._hide_timer.stop()
        if clear_queue:
            self._pending = None
        self._finish_current_alert()

    def restart_current(self):
        """Replay the alert on screen from the start, or the last one shown if nothing is showing."""
        alert = self._current or self._last
        if alert is None:
            return
        self._hide_timer.stop()
        self._current = None
        self._safe_display('hide_alert')

        if self._pending is not None and self._pending is not alert:
            self._queue.insert(0, self._pending)
        self._pending = alert
        exit_delay = EXIT_ANIMATION_BUFFER + int(alert['style']['animationSpeed'])
        QtCore.QTimer.singleShot(exit_delay, lambda: self._resume_with(alert))
        self.queue_changed.emit()

    def show_now(self, alert_id):
        """Override: put a queued alert on screen immediately. The interrupted alert goes back to the queue front."""
        for index, alert in enumerate(self._queue):
            if alert['id'] == alert_id:
                self._queue.pop(index)
                self._preempt(alert)
                return True
        return False

    def remove_from_queue(self, alert_id):
        """Drop one queued alert."""
        self._queue = [alert for alert in self._queue if alert['id'] != alert_id]
        self.queue_changed.emit()

    def clear_queue(self):
        """Drop all queued alerts."""
        self._queue.clear()
        self._pending = None
        self.queue_changed.emit()

    def shutdown(self):
        """Stop all timers and drop state when the plugin is finalised."""
        self._scheduler_timer.stop()
        self._hide_timer.stop()
        self._queue.clear()
        self._current = None
        self._pending = None
