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
The general tab of the configuration dialog.
"""
import logging
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common import get_images_filter
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.lib.settingstab import SettingsTab
from openlp.core.ui.style import UiThemes, has_ui_theme
from openlp.core.widgets.buttons import ColorButton
from openlp.core.widgets.edits import PathEdit

log = logging.getLogger(__name__)


class GeneralTab(SettingsTab):
    """
    GeneralTab is the general settings tab in the settings dialog.
    """

    def __init__(self, parent):
        """
        Initialise the general settings tab
        """
        self.logo_background_color = '#ffffff'
        self.icon_path = ':/icon/openlp-logo.svg'
        self.autoscroll_map = [None, {'dist': -1, 'pos': 0}, {'dist': -1, 'pos': 1}, {'dist': -1, 'pos': 2},
                               {'dist': 0, 'pos': 0}, {'dist': 0, 'pos': 1}, {'dist': 0, 'pos': 2},
                               {'dist': 0, 'pos': 3}, {'dist': 1, 'pos': 0}, {'dist': 1, 'pos': 1},
                               {'dist': 1, 'pos': 2}, {'dist': 1, 'pos': 3}]
        general_translated = translate('OpenLP.GeneralTab', 'General')
        super(GeneralTab, self).__init__(parent, 'Core', general_translated)

    def setup_ui(self):
        """
        Create the user interface for the general settings tab
        """
        self.setObjectName('GeneralTab')
        super(GeneralTab, self).setup_ui()
        self.tab_layout.setStretch(1, 1)
        # Application Startup
        self.startup_group_box = QtWidgets.QGroupBox(self.left_column)
        self.startup_group_box.setObjectName('startup_group_box')
        self.startup_layout = QtWidgets.QVBoxLayout(self.startup_group_box)
        self.startup_layout.setObjectName('startup_layout')
        self.warning_check_box = QtWidgets.QCheckBox(self.startup_group_box)
        self.warning_check_box.setObjectName('warning_check_box')
        self.startup_layout.addWidget(self.warning_check_box)
        self.auto_open_check_box = QtWidgets.QCheckBox(self.startup_group_box)
        self.auto_open_check_box.setObjectName('auto_open_check_box')
        self.startup_layout.addWidget(self.auto_open_check_box)
        self.show_splash_check_box = QtWidgets.QCheckBox(self.startup_group_box)
        self.show_splash_check_box.setObjectName('show_splash_check_box')
        self.startup_layout.addWidget(self.show_splash_check_box)
        self.check_for_updates_check_box = QtWidgets.QCheckBox(self.startup_group_box)
        self.check_for_updates_check_box.setObjectName('check_for_updates_check_box')
        self.startup_layout.addWidget(self.check_for_updates_check_box)
        self.check_for_remote_updates_check_box = QtWidgets.QCheckBox(self.startup_group_box)
        self.check_for_remote_updates_check_box.setObjectName('check_for_remote_updates_check_box')
        self.startup_layout.addWidget(self.check_for_remote_updates_check_box)
        self.left_layout.addWidget(self.startup_group_box)
        # Logo
        self.logo_group_box = QtWidgets.QGroupBox(self.left_column)
        self.logo_group_box.setObjectName('logo_group_box')
        self.logo_layout = QtWidgets.QFormLayout(self.logo_group_box)
        self.logo_layout.setObjectName('logo_layout')
        self.logo_file_label = QtWidgets.QLabel(self.logo_group_box)
        self.logo_file_label.setObjectName('logo_file_label')
        self.logo_file_path_edit = PathEdit(self.logo_group_box,
                                            default_path=Path(':/graphics/openlp-splash-screen.png'))
        self.logo_layout.addRow(self.logo_file_label, self.logo_file_path_edit)
        self.logo_color_label = QtWidgets.QLabel(self.logo_group_box)
        self.logo_color_label.setObjectName('logo_color_label')
        self.logo_color_button = ColorButton(self.logo_group_box)
        self.logo_color_button.setObjectName('logo_color_button')
        self.logo_layout.addRow(self.logo_color_label, self.logo_color_button)
        self.logo_hide_on_startup_check_box = QtWidgets.QCheckBox(self.logo_group_box)
        self.logo_hide_on_startup_check_box.setObjectName('logo_hide_on_startup_check_box')
        self.logo_layout.addRow(self.logo_hide_on_startup_check_box)
        self.left_layout.addWidget(self.logo_group_box)
        self.logo_color_button.colorChanged.connect(self.on_logo_background_color_changed)
        # CCLI Details
        self.ccli_group_box = QtWidgets.QGroupBox(self.left_column)
        self.ccli_group_box.setObjectName('ccli_group_box')
        self.ccli_layout = QtWidgets.QFormLayout(self.ccli_group_box)
        self.ccli_layout.setObjectName('ccli_layout')
        self.number_label = QtWidgets.QLabel(self.ccli_group_box)
        self.number_label.setObjectName('number_label')
        self.number_edit = QtWidgets.QLineEdit(self.ccli_group_box)
        self.number_edit.setValidator(QtGui.QIntValidator())
        self.number_edit.setObjectName('number_edit')
        self.ccli_layout.addRow(self.number_label, self.number_edit)
        self.left_layout.addWidget(self.ccli_group_box)
        # Ui Settings
        self.ui_group_box = QtWidgets.QGroupBox(self.right_column)
        self.ui_group_box.setObjectName('ui_group_box')
        self.ui_layout = QtWidgets.QFormLayout(self.ui_group_box)
        self.ui_layout.setObjectName('ui_layout')
        self.recent_label = QtWidgets.QLabel(self.ui_group_box)
        self.recent_label.setObjectName('recent_label')
        self.recent_spin_box = QtWidgets.QSpinBox(self.ui_group_box)
        self.recent_spin_box.setObjectName('recent_spin_box')
        self.recent_spin_box.setMinimum(0)
        self.ui_layout.addRow(self.recent_label, self.recent_spin_box)
        self.media_plugin_check_box = QtWidgets.QCheckBox(self.ui_group_box)
        self.media_plugin_check_box.setObjectName('media_plugin_check_box')
        self.ui_layout.addRow(self.media_plugin_check_box)
        self.hide_mouse_check_box = QtWidgets.QCheckBox(self.ui_group_box)
        self.hide_mouse_check_box.setObjectName('hide_mouse_check_box')
        self.ui_layout.addRow(self.hide_mouse_check_box)
        self.double_click_live_check_box = QtWidgets.QCheckBox(self.ui_group_box)
        self.double_click_live_check_box.setObjectName('double_click_live_check_box')
        self.ui_layout.addRow(self.double_click_live_check_box)
        self.single_click_preview_check_box = QtWidgets.QCheckBox(self.ui_group_box)
        self.single_click_preview_check_box.setObjectName('single_click_preview_check_box')
        self.ui_layout.addRow(self.single_click_preview_check_box)
        self.single_click_service_preview_check_box = QtWidgets.QCheckBox(self.ui_group_box)
        self.single_click_service_preview_check_box.setObjectName('single_click_service_preview_check_box')
        self.ui_layout.addRow(self.single_click_service_preview_check_box)
        self.expand_service_item_check_box = QtWidgets.QCheckBox(self.ui_group_box)
        self.expand_service_item_check_box.setObjectName('expand_service_item_check_box')
        self.ui_layout.addRow(self.expand_service_item_check_box)
        self.compact_slide_cards_check_box = QtWidgets.QCheckBox(self.ui_group_box)
        self.compact_slide_cards_check_box.setObjectName('compact_slide_cards_check_box')
        self.ui_layout.addRow(self.compact_slide_cards_check_box)
        self.slide_max_height_label = QtWidgets.QLabel(self.ui_group_box)
        self.slide_max_height_label.setObjectName('slide_max_height_label')
        self.slide_max_height_combo_box = QtWidgets.QComboBox(self.ui_group_box)
        self.slide_max_height_combo_box.addItem('', userData=0)
        self.slide_max_height_combo_box.addItem('', userData=-4)
        # Generate numeric values for combo box dynamically
        for px in range(60, 801, 5):
            self.slide_max_height_combo_box.addItem(str(px) + 'px', userData=px)
        self.slide_max_height_combo_box.setObjectName('slide_max_height_combo_box')
        self.ui_layout.addRow(self.slide_max_height_label, self.slide_max_height_combo_box)
        self.autoscroll_label = QtWidgets.QLabel(self.ui_group_box)
        self.autoscroll_label.setObjectName('autoscroll_label')
        self.autoscroll_combo_box = QtWidgets.QComboBox(self.ui_group_box)
        self.autoscroll_combo_box.addItems(['', '', '', '', '', '', '', '', '', '', '', ''])
        self.autoscroll_combo_box.setObjectName('autoscroll_combo_box')
        self.ui_layout.addRow(self.autoscroll_label)
        self.ui_layout.addRow(self.autoscroll_combo_box)
        self.slide_no_in_footer_checkbox = QtWidgets.QCheckBox(self.ui_group_box)
        self.slide_no_in_footer_checkbox.setObjectName('SlideNumbersInFooter_check_box')
        self.ui_layout.addRow(self.slide_no_in_footer_checkbox)
        self.search_as_type_check_box = QtWidgets.QCheckBox(self.ui_group_box)
        self.search_as_type_check_box.setObjectName('SearchAsType_check_box')
        self.ui_layout.addRow(self.search_as_type_check_box)
        self.enable_auto_close_check_box = QtWidgets.QCheckBox(self.ui_group_box)
        self.enable_auto_close_check_box.setObjectName('enable_auto_close_check_box')
        self.ui_layout.addRow(self.enable_auto_close_check_box)
        self.new_service_message_check_box = QtWidgets.QCheckBox(self.ui_group_box)
        self.new_service_message_check_box.setObjectName('new_service_message_check_box')
        self.ui_layout.addRow(self.new_service_message_check_box)
        self.ui_theme_style_label = QtWidgets.QLabel(self.ui_group_box)
        self.ui_theme_style_label.setObjectName('theme_style_label')
        self.ui_theme_style_combo_box = QtWidgets.QComboBox(self.ui_group_box)
        if has_ui_theme(UiThemes.QDarkStyle):
            self.ui_theme_style_combo_box.addItems(['', '', '', '', '', ''])
        else:
            self.ui_theme_style_combo_box.addItems(['', '', '', '', ''])
        self.ui_theme_style_combo_box.setObjectName('theme_style_combo_box')
        self.ui_layout.addRow(self.ui_theme_style_label)
        self.ui_layout.addRow(self.ui_theme_style_combo_box)
        self.right_layout.addWidget(self.ui_group_box)
        # Push everything in both columns to the top
        self.left_layout.addStretch()
        self.right_layout.addStretch()
        # Connect a few things
        self.search_as_type_check_box.stateChanged.connect(self.on_search_as_type_check_box_changed)

    def retranslate_ui(self):
        """
        Translate the general settings tab to the currently selected language
        """
        self.tab_title_visible = translate('OpenLP.GeneralTab', 'General')
        # Application Startup
        self.startup_group_box.setTitle(translate('OpenLP.GeneralTab', 'Application Startup'))
        self.warning_check_box.setText(translate('OpenLP.GeneralTab', 'Show blank screen warning'))
        self.auto_open_check_box.setText(translate('OpenLP.GeneralTab', 'Automatically open the previous service file'))
        self.show_splash_check_box.setText(translate('OpenLP.GeneralTab', 'Show the splash screen'))
        # Logo
        self.logo_group_box.setTitle(translate('OpenLP.GeneralTab', 'Logo'))
        self.logo_color_label.setText(UiStrings().BackgroundColorColon)
        self.logo_file_label.setText(translate('OpenLP.GeneralTab', 'Logo file:'))
        self.logo_hide_on_startup_check_box.setText(translate('OpenLP.GeneralTab', 'Don\'t show logo on startup'))
        self.check_for_updates_check_box.setText(translate('OpenLP.GeneralTab', 'Check for updates to OpenLP'))
        self.check_for_remote_updates_check_box.setText(translate('OpenLP.GeneralTab',
                                                                  'Check for updates to OpenLP Remote UI'))
        # CCLI Details
        self.ccli_group_box.setTitle(translate('OpenLP.GeneralTab', 'CCLI Details'))
        self.number_label.setText(UiStrings().CCLINumberLabel)
        self.logo_file_path_edit.dialog_caption = translate('OpenLP.AdvancedTab', 'Select Logo File')
        self.logo_file_path_edit.dialog_caption = translate('OpenLP.AdvancedTab', 'Select Logo File')
        self.logo_file_path_edit.filters = '{text};;{names} (*)'.format(
            text=get_images_filter(), names=UiStrings().AllFiles)
        # UI Settings
        self.ui_group_box.setTitle(translate('OpenLP.AdvancedTab', 'UI Settings'))
        self.recent_label.setText(translate('OpenLP.AdvancedTab', 'Number of recent service files to display:'))
        self.media_plugin_check_box.setText(translate('OpenLP.AdvancedTab',
                                                      'Open the last used Library tab on startup'))
        self.double_click_live_check_box.setText(translate('OpenLP.AdvancedTab',
                                                           'Double-click to send items straight to Live'))
        self.double_click_live_check_box.setToolTip(
            translate('OpenLP.AdvancedTab',
                      'When enabled, double-clicking a library item sends it directly to Live instead of Preview.'))
        self.single_click_preview_check_box.setText(translate('OpenLP.AdvancedTab',
                                                              'Preview items when clicked in Library'))
        self.single_click_preview_check_box.setToolTip(
            translate('OpenLP.AdvancedTab',
                      'When enabled, clicking a library item immediately loads it into Preview.'))
        self.single_click_service_preview_check_box.setText(translate('OpenLP.AdvancedTab',
                                                                      'Preview items when clicked in Service'))
        self.single_click_service_preview_check_box.setToolTip(
            translate('OpenLP.AdvancedTab',
                      'When enabled, selecting a service item immediately updates Preview.'))
        self.expand_service_item_check_box.setText(translate('OpenLP.AdvancedTab',
                                                             'Expand new service items on creation'))
        self.compact_slide_cards_check_box.setText(translate('OpenLP.AdvancedTab',
                                                             'Compact slide cards in Preview/Live (Noir theme)'))
        self.slide_max_height_label.setText(translate('OpenLP.AdvancedTab',
                                                      'Max height for non-text slides\nin slide controller:'))
        self.slide_max_height_combo_box.setItemText(0, translate('OpenLP.AdvancedTab', 'Disabled'))
        self.slide_max_height_combo_box.setItemText(1, translate('OpenLP.AdvancedTab', 'Automatic'))
        self.autoscroll_label.setText(translate('OpenLP.AdvancedTab', 'When changing slides:'))
        self.autoscroll_combo_box.setToolTip(
            translate('OpenLP.AdvancedTab',
                      'Controls how the slide list auto-scrolls as the current slide changes.'))
        self.autoscroll_combo_box.setItemText(0, translate('OpenLP.AdvancedTab', 'Do not auto-scroll'))
        self.autoscroll_combo_box.setItemText(1, translate('OpenLP.AdvancedTab',
                                                           'Auto-scroll the previous slide into view'))
        self.autoscroll_combo_box.setItemText(2, translate('OpenLP.AdvancedTab',
                                                           'Auto-scroll the previous slide to top'))
        self.autoscroll_combo_box.setItemText(3, translate('OpenLP.AdvancedTab',
                                                           'Auto-scroll the previous slide to middle'))
        self.autoscroll_combo_box.setItemText(4, translate('OpenLP.AdvancedTab',
                                                           'Auto-scroll the current slide into view'))
        self.autoscroll_combo_box.setItemText(5, translate('OpenLP.AdvancedTab',
                                                           'Auto-scroll the current slide to top'))
        self.autoscroll_combo_box.setItemText(6, translate('OpenLP.AdvancedTab',
                                                           'Auto-scroll the current slide to middle'))
        self.autoscroll_combo_box.setItemText(7, translate('OpenLP.AdvancedTab',
                                                           'Auto-scroll the current slide to bottom'))
        self.autoscroll_combo_box.setItemText(8, translate('OpenLP.AdvancedTab',
                                                           'Auto-scroll the next slide into view'))
        self.autoscroll_combo_box.setItemText(9, translate('OpenLP.AdvancedTab',
                                                           'Auto-scroll the next slide to top'))
        self.autoscroll_combo_box.setItemText(10, translate('OpenLP.AdvancedTab',
                                                            'Auto-scroll the next slide to middle'))
        self.autoscroll_combo_box.setItemText(11, translate('OpenLP.AdvancedTab',
                                                            'Auto-scroll the next slide to bottom'))
        self.enable_auto_close_check_box.setText(translate('OpenLP.AdvancedTab',
                                                           'Enable application exit confirmation'))
        self.slide_no_in_footer_checkbox.setText(translate('SongsPlugin.GeneralTab', 'Include slide number in footer'))
        self.new_service_message_check_box.setText(translate('OpenLP.AdvancedTab',
                                                             'Alert if New clicked on blank service'))
        self.search_as_type_check_box.setText(translate('SongsPlugin.GeneralTab', 'Enable search as you type'))
        self.search_as_type_check_box.setToolTip(
            translate('SongsPlugin.GeneralTab',
                      'Runs searches automatically while you type in supported library tabs.'))
        self.ui_theme_style_label.setText(translate('OpenLP.AdvancedTab', 'Interface Theme (needs restart):'))
        self.ui_theme_style_combo_box.setItemText(0, translate('OpenLP.AdvancedTab', 'Use system theme'))
        self.ui_theme_style_combo_box.setItemText(1, translate('OpenLP.AdvancedTab', 'Default Light'))
        self.ui_theme_style_combo_box.setItemText(2, translate('OpenLP.AdvancedTab', 'Default Dark'))
        if has_ui_theme(UiThemes.QDarkStyle):
            self.ui_theme_style_combo_box.setItemText(3, translate('OpenLP.AdvancedTab', 'QDarkStyle'))
            self.ui_theme_style_combo_box.setItemText(4, translate('OpenLP.AdvancedTab', 'Noir'))
            self.ui_theme_style_combo_box.setItemText(5, translate('OpenLP.AdvancedTab', 'Noir Light'))
        else:
            self.ui_theme_style_combo_box.setItemText(3, translate('OpenLP.AdvancedTab', 'Noir'))
            self.ui_theme_style_combo_box.setItemText(4, translate('OpenLP.AdvancedTab', 'Noir Light'))
        self.hide_mouse_check_box.setText(translate('OpenLP.AdvancedTab', 'Hide mouse cursor when over display window'))

    def load(self):
        """
        Load the settings to populate the form
        """
        self.number_edit.setText(self.settings.value('core/ccli number'))
        self.warning_check_box.setChecked(self.settings.value('core/blank warning'))
        self.auto_open_check_box.setChecked(self.settings.value('core/auto open'))
        self.show_splash_check_box.setChecked(self.settings.value('core/show splash'))
        self.logo_background_color = self.settings.value('core/logo background color')
        self.logo_file_path_edit.path = self.settings.value('core/logo file')
        self.logo_hide_on_startup_check_box.setChecked(self.settings.value('core/logo hide on startup'))
        self.logo_color_button.color = self.logo_background_color
        self.check_for_updates_check_box.setChecked(self.settings.value('core/update check'))
        self.check_for_remote_updates_check_box.setChecked(self.settings.value('api/update check'))
        # UI Settings
        # The max recent files value does not have an interface and so never
        # gets actually stored in the settings therefore the default value of
        # 20 will always be used.
        self.recent_spin_box.setMaximum(self.settings.value('advanced/max recent files'))
        self.recent_spin_box.setValue(self.settings.value('advanced/recent file count'))
        self.media_plugin_check_box.setChecked(self.settings.value('advanced/save current plugin'))
        self.double_click_live_check_box.setChecked(self.settings.value('advanced/double click live'))
        self.single_click_preview_check_box.setChecked(self.settings.value('advanced/single click preview'))
        self.single_click_service_preview_check_box.setChecked(
            self.settings.value('advanced/single click service preview'))
        self.expand_service_item_check_box.setChecked(self.settings.value('advanced/expand service item'))
        self.compact_slide_cards_check_box.setChecked(self.settings.value('advanced/compact slide cards'))
        slide_max_height_value = self.settings.value('advanced/slide max height')
        for i in range(0, self.slide_max_height_combo_box.count()):
            if self.slide_max_height_combo_box.itemData(i) == slide_max_height_value:
                self.slide_max_height_combo_box.setCurrentIndex(i)
        autoscroll_value = self.settings.value('advanced/autoscrolling')
        for i in range(0, len(self.autoscroll_map)):
            if self.autoscroll_map[i] == autoscroll_value and i < self.autoscroll_combo_box.count():
                self.autoscroll_combo_box.setCurrentIndex(i)
        self.enable_auto_close_check_box.setChecked(self.settings.value('advanced/enable exit confirmation'))
        ui_theme_index = GeneralTab.get_ui_theme_index(self.settings.value('advanced/ui_theme_name'))
        self.ui_theme_style_combo_box.setCurrentIndex(ui_theme_index)
        self.slide_no_in_footer_checkbox.setChecked(self.settings.value('advanced/slide numbers in footer'))
        self.new_service_message_check_box.setChecked(self.settings.value('advanced/new service message'))
        self.hide_mouse_check_box.setChecked(self.settings.value('advanced/hide mouse'))
        self.is_search_as_you_type_enabled = self.settings.value('advanced/search as type')
        self.search_as_type_check_box.setChecked(self.is_search_as_you_type_enabled)

    @staticmethod
    def get_ui_theme_index(ui_theme):
        """
        Converts :class:`~openlp.core.ui.dark.UiThemes` item to Interface Theme ComboBox

        :param ui_theme UIThemes enum item
        :return ComboBox index
        """
        if ui_theme == UiThemes.Automatic:
            return 0
        if ui_theme == UiThemes.DefaultLight:
            return 1
        if ui_theme == UiThemes.DefaultDark:
            return 2
        if ui_theme == UiThemes.QDarkStyle:
            return 3 if has_ui_theme(UiThemes.QDarkStyle) else 2
        if ui_theme == UiThemes.Noir:
            return 4 if has_ui_theme(UiThemes.QDarkStyle) else 3
        if ui_theme == UiThemes.NoirLight:
            return 5 if has_ui_theme(UiThemes.QDarkStyle) else 4

        return 0

    @staticmethod
    def get_ui_theme_name(index):
        """
        Converts "Interface Theme" ComboBox index to :class:`~openlp.core.ui.dark.UiThemes` item

        :param index "Interface Theme" ComboBox current index
        :return UiThemes enum item
        """
        if index == 0:
            return UiThemes.Automatic
        if index == 1:
            return UiThemes.DefaultLight
        if index == 2:
            return UiThemes.DefaultDark
        if index == 3:
            return UiThemes.QDarkStyle if has_ui_theme(UiThemes.QDarkStyle) else UiThemes.Noir
        if index == 4:
            return UiThemes.Noir if has_ui_theme(UiThemes.QDarkStyle) else UiThemes.NoirLight
        if index == 5:
            return UiThemes.NoirLight

        return UiThemes.Automatic

    def save(self):
        """
        Save the settings from the form
        """
        self.settings.setValue('core/blank warning', self.warning_check_box.isChecked())
        self.settings.setValue('core/auto open', self.auto_open_check_box.isChecked())
        self.settings.setValue('core/show splash', self.show_splash_check_box.isChecked())
        self.settings.setValue('core/logo background color', self.logo_background_color)
        self.settings.setValue('core/logo file', self.logo_file_path_edit.path)
        self.settings.setValue('core/logo hide on startup', self.logo_hide_on_startup_check_box.isChecked())
        self.settings.setValue('core/update check', self.check_for_updates_check_box.isChecked())
        self.settings.setValue('api/update check', self.check_for_remote_updates_check_box.isChecked())
        self.settings.setValue('core/ccli number', self.number_edit.displayText())
        # UI Settings
        self.settings.setValue('advanced/recent file count', self.recent_spin_box.value())
        self.settings.setValue('advanced/save current plugin', self.media_plugin_check_box.isChecked())
        self.settings.setValue('advanced/double click live', self.double_click_live_check_box.isChecked())
        self.settings.setValue('advanced/single click preview', self.single_click_preview_check_box.isChecked())
        self.settings.setValue('advanced/single click service preview',
                               self.single_click_service_preview_check_box.isChecked())
        self.settings.setValue('advanced/expand service item', self.expand_service_item_check_box.isChecked())
        self.settings.setValue('advanced/compact slide cards', self.compact_slide_cards_check_box.isChecked())
        slide_max_height_index = self.slide_max_height_combo_box.currentIndex()
        slide_max_height_value = self.slide_max_height_combo_box.itemData(slide_max_height_index)
        self.settings.setValue('advanced/slide max height', slide_max_height_value)
        self.settings.setValue('advanced/autoscrolling', self.autoscroll_map[self.autoscroll_combo_box.currentIndex()])
        self.settings.setValue('advanced/slide numbers in footer', self.slide_no_in_footer_checkbox.isChecked())
        self.settings.setValue('advanced/enable exit confirmation', self.enable_auto_close_check_box.isChecked())
        self.settings.setValue('advanced/new service message', self.new_service_message_check_box.isChecked())
        self.settings.setValue('advanced/hide mouse', self.hide_mouse_check_box.isChecked())
        self.settings.setValue('advanced/search as type', self.is_search_as_you_type_enabled)
        theme_name = GeneralTab.get_ui_theme_name(self.ui_theme_style_combo_box.currentIndex())
        self.settings.setValue('advanced/ui_theme_name', theme_name)
        self.post_set_up()

    def post_set_up(self):
        """
        Apply settings after the tab has loaded
        """
        self.settings_form.register_post_process('slidecontroller_live_spin_delay')

    def on_logo_background_color_changed(self, color):
        """
        Select the background color for logo.
        """
        self.logo_background_color = color

    def on_search_as_type_check_box_changed(self, check_state):
        self.is_search_as_you_type_enabled = (QtCore.Qt.CheckState(check_state) == QtCore.Qt.CheckState.Checked)
        self.settings_form.register_post_process('songs_config_updated')
        self.settings_form.register_post_process('custom_config_updated')
