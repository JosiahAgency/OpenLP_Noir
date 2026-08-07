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
Settings tab for the Timer plugin.
"""
from PySide6 import QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.common.registry import Registry
from openlp.core.lib.settingstab import SettingsTab
from openlp.core.lib.ui import find_and_set_in_combo_box


class TimerTab(SettingsTab):
    """
    Timer plugin settings.
    """
    def setup_ui(self):
        self.setObjectName('TimerTab')
        super().setup_ui()
        self.timer_theme = ''

        self.display_group_box = QtWidgets.QGroupBox(self.left_column)
        self.display_layout = QtWidgets.QFormLayout(self.display_group_box)
        self.timer_theme_label = QtWidgets.QLabel(self.display_group_box)
        self.timer_theme_combo_box = QtWidgets.QComboBox(self.display_group_box)
        self.timer_theme_combo_box.addItem('')
        self.timer_theme_combo_box.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.display_layout.addRow(self.timer_theme_label, self.timer_theme_combo_box)
        self.left_layout.addWidget(self.display_group_box)

        self.left_layout.addStretch()
        self.right_layout.addStretch()

        self.timer_theme_combo_box.activated.connect(self.on_timer_theme_combo_box_changed)
        Registry().register_function('theme_update_list', self.update_theme_list)

    def retranslate_ui(self):
        self.display_group_box.setTitle(translate('TimerPlugin.TimerTab', 'Display'))
        self.timer_theme_label.setText(translate('TimerPlugin.TimerTab', 'Timer theme:'))

    def on_timer_theme_combo_box_changed(self):
        self.timer_theme = self.timer_theme_combo_box.currentText()

    def load(self):
        self.timer_theme = self.settings.value('timer/timer theme')
        find_and_set_in_combo_box(self.timer_theme_combo_box, self.timer_theme)

    def save(self):
        self.settings.setValue('timer/timer theme', self.timer_theme)
        if self.tab_visited:
            self.settings_form.register_post_process('timer_config_updated')
        self.tab_visited = False

    def update_theme_list(self, theme_list):
        self.timer_theme_combo_box.clear()
        self.timer_theme_combo_box.addItem('')
        self.timer_theme_combo_box.addItems(theme_list)
        find_and_set_in_combo_box(self.timer_theme_combo_box, self.timer_theme)
