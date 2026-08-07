# -*- coding: utf-8 -*-

import logging
import os
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
from collections import namedtuple
from pathlib import Path
from shutil import copyfile
from typing import Any

import mako
from PySide6 import QtCore, QtWidgets
from sqlalchemy.sql import or_

from openlp.core.common.applocation import AppLocation
from openlp.core.common.enum import SongFirstSlideMode, SongSearch
from openlp.core.common.i18n import UiStrings, get_natural_key, translate
from openlp.core.common.path import create_paths
from openlp.core.common.registry import Registry
from openlp.core.lib import ServiceItemContext, check_item_selected, create_separated_list
from openlp.core.lib.mediamanageritem import MediaManagerItem
from openlp.core.lib.plugin import PluginStatus
from openlp.core.lib.serviceitem import ItemCapabilities
from openlp.core.lib.ui import create_widget_action, critical_error_message_box
from openlp.core.state import State
from openlp.core.ui.confirmationform import ConfirmationForm
from openlp.core.ui.icons import UiIcons
from openlp.plugins.songs.forms.editsongform import EditSongForm
from openlp.plugins.songs.forms.songexportform import SongExportForm
from openlp.plugins.songs.forms.songimportform import SongImportForm
from openlp.plugins.songs.forms.songmaintenanceform import SongMaintenanceForm
from openlp.plugins.songs.lib import VerseType, clean_string, delete_song
from openlp.plugins.songs.lib.db import Author, AuthorType, SongBook, MediaFile, Song, SongBookEntry, Topic
from openlp.plugins.songs.lib.openlyricsxml import OpenLyrics, SongXML
from openlp.plugins.songs.lib.ui import SongStrings

log = logging.getLogger(__name__)


