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
This module contains tests for the alerts manager: queueing, preemption and
scheduling.
"""
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from openlp.plugins.alerts.lib.alertsmanager import AlertsManager, EXIT_ANIMATION_BUFFER
from openlp.plugins.alerts.lib.presets import AlertPriority, resolve_alert_settings


@pytest.fixture
def alert_environment(registry, settings):
    """An AlertsManager with a mocked display and two screens"""
    settings.setValue('core/display on monitor', True)
    mocked_live_controller = MagicMock()
    registry.register('live_controller', mocked_live_controller)
    with patch('openlp.plugins.alerts.lib.alertsmanager.ScreenList') as mocked_screen_list:
        mocked_screen_list.return_value.__len__.return_value = 2
        alert_manager = AlertsManager(None)
        yield alert_manager, mocked_live_controller


@pytest.fixture
def single_shot(alert_environment):
    """Capture the manager's exit-animation timer so tests can run its callback by hand"""
    with patch('openlp.plugins.alerts.lib.alertsmanager.QtCore') as mocked_qtcore:
        yield mocked_qtcore


def _run_exit_callback(mocked_qtcore):
    """Fire the most recently scheduled exit-animation callback"""
    mocked_qtcore.QTimer.singleShot.call_args[0][1]()


def test_remove_message_text(registry):
    """
    Test that Alerts are not triggered with empty strings
    """
    # GIVEN: A valid Alert Manager
    alert_manager = AlertsManager(None)
    alert_manager.display_alert = MagicMock()

    # WHEN: Called with an empty string
    alert_manager.alert_text('')

    # THEN: the display should not have been triggered
    assert alert_manager.display_alert.called is False, 'The Alert should not have been called'


def test_trigger_message_text(registry):
    """
    Test that Alerts are triggered with a text string
    """
    # GIVEN: A valid Alert Manager
    alert_manager = AlertsManager(None)
    alert_manager.display_alert = MagicMock()

    # WHEN: Called with an empty string
    alert_manager.alert_text(['This is a string'])

    # THEN: the display should have been triggered
    assert alert_manager.display_alert.called is True, 'The Alert should have been called'


def test_line_break_message_text(registry):
    """
    Test that Alerts are triggered with a text string but line breaks are removed
    """
    # GIVEN: A valid Alert Manager
    alert_manager = AlertsManager(None)
    alert_manager.display_alert = MagicMock()

    # WHEN: Called with an empty string
    alert_manager.alert_text(['This is \n a string'])

    # THEN: the display should have been triggered
    assert alert_manager.display_alert.called is True, 'The Alert should have been called'
    alert_manager.display_alert.assert_called_once_with('This is   a string', AlertPriority.Notice)


def test_display_alert_shows_immediately(alert_environment):
    """An alert shows at once when nothing is on screen"""
    # GIVEN: An alerts manager with nothing showing
    alert_manager, mocked_live_controller = alert_environment

    # WHEN: An info alert is displayed
    alert_manager.display_alert('hello', AlertPriority.Info)

    # THEN: The display was called and the alert is current, with the live Info default style
    assert mocked_live_controller.display.alert.call_count == 1
    assert alert_manager._current['text'] == 'hello'
    assert alert_manager._current['style'] == resolve_alert_settings(alert_manager.settings, AlertPriority.Info)
    assert alert_manager._queue == []


def test_display_alert_uses_the_style_it_is_given(alert_environment):
    """A per-template style, if supplied, is used as-is rather than the priority default"""
    # GIVEN: An alerts manager with nothing showing, and a distinctive style
    alert_manager, mocked_live_controller = alert_environment
    own_style = dict(resolve_alert_settings(alert_manager.settings, AlertPriority.Info))
    own_style['fontSize'] = 54321

    # WHEN: An alert is displayed with that style
    alert_manager.display_alert('hello', AlertPriority.Info, style=own_style)

    # THEN: The supplied style is what is current and what was sent to the display
    assert alert_manager._current['style'] == own_style
    displayed_settings = json.loads(mocked_live_controller.display.alert.call_args[0][1])
    assert displayed_settings['fontSize'] == 54321


def test_display_alert_queues_second_alert(alert_environment):
    """A second info alert waits in the queue"""
    # GIVEN: An alerts manager already showing an alert
    alert_manager, mocked_live_controller = alert_environment
    alert_manager.display_alert('first', AlertPriority.Info)

    # WHEN: Another info alert arrives
    alert_manager.display_alert('second', AlertPriority.Info)

    # THEN: Only the first is showing; the second is queued
    assert mocked_live_controller.display.alert.call_count == 1
    assert [alert['text'] for alert in alert_manager._queue] == ['second']


