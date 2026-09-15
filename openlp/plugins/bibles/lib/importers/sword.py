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

from pysword import modules

from openlp.core.common.i18n import translate
from openlp.core.lib.ui import critical_error_message_box
from openlp.plugins.bibles.lib.bibleimport import BibleImport
from openlp.plugins.bibles.lib.db import BiblesResourcesDB


log = logging.getLogger(__name__)


class SwordBible(BibleImport):
    """
    SWORD Bible format importer class.
    """
    def __init__(self, *args, **kwargs):
        """
        Constructor to create and set up an instance of the SwordBible class. This class is used to import Bibles
        from SWORD bible modules.
        """
        log.debug(self.__class__.__name__)
        super().__init__(*args, **kwargs)
        self.sword_key = kwargs['sword_key']
        self.sword_path = kwargs['sword_path']
        if self.sword_path == '':
            self.sword_path = None

    def do_import(self, bible_name=None):
        """
        Loads a Bible from SWORD module.
        """
        log.debug('Starting SWORD import from "{key}"'.format(key=self.sword_key))
        success = True
        try:
            pysword_modules = modules.SwordModules(self.sword_path)
            pysword_module_json = pysword_modules.parse_modules()[self.sword_key]
            bible = pysword_modules.get_bible_from_module(self.sword_key)
            language = pysword_module_json['lang']
            language = language[language.find('.') + 1:]
            language_id = self.get_language_id(language, bible_name=str(self.file_path))
            if not language_id:
                return False
            books = bible.get_structure().get_books()
            # Count number of books
            num_books = 0
            if 'ot' in books:
                num_books += len(books['ot'])
            if 'nt' in books:
                num_books += len(books['nt'])
            self.wizard.progress_bar.setMaximum(num_books)
            # Import the bible
            for testament in books.keys():
                for book in books[testament]:
                    book_ref_id = self.get_book_ref_id_by_name(book.name, num_books, language_id)
                    book_details = BiblesResourcesDB.get_book_by_id(book_ref_id)
                    db_book = self.create_book(book_details['name'], book_ref_id, book_details['testament_id'])
                    for chapter_number in range(1, book.num_chapters + 1):
                        if self.stop_import_flag:
                            break
                        verses = bible.get_iter(book.name, chapter_number)
                        verse_number = 0
                        for verse in verses:
                            verse_number += 1
                            self.create_verse(db_book.id, chapter_number, verse_number, verse)
                    # Commit once per book, rather than holding one huge transaction open for the
                    # whole Bible; this bounds the amount of uncommitted work outstanding at any
                    # time and matches the batching strategy used by the other importers.
                    self.session.commit()
                    self.wizard.increment_progress_bar(
                        translate('BiblesPlugin.Sword', 'Importing {name}...').format(name=db_book.name))
            self.application.process_events()
        except Exception as e:
            critical_error_message_box(
                message=translate('BiblesPlugin.SwordImport', 'An unexpected error happened while importing the SWORD '
                                                              'bible, please report this to the OpenLP developers.\n'
                                                              '{error}').format(error=e))
            log.exception(str(e))
            success = False
        if self.stop_import_flag:
            return False
        else:
            return success
