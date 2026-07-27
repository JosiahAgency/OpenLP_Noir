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
from openlp.plugins.alerts.lib.presets import AlertPriority
from openlp.plugins.alerts.lib.style_editor import StyleEditorWidget


class AlertDialog(object):
    """
    Alert UI Class. The dialog is a template list on the left and a tabbed
    editor (Message / Style / Schedule) on the right, since each saved
    template now carries its own style rather than inheriting one of four
    fixed priority looks.
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
        alert_dialog.resize(980, 640)
        alert_dialog.setWindowIcon(UiIcons().main_icon)
        self.alert_dialog_layout = QtWidgets.QHBoxLayout(alert_dialog)
        self.alert_dialog_layout.setObjectName('alert_dialog_layout')
        self._setup_list_panel(alert_dialog)
        self._setup_editor_panel(alert_dialog)
        self.retranslate_ui(alert_dialog)

    def _setup_list_panel(self, alert_dialog):
        """The saved-template list, on the left."""
        self.list_panel = QtWidgets.QWidget(alert_dialog)
        self.list_panel_layout = QtWidgets.QVBoxLayout(self.list_panel)
        self.list_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.template_list_label = QtWidgets.QLabel(self.list_panel)
        self.list_panel_layout.addWidget(self.template_list_label)
        self.alert_list_widget = QtWidgets.QListWidget(self.list_panel)
        self.alert_list_widget.setAlternatingRowColors(True)
        self.alert_list_widget.setObjectName('alert_list_widget')
        self.list_panel_layout.addWidget(self.alert_list_widget)
        self.manage_button_layout = QtWidgets.QHBoxLayout()
        self.manage_button_layout.setObjectName('manage_button_layout')
        self.new_button = QtWidgets.QPushButton(self.list_panel)
        self.new_button.setIcon(UiIcons().new)
        self.new_button.setObjectName('new_button')
        self.manage_button_layout.addWidget(self.new_button)
        self.save_button = QtWidgets.QPushButton(self.list_panel)
        self.save_button.setEnabled(False)
        self.save_button.setIcon(UiIcons().save)
        self.save_button.setObjectName('save_button')
        self.manage_button_layout.addWidget(self.save_button)
        self.delete_button = create_button(self.list_panel, 'delete_button', role='delete', enabled=False,
                                           click=alert_dialog.on_delete_button_clicked)
        self.manage_button_layout.addWidget(self.delete_button)
        self.list_panel_layout.addLayout(self.manage_button_layout)
        self.list_panel.setMinimumWidth(260)
        self.list_panel.setMaximumWidth(340)
        self.alert_dialog_layout.addWidget(self.list_panel)

    def _setup_editor_panel(self, alert_dialog):
        """The tabbed template editor, plus the display buttons, on the right."""
        self.editor_panel = QtWidgets.QWidget(alert_dialog)
        self.editor_panel_layout = QtWidgets.QVBoxLayout(self.editor_panel)
        self.editor_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.editor_tabs = QtWidgets.QTabWidget(self.editor_panel)
        self.editor_tabs.setObjectName('editor_tabs')
        self._setup_message_tab()
        self._setup_style_tab()
        self._setup_schedule_tab()
        self.editor_panel_layout.addWidget(self.editor_tabs)
        self.display_button = create_button(alert_dialog, 'display_button', icon=UiIcons().live, enabled=False)
        self.display_close_button = create_button(alert_dialog, 'display_close_button', icon=UiIcons().live,
                                                  enabled=False)
        self.button_box = create_button_box(alert_dialog, 'button_box', ['close', 'help'],
                                            [self.display_button, self.display_close_button])
        self.editor_panel_layout.addWidget(self.button_box)
        self.alert_dialog_layout.addWidget(self.editor_panel)

    def _setup_message_tab(self):
        """Template name, text (with named placeholders) and queue priority."""
        self.message_tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(self.message_tab)
        self.name_label = QtWidgets.QLabel(self.message_tab)
        self.name_edit = QtWidgets.QLineEdit(self.message_tab)
        self.name_edit.setObjectName('name_edit')
        self.name_label.setBuddy(self.name_edit)
        layout.addRow(self.name_label, self.name_edit)
        self.alert_entry_label = QtWidgets.QLabel(self.message_tab)
        self.alert_text_edit = QtWidgets.QLineEdit(self.message_tab)
        self.alert_text_edit.setObjectName('alert_text_edit')
        self.alert_entry_label.setBuddy(self.alert_text_edit)
        layout.addRow(self.alert_entry_label, self.alert_text_edit)
        self.placeholders_label = QtWidgets.QLabel(self.message_tab)
        self.placeholders_label.setObjectName('placeholders_label')
        self.placeholders_label.setWordWrap(True)
        layout.addRow('', self.placeholders_label)
        self.priority_label = QtWidgets.QLabel(self.message_tab)
        self.priority_combo_box = QtWidgets.QComboBox(self.message_tab)
        self.priority_combo_box.setObjectName('priority_combo_box')
        self.priority_label.setBuddy(self.priority_combo_box)
        self.priority_help_button = self._create_help_button(self.message_tab, 'priority_help_button')
        layout.addRow(self.priority_label,
                      self._create_row_with_help(self.priority_combo_box, self.priority_help_button))
        self.editor_tabs.addTab(self.message_tab, '')

    def _setup_style_tab(self):
        """The template's own style: type/position, typography, background, animation."""
        self.style_tab = QtWidgets.QWidget()
        style_tab_layout = QtWidgets.QVBoxLayout(self.style_tab)
        start_from_row = QtWidgets.QHBoxLayout()
        self.start_from_label = QtWidgets.QLabel(self.style_tab)
        self.start_from_combo_box = QtWidgets.QComboBox(self.style_tab)
        self.start_from_combo_box.setObjectName('start_from_combo_box')
        self.start_from_combo_box.addItems(AlertPriority.display_names())
        self.start_from_help_button = self._create_help_button(self.style_tab, 'start_from_help_button')
        start_from_row.addWidget(self.start_from_label)
        start_from_row.addWidget(self.start_from_combo_box)
        start_from_row.addWidget(self.start_from_help_button)
        start_from_row.addStretch()
        style_tab_layout.addLayout(start_from_row)
        self.style_editor = StyleEditorWidget(self.style_tab)
        style_editor_row = QtWidgets.QHBoxLayout()
        style_editor_row.addWidget(self.style_editor.preset_tabs, 2)
        style_editor_row.addWidget(self.style_editor.preview_group_box, 1)
        style_tab_layout.addLayout(style_editor_row)
        self.editor_tabs.addTab(self.style_tab, '')

    def _setup_schedule_tab(self):
        """The optional start/end window and repeat interval."""
        self.schedule_tab = QtWidgets.QWidget()
        schedule_tab_layout = QtWidgets.QVBoxLayout(self.schedule_tab)
        self.schedule_group_box = QtWidgets.QGroupBox(self.schedule_tab)
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
        schedule_tab_layout.addWidget(self.schedule_group_box)
        schedule_tab_layout.addStretch()
        self.editor_tabs.addTab(self.schedule_tab, '')

    def retranslate_ui(self, alert_dialog):
        """
        Retranslate the UI strings

        :param alert_dialog: The dialog
        """
        alert_dialog.setWindowTitle(translate('AlertsPlugin.AlertForm', 'Alert Templates'))
        self.template_list_label.setText(translate('AlertsPlugin.AlertForm', 'Saved alerts:'))
        self.editor_tabs.setTabText(0, translate('AlertsPlugin.AlertForm', 'Message'))
        self.editor_tabs.setTabText(1, translate('AlertsPlugin.AlertForm', 'Style'))
        self.editor_tabs.setTabText(2, translate('AlertsPlugin.AlertForm', 'Schedule'))
        self.name_label.setText(translate('AlertsPlugin.AlertForm', '&Name:'))
        self.name_edit.setPlaceholderText(translate('AlertsPlugin.AlertForm', 'Optional — shown in the list below'))
        self.alert_entry_label.setText(translate('AlertsPlugin.AlertForm', 'Alert &text:'))
        self.alert_text_edit.setPlaceholderText(
            translate('AlertsPlugin.AlertForm', 'e.g. Would the owner of car {plate} please move it'))
        self.priority_label.setText(translate('AlertsPlugin.AlertForm', 'P&riority:'))
        self.start_from_label.setText(translate('AlertsPlugin.AlertForm', 'Start from:'))
        self.start_from_help_button.setToolTip('<qt>' + translate(
            'AlertsPlugin.AlertForm',
            'Copies that priority\'s current default look as a starting point for this template\'s own style. '
            'Only applies to a brand-new, unsaved template — once a template has been saved once, it keeps its '
            'own style regardless of this selection.') + '</qt>')
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
            'times, repeating at the interval set here — you do not need to click Display. Alerts with named '
            'parameters in their text cannot be scheduled, since no one is there to fill them in.') + '</qt>')
        self.new_button.setText(translate('AlertsPlugin.AlertForm', '&New'))
        self.save_button.setText(translate('AlertsPlugin.AlertForm', '&Save'))
        self.display_button.setText(translate('AlertsPlugin.AlertForm', 'Displ&ay'))
        self.display_close_button.setText(translate('AlertsPlugin.AlertForm', 'Display && Cl&ose'))