def test_important_alert_jumps_queue(alert_environment):
    """An important alert queues ahead of less urgent alerts"""
    # GIVEN: An alerts manager showing an alert with two info alerts waiting
    alert_manager, _ = alert_environment
    alert_manager.display_alert('showing', AlertPriority.Info)
    alert_manager.display_alert('waiting one', AlertPriority.Info)
    alert_manager.display_alert('waiting two', AlertPriority.Info)

    # WHEN: An important alert arrives
    alert_manager.display_alert('urgent', AlertPriority.Important)

    # THEN: It is at the front of the queue, and nothing was interrupted
    assert alert_manager._current['text'] == 'showing'
    assert [alert['text'] for alert in alert_manager._queue] == ['urgent', 'waiting one', 'waiting two']


def test_critical_alert_preempts(alert_environment):
    """A critical alert interrupts the alert on screen, which is re-queued"""
    # GIVEN: An alerts manager showing an alert
    alert_manager, mocked_live_controller = alert_environment
    alert_manager.display_alert('showing', AlertPriority.Info)

    # WHEN: A critical alert arrives
    alert_manager.display_alert('emergency', AlertPriority.Critical)

    # THEN: The critical alert took the display and the first alert waits
    assert mocked_live_controller.display.alert.call_count == 2
    assert alert_manager._current['text'] == 'emergency'
    assert [alert['text'] for alert in alert_manager._queue] == ['showing']


def test_check_schedules_fires_due_alert(alert_environment):
    """A scheduled alert inside its window fires and records the firing"""
    # GIVEN: An alerts manager whose plugin has a repeating scheduled alert due now
    alert_manager, mocked_live_controller = alert_environment
    scheduled_item = MagicMock()
    scheduled_item.text = 'scheduled hello'
    scheduled_item.priority = int(AlertPriority.Notice)
    scheduled_item.style = None
    scheduled_item.enabled = True
    scheduled_item.start_time = datetime.now() - timedelta(minutes=5)
    scheduled_item.end_time = datetime.now() + timedelta(minutes=5)
    scheduled_item.repeat_minutes = 10
    scheduled_item.last_fired = None
    mocked_plugin = MagicMock()
    mocked_plugin.manager.get_all_objects.return_value = [scheduled_item]
    alert_manager.plugin = mocked_plugin

    # WHEN: The scheduler checks for due alerts
    alert_manager.check_schedules()

    # THEN: The alert was displayed and its last firing was saved
    assert mocked_live_controller.display.alert.call_count == 1
    assert scheduled_item.last_fired is not None
    mocked_plugin.manager.save_object.assert_called_once_with(scheduled_item)


def test_check_schedules_uses_the_items_own_style(alert_environment):
    """A scheduled alert with its own saved style displays with that style, not the priority default"""
    # GIVEN: An alerts manager whose plugin has a due scheduled alert with a distinctive saved style
    alert_manager, mocked_live_controller = alert_environment
    own_style = dict(resolve_alert_settings(alert_manager.settings, AlertPriority.Notice))
    own_style['fontSize'] = 12345
    scheduled_item = MagicMock()
    scheduled_item.text = 'scheduled hello'
    scheduled_item.priority = int(AlertPriority.Notice)
    scheduled_item.style = json.dumps(own_style)
    scheduled_item.enabled = True
    scheduled_item.start_time = datetime.now() - timedelta(minutes=5)
    scheduled_item.end_time = datetime.now() + timedelta(minutes=5)
    scheduled_item.repeat_minutes = 10
    scheduled_item.last_fired = None
    mocked_plugin = MagicMock()
    mocked_plugin.manager.get_all_objects.return_value = [scheduled_item]
    alert_manager.plugin = mocked_plugin

    # WHEN: The scheduler checks for due alerts
    alert_manager.check_schedules()

    # THEN: The alert was displayed with its own style, not the live Notice default
    displayed_settings = json.loads(mocked_live_controller.display.alert.call_args[0][1])
    assert displayed_settings['fontSize'] == 12345


def test_check_schedules_disables_expired_alert(alert_environment):
    """A scheduled alert past its end time is disabled without firing"""
    # GIVEN: An alerts manager whose plugin has an expired scheduled alert
    alert_manager, mocked_live_controller = alert_environment
    scheduled_item = MagicMock()
    scheduled_item.text = 'too late'
    scheduled_item.priority = int(AlertPriority.Notice)
    scheduled_item.enabled = True
    scheduled_item.start_time = datetime.now() - timedelta(hours=2)
    scheduled_item.end_time = datetime.now() - timedelta(hours=1)
    scheduled_item.repeat_minutes = 10
    scheduled_item.last_fired = None
    mocked_plugin = MagicMock()
    mocked_plugin.manager.get_all_objects.return_value = [scheduled_item]
    alert_manager.plugin = mocked_plugin

    # WHEN: The scheduler checks for due alerts
    alert_manager.check_schedules()

    # THEN: Nothing was displayed and the alert is now disabled
    assert mocked_live_controller.display.alert.call_count == 0
    assert scheduled_item.enabled is False
    mocked_plugin.manager.save_object.assert_called_once_with(scheduled_item)


