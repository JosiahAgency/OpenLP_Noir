"""
This module contains tests for the non-modal alert monitor window.
"""
from unittest.mock import MagicMock, patch

import pytest

from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings
from openlp.plugins.alerts.forms.alertmonitor import AlertMonitorDialog
from openlp.plugins.alerts.lib.alertsmanager import AlertsManager
from openlp.plugins.alerts.lib.presets import AlertPriority


@pytest.fixture
def monitor(settings: Settings, registry: Registry):
    """An AlertMonitorDialog wired to a real AlertsManager with a mocked display"""
    settings.setValue('core/display on monitor', True)
    registry.register('main_window', None)
    registry.register('live_controller', MagicMock())
    with patch('openlp.plugins.alerts.lib.alertsmanager.ScreenList') as mocked_screen_list:
        mocked_screen_list.return_value.__len__.return_value = 2
        manager = AlertsManager(None)
        dialog = AlertMonitorDialog(MagicMock())
        yield dialog, manager
        dialog.close()


def test_monitor_starts_idle(monitor):
    """With nothing showing, the monitor says so and the controls are disabled"""
    dialog, _ = monitor

    assert dialog.current_label.text() == 'No alert is currently showing.'
    assert dialog.stop_button.isEnabled() is False
    assert dialog.stop_all_button.isEnabled() is False
    assert dialog.restart_button.isEnabled() is False
    assert dialog.queue_list.count() == 0
    assert dialog.clear_button.isEnabled() is False


def test_monitor_shows_current_and_queued_alerts(monitor):
    """The monitor follows the manager as alerts are shown and queued"""
    dialog, manager = monitor

    manager.display_alert('first', AlertPriority.Info)
    manager.display_alert('second', AlertPriority.Notice)
    manager.display_alert('third', AlertPriority.Info)

    assert dialog.current_label.text() == '[Info] first'
    assert [dialog.queue_list.item(row).text() for row in range(dialog.queue_list.count())] == [
        '1. [Notice] second', '2. [Info] third']
    assert dialog.stop_button.isEnabled() is True
    assert dialog.stop_all_button.isEnabled() is True
    assert dialog.restart_button.isEnabled() is True
    assert dialog.clear_button.isEnabled() is True


def test_queue_buttons_need_a_selection(monitor):
    """Show now and Remove are only enabled when a queued alert is selected"""
    dialog, manager = monitor
    manager.display_alert('first', AlertPriority.Info)
    manager.display_alert('second', AlertPriority.Info)
    assert dialog.show_now_button.isEnabled() is False
    assert dialog.remove_button.isEnabled() is False

    dialog.queue_list.setCurrentRow(0)

    assert dialog.show_now_button.isEnabled() is True
    assert dialog.remove_button.isEnabled() is True


def test_show_now_button_overrides_current_alert(monitor):
    """Show now puts the selected queued alert on screen"""
    dialog, manager = monitor
    manager.display_alert('first', AlertPriority.Info)
    manager.display_alert('second', AlertPriority.Info)
    dialog.queue_list.setCurrentRow(0)

    dialog.show_now_button.click()

    assert dialog.current_label.text() == '[Info] second'
    assert dialog.queue_list.item(0).text() == '1. [Info] first'


def test_remove_button_removes_selected_alert(monitor):
    """Remove drops only the selected queued alert"""
    dialog, manager = monitor
    manager.display_alert('first', AlertPriority.Info)
    manager.display_alert('second', AlertPriority.Info)
    manager.display_alert('third', AlertPriority.Info)
    dialog.queue_list.setCurrentRow(0)

    dialog.remove_button.click()

    assert [dialog.queue_list.item(row).text() for row in range(dialog.queue_list.count())] == ['1. [Info] third']


def test_clear_button_empties_the_queue(monitor):
    """Clear queue empties the list but leaves the current alert"""
    dialog, manager = monitor
    manager.display_alert('first', AlertPriority.Info)
    manager.display_alert('second', AlertPriority.Info)

    dialog.clear_button.click()

    assert dialog.queue_list.count() == 0
    assert dialog.current_label.text() == '[Info] first'


def test_selection_survives_refresh(monitor):
    """A selected queued alert stays selected when the queue changes"""
    dialog, manager = monitor
    manager.display_alert('first', AlertPriority.Info)
    manager.display_alert('second', AlertPriority.Info)
    manager.display_alert('third', AlertPriority.Info)
    dialog.queue_list.setCurrentRow(1)

    manager.display_alert('fourth', AlertPriority.Info)

    assert dialog.queue_list.currentItem().text() == '2. [Info] third'


def test_control_buttons_call_the_manager(monitor):
    """Stop, Stop all and Restart delegate to the manager; the dialog holds no queue logic"""
    dialog, manager = monitor
    manager.display_alert('first', AlertPriority.Info)

    with patch.object(manager, 'stop_current') as mocked_stop, \
            patch.object(manager, 'restart_current') as mocked_restart:
        dialog.stop_button.click()
        dialog.stop_all_button.click()
        dialog.restart_button.click()

    assert mocked_stop.call_args_list[0].args == ()
    assert mocked_stop.call_args_list[1].kwargs == {'clear_queue': True}
    mocked_restart.assert_called_once()


def test_caption_truncates_long_text():
    """Long alert text is shortened in the captions"""
    caption = AlertMonitorDialog._caption({'text': 'x' * 100, 'priority': AlertPriority.Info})

    assert caption == '[Info] ' + 'x' * 60 + '...'
