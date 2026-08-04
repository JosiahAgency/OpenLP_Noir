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
The duplicate song removal logic for OpenLP.
"""

from collections import defaultdict
from datetime import datetime
from functools import partial
import logging
import multiprocessing
from pathlib import Path
import shutil

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.mixins import RegistryProperties
from openlp.core.common.path import create_paths
from openlp.core.common.registry import Registry
from openlp.core.lib.ui import critical_error_message_box
from openlp.core.widgets.wizard import OpenLPWizard, WizardStrings
from openlp.plugins.songs.lib import clean_string, delete_song
from openlp.plugins.songs.lib.db import Song
from openlp.plugins.songs.lib.openlyricsxml import SongXML
from openlp.plugins.songs.lib.songcompare import songs_probably_equal


log = logging.getLogger(__name__)


def _blend_colors(base_color, accent_color, ratio):
    """
    Blend two colors (0.0 -> base, 1.0 -> accent).
    """
    ratio = max(0.0, min(1.0, float(ratio)))
    red = int(base_color.red() + (accent_color.red() - base_color.red()) * ratio)
    green = int(base_color.green() + (accent_color.green() - base_color.green()) * ratio)
    blue = int(base_color.blue() + (accent_color.blue() - base_color.blue()) * ratio)
    return QtGui.QColor(red, green, blue)


def build_preview_pane_style(is_keep, palette):
    """
    Build a palette-aware, high-contrast stylesheet for preview panes.
    """
    base_color = palette.base().color()
    text_color = palette.text().color()
    accent = QtGui.QColor(46, 125, 50) if is_keep else QtGui.QColor(198, 40, 40)
    background = _blend_colors(base_color, accent, 0.16)
    border = _blend_colors(accent, QtGui.QColor(255, 255, 255), 0.15)
    return (
        f'QPlainTextEdit {{'
        f'background-color: {background.name()}; '
        f'color: {text_color.name()}; '
        f'border: 1px solid {border.name()};'
        f'}}'
    )


def _song_last_modified(song):
    """
    Return song.last_modified if set, else datetime.min.
    """
    return song.last_modified if song.last_modified else datetime.min


def select_keeper_song(duplicate_group):
    """
    Select the most recently modified song as keeper.

    :param duplicate_group: List of Song objects
    :return: Song to keep
    """
    return max(duplicate_group, key=lambda song: (_song_last_modified(song), song.id or 0))


def _song_block_keys(song):
    """
    Build candidate bucket keys for a song to narrow duplicate comparisons.
    """
    keys = set()
    for value in [song.title, song.alternate_title]:
        normalized = clean_string(value or '').strip()
        if len(normalized) >= 4:
            keys.add(f'title:{normalized}')
    for value in (song.search_title or '').split('@'):
        normalized = clean_string(value or '').strip()
        if len(normalized) >= 4:
            keys.add(f'search-title:{normalized}')
    lyrics = song.search_lyrics or ''
    if len(lyrics) >= 40:
        keys.add(f'lyrics-prefix:{lyrics[:40]}')
    return keys


def generate_candidate_index_pairs(songs):
    """
    Generate likely duplicate song index pairs using bucket-based candidate blocking.

    :param songs: List of Song objects
    :return: Set of tuple(index1, index2)
    """
    buckets = defaultdict(set)
    for index, song in enumerate(songs):
        for key in _song_block_keys(song):
            buckets[key].add(index)
    candidate_pairs = set()
    for indices in buckets.values():
        if len(indices) < 2:
            continue
        sorted_indices = sorted(indices)
        for left_pos in range(len(sorted_indices) - 1):
            for right_pos in range(left_pos + 1, len(sorted_indices)):
                candidate_pairs.add((sorted_indices[left_pos], sorted_indices[right_pos]))
    return candidate_pairs


def song_payload_generator(songs, candidate_pairs):
    """
    Generator yielding pair payloads expected by songs_probably_equal().
    """
    for index1, index2 in candidate_pairs:
        yield ((index1, songs[index1].search_lyrics), (index2, songs[index2].search_lyrics))


def build_duplicate_song_groups(songs, matched_pairs):
    """
    Build duplicate groups as connected components from matched index pairs.

    :param songs: List of Song objects
    :param matched_pairs: Iterable of tuple(index1, index2)
    :return: List[List[Song]]
    """
    adjacency = defaultdict(set)
    for index1, index2 in matched_pairs:
        adjacency[index1].add(index2)
        adjacency[index2].add(index1)
    groups = []
    visited = set()
    for start in sorted(adjacency.keys()):
        if start in visited:
            continue
        stack = [start]
        component = set()
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            component.add(node)
            stack.extend(adjacency[node] - visited)
        if len(component) >= 2:
            group = [songs[index] for index in component]
            group.sort(key=lambda song: (_song_last_modified(song), song.id or 0), reverse=True)
            groups.append(group)
    groups.sort(key=lambda group: len(group), reverse=True)
    return groups


def build_song_preview_text(song):
    """
    Build a human-readable preview for side-by-side duplicate comparison.
    """
    song_xml = SongXML()
    verses = song_xml.get_verses(song.lyrics or '')
    preview_lines = [
        f'Title: {song.title or ""}',
        f'Alternate Title: {song.alternate_title or ""}',
        f'Authors: {", ".join(author.display_name for author in song.authors)}',
        f'Last Modified: {_song_last_modified(song).strftime("%Y-%m-%d %H:%M:%S")}',
        '',
        'Lyrics:',
    ]
    for verse in verses:
        tag = f'{verse[0].get("type", "")}{verse[0].get("label", "")}'.strip()
        preview_lines.append(f'[{tag}]')
        preview_lines.append(verse[1] or '')
        preview_lines.append('')
    return '\n'.join(preview_lines).strip()


class DuplicateSongRemovalForm(OpenLPWizard, RegistryProperties):
    """
    This is the Duplicate Song Removal Wizard. It provides functionality to search for and remove duplicate songs
    in the database.
    """
    log.info('DuplicateSongRemovalForm loaded')

    def __init__(self, plugin):
        """
        Instantiate the wizard, and run any extra setup we need to.

        :param plugin: The songs plugin.
        """
        self.duplicate_song_groups = []
        self.review_total_count = 0
        self.break_search = False
        self._review_rows_by_group = defaultdict(list)
        self._review_row_song = {}
        self._review_row_delete_check = {}
        self._review_keep_button_groups = {}
        self._delete_executed = False
        log.info('Initializing DuplicateSongRemovalForm')
        super(DuplicateSongRemovalForm, self).__init__(
            Registry().get('main_window'), plugin, 'duplicateSongRemovalWizard',
            ':/wizards/wizard_duplicateremoval.bmp', False)
        # OpenLPWizard enforces a fixed width of 640. Override it here for this richer review UI.
        self.setMinimumSize(1220, 800)
        # Use Qt's max widget size value directly (QWIDGETSIZE_MAX is not exposed in PySide6).
        self.setMaximumSize(16777215, 16777215)
        self.resize(1320, 860)
        log.debug('DuplicateSongRemovalForm sized to %sx%s (min: %sx%s)',
                  self.width(), self.height(), self.minimumWidth(), self.minimumHeight())

    def custom_signals(self):
        """
        Song wizard specific signals.
        """
        self.finish_button.clicked.connect(self.on_wizard_exit)
        self.cancel_button.clicked.connect(self.on_wizard_exit)
        self.apply_recommended_button.clicked.connect(self.apply_recommended_selection)
        self.select_all_for_deletion_button.clicked.connect(self.select_all_for_deletion)
        self.clear_deletions_button.clicked.connect(self.clear_deletions)
        self.review_table.cellClicked.connect(self.on_review_row_clicked)
        self.review_table.currentCellChanged.connect(self.on_current_cell_changed)

    def closeEvent(self, event):
        self.on_wizard_exit()
        super().closeEvent(event)

    def add_custom_pages(self):
        """
        Add song wizard specific pages.
        """
        self.searching_page = QtWidgets.QWizardPage()
        self.searching_page.setObjectName('searching_page')
        self.searching_vertical_layout = QtWidgets.QVBoxLayout(self.searching_page)
        self.searching_vertical_layout.setObjectName('searching_vertical_layout')
        self.duplicate_search_progress_bar = QtWidgets.QProgressBar(self.searching_page)
        self.duplicate_search_progress_bar.setObjectName('duplicate_search_progress_bar')
        self.duplicate_search_progress_bar.setFormat(WizardStrings.PercentSymbolFormat)
        self.searching_vertical_layout.addWidget(self.duplicate_search_progress_bar)
        self.found_duplicates_edit = QtWidgets.QPlainTextEdit(self.searching_page)
        self.found_duplicates_edit.setUndoRedoEnabled(False)
        self.found_duplicates_edit.setReadOnly(True)
        self.found_duplicates_edit.setObjectName('found_duplicates_edit')
        self.searching_vertical_layout.addWidget(self.found_duplicates_edit)
        self.searching_page_id = self.addPage(self.searching_page)

        self.review_page = QtWidgets.QWizardPage()
        self.review_page.setObjectName('review_page')
        self.review_layout = QtWidgets.QVBoxLayout(self.review_page)
        self.review_layout.setObjectName('review_layout')
        self.review_tools_layout = QtWidgets.QHBoxLayout()
        self.review_tools_layout.setObjectName('review_tools_layout')
        self.apply_recommended_button = QtWidgets.QPushButton(self.review_page)
        self.apply_recommended_button.setObjectName('apply_recommended_button')
        self.select_all_for_deletion_button = QtWidgets.QPushButton(self.review_page)
        self.select_all_for_deletion_button.setObjectName('select_all_for_deletion_button')
        self.clear_deletions_button = QtWidgets.QPushButton(self.review_page)
        self.clear_deletions_button.setObjectName('clear_deletions_button')
        self.review_tools_layout.addWidget(self.apply_recommended_button)
        self.review_tools_layout.addWidget(self.select_all_for_deletion_button)
        self.review_tools_layout.addWidget(self.clear_deletions_button)
        self.review_tools_layout.addStretch()
        self.review_layout.addLayout(self.review_tools_layout)
        self.comparison_hint_label = QtWidgets.QLabel(self.review_page)
        self.comparison_hint_label.setObjectName('comparison_hint_label')
        self.comparison_hint_label.setWordWrap(True)
        self.review_layout.addWidget(self.comparison_hint_label)
        self.review_table = QtWidgets.QTableWidget(self.review_page)
        self.review_table.setObjectName('review_table')
        self.review_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.review_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.review_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.review_table.setAlternatingRowColors(True)
        self.review_table.setColumnCount(8)
        self.review_table.setHorizontalHeaderLabels([
            translate('Wizard', 'Group'),
            translate('Wizard', 'Keep'),
            translate('Wizard', 'Delete'),
            translate('Wizard', 'Title'),
            translate('Wizard', 'Alternate Title'),
            translate('Wizard', 'Authors'),
            translate('Wizard', 'Last Modified'),
            translate('Wizard', 'ID')
        ])
        header = self.review_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.review_layout.addWidget(self.review_table)
        self.comparison_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, self.review_page)
        self.comparison_splitter.setObjectName('comparison_splitter')
        self.comparison_splitter.setChildrenCollapsible(False)
        self.keep_preview_group_box = QtWidgets.QGroupBox(self.comparison_splitter)
        self.keep_preview_group_box.setObjectName('keep_preview_group_box')
        self.keep_preview_layout = QtWidgets.QVBoxLayout(self.keep_preview_group_box)
        self.keep_preview_layout.setObjectName('keep_preview_layout')
        self.keep_preview_text = QtWidgets.QPlainTextEdit(self.keep_preview_group_box)
        self.keep_preview_text.setReadOnly(True)
        self.keep_preview_text.setObjectName('keep_preview_text')
        self.keep_preview_layout.addWidget(self.keep_preview_text)
        self.delete_preview_group_box = QtWidgets.QGroupBox(self.comparison_splitter)
        self.delete_preview_group_box.setObjectName('delete_preview_group_box')
        self.delete_preview_layout = QtWidgets.QVBoxLayout(self.delete_preview_group_box)
        self.delete_preview_layout.setObjectName('delete_preview_layout')
        self.delete_preview_text = QtWidgets.QPlainTextEdit(self.delete_preview_group_box)
        self.delete_preview_text.setReadOnly(True)
        self.delete_preview_text.setObjectName('delete_preview_text')
        self.delete_preview_layout.addWidget(self.delete_preview_text)
        self.keep_preview_group_box.setMinimumWidth(420)
        self.delete_preview_group_box.setMinimumWidth(420)
        self.keep_preview_text.setMinimumHeight(230)
        self.delete_preview_text.setMinimumHeight(230)
        self.comparison_splitter.setStretchFactor(0, 1)
        self.comparison_splitter.setStretchFactor(1, 1)
        self.review_layout.addWidget(self.comparison_splitter)
        self.review_layout.setStretch(2, 4)
        self.review_layout.setStretch(3, 3)
        self.review_page_id = self.addPage(self.review_page)
        self.review_page.setFinalPage(True)
        self.apply_theme_aware_preview_styles()
        log.debug('DuplicateSongRemovalForm pages created')

    def retranslate_ui(self):
        """
        Song wizard localisation.
        """
        self.setWindowTitle(translate('Wizard', 'Wizard'))
        self.title_label.setText(
            WizardStrings.HeaderStyle.format(text=translate('OpenLP.Ui',
                                                            'Welcome to the Duplicate Song Removal Wizard')))
        self.information_label.setText(
            translate("Wizard",
                      'This wizard scans for duplicate songs and prepares bulk removal. The newest song in each group '
                      'is preselected to keep. You can override selections before deleting marked duplicates.'))
        self.searching_page.setTitle(translate('Wizard', 'Searching for duplicate songs.'))
        self.searching_page.setSubTitle(translate('Wizard', 'Please wait while your songs database is analyzed.'))
        self.update_review_counter_text()
        self.review_page.setSubTitle(translate('Wizard',
                                               'Review all duplicate groups at once and bulk-remove marked songs.'))
        self.apply_recommended_button.setText(translate('Wizard', 'Apply Recommended Selection'))
        self.select_all_for_deletion_button.setText(translate('Wizard', 'Select All for Deletion'))
        self.clear_deletions_button.setText(translate('Wizard', 'Clear Deletions'))
        self.comparison_hint_label.setText(translate(
            'Wizard',
            'Select a song row to compare versions. Keep version is shown in green, delete candidate in red.'))
        self.keep_preview_group_box.setTitle(translate('Wizard', 'Keep (green)'))
        self.delete_preview_group_box.setTitle(translate('Wizard', 'Delete (red)'))

    def update_review_counter_text(self):
        """
        Set the wizard review page header text.
        """
        self.review_page.setTitle(
            translate('Wizard', 'Review duplicate songs ({total} groups)').format(total=self.review_total_count))

    def custom_page_changed(self, page_id):
        """
        Called when changing the wizard page.

        :param page_id: ID of the page the wizard changed to.
        """
        self.button(QtWidgets.QWizard.WizardButton.BackButton).hide()
        if page_id == self.searching_page_id:
            self.application.set_busy_cursor()
            try:
                self.button(QtWidgets.QWizard.WizardButton.NextButton).hide()
                self.scan_for_duplicates()
            finally:
                self.application.set_normal_cursor()
        elif page_id == self.review_page_id:
            self.populate_review_table()
            self.button(QtWidgets.QWizard.WizardButton.FinishButton).show()
            self.button(QtWidgets.QWizard.WizardButton.FinishButton).setEnabled(True)
            self.button(QtWidgets.QWizard.WizardButton.NextButton).hide()
            self.button(QtWidgets.QWizard.WizardButton.CancelButton).show()

    def scan_for_duplicates(self):
        """
        Scan songs and build duplicate groups.
        """
        log.info('Starting duplicate song scan')
        max_songs = self.plugin.manager.get_object_count(Song)
        if max_songs <= 1:
            self.duplicate_search_progress_bar.setMaximum(1)
            self.duplicate_search_progress_bar.setValue(1)
            self.notify_no_duplicates()
            return
        songs = self.plugin.manager.get_all_objects(Song)
        candidate_pairs = sorted(generate_candidate_index_pairs(songs))
        if not candidate_pairs:
            self.duplicate_search_progress_bar.setMaximum(1)
            self.duplicate_search_progress_bar.setValue(1)
            self.notify_no_duplicates()
            return
        self.duplicate_search_progress_bar.setMaximum(len(candidate_pairs))
        process_number = max(1, multiprocessing.cpu_count() - 1)
        pool = multiprocessing.Pool(process_number)
        result = pool.imap_unordered(songs_probably_equal, song_payload_generator(songs, candidate_pairs), 30)
        pool.close()
        matched_pairs = []
        for match_tuple in result:
            self.duplicate_search_progress_bar.setValue(self.duplicate_search_progress_bar.value() + 1)
            self.application.process_events()
            if self.break_search:
                pool.terminate()
                return
            if not match_tuple:
                continue
            matched_pairs.append(match_tuple)
            song1 = songs[match_tuple[0]]
            song2 = songs[match_tuple[1]]
            self.found_duplicates_edit.appendPlainText(song1.title + '  =  ' + song2.title)
        self.duplicate_song_groups = build_duplicate_song_groups(songs, matched_pairs)
        self.review_total_count = len(self.duplicate_song_groups)
        log.info('Duplicate song scan completed: %s song(s), %s candidate pair(s), %s duplicate group(s)',
                 max_songs, len(candidate_pairs), self.review_total_count)
        if self.duplicate_song_groups:
            self.button(QtWidgets.QWizard.WizardButton.NextButton).show()
        else:
            self.notify_no_duplicates()

    def notify_no_duplicates(self):
        """
        Notifies the user, that there were no duplicates found in the database.
        """
        self.button(QtWidgets.QWizard.WizardButton.FinishButton).show()
        self.button(QtWidgets.QWizard.WizardButton.FinishButton).setEnabled(True)
        self.button(QtWidgets.QWizard.WizardButton.NextButton).hide()
        self.button(QtWidgets.QWizard.WizardButton.CancelButton).hide()
        QtWidgets.QMessageBox.information(
            self, translate('Wizard', 'Information'),
            translate('Wizard', 'No duplicate songs have been found in the database.'))

    def populate_review_table(self):
        """
        Populate the review table with all duplicate groups and preselected keeper rows.
        """
        self._review_rows_by_group = defaultdict(list)
        self._review_row_song = {}
        self._review_row_delete_check = {}
        self._review_keep_button_groups = {}
        self.update_review_counter_text()
        total_rows = sum(len(group) for group in self.duplicate_song_groups)
        self.review_table.setRowCount(total_rows)
        row = 0
        for group_index, duplicate_group in enumerate(self.duplicate_song_groups, start=1):
            keeper_song = select_keeper_song(duplicate_group)
            keep_group = QtWidgets.QButtonGroup(self.review_table)
            keep_group.setExclusive(True)
            self._review_keep_button_groups[group_index] = keep_group
            for song in duplicate_group:
                self._review_rows_by_group[group_index].append(row)
                self._review_row_song[row] = song

                group_item = QtWidgets.QTableWidgetItem(str(group_index))
                id_item = QtWidgets.QTableWidgetItem(str(song.id))
                title_item = QtWidgets.QTableWidgetItem(song.title or '')
                alt_title_item = QtWidgets.QTableWidgetItem(song.alternate_title or '')
                authors_item = QtWidgets.QTableWidgetItem(', '.join(author.display_name for author in song.authors))
                modified_item = QtWidgets.QTableWidgetItem(_song_last_modified(song).strftime("%Y-%m-%d %H:%M:%S"))
                self.review_table.setItem(row, 0, group_item)
                self.review_table.setItem(row, 3, title_item)
                self.review_table.setItem(row, 4, alt_title_item)
                self.review_table.setItem(row, 5, authors_item)
                self.review_table.setItem(row, 6, modified_item)
                self.review_table.setItem(row, 7, id_item)

                keep_radio = QtWidgets.QRadioButton(self.review_table)
                keep_group.addButton(keep_radio)
                self.review_table.setCellWidget(row, 1, keep_radio)
                keep_radio.toggled.connect(partial(self.on_keep_radio_toggled, group_index, row))

                delete_checkbox = QtWidgets.QCheckBox(self.review_table)
                delete_checkbox.setChecked(song is not keeper_song)
                delete_checkbox.setEnabled(song is not keeper_song)
                self._review_row_delete_check[row] = delete_checkbox
                self.review_table.setCellWidget(row, 2, delete_checkbox)

                if song is keeper_song:
                    keep_radio.setChecked(True)
                row += 1
        self.review_table.resizeColumnsToContents()
        if total_rows > 0:
            self.review_table.selectRow(0)
            self.on_review_row_clicked(0, 0)
            self.comparison_splitter.setSizes([self.comparison_splitter.width() // 2,
                                               self.comparison_splitter.width() // 2])

    def on_keep_radio_toggled(self, group_index, keeper_row, checked):
        """
        Sync delete checkboxes with selected keeper.
        """
        if not checked:
            return
        for row in self._review_rows_by_group[group_index]:
            delete_checkbox = self._review_row_delete_check[row]
            was_enabled = delete_checkbox.isEnabled()
            delete_checkbox.blockSignals(True)
            if row == keeper_row:
                delete_checkbox.setChecked(False)
                delete_checkbox.setEnabled(False)
            else:
                delete_checkbox.setEnabled(True)
                if not was_enabled:
                    delete_checkbox.setChecked(True)
            delete_checkbox.blockSignals(False)
        current_row = self.review_table.currentRow()
        if current_row in self._review_rows_by_group[group_index]:
            self.on_review_row_clicked(current_row, 0)

    def apply_recommended_selection(self):
        """
        Reapply keeper-by-last-modified default selection.
        """
        for group_index, duplicate_group in enumerate(self.duplicate_song_groups, start=1):
            keeper_song = select_keeper_song(duplicate_group)
            for row in self._review_rows_by_group[group_index]:
                if self._review_row_song[row] is keeper_song:
                    keep_radio = self.review_table.cellWidget(row, 1)
                    keep_radio.setChecked(True)
                    break

    def select_all_for_deletion(self):
        """
        Mark all non-keeper songs for deletion.
        """
        for delete_checkbox in self._review_row_delete_check.values():
            if delete_checkbox.isEnabled():
                delete_checkbox.setChecked(True)

    def clear_deletions(self):
        """
        Unmark all deletions.
        """
        for delete_checkbox in self._review_row_delete_check.values():
            if delete_checkbox.isEnabled():
                delete_checkbox.setChecked(False)

    def on_current_cell_changed(self, current_row, _current_column, _previous_row, _previous_column):
        """
        Keep keyboard navigation and mouse behavior in sync for comparison previews.
        """
        if current_row >= 0:
            self.on_review_row_clicked(current_row, 0)

    def on_review_row_clicked(self, row, _column):
        """
        Show side-by-side comparison for selected row's duplicate group.
        """
        group_item = self.review_table.item(row, 0)
        if group_item is None:
            return
        group_index = int(group_item.text())
        keeper_row = self._current_keeper_row(group_index)
        if keeper_row is None:
            return
        delete_row = row
        if delete_row == keeper_row:
            delete_row = self._first_non_keeper_row(group_index)
            if delete_row is None:
                self.keep_preview_text.clear()
                self.delete_preview_text.clear()
                return
        keep_song = self._review_row_song[keeper_row]
        delete_song_obj = self._review_row_song[delete_row]
        log.debug('Review selection changed: group=%s keeper_song_id=%s delete_song_id=%s',
                  group_index, keep_song.id, delete_song_obj.id)
        self.keep_preview_text.setPlainText(build_song_preview_text(keep_song))
        self.delete_preview_text.setPlainText(build_song_preview_text(delete_song_obj))

    def _current_keeper_row(self, group_index):
        """
        Return currently selected keeper row for a group.
        """
        for row in self._review_rows_by_group[group_index]:
            keep_radio = self.review_table.cellWidget(row, 1)
            if keep_radio.isChecked():
                return row
        return None

    def _first_non_keeper_row(self, group_index):
        """
        Return first non-keeper row in group.
        """
        keeper_row = self._current_keeper_row(group_index)
        for row in self._review_rows_by_group[group_index]:
            if row != keeper_row:
                return row
        return None

    def apply_theme_aware_preview_styles(self):
        """
        Apply readable palette-aware colors for keep/delete preview panes.
        """
        palette = self.palette()
        keep_style = build_preview_pane_style(True, palette)
        delete_style = build_preview_pane_style(False, palette)
        self.keep_preview_text.setStyleSheet(keep_style)
        self.delete_preview_text.setStyleSheet(delete_style)
        log.debug('Applied theme-aware preview styles')

    def songs_marked_for_deletion(self):
        """
        Return songs selected for deletion.
        """
        songs_to_delete = []
        for row, song in self._review_row_song.items():
            delete_checkbox = self._review_row_delete_check[row]
            if delete_checkbox.isEnabled() and delete_checkbox.isChecked():
                songs_to_delete.append(song)
        return songs_to_delete

    def create_restore_point(self):
        """
        Create a restore point copy of the songs database before bulk delete.
        """
        database_path = self.plugin.manager.session.get_bind().url.database
        if not database_path:
            raise OSError('No songs database path available')
        source_path = Path(database_path)
        if not source_path.exists():
            raise OSError(f'Songs database not found: {source_path}')
        backup_dir = source_path.parent / 'backups'
        create_paths(backup_dir)
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_path = backup_dir / f'songs-before-deduplicate-{timestamp}.sqlite'
        shutil.copy2(source_path, backup_path)
        return backup_path

    def execute_bulk_delete(self):
        """
        Delete all songs currently marked for deletion.
        """
        songs_to_delete = self.songs_marked_for_deletion()
        if not songs_to_delete:
            QtWidgets.QMessageBox.information(
                self, translate('Wizard', 'No songs selected'),
                translate('Wizard', 'No duplicate songs are currently marked for deletion.'))
            return True
        answer = QtWidgets.QMessageBox.question(
            self,
            translate('Wizard', 'Confirm duplicate removal'),
            translate('Wizard',
                      'Delete {count} songs marked as duplicates?\n\n'
                      'OpenLP will create a restore-point backup before deleting.').format(count=len(songs_to_delete)),
            defaultButton=QtWidgets.QMessageBox.StandardButton.No
        )
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return False
        try:
            backup_path = self.create_restore_point()
        except OSError:
            log.exception('Failed to create songs database restore point')
            critical_error_message_box(
                translate('Wizard', 'Backup failed'),
                translate('Wizard', 'OpenLP could not create a restore point for the songs database. '
                                    'Duplicate removal has been cancelled.'))
            return False
        progress_dialog = QtWidgets.QProgressDialog(
            translate('Wizard', 'Removing duplicate songs...'),
            UiStrings().Cancel,
            0,
            len(songs_to_delete),
            self
        )
        progress_dialog.setWindowTitle(translate('Wizard', 'Removing duplicates'))
        progress_dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        deleted_count = 0
        for index, song in enumerate(songs_to_delete, start=1):
            if progress_dialog.wasCanceled():
                break
            delete_song(song.id, trigger_event=False)
            deleted_count += 1
            progress_dialog.setValue(index)
            self.application.process_events()
        progress_dialog.setValue(len(songs_to_delete))
        self.plugin.media_item.on_search_text_button_clicked()
        QtWidgets.QMessageBox.information(
            self,
            translate('Wizard', 'Duplicate removal complete'),
            translate('Wizard',
                      'Deleted {deleted} song(s).\nBackup created at:\n{backup}').format(
                          deleted=deleted_count, backup=backup_path))
        self._delete_executed = True
        return True

    def on_wizard_exit(self):
        """
        Once the wizard is finished, refresh the song list,
        since we potentially removed songs from it.
        """
        self.break_search = True
        self.plugin.media_item.on_search_text_button_clicked()

    def set_defaults(self):
        """
        Set default form values for the wizard.
        """
        self.restart()
        self.break_search = False
        self.duplicate_song_groups = []
        self.review_total_count = 0
        self._delete_executed = False
        self.duplicate_search_progress_bar.setValue(0)
        self.found_duplicates_edit.clear()
        self.review_table.clearContents()
        self.review_table.setRowCount(0)
        self.keep_preview_text.clear()
        self.delete_preview_text.clear()

    def accept(self):
        """
        On finish from review page, execute bulk delete before closing.
        """
        if self.currentId() == self.review_page_id and not self._delete_executed:
            if not self.execute_bulk_delete():
                return
        super().accept()