def test_display_alert_sends_text_and_style_to_display(alert_environment):
    """The display's alert method receives the text and the JSON style"""
    alert_manager, mocked_live_controller = alert_environment

    alert_manager.display_alert('hello', AlertPriority.Info)

    args = mocked_live_controller.display.alert.call_args[0]
    assert args[0] == 'hello'
    assert json.loads(args[1])['alertType'] == 'toast'


def test_alerts_get_unique_ids(alert_environment):
    """Every alert is given its own id, so views can refer to it"""
    alert_manager, _ = alert_environment
    alert_manager.display_alert('first', AlertPriority.Info)
    alert_manager.display_alert('second', AlertPriority.Info)
    alert_manager.display_alert('third', AlertPriority.Info)

    ids = [alert_manager._current['id']] + [alert['id'] for alert in alert_manager._queue]
    assert len(set(ids)) == 3


def test_queue_changed_emitted(alert_environment):
    """Showing, queueing and clearing all notify listeners"""
    alert_manager, _ = alert_environment
    emitted = []
    alert_manager.queue_changed.connect(lambda: emitted.append(True))

    alert_manager.display_alert('first', AlertPriority.Info)  # shown
    alert_manager.display_alert('second', AlertPriority.Info)  # queued
    alert_manager.clear_queue()  # cleared

    assert len(emitted) == 3


def test_get_state_snapshot(alert_environment):
    """get_state reports the current alert, the last shown alert and a copy of the queue"""
    alert_manager, _ = alert_environment
    alert_manager.display_alert('first', AlertPriority.Info)
    alert_manager.display_alert('second', AlertPriority.Info)

    state = alert_manager.get_state()

    assert state['current']['text'] == 'first'
    assert state['last']['text'] == 'first'
    assert [alert['text'] for alert in state['queue']] == ['second']
    # AND: the queue in the snapshot is a copy
    state['queue'].clear()
    assert len(alert_manager._queue) == 1


def test_stop_current_shows_next_after_exit_animation(alert_environment, single_shot):
    """Stop hides the alert on screen, then the next queued alert takes over"""
    alert_manager, mocked_live_controller = alert_environment
    alert_manager.display_alert('first', AlertPriority.Info)
    alert_manager.display_alert('second', AlertPriority.Info)

    alert_manager.stop_current()

    # THEN: Nothing is current yet, the next alert is waiting out the exit animation
    mocked_live_controller.display.hide_alert.assert_called_once()
    assert alert_manager._current is None
    assert alert_manager._pending['text'] == 'second'
    assert alert_manager._queue == []

    # WHEN: The exit animation has had time to play
    _run_exit_callback(single_shot)

    # THEN: The next alert is showing
    assert alert_manager._current['text'] == 'second'
    assert mocked_live_controller.display.alert.call_count == 2


def test_stop_all_clears_queue(alert_environment, single_shot):
    """Stop all hides the alert and drops everything waiting"""
    alert_manager, mocked_live_controller = alert_environment
    alert_manager.display_alert('first', AlertPriority.Info)
    alert_manager.display_alert('second', AlertPriority.Info)

    alert_manager.stop_current(clear_queue=True)

    mocked_live_controller.display.hide_alert.assert_called_once()
    assert alert_manager._current is None
    assert alert_manager._pending is None
    assert alert_manager._queue == []
    single_shot.QTimer.singleShot.assert_not_called()


def test_stop_during_exit_gap_cancels_pending_alert(alert_environment, single_shot):
    """Stopping while the next alert is waiting out the exit animation stops it appearing"""
    alert_manager, mocked_live_controller = alert_environment
    alert_manager.display_alert('first', AlertPriority.Info)
    alert_manager.display_alert('second', AlertPriority.Info)
    alert_manager.stop_current()
    callback = single_shot.QTimer.singleShot.call_args[0][1]

    # WHEN: Stop is pressed again during the gap, then the stale timer fires
    alert_manager.stop_current()
    callback()

    # THEN: The cancelled alert never reaches the display
    assert alert_manager._current is None
    assert mocked_live_controller.display.alert.call_count == 1


