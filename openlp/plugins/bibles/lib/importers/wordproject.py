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
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, BadZipFile

from bs4 import BeautifulSoup, NavigableString, Tag

from openlp.core.common.i18n import translate
from openlp.core.lib.ui import critical_error_message_box
from openlp.plugins.bibles.lib.bibleimport import BibleImport


BOOK_NUMBER_PATTERN = re.compile(r'\[(\d+)\]')
REPLACE_SPACES = re.compile(r'\s{2,}')

log = logging.getLogger(__name__)


class WordProjectBible(BibleImport):
    """
    `WordProject <http://www.wordproaudio.com/>`_ Bible format importer class.
    """
    def _cleanup(self):
        """
        Clean up after ourselves
        """
        self.tmp.cleanup()

    def _unzip_file(self):
        """
        Unzip the file to a temporary directory
        """
        self.tmp = TemporaryDirectory()
        try:
            with ZipFile(self.file_path) as zip_file:
                zip_file.extractall(self.tmp.name)
        except BadZipFile:
            self.log_exception('Extracting {file} failed.'.format(file=self.file_path))
            critical_error_message_box(message=translate('BiblesPlugin.WordProjectBible',
                                                         'Incorrect Bible file type, not a Zip file.'))
            return False
        self.base_path = Path(self.tmp.name, self.file_path.stem)
        return True

    def process_books(self):
        """
        Extract and create the bible books from the parsed html

        :param bible_data: parsed xml
        :return: True if books was parsed, otherwise False
        """
        idx_file = (self.base_path / 'index.htm')
        if not idx_file.exists():
            critical_error_message_box(message=translate('BiblesPlugin.WordProjectBible',
                                                         'Incorrect Bible file type, files are missing.'))
            return False
        page = idx_file.read_text(encoding='utf-8', errors='ignore')
        soup = BeautifulSoup(page, 'lxml')
        bible_books = soup.find('div', 'textOptions').find_all('li')
        book_count = len(bible_books)
        for li_book in bible_books:
            log.debug(li_book)
            if self.stop_import_flag:
                break
            if isinstance(li_book.contents[0], NavigableString) and str(li_book.contents[0]).strip():
                # Sometimes the structure is "[1] <a>Genesis</a>", and sometimes it's "<a>[1] Genesis</a>"
                book_string = str(li_book.contents[0])
                book_name = str(li_book.a.contents[0])
            elif li_book.a and ']' in li_book.a.contents[0]:
                # Sometimes there is a [1] in the link text
                book_string, book_name = str(li_book.a.contents[0]).split(' ', 1)
            elif li_book.a and 'title' in li_book.a.attrs:
                # And sometimes there's a title on the a with the number in it
                book_string = li_book.a['title'].split(' ')[0]
                book_name = li_book.a.contents[0].strip()
            else:
                continue
            book_link = li_book.a['href']
            book_id = int(BOOK_NUMBER_PATTERN.search(book_string).group(1))
            book_name = book_name.strip()
            db_book = self.find_and_create_book(book_name, book_count, self.language_id, book_id)
            self.process_chapters(db_book, book_id, book_link)
            self.session.commit()
        return True

    def process_chapters(self, db_book, book_id, book_link):
        """
        Extract the chapters, and do some initial processing of the verses

        :param book: An OpenLP bible database book object
        :param chapters: parsed chapters
        :return: None
        """
        log.debug(book_link)
        page = (self.base_path / book_link).read_text(encoding='utf-8', errors='ignore')
        soup = BeautifulSoup(page, 'lxml')
        header_div = soup.find('div', 'textHeader')
        chapters_p = header_div.find('p')
        if not chapters_p:
            log.debug('Corrupted header, searching for span instead of a p')
            chapters_p = header_div.find('span')
            if not chapters_p:
                log.debug('Cannot find chapters, using all p instead')
                chapters_p = soup.p
        log.debug(chapters_p)
        chapter_number = 0
        for item in chapters_p.contents:
            if self.stop_import_flag:
                break
            if isinstance(item, Tag) and item.name in ['a', 'span']:
                old_chapter_number = chapter_number
                chapter_number = self.get_number(item.string.strip())
                if chapter_number is None:
                    # attempt to fix a broken bible input by assuming the next chapter is just an increment
                    chapter_number = old_chapter_number + 1
                self.set_current_chapter(db_book.name, chapter_number)
                self.process_verses(db_book, book_id, chapter_number)

    def process_verses(self, db_book, book_number, chapter_number):
        """
        Get the verses for a particular book
        """
        chapter_file_path = self.base_path / '{:02d}'.format(book_number) / '{}.htm'.format(chapter_number)
        page = chapter_file_path.read_text(encoding='utf-8', errors='ignore')
        soup = BeautifulSoup(page, 'lxml')
        text_body = soup.find('div', 'textBody')
        if text_body:
            verses_p = text_body.find('p')
        else:
            verses_p = soup.find_all('p')[2]
        verse_number = 0
        verse_text = ''
        for item in verses_p.contents:
            if self.stop_import_flag:
                break
            if isinstance(item, Tag) and 'verse' in item.get('class', []):
                if verse_number > 0:
                    self.process_verse(db_book, chapter_number, verse_number, verse_text.strip())
                old_verse_number = verse_number
                verse_number = self.get_number(item.string.strip())
                if verse_number is None:
                    # attempt to fix a broken bible input by assuming the next verse is just an increment
                    verse_number = old_verse_number + 1
                verse_text = ''
            elif isinstance(item, NavigableString):
                verse_text += str(item)
            elif isinstance(item, Tag) and item.name in ['span', 'a']:
                verse_text += str(item.string)
            else:
                log.warning('Can\'t store %s', item)
        self.process_verse(db_book, chapter_number, verse_number, verse_text.strip())

    def process_verse(self, db_book, chapter_number, verse_number, verse_text):
        """
        Process a verse element
        :param book: A database Book object
        :param chapter_number: The chapter number to add the verses to (int)
        :param element: The verse element to process. (etree element type)
        :param use_milestones: set to True to process a 'milestone' verse. Defaults to False
        :return: None
        """
        if verse_text:
            log.debug('%s %s:%s %s', db_book.name, chapter_number, verse_number, verse_text.strip())
            self.create_verse(db_book.id, chapter_number, verse_number, verse_text.strip())

    def do_import(self, bible_name=None):
        """
        Loads a Bible from file.
        """
        self.log_debug('Starting WordProject import from "{name}"'.format(name=self.file_path))
        if not self._unzip_file():
            return False
        self.language_id = self.get_language_id(None, bible_name=str(self.file_path))
        result = False
        if self.language_id:
            result = self.process_books()
        self._cleanup()
        return result

    def get_number(self, input_: str) -> None | int:
        """
        Given a string extracts the integer value from the beginning of the string, stopping at first non-numeric char
        :param str: input string
        :return: integer if found, else None
        """
        if result := re.findall(r'\d+', input_):
            return int(result[0])
        else:
            return None
