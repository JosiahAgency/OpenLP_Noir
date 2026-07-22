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
The Themes configuration tab
"""
from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common import ThemeLevel
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.registry import Registry
from openlp.core.lib.settingstab import SettingsTab
from openlp.core.lib.ui import find_and_set_in_combo_box
from openlp.core.ui.icons import UiIcons


class ThemesTab(SettingsTab):
    """
    ThemesTab is the theme settings tab in the settings dialog.
    """
    def __init__(self, parent):
        """
        Constructor
        """
        self.icon_path = UiIcons().theme
        theme_translated = translate('OpenLP.ThemesTab', 'Themes')
        super(ThemesTab, self).__init__(parent, 'Themes', theme_translated)

    def setup_ui(self):
        """
        Set up the UI
        """
        self.setObjectName('ThemesTab')
        super(ThemesTab, self).setup_ui()
        self.global_group_box = QtWidgets.QGroupBox(self.left_column)
        self.global_group_box.setObjectName('global_group_box')
        self.global_group_box_layout = QtWidgets.QVBoxLayout(self.global_group_box)
        self.global_group_box_layout.setObjectName('global_group_box_layout')
        self.default_combo_box = QtWidgets.QComboBox(self.global_group_box)
        self.default_combo_box.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.default_combo_box.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.default_combo_box.setObjectName('default_combo_box')
        self.global_group_box_layout.addWidget(self.default_combo_box)
        self.default_list_view = QtWidgets.QLabel(self.global_group_box)
        self.default_list_view.setObjectName('default_list_view')
        self.global_group_box_layout.addWidget(self.default_list_view)
        self.left_layout.addWidget(self.global_group_box)
        self.universal_group_box = QtWidgets.QGroupBox(self.left_column)
        self.universal_group_box.setObjectName('universal_group_box')
        self.universal_group_box_layout = QtWidgets.QVBoxLayout(self.universal_group_box)
        self.universal_group_box_layout.setObjectName('universal_group_box_layout')
        self.item_transitions_check_box = QtWidgets.QCheckBox(self.universal_group_box)
        self.item_transitions_check_box.setObjectName('item_transitions_check_box')
        self.universal_group_box_layout.addWidget(self.item_transitions_check_box)
        self.theme_hot_reload = QtWidgets.QCheckBox(self.universal_group_box)
        self.theme_hot_reload.setObjectName('theme_hot_reload')
        self.universal_group_box_layout.addWidget(self.theme_hot_reload)
        self.left_layout.addWidget(self.universal_group_box)
        self.left_layout.addStretch()
        self.level_group_box = QtWidgets.QGroupBox(self.right_column)
        self.level_group_box.setObjectName('level_group_box')
        self.level_layout = QtWidgets.QFormLayout(self.level_group_box)
        self.level_layout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.level_layout.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.level_layout.setObjectName('level_layout')
        self.song_level_radio_button = QtWidgets.QRadioButton(self.level_group_box)
        self.song_level_radio_button.setObjectName('song_level_radio_button')
        self.song_level_label = QtWidgets.QLabel(self.level_group_box)
        self.song_level_label.setObjectName('song_level_label')
        self.level_layout.addRow(self.song_level_radio_button, self.song_level_label)
        self.service_level_radio_button = QtWidgets.QRadioButton(self.level_group_box)
        self.service_level_radio_button.setObjectName('service_level_radio_button')
        self.service_level_label = QtWidgets.QLabel(self.level_group_box)
        self.service_level_label.setObjectName('service_level_label')
        self.level_layout.addRow(self.service_level_radio_button, self.service_level_label)
        self.global_level_radio_button = QtWidgets.QRadioButton(self.level_group_box)
        self.global_level_radio_button.setObjectName('global_level_radio_button')
        self.global_level_label = QtWidgets.QLabel(self.level_group_box)
        self.global_level_label.setObjectName('global_level_label')
        self.level_layout.addRow(self.global_level_radio_button, self.global_level_label)
        label_top_margin = (self.song_level_radio_button.sizeHint().height() -
                            self.song_level_label.sizeHint().height()) // 2
        for label in [self.song_level_label, self.service_level_label, self.global_level_label]:
            rect = label.rect()
            rect.setTop(rect.top() + label_top_margin)
            label.setFrameRect(rect)
            label.setWordWrap(True)
        self.right_layout.addWidget(self.level_group_box)
        self.right_layout.addStretch()
        self.song_level_radio_button.clicked.connect(self.on_song_level_button_clicked)
        self.service_level_radio_button.clicked.connect(self.on_service_level_button_clicked)
        self.global_level_radio_button.clicked.connect(self.on_global_level_button_clicked)
        self.default_combo_box.activated.connect(self.on_default_combo_box_changed)
        Registry().register_function('theme_update_list', self.update_theme_list)

    def retranslate_ui(self):
        """
        Translate the UI on the fly
        """
        self.tab_title_visible = UiStrings().Themes
        self.global_group_box.setTitle(translate('OpenLP.ThemesTab', 'Global Theme'))
        self.universal_group_box.setTitle(translate('OpenLP.ThemesTab', 'Universal Settings'))
        self.item_transitions_check_box.setText(translate('OpenLP.ThemesTab', '&Transition between service items'))
        self.theme_hot_reload.setText(translate('OpenLP.ThemesTab', '&Reload live theme when changed'))
        self.level_group_box.setTitle(translate('OpenLP.ThemesTab', 'Theme Level'))
        self.song_level_radio_button.setText(translate('OpenLP.ThemesTab', 'S&ong Level'))
        self.song_level_label.setText(
            translate('OpenLP.ThemesTab', 'Use the theme from each song in the database. If a song doesn\'t have a '
                                          'theme associated with it, then use the service\'s theme. If the service '
                                          'doesn\'t have a theme, then use the global theme.'))
        self.service_level_radio_button.setText(translate('OpenLP.ThemesTab', '&Service Level'))
        self.service_level_label.setText(
            translate('OpenLP.ThemesTab', 'Use the theme from the service, overriding any of the individual '
                                          'songs\' themes. If the service doesn\'t have a theme, then use the global '
                                          'theme.'))
        self.global_level_radio_button.setText(translate('OpenLP.ThemesTab', '&Global Level'))
        self.global_level_label.setText(translate('OpenLP.ThemesTab', 'Use the global theme, overriding any themes '
                                                                      'associated with either the service or the '
                                                                      'songs.'))

    def load(self):
        """
        Load the theme settings into the tab
        """
        self.theme_level = self.settings.value('themes/theme level')
        self.global_theme = self.settings.value('themes/global theme')
        self.item_transitions_check_box.setChecked(self.settings.value('themes/item transitions'))
        self.theme_hot_reload.setChecked(self.settings.value('themes/hot reload'))
        if self.theme_level == ThemeLevel.Global:
            self.global_level_radio_button.setChecked(True)
        elif self.theme_level == ThemeLevel.Service:
            self.service_level_radio_button.setChecked(True)
        else:
            self.song_level_radio_button.setChecked(True)

    def save(self):
        """
        Save the settings
        """
        theme_level = self.settings.value('themes/theme level')
        global_theme = self.settings.value('themes/global theme')
        self.settings.setValue('themes/theme level', self.theme_level)
        self.settings.setValue('themes/global theme', self.global_theme)
        self.settings.setValue('themes/item transitions', self.item_transitions_check_box.isChecked())
        self.settings.setValue('themes/hot reload', self.theme_hot_reload.isChecked())
        self.renderer.set_theme_level(self.theme_level)
        if theme_level != self.theme_level:
            self.settings_form.register_post_process('theme_level_changed')
        if global_theme != self.global_theme:
            self.settings_form.register_post_process('reload_global_theme')
        if self.tab_visited:
            self.settings_form.register_post_process('theme_update_list', self.theme_manager.get_theme_names())
        self.tab_visited = False

    def on_song_level_button_clicked(self):
        """
        Set the theme level
        """
        self.theme_level = ThemeLevel.Song

    def on_service_level_button_clicked(self):
        """
        Set the theme level
        """
        self.theme_level = ThemeLevel.Service

    def on_global_level_button_clicked(self):
        """
        Set the theme level
        """
        self.theme_level = ThemeLevel.Global

    def on_default_combo_box_changed(self, value):
        """
        Set the global default theme
        """
        self.global_theme = self.default_combo_box.currentText()
        # self.renderer.set_global_theme()
        self._preview_global_theme()

    def update_theme_list(self, theme_list):
        """
        Called from ThemeManager when the Themes have changed.

        :param theme_list: The list of available themes::

                ['Bible Theme', 'Song Theme']
        """
        # Reload as may have been triggered by the ThemeManager.
        self.global_theme = self.settings.value('themes/global theme')
        self.default_combo_box.clear()
        self.default_combo_box.addItems(theme_list)
        find_and_set_in_combo_box(self.default_combo_box, self.global_theme)
        # self.renderer.set_global_theme()
        self.renderer.set_theme_level(self.theme_level)
        if self.global_theme != '':
            self._preview_global_theme()

    def _preview_global_theme(self):
        """
        Utility method to update the global theme preview image.
        """
        image_path = self.theme_manager.theme_path / '{file_name}.png'.format(file_name=self.global_theme)
        preview = QtGui.QPixmap(str(image_path))
        if not preview.isNull():
            preview = preview.scaled(300, 255, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                     QtCore.Qt.TransformationMode.SmoothTransformation)
        self.default_list_view.setPixmap(preview)
