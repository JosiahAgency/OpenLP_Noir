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
The :mod:`~openlp.core.ui.logviewer` module contains the Logs panel, a dockable
viewer that tails the application log file (openlp.log) inside the main window.
"""
import logging
import re
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.ui.icons import UiIcons
from openlp.core.ui.style import NOIR_ON_AIR, NOIR_TEXT_LOW, NOIR_WARNING
from openlp.core.widgets.toolbar import OpenLPToolbar


log = logging.getLogger(__name__)

# A log record starts with an asctime timestamp such as "2026-07-16 09:30:12,345".
# Lines that do not (e.g. traceback lines) continue the previous record.
RECORD_START = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
RECORD_LEVEL = re.compile(r' (DEBUG|INFO|WARNING|ERROR|CRITICAL) ')

LEVEL_COLOURS = {
    logging.DEBUG: NOIR_TEXT_LOW,
    logging.WARNING: NOIR_WARNING,
    logging.ERROR: NOIR_ON_AIR,
    logging.CRITICAL: NOIR_ON_AIR,
}


def find_log_file_path():
    """
    Locate the log file OpenLP is writing to by asking the root logger, so the
    correct file is found in both normal and portable mode.

    :return: The path of the log file, or None if no file handler is installed.
    """
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.FileHandler):
            return Path(handler.baseFilename)
    return None


class LogViewerPanel(QtWidgets.QWidget):
    """
    A dockable panel which tails the application log file and displays it with
    per-level colouring, level/text filtering and follow (auto-scroll) support.
    """
    MAX_LINES = 5000
    POLL_INTERVAL = 1000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('log_viewer_panel')
        self.log_file_path = find_log_file_path()
        # Each entry is (level, line). Continuation lines inherit the level of
        # the record they belong to.
        self.log_lines = []
        self._read_position = 0
        self._partial_line = ''
        self._current_level = logging.INFO
        self.setup_ui()
        self.poll_timer = QtCore.QTimer(self)
        self.poll_timer.setInterval(self.POLL_INTERVAL)
        self.poll_timer.timeout.connect(self.poll_log_file)

    def setup_ui(self):
        """
        Set up the toolbar and the log display.
        """
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.toolbar = OpenLPToolbar(self)
        self.level_selector = QtWidgets.QComboBox(self.toolbar)
        self.level_selector.setObjectName('log_level_selector')
        for title, level in ((translate('OpenLP.LogViewer', 'Debug'), logging.DEBUG),
                             (translate('OpenLP.LogViewer', 'Information'), logging.INFO),
                             (translate('OpenLP.LogViewer', 'Warning'), logging.WARNING),
                             (translate('OpenLP.LogViewer', 'Error'), logging.ERROR)):
            self.level_selector.addItem(title, level)
        self.level_selector.currentIndexChanged.connect(self.on_filter_changed)
        self.toolbar.add_toolbar_widget(self.level_selector)
        self.search_edit = QtWidgets.QLineEdit(self.toolbar)
        self.search_edit.setObjectName('log_search_edit')
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setPlaceholderText(translate('OpenLP.LogViewer', 'Filter log messages...'))
        self.search_edit.textChanged.connect(self.on_filter_changed)
        self.toolbar.add_toolbar_widget(self.search_edit)
        self.follow_action = self.toolbar.add_toolbar_action(
            'log_follow_action', icon=UiIcons().move_end, checked=True,
            text=translate('OpenLP.LogViewer', 'Follow'),
            tooltip=translate('OpenLP.LogViewer', 'Scroll to new log messages automatically.'),
            triggers=self.on_follow_toggled)
        self.copy_action = self.toolbar.add_toolbar_action(
            'log_copy_action', icon=UiIcons().copy,
            text=translate('OpenLP.LogViewer', 'Copy'),
            tooltip=translate('OpenLP.LogViewer', 'Copy the displayed log messages to the clipboard.'),
            triggers=self.on_copy_clicked)
        self.open_folder_action = self.toolbar.add_toolbar_action(
            'log_open_folder_action', icon=UiIcons().open,
            text=translate('OpenLP.LogViewer', 'Open log folder'),
            tooltip=translate('OpenLP.LogViewer', 'Open the folder containing the log file.'),
            triggers=self.on_open_folder_clicked)
        self.log_display = QtWidgets.QPlainTextEdit(self)
        self.log_display.setObjectName('log_display')
        self.log_display.setReadOnly(True)
        self.log_display.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.log_display.setMaximumBlockCount(self.MAX_LINES)
        display_font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        display_font.setPointSizeF(self.font().pointSizeF() * 0.9)
        self.log_display.setFont(display_font)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.log_display, 1)

    def showEvent(self, event):
        """
        Catch up with the log file and start tailing it while the panel is visible.
        """
        super().showEvent(event)
        self.poll_log_file()
        self.poll_timer.start()

    def hideEvent(self, event):
        """
        Stop polling the log file while the panel is hidden.
        """
        super().hideEvent(event)
        self.poll_timer.stop()

    def poll_log_file(self):
        """
        Read any new content from the log file and add it to the display.
        """
        if not self.log_file_path:
            self.log_file_path = find_log_file_path()
            if not self.log_file_path:
                return
        try:
            file_size = self.log_file_path.stat().st_size
            if file_size < self._read_position:
                # The log file was replaced (e.g. a new session), start over
                self._reset()
            if file_size == self._read_position:
                return
            with self.log_file_path.open('r', encoding='utf-8', errors='replace') as log_file:
                log_file.seek(self._read_position)
                new_content = log_file.read()
                self._read_position = log_file.tell()
        except OSError:
            return
        self._ingest(new_content)

    def _reset(self):
        """
        Forget everything read so far and clear the display.
        """
        self._read_position = 0
        self._partial_line = ''
        self._current_level = logging.INFO
        self.log_lines = []
        self.log_display.clear()

    def _ingest(self, content):
        """
        Split new file content into lines, track each line's log level and
        append the lines that pass the current filter to the display.

        :param content: New text read from the log file.
        """
        content = self._partial_line + content
        lines = content.split('\n')
        # The file may have been read mid-line; keep the incomplete tail for
        # the next poll.
        self._partial_line = lines.pop()
        for line in lines:
            if RECORD_START.match(line):
                match = RECORD_LEVEL.search(line)
                if match:
                    self._current_level = logging.getLevelName(match.group(1))
            entry = (self._current_level, line)
            self.log_lines.append(entry)
            if self._passes_filter(entry):
                self._append_line(entry)
        if len(self.log_lines) > self.MAX_LINES:
            del self.log_lines[:len(self.log_lines) - self.MAX_LINES]

    def _passes_filter(self, entry):
        """
        Check a (level, line) entry against the level selector and search box.
        """
        level, line = entry
        if level < self.level_selector.currentData():
            return False
        search_text = self.search_edit.text().strip().lower()
        return not search_text or search_text in line.lower()

    def _append_line(self, entry):
        """
        Append a single (level, line) entry to the display, coloured by level.
        """
        level, line = entry
        cursor = QtGui.QTextCursor(self.log_display.document())
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        line_format = QtGui.QTextCharFormat()
        colour = LEVEL_COLOURS.get(level)
        if colour:
            line_format.setForeground(QtGui.QColor(colour))
        cursor.insertText(line + '\n', line_format)
        if self.follow_action.isChecked():
            scroll_bar = self.log_display.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())

    def on_filter_changed(self):
        """
        Re-render the display when the level selector or search box changes.
        """
        self.log_display.clear()
        for entry in self.log_lines:
            if self._passes_filter(entry):
                self._append_line(entry)

    def on_follow_toggled(self, checked):
        """
        Jump to the end of the log when follow is switched back on.
        """
        if checked:
            scroll_bar = self.log_display.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())

    def on_copy_clicked(self):
        """
        Copy the displayed (filtered) log messages to the clipboard.
        """
        QtWidgets.QApplication.clipboard().setText(self.log_display.toPlainText())

    def on_open_folder_clicked(self):
        """
        Open the folder containing the log file in the system file manager.
        """
        if self.log_file_path:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.log_file_path.parent)))
