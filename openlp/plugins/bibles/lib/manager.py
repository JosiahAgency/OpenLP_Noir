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
import gc
import logging
from pathlib import Path

from openlp.core.common import delete_file
from openlp.core.common.enum import LanguageSelection
from openlp.core.common.applocation import AppLocation
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.mixins import LogMixin, RegistryProperties
from openlp.core.common.registry import Registry
from openlp.plugins.bibles.lib import parse_reference
from openlp.plugins.bibles.lib.db import BibleDB

from .importers.csvbible import CSVBible
from .importers.http import HTTPBible
from .importers.opensong import OpenSongBible
from .importers.osis import OSISBible
from .importers.wordproject import WordProjectBible
from .importers.zefania import ZefaniaBible


try:
    from .importers.sword import SwordBible
except ImportError:
    pass

log = logging.getLogger(__name__)


class BibleFormat(object):
    """
    This is a special enumeration class that holds the various types of Bibles.
    """
    Unknown = -1
    OSIS = 0
    CSV = 1
    OpenSong = 2
    WebDownload = 3
    Zefania = 4
    SWORD = 5
    WordProject = 6

    @staticmethod
    def get_class(bible_format):
        """
        Return the appropriate implementation class.

        :param bible_format: The Bible format.
        """
        if bible_format == BibleFormat.OSIS:
            return OSISBible
        elif bible_format == BibleFormat.CSV:
            return CSVBible
        elif bible_format == BibleFormat.OpenSong:
            return OpenSongBible
        elif bible_format == BibleFormat.WebDownload:
            return HTTPBible
        elif bible_format == BibleFormat.Zefania:
            return ZefaniaBible
        elif bible_format == BibleFormat.SWORD:
            return SwordBible
        elif bible_format == BibleFormat.WordProject:
            return WordProjectBible
        else:
            return None


