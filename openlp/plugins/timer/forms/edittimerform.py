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
Edit dialog for timer presets.
"""
from PySide6 import QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.common.registry import Registry
from openlp.plugins.timer.lib import TimerMode


class EditTimerForm(QtWidgets.QDialog):
    """
    Timer preset editor.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translate('TimerPlugin.EditTimerForm', 'Edit Timer'))
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.title_edit = QtWidgets.QLineEdit(self)
        form.addRow(translate('TimerPlugin.EditTimerForm', 'Title:'), self.title_edit)

        self.mode_combo_box = QtWidgets.QComboBox(self)
        self.mode_combo_box.addItem(translate('TimerPlugin.EditTimerForm', 'Countdown'), TimerMode.Countdown.value)
        self.mode_combo_box.addItem(translate('TimerPlugin.EditTimerForm', 'Count-up'), TimerMode.Countup.value)
        form.addRow(translate('TimerPlugin.EditTimerForm', 'Mode:'), self.mode_combo_box)

        duration_layout = QtWidgets.QHBoxLayout()
        self.minutes_spin_box = QtWidgets.QSpinBox(self)
        self.minutes_spin_box.setRange(0, 600)
        self.minutes_spin_box.setSuffix(translate('TimerPlugin.EditTimerForm', ' min'))
        self.seconds_spin_box = QtWidgets.QSpinBox(self)
        self.seconds_spin_box.setRange(0, 59)
        self.seconds_spin_box.setSuffix(translate('TimerPlugin.EditTimerForm', ' sec'))
        duration_layout.addWidget(self.minutes_spin_box)
        duration_layout.addWidget(self.seconds_spin_box)
        duration_widget = QtWidgets.QWidget(self)
        duration_widget.setLayout(duration_layout)
        form.addRow(translate('TimerPlugin.EditTimerForm', 'Duration:'), duration_widget)

        self.theme_combo_box = QtWidgets.QComboBox(self)
        self.theme_combo_box.addItem('')
        form.addRow(translate('TimerPlugin.EditTimerForm', 'Theme override:'), self.theme_combo_box)

        layout.addLayout(form)
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def load_data(self, timer_item=None):
        self.theme_combo_box.clear()
        self.theme_combo_box.addItem('')
        theme_names = Registry().execute('get_theme_names')
        if theme_names and isinstance(theme_names, list) and theme_names and isinstance(theme_names[0], list):
            theme_names = theme_names[0]
        for theme_name in theme_names or []:
            self.theme_combo_box.addItem(theme_name)
        if timer_item is None:
            self.title_edit.clear()
            self.mode_combo_box.setCurrentIndex(0)
            self.minutes_spin_box.setValue(5)
            self.seconds_spin_box.setValue(0)
            self.theme_combo_box.setCurrentIndex(0)
            return
        self.title_edit.setText(timer_item.title)
        mode = timer_item.mode or TimerMode.Countdown.value
        self.mode_combo_box.setCurrentIndex(1 if mode == TimerMode.Countup.value else 0)
        total_seconds = max(0, int(timer_item.duration_seconds or 0))
        minutes, seconds = divmod(total_seconds, 60)
        self.minutes_spin_box.setValue(minutes)
        self.seconds_spin_box.setValue(seconds)
        theme_name = timer_item.theme_name or ''
        index = self.theme_combo_box.findText(theme_name)
        self.theme_combo_box.setCurrentIndex(index if index >= 0 else 0)

    def to_payload(self):
        mode = self.mode_combo_box.currentData()
        return {
            'title': self.title_edit.text().strip(),
            'mode': mode,
            'duration_seconds': (self.minutes_spin_box.value() * 60) + self.seconds_spin_box.value(),
            'theme_name': self.theme_combo_box.currentText().strip()
        }

