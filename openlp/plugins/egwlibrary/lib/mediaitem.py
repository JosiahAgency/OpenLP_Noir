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
The :mod:`~openlp.plugins.egwlibrary.lib.mediaitem` module provides the media manager
item for the EGW Library plugin, including the "smart" search which automatically
detects whether the user typed a reference (like "DA 83.2") or words to search for.
"""
import logging
from typing import Any

from PySide6 import QtCore, QtWidgets

from openlp.core.common.enum import EGWSearch
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.lib.mediamanageritem import MediaManagerItem
from openlp.core.lib.serviceitem import ItemCapabilities
from openlp.core.lib.ui import create_horizontal_adjusting_combo_box, critical_error_message_box, \
    find_and_set_in_combo_box, set_case_insensitive_completer
from openlp.core.ui.icons import UiIcons
from openlp.core.widgets.dialogs import FileDialog
from openlp.plugins.egwlibrary.lib import format_paragraph_reference, parse_reference
from openlp.plugins.egwlibrary.lib.db import Alias
from openlp.plugins.egwlibrary.lib.importer import EGWImportError, import_book, import_json_file
from openlp.plugins.egwlibrary.lib.pdfimport import EGWPdfError, convert_pdf_book
from openlp.plugins.egwlibrary.lib.pdfimportdialog import PdfBookDetailsDialog

log = logging.getLogger(__name__)


class EGWLibraryMediaItem(MediaManagerItem):
    """
    This is the media manager item for the EGW Library.
    """
    egwlibrary_go_live = QtCore.Signal(list)
    egwlibrary_add_to_service = QtCore.Signal(list)
    log.info('EGW Library Media Item loaded')

    def __init__(self, parent, plugin):
        self.icon_path = 'egwlibrary/egwlibrary'
        self.manager = plugin.manager
        # Debounce timer for search-as-you-type
        self.search_timer = QtCore.QTimer()
        self.search_timer.setInterval(200)
        self.search_timer.setSingleShot(True)
        self.is_search_as_you_type_enabled = False
        self.search_is_interactive = True
        super().__init__(parent, plugin)
        self.search_timer.timeout.connect(self.on_search_timer_timeout)

    def setup_item(self):
        """
        Do some additional setup.
        """
        self.egwlibrary_go_live.connect(self.go_live_remote)
        self.egwlibrary_add_to_service.connect(self.add_to_service_remote)
        self.single_service_item = False
        self.quick_preview_allowed = True
        self.has_search = True

    def required_icons(self):
        """
        Set which icons the media manager toolbar should show.
        """
        super().required_icons()
        self.has_import_icon = True
        self.has_new_icon = False
        self.has_edit_icon = False
        self.has_file_icon = False
        self.has_delete_icon = True

    def add_end_header_bar(self):
        """
        Add the book selector row and the search field.
        """
        self.book_widget = QtWidgets.QWidget(self)
        self.book_widget.setObjectName('book_widget')
        self.book_layout = QtWidgets.QFormLayout(self.book_widget)
        self.book_layout.setObjectName('book_layout')
        self.book_label = QtWidgets.QLabel(self.book_widget)
        self.book_label.setObjectName('book_label')
        self.book_combo_box = create_horizontal_adjusting_combo_box(self.book_widget, 'book_combo_box')
        self.book_label.setBuddy(self.book_combo_box)
        self.book_layout.addRow(self.book_label, self.book_combo_box)
        self.all_books_check_box = QtWidgets.QCheckBox(self.book_widget)
        self.all_books_check_box.setObjectName('all_books_check_box')
        self.book_layout.addRow(self.all_books_check_box)
        self.page_layout.addWidget(self.book_widget)
        self.add_search_to_toolbar()
        # Signals and slots
        self.book_combo_box.activated.connect(self.on_book_combo_box_activated)
        self.all_books_check_box.stateChanged.connect(self.on_all_books_check_box_changed)
        self.search_text_edit.searchTypeChanged.connect(self.on_search_text_button_clicked)

    def retranslate_ui(self):
        """
        Set the translated texts of the media item.
        """
        self.book_label.setText(translate('EGWLibraryPlugin.MediaItem', 'Book:'))
        self.all_books_check_box.setText(translate('EGWLibraryPlugin.MediaItem', 'Search all books'))
        self.search_text_label.setText('{text}:'.format(text=UiStrings().Search))
        self.search_text_button.setText(UiStrings().Search)

    def initialise(self):
        """
        Initialise the UI so it can provide searches.
        """
        self.search_text_edit.set_search_types([
            (EGWSearch.Smart, UiIcons().search_comb,
                translate('EGWLibraryPlugin.MediaItem', 'Text or Reference'),
                translate('EGWLibraryPlugin.MediaItem', 'Text or Reference...')),
            (EGWSearch.Reference, UiIcons().search_ref,
                translate('EGWLibraryPlugin.MediaItem', 'Reference'),
                translate('EGWLibraryPlugin.MediaItem', 'Search Reference (e.g. DA 83.2)...')),
            (EGWSearch.Text, UiIcons().text,
                translate('EGWLibraryPlugin.MediaItem', 'Text Search'),
                translate('EGWLibraryPlugin.MediaItem', 'Search Text...'))
        ])
        self.populate_book_combo_box()
        self.all_books_check_box.setChecked(self.settings.value('egwlibrary/search all books'))
        self.config_update()

    def config_update(self):
        """
        Reload values that depend on the settings.
        """
        self.is_search_as_you_type_enabled = self.settings.value('egwlibrary/is search while typing enabled')

    def on_focus(self):
        """
        Set the focus to the search field.
        """
        self.search_text_edit.setFocus()
        self.search_text_edit.selectAll()

    def populate_book_combo_box(self):
        """
        Fill the book combo box with the books in the library and update the search
        completer with all the book names and aliases.
        """
        self.book_combo_box.clear()
        books = self.manager.get_books()
        for book in books:
            self.book_combo_box.addItem(book.title, book.id)
        find_and_set_in_combo_box(self.book_combo_box, self.settings.value('egwlibrary/last selected book'))
        # Book names and aliases followed by a space, so "DA" completes to "DA " ready
        # for the reference part.
        aliases = self.manager.get_all_objects(Alias)
        completions = sorted({alias.display + ' ' for alias in aliases})
        set_case_insensitive_completer(completions, self.search_text_edit)

    def on_book_combo_box_activated(self):
        """
        Remember the selected book.
        """
        self.settings.setValue('egwlibrary/last selected book', self.book_combo_box.currentText())

    def on_all_books_check_box_changed(self):
        """
        Remember the "search all books" choice and re-run the search with the new scope.
        """
        self.settings.setValue('egwlibrary/search all books', self.all_books_check_box.isChecked())
        self.book_combo_box.setEnabled(not self.all_books_check_box.isChecked())
        if self.search_text_edit.displayText():
            self.on_search_text_button_clicked()

    def on_import_click(self):
        """
        Import one or more books from JSON files or EGW Estate PDF exports.
        """
        file_paths, _ = FileDialog.getOpenFileNames(
            self, translate('EGWLibraryPlugin.MediaItem', 'Import EGW Library Book(s)'),
            self.settings.value('egwlibrary/last directory import'),
            translate('EGWLibraryPlugin.MediaItem',
                      'EGW Library book files (*.json *.pdf);;JSON book files (*.json);;'
                      'EGW Estate PDF exports (*.pdf)'))
        if not file_paths:
            return
        self.application.set_busy_cursor()
        imported = []
        errors = []
        for file_path in file_paths:
            try:
                if file_path.suffix.lower() == '.pdf':
                    self._import_pdf(file_path, imported)
                else:
                    for book, paragraph_count in import_json_file(self.manager, file_path):
                        imported.append('{title} ({count})'.format(title=book.title, count=paragraph_count))
            except (EGWImportError, EGWPdfError) as import_error:
                errors.append(str(import_error))
        self.settings.setValue('egwlibrary/last directory import', file_paths[0].parent)
        self.populate_book_combo_box()
        self.application.set_normal_cursor()
        if errors:
            critical_error_message_box(
                translate('EGWLibraryPlugin.MediaItem', 'Import Problems'), '\n'.join(errors))
        if imported:
            self.main_window.information_message(
                translate('EGWLibraryPlugin.MediaItem', 'Import Complete'),
                translate('EGWLibraryPlugin.MediaItem',
                          'Imported the following book(s), with the paragraph count in brackets:\n{books}'
                          ).format(books='\n'.join(imported)))

    def _import_pdf(self, file_path, imported):
        """
        Convert an EGW Estate PDF export and import it, letting the user confirm or
        correct the guessed book details first.

        :param file_path: A Path to the PDF.
        :param imported: The list of "Title (count)" strings to append to on success.
        :raises EGWPdfError | EGWImportError: When conversion or import fails.
        """
        book_data, warnings = convert_pdf_book(file_path)
        # The details dialog needs a normal cursor; on_import_click set the busy one
        self.application.set_normal_cursor()
        try:
            details_dialog = PdfBookDetailsDialog(self, file_path.name, book_data, warnings)
            if not details_dialog.exec():
                # The user chose not to import this PDF
                return
            book_data = details_dialog.book_data()
        finally:
            self.application.set_busy_cursor()
        book, paragraph_count = import_book(self.manager, book_data)
        imported.append('{title} ({count})'.format(title=book.title, count=paragraph_count))

    def on_delete_click(self):
        """
        Delete the book currently selected in the book combo box from the library.
        """
        book_id = self.book_combo_box.currentData()
        if book_id is None:
            return
        book_title = self.book_combo_box.currentText()
        answer = QtWidgets.QMessageBox.question(
            self, UiStrings().ConfirmDelete,
            translate('EGWLibraryPlugin.MediaItem',
                      'Are you sure you want to completely delete "{book}" from the library?\n\n'
                      'You will need to re-import this book to use it again.').format(book=book_title),
            defaultButton=QtWidgets.QMessageBox.StandardButton.No)
        if answer == QtWidgets.QMessageBox.StandardButton.No:
            return
        self.manager.delete_book(book_id)
        self.populate_book_combo_box()
        self.list_view.clear()

    def on_search_text_edit_changed(self, text):
        """
        Debounce search-as-you-type through a timer so we do not search on every
        keystroke.
        """
        if not self.is_search_as_you_type_enabled:
            return
        if len(text) > 2:
            self.search_is_interactive = False
            self.search_timer.start()
        elif not text:
            self.list_view.clear()

    def on_search_timer_timeout(self):
        """
        Perform the search-as-you-type search.
        """
        self.do_search()
        self.search_is_interactive = True

    def on_search_text_button_clicked(self):
        """
        Perform a search when the search button is clicked or return is pressed.
        """
        self.search_timer.stop()
        self.search_is_interactive = True
        self.do_search()

    def do_search(self):
        """
        Run the search in the search field, dispatching on the selected search type.
        The smart search first tries to read the text as a reference against the book
        aliases and falls back to a full text search.
        """
        search_text = self.search_text_edit.displayText().strip()
        if not search_text:
            self.list_view.clear()
            return
        if not self.manager.get_books():
            if self.search_is_interactive:
                self.main_window.information_message(
                    translate('EGWLibraryPlugin.MediaItem', 'No books in the library'),
                    translate('EGWLibraryPlugin.MediaItem',
                              'There are no books in the EGW library yet. Use the import button to add books.'))
            return
        self.application.set_busy_cursor()
        search_type = self.search_text_edit.current_search_type()
        results = []
        select_results = False
        reference = parse_reference(search_text)
        book = self.manager.get_book_by_alias(reference['book']) if reference else None
        if search_type in [EGWSearch.Smart, EGWSearch.Reference] and book:
            results = self.reference_search(book, reference)
            # Pre-select reference results, like Bible verses, so they can be sent
            # live right away. Chapter rows are for browsing, so leave them unselected.
            select_results = bool(results) and results[0]['type'] == 'paragraph'
        elif search_type == EGWSearch.Reference:
            if self.search_is_interactive:
                critical_error_message_box(
                    translate('EGWLibraryPlugin.MediaItem', 'Book not found'),
                    translate('EGWLibraryPlugin.MediaItem',
                              'No book matching "{book}" was found in the library. References look like '
                              '"DA 83.2" (book, page and paragraph) or "DA ch 5" (book and chapter).'
                              ).format(book=reference['book'] if reference else search_text))
        else:
            results = self.do_text_search(search_text)
        self.list_view.clear()
        for data in results:
            list_item = QtWidgets.QListWidgetItem(data['item_title'])
            list_item.setData(QtCore.Qt.ItemDataRole.UserRole, data)
            self.list_view.addItem(list_item)
        if select_results:
            self.list_view.selectAll()
        self.application.set_normal_cursor()

    def reference_search(self, book, reference):
        """
        Perform a reference search and return the display results.

        :param book: The Book the reference points into.
        :param reference: The parsed reference dict from
            :func:`~openlp.plugins.egwlibrary.lib.parse_reference`.
        """
        if reference['chapter'] is not None:
            chapter = self.manager.get_chapter(book.id, reference['chapter'])
            if not chapter:
                return []
            return [self.build_paragraph_result(book, paragraph)
                    for paragraph in self.manager.get_paragraphs_for_chapter(chapter.id)]
        if reference['from_page'] is not None:
            if reference['from_para'] is not None:
                paragraphs = self.manager.get_paragraphs_for_reference(
                    book.id, reference['from_page'], reference['from_para'],
                    reference['to_page'], reference['to_para'])
            else:
                paragraphs = self.manager.get_paragraphs_for_pages(
                    book.id, reference['from_page'], reference['to_page'])
            return [self.build_paragraph_result(book, paragraph) for paragraph in paragraphs]
        # Only a book: browse it. Books with real chapters list their chapters, a book
        # with just the implicit chapter lists its paragraphs directly.
        chapters = self.manager.get_chapters(book.id)
        if len(chapters) == 1 and chapters[0].number == 0:
            return [self.build_paragraph_result(book, paragraph)
                    for paragraph in self.manager.get_paragraphs_for_chapter(chapters[0].id)]
        return [self.build_chapter_result(book, chapter) for chapter in chapters]

    def do_text_search(self, search_text):
        """
        Perform a full text search, in the selected book or in all books, and return
        the display results.
        """
        book_id = None if self.all_books_check_box.isChecked() else self.book_combo_box.currentData()
        show_book = self.all_books_check_box.isChecked()
        return [self.build_paragraph_result(paragraph.book, paragraph, show_book=show_book)
                for paragraph in self.manager.text_search(search_text, book_id=book_id)]

    def build_paragraph_result(self, book, paragraph, show_book=False):
        """
        Build the result dict for one paragraph. This dict holds everything needed to
        generate the slides later, so no database access is needed once the search
        results are on screen.
        """
        reference = format_paragraph_reference(book.abbreviation, paragraph)
        snippet = paragraph.text if len(paragraph.text) <= 70 else paragraph.text[:70].rsplit(' ', 1)[0] + '…'
        item_title = '{reference} — {snippet}'.format(reference=reference, snippet=snippet)
        return {
            'type': 'paragraph',
            'paragraph_id': paragraph.id,
            'book_title': book.title,
            'abbreviation': book.abbreviation,
            'copyright': book.copyright or '',
            'chapter_number': paragraph.chapter.number,
            'chapter_title': paragraph.chapter.title or '',
            'paragraph_number': paragraph.paragraph_number,
            'page': paragraph.page,
            'para': paragraph.para_on_page,
            'reference': reference,
            'text': paragraph.text,
            'item_title': item_title
        }

    def build_chapter_result(self, book, chapter):
        """
        Build the result dict for a chapter row (shown when browsing a book).
        """
        chapter_reference = '{abbr}, {chapter} {number}'.format(
            abbr=book.abbreviation, chapter=translate('EGWLibraryPlugin.MediaItem', 'ch.'), number=chapter.number)
        item_title = chapter_reference
        if chapter.title:
            item_title = '{reference} — {title}'.format(reference=chapter_reference, title=chapter.title)
        return {
            'type': 'chapter',
            'chapter_id': chapter.id,
            'book_title': book.title,
            'abbreviation': book.abbreviation,
            'copyright': book.copyright or '',
            'chapter_number': chapter.number,
            'chapter_title': chapter.title or '',
            'reference': chapter_reference,
            'item_title': item_title
        }

    def generate_slide_data(self, service_item, *, item=None, **kwargs):
        """
        Generate the service item from the selected paragraphs and/or chapters. Each
        paragraph becomes one slide; long paragraphs are split over multiple slides
        automatically by the renderer (via the CanWordSplit capability).

        :param service_item: The service item to be built on
        :param item: The list widget items to use instead of the current selection
        :param kwargs: Consume other unused args specified by the base implementation.
        """
        items = item if item else self.list_view.selectedItems()
        if not items:
            return False
        paragraph_datas = []
        for list_item in items:
            data = list_item.data(QtCore.Qt.ItemDataRole.UserRole)
            if data['type'] == 'chapter':
                # Expand a chapter row into all of its paragraphs
                book = self.manager.get_book_by_alias(data['abbreviation'])
                for paragraph in self.manager.get_paragraphs_for_chapter(data['chapter_id']):
                    paragraph_datas.append(self.build_paragraph_result(book, paragraph))
            else:
                paragraph_datas.append(data)
        if not paragraph_datas:
            return False
        # Slides: one paragraph per slide, with the citation as a superscript marker
        references = []
        copyrights = []
        book_titles = []
        for data in paragraph_datas:
            marker = data['reference'].replace('{abbr} '.format(abbr=data['abbreviation']), '', 1)
            slide_text = '{{su}}{marker}&nbsp;{{/su}}{text}'.format(marker=marker, text=data['text'])
            service_item.add_from_text(slide_text)
            references.append(data['reference'])
            if data['book_title'] not in book_titles:
                book_titles.append(data['book_title'])
            if data['copyright'] and data['copyright'] not in copyrights:
                copyrights.append(data['copyright'])
        reference_text = ', '.join(references)
        if len(reference_text) > 80:
            reference_text = '{first} — {last}'.format(first=references[0], last=references[-1])
        service_item.title = reference_text
        # Service Item: Theme
        if self.plugin.settings_tab and self.plugin.settings_tab.egw_theme:
            service_item.theme = self.plugin.settings_tab.egw_theme
        # Footer, following the Bible footer pattern
        if self.settings.value('egwlibrary/footer show reference'):
            service_item.raw_footer.append('{books}: {references}'.format(
                books=', '.join(book_titles), references=reference_text))
        if self.settings.value('egwlibrary/footer show copyright') and copyrights:
            service_item.raw_footer.append(' '.join(copyrights))
        service_item.data_string = {
            'books': book_titles,
            'references': references
        }
        service_item.add_capability(ItemCapabilities.CanPreview)
        service_item.add_capability(ItemCapabilities.CanLoop)
        service_item.add_capability(ItemCapabilities.CanWordSplit)
        service_item.add_capability(ItemCapabilities.CanEditTitle)
        return True

    @QtCore.Slot(str, bool, result=list)
    def search(self, string: str, show_error: bool = True) -> list[list[Any]]:
        """
        Search the library, for the remote API.

        :param string: The search string
        :param show_error: Unused, errors are never shown for remote searches.
        """
        reference = parse_reference(string)
        book = self.manager.get_book_by_alias(reference['book']) if reference else None
        if book and (reference['chapter'] is not None or reference['from_page'] is not None):
            results = self.reference_search(book, reference)
        else:
            results = self.do_text_search(string)
        return [[result['paragraph_id'], result['item_title']]
                for result in results if result['type'] == 'paragraph']