class BibleManager(LogMixin, RegistryProperties):
    """
    The Bible manager which holds and manages all the Bibles.
    """
    log.info('Bible manager loaded')

    def __init__(self, parent):
        """
        Finds all the bibles defined for the system and creates an interface object for each bible containing
        connection information. Throws Exception if no Bibles are found.

        Init confirms the bible exists and stores the database path.
        """
        log.debug('Bible Initialising')
        self.parent = parent

        self.web = 'Web'
        self.db_cache = None
        self.path = AppLocation.get_section_data_path('bibles')
        self.suffix = '.sqlite'
        self.import_wizard = None
        self.reload_bibles()
        self.media = None

    def reload_bibles(self):
        """
        Reloads the Bibles from the available Bible databases on disk. If a web Bible is encountered, an instance
        of HTTPBible is loaded instead of the BibleDB class.
        """
        log.debug('Reload bibles')
        file_paths = AppLocation.get_files('bibles', self.suffix)
        if Path('alternative_book_names.sqlite') in file_paths:
            file_paths.remove(Path('alternative_book_names.sqlite'))
        log.debug('Bible Files {text}'.format(text=file_paths))
        self.db_cache = {}
        for file_path in file_paths:
            bible = BibleDB(self.parent, path=self.path, file=file_path)
            if not bible.session:
                continue
            name = bible.get_name()
            # Remove corrupted files.
            if name is None:
                bible.session.close()
                bible.session = None
                gc.collect()
                delete_file(self.path / file_path)
                continue
            log.debug('Bible Name: "{name}"'.format(name=name))
            self.db_cache[name] = bible
            # Look to see if lazy load bible exists and get create getter.
            if self.db_cache[name].is_web_bible:
                source = self.db_cache[name].get_object(bible.BibleMeta, 'download_source')
                download_name_meta = self.db_cache[name].get_object(bible.BibleMeta, 'download_name')
                if download_name_meta is None:
                    # Corrupted or incomplete web bible database; missing required metadata.
                    log.warning('Web bible "{name}" is missing its "download_name" metadata, '
                               'removing corrupted file'.format(name=name))
                    del self.db_cache[name]
                    bible.session.close()
                    bible.session = None
                    gc.collect()
                    delete_file(self.path / file_path)
                    continue
                web_bible = HTTPBible(self.parent, path=self.path, file=file_path, download_source=source.value,
                                      download_name=download_name_meta.value)
                self.db_cache[name] = web_bible
        log.debug('Bibles reloaded')

    def set_process_dialog(self, wizard):
        """
        Sets the reference to the dialog with the progress bar on it.

        :param wizard: The reference to the import wizard.
        """
        self.import_wizard = wizard

    def import_bible(self, type, **kwargs):
        """
        Register a bible in the bible cache, and then import the verses.

        :param type: What type of Bible, one of the ``BibleFormat`` values.
        :param kwargs: Keyword arguments to send to the actual importer class.
        """
        class_ = BibleFormat.get_class(type)
        kwargs['path'] = self.path
        importer = class_(self.parent, **kwargs)
        name = importer.register(self.import_wizard)
        self.db_cache[name] = importer
        return importer

    def delete_bible(self, name):
        """
        Delete a bible completely.

        :param name: The name of the bible.
        """
        log.debug('BibleManager.delete_bible("{name}")'.format(name=name))
        bible = self.db_cache[name]
        bible.session.close()
        bible.session = None
        gc.collect()
        if bible.file_path:
            bible_path = bible.path / bible.file_path
        else:
            bible_path = bible.path / f'{bible.name}{self.suffix}'
        return delete_file(bible_path)

    def get_bibles(self):
        """
        Returns a dict with all available Bibles.
        """
        log.debug('get_bibles')
        return self.db_cache

    def get_books(self, bible):
        """
        Returns a list of Bible books, and the number of chapters in that book.

        :param bible: Unicode. The Bible to get the list of books from.
        """
        log.debug('BibleManager.get_books("{bible}")'.format(bible=bible))
        return [
            {
                'name': book.name,
                'book_reference_id': book.book_reference_id,
                'chapters': self.db_cache[bible].get_chapter_count(book)
            }
            for book in self.db_cache[bible].get_books()
        ]

    def get_book_by_id(self, bible, id):
        """
        Returns a book object by given id.

        :param bible: Unicode. The Bible to get the list of books from.
        :param id: Unicode. The book_reference_id to get the book for.
        """
        log.debug('BibleManager.get_book_by_id("{bible}", "{ref}")'.format(bible=bible, ref=id))
        return self.db_cache[bible].get_book_by_book_ref_id(id)

    def get_chapter_count(self, bible, book):
        """
        Returns the number of Chapters for a given book.

        :param bible: Unicode. The Bible to get the list of books from.
        :param book: The book object to get the chapter count for.
        """
        log.debug('BibleManager.get_book_chapter_count ("{bible}", "{name}")'.format(bible=bible, name=book.name))
        return self.db_cache[bible].get_chapter_count(book)

    def get_verse_count(self, bible, book, chapter):
        """
        Returns all the number of verses for a given book and chapterMaxBibleBookVerses.
        """
        log.debug('BibleManager.get_verse_count("{bible}", "{book}", {chapter})'.format(bible=bible,
                                                                                        book=book,
                                                                                        chapter=chapter))
        language_selection = self.get_language_selection(bible)
        book_ref_ids = self.db_cache[bible].get_book_ref_id_by_localised_name(book, language_selection)
        if book_ref_ids:
            return self.db_cache[bible].get_verse_count(book_ref_ids[0], chapter)
        return 0

    def get_verse_count_by_book_ref_id(self, bible, book_ref_id, chapter):
        """
        Returns all the number of verses for a given
        book_ref_id and chapterMaxBibleBookVerses.
        """
        log.debug('BibleManager.get_verse_count_by_book_ref_id("{bible}", '
                  '"{book}", "{chapter}")'.format(bible=bible, book=book_ref_id, chapter=chapter))
        return self.db_cache[bible].get_verse_count(book_ref_id, chapter)

    def parse_ref(self, bible, reference_text, book_ref_id=False):
        if not bible:
            return
        language_selection = self.get_language_selection(bible)
        return parse_reference(reference_text, self.db_cache[bible], language_selection, book_ref_id)

    def get_verses(self, bible, ref_list, show_error=True):
        """
        Parses a scripture reference, fetches the verses from the Bible
        specified, and returns a list of ``Verse`` objects.

        :param bible: Unicode. The Bible to use.
        :param verse_text:
             String. The scripture reference. Valid scripture references are:

                - Genesis 1
                - Genesis 1-2
                - Genesis 1:1
                - Genesis 1:1-10
                - Genesis 1:1-10,15-20
                - Genesis 1:1-2:10
                - Genesis 1:1-10,2:1-10

        :param book_ref_id:  Unicode. The book reference id from the book in verse_text.
            For second bible this is necessary.
        :param show_error:
        """
        if not bible or not ref_list:
            return []
        return self.db_cache[bible].get_verses(ref_list, show_error)

    def get_language_selection(self, bible):
        """
        Returns the language selection of a bible.

        :param bible:  Unicode. The Bible to get the language selection from.
        """
        log.debug('BibleManager.get_language_selection("{bible}")'.format(bible=bible))
        language_selection = self.get_meta_data(bible, 'book_name_language')
        if not language_selection or language_selection.value == "None" or language_selection.value == "-1":
            # If None is returned, it's not the singleton object but a
            # BibleMeta object with the value "None"
            language_selection = Registry().get('settings').value('bibles/book name language')
        else:
            language_selection = language_selection.value
        try:
            language_selection = int(language_selection)
        except (ValueError, TypeError):
            language_selection = LanguageSelection.Application
        return language_selection

    def verse_search(self, bible, text):
        """
        Does a verse search for the given bible and text.

        :param str bible: The bible to search
        :param str text: The text to search for
        :return: The search results if valid, or None if the search is invalid.
        :rtype: None | list
        """
        log.debug('BibleManager.verse_search("{bible}", "{text}")'.format(bible=bible, text=text))
        if not text:
            return None
        # If no bibles are installed, message is given.
        if not bible:
            self.main_window.information_message(
                UiStrings().BibleNoBiblesTitle,
                UiStrings().BibleNoBibles)
            return None
        # Check if the bible or second_bible is a web bible.
        if self.db_cache[bible].is_web_bible:
            # If either Bible is Web, cursor is reset to normal and message is given.
            self.application.set_normal_cursor()
            self.main_window.information_message(
                translate('BiblesPlugin.BibleManager', 'Web Bible cannot be used in Text Search'),
                translate('BiblesPlugin.BibleManager', 'Text Search is not available with Web Bibles.\n'
                                                       'Please use the Scripture Reference Search instead.\n\n'
                                                       'This means that the currently selected Bible is a Web Bible.')
            )
            return None
        # Fetch the results from db. If no results are found, return None, no message is given for this.
        if text:
            return self.db_cache[bible].verse_search(text)
        else:
            return None

    def process_verse_range(self, book_ref_id, chapter_from, verse_from, chapter_to, verse_to):
        verse_ranges = []
        for chapter in range(chapter_from, chapter_to + 1):
            if chapter == chapter_from:
                start_verse = verse_from
            else:
                start_verse = 1
            if chapter == chapter_to:
                end_verse = verse_to
            else:
                end_verse = -1
            verse_ranges.append((book_ref_id, chapter, start_verse, end_verse))
        return verse_ranges

    def save_meta_data(self, bible, version, copyright, permissions, full_license, book_name_language=None):
        """
        Saves the bibles meta data.
        """
        log.debug('save_meta data {bible}, {version}, {copyright},'
                  ' {perms}, {full_license}'.format(bible=bible, version=version, copyright=copyright,
                                                    perms=permissions, full_license=full_license))
        self.db_cache[bible].save_meta('name', version)
        self.db_cache[bible].save_meta('copyright', copyright)
        self.db_cache[bible].save_meta('permissions', permissions)
        self.db_cache[bible].save_meta('full_license', full_license)
        self.db_cache[bible].save_meta('book_name_language', book_name_language)

    def get_meta_data(self, bible, key):
        """
        Returns the meta data for a given key.
        """
        log.debug('get_meta {bible},{key}'.format(bible=bible, key=key))
        bible_db = self.db_cache[bible]
        return bible_db.get_object(bible_db.BibleMeta, key)

    def update_book(self, bible, book):
        """
        Update a book of the bible.
        """
        log.debug('BibleManager.update_book("{bible}", "{name}")'.format(bible=bible, name=book.name))
        self.db_cache[bible].update_book(book)

    def exists(self, name):
        """
        Check cache to see if new bible.
        """
        if not isinstance(name, str):
            name = str(name)
        for bible in list(self.db_cache.keys()):
            log.debug('Bible from cache in is_new_bible {bible}'.format(bible=bible))
            if not isinstance(bible, str):
                bible = str(bible)
            if bible == name:
                return True
        return False

    def finalise(self):
        """
        Loop through the databases to VACUUM them.
        """
        for bible in self.db_cache:
            self.db_cache[bible].finalise()


__all__ = ['BibleFormat', 'BibleManager']
