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
The :mod:`~openlp.plugins.custom.lib.customtab` module contains the settings tab
for the Custom Slides plugin, which is inserted into the configuration dialog.
"""
from PySide6 import QtCore, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.lib.settingstab import SettingsTab


class CustomTab(SettingsTab):
    """
    CustomTab is the Custom settings tab in the settings dialog.
    """
    def setup_ui(self):
        self.setObjectName('CustomTab')
        super(CustomTab, self).setup_ui()
        self.custom_mode_group_box = QtWidgets.QGroupBox(self.left_column)
        self.custom_mode_group_box.setObjectName('custom_mode_group_box')
        self.custom_mode_layout = QtWidgets.QFormLayout(self.custom_mode_group_box)
        self.custom_mode_layout.setObjectName('custom_mode_layout')
        self.display_footer_check_box = QtWidgets.QCheckBox(self.custom_mode_group_box)
        self.display_footer_check_box.setObjectName('display_footer_check_box')
        self.custom_mode_layout.addRow(self.display_footer_check_box)
        self.add_from_service_checkbox = QtWidgets.QCheckBox(self.custom_mode_group_box)
        self.add_from_service_checkbox.setObjectName('add_from_service_checkbox')
        self.custom_mode_layout.addRow(self.add_from_service_checkbox)
        self.left_layout.addWidget(self.custom_mode_group_box)
        self.left_layout.addStretch()
        self.right_layout.addStretch()
        self.display_footer_check_box.stateChanged.connect(self.on_display_footer_check_box_changed)
        self.add_from_service_checkbox.stateChanged.connect(self.on_add_from_service_check_box_changed)

    def retranslate_ui(self):
        self.custom_mode_group_box.setTitle(translate('CustomPlugin.CustomTab', 'Custom Display'))
        self.display_footer_check_box.setText(translate('CustomPlugin.CustomTab', 'Display footer'))
        self.add_from_service_checkbox.setText(translate('CustomPlugin.CustomTab',
                                               'Import missing custom slides from service files'))

    def on_display_footer_check_box_changed(self, check_state):
        """
        Toggle the setting for displaying the footer.

        :param check_state: The current check box state
        """
        self.display_footer = False
        # we have a set value convert to True/False
        if QtCore.Qt.CheckState(check_state) == QtCore.Qt.CheckState.Checked:
            self.display_footer = True

    def on_add_from_service_check_box_changed(self, check_state):
        """
        Allows service items to create Custom items.

        :param check_state: The current check box state
        """
        self.update_load = (QtCore.Qt.CheckState(check_state) == QtCore.Qt.CheckState.Checked)

    def load(self):
        """

        Load the settings into the dialog
        """
        self.display_footer = self.settings.value('custom/display footer')
        self.update_load = self.settings.value('custom/add custom from service')
        self.display_footer_check_box.setChecked(self.display_footer)
        self.add_from_service_checkbox.setChecked(self.update_load)

    def save(self):
        """
        Save the Dialog settings
        """
        self.settings.setValue('custom/display footer', self.display_footer)
        self.settings.setValue('custom/add custom from service', self.update_load)
        if self.tab_visited:
            self.settings_form.register_post_process('custom_config_updated')
        self.tab_visited = False
