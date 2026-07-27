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
The alerts settings tab: editor for the four priority default styles. These
are no longer "the" look of every alert — each saved alert template has its
own style, editable in the Alert Manager itself. What's edited here is used
as (a) the starting point offered when creating a new template, and (b) the
look used for alerts triggered with no template at all, e.g. via the web
remote.
"""
from PySide6 import QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.lib.settingstab import SettingsTab
from openlp.plugins.alerts.lib.presets import (DEFAULT_PRESETS, PRIORITY_KEYS, AlertPriority, get_alert_presets,
                                               save_alert_presets)
from openlp.plugins.alerts.lib.style_editor import StyleEditorWidget


class AlertsTab(SettingsTab):
    """
    AlertsTab is the alerts settings tab in the settings dialog.
    """
    def setup_ui(self):
        self.setObjectName('AlertsTab')
        super(AlertsTab, self).setup_ui()
        self.presets = {}
        self.current_priority_key = PRIORITY_KEYS[0]
        # Priority selector
        self.priority_group_box = QtWidgets.QGroupBox(self.left_column)
        self.priority_group_box.setObjectName('priority_group_box')
        self.priority_layout = QtWidgets.QFormLayout(self.priority_group_box)
        self.priority_label = QtWidgets.QLabel(self.priority_group_box)
        self.priority_combo_box = QtWidgets.QComboBox(self.priority_group_box)
        self.priority_combo_box.setObjectName('priority_combo_box')
        self.priority_layout.addRow(self.priority_label, self.priority_combo_box)
        self.left_layout.addWidget(self.priority_group_box)
        # The style editor (type/position, typography, background,
        # animation, plus preview) is shared with the per-template editor in
        # the Alert Manager.
        self.style_editor = StyleEditorWidget(self)
        self.left_layout.addWidget(self.style_editor.preset_tabs)
        self.left_layout.addStretch()
        self.right_layout.addWidget(self.style_editor.preview_group_box)
        self.right_layout.addStretch()
        # Signals
        self.priority_combo_box.currentIndexChanged.connect(self.on_priority_changed)
        self.style_editor.valueChanged.connect(self.on_value_changed)
        self.style_editor.reset_button.clicked.connect(self.on_reset_clicked)

    def retranslate_ui(self):
        self.priority_group_box.setTitle(translate('AlertsPlugin.AlertsTab', 'Default Alert Styles'))
        self.priority_label.setText(translate('AlertsPlugin.AlertsTab', 'Edit default for:'))
        self.priority_combo_box.clear()
        self.priority_combo_box.addItems(AlertPriority.display_names())

    def on_priority_changed(self, index):
        """A different priority default was selected for editing."""
        if index < 0 or not self.presets:
            return
        self.current_priority_key = PRIORITY_KEYS[index]
        self.style_editor.load_style(self.presets[self.current_priority_key])

    def on_value_changed(self):
        """Any style value changed: keep it on the current priority's default."""
        if not self.presets:
            return
        self.presets[self.current_priority_key] = self.style_editor.store_style()
        self.changed = True

    def on_reset_clicked(self):
        """Reset the currently edited default to its built-in factory look."""
        self.presets[self.current_priority_key] = dict(DEFAULT_PRESETS[self.current_priority_key])
        self.changed = True
        self.style_editor.load_style(self.presets[self.current_priority_key])

    def load(self):
        """
        Load the presets into the UI.
        """
        self.presets = get_alert_presets(self.settings)
        self.current_priority_key = PRIORITY_KEYS[self.priority_combo_box.currentIndex()]
        self.style_editor.load_style(self.presets[self.current_priority_key])
        self.changed = False

    def save(self):
        """
        Save the presets on exit of the Settings dialog.
        """
        self.presets[self.current_priority_key] = self.style_editor.store_style()
        save_alert_presets(self.settings, self.presets)
        self.changed = False
