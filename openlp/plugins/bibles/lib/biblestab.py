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

import logging

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common.enum import DisplayStyle, LanguageSelection, LayoutStyle
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.registry import Registry
from openlp.core.lib.settingstab import SettingsTab
from openlp.core.lib.ui import find_and_set_in_combo_box
from openlp.plugins.bibles.lib import get_reference_separator, update_reference_separators


log = logging.getLogger(__name__)


class BiblesTab(SettingsTab):
    """
    BiblesTab is the Bibles settings tab in the settings dialog.
    """
    log.info('Bible Tab loaded')

    def _init_(self, *args, **kwargs):
        self.paragraph_style = True
        self.show_new_chapters = False
        self.display_style = 0
        super().__init__(*args, **kwargs)

    def setup_ui(self):
        self.setObjectName('BiblesTab')
        super(BiblesTab, self).setup_ui()
        self.verse_display_group_box = QtWidgets.QGroupBox(self.left_column)
        self.verse_display_group_box.setObjectName('verse_display_group_box')
        self.verse_display_layout = QtWidgets.QFormLayout(self.verse_display_group_box)
        self.verse_display_layout.setObjectName('verse_display_layout')
        self.is_verse_number_visible_check_box = QtWidgets.QCheckBox(self.verse_display_group_box)
        self.is_verse_number_visible_check_box.setObjectName('is_verse_number_visible_check_box')
        self.verse_display_layout.addRow(self.is_verse_number_visible_check_box)
        self.new_chapters_check_box = QtWidgets.QCheckBox(self.verse_display_group_box)
        self.new_chapters_check_box.setObjectName('new_chapters_check_box')
        self.verse_display_layout.addRow(self.new_chapters_check_box)
        self.display_style_label = QtWidgets.QLabel(self.verse_display_group_box)
        self.display_style_label.setObjectName('display_style_label')
        self.display_style_combo_box = QtWidgets.QComboBox(self.verse_display_group_box)
        self.display_style_combo_box.addItems(['', '', '', ''])
        self.display_style_combo_box.setObjectName('display_style_combo_box')
        self.verse_display_layout.addRow(self.display_style_label, self.display_style_combo_box)
        self.layout_style_label = QtWidgets.QLabel(self.verse_display_group_box)
        self.layout_style_label.setObjectName('layout_style_label')
        self.layout_style_combo_box = QtWidgets.QComboBox(self.verse_display_group_box)
        self.layout_style_combo_box.setObjectName('layout_style_combo_box')
        self.layout_style_combo_box.addItems(['', '', '', ''])
        self.verse_display_layout.addRow(self.layout_style_label, self.layout_style_combo_box)
        self.bible_second_check_box = QtWidgets.QCheckBox(self.verse_display_group_box)
        self.bible_second_check_box.setObjectName('bible_second_check_box')
        self.verse_display_layout.addRow(self.bible_second_check_box)
        self.bible_theme_label = QtWidgets.QLabel(self.verse_display_group_box)
        self.bible_theme_label.setObjectName('BibleTheme_label')
        self.bible_theme_combo_box = QtWidgets.QComboBox(self.verse_display_group_box)
        self.bible_theme_combo_box.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.bible_theme_combo_box.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                                 QtWidgets.QSizePolicy.Policy.Fixed)
        self.bible_theme_combo_box.addItem('')
        self.bible_theme_combo_box.setObjectName('BibleThemecombo_box')
        self.verse_display_layout.addRow(self.bible_theme_label, self.bible_theme_combo_box)
        self.change_note_label = QtWidgets.QLabel(self.verse_display_group_box)
        self.change_note_label.setWordWrap(True)
        self.change_note_label.setObjectName('change_note_label')
        self.verse_display_layout.addRow(self.change_note_label)
        self.left_layout.addWidget(self.verse_display_group_box)
        self.scripture_reference_group_box = QtWidgets.QGroupBox(self.left_column)
        self.scripture_reference_group_box.setObjectName('scripture_reference_group_box')
        self.scripture_reference_layout = QtWidgets.QGridLayout(self.scripture_reference_group_box)
        self.verse_separator_check_box = QtWidgets.QCheckBox(self.scripture_reference_group_box)
        self.verse_separator_check_box.setObjectName('verse_separator_check_box')
        self.scripture_reference_layout.addWidget(self.verse_separator_check_box, 0, 0)
        self.verse_separator_line_edit = QtWidgets.QLineEdit(self.scripture_reference_group_box)
        self.verse_separator_line_edit.setObjectName('verse_separator_line_edit')
        self.scripture_reference_layout.addWidget(self.verse_separator_line_edit, 0, 1)
        self.range_separator_check_box = QtWidgets.QCheckBox(self.scripture_reference_group_box)
        self.range_separator_check_box.setObjectName('range_separator_check_box')
        self.scripture_reference_layout.addWidget(self.range_separator_check_box, 1, 0)
        self.range_separator_line_edit = QtWidgets.QLineEdit(self.scripture_reference_group_box)
        self.range_separator_line_edit.setObjectName('range_separator_line_edit')
        self.scripture_reference_layout.addWidget(self.range_separator_line_edit, 1, 1)
        self.list_separator_check_box = QtWidgets.QCheckBox(self.scripture_reference_group_box)
        self.list_separator_check_box.setObjectName('list_separator_check_box')
        self.scripture_reference_layout.addWidget(self.list_separator_check_box, 2, 0)
        self.list_separator_line_edit = QtWidgets.QLineEdit(self.scripture_reference_group_box)
        self.list_separator_line_edit.setObjectName('list_separator_line_edit')
        self.scripture_reference_layout.addWidget(self.list_separator_line_edit, 2, 1)
        self.end_separator_check_box = QtWidgets.QCheckBox(self.scripture_reference_group_box)
        self.end_separator_check_box.setObjectName('end_separator_check_box')
        self.scripture_reference_layout.addWidget(self.end_separator_check_box, 3, 0)
        self.end_separator_line_edit = QtWidgets.QLineEdit(self.scripture_reference_group_box)
        self.end_separator_line_edit.setObjectName('end_separator_line_edit')
        self.end_separator_line_edit.setValidator(
            QtGui.QRegularExpressionValidator(QtCore.QRegularExpression(r'[^0-9]*'), self.end_separator_line_edit))
        self.scripture_reference_layout.addWidget(self.end_separator_line_edit, 3, 1)
        self.left_layout.addWidget(self.scripture_reference_group_box)
        self.right_column.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        self.language_selection_group_box = QtWidgets.QGroupBox(self.right_column)
        self.language_selection_group_box.setObjectName('language_selection_group_box')
        self.language_selection_layout = QtWidgets.QVBoxLayout(self.language_selection_group_box)
        self.language_selection_label = QtWidgets.QLabel(self.language_selection_group_box)
        self.language_selection_label.setObjectName('language_selection_label')
        self.language_selection_combo_box = QtWidgets.QComboBox(self.language_selection_group_box)
        self.language_selection_combo_box.setObjectName('language_selection_combo_box')
        self.language_selection_combo_box.addItems(['', '', ''])
        self.language_selection_layout.addWidget(self.language_selection_label)
        self.language_selection_layout.addWidget(self.language_selection_combo_box)
        self.right_layout.addWidget(self.language_selection_group_box)
        self.bible_quick_settings_group_box = QtWidgets.QGroupBox(self.right_column)
        self.bible_quick_settings_group_box.setObjectName('bible_quick_settings_group_box')
        self.right_layout.addWidget(self.bible_quick_settings_group_box)
        self.search_settings_layout = QtWidgets.QFormLayout(self.bible_quick_settings_group_box)
        self.search_settings_layout.setObjectName('search_settings_layout')
        self.reset_to_combined_quick_search_check_box = QtWidgets.QCheckBox(self.bible_quick_settings_group_box)
        self.reset_to_combined_quick_search_check_box.setObjectName('reset_to_combined_quick_search_check_box')
        self.search_settings_layout.addRow(self.reset_to_combined_quick_search_check_box)
        self.hide_combined_quick_error_check_box = QtWidgets.QCheckBox(self.bible_quick_settings_group_box)
        self.hide_combined_quick_error_check_box.setObjectName('hide_combined_quick_error_check_box')
        self.search_settings_layout.addRow(self.hide_combined_quick_error_check_box)
        self.bible_search_while_typing_check_box = QtWidgets.QCheckBox(self.bible_quick_settings_group_box)
        self.bible_search_while_typing_check_box.setObjectName('bible_search_while_typing_check_box')
        self.search_settings_layout.addRow(self.bible_search_while_typing_check_box)
        self.footer_group_box = QtWidgets.QGroupBox(self.right_column)
        self.footer_group_box.setObjectName('footer_group_box')
        self.footer_layout = QtWidgets.QFormLayout(self.footer_group_box)
        self.footer_layout.setObjectName('footer_layout')
        self.footer_reference_check_box = QtWidgets.QCheckBox(self.footer_group_box)
        self.footer_reference_check_box.setObjectName('footer_reference_check_box')
        self.footer_layout.addRow(self.footer_reference_check_box)
        self.footer_version_check_box = QtWidgets.QCheckBox(self.footer_group_box)
        self.footer_version_check_box.setObjectName('footer_version_check_box')
        self.footer_layout.addRow(self.footer_version_check_box)
        self.footer_copyright_check_box = QtWidgets.QCheckBox(self.footer_group_box)
        self.footer_copyright_check_box.setObjectName('footer_copyright_check_box')
        self.footer_layout.addRow(self.footer_copyright_check_box)
        self.footer_permission_check_box = QtWidgets.QCheckBox(self.footer_group_box)
        self.footer_permission_check_box.setObjectName('footer_permission_check_box')
        self.footer_layout.addRow(self.footer_permission_check_box)
        self.footer_note_label = QtWidgets.QLabel(self.footer_group_box)
        self.footer_note_label.setWordWrap(True)
        self.footer_note_label.setObjectName('footer_note_label')
        self.footer_layout.addRow(self.footer_note_label)
        self.right_layout.addWidget(self.footer_group_box)
        self.left_layout.addStretch()
        self.right_layout.addStretch()
        # Signals and slots
        self.is_verse_number_visible_check_box.stateChanged.connect(self.on_is_verse_number_visible_check_box_changed)
        self.new_chapters_check_box.stateChanged.connect(self.on_new_chapters_check_box_changed)
        self.display_style_combo_box.activated.connect(self.on_display_style_combo_box_changed)
        self.bible_theme_combo_box.activated.connect(self.on_bible_theme_combo_box_changed)
        self.layout_style_combo_box.activated.connect(self.on_layout_style_combo_box_changed)
        self.bible_second_check_box.stateChanged.connect(self.on_bible_second_check_box)
        self.verse_separator_check_box.clicked.connect(self.on_verse_separator_check_box_clicked)
        self.verse_separator_line_edit.textEdited.connect(self.on_verse_separator_line_edit_edited)
        self.verse_separator_line_edit.editingFinished.connect(self.on_verse_separator_line_edit_finished)
        self.range_separator_check_box.clicked.connect(self.on_range_separator_check_box_clicked)
        self.range_separator_line_edit.textEdited.connect(self.on_range_separator_line_edit_edited)
        self.range_separator_line_edit.editingFinished.connect(self.on_range_separator_line_edit_finished)
        self.list_separator_check_box.clicked.connect(self.on_list_separator_check_box_clicked)
        self.list_separator_line_edit.textEdited.connect(self.on_list_separator_line_edit_edited)
        self.list_separator_line_edit.editingFinished.connect(self.on_list_separator_line_edit_finished)
        self.end_separator_check_box.clicked.connect(self.on_end_separator_check_box_clicked)
        self.end_separator_line_edit.textEdited.connect(self.on_end_separator_line_edit_edited)
        self.end_separator_line_edit.editingFinished.connect(self.on_end_separator_line_edit_finished)
        Registry().register_function('theme_update_list', self.update_theme_list)
        self.language_selection_combo_box.activated.connect(self.on_language_selection_combo_box_changed)
        self.reset_to_combined_quick_search_check_box.stateChanged.connect(
            self.on_reset_to_combined_quick_search_check_box_changed)
        self.hide_combined_quick_error_check_box.stateChanged.connect(
            self.on_hide_combined_quick_error_check_box_changed)
        self.bible_search_while_typing_check_box.stateChanged.connect(
            self.on_bible_search_while_typing_check_box_changed)
        self.footer_reference_check_box.stateChanged.connect(self.on_footer_reference_check_box_changed)
        self.footer_version_check_box.stateChanged.connect(self.on_footer_version_check_box_changed)
        self.footer_copyright_check_box.stateChanged.connect(self.on_footer_copyright_check_box_changed)
        self.footer_permission_check_box.stateChanged.connect(self.on_footer_permission_check_box_changed)

    def retranslate_ui(self):
        self.verse_display_group_box.setTitle(translate('BiblesPlugin.BiblesTab', 'Verse Display'))
        self.is_verse_number_visible_check_box.setText(translate('BiblesPlugin.BiblesTab', 'Show verse numbers'))
        self.new_chapters_check_box.setText(translate('BiblesPlugin.BiblesTab', 'Only show new chapter numbers'))
        self.layout_style_label.setText(UiStrings().LayoutStyle)
        self.display_style_label.setText(UiStrings().DisplayStyle)
        self.bible_theme_label.setText(translate('BiblesPlugin.BiblesTab', 'Bible theme:'))
        self.layout_style_combo_box.setItemText(LayoutStyle.VersePerSlide, UiStrings().VersePerSlide)
        self.layout_style_combo_box.setItemText(LayoutStyle.VersePerLine, UiStrings().VersePerLine)
        self.layout_style_combo_box.setItemText(LayoutStyle.Continuous, UiStrings().Continuous)
        self.layout_style_combo_box.setItemText(LayoutStyle.WholeVerseContinuous, UiStrings().WholeVerseContinuous)
        self.display_style_combo_box.setItemText(DisplayStyle.NoBrackets,
                                                 translate('BiblesPlugin.BiblesTab', 'No Brackets'))
        self.display_style_combo_box.setItemText(DisplayStyle.Round,
                                                 translate('BiblesPlugin.BiblesTab', '( And )'))
        self.display_style_combo_box.setItemText(DisplayStyle.Curly,
                                                 translate('BiblesPlugin.BiblesTab', '{ And }'))
        self.display_style_combo_box.setItemText(DisplayStyle.Square,
                                                 translate('BiblesPlugin.BiblesTab', '[ And ]'))
        self.change_note_label.setText(translate('BiblesPlugin.BiblesTab',
                                       'Note: Changes do not affect verses in the Service'))
        self.bible_second_check_box.setText(translate('BiblesPlugin.BiblesTab', 'Display second Bible verses'))
        self.scripture_reference_group_box.setTitle(translate('BiblesPlugin.BiblesTab', 'Custom Scripture References'))
        self.verse_separator_check_box.setText(translate('BiblesPlugin.BiblesTab', 'Verse separator:'))
        self.range_separator_check_box.setText(translate('BiblesPlugin.BiblesTab', 'Range separator:'))
        self.list_separator_check_box.setText(translate('BiblesPlugin.BiblesTab', 'List separator:'))
        self.end_separator_check_box.setText(translate('BiblesPlugin.BiblesTab', 'End mark:'))
        tip_text = translate('BiblesPlugin.BiblesTab',
                             'Multiple alternative verse separators may be defined.\nThey have to be separated by a '
                             'vertical bar "|".\nPlease clear this edit line to use the default value.')
        self.verse_separator_line_edit.setToolTip(tip_text)
        self.range_separator_line_edit.setToolTip(tip_text)
        self.list_separator_line_edit.setToolTip(tip_text)
        self.end_separator_line_edit.setToolTip(tip_text)
        self.language_selection_group_box.setTitle(translate('BiblesPlugin.BiblesTab', 'Default Bible Language'))
        self.language_selection_label.setText(
            translate('BiblesPlugin.BiblesTab', 'Book name language in search field,\nsearch results and on display:'))
        self.language_selection_combo_box.setItemText(
            LanguageSelection.Bible, translate('BiblesPlugin.BiblesTab', 'Bible Language'))
        self.language_selection_combo_box.setItemText(
            LanguageSelection.Application, translate('BiblesPlugin.BiblesTab', 'Application Language'))
        self.language_selection_combo_box.setItemText(
            LanguageSelection.English, translate('BiblesPlugin.BiblesTab', 'English'))
        self.bible_quick_settings_group_box.setTitle(translate('BiblesPlugin.BiblesTab', 'Quick Search Settings'))
        self.reset_to_combined_quick_search_check_box.setText(translate('BiblesPlugin.BiblesTab',
                                                                        'Reset search type to "Text or Scripture'
                                                                        ' Reference" on startup'))
        self.hide_combined_quick_error_check_box.setText(translate('BiblesPlugin.BiblesTab',
                                                                   'Don\'t show error if nothing is found in "Text or '
                                                                   'Scripture Reference"'))
        self.bible_search_while_typing_check_box.setText(translate('BiblesPlugin.BiblesTab',
                                                                   'Search automatically while typing (Text search must'
                                                                   ' contain a\nminimum of {count} characters and a '
                                                                   'space for performance reasons)').format(count='8'))
        self.footer_group_box.setTitle(translate('BiblesPlugin.BiblesTab', 'Bible Footer'))
        self.footer_reference_check_box.setText(
            translate('BiblesPlugin.BiblesTab', 'Show book, chapter and verse reference'))
        self.footer_version_check_box.setText(translate('BiblesPlugin.BiblesTab', 'Show Bible version name'))
        self.footer_copyright_check_box.setText(translate('BiblesPlugin.BiblesTab', 'Show copyright information'))
        self.footer_permission_check_box.setText(
            translate('BiblesPlugin.BiblesTab', 'Show licensing / permission information'))
        self.footer_note_label.setText(translate('BiblesPlugin.BiblesTab',
                                                 'Note: Changes do not affect verses already in the Service'))

    def on_bible_theme_combo_box_changed(self):
        self.bible_theme = self.bible_theme_combo_box.currentText()

    def on_display_style_combo_box_changed(self):
        self.display_style = self.display_style_combo_box.currentIndex()

    def on_layout_style_combo_box_changed(self):
        self.layout_style = self.layout_style_combo_box.currentIndex()

    def on_language_selection_combo_box_changed(self):
        self.language_selection = self.language_selection_combo_box.currentIndex()

    def on_is_verse_number_visible_check_box_changed(self, check_state):
        """
        Event handler for the 'verse number visible' check box
        """
        self.is_verse_number_visible = (QtCore.Qt.CheckState(check_state) == QtCore.Qt.CheckState.Checked)
        self.check_is_verse_number_visible()

    def on_new_chapters_check_box_changed(self, check_state):
        self.show_new_chapters = False
        # We have a set value convert to True/False.
        if QtCore.Qt.CheckState(check_state) == QtCore.Qt.CheckState.Checked:
            self.show_new_chapters = True

    def on_bible_second_check_box(self, check_state):
        self.second_bibles = False
        # We have a set value convert to True/False.
        if QtCore.Qt.CheckState(check_state) == QtCore.Qt.CheckState.Checked:
            self.second_bibles = True

    def on_verse_separator_check_box_clicked(self, checked):
        if checked:
            self.verse_separator_line_edit.setFocus()
        else:
            self.verse_separator_line_edit.setText(get_reference_separator('sep_v_default'))
        self.verse_separator_line_edit.setPalette(self.get_grey_text_palette(not checked))

    def on_verse_separator_line_edit_edited(self, text):
        self.verse_separator_check_box.setChecked(True)
        self.verse_separator_line_edit.setPalette(self.get_grey_text_palette(False))

    def on_verse_separator_line_edit_finished(self):
        if self.verse_separator_line_edit.isModified():
            text = self.verse_separator_line_edit.text()
            if text == get_reference_separator('sep_v_default') or not text.replace('|', ''):
                self.verse_separator_check_box.setChecked(False)
                self.verse_separator_line_edit.setText(get_reference_separator('sep_v_default'))
                self.verse_separator_line_edit.setPalette(self.get_grey_text_palette(True))

    def on_range_separator_check_box_clicked(self, checked):
        if checked:
            self.range_separator_line_edit.setFocus()
        else:
            self.range_separator_line_edit.setText(get_reference_separator('sep_r_default'))
        self.range_separator_line_edit.setPalette(self.get_grey_text_palette(not checked))

    def on_range_separator_line_edit_edited(self, text):
        self.range_separator_check_box.setChecked(True)
        self.range_separator_line_edit.setPalette(self.get_grey_text_palette(False))

    def on_range_separator_line_edit_finished(self):
        if self.range_separator_line_edit.isModified():
            text = self.range_separator_line_edit.text()
            if text == get_reference_separator('sep_r_default') or not text.replace('|', ''):
                self.range_separator_check_box.setChecked(False)
                self.range_separator_line_edit.setText(get_reference_separator('sep_r_default'))
                self.range_separator_line_edit.setPalette(self.get_grey_text_palette(True))

    def on_list_separator_check_box_clicked(self, checked):
        if checked:
            self.list_separator_line_edit.setFocus()
        else:
            self.list_separator_line_edit.setText(get_reference_separator('sep_l_default'))
        self.list_separator_line_edit.setPalette(self.get_grey_text_palette(not checked))

    def on_list_separator_line_edit_edited(self, text):
        self.list_separator_check_box.setChecked(True)
        self.list_separator_line_edit.setPalette(self.get_grey_text_palette(False))

    def on_list_separator_line_edit_finished(self):
        if self.list_separator_line_edit.isModified():
            text = self.list_separator_line_edit.text()
            if text == get_reference_separator('sep_l_default') or not text.replace('|', ''):
                self.list_separator_check_box.setChecked(False)
                self.list_separator_line_edit.setText(get_reference_separator('sep_l_default'))
                self.list_separator_line_edit.setPalette(self.get_grey_text_palette(True))

    def on_end_separator_check_box_clicked(self, checked):
        if checked:
            self.end_separator_line_edit.setFocus()
        else:
            self.end_separator_line_edit.setText(get_reference_separator('sep_e_default'))
        self.end_separator_line_edit.setPalette(self.get_grey_text_palette(not checked))

    def on_end_separator_line_edit_edited(self, text):
        self.end_separator_check_box.setChecked(True)
        self.end_separator_line_edit.setPalette(self.get_grey_text_palette(False))

    def on_end_separator_line_edit_finished(self):
        if self.end_separator_line_edit.isModified():
            text = self.end_separator_line_edit.text()
            if text == get_reference_separator('sep_e_default') or not text.replace('|', ''):
                self.end_separator_check_box.setChecked(False)
                self.end_separator_line_edit.setText(get_reference_separator('sep_e_default'))
                self.end_separator_line_edit.setPalette(self.get_grey_text_palette(True))

    def on_reset_to_combined_quick_search_check_box_changed(self, check_state):
        """
        Event handler for the 'hide_combined_quick_error' check box
        """
        self.reset_to_combined_quick_search = (QtCore.Qt.CheckState(check_state) == QtCore.Qt.CheckState.Checked)

    def on_hide_combined_quick_error_check_box_changed(self, check_state):
        """
        Event handler for the 'hide_combined_quick_error' check box
        """
        self.hide_combined_quick_error = (QtCore.Qt.CheckState(check_state) == QtCore.Qt.CheckState.Checked)

    def on_bible_search_while_typing_check_box_changed(self, check_state):
        """
        Event handler for the 'hide_combined_quick_error' check box
        """
        self.bible_search_while_typing = (QtCore.Qt.CheckState(check_state) == QtCore.Qt.CheckState.Checked)

    def on_footer_reference_check_box_changed(self, check_state):
        """
        Event handler for the 'footer_reference' check box
        """
        self.show_reference_in_footer = (QtCore.Qt.CheckState(check_state) == QtCore.Qt.CheckState.Checked)

    def on_footer_version_check_box_changed(self, check_state):
        """
        Event handler for the 'footer_version' check box
        """
        self.show_version_in_footer = (QtCore.Qt.CheckState(check_state) == QtCore.Qt.CheckState.Checked)

    def on_footer_copyright_check_box_changed(self, check_state):
        """
        Event handler for the 'footer_copyright' check box
        """
        self.show_copyright_in_footer = (QtCore.Qt.CheckState(check_state) == QtCore.Qt.CheckState.Checked)

    def on_footer_permission_check_box_changed(self, check_state):
        """
        Event handler for the 'footer_permission' check box
        """
        self.show_permission_in_footer = (QtCore.Qt.CheckState(check_state) == QtCore.Qt.CheckState.Checked)

    def load(self):
        self.is_verse_number_visible = self.settings.value('bibles/is verse number visible')
        self.show_new_chapters = self.settings.value('bibles/display new chapter')
        self.display_style = self.settings.value('bibles/display brackets')
        self.layout_style = self.settings.value('bibles/verse layout style')
        self.bible_theme = self.settings.value('bibles/bible theme')
        self.second_bibles = self.settings.value('bibles/second bibles')
        self.is_verse_number_visible_check_box.setChecked(self.is_verse_number_visible)
        self.check_is_verse_number_visible()
        self.new_chapters_check_box.setChecked(self.show_new_chapters)
        self.display_style_combo_box.setCurrentIndex(self.display_style)
        self.layout_style_combo_box.setCurrentIndex(self.layout_style)
        self.bible_second_check_box.setChecked(self.second_bibles)
        verse_separator = self.settings.value('bibles/verse separator')
        if verse_separator.strip('|') == '':
            self.verse_separator_line_edit.setText(get_reference_separator('sep_v_default'))
            self.verse_separator_line_edit.setPalette(self.get_grey_text_palette(True))
            self.verse_separator_check_box.setChecked(False)
        else:
            self.verse_separator_line_edit.setText(verse_separator)
            self.verse_separator_line_edit.setPalette(self.get_grey_text_palette(False))
            verse_separator_set = self.settings.contains('bibles/verse separator')
            self.verse_separator_check_box.setChecked(verse_separator_set)
        range_separator = self.settings.value('bibles/range separator')
        if range_separator.strip('|') == '':
            self.range_separator_line_edit.setText(get_reference_separator('sep_r_default'))
            self.range_separator_line_edit.setPalette(self.get_grey_text_palette(True))
            self.range_separator_check_box.setChecked(False)
        else:
            self.range_separator_line_edit.setText(range_separator)
            self.range_separator_line_edit.setPalette(self.get_grey_text_palette(False))
            range_separator_set = self.settings.contains('bibles/range separator')
            self.range_separator_check_box.setChecked(range_separator_set)
        list_separator = self.settings.value('bibles/list separator')
        if list_separator.strip('|') == '':
            self.list_separator_line_edit.setText(get_reference_separator('sep_l_default'))
            self.list_separator_line_edit.setPalette(self.get_grey_text_palette(True))
            self.list_separator_check_box.setChecked(False)
        else:
            self.list_separator_line_edit.setText(list_separator)
            self.list_separator_line_edit.setPalette(self.get_grey_text_palette(False))
            list_separator_set = self.settings.contains('bibles/list separator')
            self.list_separator_check_box.setChecked(list_separator_set)
        end_separator = self.settings.value('bibles/end separator')
        if end_separator.strip('|') == '':
            self.end_separator_line_edit.setText(get_reference_separator('sep_e_default'))
            self.end_separator_line_edit.setPalette(self.get_grey_text_palette(True))
            self.end_separator_check_box.setChecked(False)
        else:
            self.end_separator_line_edit.setText(end_separator)
            self.end_separator_line_edit.setPalette(self.get_grey_text_palette(False))
            end_separator_set = self.settings.contains('bibles/end separator')
            self.end_separator_check_box.setChecked(end_separator_set)
        self.language_selection = self.settings.value('bibles/book name language')
        self.language_selection_combo_box.setCurrentIndex(self.language_selection)
        self.reset_to_combined_quick_search = self.settings.value('bibles/reset to combined quick search')
        self.reset_to_combined_quick_search_check_box.setChecked(self.reset_to_combined_quick_search)
        self.hide_combined_quick_error = self.settings.value('bibles/hide combined quick error')
        self.hide_combined_quick_error_check_box.setChecked(self.hide_combined_quick_error)
        self.bible_search_while_typing = self.settings.value('bibles/is search while typing enabled')
        self.bible_search_while_typing_check_box.setChecked(self.bible_search_while_typing)
        self.show_reference_in_footer = self.settings.value('bibles/footer show reference')
        self.footer_reference_check_box.setChecked(self.show_reference_in_footer)
        self.show_version_in_footer = self.settings.value('bibles/footer show version')
        self.footer_version_check_box.setChecked(self.show_version_in_footer)
        self.show_copyright_in_footer = self.settings.value('bibles/footer show copyright')
        self.footer_copyright_check_box.setChecked(self.show_copyright_in_footer)
        self.show_permission_in_footer = self.settings.value('bibles/footer show permission')
        self.footer_permission_check_box.setChecked(self.show_permission_in_footer)

    def save(self):
        self.settings.setValue('bibles/is verse number visible', self.is_verse_number_visible)
        self.settings.setValue('bibles/display new chapter', self.show_new_chapters)
        self.settings.setValue('bibles/display brackets', self.display_style)
        self.settings.setValue('bibles/verse layout style', self.layout_style)
        self.settings.setValue('bibles/second bibles', self.second_bibles)
        self.settings.setValue('bibles/bible theme', self.bible_theme)
        if self.verse_separator_check_box.isChecked():
            self.settings.setValue('bibles/verse separator', self.verse_separator_line_edit.text())
        else:
            self.settings.remove('bibles/verse separator')
        if self.range_separator_check_box.isChecked():
            self.settings.setValue('bibles/range separator', self.range_separator_line_edit.text())
        else:
            self.settings.remove('bibles/range separator')
        if self.list_separator_check_box.isChecked():
            self.settings.setValue('bibles/list separator', self.list_separator_line_edit.text())
        else:
            self.settings.remove('bibles/list separator')
        if self.end_separator_check_box.isChecked():
            self.settings.setValue('bibles/end separator', self.end_separator_line_edit.text())
        else:
            self.settings.remove('bibles/end separator')
        update_reference_separators()
        if self.language_selection != self.settings.value('bibles/book name language'):
            self.settings.setValue('bibles/book name language', self.language_selection)
            self.settings_form.register_post_process('bibles/bibles_load_list')
        self.settings.setValue('bibles/reset to combined quick search', self.reset_to_combined_quick_search)
        self.settings.setValue('bibles/hide combined quick error', self.hide_combined_quick_error)
        self.settings.setValue('bibles/is search while typing enabled', self.bible_search_while_typing)
        self.settings.setValue('bibles/footer show reference', self.show_reference_in_footer)
        self.settings.setValue('bibles/footer show version', self.show_version_in_footer)
        self.settings.setValue('bibles/footer show copyright', self.show_copyright_in_footer)
        self.settings.setValue('bibles/footer show permission', self.show_permission_in_footer)
        if self.tab_visited:
            self.settings_form.register_post_process('bibles_config_updated')
        self.tab_visited = False

    def update_theme_list(self, theme_list):
        """
        Called from ThemeManager when the Themes have changed.

        :param theme_list:
            The list of available themes::

                ['Bible Theme', 'Song Theme']
        """
        self.bible_theme_combo_box.clear()
        self.bible_theme_combo_box.addItem('')
        self.bible_theme_combo_box.addItems(theme_list)
        find_and_set_in_combo_box(self.bible_theme_combo_box, self.bible_theme)

    def get_grey_text_palette(self, greyed):
        """
        Returns a QPalette with greyed out text as used for placeholderText.
        """
        palette = QtGui.QPalette()
        color = self.palette().color(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Text)
        if greyed:
            color.setAlpha(128)
        palette.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.Text, color)
        return palette

    def check_is_verse_number_visible(self):
        """
        Enables / Disables verse settings dependent on is_verse_number_visible
        """
        self.new_chapters_check_box.setEnabled(self.is_verse_number_visible)
        self.display_style_label.setEnabled(self.is_verse_number_visible)
        self.display_style_combo_box.setEnabled(self.is_verse_number_visible)
