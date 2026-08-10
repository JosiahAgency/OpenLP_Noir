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

from openlp.core.common.i18n import translate
from openlp.plugins.bibles.lib.bibleimport import BibleImport


def get_text(element):
    """
    Recursively get all text in an objectify element and its child elements.

    :param element: An objectify element to get the text from
    :return: The text content of the element (str)
    """
    verse_text = ''
    if element.text:
        verse_text = element.text
    for sub_element in element.iterchildren():
        verse_text += get_text(sub_element)
    if element.tail:
        verse_text += element.tail
    return verse_text


def parse_chapter_number(number, previous_number):
    """
    Parse the chapter number

    :param number: The raw data from the xml
    :param previous_number: The previous chapter number
    :return: Number of current chapter.
    :rtype: int
    """
    if number:
        return int(number.split()[-1])
    return previous_number + 1


class OpenSongBible(BibleImport):
    """
    OpenSong Bible format importer class. This class is used to import Bibles from OpenSong's XML format.
    """

    def parse_verse_number(self, number, previous_number):
        """
        Parse the verse number retrieved from the xml

        :param number: The raw data from the xml
        :param previous_number: The previous verse number
        :return: Number of current verse. (Int)
        """
        if not number:
            return previous_number + 1
        try:
            return int(number)
        except ValueError:
            verse_parts = number.split('-')
            if len(verse_parts) > 1:
                number = int(verse_parts[0])
                return number
        except TypeError:
            self.log_warning('Illegal verse number: {verse_no}'.format(verse_no=str(number)))
        return previous_number + 1

    def process_books(self, books):
        """
        Extract and create the books from the objectified xml

        :param books: Objectified xml
        :return: None
        """
        for book in books:
            if self.stop_import_flag:
                break
            db_book = self.find_and_create_book(str(book.attrib['n']), len(books), self.language_id)
            self.process_chapters(db_book, book.c)
            self.session.commit()

    def process_chapters(self, book, chapters):
        """
        Extract and create the chapters from the objectified xml for the book `book`

        :param book: A database Book object to add the chapters to
        :param chapters: Objectified xml containing chapters
        :return: None
        """
        chapter_number = 0
        for chapter in chapters:
            if self.stop_import_flag:
                break
            chapter_number = parse_chapter_number(chapter.attrib['n'], chapter_number)
            self.set_current_chapter(book.name, chapter_number)
            self.process_verses(book, chapter_number, chapter.v)

    def process_verses(self, book, chapter_number, verses):
        """
        Extract and create the verses from the objectified xml

        :param book: A database Book object
        :param chapter_number: The chapter number to add the verses to (int)
        :param verses: Objectified xml containing verses
        :return: None
        """
        verse_number = 0
        for verse in verses:
            if self.stop_import_flag:
                break
            verse_number = self.parse_verse_number(verse.attrib['n'], verse_number)
            self.create_verse(book.id, chapter_number, verse_number, get_text(verse))

    def do_import(self, bible_name=None):
        """
        Loads an Open Song Bible from a file.

        :param bible_name: The name of the bible being imported
        :return: True if import completed, False if import was unsuccessful
        """
        self.clear_import_failure()
        self.log_debug('Starting OpenSong import from "{name}"'.format(name=self.file_path))
        self.validate_xml_file(self.file_path, 'bible')
        bible = self.parse_xml(self.file_path, use_objectify=True)
        if bible is None:
            self.set_import_failure(
                code='opensong-parse-failed',
                summary=translate('BiblesPlugin.OpenSongImport', 'OpenSong Bible could not be parsed.'),
                actions=(
                    translate('BiblesPlugin.OpenSongImport', 'Verify the file is a valid OpenSong Bible XML file.'),
                )
            )
            return False
        if not hasattr(bible, 'b') or len(bible.b) == 0:
            self.set_import_failure(
                code='opensong-missing-books',
                summary=translate('BiblesPlugin.OpenSongImport', 'No books were found in this OpenSong Bible file.'),
                actions=(
                    translate('BiblesPlugin.OpenSongImport',
                              'Re-export the Bible as OpenSong XML and try importing again.'),
                )
            )
            return False
        # No language info in the opensong format, so ask the user
        self.language_id = self.get_language_id(bible_name=str(self.file_path))
        if not self.language_id:
            return False
        self.process_books(bible.b)
        return True