def test_finish_waits_for_the_outgoing_alerts_animation(alert_environment, single_shot):
    """The delay before the next alert is based on the alert that is leaving"""
    alert_manager, _ = alert_environment
    leaving_style = dict(resolve_alert_settings(alert_manager.settings, AlertPriority.Info))
    leaving_style['animationSpeed'] = 700
    arriving_style = dict(leaving_style)
    arriving_style['animationSpeed'] = 100
    alert_manager.display_alert('leaving', AlertPriority.Info, style=leaving_style)
    alert_manager.display_alert('arriving', AlertPriority.Info, style=arriving_style)

    alert_manager._finish_current_alert()

    assert single_shot.QTimer.singleShot.call_args[0][0] == EXIT_ANIMATION_BUFFER + 700


def test_restart_replays_current_alert(alert_environment, single_shot):
    """Restart hides the alert and shows the same alert again from the start"""
    alert_manager, mocked_live_controller = alert_environment
    alert_manager.display_alert('first', AlertPriority.Info)

    alert_manager.restart_current()

    mocked_live_controller.display.hide_alert.assert_called_once()
    assert alert_manager._current is None
    assert alert_manager._pending['text'] == 'first'

    _run_exit_callback(single_shot)

    assert alert_manager._current['text'] == 'first'
    assert mocked_live_controller.display.alert.call_count == 2


def test_restart_replays_last_alert_when_nothing_is_showing(alert_environment, single_shot):
    """With nothing on screen, Restart replays the last alert that was shown"""
    alert_manager, mocked_live_controller = alert_environment
    alert_manager.display_alert('first', AlertPriority.Info)
    alert_manager.stop_current(clear_queue=True)

    alert_manager.restart_current()
    _run_exit_callback(single_shot)

    assert alert_manager._current['text'] == 'first'
    assert mocked_live_controller.display.alert.call_count == 2


def test_restart_with_no_history_does_nothing(alert_environment, single_shot):
    """Restart is a no-op when no alert has ever been shown"""
    alert_manager, mocked_live_controller = alert_environment

    alert_manager.restart_current()

    mocked_live_controller.display.hide_alert.assert_not_called()
    single_shot.QTimer.singleShot.assert_not_called()


def test_show_now_overrides_current_alert(alert_environment):
    """Show now puts a queued alert on screen; the interrupted alert returns to the queue front"""
    alert_manager, _ = alert_environment
    alert_manager.display_alert('first', AlertPriority.Info)
    alert_manager.display_alert('second', AlertPriority.Info)
    alert_manager.display_alert('third', AlertPriority.Info)
    third_id = alert_manager._queue[1]['id']

    result = alert_manager.show_now(third_id)

    assert result is True
    assert alert_manager._current['text'] == 'third'
    assert [alert['text'] for alert in alert_manager._queue] == ['first', 'second']


def test_show_now_unknown_id(alert_environment):
    """Show now with an id that is not queued changes nothing"""
    alert_manager, _ = alert_environment
    alert_manager.display_alert('first', AlertPriority.Info)

    assert alert_manager.show_now(99999) is False
    assert alert_manager._current['text'] == 'first'


def test_remove_from_queue(alert_environment):
    """Removing one queued alert leaves the others"""
    alert_manager, _ = alert_environment
    alert_manager.display_alert('first', AlertPriority.Info)
    alert_manager.display_alert('second', AlertPriority.Info)
    alert_manager.display_alert('third', AlertPriority.Info)

    alert_manager.remove_from_queue(alert_manager._queue[0]['id'])

    assert [alert['text'] for alert in alert_manager._queue] == ['third']
    assert alert_manager._current['text'] == 'first'


def test_clear_queue_leaves_current_alert(alert_environment):
    """Clear queue drops the waiting alerts but not the one on screen"""
    alert_manager, _ = alert_environment
    alert_manager.display_alert('first', AlertPriority.Info)
    alert_manager.display_alert('second', AlertPriority.Info)

    alert_manager.clear_queue()

    assert alert_manager._queue == []
    assert alert_manager._current['text'] == 'first'


def test_display_failure_does_not_wedge_the_manager(alert_environment, single_shot):
    """A failing display call is logged, and Stop all still recovers the manager"""
    alert_manager, mocked_live_controller = alert_environment
    mocked_live_controller.display.alert.side_effect = RuntimeError('boom')
    alert_manager.log_exception = MagicMock()

    alert_manager.display_alert('first', AlertPriority.Info)

    # THEN: The failure was logged, not raised
    alert_manager.log_exception.assert_called_once()
    assert alert_manager._current['text'] == 'first'

    # WHEN: Stop all is used
    alert_manager.stop_current(clear_queue=True)

    # THEN: The manager is clean again
    assert alert_manager._current is None
    assert alert_manager._pending is None
