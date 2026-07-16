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
The :mod:`~openlp.plugins.egwlibrary.lib.egwlibrarytab` module contains the settings
tab for the EGW Library plugin.
"""
from PySide6 import QtCore, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.common.registry import Registry
from openlp.core.lib.settingstab import SettingsTab
from openlp.core.lib.ui import find_and_set_in_combo_box


class EGWLibraryTab(SettingsTab):
    """
    EGWLibraryTab is the settings tab for the EGW Library plugin.
    """
    def setup_ui(self):
        self.setObjectName('EGWLibraryTab')
        super().setup_ui()
        self.search_group_box = QtWidgets.QGroupBox(self.left_column)
        self.search_group_box.setObjectName('search_group_box')
        self.search_layout = QtWidgets.QFormLayout(self.search_group_box)
        self.search_layout.setObjectName('search_layout')
        self.search_while_typing_check_box = QtWidgets.QCheckBox(self.search_group_box)
        self.search_while_typing_check_box.setObjectName('search_while_typing_check_box')
        self.search_layout.addRow(self.search_while_typing_check_box)
        self.left_layout.addWidget(self.search_group_box)
        self.display_group_box = QtWidgets.QGroupBox(self.left_column)
        self.display_group_box.setObjectName('display_group_box')
        self.display_layout = QtWidgets.QFormLayout(self.display_group_box)
        self.display_layout.setObjectName('display_layout')
        self.egw_theme_label = QtWidgets.QLabel(self.display_group_box)
        self.egw_theme_label.setObjectName('egw_theme_label')
        self.egw_theme_combo_box = QtWidgets.QComboBox(self.display_group_box)
        self.egw_theme_combo_box.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.egw_theme_combo_box.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                               QtWidgets.QSizePolicy.Policy.Fixed)
        self.egw_theme_combo_box.addItem('')
        self.egw_theme_combo_box.setObjectName('egw_theme_combo_box')
        self.display_layout.addRow(self.egw_theme_label, self.egw_theme_combo_box)
        self.left_layout.addWidget(self.display_group_box)
        self.footer_group_box = QtWidgets.QGroupBox(self.right_column)
        self.footer_group_box.setObjectName('footer_group_box')
        self.footer_layout = QtWidgets.QFormLayout(self.footer_group_box)
        self.footer_layout.setObjectName('footer_layout')
        self.footer_reference_check_box = QtWidgets.QCheckBox(self.footer_group_box)
        self.footer_reference_check_box.setObjectName('footer_reference_check_box')
        self.footer_layout.addRow(self.footer_reference_check_box)
        self.footer_copyright_check_box = QtWidgets.QCheckBox(self.footer_group_box)
        self.footer_copyright_check_box.setObjectName('footer_copyright_check_box')
        self.footer_layout.addRow(self.footer_copyright_check_box)
        self.footer_note_label = QtWidgets.QLabel(self.footer_group_box)
        self.footer_note_label.setWordWrap(True)
        self.footer_note_label.setObjectName('footer_note_label')
        self.footer_layout.addRow(self.footer_note_label)
        self.right_layout.addWidget(self.footer_group_box)
        self.left_layout.addStretch()
        self.right_layout.addStretch()
        # Signals and slots
        self.search_while_typing_check_box.stateChanged.connect(self.on_search_while_typing_check_box_changed)
        self.egw_theme_combo_box.activated.connect(self.on_egw_theme_combo_box_changed)
        self.footer_reference_check_box.stateChanged.connect(self.on_footer_reference_check_box_changed)
        self.footer_copyright_check_box.stateChanged.connect(self.on_footer_copyright_check_box_changed)
        Registry().register_function('theme_update_list', self.update_theme_list)

    def retranslate_ui(self):
        self.search_group_box.setTitle(translate('EGWLibraryPlugin.EGWLibraryTab', 'Search'))
        self.search_while_typing_check_box.setText(
            translate('EGWLibraryPlugin.EGWLibraryTab', 'Search automatically while typing'))
        self.display_group_box.setTitle(translate('EGWLibraryPlugin.EGWLibraryTab', 'Display'))
        self.egw_theme_label.setText(translate('EGWLibraryPlugin.EGWLibraryTab', 'EGW theme:'))
        self.footer_group_box.setTitle(translate('EGWLibraryPlugin.EGWLibraryTab', 'EGW Footer'))
        self.footer_reference_check_box.setText(
            translate('EGWLibraryPlugin.EGWLibraryTab', 'Show book and paragraph reference'))
        self.footer_copyright_check_box.setText(
            translate('EGWLibraryPlugin.EGWLibraryTab', 'Show copyright information'))
        self.footer_note_label.setText(translate('EGWLibraryPlugin.EGWLibraryTab',
                                                 'Note: Changes do not affect paragraphs already in the Service'))

    def on_search_while_typing_check_box_changed(self, check_state):
        """
        Event handler for the 'search_while_typing' check box
        """
        self.search_while_typing = (QtCore.Qt.CheckState(check_state) == QtCore.Qt.CheckState.Checked)

    def on_egw_theme_combo_box_changed(self):
        self.egw_theme = self.egw_theme_combo_box.currentText()

    def on_footer_reference_check_box_changed(self, check_state):
        """
        Event handler for the 'footer_reference' check box
        """
        self.show_reference_in_footer = (QtCore.Qt.CheckState(check_state) == QtCore.Qt.CheckState.Checked)

    def on_footer_copyright_check_box_changed(self, check_state):
        """
        Event handler for the 'footer_copyright' check box
        """
        self.show_copyright_in_footer = (QtCore.Qt.CheckState(check_state) == QtCore.Qt.CheckState.Checked)

    def load(self):
        self.search_while_typing = self.settings.value('egwlibrary/is search while typing enabled')
        self.search_while_typing_check_box.setChecked(self.search_while_typing)
        self.egw_theme = self.settings.value('egwlibrary/egw theme')
        find_and_set_in_combo_box(self.egw_theme_combo_box, self.egw_theme)
        self.show_reference_in_footer = self.settings.value('egwlibrary/footer show reference')
        self.footer_reference_check_box.setChecked(self.show_reference_in_footer)
        self.show_copyright_in_footer = self.settings.value('egwlibrary/footer show copyright')
        self.footer_copyright_check_box.setChecked(self.show_copyright_in_footer)

    def save(self):
        self.settings.setValue('egwlibrary/is search while typing enabled', self.search_while_typing)
        self.settings.setValue('egwlibrary/egw theme', self.egw_theme)
        self.settings.setValue('egwlibrary/footer show reference', self.show_reference_in_footer)
        self.settings.setValue('egwlibrary/footer show copyright', self.show_copyright_in_footer)
        if self.tab_visited:
            self.settings_form.register_post_process('egwlibrary_config_updated')
        self.tab_visited = False

    def update_theme_list(self, theme_list):
        """
        Called from ThemeManager when the Themes have changed.

        :param theme_list: The list of available themes
        """
        self.egw_theme_combo_box.clear()
        self.egw_theme_combo_box.addItem('')
        self.egw_theme_combo_box.addItems(theme_list)
        find_and_set_in_combo_box(self.egw_theme_combo_box, self.egw_theme)