class SongMediaItem(MediaManagerItem):
    """
    This is the custom media manager item for Songs.
    """
    songs_go_live = QtCore.Signal(list)
    songs_add_to_service = QtCore.Signal(list)
    log.info('Song Media Item loaded')

    def __init__(self, parent, plugin):
        self.icon_path = 'songs/song'
        super(SongMediaItem, self).__init__(parent, plugin)

    def setup_item(self):
        """
        Do some additional setup.
        """
        self.songs_go_live.connect(self.go_live_remote)
        self.songs_add_to_service.connect(self.add_to_service_remote)
        self.single_service_item = False
        # Holds information about whether the edit is remotely triggered and which Song is required.
        self.remote_song = -1
        self.edit_item = None
        self.quick_preview_allowed = True
        self.has_search = True
        self.search_timer = self.create_debounce_timer(self.on_search_timer_timeout)

    def _update_background_audio(self, song, item):
        song.media_files = []
        for i, bga in enumerate(item.background_audio):
            dest_path = \
                AppLocation.get_section_data_path(self.plugin.name) / 'audio' / str(song.id) / os.path.split(bga[0])[1]
            create_paths(dest_path.parent)
            copyfile(AppLocation.get_section_data_path('servicemanager') / bga[0], dest_path)
            song.media_files.append(MediaFile(weight=i, file_path=dest_path, file_hash=bga[1]))
        self.plugin.manager.save_object(song, True)

    def add_middle_header_bar(self):
        self.toolbar.addSeparator()
        # Song Maintenance Button
        self.maintenance_action = self.toolbar.add_toolbar_action('maintenance_action',
                                                                  icon=UiIcons().database,
                                                                  triggers=self.on_song_maintenance_click)

        self.add_search_to_toolbar()
        # Add in an extra toggle button
        self.favourite_toggle_button = QtWidgets.QPushButton(self)
        self.favourite_toggle_button.setObjectName('favourite_toggle_button')
        self.favourite_toggle_button.setIcon(UiIcons().favourite)
        self.favourite_toggle_button.setCheckable(True)
        self.favourite_toggle_button.setChecked(self.settings.value('songs/favourites_toggled'))
        self.search_button_layout.insertWidget(1, self.favourite_toggle_button)
        # Signals and slots
        Registry().register_function('songs_load_list', self.on_song_list_load)
        Registry().register_function('songs_preview', self.on_preview_click)
        self.search_text_edit.searchTypeChanged.connect(self.on_search_text_button_clicked)
        self.favourite_toggle_button.toggled.connect(self.on_favourite_toggle_button_clicked)

    def add_custom_context_actions(self):
        create_widget_action(self.list_view, separator=True)
        create_widget_action(
            self.list_view, text=translate('OpenLP.MediaManagerItem', '&Clone'), icon=UiIcons().clone,
            triggers=self.on_clone_click)
        create_widget_action(
            self.list_view,
            text=translate('OpenLP.SongsPlugin', 'Toggle Favourite'),
            icon=UiIcons().favourite,
            triggers=self.on_favourite_click
        )

    def on_focus(self):
        self.search_text_edit.setFocus()
        self.search_text_edit.selectAll()

    def config_update(self):
        """
        Is triggered when the songs config is updated
        """
        log.debug('config_updated')
        self.is_search_as_you_type_enabled = self.settings.value('advanced/search as type')
        self.update_service_on_edit = self.settings.value('songs/update service on edit')
        self.add_song_from_service = self.settings.value('songs/add song from service')

    def retranslate_ui(self):
        self.search_text_label.setText('{text}:'.format(text=UiStrings().Search))
        self.search_text_button.setText(UiStrings().Search)
        self.maintenance_action.setText(SongStrings().SongMaintenance)
        self.maintenance_action.setToolTip(translate('SongsPlugin.MediaItem',
                                                     'Maintain the lists of authors, topics and books.'))
        self.favourite_toggle_button.setToolTip(translate('SongsPlugin.MediaItem',
                                                          'Show only favourites'))

    def initialise(self):
        """
        Initialise variables when they cannot be initialised in the constructor.
        """
        self.song_maintenance_form = SongMaintenanceForm(self.plugin.manager, self)
        self.edit_song_form = EditSongForm(self, self.main_window, self.plugin.manager)
        self.open_lyrics = OpenLyrics(self.plugin.manager)
        self.search_text_edit.set_search_types([
            (SongSearch.Entire, UiIcons().music,
             translate('SongsPlugin.MediaItem', 'Entire Song'),
             translate('SongsPlugin.MediaItem', 'Search Entire Song...')),
            (SongSearch.Titles, UiIcons().search_text,
             translate('SongsPlugin.MediaItem', 'Titles'),
             translate('SongsPlugin.MediaItem', 'Search Titles...')),
            (SongSearch.Lyrics, UiIcons().search_lyrics,
             translate('SongsPlugin.MediaItem', 'Lyrics'),
             translate('SongsPlugin.MediaItem', 'Search Lyrics...')),
            (SongSearch.Authors, UiIcons().user, SongStrings().Authors,
             translate('SongsPlugin.MediaItem', 'Search Authors...')),
            (SongSearch.Topics, UiIcons().light_bulb, SongStrings().Topics,
             translate('SongsPlugin.MediaItem', 'Search Topics...')),
            (SongSearch.Books, UiIcons().address, SongStrings().SongBooks,
             translate('SongsPlugin.MediaItem', 'Search Songbooks...')),
            (SongSearch.Themes, UiIcons().theme, UiStrings().Themes, UiStrings().SearchThemes),
            (SongSearch.Copyright, UiIcons().copyright,
             translate('SongsPlugin.MediaItem', 'Copyright'),
             translate('SongsPlugin.MediaItem', 'Search Copyright...')),
            (SongSearch.CCLInumber, UiIcons().search_ccli,
             translate('SongsPlugin.MediaItem', 'CCLI number'),
             translate('SongsPlugin.MediaItem', 'Search CCLI number...'))
        ])
        self.config_update()

    def on_favourite_toggle_button_clicked(self, checked: bool) -> None:
        """Run the search when the button is clicked, and save the state to the settings"""
        self.settings.setValue('songs/favourites_toggled', checked)
        self.on_search_text_button_clicked()

    def on_search_text_button_clicked(self):
        # Reload the list considering the new search type.
        self.list_view.set_loading_state(True)
        search_keywords = str(self.search_text_edit.displayText())
        search_type = self.search_text_edit.current_search_type()
        filter_clauses = []
        is_fav = self.favourite_toggle_button.isChecked()
        try:
            if is_fav and search_type not in [SongSearch.Authors, SongSearch.Topics]:
                filter_clauses.append(Song.is_favourite.is_(True))
            if search_type == SongSearch.Entire:
                log.debug('Entire Song Search')
                search_results = self.search_entire(search_keywords, *filter_clauses)
                self.display_results_song(search_results)
            elif search_type == SongSearch.Titles:
                log.debug('Titles Search')
                search_string = '%{text}%'.format(text=clean_string(search_keywords))
                filter_clauses.append(Song.search_title.like(search_string))
                search_results = self.plugin.manager.get_all_objects(Song, *filter_clauses)
                self.display_results_song(search_results)
            elif search_type == SongSearch.Lyrics:
                log.debug('Lyrics Search')
                search_string = '%{text}%'.format(text=clean_string(search_keywords))
                filter_clauses.append(Song.search_lyrics.like(search_string))
                search_results = self.plugin.manager.get_all_objects(Song, *filter_clauses)
                self.display_results_song(search_results)
            elif search_type == SongSearch.Authors:
                log.debug('Authors Search')
                search_string = '%{text}%'.format(text=search_keywords)
                search_results = self.plugin.manager.get_all_objects(Author, Author.display_name.like(search_string))
                self.display_results_author(search_results, is_fav)
            elif search_type == SongSearch.Topics:
                log.debug('Topics Search')
                search_string = '%{text}%'.format(text=search_keywords)
                search_results = self.plugin.manager.get_all_objects(Topic, Topic.name.like(search_string))
                self.display_results_topic(search_results, is_fav)
            elif search_type == SongSearch.Books:
                log.debug('Songbook Search')
                search_keywords = search_keywords.rpartition(' ')
                search_book = '{text}%'.format(text=search_keywords[0])
                search_entry = '{text}%'.format(text=search_keywords[2])
                filter_clauses.extend([
                    SongBook.name.like(search_book),
                    SongBookEntry.entry.like(search_entry),
                    Song.temporary.is_(False)
                ])
                search_results = self.plugin.manager.session.query(
                    SongBookEntry.entry,
                    SongBook.name,
                    Song.title,
                    Song.id
                ).join(Song).join(SongBook).filter(*filter_clauses).all()
                self.display_results_book(search_results)
            elif search_type == SongSearch.Themes:
                log.debug('Theme Search')
                search_string = '%{text}%'.format(text=search_keywords)
                filter_clauses.append(Song.theme_name.like(search_string))
                search_results = self.plugin.manager.get_all_objects(Song, *filter_clauses)
                self.display_results_themes(search_results)
            elif search_type == SongSearch.Copyright:
                log.debug('Copyright Search')
                search_string = '%{text}%'.format(text=search_keywords)
                filter_clauses.extend([
                    Song.copyright.like(search_string),
                    Song.copyright != ''
                ])
                search_results = self.plugin.manager.get_all_objects(Song, *filter_clauses)
                self.display_results_song(search_results)
            elif search_type == SongSearch.CCLInumber:
                log.debug('CCLI number Search')
                search_string = '%{text}%'.format(text=search_keywords)
                filter_clauses.extend([
                    Song.ccli_number.like(search_string),
                    Song.ccli_number != ''
                ])
                search_results = self.plugin.manager.get_all_objects(Song, *filter_clauses)
                self.display_results_cclinumber(search_results)
        finally:
            self.list_view.set_loading_state(False)

    def search_entire(self, search_keywords: str, *filter_clauses):
        search_string = '%{text}%'.format(text=clean_string(search_keywords))
        filter_clauses = list(filter_clauses)
        filter_clauses.append(
            or_(
                SongBook.name.like(search_string), SongBookEntry.entry.like(search_string),
                # hint: search_title contains alternate title
                Song.search_title.like(search_string), Song.search_lyrics.like(search_string),
                Song.comments.like(search_string)
            )
        )
        return self.plugin.manager.session.query(Song) \
            .join(SongBookEntry, isouter=True) \
            .join(SongBook, isouter=True) \
            .filter(*filter_clauses) \
            .all()

    def on_song_list_load(self):
        """
        Handle the exit from the edit dialog and trigger remote updates of songs
        """
        log.debug('on_song_list_load - start')
        # Called to redisplay the song list screen edit from a search or from the exit of the Song edit dialog. If
        # remote editing is active Trigger it and clean up so it will not update again. Push edits to the service
        # manager to update items
        if self.edit_item and self.update_service_on_edit and not self.remote_triggered:
            item = self.build_service_item(self.edit_item)
            self.service_manager.replace_service_item(item)
        self.on_search_text_button_clicked()
        log.debug('on_song_list_load - finished')

    def display_results_song(self, search_results):
        """
        Display the song search results in the media manager list

        :param search_results: A list of db Song objects
        :return: None
        """

        def get_song_key(song):
            """Get the key to sort by"""
            return song.sort_key

        log.debug('display results Song')
        self.save_auto_select_id()
        self.list_view.clear()
        search_results.sort(key=get_song_key)
        for song in search_results:
            # Do not display temporary songs
            if song.temporary:
                continue
            song_name = QtWidgets.QListWidgetItem(song.song_detail)
            song_name.setData(QtCore.Qt.ItemDataRole.UserRole, song.id)
            self.list_view.addItem(song_name)
            # Auto-select the item if name has been set
            if song.id == self.auto_select_id:
                self.list_view.setCurrentItem(song_name)
        self.auto_select_id = -1

    def display_results_author(self, search_results: list[Author], is_fav: bool = False):
        """
        Display the song search results in the media manager list, grouped by author

        :param search_results: A list of db Author objects
        :return: None
        """

        def get_author_key(author):
            """Get the key to sort by"""
            return get_natural_key(author.display_name)

        def get_song_key(song):
            """Get the key to sort by"""
            return song.sort_key

        log.debug('display results Author')
        self.list_view.clear()
        search_results.sort(key=get_author_key)
        for author in search_results:
            if is_fav:
                songs = [author_song.song for author_song in author.authors_songs if author_song.song.is_favourite]
            else:
                songs = [author_song.song for author_song in author.authors_songs]
            songs.sort(key=get_song_key)
            for song in songs:
                # Do not display temporary songs
                if song.temporary:
                    continue
                song_detail = '{author} ({title})'.format(author=author.display_name, title=song.title)
                song_name = QtWidgets.QListWidgetItem(song_detail)
                song_name.setData(QtCore.Qt.ItemDataRole.UserRole, song.id)
                self.list_view.addItem(song_name)

    def display_results_book(self, search_results):
        """
        Display the song search results in the media manager list, grouped by book and entry

        :param search_results: A tuple containing (songbook entry, book name, song title, song id)
        :return: None
        """

        def get_songbook_key(text):
            """
            Get the key to sort by
            :param text: the text tuple to be processed.
            """
            return get_natural_key('{0} {1} {2}'.format(text[1], text[0], text[2]))

        log.debug('display results Book')
        self.list_view.clear()
        search_results.sort(key=get_songbook_key)
        for result in search_results:
            song_detail = '{result1} #{result0}: {result2}'.format(result1=result[1], result0=result[0],
                                                                   result2=result[2])
            song_name = QtWidgets.QListWidgetItem(song_detail)
            song_name.setData(QtCore.Qt.ItemDataRole.UserRole, result[3])
            self.list_view.addItem(song_name)

    def display_results_topic(self, search_results, is_fav: bool = False):
        """
        Display the song search results in the media manager list, grouped by topic

        :param search_results: A list of db Topic objects
        :return: None
        """

        def get_topic_key(topic):
            """Get the key to sort by"""
            return get_natural_key(topic.name)

        def get_song_key(song):
            """Get the key to sort by"""
            return song.sort_key

        log.debug('display results Topic')
        self.list_view.clear()
        search_results.sort(key=get_topic_key)
        for topic in search_results:
            topic.songs.sort(key=get_song_key)
            for song in topic.songs:
                # Do not display temporary songs
                if (is_fav and not song.is_favourite) or song.temporary:
                    continue
                song_detail = '{topic} ({title})'.format(topic=topic.name, title=song.title)
                song_name = QtWidgets.QListWidgetItem(song_detail)
                song_name.setData(QtCore.Qt.ItemDataRole.UserRole, song.id)
                self.list_view.addItem(song_name)

    def display_results_themes(self, search_results):
        """
        Display the song search results in the media manager list, sorted by theme

        :param search_results: A list of db Song objects
        :return: None
        """

        def get_theme_key(song):
            """Get the key to sort by"""
            return get_natural_key(song.theme_name), song.sort_key

        log.debug('display results Themes')
        self.list_view.clear()
        search_results.sort(key=get_theme_key)
        for song in search_results:
            # Do not display temporary songs
            if song.temporary:
                continue
            song_detail = '{theme} ({song})'.format(theme=song.theme_name, song=song.title)
            song_name = QtWidgets.QListWidgetItem(song_detail)
            song_name.setData(QtCore.Qt.ItemDataRole.UserRole, song.id)
            self.list_view.addItem(song_name)

    def display_results_cclinumber(self, search_results):
        """
        Display the song search results in the media manager list, sorted by CCLI number

        :param search_results: A list of db Song objects
        :return: None
        """

        def get_cclinumber_key(song):
            """Get the key to sort by"""
            return get_natural_key(song.ccli_number), song.sort_key

        log.debug('display results CCLI number')
        self.list_view.clear()
        search_results.sort(key=get_cclinumber_key)
        for song in search_results:
            # Do not display temporary songs
            if song.temporary:
                continue
            song_detail = '{ccli} ({song})'.format(ccli=song.ccli_number, song=song.title)
            song_name = QtWidgets.QListWidgetItem(song_detail)
            song_name.setData(QtCore.Qt.ItemDataRole.UserRole, song.id)
            self.list_view.addItem(song_name)

    def on_clear_text_button_click(self):
        """
        Clear the search text.
        """
        self.search_text_edit.clear()
        self.on_search_text_button_clicked()

    def on_search_text_edit_changed(self, text):
        """
        If search as type enabled invoke the search on each key press. If the Lyrics are being searched do not start
        till 7 characters have been entered.
        """
        if self.is_search_as_you_type_enabled:
            search_length = 1
            if self.search_text_edit.current_search_type() == SongSearch.Entire:
                search_length = 4
            elif self.search_text_edit.current_search_type() == SongSearch.Lyrics:
                search_length = 3
            if len(text) > search_length:
                self.start_debounced_search(self.search_timer)
            elif not text:
                self.search_timer.stop()
                self.on_clear_text_button_click()

    def on_search_timer_timeout(self):
        """
        Perform a debounced song search.
        """
        self.on_search_text_button_clicked()

    def on_import_click(self):
        if not hasattr(self, 'import_wizard'):
            self.import_wizard = SongImportForm(self, self.plugin)
        self.import_wizard.exec()
        # Run song load as list may have been cancelled but some songs loaded
        Registry().execute('songs_load_list')

    def on_export_click(self):
        if not hasattr(self, 'export_wizard'):
            self.export_wizard = SongExportForm(self, self.plugin)
        self.export_wizard.exec()

    def on_new_click(self):
        log.debug('on_new_click')
        self.edit_song_form.new_song()
        self.edit_song_form.exec()
        self.on_clear_text_button_click()
        self.on_selection_change()
        self.auto_select_id = -1

    def on_song_maintenance_click(self):
        self.song_maintenance_form.exec()

    def on_remote_edit(self, song_id, preview=False):
        """
        Called by ServiceManager or SlideController by event passing the Song Id in the payload along with an indicator
        to say which type of display is required.
        :param song_id: the id of the song
        :param preview: show we preview after the update
        """
        log.debug('on_remote_edit for song {song}'.format(song=song_id))
        song_id = int(song_id)
        valid = self.plugin.manager.get_object(Song, song_id)
        if valid:
            self.edit_song_form.load_song(song_id, preview)
            if self.edit_song_form.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                self.auto_select_id = -1
                self.on_song_list_load()
                self.remote_song = song_id
                self.remote_triggered = True
                item = self.build_service_item(remote=True)
                self.remote_song = -1
                self.remote_triggered = None
                if item:
                    if preview:
                        # A song can only be edited if it comes from plugin, so we set it again for the new item.
                        item.from_plugin = True
                    return item
        return None

    def on_edit_click(self):
        """
        Edit a song
        """
        log.debug('on_edit_click')
        if check_item_selected(self.list_view, UiStrings().SelectEdit):
            self.edit_item = self.list_view.currentItem()
            item_id = self.edit_item.data(QtCore.Qt.ItemDataRole.UserRole)
            self.edit_song_form.load_song(item_id, False)
            self.edit_song_form.exec()
            self.auto_select_id = -1
            self.on_song_list_load()
        self.edit_item = None

    def on_delete_click(self):
        """
        Remove a song or songs from the list and database
        """
        if check_item_selected(self.list_view, UiStrings().SelectDelete):
            items = self.list_view.selectedItems()
            item_strings = map(lambda i: i.text(), items)
            delete_confirmed = ConfirmationForm(self, UiStrings().ConfirmDelete, item_strings,
                                                translate('SongsPlugin.MediaItem',
                                                          'Are you sure you want to delete these songs?')).exec()
            if not delete_confirmed:
                return
            self.application.set_busy_cursor()
            self.main_window.display_progress_bar(len(items))
            for item in items:
                item_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
                delete_song(item_id, self.plugin)
                self.main_window.increment_progress_bar()
            self.main_window.finished_progress_bar()
            self.application.set_normal_cursor()
            self.on_search_text_button_clicked()

    def on_clone_click(self):
        """
        Clone a Song
        """
        log.debug('on_clone_click')
        if check_item_selected(self.list_view, UiStrings().SelectEdit):
            self.edit_item = self.list_view.currentItem()
            item_id = self.edit_item.data(QtCore.Qt.ItemDataRole.UserRole)
            old_song = self.plugin.manager.get_object(Song, item_id)
            song_xml = self.open_lyrics.song_to_xml(old_song)
            new_song = self.open_lyrics.xml_to_song(song_xml)
            new_song.title = '{title} <{text}>'.format(title=new_song.title,
                                                       text=translate('SongsPlugin.MediaItem',
                                                                      'copy', 'For song cloning'))
            # Copy audio files from the old to the new song
            if len(old_song.media_files) > 0:
                save_path = AppLocation.get_section_data_path(self.plugin.name) / 'audio' / str(new_song.id)
                create_paths(save_path)
                for media_file in old_song.media_files:
                    new_media_file_path = save_path / media_file.file_path.name
                    copyfile(media_file.file_path, new_media_file_path)
                    new_media_file = MediaFile()
                    new_media_file.file_path = new_media_file_path
                    new_media_file.file_hash = media_file.file_hash
                    new_media_file.type = media_file.type
                    new_media_file.weight = media_file.weight
                    new_song.media_files.append(new_media_file)
            self.plugin.manager.save_object(new_song)
            new_song.init_on_load()
            Registry().execute('song_changed', new_song.id)
        self.on_song_list_load()

    def on_favourite_click(self):
        """Toggle a song as a favourite"""
        log.debug('on_favourite_click')
        if check_item_selected(self.list_view, UiStrings().SelectEdit):
            for selected_item in self.list_view.selectedItems():
                item_id = selected_item.data(QtCore.Qt.ItemDataRole.UserRole)
                song = self.plugin.manager.get_object(Song, item_id)
                song.is_favourite = not song.is_favourite
                self.plugin.manager.save_object(song)
                Registry().execute('song_changed', song.id)
        self.on_song_list_load()

    def generate_slide_data(self, service_item, *, item=None, context=ServiceItemContext.Service, **kwargs):
        """
        Generate the slide data. Needs to be implemented by the plugin.

        :param service_item: The service item to be built on
        :param item: The Song item to be used
        :param context: Why is it being generated
        :param kwargs: Consume other unused args specified by the base implementation, but not use by this one.
        """
        log.debug('generate_slide_data: {service}, {item}, {remote}'.format(service=service_item, item=item,
                                                                            remote=self.remote_song))
        uppercase = bool(self.settings.value('songs/uppercase songs'))

        # Load preview settings
        preview_enabled = bool(self.settings.value('songs/preview_enabled'))
        preview_intro = bool(self.settings.value('songs/preview_intro'))
        preview_verse = bool(self.settings.value('songs/preview_verse'))
        preview_chorus = bool(self.settings.value('songs/preview_chorus'))
        preview_bridge = bool(self.settings.value('songs/preview_bridge'))
        preview_pre_chorus = bool(self.settings.value('songs/preview_pre_chorus'))
        preview_ending = bool(self.settings.value('songs/preview_ending'))
        preview_other = bool(self.settings.value('songs/preview_other'))

        item_id = self._get_id_of_item_to_generate(item, self.remote_song)
        service_item.add_capability(ItemCapabilities.CanEdit)
        service_item.add_capability(ItemCapabilities.CanPreview)
        service_item.add_capability(ItemCapabilities.CanLoop)
        service_item.add_capability(ItemCapabilities.OnLoadUpdate)
        service_item.add_capability(ItemCapabilities.AddIfNewItem)
        service_item.add_capability(ItemCapabilities.CanSoftBreak)
        service_item.add_capability(ItemCapabilities.HasMetaData)
        song = self.plugin.manager.get_object(Song, item_id)
        service_item.theme = song.theme_name
        service_item.edit_id = item_id
        verse_list = SongXML().get_verses(song.lyrics)
        authors = self._get_music_authors(song)
        songbooks_str = [str(songbook_entry) for songbook_entry in song.songbook_entries]
        mako_vars = self._get_mako_vars(song, authors, songbooks_str)
        service_item.title = song.title
        author_list = self.generate_first_slide_and_footer(service_item, song, authors, songbooks_str, mako_vars)
        # no verse list or only 1 space (in error)
        verse_tags_translated = False
        if VerseType.from_translated_string(str(verse_list[0][0]['type'])) is not None:
            verse_tags_translated = True
        if not song.verse_order.strip():
            for verse in verse_list:
                # We cannot use from_loose_input() here, because database is supposed to contain English lowercase
                # single char tags.
                verse_tag = verse[0]['type']
                verse_index = None
                if len(verse_tag) > 1:
                    verse_index = VerseType.from_translated_string(verse_tag)
                    if verse_index is None:
                        verse_index = VerseType.from_string(verse_tag, None)
                if verse_index is None:
                    verse_index = VerseType.from_tag(verse_tag)
                verse_tag = VerseType.translated_tags[verse_index].upper()
                verse_def = '{tag}{label}'.format(tag=verse_tag, label=verse[0]['label'])
                force_verse = verse[1].split('[--}{--]\n')
                for split_verse in force_verse:
                    if uppercase:
                        split_verse = "{uc}" + split_verse + "{/uc}"
                    service_item.add_from_text(split_verse, verse_def)
        else:
            # Loop through the verse list and expand the song accordingly.
            order_list = song.verse_order.lower().split()
            for order_pos, order in enumerate(order_list):
                if not order:
                    break
                for verse in verse_list:
                    if verse[0]['type'][0].lower() == \
                            order[0] and (verse[0]['label'].lower() == order[1:] or not order[1:]):
                        if verse_tags_translated:
                            verse_index = VerseType.from_translated_tag(verse[0]['type'])
                        else:
                            verse_index = VerseType.from_tag(verse[0]['type'])
                        verse_tag = VerseType.translated_tags[verse_index]
                        verse_def = '{tag}{label}'.format(tag=verse_tag, label=verse[0]['label'])
                        force_verse = verse[1].split('[--}{--]\n')

                        for i, split_verse in enumerate(force_verse):
                            # Feature #118 - Append preview of next verse's first line if applicable
                            preview_line = ""

                            if preview_enabled:
                                verse_type_lower = verse[0]['type'].lower()

                                # Determine if preview is allowed for this strophe type
                                preview_allowed = any([
                                    (verse_type_lower.startswith("i") and preview_intro),
                                    (verse_type_lower.startswith("v") and preview_verse),
                                    (verse_type_lower.startswith("c") and preview_chorus),
                                    (verse_type_lower.startswith("b") and preview_bridge),
                                    (verse_type_lower.startswith("p") and preview_pre_chorus),
                                    (verse_type_lower.startswith("e") and preview_ending),
                                    (verse_type_lower.startswith("o") and preview_other)
                                ])

                                if preview_allowed:
                                    if i < len(force_verse) - 1:
                                        # Case 1: preview next split of the same verse
                                        next_lines = force_verse[i + 1].splitlines()
                                        if next_lines:
                                            preview_line = "{preview}" + next_lines[0] + "{/preview}"

                                    if (
                                            not preview_line
                                            and i == len(force_verse) - 1
                                            and order_pos + 1 < len(order_list)
                                    ):
                                        # Case 2: preview first line of the next verse
                                        next_order = order_list[order_pos + 1]
                                        for next_verse in verse_list:
                                            if (
                                                next_verse[0]['type'][0].lower() == next_order[0]
                                                and (
                                                    next_verse[0]['label'].lower() == next_order[1:]
                                                    or not next_order[1:]
                                                )
                                            ):
                                                next_verse_type = next_verse[0]['type'].lower()
                                                next_allowed = any([
                                                    (next_verse_type.startswith("i") and preview_intro),
                                                    (next_verse_type.startswith("v") and preview_verse),
                                                    (next_verse_type.startswith("c") and preview_chorus),
                                                    (next_verse_type.startswith("b") and preview_bridge),
                                                    (next_verse_type.startswith("p") and preview_pre_chorus),
                                                    (next_verse_type.startswith("e") and preview_ending),
                                                    (next_verse_type.startswith("o") and preview_other)
                                                ])
                                                if next_allowed:
                                                    next_verse_lines = next_verse[1].splitlines()
                                                    if next_verse_lines:
                                                        preview_line = "{preview}" + next_verse_lines[0] + "{/preview}"
                                                break

                            # Append preview line if present
                            if preview_line:
                                split_verse = split_verse.rstrip() + "\n" + preview_line
                            # Feature #2098 - uppercase
                            if uppercase:
                                split_verse = "{uc}" + split_verse + "{/uc}"

                            service_item.add_from_text(split_verse, verse_def)

        service_item.data_string = {
            'title': song.search_title,
            'alternate_title': song.alternate_title,
            'authors': ', '.join(author_list),
            'ccli_number': song.ccli_number,
            'copyright': song.copyright
        }
        service_item.xml_version = self.open_lyrics.song_to_xml(song)
        # Add the audio file to the service item.
        if song.media_files:
            if State().check_preconditions('media'):
                service_item.add_capability(ItemCapabilities.HasBackgroundAudio)
                total_length = 0
                # We could have stored multiple files but only the first one will be played.
                for m in song.media_files:
                    file_path = Path(m.file_path)
                    if file_path.is_file():
                        total_length += self.media_controller.media_length(file_path)
                        service_item.background_audio = [(file_path, m.file_hash)]
                    break
                service_item.set_media_length(total_length)
                service_item.metadata.append('<em>{label}:</em> {media}'.
                                             format(label=translate('SongsPlugin.MediaItem', 'Media'),
                                                    media=service_item.background_audio))
        return True

    def generate_footer(self, item, song, authors, songbooks, mako_vars):
        """
        Generates the song footer based on a song and adds details to a service item.

        :param item: The service item to be amended
        :param song: The song to be used to generate the footer
        :param authors: The authors of the song
        :return: List of all authors (only required for initial song generation)
        """
        item.audit = [
            song.title, authors.all, song.copyright, str(song.ccli_number)
        ]
        item.raw_footer = []
        item.raw_footer.append(song.title)
        if authors.none:
            item.raw_footer.append("{text}: {authors}".format(text=translate('OpenLP.Ui', 'Written by'),
                                                              authors=create_separated_list(authors.none)))
        if authors.words_music:
            item.raw_footer.append("{text}: {authors}".format(
                text=AuthorType.get_translated_type(AuthorType.WordsAndMusic),
                authors=create_separated_list(authors.words_music))
            )
        if authors.words:
            item.raw_footer.append("{text}: {authors}".format(text=AuthorType.get_translated_type(AuthorType.Words),
                                                              authors=create_separated_list(authors.words)))
        if authors.music:
            item.raw_footer.append("{text}: {authors}".format(text=AuthorType.get_translated_type(AuthorType.Music),
                                                              authors=create_separated_list(authors.music)))
        if authors.translation:
            item.raw_footer.append("{text}: {authors}".format(
                text=AuthorType.get_translated_type(AuthorType.Translation),
                authors=create_separated_list(authors.translation))
            )
        if song.copyright:
            item.raw_footer.append("{symbol} {song}".format(symbol=SongStrings().CopyrightSymbol,
                                                            song=song.copyright))
        if song.songbook_entries:
            item.raw_footer.append(", ".join(songbooks))
        if self.settings.value('core/ccli number'):
            item.raw_footer.append(translate('SongsPlugin.MediaItem', 'CCLI License: ') +
                                   self.settings.value('core/ccli number'))
        item.footer_html = self._generate_mako_footer(mako_vars)
        return authors.all

    def _get_music_authors(self, song):
        authors_tuple = namedtuple('AuthorsTuple', ['words', 'music', 'words_music', 'translation', 'none', 'all'])
        authors_words = []
        authors_music = []
        authors_words_music = []
        authors_translation = []
        authors_none = []
        for author_song in song.authors_songs:
            if author_song.author_type == AuthorType.Words:
                authors_words.append(author_song.author.display_name)
            elif author_song.author_type == AuthorType.Music:
                authors_music.append(author_song.author.display_name)
            elif author_song.author_type == AuthorType.WordsAndMusic:
                authors_words_music.append(author_song.author.display_name)
            elif author_song.author_type == AuthorType.Translation:
                authors_translation.append(author_song.author.display_name)
            else:
                authors_none.append(author_song.author.display_name)
        authors_all = authors_words_music + authors_words + authors_music + authors_translation + authors_none
        return authors_tuple(authors_words, authors_music, authors_words_music, authors_translation, authors_none,
                             authors_all)

    def _get_mako_vars(self, song, authors, songbooks):
        # Keep this in sync with the list in songstab.py
        return {
            'title': song.title,
            'alternate_title': song.alternate_title,
            'authors_none_label': translate('OpenLP.Ui', 'Written by'),
            'authors_none': authors.none,
            'authors_words_label': AuthorType.get_translated_type(AuthorType.Words),
            'authors_words': authors.words,
            'authors_music_label': AuthorType.get_translated_type(AuthorType.Music),
            'authors_music': authors.music,
            'authors_words_music_label': AuthorType.get_translated_type(AuthorType.WordsAndMusic),
            'authors_words_music': authors.words_music,
            'authors_translation_label': AuthorType.get_translated_type(AuthorType.Translation),
            'authors_translation': authors.translation,
            'authors_words_all': authors.words + authors.words_music,
            'authors_music_all': authors.music + authors.words_music,
            'copyright': song.copyright,
            'songbook_entries': songbooks,
            'ccli_license': self.settings.value('core/ccli number'),
            'ccli_license_label': translate('SongsPlugin.MediaItem', 'CCLI License'),
            'ccli_number': song.ccli_number,
            'topics': [topic.name for topic in song.topics],
            'first_slide': False
        }

    def _generate_mako_footer(self, vars, show_error=True):
        footer_template = self.settings.value('songs/footer template')
        try:
            return mako.template.Template(footer_template).render_unicode(**vars).replace('\n', '')
        except (mako.exceptions.SyntaxException, mako.exceptions.CompileException):
            log.error('Failed to render Song footer html:\n' + mako.exceptions.text_error_template().render())
            if show_error:
                critical_error_message_box(message=translate('SongsPlugin.MediaItem',
                                                             'Failed to render Song footer html.\nSee log for details'))
        return None

    def service_load(self, item):
        """
        Triggered by a song being loaded by the service manager.
        """
        log.debug('service_load')
        if self.plugin.status != PluginStatus.Active or not item.data_string:
            return
        search_results = self.plugin.manager.get_all_objects(
            Song, Song.search_title == item.data_string['title'], Song.search_title.asc())
        edit_id = 0
        add_song = True
        if search_results:
            for song in search_results:
                if self._authors_match(song, item.data_string['authors']):
                    add_song = False
                    edit_id = song.id
                    break
                # If there's any backing tracks, copy them over.
                if item.background_audio:
                    self._update_background_audio(song, item)
        if add_song and self.add_song_from_service:
            song = self.open_lyrics.xml_to_song(item.xml_version)
            # If there's any backing tracks, copy them over.
            if item.background_audio:
                self._update_background_audio(song, item)
            edit_id = song.id
            song.init_on_load()
            self.on_search_text_button_clicked()
        elif add_song and not self.add_song_from_service:
            # Make sure we temporary import formatting tags.
            song = self.open_lyrics.xml_to_song(item.xml_version, True)
            # If there's any backing tracks, copy them over.
            if item.background_audio:
                self._update_background_audio(song, item)
            edit_id = song.id
        # Update service with correct song id and return it to caller.
        authors = self._get_music_authors(song)
        songbooks_str = [str(songbook_entry) for songbook_entry in song.songbook_entries]
        mako_vars = self._get_mako_vars(song, authors, songbooks_str)
        self.generate_footer(item, song, authors, songbooks_str, mako_vars)
        if len(item.slides):
            first_slide = item.slides[0]
            if 'metadata' in first_slide and 'songs_first_slide_type' in first_slide['metadata']:
                try:
                    slide_mode = SongFirstSlideMode(first_slide['metadata']['songs_first_slide_type'])
                    if slide_mode == SongFirstSlideMode.Footer:
                        # For now only the footer needs to be regenerated on import, as it's dependent on what
                        # user defined on each OpenLP instance settings.
                        self.generate_first_slide_and_footer(item, song, authors, songbooks_str, mako_vars, True)
                except ValueError:
                    # Maybe it's a new slide mode generated in a greater OpenLP version, better leave it as-is.
                    pass
        item.edit_id = edit_id
        return item

    def generate_first_slide_and_footer(self, service_item, song, authors, songbooks_str, mako_vars, replace=False):
        song_first_slide = self.settings.value('songs/first slide mode')
        service_item.title = song.title
        author_list = self.generate_footer(service_item, song, authors, songbooks_str, mako_vars)
        slide_metadata = {'songs_first_slide_type': song_first_slide}
        if song_first_slide == SongFirstSlideMode.Songbook and song.songbook_entries:
            first_slide = '\n'
            for songbook_entry in song.songbook_entries:
                if songbook_entry.entry:
                    first_slide += '{book} #{num}'.format(book=songbook_entry.songbook.name,
                                                          num=songbook_entry.entry)
                else:
                    first_slide += songbook_entry.songbook.name
                if songbook_entry.songbook.publisher:
                    first_slide += ' ({pub})'.format(pub=songbook_entry.songbook.publisher)
                first_slide += '\n\n'
            if replace:
                service_item.replace_slide_from_text(0, first_slide, 'O1', metadata=slide_metadata)
            else:
                service_item.add_from_text(first_slide, 'O1', metadata=slide_metadata)
        elif song_first_slide == SongFirstSlideMode.Footer:
            mako_vars['first_slide'] = True
            first_slide = self._generate_mako_footer(mako_vars, False)  # Avoiding show message error box twice
            first_slide = first_slide if first_slide is not None else '\n'.join(service_item.raw_footer)
            if replace:
                service_item.replace_slide_from_text(0, first_slide, 'O2', footer_html='', metadata=slide_metadata)
            else:
                service_item.add_from_text(first_slide, 'O2', footer_html='', metadata=slide_metadata)
            mako_vars['first_slide'] = False
        return author_list

    @staticmethod
    def _authors_match(song, authors):
        """
        Checks whether authors from a song in the database match the authors of the song to be imported.

        :param song: A list of authors from the song in the database
        :param authors: A string with authors from the song to be imported
        :return: True when Authors do match, else False.
        """
        author_list = authors.split(', ')
        for author in song.authors:
            if author.display_name in author_list:
                author_list.remove(author.display_name)
            else:
                return False
        # List must be empty at the end
        return not author_list

    @QtCore.Slot(str, bool, result=list)
    def search(self, string: str, show_error: bool = True) -> list[list[Any]]:
        """
        Search for some songs
        :param string: The string to show
        :param show_error: Is this an error?
        :return: the results of the search
        """
        search_results = self.search_entire(string)
        return [[song.id, song.title, song.alternate_title] for song in search_results]
