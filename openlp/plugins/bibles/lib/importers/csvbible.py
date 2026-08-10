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
The :mod:`cvsbible` modules provides a facility to import bibles from a set of CSV files.

The module expects two mandatory files containing the books and the verses.

The format of the books file is:

    <book_id>,<testament_id>,<book_name>,<book_abbreviation>

    For example

        1,1,Genesis,Gen
        2,1,Exodus,Exod
        ...
        40,2,Matthew,Matt

There are two acceptable formats of the verses file.  They are:

    <book_id>,<chapter_number>,<verse_number>,<verse_text>
    or
    <book_name>,<chapter_number>,<verse_number>,<verse_text>

    For example:

        1,1,1,"In the beginning God created the heaven and the earth."
        or
        "Genesis",1,2,"And the earth was without form, and void; and...."

All CSV files are expected to use a comma (',') as the delimiter and double quotes ('"') as the quote symbol.
"""
from enum import Enum
import logging
from collections import namedtuple
from csv import Error as CSVError, reader
from typing import Type, Union, Optional
from pathlib import Path

from openlp.core.common import get_file_encoding
from openlp.core.common.i18n import translate
from openlp.core.lib.exceptions import ValidationError
from openlp.plugins.bibles.lib.bibleimport import BibleImport

log = logging.getLogger(__name__)

Book = namedtuple('Book', 'id, testament_id, name, abbreviation')
Verse = namedtuple('Verse', 'book_id_name, chapter_number, number, text')


class CSVBibleFileType(str, Enum):
    Book = 'book'
    Verse = 'verse'


def _has_header(sample: str, file_type: CSVBibleFileType) -> bool:
    """Determine if the sample of a csv file has a header line"""
    if '\r\n' in sample:
        lines = sample.split('\r\n')
    else:
        lines = sample.split('\n')
    row_1 = lines[0].split(',')
    row_2 = lines[1].split(',')
    if file_type == CSVBibleFileType.Book and all([row_2[0].isdigit(),
                                                   row_2[1].isdigit()]) and not all([row_1[0].isdigit(),
                                                                                     row_1[1].isdigit()]):
        return True
    elif file_type == CSVBibleFileType.Verse and all([row_2[1].isdigit(),
                                                      row_2[2].isdigit()]) and not all([row_1[1].isdigit(),
                                                                                        row_1[2].isdigit()]):
        return True
    return False


class CSVBible(BibleImport):
    """
    This class provides a specialisation for importing of CSV Bibles.
    """
    def __init__(self, *args, **kwargs):
        """
        Loads a Bible from a set of CSV files. This class assumes the files contain all the information and a clean
        bible is being loaded.
        """
        super().__init__(*args, **kwargs)
        self.log_info(self.__class__.__name__)
        self.books_path = kwargs['books_path']
        self.verses_path = kwargs['verse_path']

    @staticmethod
    def get_book_name(name, books):
        """
        Normalize a book name or id.

        :param name: The name, or id of a book. Str
        :param books: A dict of books parsed from the books file.
        :return: The normalized name. Str
        """
        try:
            book_name = books[int(name)]
        except ValueError:
            book_name = name
        return book_name

    @staticmethod
    def parse_csv_file(
        file_path: Path,
        results_tuple: Type[Union[Book, Verse]],
        file_type: CSVBibleFileType
    ) -> list[Union[Book, Verse]]:
        """
        Parse the supplied CSV file.

        :param pathlib.Path file_path: The name of the file to parse.
        :param namedtuple results_tuple: The namedtuple to use to store the results.
        :param CSVBibleFileType file_type: Specifies if its a book file or verses file.
        :return: An list of namedtuples of type results_tuple
        :rtype: list[namedtuple]
        """
        try:
            encoding = get_file_encoding(file_path)
            with file_path.open('r', encoding=encoding, newline='') as csv_file:
                # Grab a sample from the file, and rewind to the beginning
                sample = csv_file.read(4096)
                csv_file.seek(0)
                # Create the reader
                csv_reader = reader(csv_file, delimiter=',', quotechar='"')
                # Determine if the CSV has a header and skip if necessary
                if _has_header(sample, file_type):
                    print("has_header")
                    next(csv_reader)
                return [results_tuple(*line) for line in csv_reader]
        except (OSError, CSVError, TypeError, UnicodeDecodeError, ValueError):
            log.exception('Parsing {file} failed.'.format(file=file_path))
            raise ValidationError(msg='Parsing "{file}" failed'.format(file=file_path))

    def process_books(self, books: list[Book]) -> dict:
        """
        Process the books parsed from the books file.

        :param books: An a list Book namedtuples
        :return: A dict of books or None
        """
        book_list = {}
        number_of_books = len(books)
        for book in books:
            if self.stop_import_flag:
                break
            self.wizard.increment_progress_bar(
                translate('BiblesPlugin.CSVBible', 'Importing books... {book}').format(book=book.name))
            self.find_and_create_book(book.name, number_of_books, self.language_id)
            book_list.update({int(book.id): book.name})
        return book_list

    def process_verses(self, verses: list[Verse], books: dict):
        """
        Process the verses parsed from the verses file.

        :param verses: A list of Verse namedtuples
        :param books: A dict of books
        :return: None
        """
        book_ptr = None
        for verse in verses:
            if self.stop_import_flag:
                break
            verse_book = self.get_book_name(verse.book_id_name, books)
            if book_ptr != verse_book:
                book = self.get_book(verse_book)
                book_ptr = book.name
                self.wizard.increment_progress_bar(
                    translate('BiblesPlugin.CSVBible', 'Importing verses from {book}...',
                              'Importing verses from <book name>...').format(book=book.name))
                self.session.commit()
            self.create_verse(book.id, int(verse.chapter_number), int(verse.number), verse.text)
        self.session.commit()

    def do_import(self, bible_name: Optional[str] = None):
        """
        Import a bible from the CSV files.

        :param bible_name: Optional name of the bible being imported. Str or None
        :return: True if the import was successful, False if it failed or was cancelled
        """
        self.clear_import_failure()
        self.language_id = self.get_language(bible_name)
        if not self.language_id:
            return False
        try:
            books: list[Book] = self.parse_csv_file(self.books_path, Book, CSVBibleFileType.Book)
        except ValidationError:
            self.set_import_failure(
                code='csv-books-parse-failed',
                summary=translate('BiblesPlugin.CSVBible', 'Books CSV file could not be parsed.'),
                details=translate('BiblesPlugin.CSVBible',
                                  'OpenLP could not parse the selected books file: {file}').format(
                    file=self.books_path
                ),
                actions=(
                    translate('BiblesPlugin.CSVBible',
                              'Ensure the books file is a valid CSV file using comma-separated columns.'),
                )
            )
            return False
        if not books:
            self.set_import_failure(
                code='csv-books-empty',
                summary=translate('BiblesPlugin.CSVBible', 'Books CSV file has no importable rows.'),
                actions=(
                    translate('BiblesPlugin.CSVBible', 'Verify the books file contains Bible book rows.'),
                )
            )
            return False
        self.wizard.progress_bar.setValue(0)
        self.wizard.progress_bar.setMinimum(0)
        self.wizard.progress_bar.setMaximum(len(books))
        book_list = self.process_books(books)
        try:
            verses: list[Verse] = self.parse_csv_file(self.verses_path, Verse, CSVBibleFileType.Verse)
        except ValidationError:
            self.set_import_failure(
                code='csv-verses-parse-failed',
                summary=translate('BiblesPlugin.CSVBible', 'Verses CSV file could not be parsed.'),
                details=translate('BiblesPlugin.CSVBible',
                                  'OpenLP could not parse the selected verses file: {file}').format(
                    file=self.verses_path
                ),
                actions=(
                    translate('BiblesPlugin.CSVBible',
                              'Ensure the verses file is valid CSV with book, chapter, verse, and text columns.'),
                )
            )
            return False
        if not verses:
            self.set_import_failure(
                code='csv-verses-empty',
                summary=translate('BiblesPlugin.CSVBible', 'Verses CSV file has no importable rows.'),
                actions=(
                    translate('BiblesPlugin.CSVBible', 'Verify the verses file contains verse data rows.'),
                )
            )
            return False
        self.wizard.progress_bar.setValue(0)
        self.wizard.progress_bar.setMaximum(len(books) + 1)
        self.process_verses(verses, book_list)
        return True
