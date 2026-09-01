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
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, List, Optional, Tuple

import chardet
from PySide6 import QtCore
from sqlalchemy import Column, ForeignKey, func, or_
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, declarative_base, relationship
from sqlalchemy.types import Unicode, UnicodeText, Integer

from openlp.core.common import clean_filename
from openlp.core.common.applocation import AppLocation
from openlp.core.common.enum import LanguageSelection
from openlp.core.common.i18n import translate
from openlp.core.db.helpers import init_db
from openlp.core.db.manager import DBManager
from openlp.core.lib.ui import critical_error_message_box
from openlp.plugins.bibles.lib import BibleStrings, upgrade

log = logging.getLogger(__name__)

RESERVED_CHARACTERS = '\\.^$*+?{}[]()'


class BibleDB(DBManager):
    """
    This class represents a database-bound Bible. It is used as a base class for all the custom importers, so that
    the can implement their own import methods, but benefit from the database methods in here via inheritance,
    rather than depending on yet another object.
    """
    log.info('BibleDB loaded')

    def __init__(self, parent, **kwargs):
        """
        The constructor loads up the database and creates and initialises the
        tables if the database doesn't exist.

        :param parent:
        :param kwargs:
            ``path``
                The path to the bible database file. Type: Path

            ``name``
                The name of the database. This is also used as the file name for SQLite databases.

            ``file``
                Type: Path

        :rtype: None
        """
        log.info('BibleDB loaded')
        self._setup(parent, **kwargs)

    def _setup(self, parent, **kwargs):
        """
        Run some initial setup. This method is separate from __init__ in order to mock it out in tests.
        """
        self.bible_plugin = parent
        self.session = None
        if 'path' not in kwargs:
            raise KeyError('Missing keyword argument "path".')
        self.path = kwargs['path']
        if 'name' not in kwargs and 'file' not in kwargs:
            raise KeyError('Missing keyword argument "name" or "file".')
        if 'name' in kwargs:
            self.name = kwargs['name']
            if not isinstance(self.name, str):
                self.name = str(self.name, 'utf-8')
            self.file_path = Path(clean_filename(self.name) + '.sqlite')
        if 'file' in kwargs:
            self.file_path = kwargs['file']
        DBManager.__init__(self, 'bibles', self.init_schema, self.file_path, upgrade)
        if self.session and 'file' in kwargs:
            self.get_name()
        self._is_web_bible = None

    def init_schema(self, url: str) -> Session:
        """
        Setup a bible database connection and initialise the database schema.

        Due to the fact that we have to set up separate ``Base`` classes for each database, all the models are declared
        here. They can be subsequently referenced via ``self.ModelName`` or ``bible.ModelName``.

        :param url: The database to setup.
        """
        Base = declarative_base()

        class BibleMeta(Base):
            """
            Bible Meta Data
            """
            __tablename__ = 'metadata'

            key = Column(Unicode(255), primary_key=True, index=True)
            value = Column(Unicode(255))

        class Book(Base):
            """
            Bible Book model
            """
            __tablename__ = 'book'

            id = Column(Integer, primary_key=True)
            book_reference_id = Column(Integer, index=True)
            testament_reference_id = Column(Integer)
            name = Column(Unicode(50), index=True)

            verses = relationship('Verse', back_populates='book')

            def get_name(self, language_selection=LanguageSelection.Bible) -> str:
                if language_selection == LanguageSelection.Bible:
                    return self.name
                elif language_selection == LanguageSelection.Application:
                    return BibleStrings().BookNames[
                        BiblesResourcesDB.get_book_by_id(self.book_reference_id)['abbreviation']
                    ]
                elif language_selection == LanguageSelection.English:
                    return BiblesResourcesDB.get_book_by_id(self.book_reference_id)['name']

        class Verse(Base):
            """
            Topic model
            """
            __tablename__ = 'verse'

            id = Column(Integer, primary_key=True, index=True)
            book_id = Column(Integer, ForeignKey('book.id'), index=True)
            chapter = Column(Integer, index=True)
            verse = Column(Integer, index=True)
            text = Column(UnicodeText, index=True)

            book = relationship('Book', back_populates='verses')

        # Assign the classes so that they can be used elsewhere in the BibleDB class
        self.BibleMeta = BibleMeta
        self.Book = Book
        self.Verse = Verse

        session, metadata = init_db(url, base=Base)
        metadata.create_all(bind=metadata.bind, checkfirst=True)
        return session

    def get_name(self) -> str:
        """
        Returns the version name of the Bible.
        """
        version_name = self.get_object(self.BibleMeta, 'name')
        self.name = version_name.value if version_name else None
        return self.name

    def create_book(self, name: str, bk_ref_id: str, testament: int = 1):
        """
        Add a book to the database.

        :param name: The name of the book.
        :param bk_ref_id: The book_reference_id from bibles_resources.sqlite of the book.
        :param testament: *Defaults to 1.* The testament_reference_id from
            bibles_resources.sqlite of the testament this book belongs to.
        """
        log.debug('BibleDB.create_book("{name}", "{number}")'.format(name=name, number=bk_ref_id))
        book = self.Book(name=name, book_reference_id=bk_ref_id, testament_reference_id=testament)
        self.save_object(book)
        return book

    def update_book(self, book):
        """
        Update a book in the database.

        :param book: The book object
        """
        log.debug('BibleDB.update_book("{name}")'.format(name=book.name))
        return self.save_object(book)

    def delete_book(self, db_book) -> bool:
        """
        Delete a book from the database.

        :param db_book: The book object.
        """
        log.debug('BibleDB.delete_book("{name}")'.format(name=db_book.name))
        if self.delete_object(self.Book, db_book.id):
            return True
        return False

    def create_chapter(self, book_id: int, chapter: int, text_list: List[str]):
        """
        Add a chapter and its verses to a book.

        :param book_id: The id of the book being appended.
        :param chapter: The chapter number.
        :param text_list: A dict of the verses to be inserted. The key is the verse number, and the value is the
            verse text.
        """
        log.debug('BibleDBcreate_chapter("{number}", "{chapter}")'.format(number=book_id, chapter=chapter))
        # Text list has book and chapter as first two elements of the array.
        for verse_number, verse_text in text_list.items():
            verse = self.Verse(book_id=book_id, chapter=chapter, verse=verse_number, text=verse_text)
            self.session.add(verse)
        try:
            self.session.commit()
        except OperationalError:
            # Wait 10ms and try again (lp#1154467)
            time.sleep(0.01)
            self.session.commit()

    def create_verse(self, book_id: int, chapter: int, verse: int, text: str):
        """
        Add a single verse to a chapter.

        :param book_id: The id of the book being appended.
        :param chapter: The chapter number.
        :param verse: The verse number.
        :param text: The verse text.
        """
        if not isinstance(text, str):
            details = chardet.detect(text)
            text = str(text, details['encoding'])
        verse = self.Verse(book_id=book_id, chapter=chapter, verse=verse, text=text)
        self.session.add(verse)
        return verse

    def save_meta(self, key: str, value: Any):
        """
        Utility method to save or update BibleMeta objects in a Bible database.

        :param key: The key for this instance.
        :param value: The value for this instance.
        """
        if not isinstance(value, str):
            value = str(value)
        log.debug('BibleDB.save_meta("{key}/{val}")'.format(key=key, val=value))
        meta = self.get_object(self.BibleMeta, key)
        if meta:
            meta.value = value
            self.save_object(meta)
        else:
            self.save_object(self.BibleMeta(key=key, value=value))

    def get_book(self, book: str):
        """
        Return a book object from the database.

        :param book: The name of the book to return.
        """
        log.debug('BibleDB.get_book("{book}")'.format(book=book))
        return self.get_object_filtered(self.Book, self.Book.name.like(book + '%'))

    def get_books(self, book: Optional[str] = None):
        """
        A wrapper so both local and web bibles have a get_books() method that
        manager can call. Used in the media manager advanced search tab.
        """
        log.debug('BibleDB.get_books("{book}")'.format(book=book))
        filter = self.Book.name.like(book + '%') if book else None
        return self.get_all_objects(self.Book, filter_clause=filter, order_by_ref=self.Book.id)

    def get_book_by_book_ref_id(self, ref_id: str):
        """
        Return a book object from the database.

        :param ref_id: The reference id of the book to return.
        """
        log.debug('BibleDB.get_book_by_book_ref_id("{ref}")'.format(ref=ref_id))
        return self.get_object_filtered(self.Book, self.Book.book_reference_id.like(ref_id))

    def get_book_ref_id_by_localised_name(self, book: str, language_selection):
        """
        Return the ids of a matching named book.

        :param book: The name of the book, according to the selected language.
        :param language_selection:  The language selection the user has chosen in the settings section of the Bible.
        :rtype: list[int]
        """
        log.debug('get_book_ref_id_by_localised_name("{book}", "{lang}")'.format(book=book, lang=language_selection))
        from openlp.core.common.enum import LanguageSelection
        from openlp.plugins.bibles.lib import BibleStrings
        book_names = BibleStrings().BookNames
        # escape reserved characters
        for character in RESERVED_CHARACTERS:
            book_escaped = book.replace(character, '\\' + character)
        regex_book = re.compile('\\s*{book}\\s*'.format(book='\\s*'.join(book_escaped.split())), re.IGNORECASE)
        if language_selection == LanguageSelection.Bible:
            db_books = self.get_books(book)
            return [db_book.book_reference_id for db_book in db_books]
        else:
            book_list = []
            if language_selection == LanguageSelection.Application:
                books = [key for key in list(book_names.keys()) if regex_book.match(book_names[key])]
                book_list = [_f for _f in map(BiblesResourcesDB.get_book, books) if _f]
            elif language_selection == LanguageSelection.English:
                books = BiblesResourcesDB.get_books_like(book)
                if books:
                    book_list = [value for value in books if regex_book.match(value['name'])]
                    if not book_list:
                        book_list = books
            return [value['id'] for value in book_list if self.get_book_by_book_ref_id(value['id'])]

    def get_verses(self, reference_list: List[Tuple[str, int, int, int]], show_error: bool = True):
        """
        This is probably the most used function. It retrieves the list of
        verses based on the user's query.

        :param reference_list: This is the list of references the media manager item wants. It is a list of tuples, with
            the following format::

                (book_reference_id, chapter, start_verse, end_verse)

            Therefore, when you are looking for multiple items, simply break them up into references like this, bundle
            them into a list. This function then runs through the list, and returns an amalgamated list of ``Verse``
            objects. For example::

                [('35', 1, 1, 1), ('35', 2, 2, 3)]
        :param show_error:
        """
        log.debug('BibleDB.get_verses("{ref}")'.format(ref=reference_list))
        verse_list = []
        book_error = False
        for book_id, chapter, start_verse, end_verse in reference_list:
            db_book = self.get_book_by_book_ref_id(book_id)
            if db_book:
                book_id = db_book.book_reference_id
                log.debug('Book name corrected to "{book}"'.format(book=db_book.name))
                if end_verse == -1:
                    end_verse = self.get_verse_count(book_id, chapter)
                verses = self.session.query(self.Verse) \
                    .filter_by(book_id=db_book.id) \
                    .filter_by(chapter=chapter) \
                    .filter(self.Verse.verse >= start_verse) \
                    .filter(self.Verse.verse <= end_verse) \
                    .order_by(self.Verse.verse) \
                    .all()
                verse_list.extend(verses)
            else:
                log.debug('OpenLP failed to find book with id "{book}"'.format(book=book_id))
                book_error = True
        if book_error and show_error:
            critical_error_message_box(
                translate('BiblesPlugin', 'No Book Found'),
                translate('BiblesPlugin', 'No matching book '
                                          'could be found in this Bible. Check that you have spelled the name of the book correctly.'))
        return verse_list

    def verse_search(self, text: str):
        """
        Search for verses containing text ``text``.

        :param text:
            The text to search for. If the text contains commas, it will be
            split apart and OR'd on the list of values. If the text just
            contains spaces, it will split apart and AND'd on the list of
            values.
        """
        log.debug('BibleDB.verse_search("{text}")'.format(text=text))
        verses = self.session.query(self.Verse)
        if text.find(',') > -1:
            keywords = ['%{keyword}%'.format(keyword=keyword.strip()) for keyword in text.split(',') if keyword.strip()]
            or_clause = [self.Verse.text.like(keyword) for keyword in keywords]
            verses = verses.filter(or_(*or_clause))
        else:
            keywords = ['%{keyword}%'.format(keyword=keyword.strip()) for keyword in text.split(' ') if keyword.strip()]
            for keyword in keywords:
                verses = verses.filter(self.Verse.text.like(keyword))
        verses = verses.all()
        return verses

    def get_chapter_count(self, book) -> int:
        """
        Return the number of chapters in a book.

        :param book: The book object to get the chapter count for.
        """
        log.debug('BibleDB.get_chapter_count("{book}")'.format(book=book.name))
        count = self.session.query(func.max(self.Verse.chapter)).join(self.Book).filter(
            self.Book.book_reference_id == book.book_reference_id).scalar()
        if not count:
            return 0
        return count

    def get_verse_count(self, book_ref_id: str, chapter: int) -> int:
        """
        Return the number of verses in a chapter.

        :param book_ref_id: The book reference id.
        :param chapter: The chapter to get the verse count for.
        """
        log.debug('BibleDB.get_verse_count("{ref}", "{chapter}")'.format(ref=book_ref_id, chapter=chapter))
        count = self.session.query(func.max(self.Verse.verse)).join(self.Book) \
            .filter(self.Book.book_reference_id == book_ref_id) \
            .filter(self.Verse.chapter == chapter) \
            .scalar()
        if not count:
            return 0
        return count

    @property
    def is_web_bible(self) -> bool:
        """
        A read only property indicating if the bible is a 'web bible'

        :return: If the bible is a web bible.
        :rtype: bool
        """
        if self._is_web_bible is None:
            self._is_web_bible = bool(self.get_object(self.BibleMeta, 'download_source'))
        return self._is_web_bible


