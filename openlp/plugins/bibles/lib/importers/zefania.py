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

from openlp.core.common.i18n import translate
from openlp.core.lib.ui import critical_error_message_box
from openlp.plugins.bibles.lib.bibleimport import BibleImport
from openlp.plugins.bibles.lib.db import BiblesResourcesDB


log = logging.getLogger(__name__)

# Tags we don't use and can remove the content
REMOVABLE_ELEMENTS = ('PROLOG', 'REMARK', 'CAPTION', 'MEDIA')
# Tags we don't use but need to keep the content
REMOVABLE_TAGS = ('STYLE', 'GRAM', 'NOTE', 'SUP', 'XREF')


class ZefaniaBible(BibleImport):
    """
    Zefania Bible format importer class. This class is used to import Bibles from ZefaniaBible's XML format.
    """

    def do_import(self, bible_name=None):
        """
        Loads a Bible from file.
        """
        log.debug('Starting Zefania import from "{name}"'.format(name=self.file_path))
        self.clear_import_failure()
        success = True
        try:
            xmlbible = self.parse_xml(self.file_path, elements=REMOVABLE_ELEMENTS, tags=REMOVABLE_TAGS)
            if xmlbible is None:
                self.set_import_failure(
                    code='zefania-parse-failed',
                    summary=translate('BiblesPlugin.ZefaniaImport', 'Zefania Bible could not be parsed.'),
                    actions=(
                        translate('BiblesPlugin.ZefaniaImport',
                                  'Verify the selected file is valid Zefania XML and try again.'),
                    )
                )
                return False
            # Find bible language
            language = xmlbible.xpath("/XMLBIBLE/INFORMATION/language/text()")
            language_id = self.get_language_id(language[0] if language else None, bible_name=str(self.file_path))
            if not language_id:
                return False
            no_of_books = int(xmlbible.xpath('count(//BIBLEBOOK)'))
            no_of_chap = int(xmlbible.xpath('count(//CHAPTER)'))
            if not no_of_books or not no_of_chap:
                self.set_import_failure(
                    code='zefania-missing-content',
                    summary=translate('BiblesPlugin.ZefaniaImport',
                                      'Incorrect Bible file type. Expected data is missing.'),
                    actions=(
                        translate('BiblesPlugin.ZefaniaImport',
                                  'Ensure the XML contains BIBLEBOOK and CHAPTER nodes and retry.'),
                    )
                )
                critical_error_message_box(message=translate('BiblesPlugin.ZefaniaImport',
                                                             'Incorrect Bible file type. Expected data is missing.'))
                return False
            self.wizard.progress_bar.setMaximum(no_of_chap)
            for BIBLEBOOK in xmlbible:
                if self.stop_import_flag:
                    break
                bname = BIBLEBOOK.get('bname')
                bnumber = BIBLEBOOK.get('bnumber')
                if not bname and not bnumber:
                    continue
                if bname:
                    book_ref_id = self.get_book_ref_id_by_name(bname, no_of_books, language_id)
                else:
                    log.debug('Could not find a name, will use number, basically a guess.')
                    book_ref_id = int(bnumber)
                if not book_ref_id:
                    log.error('Importing books from "{name}" failed'.format(name=self.file_path))
                    return False
                book_details = BiblesResourcesDB.get_book_by_id(book_ref_id)
                db_book = self.create_book(book_details['name'], book_ref_id, book_details['testament_id'])
                for CHAPTER in BIBLEBOOK:
                    if self.stop_import_flag:
                        break
                    chapter_number = CHAPTER.get("cnumber")
                    for VERS in CHAPTER:
                        verse_number = VERS.get("vnumber")
                        self.create_verse(
                            db_book.id, int(chapter_number), int(verse_number), VERS.text.replace('<BR/>', '\n'))
                    self.wizard.increment_progress_bar(
                        translate('BiblesPlugin.Zefnia',
                                  'Importing {book} {chapter}...').format(book=db_book.name,
                                                                          chapter=chapter_number))
            self.session.commit()
            self.application.process_events()
        except Exception as e:
            self.set_import_failure(
                code='zefania-unexpected-error',
                summary=translate('BiblesPlugin.ZefaniaImport', 'Zefania import failed unexpectedly.'),
                details=str(e),
                actions=(
                    translate('BiblesPlugin.ZefaniaImport',
                              'If the source file is compressed, extract it first and import the XML file.'),
                    translate('BiblesPlugin.ZefaniaImport',
                              'If the problem persists, re-export the file and try again.'),
                )
            )
            critical_error_message_box(
                message=translate('BiblesPlugin.ZefaniaImport',
                                  'Incorrect Bible file type supplied. Zefania Bibles may be '
                                  'compressed. You must decompress them before import.'))
            log.exception(str(e))
            success = False
        if self.stop_import_flag:
            return False
        else:
            return success
