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
Package to test the openlp.plugins.alerts.forms.alertform package.
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from PySide6 import QtWidgets, QtTest, QtCore

from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings
from openlp.plugins.alerts.forms.alertform import AlertForm
from openlp.plugins.alerts.lib.db import AlertItem
from openlp.plugins.alerts.lib.presets import DEFAULT_PRESETS, AlertPriority


class FakeAlertsDbManager:
    """A minimal stand-in for the alerts plugin's Manager, backed by a dict."""
    def __init__(self):
        self._items = {}
        self._next_id = 1

    def save_object(self, obj, commit=True):
        if getattr(obj, 'id', None) is None:
            obj.id = self._next_id
            self._next_id += 1
        self._items[obj.id] = obj
        return True

    def get_object(self, object_class, key=None):
        if not key:
            return object_class()
        return self._items.get(key)

    def get_all_objects(self, object_class, filter_clause=None, order_by_ref=None):
        items = list(self._items.values())
        if order_by_ref is not None:
            items.sort(key=lambda item: getattr(item, order_by_ref.key))
        return items

    def delete_object(self, object_class, key):
        self._items.pop(key, None)
        return True


@pytest.fixture
def alert_form(settings: Settings, registry: Registry):
    """An AlertForm wired to a fake in-memory manager, without opening the (blocking) modal dialog."""
    registry.register('main_window', None)
    plugin = MagicMock()
    plugin.manager = FakeAlertsDbManager()
    form = AlertForm(plugin)
    yield form


def test_help(alert_form):
    """
    Test the help button
    """
    # WHEN: The Help button is clicked
    with patch.object(alert_form, 'provide_help') as mocked_help:
        QtTest.QTest.mouseClick(alert_form.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Help),
                                QtCore.Qt.MouseButton.LeftButton)

    # THEN: The Help function should be called
    mocked_help.assert_called_once()


def test_new_template_saves_name_and_style_and_reloads(alert_form):
    """Creating a new template persists its name, text and edited style, and reloads them correctly"""
    # GIVEN: A name, some templated text, and a customized style
    alert_form.name_edit.setText('Car alert')
    alert_form.alert_text_edit.setText('Car {plate} is blocking the exit')
    alert_form.style_editor.font_size_spin_box.setValue(88)

    # WHEN: New is clicked
    alert_form.on_new_click()

    # THEN: The item was saved with its own name, text and style
    assert alert_form.item_id is not None
    saved = alert_form.manager.get_object(AlertItem, alert_form.item_id)
    assert saved.name == 'Car alert'
    assert saved.text == 'Car {plate} is blocking the exit'
    assert json.loads(saved.style)['fontSize'] == 88

    # AND: Loading it back into a fresh-looking form restores that style, and locks "Start from"
    alert_form.name_edit.setText('')
    alert_form.alert_text_edit.setText('')
    alert_form._load_alert_into_form(saved)
    assert alert_form.name_edit.text() == 'Car alert'
    assert alert_form.style_editor.font_size_spin_box.value() == 88
    assert alert_form.start_from_combo_box.isEnabled() is False


def test_start_from_swaps_style_for_a_new_unsaved_template(alert_form):
    """Changing "Start from" loads that priority's current default as an editable starting point"""
    # GIVEN: A brand-new, unsaved template (start_from is enabled by default)
    assert alert_form.start_from_combo_box.isEnabled()

    # WHEN: "Critical" is chosen as the starting point
    alert_form.start_from_combo_box.setCurrentIndex(AlertPriority.Critical.value)

    # THEN: The style editor now shows Critical's default look
    assert alert_form.style_editor.font_size_spin_box.value() == DEFAULT_PRESETS['critical']['fontSize']


def test_trigger_alert_substitutes_named_placeholders(alert_form):
    """Triggering an alert with named placeholders prompts for and substitutes each one"""
    # GIVEN: Alert text with two named placeholders
    alert_form.alert_text_edit.setText('Car {plate} is blocking {location}')

    # WHEN: The alert is triggered and the (mocked) prompt supplies values
    with patch.object(alert_form, '_prompt_for_placeholders',
                      return_value={'plate': 'KDA 123B', 'location': 'the exit'}) as mocked_prompt:
        result = alert_form.trigger_alert(alert_form.alert_text_edit.text())

    # THEN: The substituted text was sent to the alerts manager
    assert result is True
    mocked_prompt.assert_called_once_with(['plate', 'location'])
    args, kwargs = alert_form.plugin.alerts_manager.display_alert.call_args
    assert args[0] == 'Car KDA 123B is blocking the exit'


def test_trigger_alert_cancelled_prompt_does_not_display(alert_form):
    """Cancelling the parameter prompt aborts the display, rather than showing literal placeholders"""
    # GIVEN: Alert text with a placeholder
    alert_form.alert_text_edit.setText('Car {plate} is blocking the exit')

    # WHEN: The user cancels the parameter prompt
    with patch.object(alert_form, '_prompt_for_placeholders', return_value=None):
        result = alert_form.trigger_alert(alert_form.alert_text_edit.text())

    # THEN: Nothing was displayed
    assert result is False
    alert_form.plugin.alerts_manager.display_alert.assert_not_called()


def test_cannot_save_scheduled_alert_with_placeholders(alert_form):
    """A scheduled alert with named placeholders is rejected, since nobody would fill them in"""
    # GIVEN: Alert text with a placeholder, scheduled
    alert_form.alert_text_edit.setText('Car {plate} is blocking the exit')
    alert_form.schedule_group_box.setChecked(True)

    # WHEN: New is clicked
    with patch.object(QtWidgets.QMessageBox, 'warning') as mocked_warning:
        alert_form.on_new_click()

    # THEN: The user was warned and nothing was saved
    mocked_warning.assert_called_once()
    assert alert_form.item_id is None
