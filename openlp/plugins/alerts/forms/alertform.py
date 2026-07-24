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

from PySide6 import QtCore, QtWidgets, QtGui

from openlp.core.common.i18n import translate
from openlp.core.common.registry import Registry
from openlp.plugins.alerts.lib.db import AlertItem
from openlp.plugins.alerts.lib.presets import (PRIORITY_BEHAVIOUR, PRIORITY_KEYS, AlertPriority,
                                               get_alert_presets)

from openlp.plugins.alerts.forms.alertdialog import AlertDialog


class AlertForm(QtWidgets.QDialog, AlertDialog):
    """
    Provide UI for the alert system
    """
    def __init__(self, plugin):
        """
        Initialise the alert form
        """
        super(AlertForm, self).__init__(Registry().get('main_window'),
                                        QtCore.Qt.WindowType.WindowSystemMenuHint |
                                        QtCore.Qt.WindowType.WindowTitleHint |
                                        QtCore.Qt.WindowType.WindowCloseButtonHint)
        self.manager = plugin.manager
        self.plugin = plugin
        self.item_id = None
        self.setup_ui(self)
        self._refresh_priority_captions()
        self.priority_combo_box.setCurrentIndex(AlertPriority.Info.value)
        self._update_priority_info()
        self.priority_combo_box.currentIndexChanged.connect(self._update_priority_info)
        self.display_button.clicked.connect(self.on_display_clicked)
        self.display_close_button.clicked.connect(self.on_display_close_clicked)
        self.alert_text_edit.textChanged.connect(self.on_text_changed)
        self.new_button.clicked.connect(self.on_new_click)
        self.save_button.clicked.connect(self.on_save_all)
        self.alert_list_widget.doubleClicked.connect(self.on_double_click)
        self.alert_list_widget.clicked.connect(self.on_single_click)
        self.alert_list_widget.currentRowChanged.connect(self.on_current_row_changed)
        self.schedule_group_box.toggled.connect(self.on_schedule_toggled)

    def exec(self):
        """
        Execute the dialog and return the exit code.
        """
        self.display_button.setEnabled(False)
        self.display_close_button.setEnabled(False)
        self.alert_text_edit.setText('')
        self.schedule_group_box.setChecked(False)
        # The presets may have been edited in Settings since the dialog was
        # last shown, so rebuild the priority captions and explanations
        self._refresh_priority_captions()
        self._update_priority_info()
        return QtWidgets.QDialog.exec(self)

    def _current_presets(self):
        """The live style presets, as configured in Settings."""
        return get_alert_presets(Registry().get('settings'))

    def _refresh_priority_captions(self):
        """
        Fill the priority selector with each priority's name plus how, and for
        how long, it will display, so nothing about the behaviour is hidden.
        """
        presets = self._current_presets()
        names = AlertPriority.display_names()
        type_names = self._alert_type_names()
        current = max(0, self.priority_combo_box.currentIndex())
        self.priority_combo_box.blockSignals(True)
        self.priority_combo_box.clear()
        for priority in AlertPriority:
            preset = presets[PRIORITY_KEYS[priority.value]]
            caption = translate('AlertsPlugin.AlertForm', '{name} — {type}, {seconds} s').format(
                name=names[priority.value], type=type_names.get(preset['alertType'], preset['alertType']),
                seconds=preset['timeout'])
            self.priority_combo_box.addItem(caption)
        self.priority_combo_box.setCurrentIndex(min(current, self.priority_combo_box.count() - 1))
        self.priority_combo_box.blockSignals(False)

    @staticmethod
    def _alert_type_names():
        """Short translated names for the alert types."""
        return {
            'banner': translate('AlertsPlugin.AlertForm', 'full-width banner'),
            'toast': translate('AlertsPlugin.AlertForm', 'small floating card'),
            'lowerThird': translate('AlertsPlugin.AlertForm', 'lower third'),
            'centerOverlay': translate('AlertsPlugin.AlertForm', 'center overlay'),
            'fullscreen': translate('AlertsPlugin.AlertForm', 'full-screen takeover'),
        }

    def _update_priority_info(self, *args):
        """
        Explain, in plain words, what the selected priority will do: how it
        looks, where it appears, how long it stays, and how it queues.
        """
        priority = AlertPriority(max(0, self.priority_combo_box.currentIndex()))
        preset = self._current_presets()[priority.key]
        type_names = self._alert_type_names()
        appearance = type_names.get(preset['alertType'], preset['alertType'])
        if preset['alertType'] != 'fullscreen':
            zone_v = {'top': translate('AlertsPlugin.AlertForm', 'top'),
                      'middle': translate('AlertsPlugin.AlertForm', 'middle'),
                      'bottom': translate('AlertsPlugin.AlertForm', 'bottom')}.get(preset['zoneV'], preset['zoneV'])
            zone_h = {'left': translate('AlertsPlugin.AlertForm', 'left'),
                      'center': translate('AlertsPlugin.AlertForm', 'center'),
                      'right': translate('AlertsPlugin.AlertForm', 'right')}.get(preset['zoneH'], preset['zoneH'])
            appearance += translate('AlertsPlugin.AlertForm', ' ({vertical} {horizontal})').format(
                vertical=zone_v, horizontal=zone_h)
        queue_sentences = {
            'queue': translate('AlertsPlugin.AlertForm',
                               'If another alert is on screen, it waits its turn in the queue.'),
            'front': translate('AlertsPlugin.AlertForm',
                               'It goes ahead of any alerts waiting in the queue.'),
            'preempt': translate('AlertsPlugin.AlertForm',
                                 'It interrupts whatever alert is on screen immediately.'),
        }
        self.priority_help_button.setToolTip('<qt>' + translate(
            'AlertsPlugin.AlertForm',
            'Displays as a {appearance} for {seconds} seconds. {queue} It appears when you click Display, or '
            'automatically if you schedule it below. Change the look and timing per priority in '
            'Settings → Alerts.').format(appearance=appearance, seconds=preset['timeout'],
                                         queue=queue_sentences[PRIORITY_BEHAVIOUR[priority]]) + '</qt>')

    def load_list(self):
        """
        Loads the list with alerts.
        """
        self.alert_list_widget.clear()
        alerts = self.manager.get_all_objects(AlertItem, order_by_ref=AlertItem.text)
        for alert in alerts:
            item_name = QtWidgets.QListWidgetItem(self._item_caption(alert))
            item_name.setData(QtCore.Qt.ItemDataRole.UserRole, alert.id)
            self.alert_list_widget.addItem(item_name)
            if alert.text == self.alert_text_edit.text():
                self.item_id = alert.id
                self.alert_list_widget.setCurrentRow(self.alert_list_widget.row(item_name))

    def _item_caption(self, alert):
        """
        Caption for an alert in the list: text plus priority and schedule.

        :param alert: The AlertItem
        """
        priority_name = AlertPriority.display_names()[alert.priority or 0]
        caption = f'[{priority_name}] {alert.text}'
        if alert.scheduled:
            if alert.repeat_minutes:
                caption += ' ' + translate('AlertsPlugin.AlertForm',
                                           '(scheduled, every {minutes} min)').format(minutes=alert.repeat_minutes)
            else:
                caption += ' ' + translate('AlertsPlugin.AlertForm', '(scheduled)')
            if not alert.enabled:
                caption += ' ' + translate('AlertsPlugin.AlertForm', '(finished)')
        return caption

    def on_schedule_toggled(self, checked):
        """
        Keep the button labels honest: a scheduled alert is armed by New/Save,
        not by the Display buttons.
        """
        self.on_text_changed()

    def on_display_clicked(self):
        """
        Display the current alert text.
        """
        self.trigger_alert(self.alert_text_edit.text())

    def on_display_close_clicked(self):
        """
        Close the alert preview.
        """
        if self.trigger_alert(self.alert_text_edit.text()):
            self.close()

    def on_delete_button_clicked(self):
        """
        Deletes the selected item.
        """
        item = self.alert_list_widget.currentItem()
        if item:
            item_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
            self.manager.delete_object(AlertItem, item_id)
            row = self.alert_list_widget.row(item)
            self.alert_list_widget.takeItem(row)
        self.item_id = None
        self.alert_text_edit.setText('')

    def _apply_form_to_alert(self, alert):
        """
        Copy the form fields (text, priority, schedule) onto an AlertItem.

        :param alert: The AlertItem to update
        """
        alert.text = self.alert_text_edit.text()
        alert.priority = self.priority_combo_box.currentIndex()
        alert.scheduled = self.schedule_group_box.isChecked()
        if alert.scheduled:
            alert.start_time = self.start_time_edit.dateTime().toPython()
            alert.end_time = self.end_time_edit.dateTime().toPython()
            alert.repeat_minutes = self.repeat_interval_spin_box.value()
            # (Re-)arm the schedule
            alert.enabled = True
            alert.last_fired = None
        else:
            alert.start_time = None
            alert.end_time = None
            alert.repeat_minutes = 0
            alert.enabled = True
            alert.last_fired = None

    def _load_alert_into_form(self, alert):
        """
        Populate the form fields from an AlertItem.

        :param alert: The AlertItem to show
        """
        self.alert_text_edit.setText(alert.text)
        self.priority_combo_box.setCurrentIndex(alert.priority or 0)
        self.schedule_group_box.setChecked(bool(alert.scheduled))
        if alert.scheduled:
            if alert.start_time:
                self.start_time_edit.setDateTime(QtCore.QDateTime(alert.start_time))
            if alert.end_time:
                self.end_time_edit.setDateTime(QtCore.QDateTime(alert.end_time))
            self.repeat_interval_spin_box.setValue(alert.repeat_minutes or 0)

    def on_new_click(self):
        """
        Create a new alert.
        """
        if not self.alert_text_edit.text():
            QtWidgets.QMessageBox.information(self,
                                              translate('AlertsPlugin.AlertForm', 'New Alert'),
                                              translate('AlertsPlugin.AlertForm',
                                                        'You haven\'t specified any text for your alert. \n'
                                                        'Please type in some text before clicking New.'))
        else:
            alert = AlertItem()
            self._apply_form_to_alert(alert)
            self.manager.save_object(alert)
        self.load_list()

    def on_save_all(self):
        """
        Save the alert, we are editing.
        """
        if self.item_id:
            alert = self.manager.get_object(AlertItem, self.item_id)
            self._apply_form_to_alert(alert)
            self.manager.save_object(alert)
            self.item_id = None
            self.load_list()
        self.save_button.setEnabled(False)

    def on_text_changed(self):
        """
        Enable save button when data has been changed by editing the form.
        """
        # Only enable the button, if we are editing an item.
        if self.item_id:
            self.save_button.setEnabled(True)
        if self.alert_text_edit.text():
            self.display_button.setEnabled(True)
            self.display_close_button.setEnabled(True)
        else:
            self.display_button.setEnabled(False)
            self.display_close_button.setEnabled(False)

    def on_double_click(self):
        """
        List item has been double clicked to display it.
        """
        item = self.alert_list_widget.selectedIndexes()[0]
        list_item = self.alert_list_widget.item(item.row())
        alert = self.manager.get_object(AlertItem, list_item.data(QtCore.Qt.ItemDataRole.UserRole))
        if not alert:
            return
        self._load_alert_into_form(alert)
        self.trigger_alert(alert.text)
        self.item_id = alert.id
        self.save_button.setEnabled(False)

    def on_single_click(self):
        """
        List item has been single clicked to add it to the edit field so it can be changed.
        """
        item = self.alert_list_widget.selectedIndexes()[0]
        list_item = self.alert_list_widget.item(item.row())
        alert = self.manager.get_object(AlertItem, list_item.data(QtCore.Qt.ItemDataRole.UserRole))
        if not alert:
            return
        self._load_alert_into_form(alert)
        self.item_id = alert.id
        # If the alert does not contain '<>' we clear the ParameterEdit field.
        if self.alert_text_edit.text().find('<>') == -1:
            self.parameter_edit.setText('')
        self.save_button.setEnabled(False)

    def trigger_alert(self, text):
        """
        Prepares the alert text for displaying.

        :param text: The alert text.
        """
        if not text:
            return False
        # We found '<>' in the alert text, but the ParameterEdit field is empty.
        if text.find('<>') != -1 and not self.parameter_edit.text() and \
            QtWidgets.QMessageBox.question(self,
                                           translate('AlertsPlugin.AlertForm', 'No Parameter Found'),
                                           translate('AlertsPlugin.AlertForm',
                                                     'You have not entered a parameter to be replaced.\n'
                                                     'Do you want to continue anyway?')
                                           ) == QtWidgets.QMessageBox.StandardButton.No:
            self.parameter_edit.setFocus()
            return False
        # The ParameterEdit field is not empty, but we have not found '<>'
        # in the alert text.
        elif text.find('<>') == -1 and self.parameter_edit.text() and \
            QtWidgets.QMessageBox.question(self,
                                           translate('AlertsPlugin.AlertForm', 'No Placeholder Found'),
                                           translate('AlertsPlugin.AlertForm',
                                                     'The alert text does not contain \'<>\'.\n'
                                                     'Do you want to continue anyway?')
                                           ) == QtWidgets.QMessageBox.StandardButton.No:
            self.parameter_edit.setFocus()
            return False
        text = text.replace('<>', self.parameter_edit.text())
        self.plugin.alerts_manager.display_alert(text, AlertPriority(self.priority_combo_box.currentIndex()))
        return True

    def on_current_row_changed(self, row):
        """
        Called when the *alert_list_widget*'s current row has been changed. This enables or disables buttons which
        require an item to act on.

        :param row: The row (int). If there is no current row, the value is -1.
        """
        if row == -1:
            self.display_button.setEnabled(False)
            self.display_close_button.setEnabled(False)
            self.save_button.setEnabled(False)
            self.delete_button.setEnabled(False)
        else:
            self.display_button.setEnabled(True)
            self.display_close_button.setEnabled(True)
            self.delete_button.setEnabled(True)
            # We do not need to enable the save button, as it is only enabled
            # when typing text in the "alert_text_edit".

    def provide_help(self):
        """
        Provide help within the form by opening the appropriate page of the openlp manual in the user's browser
        """
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://manual.openlp.org/alert.html"))
