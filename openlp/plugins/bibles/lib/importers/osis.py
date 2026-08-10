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

from lxml import etree

from openlp.core.common.i18n import translate
from openlp.plugins.bibles.lib.bibleimport import BibleImport


NS = {'ns': 'http://www.bibletechnologies.net/2003/OSIS/namespace'}
# Tags we don't use and can remove the content
REMOVABLE_ELEMENTS = (
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}note',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}milestone',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}title',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}abbr',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}catchWord',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}index',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}rdg',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}rdgGroup',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}figure'
)
# Tags we don't use but need to keep the content
REMOVABLE_TAGS = (
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}p',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}l',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}lg',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}q',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}a',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}w',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}divineName',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}foreign',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}hi',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}inscription',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}mentioned',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}name',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}reference',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}seg',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}transChange',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}salute',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}signed',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}closer',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}speech',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}speaker',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}list',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}item',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}table',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}head',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}row',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}cell',
    '{http://www.bibletechnologies.net/2003/OSIS/namespace}caption'
)

# Precompile a few xpath-querys
verse_in_chapter = etree.XPath('//ns:chapter[1]/ns:verse', namespaces=NS)
text_in_verse = etree.XPath('//ns:verse[1]/text()', namespaces=NS)


class OSISBible(BibleImport):
    """
    `OSIS <http://www.bibletechnologies.net/>`_ Bible format importer class.
    """
    def process_books(self, bible_data):
        """
        Extract and create the bible books from the parsed xml

        :param bible_data: parsed xml
        :return: None
        """
        # Find books in the bible
        bible_books = bible_data.xpath("//ns:div[@type='book']", namespaces=NS)
        no_of_books = len(bible_books)
        for book in bible_books:
            if self.stop_import_flag:
                break
            # Remove div-tags in the book
            etree.strip_tags(book, '{http://www.bibletechnologies.net/2003/OSIS/namespace}div')
            db_book = self.find_and_create_book(book.get('osisID'), no_of_books, self.language_id)
            self.process_chapters(db_book, book)
            self.session.commit()

    def process_chapters(self, book, chapters):
        """
        Extract the chapters, and do some initial processing of the verses

        :param book: An OpenLP bible database book object
        :param chapters: parsed chapters
        :return: None
        """
        # Find out if chapter-tags contains the verses, or if it is used as milestone/anchor
        if verse_in_chapter(chapters):
            # The chapter tags contains the verses
            for chapter in chapters:
                chapter_number = int(chapter.get("osisID").split('.')[1])
                self.set_current_chapter(book.name, chapter_number)
                # Find out if verse-tags contains the text, or if it is used as milestone/anchor
                if not text_in_verse(chapter):
                    # verse-tags are used as milestone
                    for verse in chapter:
                        # If this tag marks the start of a verse, the verse text is between this tag and
                        # the next tag, which the "tail" attribute gives us.
                        self.process_verse(book, chapter_number, verse, use_milestones=True)
                else:
                    # Verse-tags contains the text
                    for verse in chapter:
                        self.process_verse(book, chapter_number, verse)
        else:
            # The chapter tags is used as milestones. For now we assume verses is also milestones
            chapter_number = 0
            for element in chapters:
                if element.tag == '{http://www.bibletechnologies.net/2003/OSIS/namespace}chapter' \
                        and element.get('sID'):
                    chapter_number = int(element.get("osisID").split('.')[1])
                    self.set_current_chapter(book.name, chapter_number)
                elif element.tag == '{http://www.bibletechnologies.net/2003/OSIS/namespace}verse':
                    # If this tag marks the start of a verse, the verse text is between this tag and
                    # the next tag, which the "tail" attribute gives us.
                    self.process_verse(book, chapter_number, element, use_milestones=True)

    def process_verse(self, book, chapter_number, element, use_milestones=False):
        """
        Process a verse element
        :param book: A database Book object
        :param chapter_number: The chapter number to add the verses to (int)
        :param element: The verse element to process. (etree element type)
        :param use_milestones: set to True to process a 'milestone' verse. Defaults to False
        :return: None
        """
        osis_id = element.get("osisID")
        if not osis_id:
            return None
        verse_number = int(osis_id.split('.')[2])
        verse_text = ''
        if use_milestones and element.get('sID'):
            verse_text = element.tail
        elif not use_milestones:
            verse_text = element.text
        if verse_text:
            self.create_verse(book.id, chapter_number, verse_number, verse_text.strip())

    def do_import(self, bible_name=None):
        """
        Loads a Bible from file.
        """
        self.clear_import_failure()
        self.log_debug('Starting OSIS import from "{name}"'.format(name=self.file_path))
        self.validate_xml_file(self.file_path, '{http://www.bibletechnologies.net/2003/osis/namespace}osis')
        bible = self.parse_xml(self.file_path, elements=REMOVABLE_ELEMENTS, tags=REMOVABLE_TAGS)
        if bible is None:
            self.set_import_failure(
                code='osis-parse-failed',
                summary=translate('BiblesPlugin.OsisImport', 'OSIS Bible could not be parsed.'),
                actions=(
                    translate('BiblesPlugin.OsisImport', 'Verify the file is valid OSIS XML and try again.'),
                )
            )
            return False
        if len(bible.xpath("//ns:div[@type='book']", namespaces=NS)) == 0:
            self.set_import_failure(
                code='osis-missing-books',
                summary=translate('BiblesPlugin.OsisImport', 'No books were found in this OSIS file.'),
                actions=(
                    translate('BiblesPlugin.OsisImport', 'Re-export the file as OSIS XML and import again.'),
                )
            )
            return False
        # Find bible language
        language = bible.xpath("//ns:osisText/@xml:lang", namespaces=NS)
        self.language_id = self.get_language_id(language[0] if language else None, bible_name=str(self.file_path))
        if not self.language_id:
            return False
        self.process_books(bible)
        return True
