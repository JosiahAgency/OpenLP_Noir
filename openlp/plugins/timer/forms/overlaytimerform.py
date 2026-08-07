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
Dialog for ad-hoc timer overlay control.
"""
from PySide6 import QtWidgets

from openlp.core.common.i18n import translate
from openlp.plugins.timer.lib import TimerMode, format_seconds


class OverlayTimerForm(QtWidgets.QDialog):
    """
    Ad-hoc overlay timer controls.
    """
    def __init__(self, overlay_manager, parent=None):
        super().__init__(parent)
        self.overlay_manager = overlay_manager
        self.setWindowTitle(translate('TimerPlugin.OverlayTimerForm', 'Overlay Timer'))
        self._setup_ui()
        self.update_status_text()

    def _setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        form_layout = QtWidgets.QFormLayout()
        self.mode_combo_box = QtWidgets.QComboBox(self)
        self.mode_combo_box.addItem(translate('TimerPlugin.OverlayTimerForm', 'Countdown'), TimerMode.Countdown.value)
        self.mode_combo_box.addItem(translate('TimerPlugin.OverlayTimerForm', 'Count-up'), TimerMode.Countup.value)
        form_layout.addRow(translate('TimerPlugin.OverlayTimerForm', 'Mode:'), self.mode_combo_box)

        duration_layout = QtWidgets.QHBoxLayout()
        self.minutes_spin_box = QtWidgets.QSpinBox(self)
        self.minutes_spin_box.setRange(0, 600)
        self.minutes_spin_box.setValue(5)
        self.minutes_spin_box.setSuffix(translate('TimerPlugin.OverlayTimerForm', ' min'))
        self.seconds_spin_box = QtWidgets.QSpinBox(self)
        self.seconds_spin_box.setRange(0, 59)
        self.seconds_spin_box.setSuffix(translate('TimerPlugin.OverlayTimerForm', ' sec'))
        duration_layout.addWidget(self.minutes_spin_box)
        duration_layout.addWidget(self.seconds_spin_box)
        duration_widget = QtWidgets.QWidget(self)
        duration_widget.setLayout(duration_layout)
        form_layout.addRow(translate('TimerPlugin.OverlayTimerForm', 'Duration:'), duration_widget)
        main_layout.addLayout(form_layout)

        self.state_label = QtWidgets.QLabel(self)
        main_layout.addWidget(self.state_label)

        button_row = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton(translate('TimerPlugin.OverlayTimerForm', 'Start'), self)
        self.pause_button = QtWidgets.QPushButton(translate('TimerPlugin.OverlayTimerForm', 'Pause'), self)
        self.resume_button = QtWidgets.QPushButton(translate('TimerPlugin.OverlayTimerForm', 'Resume'), self)
        self.reset_button = QtWidgets.QPushButton(translate('TimerPlugin.OverlayTimerForm', 'Reset'), self)
        self.stop_button = QtWidgets.QPushButton(translate('TimerPlugin.OverlayTimerForm', 'Stop'), self)
        for button in [self.start_button, self.pause_button, self.resume_button, self.reset_button, self.stop_button]:
            button_row.addWidget(button)
        main_layout.addLayout(button_row)

        close_button = QtWidgets.QPushButton(translate('TimerPlugin.OverlayTimerForm', 'Close'), self)
        close_button.clicked.connect(self.accept)
        main_layout.addWidget(close_button)

        self.start_button.clicked.connect(self.on_start_clicked)
        self.pause_button.clicked.connect(self.on_pause_clicked)
        self.resume_button.clicked.connect(self.on_resume_clicked)
        self.reset_button.clicked.connect(self.on_reset_clicked)
        self.stop_button.clicked.connect(self.on_stop_clicked)
        self.overlay_manager.timer_updated.connect(self.on_timer_updated)

    def update_status_text(self):
        mode = self.overlay_manager.mode
        current = format_seconds(self.overlay_manager.current_seconds)
        state = translate('TimerPlugin.OverlayTimerForm', 'Running') if self.overlay_manager.is_running else \
            translate('TimerPlugin.OverlayTimerForm', 'Paused') if self.overlay_manager.is_paused else \
            translate('TimerPlugin.OverlayTimerForm', 'Stopped')
        mode_text = translate('TimerPlugin.OverlayTimerForm', 'Countdown') if mode == TimerMode.Countdown.value else \
            translate('TimerPlugin.OverlayTimerForm', 'Count-up')
        self.state_label.setText(translate('TimerPlugin.OverlayTimerForm',
                                           'State: {state} | Mode: {mode} | Time: {time}'
                                           ).format(state=state, mode=mode_text, time=current))

    def on_start_clicked(self):
        duration_seconds = (self.minutes_spin_box.value() * 60) + self.seconds_spin_box.value()
        self.overlay_manager.start(self.mode_combo_box.currentData(), duration_seconds)
        self.update_status_text()

    def on_pause_clicked(self):
        self.overlay_manager.pause()
        self.update_status_text()

    def on_resume_clicked(self):
        self.overlay_manager.resume()
        self.update_status_text()

    def on_reset_clicked(self):
        self.overlay_manager.reset()
        self.update_status_text()

    def on_stop_clicked(self):
        self.overlay_manager.stop()
        self.update_status_text()

    def on_timer_updated(self, _):
        self.update_status_text()
