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
import json

from PySide6 import QtCore, QtWidgets, QtGui

from openlp.core.common.i18n import translate
from openlp.core.common.registry import Registry
from openlp.plugins.alerts.forms.alertdialog import AlertDialog
from openlp.plugins.alerts.lib.db import AlertItem
from openlp.plugins.alerts.lib.placeholders import find_placeholders, substitute_placeholders
from openlp.plugins.alerts.lib.presets import PRIORITY_BEHAVIOUR, AlertPriority, new_template_style, \
    resolve_template_style


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
        self.start_from_combo_box.currentIndexChanged.connect(self.on_start_from_changed)
        self.style_editor.valueChanged.connect(self.on_style_changed)
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
        self.name_edit.setText('')
        self.alert_text_edit.setText('')
        self.schedule_group_box.setChecked(False)
        self.item_id = None
        # A fresh, unsaved template starts from the selected priority's
        # current default and may freely borrow from any of the four.
        self.start_from_combo_box.setEnabled(True)
        self.start_from_combo_box.setCurrentIndex(AlertPriority.Info.value)
        self.style_editor.load_style(new_template_style(Registry().get('settings'), AlertPriority.Info))
        # The presets may have been edited in Settings since the dialog was
        # last shown, so rebuild the priority captions and explanations
        self._refresh_priority_captions()
        self._update_priority_info()
        return QtWidgets.QDialog.exec(self)

    def _refresh_priority_captions(self):
        """
        Fill the priority selector with each priority's name. Priority now
        only controls queue behaviour — the look lives on the Style tab.
        """
        names = AlertPriority.display_names()
        current = max(0, self.priority_combo_box.currentIndex())
        self.priority_combo_box.blockSignals(True)
        self.priority_combo_box.clear()
        self.priority_combo_box.addItems(names)
        self.priority_combo_box.setCurrentIndex(min(current, self.priority_combo_box.count() - 1))
        self.priority_combo_box.blockSignals(False)

    def _update_priority_info(self, *args):
        """
        Explain, in plain words, how the selected priority behaves in the
        queue relative to other alerts.
        """
        priority = AlertPriority(max(0, self.priority_combo_box.currentIndex()))
        queue_sentences = {
            'queue': translate('AlertsPlugin.AlertForm',
                               'If another alert is on screen, this one waits its turn in the queue.'),
            'front': translate('AlertsPlugin.AlertForm',
                               'This alert goes ahead of any alerts waiting in the queue.'),
            'preempt': translate('AlertsPlugin.AlertForm',
                                 'This alert interrupts whatever alert is on screen immediately.'),
        }
        self.priority_help_button.setToolTip('<qt>' + translate(
            'AlertsPlugin.AlertForm',
            '{queue} Its look and timing are set on the Style tab, not by priority.').format(
            queue=queue_sentences[PRIORITY_BEHAVIOUR[priority]]) + '</qt>')

    def on_start_from_changed(self, index):
        """
        While creating a brand-new template, changing "Start from" swaps in
        that priority's current default style as an editable starting point.
        Has no effect once a template has its own saved style.
        """
        if not self.start_from_combo_box.isEnabled() or index < 0:
            return
        style = new_template_style(Registry().get('settings'), AlertPriority(index))
        self.style_editor.load_style(style)

    def on_style_changed(self):
        """The style was edited: if we're editing a saved template, allow saving the change."""
        if self.item_id:
            self.save_button.setEnabled(True)

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
            if self.item_id and alert.id == self.item_id:
                self.alert_list_widget.setCurrentRow(self.alert_list_widget.row(item_name))

    def _item_caption(self, alert):
        """
        Caption for an alert in the list: name (or text) plus priority and schedule.

        :param alert: The AlertItem
        """
        priority_name = AlertPriority.display_names()[alert.priority or 0]
        label = alert.name or alert.text
        caption = f'[{priority_name}] {label}'
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
        self.name_edit.setText('')
        self.alert_text_edit.setText('')

    def _apply_form_to_alert(self, alert):
        """
        Copy the form fields (name, text, priority, style, schedule) onto an AlertItem.

        :param alert: The AlertItem to update
        """
        alert.name = self.name_edit.text() or None
        alert.text = self.alert_text_edit.text()
        alert.priority = self.priority_combo_box.currentIndex()
        alert.style = json.dumps(self.style_editor.store_style())
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
        self.name_edit.setText(alert.name or '')
        self.alert_text_edit.setText(alert.text)
        self.priority_combo_box.setCurrentIndex(alert.priority or 0)
        # A saved template keeps its own style; "Start from" only matters
        # before a template has ever been saved.
        self.start_from_combo_box.setEnabled(False)
        self.style_editor.load_style(resolve_template_style(alert, Registry().get('settings')))
        self.schedule_group_box.setChecked(bool(alert.scheduled))
        if alert.scheduled:
            if alert.start_time:
                self.start_time_edit.setDateTime(QtCore.QDateTime(alert.start_time))
            if alert.end_time:
                self.end_time_edit.setDateTime(QtCore.QDateTime(alert.end_time))
            self.repeat_interval_spin_box.setValue(alert.repeat_minutes or 0)

    def _warn_if_placeholders_scheduled(self):
        """
        Scheduled alerts fire with nobody present to fill in named
        placeholders, so block scheduling text that contains any.

        :return: True if it's fine to proceed, False if the save should be aborted.
        """
        if self.schedule_group_box.isChecked() and find_placeholders(self.alert_text_edit.text()):
            QtWidgets.QMessageBox.warning(
                self, translate('AlertsPlugin.AlertForm', 'Cannot Schedule'),
                translate('AlertsPlugin.AlertForm',
                          'This alert\'s text contains {name}-style parameters, so nobody would be there to fill '
                          'them in when it fires automatically. Remove the schedule, or remove the parameters.'))
            return False
        return True

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
        elif self._warn_if_placeholders_scheduled():
            alert = AlertItem()
            self._apply_form_to_alert(alert)
            self.manager.save_object(alert)
            self.item_id = alert.id
            self.start_from_combo_box.setEnabled(False)
        self.load_list()

    def on_save_all(self):
        """
        Save the alert, we are editing.
        """
        if self.item_id and self._warn_if_placeholders_scheduled():
            alert = self.manager.get_object(AlertItem, self.item_id)
            self._apply_form_to_alert(alert)
            self.manager.save_object(alert)
            self.item_id = None
            self.load_list()
        self.save_button.setEnabled(False)

    def on_text_changed(self):
        """
        Enable save button when data has been changed by editing the form, and
        keep the parameter hint in sync with the text.
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
        self._update_placeholders_label()

    def _update_placeholders_label(self):
        """Keep the Message tab's parameter hint in sync with the alert text."""
        names = find_placeholders(self.alert_text_edit.text())
        if names:
            self.placeholders_label.setText(translate(
                'AlertsPlugin.AlertForm',
                'Parameters found: {names}. You will be asked to fill each one in when the alert is displayed.'
            ).format(names=', '.join(names)))
        else:
            self.placeholders_label.setText(translate(
                'AlertsPlugin.AlertForm',
                'Tip: put a name in curly braces, e.g. "Car {plate} is blocking the exit", to reuse this alert '
                'with different details each time.'))

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
        self.save_button.setEnabled(False)

    def trigger_alert(self, text):
        """
        Fills in any named parameters and sends the alert text for displaying.

        :param text: The alert text.
        """
        if not text:
            return False
        names = find_placeholders(text)
        values = {}
        if names:
            values = self._prompt_for_placeholders(names)
            if values is None:
                return False
        text = substitute_placeholders(text, values)
        priority = AlertPriority(self.priority_combo_box.currentIndex())
        style = self.style_editor.store_style()
        self.plugin.alerts_manager.display_alert(text, priority, style=style)
        return True

    def _prompt_for_placeholders(self, names):
        """
        Ask the user to fill in a value for each named parameter found in the
        alert text, in the order they first appear.

        :param names: The parameter names.
        :return: A dict of name -> value, or None if the user cancelled.
        """
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(translate('AlertsPlugin.AlertForm', 'Fill in the Alert'))
        layout = QtWidgets.QFormLayout(dialog)
        edits = {}
        for name in names:
            edit = QtWidgets.QLineEdit(dialog)
            edits[name] = edit
            layout.addRow(f'{name}:', edit)
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel, dialog)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return None
        return {name: edit.text() for name, edit in edits.items()}

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