class BiblesResourcesDB(QtCore.QObject):
    """
    This class represents the database-bound Bible Resources. It provide
    some resources which are used in the Bibles plugin.
    A wrapper class around a small SQLite database which contains the download
    resources, a biblelist from the different download resources, the books,
    chapter counts and verse counts for the web download Bibles, a language
    reference, the testament reference and some alternative book names. This
    class contains a singleton "cursor" so that only one connection to the
    SQLite database is ever used.
    """
    cursor = None

    @staticmethod
    def get_cursor():
        """
        Return the cursor object. Instantiate one if it doesn't exist yet.
        """
        if BiblesResourcesDB.cursor is None:
            file_path = \
                AppLocation.get_directory(AppLocation.PluginsDir) / 'bibles' / 'resources' / 'bibles_resources.sqlite'
            conn = sqlite3.connect(str(file_path))
            BiblesResourcesDB.cursor = conn.cursor()
        return BiblesResourcesDB.cursor

    @staticmethod
    def run_sql(query, parameters=()):
        """
        Run an SQL query on the database, returning the results.

        ``query``
            The actual SQL query to run.

        ``parameters``
            Any variable parameters to add to the query.
        """
        cursor = BiblesResourcesDB.get_cursor()
        cursor.execute(query, parameters)
        return cursor.fetchall()

    @staticmethod
    def get_books():
        """
        Return a list of all the books of the Bible.
        """
        log.debug('BiblesResourcesDB.get_books()')
        books = BiblesResourcesDB.run_sql(
            'SELECT id, testament_id, name, abbreviation, chapters FROM book_reference ORDER BY id')
        return [{
            'id': book[0],
            'testament_id': book[1],
            'name': str(book[2]),
            'abbreviation': str(book[3]),
            'chapters': book[4]
        } for book in books]

    @staticmethod
    def get_book(name, lower=False):
        """
        Return a book by name or abbreviation.

        :param name: The name or abbreviation of the book.
        :param lower: True if the comparison should be only lowercase
        """
        log.debug('BiblesResourcesDB.get_book("{name}")'.format(name=name))
        if not isinstance(name, str):
            name = str(name)
        if lower:
            books = BiblesResourcesDB.run_sql(
                'SELECT id, testament_id, name, abbreviation, chapters FROM book_reference WHERE '
                'LOWER(name) = ? OR LOWER(abbreviation) = ?', (name.lower(), name.lower()))
        else:
            books = BiblesResourcesDB.run_sql(
                'SELECT id, testament_id, name, abbreviation, chapters FROM book_reference WHERE name = ?'
                ' OR abbreviation = ?', (name, name))
        if books:
            return {
                'id': books[0][0],
                'testament_id': books[0][1],
                'name': str(books[0][2]),
                'abbreviation': str(books[0][3]),
                'chapters': books[0][4]
            }
        else:
            return None

    @staticmethod
    def get_books_like(string):
        """
        Return the books which include string.

        :param string: The string to search for in the book names or abbreviations.
        """
        log.debug('BiblesResourcesDB.get_book_like("{text}")'.format(text=string))
        if not isinstance(string, str):
            string = str(string)
        books = BiblesResourcesDB.run_sql(
            'SELECT id, testament_id, name, abbreviation, chapters FROM book_reference WHERE '
            'LOWER(name) LIKE ? OR LOWER(abbreviation) LIKE ?',
            ('%' + string.lower() + '%', '%' + string.lower() + '%'))
        if books:
            return [{
                'id': book[0],
                'testament_id': book[1],
                'name': str(book[2]),
                'abbreviation': str(book[3]),
                'chapters': book[4]
            } for book in books]
        else:
            return None

    @staticmethod
    def get_book_by_id(book_id):
        """
        Return a book by id.

        :param book_id: The id of the book.
        """
        log.debug('BiblesResourcesDB.get_book_by_id("{book}")'.format(book=book_id))
        if not isinstance(book_id, int):
            book_id = int(book_id)
        books = BiblesResourcesDB.run_sql(
            'SELECT id, testament_id, name, abbreviation, chapters FROM book_reference WHERE id = ?', (book_id,))
        if books:
            return {
                'id': books[0][0],
                'testament_id': books[0][1],
                'name': str(books[0][2]),
                'abbreviation': str(books[0][3]),
                'chapters': books[0][4]
            }
        else:
            return None

    @staticmethod
    def get_chapter(book_ref_id, chapter):
        """
        Return the chapter details for a specific chapter of a book.

        :param book_ref_id: The id of a book.
        :param chapter: The chapter number.
        """
        log.debug('BiblesResourcesDB.get_chapter("{book}", "{ref}")'.format(book=book_ref_id, ref=chapter))
        if not isinstance(chapter, int):
            chapter = int(chapter)
        chapters = BiblesResourcesDB.run_sql(
            'SELECT id, book_reference_id, '
            'chapter, verse_count FROM chapters WHERE book_reference_id = ?', (book_ref_id,))
        try:
            return {
                'id': chapters[chapter - 1][0],
                'book_reference_id': chapters[chapter - 1][1],
                'chapter': chapters[chapter - 1][2],
                'verse_count': chapters[chapter - 1][3]
            }
        except (IndexError, TypeError):
            return None

    @staticmethod
    def get_chapter_count(book_ref_id):
        """
        Return the number of chapters in a book.

        :param book_ref_id: The id of the book.
        """
        log.debug('BiblesResourcesDB.get_chapter_count("{ref}")'.format(ref=book_ref_id))
        details = BiblesResourcesDB.get_book_by_id(book_ref_id)
        if details:
            return details['chapters']
        return 0

    @staticmethod
    def get_verse_count(book_ref_id, chapter):
        """
        Return the number of verses in a chapter.

        :param book_ref_id: The id of the book.
        :param chapter: The number of the chapter.
        """
        log.debug('BiblesResourcesDB.get_verse_count("{ref}", "{chapter}")'.format(ref=book_ref_id, chapter=chapter))
        details = BiblesResourcesDB.get_chapter(book_ref_id, chapter)
        if details:
            return details['verse_count']
        return 0

    @staticmethod
    def get_download_source(source):
        """
        Return a download_source_id by source.

        :param source: The name or abbreviation of the book.
        """
        log.debug('BiblesResourcesDB.get_download_source("{source}")'.format(source=source))
        if not isinstance(source, str):
            source = str(source)
        source = source.title()
        dl_source = BiblesResourcesDB.run_sql(
            'SELECT id, source FROM download_source WHERE source = ?', (source.lower(),))
        if dl_source:
            return {
                'id': dl_source[0][0],
                'source': dl_source[0][1]
            }
        else:
            return None

    @staticmethod
    def get_webbibles(source):
        """
        Return the bibles a web_bible provide for download.

        :param source: The source of the web_bible.
        """
        log.debug('BiblesResourcesDB.get_webbibles("{source}")'.format(source=source))
        if not isinstance(source, str):
            source = str(source)
        source = BiblesResourcesDB.get_download_source(source)
        bibles = BiblesResourcesDB.run_sql('SELECT id, name, abbreviation, language_id, download_source_id '
                                           'FROM webbibles WHERE download_source_id = ?', (source['id'],))
        if bibles:
            return [{
                'id': bible[0],
                'name': bible[1],
                'abbreviation': bible[2],
                'language_id': bible[3],
                'download_source_id': bible[4]
            } for bible in bibles]
        else:
            return None

    @staticmethod
    def get_alternative_book_name(name, language_id=None):
        """
        Return a book_reference_id if the name matches.

        :param name: The name to search the id.
        :param language_id: The language_id for which language should be searched
        """
        log.debug('BiblesResourcesDB.get_alternative_book_name("{name}", "{lang}")'.format(name=name, lang=language_id))
        if language_id:
            books = BiblesResourcesDB.run_sql(
                'SELECT book_reference_id, name FROM alternative_book_names WHERE language_id = ? ORDER BY id',
                (language_id,))
        else:
            books = BiblesResourcesDB.run_sql('SELECT book_reference_id, name FROM alternative_book_names ORDER BY id')
        for book in books:
            if book[1].lower() == name.lower():
                return book[0]
        return None

    @staticmethod
    def get_testament_reference():
        """
        Return a list of all testaments and their id of the Bible.
        """
        log.debug('BiblesResourcesDB.get_testament_reference()')
        testaments = BiblesResourcesDB.run_sql('SELECT id, name FROM testament_reference ORDER BY id')
        return [
            {'id': testament[0],
             'name': str(testament[1])
             }
            for testament in testaments
        ]


