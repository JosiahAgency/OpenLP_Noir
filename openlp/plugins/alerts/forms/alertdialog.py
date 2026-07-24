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

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.lib.ui import create_button, create_button_box
from openlp.core.ui.icons import UiIcons


class AlertDialog(object):
    """
    Alert UI Class
    """
    @staticmethod
    def _create_help_button(parent, name):
        """
        A small info button which shows its explanation in a tooltip on hover
        or click, so the form is not cluttered with permanent help text.

        :param parent: The parent widget
        :param name: The object name
        """
        button = QtWidgets.QToolButton(parent)
        button.setObjectName(name)
        button.setIcon(UiIcons().info)
        button.setAutoRaise(True)
        button.setFixedSize(22, 22)
        button.setCursor(QtCore.Qt.CursorShape.WhatsThisCursor)
        button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        button.clicked.connect(
            lambda: QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), button.toolTip(), button))
        return button

    @staticmethod
    def _create_row_with_help(widget, button):
        """
        A layout holding a form row widget with its help button to the right.

        :param widget: The form widget
        :param button: The help button
        """
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)
        layout.addWidget(button)
        return layout

    def setup_ui(self, alert_dialog):
        """
        Setup the Alert UI dialog

        :param alert_dialog: The dialog
        """
        alert_dialog.setObjectName('alert_dialog')
        alert_dialog.resize(480, 420)
        alert_dialog.setWindowIcon(UiIcons().main_icon)
        self.alert_dialog_layout = QtWidgets.QGridLayout(alert_dialog)
        self.alert_dialog_layout.setObjectName('alert_dialog_layout')
        self.alert_text_layout = QtWidgets.QFormLayout()
        self.alert_text_layout.setObjectName('alert_text_layout')
        self.alert_entry_label = QtWidgets.QLabel(alert_dialog)
        self.alert_entry_label.setObjectName('alert_entry_label')
        self.alert_text_edit = QtWidgets.QLineEdit(alert_dialog)
        self.alert_text_edit.setObjectName('alert_text_edit')
        self.alert_entry_label.setBuddy(self.alert_text_edit)
        self.alert_text_layout.addRow(self.alert_entry_label, self.alert_text_edit)
        self.alert_parameter = QtWidgets.QLabel(alert_dialog)
        self.alert_parameter.setObjectName('alert_parameter')
        self.parameter_edit = QtWidgets.QLineEdit(alert_dialog)
        self.parameter_edit.setObjectName('parameter_edit')
        self.alert_parameter.setBuddy(self.parameter_edit)
        self.parameter_help_button = self._create_help_button(alert_dialog, 'parameter_help_button')
        self.alert_text_layout.addRow(self.alert_parameter,
                                      self._create_row_with_help(self.parameter_edit, self.parameter_help_button))
        self.priority_label = QtWidgets.QLabel(alert_dialog)
        self.priority_label.setObjectName('priority_label')
        self.priority_combo_box = QtWidgets.QComboBox(alert_dialog)
        self.priority_combo_box.setObjectName('priority_combo_box')
        self.priority_label.setBuddy(self.priority_combo_box)
        self.priority_help_button = self._create_help_button(alert_dialog, 'priority_help_button')
        self.alert_text_layout.addRow(self.priority_label,
                                      self._create_row_with_help(self.priority_combo_box, self.priority_help_button))
        self.alert_dialog_layout.addLayout(self.alert_text_layout, 0, 0, 1, 2)
        # Scheduling
        self.schedule_group_box = QtWidgets.QGroupBox(alert_dialog)
        self.schedule_group_box.setObjectName('schedule_group_box')
        self.schedule_group_box.setCheckable(True)
        self.schedule_group_box.setChecked(False)
        self.schedule_layout = QtWidgets.QFormLayout(self.schedule_group_box)
        self.schedule_layout.setObjectName('schedule_layout')
        self.start_time_label = QtWidgets.QLabel(self.schedule_group_box)
        self.start_time_edit = QtWidgets.QDateTimeEdit(self.schedule_group_box)
        self.start_time_edit.setObjectName('start_time_edit')
        self.start_time_edit.setCalendarPopup(True)
        self.start_time_edit.setDateTime(QtCore.QDateTime.currentDateTime())
        self.schedule_layout.addRow(self.start_time_label, self.start_time_edit)
        self.end_time_label = QtWidgets.QLabel(self.schedule_group_box)
        self.end_time_edit = QtWidgets.QDateTimeEdit(self.schedule_group_box)
        self.end_time_edit.setObjectName('end_time_edit')
        self.end_time_edit.setCalendarPopup(True)
        self.end_time_edit.setDateTime(QtCore.QDateTime.currentDateTime().addSecs(3600))
        self.schedule_layout.addRow(self.end_time_label, self.end_time_edit)
        self.repeat_interval_label = QtWidgets.QLabel(self.schedule_group_box)
        self.repeat_interval_spin_box = QtWidgets.QSpinBox(self.schedule_group_box)
        self.repeat_interval_spin_box.setObjectName('repeat_interval_spin_box')
        self.repeat_interval_spin_box.setRange(0, 1440)
        self.schedule_help_button = self._create_help_button(self.schedule_group_box, 'schedule_help_button')
        self.schedule_layout.addRow(self.repeat_interval_label,
                                    self._create_row_with_help(self.repeat_interval_spin_box,
                                                               self.schedule_help_button))
        self.alert_dialog_layout.addWidget(self.schedule_group_box, 1, 0, 1, 2)
        self.alert_list_widget = QtWidgets.QListWidget(alert_dialog)
        self.alert_list_widget.setAlternatingRowColors(True)
        self.alert_list_widget.setObjectName('alert_list_widget')
        self.alert_dialog_layout.addWidget(self.alert_list_widget, 2, 0)
        self.manage_button_layout = QtWidgets.QVBoxLayout()
        self.manage_button_layout.setObjectName('manage_button_layout')
        self.new_button = QtWidgets.QPushButton(alert_dialog)
        self.new_button.setIcon(UiIcons().new)
        self.new_button.setObjectName('new_button')
        self.manage_button_layout.addWidget(self.new_button)
        self.save_button = QtWidgets.QPushButton(alert_dialog)
        self.save_button.setEnabled(False)
        self.save_button.setIcon(UiIcons().save)
        self.save_button.setObjectName('save_button')
        self.manage_button_layout.addWidget(self.save_button)
        self.delete_button = create_button(alert_dialog, 'delete_button', role='delete', enabled=False,
                                           click=alert_dialog.on_delete_button_clicked)
        self.manage_button_layout.addWidget(self.delete_button)
        self.manage_button_layout.addStretch()
        self.alert_dialog_layout.addLayout(self.manage_button_layout, 2, 1)
        self.display_button = create_button(alert_dialog, 'display_button', icon=UiIcons().live, enabled=False)
        self.display_close_button = create_button(alert_dialog, 'display_close_button', icon=UiIcons().live,
                                                  enabled=False)
        self.button_box = create_button_box(alert_dialog, 'button_box', ['close', 'help'],
                                            [self.display_button, self.display_close_button])
        self.alert_dialog_layout.addWidget(self.button_box, 3, 0, 1, 2)
        self.retranslate_ui(alert_dialog)

    def retranslate_ui(self, alert_dialog):
        """
        Retranslate the UI strings

        :param alert_dialog: The dialog
        """
        alert_dialog.setWindowTitle(translate('AlertsPlugin.AlertForm', 'Alert Message'))
        self.alert_entry_label.setText(translate('AlertsPlugin.AlertForm', 'Alert &text:'))
        self.alert_text_edit.setPlaceholderText(
            translate('AlertsPlugin.AlertForm', 'e.g. Would the owner of car <> please move it'))
        self.alert_parameter.setText(translate('AlertsPlugin.AlertForm', '&Parameter:'))
        self.parameter_edit.setPlaceholderText(
            translate('AlertsPlugin.AlertForm', 'Optional — replaces <> in the alert text'))
        self.parameter_help_button.setToolTip('<qt>' + translate(
            'AlertsPlugin.AlertForm',
            'The parameter is optional. Put <> in the alert text as a placeholder, and it is swapped for the '
            'parameter when the alert is displayed. This lets you reuse one saved alert with different details, '
            'e.g. text "Car <> is blocking the exit" with parameter "KDA 123B".') + '</qt>')
        self.priority_label.setText(translate('AlertsPlugin.AlertForm', 'P&riority:'))
        self.schedule_group_box.setTitle(translate('AlertsPlugin.AlertForm', 'Schedule this alert'))
        self.start_time_label.setText(translate('AlertsPlugin.AlertForm', 'Start:'))
        self.end_time_label.setText(translate('AlertsPlugin.AlertForm', 'End:'))
        self.repeat_interval_label.setText(translate('AlertsPlugin.AlertForm', 'Repeat every:'))
        self.repeat_interval_spin_box.setSuffix(translate('AlertsPlugin.AlertForm', ' minutes'))
        self.repeat_interval_spin_box.setSpecialValueText(translate('AlertsPlugin.AlertForm', 'Show once'))
        self.schedule_group_box.setToolTip(translate(
            'AlertsPlugin.AlertForm',
            'Leave unticked to show the alert only when you click Display.'))
        self.schedule_help_button.setToolTip('<qt>' + translate(
            'AlertsPlugin.AlertForm',
            'Store the schedule with New or Save. The alert then displays by itself between the start and end '
            'times, repeating at the interval set here — you do not need to click Display.') + '</qt>')
        self.new_button.setText(translate('AlertsPlugin.AlertForm', '&New'))
        self.save_button.setText(translate('AlertsPlugin.AlertForm', '&Save'))
        self.display_button.setText(translate('AlertsPlugin.AlertForm', 'Displ&ay'))
        self.display_close_button.setText(translate('AlertsPlugin.AlertForm', 'Display && Cl&ose'))
