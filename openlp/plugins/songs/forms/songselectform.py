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
The :mod:`~openlp.plugins.songs.forms.songselectform` module contains the GUI for the SongSelect importer
"""
import logging
import re

from PySide6 import QtCore, QtWidgets, QtWebEngineCore
from sqlalchemy.sql import and_
from tempfile import TemporaryDirectory

from openlp.core.common.i18n import translate
from openlp.core.common.mixins import RegistryProperties
from openlp.plugins.songs.forms.songselectdialog import Ui_SongSelectDialog
from openlp.plugins.songs.lib.db import Song
from openlp.plugins.songs.lib.songselect import SongSelectImport, Pages
from openlp.plugins.songs.lib.importers.chordpro import ChordProImport
from openlp.plugins.songs.lib.importers.cclifile import CCLIFileImport


REPLACE_ALL_JS = """
// Based on: https://vanillajstoolkit.com/polyfills/stringreplaceall/
if (!String.prototype.replaceAll) {
    String.prototype.replaceAll = function(str, newStr){
        // If a regex pattern
        if (Object.prototype.toString.call(str).toLowerCase() === '[object regexp]') {
            return this.replace(str, newStr);
        }
        // If a string
        return this.split(str).join(newStr);
    };
}
"""

log = logging.getLogger(__name__)


class SongSelectForm(QtWidgets.QDialog, Ui_SongSelectDialog, RegistryProperties):
    """
    The :class:`SongSelectForm` class is the SongSelect dialog.
    """

    def __init__(self, parent=None, plugin=None, db_manager=None):
        QtWidgets.QDialog.__init__(self, parent, QtCore.Qt.WindowType.WindowSystemMenuHint |
                                   QtCore.Qt.WindowType.WindowTitleHint |
                                   QtCore.Qt.WindowType.WindowCloseButtonHint)
        self.plugin = plugin
        self.db_manager = db_manager
        self.setup_ui(self)
        self.current_download_item = None
        self.tmp_folder = TemporaryDirectory(prefix='openlp_songselect_', ignore_cleanup_errors=True)

    def initialise(self):
        """
        Initialise the SongSelectForm
        """
        self.song = None
        self.song_select_importer = SongSelectImport(self.db_manager, self.webview)
        self.url_bar.returnPressed.connect(self.on_url_bar_return_pressed)
        self.back_button.clicked.connect(self.on_back_button_clicked)
        self.close_button.clicked.connect(self.done)
        self.webview.page().loadStarted.connect(self.page_load_started)
        self.webview.page().loadFinished.connect(self.page_loaded)
        self.webview.page().profile().downloadRequested.connect(self.on_download_requested)
        self.webview.urlChanged.connect(self.update_url)
        self.inject_js_str_replaceall()

    def inject_js_str_replaceall(self):
        """
        Inject an implementation of string replaceAll which are missing in pre 5.15.3 QWebEngine
        """
        script = QtWebEngineCore.QWebEngineScript()
        script.setInjectionPoint(QtWebEngineCore.QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setSourceCode(REPLACE_ALL_JS)
        script.setWorldId(QtWebEngineCore.QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(True)
        script.setName('string_replaceall')
        self.webview.page().scripts().insert(script)

    def update_url(self, new_url):
        self.url_bar.setText(new_url.toString())

    def download_finished(self):
        """
        Callback for when download has finished
        """
        if self.current_download_item:
            if self.current_download_item.state() ==\
                    QtWebEngineCore.QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                self.song_progress_bar.setValue(2)
                song_filename = self.current_download_item.downloadDirectory() + '/' \
                    + self.current_download_item.downloadFileName()
                song_file = open(song_filename, 'rt', encoding='utf-8')
                song_content = song_file.read()
                song_file.seek(0)
                if self.check_for_duplicate(song_content):
                    # if a chordpro title tag is in the file, assume it is chordpro format
                    if '{title:' in song_content:
                        # assume it is a ChordPro file
                        chordpro_importer = ChordProImport(self.plugin.manager, file_path=song_filename)
                        chordpro_importer.do_import_file(song_file)
                    else:
                        # assume it is a simple lyrics
                        cccli_lyrics_importer = CCLIFileImport(self.plugin.manager, file_path=song_filename)
                        lines = song_file.readlines()
                        cccli_lyrics_importer.do_import_txt_file(lines)
                    self.song_progress_bar.setValue(3)
                    QtWidgets.QMessageBox.information(self, translate('SongsPlugin.SongSelectForm', 'Song Imported'),
                                                      translate('SongsPlugin.SongSelectForm',
                                                                'Your song has been imported'))
                song_file.close()
                self.song_progress_bar.setVisible(False)
            self.url_bar.setVisible(True)
            self.webview.setEnabled(True)

    @QtCore.Slot(QtWebEngineCore.QWebEngineDownloadRequest)
    def on_download_requested(self, download_item):
        """
        Called when download is started
        """
        # only import from txt is supported
        if download_item.suggestedFileName().endswith('.txt'):
            self.song_progress_bar.setMaximum(3)
            self.song_progress_bar.setValue(1)
            self.song_progress_bar.setVisible(True)
            self.webview.setEnabled(False)
            download_item.setDownloadDirectory(self.tmp_folder.name)
            download_item.accept()
            self.current_download_item = download_item
            self.current_download_item.finished.connect(self.download_finished)
        else:
            download_item.cancel()
            QtWidgets.QMessageBox.information(self, translate('SongsPlugin.SongSelectForm', 'Unsupported format'),
                                              translate('SongsPlugin.SongSelectForm',
                                                        'OpenLP can only import simple lyrics or ChordPro'))

    def exec(self):
        """
        Execute the dialog. This method sets everything back to its initial
        values.
        """
        self.song_select_importer.reset_webview()
        self.back_button.setEnabled(False)
        self.stacked_widget.setCurrentIndex(0)
        return QtWidgets.QDialog.exec(self)

    def done(self, result_code):
        """
        Log out of SongSelect.

        :param result_code: The result of the dialog.
        """
        return QtWidgets.QDialog.done(self, result_code)

    def page_load_started(self):
        self.back_button.setEnabled(False)
        self.url_bar.setCursorPosition(0)
        self.url_bar.setVisible(True)
        self.message_area.setText(translate('SongsPlugin.SongSelectForm',
                                            'Import songs by clicking the "Download" in the Lyrics tab '
                                            'or "Download ChordPro" in the Chords tabs.'))

    def page_loaded(self, successful):
        self.song = None
        page_type = self.song_select_importer.get_page_type()
        if page_type == Pages.Login:
            self.signin_page_loaded()
        else:
            self.back_button.setEnabled(True)

    def signin_page_loaded(self):
        username = self.settings.value('songs/songselect username')
        password = self.settings.value('songs/songselect password')
        self.song_select_importer.set_login_fields(username, password)

    def _view_song(self):
        """
        Load a song into the song view.
        """
        if not self.song:
            QtWidgets.QMessageBox.critical(
                self, translate('SongsPlugin.SongSelectForm', 'Incomplete song'),
                translate('SongsPlugin.SongSelectForm', 'This song is missing some information, like the lyrics, '
                                                        'and cannot be imported.'),
                QtWidgets.QMessageBox.StandardButton(QtWidgets.QMessageBox.StandardButton.Ok),
                QtWidgets.QMessageBox.StandardButton.Ok)
            return
        # Clear up the UI
        self.author_list_widget.clear()
        self.lyrics_table_widget.clear()
        self.lyrics_table_widget.setRowCount(0)
        # Update the UI
        self.title_edit.setText(self.song['title'])
        self.copyright_edit.setText(self.song['copyright'])
        self.ccli_edit.setText(self.song['ccli_number'])
        for author in self.song['authors']:
            self.author_list_widget.addItem(QtWidgets.QListWidgetItem(author, self.author_list_widget))
        for counter, verse in enumerate(self.song['verses']):
            self.lyrics_table_widget.setRowCount(self.lyrics_table_widget.rowCount() + 1)
            item = QtWidgets.QTableWidgetItem(verse['lyrics'])
            item.setData(QtCore.Qt.ItemDataRole.UserRole, verse['label'])
            item.setFlags(item.flags() ^ QtCore.Qt.ItemFlag.ItemIsEditable)
            self.lyrics_table_widget.setItem(counter, 0, item)
        self.lyrics_table_widget.setVerticalHeaderLabels([verse['label'] for verse in self.song['verses']])
        self.lyrics_table_widget.resizeRowsToContents()
        self.lyrics_table_widget.scrollToTop()
        self.stacked_widget.setCurrentIndex(1)

    def on_url_bar_return_pressed(self):
        """
        Go to the url in the url bar
        """
        url = self.url_bar.text()
        self.song_select_importer.set_page(url)

    def on_back_button_clicked(self, force_return_to_home=False):
        """
        Go back to the search page or just to the webview if on the preview screen
        """
        if (self.stacked_widget.currentIndex() == 0 or force_return_to_home):
            self.song_select_importer.set_home_page()
        else:
            self.url_bar.setEnabled(True)
        self.stacked_widget.setCurrentIndex(0)

    def check_for_duplicate(self, song_content):
        """
        Warn user if a song exists in the database with the same ccli_number
        """
        # First extract the CCLI number of the song
        match = re.search(r'\nCCLI.+?#\s*(\d+)', song_content)
        if match:
            self.ccli_number = match.group(1)
        else:
            return True
        songs_with_same_ccli_number = self.plugin.manager.get_all_objects(
            Song, and_(Song.ccli_number.like(self.ccli_number), Song.ccli_number != ''))
        if len(songs_with_same_ccli_number) > 0:
            continue_import = QtWidgets.QMessageBox.question(self,
                                                             translate('SongsPlugin.SongSelectForm',
                                                                       'Song Duplicate Warning'),
                                                             translate('SongsPlugin.SongSelectForm',
                                                                       'A song with the same CCLI number is already in '
                                                                       'your database.\n\n'
                                                                       'Are you sure you want to import this song?'),
                                                             defaultButton=QtWidgets.QMessageBox.StandardButton.No)
            if continue_import == QtWidgets.QMessageBox.StandardButton.No:
                return False
        return True
