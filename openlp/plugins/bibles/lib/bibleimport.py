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

from zipfile import is_zipfile

from lxml import etree, objectify
from dataclasses import dataclass

from openlp.core.common.i18n import get_language, translate
from openlp.core.common.mixins import LogMixin, RegistryProperties
from openlp.core.common.registry import Registry
from openlp.core.lib.exceptions import ValidationError
from openlp.core.lib.ui import critical_error_message_box
from openlp.plugins.bibles.lib.db import AlternativeBookNamesDB, BibleDB, BiblesResourcesDB


@dataclass
class ImportFailure:
    """
    A normalized error payload used to communicate importer failures back to the wizard.
    """
    code: str
    summary: str
    details: str = ''
    actions: tuple[str, ...] = ()
    is_user_cancelled: bool = False


class BibleImport(BibleDB, LogMixin, RegistryProperties):
    """
    Helper class to import bibles from a third party source into OpenLP
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_path = kwargs.get('file_path')
        self.wizard = None
        self.stop_import_flag = False
        self.import_failure = None
        Registry().register_function('openlp_stop_wizard', self.stop_import)

    def clear_import_failure(self):
        """
        Clear previous failure details before running an import.
        """
        self.import_failure = None

    def set_import_failure(self, code, summary, details='', actions=(), is_user_cancelled=False):
        """
        Store normalized failure details for UI feedback and diagnostics.
        """
        self.import_failure = ImportFailure(
            code=code,
            summary=summary,
            details=details,
            actions=tuple(actions) if actions else (),
            is_user_cancelled=is_user_cancelled
        )
        return False

    @staticmethod
    def is_compressed(file_path):
        """
        Check if the supplied file is compressed

        :param pathlib.Path file_path: A path to the file to check
        """
        if is_zipfile(file_path):
            critical_error_message_box(
                message=translate('BiblesPlugin.BibleImport',
                                  'The file "{file}" you supplied is compressed. You must decompress it before import.'
                                  ).format(file=file_path))
            return True
        return False

    def get_book_ref_id_by_name(self, book, maxbooks=66, language_id=None):
        """
        Find the book id from the name or abbreviation of the book. If it doesn't currently exist, ask the user.

        :param book: The name or abbreviation of the book
        :param maxbooks: The number of books in the bible
        :param language_id: The language_id of the bible
        :return: The id of the bible, or None
        """
        self.log_debug('BibleDB.get_book_ref_id_by_name:("{book}", "{lang}")'.format(book=book, lang=language_id))
        book_temp = BiblesResourcesDB.get_book(book, True)
        if book_temp:
            return book_temp['id']
        book_id = BiblesResourcesDB.get_alternative_book_name(book)
        if book_id:
            return book_id
        book_id = AlternativeBookNamesDB.get_book_reference_id(book)
        if book_id:
            return book_id
        from openlp.plugins.bibles.forms import BookNameForm
        book_name = BookNameForm(self.wizard)
        if book_name.exec(book, self.get_books(), maxbooks) and book_name.book_id:
            AlternativeBookNamesDB.create_alternative_book_name(book, book_name.book_id, language_id)
            return book_name.book_id

    def get_language(self, bible_name=None):
        """
        If no language is given it calls a dialog window where the user could  select the bible language.
        Return the language id of a bible.

        :param bible_name: The language the bible is.
        """
        self.log_debug('BibleImpoer.get_language()')
        from openlp.plugins.bibles.forms import LanguageForm
        language_id = None
        language_form = LanguageForm(self.wizard)
        if language_form.exec(bible_name):
            combo_box = language_form.language_combo_box
            language_id = combo_box.itemData(combo_box.currentIndex())
        else:
            self.set_import_failure(
                code='language-selection-cancelled',
                summary=translate('BiblesPlugin.BibleImport', 'Import cancelled while selecting language.'),
                details=translate('BiblesPlugin.BibleImport',
                                  'Language could not be detected from the file, and language selection was '
                                  'cancelled.'),
                actions=(
                    translate('BiblesPlugin.BibleImport', 'Run the import again and choose the Bible language.'),
                ),
                is_user_cancelled=True
            )
            return False
        if not language_id:
            self.set_import_failure(
                code='language-selection-missing',
                summary=translate('BiblesPlugin.BibleImport', 'No language was selected for this Bible import.'),
                actions=(
                    translate('BiblesPlugin.BibleImport', 'Run the import again and select a language.'),
                )
            )
            return None
        self.save_meta('language_id', language_id)
        return language_id

    def get_language_id(self, file_language=None, bible_name=None):
        """
        Get the language_id for the language of the bible. Fallback to user input if we cannot do this pragmatically.

        :param file_language: Language of the bible. Possibly retrieved from the file being imported. Str
        :param bible_name: Name of the bible to display on the get_language dialog. Str
        :return: The id of a language Int or None
        """
        language_id = None
        if file_language:
            language = get_language(file_language)
            if language and language.id:
                language_id = language.id
        if not language_id:
            # The language couldn't be detected, ask the user
            language_id = self.get_language(bible_name)
        if not language_id:
            # User cancelled get_language dialog
            self.log_error('Language detection failed when importing from "{name}". User aborted language selection.'
                           .format(name=bible_name))
            if self.import_failure is None:
                self.set_import_failure(
                    code='language-detection-failed',
                    summary=translate('BiblesPlugin.BibleImport', 'Could not determine Bible language.'),
                    actions=(
                        translate('BiblesPlugin.BibleImport', 'Run the import again and select a language.'),
                    )
                )
            return None
        self.save_meta('language_id', language_id)
        return language_id

    def find_and_create_book(self, name, no_of_books, language_id, guess_id=None):
        """
        Find the OpenLP book id and then create the book in this bible db

        :param name: Name of the book. If None, then fall back to the guess_id Str
        :param no_of_books: The total number of books contained in this bible Int
        :param language_id: The OpenLP id of the language of this bible Int
        :param guess_id: The guessed id of the book, used if name is None Int
        :return:
        """
        if name:
            book_ref_id = self.get_book_ref_id_by_name(name, no_of_books, language_id)
        else:
            self.log_debug('No book name supplied. Falling back to guess_id')
            book_ref_id = guess_id
        if not book_ref_id:
            self.set_import_failure(
                code='book-mapping-required',
                summary=translate('BiblesPlugin.BibleImport', 'A book name in this Bible could not be matched.'),
                details=translate('BiblesPlugin.BibleImport',
                                  'One or more book names in the source file could not be mapped to OpenLP books.'),
                actions=(
                    translate('BiblesPlugin.BibleImport',
                              'Run the import again and map unknown book names when prompted.'),
                )
            )
            raise ValidationError(msg='Could not resolve book_ref_id in "{}"'.format(self.file_path))
        book_details = BiblesResourcesDB.get_book_by_id(book_ref_id)
        if book_details is None:
            self.set_import_failure(
                code='book-reference-invalid',
                summary=translate('BiblesPlugin.BibleImport', 'Book mapping failed while importing this Bible.'),
                details=translate('BiblesPlugin.BibleImport',
                                  'OpenLP could not resolve an internal book reference for the source file.'),
                actions=(
                    translate('BiblesPlugin.BibleImport',
                              'Verify the source Bible uses standard book names or re-export the file.'),
                )
            )
            raise ValidationError(msg='book_ref_id: {book_ref} Could not be found in the BibleResourcesDB while '
                                      'importing {file}'.format(book_ref=book_ref_id, file=self.file_path))
        return self.create_book(name, book_ref_id, book_details['testament_id'])

    def parse_xml(self, file_path, use_objectify=False, elements=None, tags=None):
        """
        Parse and clean the supplied file by removing any elements or tags we don't use.
        :param file_path: The filename of the xml file to parse. Str
        :param use_objectify: Use the objectify parser rather than the etree parser. (Bool)
        :param elements: A tuple of element names (Str) to remove along with their content.
        :param tags: A tuple of element names (Str) to remove, preserving their content.
        :return: The root element of the xml document
        """
        try:
            with file_path.open('rb') as import_file:
                # NOTE: We don't need to do any of the normal encoding detection here, because lxml does it's own
                # encoding detection, and the two mechanisms together interfere with each other.
                if not use_objectify:
                    tree = etree.parse(import_file, parser=etree.XMLParser(recover=True))
                else:
                    tree = objectify.parse(import_file, parser=objectify.makeparser(recover=True))
                if elements or tags:
                    self.wizard.increment_progress_bar(
                        translate('BiblesPlugin.OsisImport', 'Removing unused tags (this may take a few minutes)...'))
                if elements:
                    # Strip tags we don't use - remove content
                    etree.strip_elements(tree, elements, with_tail=False)
                if tags:
                    # Strip tags we don't use - keep content
                    etree.strip_tags(tree, tags)
                return tree.getroot()
        except OSError as e:
            self.log_exception('Opening {file_name} failed.'.format(file_name=e.filename))
            self.set_import_failure(
                code='file-open-failed',
                summary=translate('BiblesPlugin.BibleImport', 'OpenLP could not read the selected Bible file.'),
                details=translate('BiblesPlugin.BibleImport',
                                  'The selected file could not be opened: {error}').format(error=e.strerror),
                actions=(
                    translate('BiblesPlugin.BibleImport', 'Verify the file path and file permissions.'),
                    translate('BiblesPlugin.BibleImport', 'Close other applications that might lock the file.'),
                )
            )
            critical_error_message_box(
                title='An Error Occured When Opening A File',
                message='The following error occurred when trying to open\n{file_name}:\n\n{error}'
                .format(file_name=e.filename, error=e.strerror))
        return None

    def register(self, wizard):
        """
        This method basically just initialises the database. It is called from the Bible Manager when a Bible is
        imported. Descendant classes may want to override this method to supply their own custom
        initialisation as well.

        :param wizard: The actual Qt wizard form.
        """
        self.wizard = wizard
        return self.name

    def set_current_chapter(self, book_name, chapter_name):
        self.wizard.increment_progress_bar(translate('BiblesPlugin.OsisImport', 'Importing {book} {chapter}...')
                                           .format(book=book_name, chapter=chapter_name))

    def stop_import(self):
        """
        Stops the import of the Bible.
        """
        self.log_debug('Stopping import')
        self.stop_import_flag = True

    def validate_xml_file(self, file_path, tag):
        """
        Validate the supplied file

        :param file_path: The supplied file
        :param tag: The expected root tag type
        :return: True if valid. ValidationError is raised otherwise.
        """
        if BibleImport.is_compressed(file_path):
            self.set_import_failure(
                code='compressed-file',
                summary=translate('BiblesPlugin.BibleImport', 'The selected Bible file is compressed.'),
                actions=(
                    translate('BiblesPlugin.BibleImport', 'Extract the archive and import the XML/CSV file inside.'),
                )
            )
            raise ValidationError(msg='Compressed file')
        bible = self.parse_xml(file_path, use_objectify=True)
        if bible is None:
            if self.import_failure is None:
                self.set_import_failure(
                    code='xml-open-failed',
                    summary=translate('BiblesPlugin.BibleImport', 'OpenLP could not open this Bible file.'),
                    actions=(
                        translate('BiblesPlugin.BibleImport', 'Verify the file path and try again.'),
                    )
                )
            raise ValidationError(msg='Error when opening file')
        root_tag = bible.tag.lower()
        bible_type = translate('BiblesPlugin.BibleImport', 'unknown type of',
                               'This looks like an unknown type of XML bible.')
        if root_tag == tag:
            return True
        elif root_tag == 'bible':
            bible_type = "OpenSong"
        elif root_tag == '{http://www.bibletechnologies.net/2003/osis/namespace}osis':
            bible_type = 'OSIS'
        elif root_tag == 'xmlbible':
            bible_type = 'Zefania'
        critical_error_message_box(
            message=translate('BiblesPlugin.BibleImport',
                              'Incorrect Bible file type supplied. This looks like an {bible_type} XML bible.'
                              .format(bible_type=bible_type)))
        self.set_import_failure(
            code='invalid-xml-root',
            summary=translate('BiblesPlugin.BibleImport', 'Incorrect Bible file type supplied.'),
            details=translate('BiblesPlugin.BibleImport',
                              'Expected a different root type for this import format.'),
            actions=(
                translate('BiblesPlugin.BibleImport', 'Select the matching import format and try again.'),
            )
        )
        raise ValidationError(msg='Invalid xml.')
