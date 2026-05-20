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

from PySide6 import QtCore, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.common.enum import SongFirstSlideMode
from openlp.core.lib.settingstab import SettingsTab
from openlp.plugins.songs.lib.db import AuthorType


class SongsTab(SettingsTab):
    """
    SongsTab is the Songs settings tab in the settings dialog.
    """
    def setup_ui(self):
        """
        Set up the configuration tab UI.
        """
        self.setObjectName('SongsTab')
        super(SongsTab, self).setup_ui()
        # Song settings group box
        self.mode_group_box = QtWidgets.QGroupBox(self.left_column)
        self.mode_group_box.setObjectName('mode_group_box')
        self.mode_layout = QtWidgets.QVBoxLayout(self.mode_group_box)
        self.mode_layout.setObjectName('mode_layout')
        self.tool_bar_active_check_box = QtWidgets.QCheckBox(self.mode_group_box)
        self.tool_bar_active_check_box.setObjectName('tool_bar_active_check_box')
        self.mode_layout.addWidget(self.tool_bar_active_check_box)
        self.update_on_edit_check_box = QtWidgets.QCheckBox(self.mode_group_box)
        self.update_on_edit_check_box.setObjectName('update_on_edit_check_box')
        self.mode_layout.addWidget(self.update_on_edit_check_box)
        self.add_from_service_check_box = QtWidgets.QCheckBox(self.mode_group_box)
        self.add_from_service_check_box.setObjectName('add_from_service_check_box')
        self.mode_layout.addWidget(self.add_from_service_check_box)
        self.auto_play_check_box = QtWidgets.QCheckBox(self.mode_group_box)
        self.auto_play_check_box.setObjectName('auto_play_check_box')
        self.mode_layout.addWidget(self.auto_play_check_box)
        self.uppercase_check_box = QtWidgets.QCheckBox(self.mode_group_box)
        self.uppercase_check_box.setObjectName('uppercase_check_box')
        self.mode_layout.addWidget(self.uppercase_check_box)
        # First Slide Mode
        self.first_slide_mode_widget = QtWidgets.QWidget(self.mode_group_box)
        self.first_slide_mode_layout = QtWidgets.QHBoxLayout(self.first_slide_mode_widget)
        self.first_slide_mode_layout.setContentsMargins(0, 0, 0, 0)
        self.first_slide_mode_label = QtWidgets.QLabel(self.first_slide_mode_widget)
        self.first_slide_mode_combobox = QtWidgets.QComboBox(self.first_slide_mode_widget)
        self.first_slide_mode_combobox.addItems(['', '', ''])
        self.first_slide_mode_layout.addWidget(self.first_slide_mode_label)
        self.first_slide_mode_layout.addWidget(self.first_slide_mode_combobox)
        self.first_slide_mode_widget.setLayout(self.first_slide_mode_layout)
        self.mode_layout.addWidget(self.first_slide_mode_widget)
        self.left_layout.addWidget(self.mode_group_box)

        # Chords group box
        self.chords_group_box = QtWidgets.QGroupBox(self.left_column)
        self.chords_group_box.setObjectName('chords_group_box')
        self.chords_group_box.setCheckable(True)
        self.chords_layout = QtWidgets.QVBoxLayout(self.chords_group_box)
        self.chords_layout.setObjectName('chords_layout')
        self.chords_info_label = QtWidgets.QLabel(self.chords_group_box)
        self.chords_info_label.setWordWrap(True)
        self.chords_layout.addWidget(self.chords_info_label)
        self.disable_chords_import_check_box = QtWidgets.QCheckBox(self.mode_group_box)
        self.disable_chords_import_check_box.setObjectName('disable_chords_import_check_box')
        self.song_key_warning_check_box = QtWidgets.QCheckBox(self.mode_group_box)
        self.song_key_warning_check_box.setObjectName('song_key_warning_checkbox')
        self.chords_layout.addWidget(self.disable_chords_import_check_box)
        self.chords_layout.addWidget(self.song_key_warning_check_box)

        # Chords notation group box
        self.chord_notation_label = QtWidgets.QLabel(self.chords_group_box)
        self.chord_notation_label.setWordWrap(True)
        self.chords_layout.addWidget(self.chord_notation_label)
        self.english_notation_radio_button = QtWidgets.QRadioButton(self.chords_group_box)
        self.english_notation_radio_button.setObjectName('english_notation_radio_button')
        self.chords_layout.addWidget(self.english_notation_radio_button)
        self.german_notation_radio_button = QtWidgets.QRadioButton(self.chords_group_box)
        self.german_notation_radio_button.setObjectName('german_notation_radio_button')
        self.chords_layout.addWidget(self.german_notation_radio_button)
        self.neolatin_notation_radio_button = QtWidgets.QRadioButton(self.chords_group_box)
        self.neolatin_notation_radio_button.setObjectName('neolatin_notation_radio_button')
        self.chords_layout.addWidget(self.neolatin_notation_radio_button)
        self.left_layout.addWidget(self.chords_group_box)

        # Footer group box
        self.footer_group_box = QtWidgets.QGroupBox(self.left_column)
        self.footer_group_box.setObjectName('footer_group_box')
        self.footer_layout = QtWidgets.QVBoxLayout(self.footer_group_box)
        self.footer_layout.setObjectName('footer_layout')
        self.footer_tabs = QtWidgets.QTabWidget(self.footer_group_box)
        self.footer_template_page = QtWidgets.QWidget()
        self.footer_template_layout = QtWidgets.QVBoxLayout(self.footer_template_page)
        self.footer_edit_box = QtWidgets.QTextEdit(self.footer_template_page)
        self.footer_template_layout.addWidget(self.footer_edit_box)
        self.footer_aux_layout = QtWidgets.QHBoxLayout()
        self.footer_help_label = QtWidgets.QLabel(self.footer_template_page)
        self.footer_aux_layout.addWidget(self.footer_help_label)
        self.footer_aux_layout.addStretch()
        self.footer_reset_button = QtWidgets.QPushButton(self.footer_template_page)
        self.footer_aux_layout.addWidget(self.footer_reset_button)
        self.footer_template_layout.addLayout(self.footer_aux_layout)
        self.footer_tabs.addTab(self.footer_template_page, '')
        self.footer_legend_page = QtWidgets.QWidget()
        self.footer_legend_layout = QtWidgets.QVBoxLayout(self.footer_legend_page)
        self.footer_placeholder_info = QtWidgets.QTextEdit(self.footer_legend_page)
        self.footer_legend_layout.addWidget(self.footer_placeholder_info)
        self.footer_tabs.addTab(self.footer_legend_page, '')
        self.footer_layout.addWidget(self.footer_tabs)
        self.right_layout.addWidget(self.footer_group_box)

        # CCLI SongSelect login group box
        self.ccli_login_group_box = QtWidgets.QGroupBox(self.left_column)
        self.ccli_login_group_box.setObjectName('ccli_login_group_box')
        self.ccli_login_layout = QtWidgets.QFormLayout(self.ccli_login_group_box)
        self.ccli_login_layout.setObjectName('ccli_login_layout')
        self.ccli_username_label = QtWidgets.QLabel(self.ccli_login_group_box)
        self.ccli_username_label.setObjectName('ccli_username_label')
        self.ccli_username = QtWidgets.QLineEdit(self.ccli_login_group_box)
        self.ccli_username.setObjectName('ccli_username')
        self.ccli_login_layout.addRow(self.ccli_username_label, self.ccli_username)
        self.ccli_password_label = QtWidgets.QLabel(self.ccli_login_group_box)
        self.ccli_password_label.setObjectName('ccli_password_label')
        self.ccli_password = QtWidgets.QLineEdit(self.ccli_login_group_box)
        self.ccli_password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.ccli_password.setObjectName('ccli_password')
        self.ccli_login_layout.addRow(self.ccli_password_label, self.ccli_password)
        self.right_layout.addWidget(self.ccli_login_group_box)

        # Enable Preview of first line group box
        self.preview_group_box = QtWidgets.QGroupBox(self.left_column)
        self.preview_group_box.setObjectName('preview_group_box')
        self.preview_group_box.setCheckable(True)  # whole feature can be enabled/disabled
        self.preview_layout = QtWidgets.QVBoxLayout(self.preview_group_box)
        self.preview_layout.setObjectName('preview_layout')
        self.preview_info_label = QtWidgets.QLabel(self.preview_group_box)  # Info label
        self.preview_info_label.setWordWrap(True)
        self.preview_layout.addWidget(self.preview_info_label)

        # Individual strophe type checkboxes for preview
        self.preview_intro_check_box = QtWidgets.QCheckBox(self.preview_group_box)
        self.preview_intro_check_box.setObjectName('preview_intro_check_box')
        self.preview_layout.addWidget(self.preview_intro_check_box)

        self.preview_verse_check_box = QtWidgets.QCheckBox(self.preview_group_box)
        self.preview_verse_check_box.setObjectName('preview_verse_check_box')
        self.preview_layout.addWidget(self.preview_verse_check_box)

        self.preview_chorus_check_box = QtWidgets.QCheckBox(self.preview_group_box)
        self.preview_chorus_check_box.setObjectName('preview_chorus_check_box')
        self.preview_layout.addWidget(self.preview_chorus_check_box)

        self.preview_bridge_check_box = QtWidgets.QCheckBox(self.preview_group_box)
        self.preview_bridge_check_box.setObjectName('preview_bridge_check_box')
        self.preview_layout.addWidget(self.preview_bridge_check_box)

        self.preview_pre_chorus_check_box = QtWidgets.QCheckBox(self.preview_group_box)
        self.preview_pre_chorus_check_box.setObjectName('preview_pre_chorus_check_box')
        self.preview_layout.addWidget(self.preview_pre_chorus_check_box)

        self.preview_ending_check_box = QtWidgets.QCheckBox(self.preview_group_box)
        self.preview_ending_check_box.setObjectName('preview_ending_check_box')
        self.preview_layout.addWidget(self.preview_ending_check_box)

        self.preview_other_check_box = QtWidgets.QCheckBox(self.preview_group_box)
        self.preview_other_check_box.setObjectName('preview_other_check_box')
        self.preview_layout.addWidget(self.preview_other_check_box)

        # Add group box to the left column
        self.left_layout.addWidget(self.preview_group_box)

        # Make sure everything is top-aligned
        self.left_layout.addStretch()
        self.right_layout.addStretch()

        # Connect all the signals!
        self.tool_bar_active_check_box.stateChanged.connect(self.on_tool_bar_active_check_box_changed)
        self.update_on_edit_check_box.stateChanged.connect(self.on_update_on_edit_check_box_changed)
        self.add_from_service_check_box.stateChanged.connect(self.on_add_from_service_check_box_changed)
        self.first_slide_mode_combobox.currentIndexChanged.connect(self.on_first_slide_mode_combo_box_changed)
        self.auto_play_check_box.stateChanged.connect(self.on_auto_play_check_box_changed)
        self.uppercase_check_box.stateChanged.connect(self.on_uppercase_check_box_changed)
        self.disable_chords_import_check_box.stateChanged.connect(self.on_disable_chords_import_check_box_changed)
        self.song_key_warning_check_box.stateChanged.connect(self.on_song_key_warning_check_box_changed)
        self.english_notation_radio_button.clicked.connect(self.on_english_notation_button_clicked)
        self.german_notation_radio_button.clicked.connect(self.on_german_notation_button_clicked)
        self.neolatin_notation_radio_button.clicked.connect(self.on_neolatin_notation_button_clicked)
        self.footer_reset_button.clicked.connect(self.on_footer_reset_button_clicked)

        # Connect Preview group signals
        self.preview_group_box.toggled.connect(self.on_preview_group_box_toggled)
        self.preview_intro_check_box.stateChanged.connect(self.on_preview_intro_check_box_changed)
        self.preview_verse_check_box.stateChanged.connect(self.on_preview_verse_check_box_changed)
        self.preview_chorus_check_box.stateChanged.connect(self.on_preview_chorus_check_box_changed)
        self.preview_bridge_check_box.stateChanged.connect(self.on_preview_bridge_check_box_changed)
        self.preview_pre_chorus_check_box.stateChanged.connect(self.on_preview_pre_chorus_check_box_changed)
        self.preview_ending_check_box.stateChanged.connect(self.on_preview_ending_check_box_changed)
        self.preview_other_check_box.stateChanged.connect(self.on_preview_other_check_box_changed)

    def retranslate_ui(self):
        self.mode_group_box.setTitle(translate('SongsPlugin.SongsTab', 'Song related settings'))
        self.tool_bar_active_check_box.setText(translate('SongsPlugin.SongsTab',
                                                         'Enable "Go to verse" button in Live panel'))
        self.update_on_edit_check_box.setText(translate('SongsPlugin.SongsTab', 'Update service from song edit'))
        self.add_from_service_check_box.setText(translate('SongsPlugin.SongsTab',
                                                          'Import missing songs from Service files'))
        self.first_slide_mode_label.setText(translate('SongsPlugin.SongsTab', 'Add first slide:'))
        self.first_slide_mode_combobox.setItemText(0, translate('SongsPlugin.SongsTab', 'None'))
        self.first_slide_mode_combobox.setItemText(1, translate('SongsPlugin.SongsTab', 'Songbook'))
        self.first_slide_mode_combobox.setItemText(2, translate('SongsPlugin.SongsTab', 'Same as Footer'))
        self.auto_play_check_box.setText(translate('SongsPlugin.SongsTab', 'Auto-play background audio'))
        self.uppercase_check_box.setText(translate('SongsPlugin.SongsTab', 'Apply UPPERCASE globally to all songs.'))
        self.chords_info_label.setText(translate('SongsPlugin.SongsTab', 'If enabled all text between "[" and "]" will '
                                                                         'be regarded as chords.'))
        self.chords_group_box.setTitle(translate('SongsPlugin.SongsTab', 'Chords'))
        self.disable_chords_import_check_box.setText(translate('SongsPlugin.SongsTab',
                                                               'Ignore chords when importing songs'))
        self.ccli_login_group_box.setTitle(translate('SongsPlugin.SongsTab', 'SongSelect Login'))
        self.ccli_username_label.setText(translate('SongsPlugin.SongsTab', 'Username:'))
        self.ccli_password_label.setText(translate('SongsPlugin.SongsTab', 'Password:'))
        self.chord_notation_label.setText(translate('SongsPlugin.SongsTab', 'Chord notation to use:'))
        self.english_notation_radio_button.setText(translate('SongsPlugin.SongsTab', 'English') + ' (C-D-E-F-G-A-B)')
        self.german_notation_radio_button.setText(translate('SongsPlugin.SongsTab', 'German') + ' (C-D-E-F-G-A-H)')
        self.neolatin_notation_radio_button.setText(
            translate('SongsPlugin.SongsTab', 'Neo-Latin') + ' (Do-Re-Mi-Fa-Sol-La-Si)')
        self.song_key_warning_check_box.setText(translate('SongsPlugin.SongsTab', 'Warn about missing song key'))
        self.footer_group_box.setTitle(translate('SongsPlugin.SongsTab', 'Footer'))
        # Preview first line feature
        self.preview_group_box.setTitle(translate('SongsPlugin.SongsTab', 'Preview'))
        self.preview_info_label.setText(translate('SongsPlugin.SongsTab',
                                                  'Enable previewing the first line of the next section.'))
        self.preview_intro_check_box.setText(translate('SongsPlugin.SongsTab', 'Intro'))
        self.preview_verse_check_box.setText(translate('SongsPlugin.SongsTab', 'Verse'))
        self.preview_chorus_check_box.setText(translate('SongsPlugin.SongsTab', 'Chorus'))
        self.preview_bridge_check_box.setText(translate('SongsPlugin.SongsTab', 'Bridge'))
        self.preview_pre_chorus_check_box.setText(translate('SongsPlugin.SongsTab', 'Pre-Chorus'))
        self.preview_ending_check_box.setText(translate('SongsPlugin.SongsTab', 'Ending'))
        self.preview_other_check_box.setText(translate('SongsPlugin.SongsTab', 'Other'))
        # Keep this in sync with the list in mediaitem.py
        const = '<code>"{}"</code>'
        placeholders = [
            # placeholder, description, can be empty, is a list
            ['title', translate('SongsPlugin.SongsTab', 'Song Title'), False, False],
            ['alternate_title', translate('SongsPlugin.SongsTab', 'Alternate Title'), True, False],
            ['written_by', const.format(translate('SongsPlugin.SongsTab', 'Written By')), True, False],
            ['authors_none', translate('SongsPlugin.SongsTab', 'Authors when type is not set'), False, True],
            ['authors_words_label', const.format(AuthorType.get_translated_type(AuthorType.Words)), False, False],
            ['authors_words', translate('SongsPlugin.SongsTab', 'Authors (Type "Words")'), False, True],
            ['authors_music_label', const.format(AuthorType.get_translated_type(AuthorType.Music)), False, False],
            ['authors_music', translate('SongsPlugin.SongsTab', 'Authors (Type "Music")'), False, True],
            ['authors_words_music_label', const.format(AuthorType.get_translated_type(AuthorType.WordsAndMusic)),
             False, False],
            ['authors_words_music', translate('SongsPlugin.SongsTab', 'Authors (Type "Words and Music")'), False, True],
            ['authors_translation_label', const.format(AuthorType.get_translated_type(AuthorType.Translation)),
             False, False],
            ['authors_translation', translate('SongsPlugin.SongsTab', 'Authors (Type "Translation")'), False, True],
            ['authors_words_all', translate('SongsPlugin.SongsTab', 'Authors (Type "Words" & "Words and Music")'),
             False, True],
            ['authors_music_all', translate('SongsPlugin.SongsTab', 'Authors (Type "Music" & "Words and Music")'),
             False, True],
            ['copyright', translate('SongsPlugin.SongsTab', 'Copyright information'), True, False],
            ['songbook_entries', translate('SongsPlugin.SongsTab', 'Songbook Entries'), False, True],
            ['ccli_license', translate('SongsPlugin.SongsTab', 'CCLI License'), True, False],
            ['ccli_license_label', const.format(translate('SongsPlugin.SongsTab', 'CCLI License')), False, False],
            ['ccli_number', translate('SongsPlugin.SongsTab', 'Song CCLI Number'), True, False],
            ['topics', translate('SongsPlugin.SongsTab', 'Topics'), False, True],
            ['first_slide', translate('SongsPlugin.SongsTab', 'Where rendering on first (cover) slide'), False, False],
        ]
        placeholder_info = '<table><tr><th><b>{ph}</b></th><th><b>{desc}</b></th></tr>'.format(
            ph=translate('SongsPlugin.SongsTab', 'Placeholder'), desc=translate('SongsPlugin.SongsTab', 'Description'))
        for placeholder in placeholders:
            placeholder_info += '<tr><td>${{{pl}}}</td><td>{des}{opt}</td></tr>'.format(
                pl=placeholder[0], des=placeholder[1], opt=('&nbsp;<sup>1</sup>' if placeholder[2] else '') +
                ('&nbsp;<sup>2</sup>' if placeholder[3] else ''))
        placeholder_info += '</table>'
        placeholder_info += '<p><sup>1</sup> {}<br/>'.format(translate('SongsPlugin.SongsTab', 'can be empty'))
        placeholder_info += '<sup>2</sup> {}</p>'.format(
            translate('SongsPlugin.SongsTab', 'list of entries, can be empty'))
        self.footer_placeholder_info.setHtml(placeholder_info)
        self.footer_placeholder_info.setReadOnly(True)

        self.footer_tabs.setTabText(1, translate('SongsPlugin.SongsTab', 'How to Use'))
        self.footer_tabs.setTabText(0, translate('SongsPlugin.SongsTab', 'Template'))
        self.footer_help_label.setText('<a href="http://docs.makotemplates.org">{}</a>'
                                       .format(translate('SongsPlugin.SongsTab', 'Mako Syntax')))
        self.footer_reset_button.setText(translate('SongsPlugin.SongsTab', 'Reset Template'))

    def on_search_as_type_check_box_changed(self, check_state):
        self.song_search = (check_state == QtCore.Qt.CheckState.Checked)

    def on_tool_bar_active_check_box_changed(self, check_state):
        self.tool_bar = (check_state == QtCore.Qt.CheckState.Checked)

    def on_update_on_edit_check_box_changed(self, check_state):
        self.update_edit = (check_state == QtCore.Qt.CheckState.Checked)

    def on_add_from_service_check_box_changed(self, check_state):
        self.update_load = (check_state == QtCore.Qt.CheckState.Checked)

    def on_first_slide_mode_combo_box_changed(self, index):
        self.first_slide_mode = SongFirstSlideMode(index)

    def on_auto_play_check_box_changed(self, check_state):
        self.auto_play = (check_state == QtCore.Qt.CheckState.Checked)

    def on_uppercase_check_box_changed(self, check_state):
        self.uppercase = (check_state == QtCore.Qt.CheckState.Checked)

    def on_disable_chords_import_check_box_changed(self, check_state):
        self.disable_chords_import = (check_state == QtCore.Qt.CheckState.Checked)

    def on_song_key_warning_check_box_changed(self, check_state):
        self.song_key_warning = (check_state == QtCore.Qt.CheckState.Checked)

    def on_english_notation_button_clicked(self):
        self.chord_notation = 'english'

    def on_german_notation_button_clicked(self):
        self.chord_notation = 'german'

    def on_neolatin_notation_button_clicked(self):
        self.chord_notation = 'neo-latin'

    def on_footer_reset_button_clicked(self):
        self.footer_edit_box.setPlainText(self.settings.get_default_value('songs/footer template'))

    def on_preview_group_box_toggled(self, checked):
        self.preview_enabled = checked

    def on_preview_intro_check_box_changed(self, check_state):
        self.preview_intro = (check_state == QtCore.Qt.CheckState.Checked)

    def on_preview_verse_check_box_changed(self, check_state):
        self.preview_verse = (check_state == QtCore.Qt.CheckState.Checked)

    def on_preview_chorus_check_box_changed(self, check_state):
        self.preview_chorus = (check_state == QtCore.Qt.CheckState.Checked)

    def on_preview_bridge_check_box_changed(self, check_state):
        self.preview_bridge = (check_state == QtCore.Qt.CheckState.Checked)

    def on_preview_pre_chorus_check_box_changed(self, check_state):
        self.preview_pre_chorus = (check_state == QtCore.Qt.CheckState.Checked)

    def on_preview_ending_check_box_changed(self, check_state):
        self.preview_ending = (check_state == QtCore.Qt.CheckState.Checked)

    def on_preview_other_check_box_changed(self, check_state):
        self.preview_other = (check_state == QtCore.Qt.CheckState.Checked)

    def load(self):
        """
        Load the songs settings
        """
        self.tool_bar = self.settings.value('songs/display songbar')
        self.update_edit = self.settings.value('songs/update service on edit')
        self.update_load = self.settings.value('songs/add song from service')
        self.first_slide_mode = self.settings.value('songs/first slide mode')
        self.auto_play = self.settings.value('songs/auto play audio')
        self.uppercase = self.settings.value('songs/uppercase songs')
        self.enable_chords = self.settings.value('songs/enable chords')
        self.chord_notation = self.settings.value('songs/chord notation')
        self.disable_chords_import = self.settings.value('songs/disable chords import')
        self.song_key_warning = self.settings.value('songs/warn about missing song key')
        self.tool_bar_active_check_box.setChecked(self.tool_bar)
        self.update_on_edit_check_box.setChecked(self.update_edit)
        self.add_from_service_check_box.setChecked(self.update_load)
        self.auto_play_check_box.setChecked(self.auto_play)
        self.uppercase_check_box.setChecked(self.uppercase)
        self.chords_group_box.setChecked(self.enable_chords)
        self.disable_chords_import_check_box.setChecked(self.disable_chords_import)
        self.song_key_warning_check_box.setChecked(self.song_key_warning)
        if self.chord_notation == 'german':
            self.german_notation_radio_button.setChecked(True)
        elif self.chord_notation == 'neo-latin':
            self.neolatin_notation_radio_button.setChecked(True)
        else:
            self.english_notation_radio_button.setChecked(True)
        self.ccli_username.setText(self.settings.value('songs/songselect username'))
        self.ccli_password.setText(self.settings.value('songs/songselect password'))
        self.footer_edit_box.setPlainText(self.settings.value('songs/footer template'))
        if self.first_slide_mode > 0:
            self.first_slide_mode_combobox.setCurrentIndex(self.first_slide_mode)

        # Preview group box (master enable/disable)
        self.preview_enabled = self.settings.value('songs/preview_enabled')
        self.preview_group_box.setChecked(self.preview_enabled)

        # Individual preview checkboxes
        self.preview_intro = self.settings.value('songs/preview_intro')
        self.preview_intro_check_box.setChecked(self.preview_intro)

        self.preview_verse = self.settings.value('songs/preview_verse')
        self.preview_verse_check_box.setChecked(self.preview_verse)

        self.preview_chorus = self.settings.value('songs/preview_chorus')
        self.preview_chorus_check_box.setChecked(self.preview_chorus)

        self.preview_bridge = self.settings.value('songs/preview_bridge')
        self.preview_bridge_check_box.setChecked(self.preview_bridge)

        self.preview_pre_chorus = self.settings.value('songs/preview_pre_chorus')
        self.preview_pre_chorus_check_box.setChecked(self.preview_pre_chorus)

        self.preview_ending = self.settings.value('songs/preview_ending')
        self.preview_ending_check_box.setChecked(self.preview_ending)

        self.preview_other = self.settings.value('songs/preview_other')
        self.preview_other_check_box.setChecked(self.preview_other)

    def save(self):
        """
        Save the song settings
        """
        self.settings.setValue('songs/display songbar', self.tool_bar)
        self.settings.setValue('songs/update service on edit', self.update_edit)
        self.settings.setValue('songs/add song from service', self.update_load)
        self.settings.setValue('songs/auto play audio', self.auto_play)
        self.settings.setValue('songs/uppercase songs', self.uppercase)
        self.settings.setValue('songs/enable chords', self.chords_group_box.isChecked())
        self.settings.setValue('songs/disable chords import', self.disable_chords_import)
        self.settings.setValue('songs/warn about missing song key', self.song_key_warning)
        self.settings.setValue('songs/chord notation', self.chord_notation)
        self.settings.setValue('songs/songselect username', self.ccli_username.text())

        # Preview group box (master enable/disable)
        self.settings.setValue('songs/preview_enabled', self.preview_group_box.isChecked())

        # Individual preview checkboxes
        self.settings.setValue('songs/preview_intro', self.preview_intro)
        self.settings.setValue('songs/preview_verse', self.preview_verse)
        self.settings.setValue('songs/preview_chorus', self.preview_chorus)
        self.settings.setValue('songs/preview_bridge', self.preview_bridge)
        self.settings.setValue('songs/preview_pre_chorus', self.preview_pre_chorus)
        self.settings.setValue('songs/preview_ending', self.preview_ending)
        self.settings.setValue('songs/preview_other', self.preview_other)

        # Only save password if it's blank or the user acknowleges the warning
        if (self.ccli_password.text() == ''):
            self.settings.setValue('songs/songselect password', '')
        elif (self.ccli_password.text() != self.settings.value('songs/songselect password')):
            answer = QtWidgets.QMessageBox.question(
                self, translate('SongsPlugin.SongsTab', 'Save Username and Password'),
                translate('SongsPlugin.SongsTab', 'WARNING: Saving your SongSelect password is INSECURE, '
                                                  'your password is stored in PLAIN TEXT. Click Yes to save '
                                                  'your password or No to cancel this.'),
                defaultButton=QtWidgets.QMessageBox.StandardButton.No)
            if answer == QtWidgets.QMessageBox.StandardButton.Yes:
                self.settings.setValue('songs/songselect password', self.ccli_password.text())
        # Only save footer template if it has been changed. This allows future updates
        if self.footer_edit_box.toPlainText() != self.settings.value('songs/footer template'):
            self.settings.setValue('songs/footer template', self.footer_edit_box.toPlainText())
        self.settings.setValue('songs/first slide mode', self.first_slide_mode)
        if self.tab_visited:
            self.settings_form.register_post_process('songs_config_updated')
        self.tab_visited = False
