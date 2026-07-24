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
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from openlp.plugins.alerts.lib.alertsmanager import AlertsManager
from openlp.plugins.alerts.lib.presets import AlertPriority


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

    # THEN: The display was called and the alert is current
    assert mocked_live_controller.display.alert.call_count == 1
    assert alert_manager._current['text'] == 'hello'
    assert alert_manager._queue == []


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