class AlternativeBookNamesDB(object):
    """
    This class represents a database-bound alternative book names system.
    """
    cursor = None
    conn = None

    @staticmethod
    def get_cursor():
        """
        Return the cursor object. Instantiate one if it doesn't exist yet.
        If necessary loads up the database and creates the tables if the database doesn't exist.
        """
        if AlternativeBookNamesDB.cursor is None:
            file_path = AppLocation.get_section_data_path('bibles') / 'alternative_book_names.sqlite'
            exists = file_path.exists()
            AlternativeBookNamesDB.conn = sqlite3.connect(str(file_path))
            if not exists:
                # create new DB, create table alternative_book_names
                AlternativeBookNamesDB.conn.execute(
                    'CREATE TABLE alternative_book_names(id INTEGER NOT NULL, '
                    'book_reference_id INTEGER, language_id INTEGER, name VARCHAR(50), PRIMARY KEY (id))')
            AlternativeBookNamesDB.cursor = AlternativeBookNamesDB.conn.cursor()
        return AlternativeBookNamesDB.cursor

    @staticmethod
    def run_sql(query, parameters=(), commit=None):
        """
        Run an SQL query on the database, returning the results.

        :param query: The actual SQL query to run.
        :param parameters: Any variable parameters to add to the query
        :param commit: If a commit statement is necessary this should be True.
        """
        cursor = AlternativeBookNamesDB.get_cursor()
        cursor.execute(query, parameters)
        if commit:
            AlternativeBookNamesDB.conn.commit()
        return cursor.fetchall()

    @staticmethod
    def get_book_reference_id(name, language_id=None):
        """
        Return a book_reference_id if the name matches.

        :param name: The name to search the id.
        :param language_id: The language_id for which language should be searched
        """
        log.debug('AlternativeBookNamesDB.get_book_reference_id("{name}", "{ref}")'.format(name=name, ref=language_id))
        if language_id:
            books = AlternativeBookNamesDB.run_sql(
                'SELECT book_reference_id, name FROM alternative_book_names WHERE language_id = ?', (language_id,))
        else:
            books = AlternativeBookNamesDB.run_sql(
                'SELECT book_reference_id, name FROM alternative_book_names')
        for book in books:
            if book[1].lower() == name.lower():
                return book[0]
        return None

    @staticmethod
    def create_alternative_book_name(name, book_reference_id, language_id):
        """
        Add an alternative book name to the database.

        :param name:  The name of the alternative book name.
        :param book_reference_id: The book_reference_id of the book.
        :param language_id: The language to which the alternative book name belong.
        """
        log.debug('AlternativeBookNamesDB.create_alternative_book_name("{name}", '
                  '"{ref}", "{lang}")'.format(name=name, ref=book_reference_id, lang=language_id))
        return AlternativeBookNamesDB.run_sql(
            'INSERT INTO alternative_book_names(book_reference_id, language_id, name) '
            'VALUES (?, ?, ?)', (book_reference_id, language_id, name), True)
