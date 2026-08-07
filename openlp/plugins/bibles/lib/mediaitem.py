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
from enum import IntEnum, unique
from typing import Any

from PySide6 import QtCore, QtWidgets

from openlp.core.common.enum import BibleSearch, DisplayStyle, LayoutStyle, ReferencePlacement
from openlp.core.common.i18n import UiStrings, get_locale_key, translate
from openlp.core.common.registry import Registry
from openlp.core.lib import ServiceItemContext
from openlp.core.lib.mediamanageritem import MediaManagerItem
from openlp.core.lib.serviceitem import ItemCapabilities
from openlp.core.lib.ui import create_horizontal_adjusting_combo_box, critical_error_message_box, \
    find_and_set_in_combo_box, set_case_insensitive_completer
from openlp.core.ui.icons import UiIcons
from openlp.core.widgets.edits import SearchEdit
from openlp.plugins.bibles.forms.bibleimportform import BibleImportForm
from openlp.plugins.bibles.forms.editbibleform import EditBibleForm
from openlp.plugins.bibles.lib import get_reference_match, get_reference_separator
from openlp.plugins.bibles.lib.db import BiblesResourcesDB
from openlp.plugins.bibles.lib.versereferencelist import VerseReferenceList

log = logging.getLogger(__name__)

VALID_TEXT_SEARCH = re.compile(r'\w\w\w')


def get_reference_separators():
    return {'verse': get_reference_separator('sep_v_display'),
            'range': get_reference_separator('sep_r_display'),
            'list': get_reference_separator('sep_l_display')}


@unique
class ResultsTab(IntEnum):
    """
    Enumeration class for the different tabs for the results list.
    """
    Saved = 0
    Search = 1


@unique
class SearchStatus(IntEnum):
    """
    Enumeration class for the different search methods.
    """
    SearchButton = 0
    SearchAsYouType = 1
    NotEnoughText = 2


@unique
class SearchTabs(IntEnum):
    """
    Enumeration class for the tabs on the media item.
    """
    Search = 0
    Select = 1
    Options = 2


class BibleMediaItem(MediaManagerItem):
    """
    This is the custom media manager item for Bibles.
    """
    bibles_go_live = QtCore.Signal(list)
    bibles_add_to_service = QtCore.Signal(list)
    log.info('Bible Media Item loaded')

    def __init__(self, *args, **kwargs):
        """
        Constructor

        :param args: Positional arguments to pass to the super method. (tuple)
        :param kwargs: Keyword arguments to pass to the super method. (dict)
        """
        log.debug('BibleMediaItem __init__')
        self.clear_icon = UiIcons().square
        self.save_results_icon = UiIcons().save
        self.sort_icon = UiIcons().sort
        self.bible = None
        self.second_bible = None
        self.saved_results = []
        self.current_results = []
        self.search_status = SearchStatus.SearchButton
        self.search_timer = None
        super().__init__(*args, **kwargs)
        Registry().register_function('populate_bible_combo_boxes', self.populate_bible_combo_boxes)
        log.debug('BibleMediaItem __init__ complete')

    def setup_item(self):
        """
        Do some additional setup.

        :return: None
        """
        log.debug('setup_item')
        self.bibles_go_live.connect(self.go_live_remote)
        self.bibles_add_to_service.connect(self.add_to_service_remote)
        # Place to store the search results for both bibles.
        self.settings_tab = self.plugin.settings_tab
        self.quick_preview_allowed = True
        self.has_search = True
        self.search_results = []
        self.second_search_results = []
        self.search_timer = self.create_debounce_timer(self.on_search_timer_timeout)
        Registry().register_function('bibles_load_list', self.reload_bibles)

    def required_icons(self):
        """
        Set which icons the media manager tab should show

        :return: None
        """
        log.debug('required_icons')
        super().required_icons()
        self.has_import_icon = True
        self.has_new_icon = False
        self.has_edit_icon = True
        self.has_delete_icon = True
        self.add_to_service_item = False

    def add_middle_header_bar(self):
        self.search_tab_bar = QtWidgets.QTabBar(self)
        self.search_tab_bar.setExpanding(False)
        self.page_layout.addWidget(self.search_tab_bar)
        # Add the Search tab.
        self.search_tab = QtWidgets.QWidget()
        self.search_tab.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
        self.search_tab_bar.addTab(translate('BiblesPlugin.MediaItem', 'Find'))
        self.search_layout = QtWidgets.QFormLayout(self.search_tab)
        self.search_edit = SearchEdit(self.search_tab, 'bibles')
        self.search_layout.addRow(translate('BiblesPlugin.MediaItem', 'Find:'), self.search_edit)
        self.search_tab.setVisible(True)
        self.page_layout.addWidget(self.search_tab)
        # Add the Select tab.
        self.select_tab = QtWidgets.QWidget()
        self.select_tab.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
        self.search_tab_bar.addTab(translate('BiblesPlugin.MediaItem', 'Select'))
        self.select_layout = QtWidgets.QFormLayout(self.select_tab)
        self.book_layout = QtWidgets.QHBoxLayout()
        self.select_book_combo_box = create_horizontal_adjusting_combo_box(self.select_tab, 'select_book_combo_box')
        self.book_layout.addWidget(self.select_book_combo_box)
        self.book_order_button = QtWidgets.QToolButton()
        self.book_order_button.setIcon(self.sort_icon)
        self.book_order_button.setCheckable(True)
        self.book_order_button.setToolTip(translate('BiblesPlugin.MediaItem', 'Sort bible books alphabetically.'))
        self.book_layout.addWidget(self.book_order_button)
        self.select_layout.addRow(translate('BiblesPlugin.MediaItem', 'Book:'), self.book_layout)
        self.verse_title_layout = QtWidgets.QHBoxLayout()
        self.chapter_label = QtWidgets.QLabel(self.select_tab)
        self.verse_title_layout.addWidget(self.chapter_label)
        self.verse_label = QtWidgets.QLabel(self.select_tab)
        self.verse_title_layout.addWidget(self.verse_label)
        self.select_layout.addRow('', self.verse_title_layout)
        self.from_layout = QtWidgets.QHBoxLayout()
        self.from_chapter = QtWidgets.QComboBox(self.select_tab)
        self.from_layout.addWidget(self.from_chapter)
        self.from_verse = QtWidgets.QComboBox(self.select_tab)
        self.from_layout.addWidget(self.from_verse)
        self.select_layout.addRow(translate('BiblesPlugin.MediaItem', 'From:'), self.from_layout)
        self.to_layout = QtWidgets.QHBoxLayout()
        self.to_chapter = QtWidgets.QComboBox(self.select_tab)
        self.to_layout.addWidget(self.to_chapter)
        self.to_verse = QtWidgets.QComboBox(self.select_tab)
        self.to_layout.addWidget(self.to_verse)
        self.select_layout.addRow(translate('BiblesPlugin.MediaItem', 'To:'), self.to_layout)
        self.select_tab.setVisible(False)
        self.page_layout.addWidget(self.select_tab)
        # General Search Opions
        self.options_tab = QtWidgets.QWidget()
        self.options_tab.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
        self.search_tab_bar.addTab(translate('BiblesPlugin.MediaItem', 'Options'))
        self.general_bible_layout = QtWidgets.QFormLayout(self.options_tab)
        self.version_combo_box = create_horizontal_adjusting_combo_box(self, 'version_combo_box')
        self.general_bible_layout.addRow('{version}:'.format(version=UiStrings().Version), self.version_combo_box)
        self.second_combo_box = create_horizontal_adjusting_combo_box(self, 'second_combo_box')
        self.general_bible_layout.addRow(translate('BiblesPlugin.MediaItem', 'Second:'), self.second_combo_box)
        self.style_combo_box = create_horizontal_adjusting_combo_box(self, 'style_combo_box')
        self.style_combo_box.addItems(['', '', '', ''])
        self.general_bible_layout.addRow(UiStrings().LayoutStyle, self.style_combo_box)
        self.options_tab.setVisible(False)
        self.page_layout.addWidget(self.options_tab)
        # This widget is the easier way to reset the spacing of search_button_layout. (Because page_layout has had its
        # spacing set to 0)
        self.search_button_widget = QtWidgets.QWidget()
        self.search_button_layout = QtWidgets.QHBoxLayout(self.search_button_widget)
        self.search_button_layout.addStretch()
        # Note: If we use QPushButton instead of the QToolButton, the icon will be larger than the Lock icon.
        self.clear_button = QtWidgets.QPushButton()
        self.clear_button.setIcon(self.clear_icon)
        self.save_results_button = QtWidgets.QPushButton()
        self.save_results_button.setIcon(self.save_results_icon)
        self.search_button_layout.addWidget(self.clear_button)
        self.search_button_layout.addWidget(self.save_results_button)
        self.search_button = QtWidgets.QPushButton(self)
        self.search_button_layout.addWidget(self.search_button)
        self.page_layout.addWidget(self.search_button_widget)
        self.results_view_tab = QtWidgets.QTabBar(self)
        self.results_view_tab.addTab('')
        self.results_view_tab.addTab('')
        self.results_view_tab.setCurrentIndex(ResultsTab.Search)
        self.page_layout.addWidget(self.results_view_tab)

    def setup_ui(self):
        log.debug('setup_ui')
        super().setup_ui()
        sort_model = QtCore.QSortFilterProxyModel(self.select_book_combo_box)
        model = self.select_book_combo_box.model()
        # Reparent the combo box model to the sort proxy, otherwise it will be deleted when we change the comobox's
        # model
        model.setParent(sort_model)
        sort_model.setSourceModel(model)
        self.select_book_combo_box.setModel(sort_model)

        # Signals & Slots
        # Combo Boxes
        self.select_book_combo_box.activated.connect(self.on_advanced_book_combo_box)
        self.from_chapter.activated.connect(self.on_from_chapter_activated)
        self.from_verse.activated.connect(self.on_from_verse)
        self.to_chapter.activated.connect(self.on_to_chapter)
        self.version_combo_box.currentIndexChanged.connect(self.on_version_combo_box_index_changed)
        self.version_combo_box.currentIndexChanged.connect(self.update_auto_completer)
        self.second_combo_box.currentIndexChanged.connect(self.on_second_combo_box_index_changed)
        self.second_combo_box.currentIndexChanged.connect(self.update_auto_completer)
        self.style_combo_box.currentIndexChanged.connect(self.on_style_combo_box_index_changed)
        self.search_edit.searchTypeChanged.connect(self.update_auto_completer)
        # Buttons
        self.book_order_button.toggled.connect(self.on_book_order_button_toggled)
        self.clear_button.clicked.connect(self.on_clear_button_clicked)
        self.save_results_button.clicked.connect(self.on_save_results_button_clicked)
        self.search_button.clicked.connect(self.on_search_button_clicked)
        # Other stuff
        self.search_edit.returnPressed.connect(self.on_search_button_clicked)
        self.search_tab_bar.currentChanged.connect(self.on_search_tab_bar_current_changed)
        self.results_view_tab.currentChanged.connect(self.on_results_view_tab_current_changed)
        self.search_edit.textChanged.connect(self.on_search_edit_text_changed)
        self.on_results_view_tab_total_update(ResultsTab.Saved)
        self.on_results_view_tab_total_update(ResultsTab.Search)

    def retranslate_ui(self):
        log.debug('retranslate_ui')
        self.chapter_label.setText(translate('BiblesPlugin.MediaItem', 'Chapter:'))
        self.verse_label.setText(translate('BiblesPlugin.MediaItem', 'Verse:'))
        self.style_combo_box.setItemText(LayoutStyle.VersePerSlide, UiStrings().VersePerSlide)
        self.style_combo_box.setItemText(LayoutStyle.VersePerLine, UiStrings().VersePerLine)
        self.style_combo_box.setItemText(LayoutStyle.Continuous, UiStrings().Continuous)
        self.style_combo_box.setItemText(LayoutStyle.WholeVerseContinuous, UiStrings().WholeVerseContinuous)
        self.clear_button.setToolTip(translate('BiblesPlugin.MediaItem', 'Clear the results on the current tab.'))
        self.save_results_button.setToolTip(
            translate('BiblesPlugin.MediaItem', 'Add the search results to the saved list.'))
        self.search_button.setText(UiStrings().Search)

    def on_focus(self):
        """
        Set focus on the appropriate widget when BibleMediaItem receives focus

        Reimplements MediaManagerItem.on_focus()

        :return: None
        """
        log.debug('on_focus')
        if self.search_tab.isVisible():
            self.search_edit.setFocus()
            self.search_edit.selectAll()
        if self.select_tab.isVisible():
            self.select_book_combo_box.setFocus()
        if self.options_tab.isVisible():
            self.version_combo_box.setFocus()

    def config_update(self):
        """
        Change the visible widgets when the config changes

        :return: None
        """
        log.debug('config_update')
        visible = self.settings.value('bibles/second bibles')
        self.general_bible_layout.labelForField(self.second_combo_box).setVisible(visible)
        self.second_combo_box.setVisible(visible)
        layout_style = self.settings.value('bibles/verse layout style')
        if layout_style is not None:
            self.style_combo_box.setCurrentIndex(layout_style)

    def initialise(self):
        """
        Called to complete initialisation that could not be completed in the constructor.

        :return: None
        """
        log.debug('bible manager initialise')
        self.plugin.manager.media = self
        self.populate_bible_combo_boxes()
        self.search_edit.set_search_types([
            (BibleSearch.Combined, UiIcons().search_comb,
             translate('BiblesPlugin.MediaItem', 'Text or Reference'),
             translate('BiblesPlugin.MediaItem', 'Text or Reference...')),
            (BibleSearch.Reference, UiIcons().search_ref,
             translate('BiblesPlugin.MediaItem', 'Scripture Reference'),
             translate('BiblesPlugin.MediaItem', 'Search Scripture Reference...')),
            (BibleSearch.Text, UiIcons().text,
             translate('BiblesPlugin.MediaItem', 'Text Search'),
             translate('BiblesPlugin.MediaItem', 'Search Text...'))
        ])
        if self.settings.value('bibles/reset to combined quick search'):
            self.search_edit.set_current_search_type(BibleSearch.Combined)
        self.config_update()
        log.debug('bible manager initialise complete')

    def populate_bible_combo_boxes(self):
        """
        Populate the bible combo boxes with the list of bibles that have been loaded

        :return: None
        """
        log.debug('Loading Bibles')
        self.version_combo_box.blockSignals(True)
        self.second_combo_box.blockSignals(True)
        self.version_combo_box.clear()
        self.second_combo_box.clear()
        self.second_combo_box.addItem('', None)
        # Get all bibles and sort the list.
        bibles = self.plugin.manager.get_bibles()
        bibles = [(_f, bibles[_f]) for _f in bibles if _f]
        bibles.sort(key=lambda k: get_locale_key(k[0]))
        for bible in bibles:
            self.version_combo_box.addItem(bible[0], bible[1])
            self.second_combo_box.addItem(bible[0], bible[1])
        self.version_combo_box.blockSignals(False)
        self.second_combo_box.blockSignals(False)
        # set the default value
        bible = self.settings.value('bibles/primary bible')
        second_bible = self.settings.value('bibles/second bible')
        find_and_set_in_combo_box(self.version_combo_box, bible)
        find_and_set_in_combo_box(self.second_combo_box, second_bible)
        # make sure the selected bible ripples down to other gui elements
        self.on_version_combo_box_index_changed()

    def reload_bibles(self):
        """
        Reload the bibles and update the combo boxes

        :return: None
        """
        log.debug('Reloading Bibles')
        self.plugin.manager.reload_bibles()
        self.populate_bible_combo_boxes()

    def get_common_books(self, first_bible, second_bible=None):
        """
        Return a list of common books between two bibles.

        :param first_bible: The first bible (BibleDB)
        :param second_bible: The second bible. (Optional, BibleDB
        :return: A list of common books between the two bibles. Or if only one bible is supplied a list of that bibles
                books (list of Book objects)
        """
        if not second_bible:
            return first_bible.get_books()
        book_data = []
        for book in first_bible.get_books():
            for second_book in second_bible.get_books():
                if book.book_reference_id == second_book.book_reference_id:
                    book_data.append(book)
        return book_data

    def initialise_advanced_bible(self, last_book=None):
        """
        This initialises the given bible, which means that its book names and their chapter numbers is added to the
        combo boxes on the 'Select' Tab. This is not of any importance of the 'Search' Tab.

        :param last_book: The "book reference id" of the book which is chosen at the moment. (int)
        :return: None
        """
        log.debug('initialise_advanced_bible {bible}, {ref}'.format(bible=self.bible, ref=last_book))
        self.select_book_combo_box.clear()
        if self.bible is None:
            return
        book_data = self.get_common_books(self.bible, self.second_bible)
        language_selection = self.plugin.manager.get_language_selection(self.bible.name)
        self.select_book_combo_box.model().setDynamicSortFilter(False)
        for book in book_data:
            self.select_book_combo_box.addItem(book.get_name(language_selection), book.book_reference_id)
        self.select_book_combo_box.model().setDynamicSortFilter(True)
        if last_book:
            index = self.select_book_combo_box.findData(last_book)
            self.select_book_combo_box.setCurrentIndex(index if index != -1 else 0)
        self.on_advanced_book_combo_box()

    def update_auto_completer(self):
        """
        This updates the bible book completion list for the search field. The completion depends on the bible. It is
        only updated when we are doing reference or combined search, in text search the completion list is removed.

        :return: None
        """
        books = []
        # We have to do a 'Reference Search' (Or as part of Combined Search).
        if self.search_edit.current_search_type() is not BibleSearch.Text:
            if self.bible:
                book_data = self.get_common_books(self.bible, self.second_bible)
                language_selection = self.plugin.manager.get_language_selection(self.bible.name)
                # Get book names + add a space to the end. Thus Psalm23 becomes Psalm 23
                # when auto complete is used and user does not need to add the space manually.
                books = [book.get_name(language_selection) + ' ' for book in book_data]
                books.sort(key=get_locale_key)
        set_case_insensitive_completer(books, self.search_edit)

    def on_import_click(self):
        """
        Create, if not already, the `BibleImportForm` and execute it

        :return: None
        """
        log.debug('on_import_click')
        if not hasattr(self, 'import_wizard'):
            self.import_wizard = BibleImportForm(self, self.plugin.manager, self.plugin)
        # If the import was not cancelled then reload.
        if self.import_wizard.exec():
            self.reload_bibles()
        else:
            log.debug('on_import_click: user cancelled the import wizard')

    def on_edit_click(self):
        """
        Load the EditBibleForm and reload the bibles if the user accepts it

        :return: None
        """
        log.debug('on_edit_click')
        if self.bible:
            self.edit_bible_form = EditBibleForm(self, self.main_window, self.plugin.manager)
            self.edit_bible_form.load_bible(self.bible.name)
            if self.edit_bible_form.exec():
                self.reload_bibles()

    def on_delete_click(self):
        """
        Confirm that the user wants to delete the main bible

        :return: None
        """
        log.debug('on_delete_click')
        if self.bible:
            if QtWidgets.QMessageBox.question(
                    self, UiStrings().ConfirmDelete,
                    translate('BiblesPlugin.MediaItem',
                              'Are you sure you want to completely delete "{bible}" Bible from OpenLP?\n\n'
                              'You will need to re-import this Bible to use it again.').format(bible=self.bible.name),
                    defaultButton=QtWidgets.QMessageBox.StandardButton.No) == QtWidgets.QMessageBox.StandardButton.No:
                log.debug('on_delete_click: user cancelled deleting {bible}'.format(bible=self.bible.name))
                return
            log.debug('on_delete_click: deleting {bible}'.format(bible=self.bible.name))
            self.plugin.manager.delete_bible(self.bible.name)
            self.reload_bibles()

    def on_search_tab_bar_current_changed(self, index):
        """
        Show the selected tab and set focus to it

        :param int index: The tab selected
        :return: None
        """
        if index == SearchTabs.Search or index == SearchTabs.Select:
            self.search_button.setEnabled(True)
        else:
            self.search_button.setEnabled(False)
        self.search_tab.setVisible(index == SearchTabs.Search)
        self.select_tab.setVisible(index == SearchTabs.Select)
        self.options_tab.setVisible(index == SearchTabs.Options)
        self.on_focus()

    def on_results_view_tab_current_changed(self, index):
        """
        Update list_widget with the contents of the selected list

        :param index: The index of the tab that has been changed to. (int)
        :rtype: None
        """
        if index == ResultsTab.Saved:
            self.add_built_results_to_list_widget(self.saved_results)
        elif index == ResultsTab.Search:
            self.add_built_results_to_list_widget(self.current_results)

    def on_results_view_tab_total_update(self, index):
        """
        Update the result total count on the tab with the given index.

        :param index: Index of the tab to update (int)
        :return: None
        """
        string = ''
        count = 0
        if index == ResultsTab.Saved:
            string = translate('BiblesPlugin.MediaItem', 'Saved ({result_count})')
            count = len(self.saved_results)
        elif index == ResultsTab.Search:
            string = translate('BiblesPlugin.MediaItem', 'Results ({result_count})')
            count = len(self.current_results)
        self.results_view_tab.setTabText(index, string.format(result_count=count))

    def on_book_order_button_toggled(self, checked):
        """
        Change the sort order of the book names

        :param checked: Indicates if the button is checked or not (Bool)
        :return: None
        """
        if checked:
            self.select_book_combo_box.model().sort(0)
        else:
            # -1 Removes the sorting, and returns the items to the order they were added in
            self.select_book_combo_box.model().sort(-1)

    def on_clear_button_clicked(self):
        """
        Clear the list_view and the search_edit

        :return: None
        """
        current_index = self.results_view_tab.currentIndex()
        for item in self.list_view.selectedItems():
            self.list_view.takeItem(self.list_view.row(item))
        results = [item.data(QtCore.Qt.ItemDataRole.UserRole) for item in self.list_view.allItems()]
        if current_index == ResultsTab.Saved:
            self.saved_results = results
        elif current_index == ResultsTab.Search:
            self.current_results = results
        self.on_results_view_tab_total_update(current_index)

    def on_save_results_button_clicked(self):
        """
        Add the selected verses to the saved_results list.

        :return: None
        """
        for verse in self.list_view.selectedItems():
            self.saved_results.append(verse.data(QtCore.Qt.ItemDataRole.UserRole))
        self.on_results_view_tab_total_update(ResultsTab.Saved)

    def on_style_combo_box_index_changed(self, index):
        """
        Change the layout style and save the setting

        :param index: The index of the current item in the combobox (int)
        :return: None
        """
        # TODO: Change layout_style to a property
        self.settings_tab.layout_style = index
        self.settings_tab.layout_style_combo_box.setCurrentIndex(index)
        self.settings.setValue('bibles/verse layout style', self.settings_tab.layout_style)

    def on_version_combo_box_index_changed(self):
        """
        Update the main bible and save it to settings

        :return: None
        """
        self.bible = self.version_combo_box.currentData()
        if self.bible is not None:
            self.settings.setValue('bibles/primary bible', self.bible.name)
        self.initialise_advanced_bible(self.select_book_combo_box.currentData())

    def on_second_combo_box_index_changed(self, selection):
        """
        Update the second bible. If changing from single to dual bible modes as if the user wants to clear the search
        results, if not revert to the previously selected bible

        :param: selection not required by part of the signature
        :return: None
        """
        new_selection = self.second_combo_box.currentData()
        if self.saved_results:
            # Exclusive or (^) the new and previous selections to detect if the user has switched between single and
            # dual bible mode
            if (new_selection is None) ^ (self.second_bible is None):
                if critical_error_message_box(
                        message=translate('BiblesPlugin.MediaItem',
                                          'OpenLP cannot combine single and dual Bible verse search results. '
                                          'Do you want to clear your saved results?'),
                        parent=self, question=True) == QtWidgets.QMessageBox.StandardButton.Yes:
                    self.saved_results = []
                    self.on_results_view_tab_total_update(ResultsTab.Saved)
                else:
                    self.second_combo_box.setCurrentIndex(self.second_combo_box.findData(self.second_bible))
                    return
        self.second_bible = new_selection
        if new_selection is None:
            self.style_combo_box.setEnabled(True)
            self.settings.setValue('bibles/second bible', None)
        else:
            self.style_combo_box.setEnabled(False)
            self.settings.setValue('bibles/second bible', self.second_bible.name)
            if bible := self.select_book_combo_box.currentData():
                self.initialise_advanced_bible(bible)

    def on_advanced_book_combo_box(self):
        """
        Update the verse selection boxes

        :return: None
        """
        book_ref_id = self.select_book_combo_box.currentData()
        if not book_ref_id:
            # If there is no book selected, just exit early
            return
        book = self.plugin.manager.get_book_by_id(self.bible.name, book_ref_id)
        self.chapter_count = self.plugin.manager.get_chapter_count(self.bible.name, book)
        verse_count = self.plugin.manager.get_verse_count_by_book_ref_id(self.bible.name, book_ref_id, 1)
        if verse_count == 0:
            self.search_button.setEnabled(False)
            log.warning('Not enough chapters in %s', book_ref_id)
            critical_error_message_box(message=translate('BiblesPlugin.MediaItem', 'Bible not fully loaded.'))
        else:
            if self.select_tab.isVisible():
                self.search_button.setEnabled(True)
            self.adjust_combo_box(1, self.chapter_count, self.from_chapter)
            self.adjust_combo_box(1, self.chapter_count, self.to_chapter)
            self.adjust_combo_box(1, verse_count, self.from_verse)
            self.adjust_combo_box(1, verse_count, self.to_verse)

    def on_from_chapter_activated(self):
        """
        Update the verse selection boxes

        :return: None
        """
        book_ref_id = self.select_book_combo_box.currentData()
        chapter_from = self.from_chapter.currentData()
        chapter_to = self.to_chapter.currentData()
        verse_count = self.plugin.manager.get_verse_count_by_book_ref_id(self.bible.name, book_ref_id, chapter_from)
        self.adjust_combo_box(1, verse_count, self.from_verse)
        if chapter_from >= chapter_to:
            self.adjust_combo_box(1, verse_count, self.to_verse, chapter_from == chapter_to)
        self.adjust_combo_box(chapter_from, self.chapter_count, self.to_chapter, chapter_from < chapter_to)

    def on_from_verse(self):
        """
        Update the verse selection boxes

        :return: None
        """
        chapter_from = self.from_chapter.currentData()
        chapter_to = self.to_chapter.currentData()
        if chapter_from == chapter_to:
            book_ref_id = self.select_book_combo_box.currentData()
            verse_from = self.from_verse.currentData()
            verse_count = self.plugin.manager.get_verse_count_by_book_ref_id(self.bible.name, book_ref_id, chapter_to)
            self.adjust_combo_box(verse_from, verse_count, self.to_verse, True)

    def on_to_chapter(self):
        """
        Update the verse selection boxes

        :return: None
        """
        book_ref_id = self.select_book_combo_box.currentData()
        chapter_from = self.from_chapter.currentData()
        chapter_to = self.to_chapter.currentData()
        verse_from = self.from_verse.currentData()
        verse_to = self.to_verse.currentData()
        verse_count = self.plugin.manager.get_verse_count_by_book_ref_id(self.bible.name, book_ref_id, chapter_to)
        if chapter_from == chapter_to and verse_from > verse_to:
            self.adjust_combo_box(verse_from, verse_count, self.to_verse)
        else:
            self.adjust_combo_box(1, verse_count, self.to_verse)

    def adjust_combo_box(self, range_from, range_to, combo, restore=False):
        """
        Adjusts the given como box to the given values.

        :param range_from: The first number of the range (int).
        :param range_to: The last number of the range (int).
        :param combo: The combo box itself (QComboBox).
        :param restore: If True, then the combo's currentText will be restored after adjusting (if possible).
        """
        log.debug('adjust_combo_box {box}, {start}, {end}'.format(box=combo, start=range_from, end=range_to))
        if restore:
            old_selection = combo.currentData()
        combo.clear()
        for item in range(range_from, range_to + 1):
            combo.addItem(str(item), item)
        if restore:
            index = combo.findData(old_selection)
            combo.setCurrentIndex(index if index != -1 else 0)

    def on_search_button_clicked(self):
        """
        Call the correct search function depending on which tab the user is using

        :return: None
        """
        log.debug('on_search_button_clicked')
        if self.search_timer is not None:
            self.search_timer.stop()
        self.search_status = SearchStatus.SearchButton
        if not self.bible:
            log.debug('on_search_button_clicked: no bible selected')
            self.main_window.information_message(UiStrings().BibleNoBiblesTitle, UiStrings().BibleNoBibles)
            return
        if hasattr(self, 'list_view'):
            self.list_view.set_loading_state(True)
        self.search_button.setEnabled(False)
        self.application.set_busy_cursor()
        self.application.process_events()
        try:
            if self.search_tab.isVisible():
                self.text_search()
            elif self.select_tab.isVisible():
                self.select_search()
            self.results_view_tab.setCurrentIndex(ResultsTab.Search)
        finally:
            self.search_button.setEnabled(True)
            self.application.set_normal_cursor()
            if hasattr(self, 'list_view'):
                self.list_view.set_loading_state(False)

    def select_search(self):
        """
        Preform a search using the passage selected on the `Select` tab

        :return: None
        """
        log.debug('select_search')
        verse_range = self.plugin.manager.process_verse_range(
            self.select_book_combo_box.currentData(), self.from_chapter.currentData(), self.from_verse.currentData(),
            self.to_chapter.currentData(), self.to_verse.currentData())
        self.search_results = self.plugin.manager.get_verses(self.bible.name, verse_range, False)
        if self.second_bible:
            self.second_search_results = self.plugin.manager.get_verses(self.second_bible.name, verse_range, False)
        self.display_results()

    def text_reference_search(self, search_text):
        """
        We are doing a 'Reference Search'.
        This search is called on def text_search by Reference and Combined Searches.

        :return: None
        """
        log.debug('text_reference_search: "{text}"'.format(text=search_text))
        self.search_results = []
        verse_refs = self.plugin.manager.parse_ref(self.bible.name, search_text)
        self.search_results = self.plugin.manager.get_verses(self.bible.name, verse_refs, True)
        if self.second_bible and self.search_results:
            self.second_search_results = self.plugin.manager.get_verses(self.second_bible.name, verse_refs, True)
        self.display_results()

    def on_text_search(self, text):
        """
        We are doing a 'Text Search'.
        This search is called on def text_search by 'Search' Text and Combined Searches.
        """
        log.debug('on_text_search: "{text}"'.format(text=text))
        self.search_results = self.plugin.manager.verse_search(self.bible.name, text)
        if self.search_results is None:
            return
        if self.second_bible and self.search_results:
            filtered_search_results = []
            not_found_count = 0
            for verse in self.search_results:
                second_verse = self.second_bible.get_verses(
                    [(verse.book.book_reference_id, verse.chapter, verse.verse, verse.verse)], False)
                if second_verse:
                    filtered_search_results.append(verse)
                    self.second_search_results += second_verse
                else:
                    log.debug('Verse "{name} {chapter:d}:{verse:d}" not found in Second Bible "{bible_name}"'.format(
                        name=verse.book.name, chapter=verse.chapter,
                        verse=verse.verse, bible_name=self.second_bible.name))
                    not_found_count += 1
            self.search_results = filtered_search_results
            if not_found_count != 0 and self.search_status == SearchStatus.SearchButton:
                self.main_window.information_message(
                    translate('BiblesPlugin.MediaItem', 'Verses not found'),
                    translate('BiblesPlugin.MediaItem',
                              'The second Bible "{second_name}" does not contain all the verses that are in the main '
                              'Bible "{name}".\nOnly verses found in both Bibles will be shown.\n\n'
                              '{count:d} verses have not been included in the results.'
                              ).format(second_name=self.second_bible.name, name=self.bible.name, count=not_found_count))
        log.debug('on_text_search complete: {count} result(s)'.format(count=len(self.search_results)))
        self.display_results()

    def text_search(self):
        """
        This triggers the proper 'Search' search based on which search type is used.
        "Eg. "Reference Search", "Text Search" or "Combined search".
        """
        self.search_results = []
        log.debug('text_search called')
        text = self.search_edit.text()
        if text == '':
            self.display_results()
            return
        self.on_results_view_tab_total_update(ResultsTab.Search)
        if self.search_edit.current_search_type() == BibleSearch.Reference:
            if get_reference_match('full').match(text):
                # Valid reference found. Do reference search.
                self.text_reference_search(text)
            elif self.search_status == SearchStatus.SearchButton:
                self.main_window.information_message(
                    translate('BiblesPlugin.BibleManager', 'Scripture Reference Error'),
                    translate('BiblesPlugin.BibleManager',
                              '<strong>The reference you typed is invalid!<br><br>'
                              'Please make sure that your reference follows one of these patterns:</strong><br><br>%s')
                    % UiStrings().BibleScriptureError % get_reference_separators())
        elif self.search_edit.current_search_type() == BibleSearch.Combined and get_reference_match('full').match(text):
            # Valid reference found. Do reference search.
            self.text_reference_search(text)
        else:
            # It can only be a 'Combined' search without a valid reference, or a 'Text' search
            if self.search_status == SearchStatus.SearchAsYouType:
                if len(text) <= 8:
                    self.search_status = SearchStatus.NotEnoughText
                    self.display_results()
                    return
            if VALID_TEXT_SEARCH.search(text):
                self.on_text_search(text)

    def on_search_edit_text_changed(self):
        """
        If 'search_as_you_type' is enabled, start a timer when the search_edit emits a textChanged signal. This is to
        prevent overloading the system by submitting too many search requests in a short space of time.

        :return: None
        """
        if not self.settings.value('bibles/is search while typing enabled') or \
                not self.bible or self.bible.is_web_bible or \
                (self.second_bible and self.bible.is_web_bible):
            return
        self.start_debounced_search(self.search_timer)

    def on_search_timer_timeout(self):
        """
        Perform a search when the search timer timeouts. The search timer is used for 'search_as_you_type' so that we
        don't overload the system buy submitting too many search requests in a short space of time.

        :return: None
        """
        if hasattr(self, 'list_view'):
            self.list_view.set_loading_state(True)
        try:
            self.search_status = SearchStatus.SearchAsYouType
            self.text_search()
            self.results_view_tab.setCurrentIndex(ResultsTab.Search)
        finally:
            if hasattr(self, 'list_view'):
                self.list_view.set_loading_state(False)

    def display_results(self):
        """
        Add the search results to the media manager list.

        :return: None
        """
        log.debug('display_results: {count} result(s)'.format(count=len(self.search_results)))
        self.current_results = self.build_display_results(self.bible, self.second_bible, self.search_results)
        self.search_results = []
        self.add_built_results_to_list_widget(self.current_results)

    def add_built_results_to_list_widget(self, results):
        self.list_view.clear(self.search_status == SearchStatus.NotEnoughText)
        for item in self.build_list_widget_items(results):
            self.list_view.addItem(item)
        self.list_view.selectAll()
        self.on_results_view_tab_total_update(ResultsTab.Search)

    def build_display_results(self, bible, second_bible, search_results):
        """
        Displays the search results in the media manager. All data needed for further action is saved for/in each row.
        """
        verse_separator = get_reference_separators()['verse']
        version = self.plugin.manager.get_meta_data(self.bible.name, 'name').value
        copyright = self.plugin.manager.get_meta_data(self.bible.name, 'copyright').value
        permissions = self.plugin.manager.get_meta_data(self.bible.name, 'permissions').value
        second_name = ''
        second_version = ''
        second_copyright = ''
        second_permissions = ''
        if second_bible:
            second_name = second_bible.name
            second_version = self.plugin.manager.get_meta_data(self.second_bible.name, 'name').value
            second_copyright = self.plugin.manager.get_meta_data(self.second_bible.name, 'copyright').value
            second_permissions = self.plugin.manager.get_meta_data(self.second_bible.name, 'permissions').value
        items = []
        language_selection = self.plugin.manager.get_language_selection(self.bible.name)
        for count, verse in enumerate(search_results):
            data = {
                'book': verse.book.get_name(language_selection),
                'book_abbreviation': BiblesResourcesDB.get_book_by_id(verse.book.book_reference_id)['abbreviation'],
                'chapter': verse.chapter,
                'verse': verse.verse,
                'bible': self.bible.name,
                'version': version,
                'copyright': copyright,
                'permissions': permissions,
                'text': verse.text,
                'second_bible': second_name,
                'second_version': second_version,
                'second_copyright': second_copyright,
                'second_permissions': second_permissions,
                'second_text': ''
            }

            if second_bible:
                try:
                    data['second_text'] = self.second_search_results[count].text
                except IndexError:
                    log.exception('The second_search_results does not have as many verses as the search_results.')
                    break
                except TypeError:
                    log.exception('The second_search_results does not have this book.')
                    break
                bible_text = '{book} {chapter:d}{sep}{verse:d} ({version}, {second_version})'
            else:
                bible_text = '{book} {chapter:d}{sep}{verse:d} ({version})'
            data['item_title'] = bible_text.format(sep=verse_separator, **data)
            items.append(data)
        return items

    def build_list_widget_items(self, items):
        list_widget_items = []
        for data in items:
            bible_verse = QtWidgets.QListWidgetItem(data['item_title'])
            bible_verse.setData(QtCore.Qt.ItemDataRole.UserRole, data)
            list_widget_items.append(bible_verse)
        return list_widget_items

    def generate_slide_data(self, service_item, *, item=None, remote=False, context=ServiceItemContext.Service,
                            **kwargs):
        """
        Generate the slide data. Needs to be implemented by the plugin.

        :param service_item: The service item to be built on
        :param item: The Bible items to be used
        :param remote: Triggered from remote
        :param context: Why is it being generated
        :param kwargs: Consume other unused args specified by the base implementation, but not use by this one.
        """
        log.debug('generating slide data')
        if item:
            items = item
        else:
            items = self.list_view.selectedItems()
        if not items:
            log.debug('generate_slide_data: no items selected')
            return False
        bible_text = ''
        old_chapter = -1
        raw_slides = []
        verses = VerseReferenceList()
        for bitem in items:
            data = bitem.data(QtCore.Qt.ItemDataRole.UserRole)
            verses.add(
                data['book'], data['chapter'], data['verse'], data['version'], data['copyright'], data['permissions'])
            verse_text = self.format_verse(old_chapter, data['chapter'], data['verse'])
            reference = self.format_verse_reference(data['book_abbreviation'], data['chapter'], data['verse'])
            # We only support 'Verse Per Slide' when using a scond bible
            if data['second_bible']:
                second_text = self.format_verse(old_chapter, data['chapter'], data['verse'])
                bible_text = '{first_version}{data[text]}{reference}\n\n{second_version}{data[second_text]}' \
                             '{reference}'.format(first_version=verse_text, second_version=second_text,
                                                  reference=reference,
                                                  data=data)
                raw_slides.append(bible_text.rstrip())
                bible_text = ''
            # If we are 'Verse Per Slide' then create a new slide.
            elif self.settings_tab.layout_style == LayoutStyle.VersePerSlide:
                bible_text = '{first_version}{data[text]}{reference}'.format(
                    first_version=verse_text, data=data, reference=reference)
                raw_slides.append(bible_text.rstrip())
                bible_text = ''
            # If we are 'Verse Per Line' then force a new line.
            elif self.settings_tab.layout_style == LayoutStyle.VersePerLine:
                bible_text = '{bible} {verse}{data[text]}{reference}\n'.format(
                    bible=bible_text, verse=verse_text, data=data, reference=reference)
            elif self.settings_tab.layout_style == LayoutStyle.WholeVerseContinuous:
                bible_text = '{bible} {verse}{data[text]}{reference}\n'.format(
                    bible=bible_text, verse=verse_text, data=data, reference=reference)
            # We have to be 'Continuous'.
            else:
                bible_text = '{bible} {verse}{data[text]}{reference}'.format(
                    bible=bible_text, verse=verse_text, data=data, reference=reference)
            bible_text = bible_text.strip(' ')
            old_chapter = data['chapter']
        # Add service item data (handy things for http api)
        # Bibles in array to make api compatible with any number of bibles.
        bibles = []
        if data['version']:
            bibles.append({
                'version': data['version'],
                'copyright': data['copyright'],
                'permissions': data['permissions']
            })
        if data['second_bible']:
            bibles.append({
                'version': data['second_version'],
                'copyright': data['second_copyright'],
                'permissions': data['second_permissions']
            })
        service_item.data_string = {
            'bibles': bibles
        }
        # Add footer
        if (self.settings_tab.show_reference_in_footer
                and self.settings_tab.reference_placement == ReferencePlacement.Footer):
            service_item.raw_footer.append(verses.format_verses())
        if data['second_bible']:
            verses.add_version(data['second_version'], data['second_copyright'], data['second_permissions'])
        footer_versions = verses.format_versions(version=self.settings_tab.show_version_in_footer,
                                                 copyright=self.settings_tab.show_copyright_in_footer,
                                                 permission=self.settings_tab.show_permission_in_footer)
        if footer_versions:
            service_item.raw_footer.append(footer_versions)
        # If there are no more items we check whether we have to add bible_text.
        if bible_text:
            raw_slides.append(bible_text.lstrip())
        # Service Item: Capabilities
        if self.settings_tab.layout_style == LayoutStyle.Continuous and not data['second_bible']:
            # Split the line but do not replace line breaks in renderer.
            service_item.add_capability(ItemCapabilities.NoLineBreaks)
        if self.settings_tab.layout_style == LayoutStyle.WholeVerseContinuous and not data['second_bible']:
            service_item.add_capability(ItemCapabilities.NoLineBreaks)
            service_item.add_capability(ItemCapabilities.CanWordSplit)
        elif self.settings_tab.layout_style != LayoutStyle.WholeVerseContinuous:
            service_item.add_capability(ItemCapabilities.CanWordSplit)
        service_item.add_capability(ItemCapabilities.CanPreview)
        service_item.add_capability(ItemCapabilities.CanLoop)
        service_item.add_capability(ItemCapabilities.CanEditTitle)
        # Service Item: Title
        service_item.title = '{verse} {version}'.format(verse=verses.format_verses(), version=verses.format_versions())
        # Service Item: Theme
        if self.settings_tab.bible_theme:
            service_item.theme = self.settings_tab.bible_theme
        for slide in raw_slides:
            service_item.add_from_text(slide)
        log.debug('generate_slide_data complete: {count} slide(s)'.format(count=len(raw_slides)))
        return True

    def format_verse(self, old_chapter, chapter, verse):
        """
        Formats and returns the text, each verse starts with, for the given chapter and verse. The text is either
        surrounded by round, square, curly brackets or no brackets at all. For example::

            '{su}1:1{/su}'

        :param old_chapter: The previous verse's chapter number (int).
        :param chapter: The chapter number (int).
        :param verse: The verse number (int).
        :return: An empty or formatted string
        """
        if not self.settings_tab.is_verse_number_visible:
            return ''
        verse_separator = get_reference_separators()['verse']
        if not self.settings_tab.show_new_chapters or old_chapter != chapter:
            verse_text = '{chapter}{sep}{verse}'.format(chapter=chapter, sep=verse_separator, verse=verse)
        else:
            verse_text = verse
        bracket = {
            DisplayStyle.NoBrackets: ('', ''),
            DisplayStyle.Round: ('(', ')'),
            DisplayStyle.Curly: ('{', '}'),
            DisplayStyle.Square: ('[', ']')
        }[self.settings_tab.display_style]
        return '{{su}}{bracket[0]}{verse_text}{bracket[1]}&nbsp;{{/su}}'.format(verse_text=verse_text, bracket=bracket)

    def format_verse_reference(self, book_abbreviation, chapter, verse):
        """
        Formats and returns a short, superscript reference to be shown inline after a verse's text, when
        "Reference placement" is set to Inline. For example::

            '{su}&nbsp;Gen&nbsp;1:1{/su}'

        Uses ``&nbsp;`` (not a literal space) around the marker so the word-wrap/pagination in
        core/display/render.py can never strand the reference on its own, or split it away from the verse
        text it belongs to, when a slide overflows mid-verse.

        :param book_abbreviation: The short form of the book name (e.g. 'Gen').
        :param chapter: The chapter number (int).
        :param verse: The verse number (int).
        :return: An empty string, or a formatted, superscript reference string.
        """
        if self.settings_tab.reference_placement != ReferencePlacement.Inline:
            return ''
        verse_separator = get_reference_separators()['verse']
        return '{{su}}&nbsp;{book}&nbsp;{chapter}{sep}{verse}{{/su}}'.format(
            book=book_abbreviation, chapter=chapter, sep=verse_separator, verse=verse)

    def search_options(self, option=None):
        """
        Returns a list of search options and values for bibles

        :param option: Can be set to an option to only return that option
        """
        if (option is not None and option != 'primary bible'):
            return []
        bibles = list(self.plugin.manager.get_bibles().keys())
        primary = Registry().get('settings').value('bibles/primary bible')
        return [
            {
                'name': 'primary bible',
                'list': bibles,
                'selected': primary
            }
        ]

    def set_search_option(self, search_option, value):
        """
        Sets a search option

        :param search_option: The option to be set
        :param value: The new value for the search option
        :return: True if the search_option was successfully set
        """
        if search_option == 'primary bible' and value in self.search_options('primary bible')[0]['list']:
            Registry().get('settings').setValue('bibles/primary bible', value)
            Registry().execute('populate_bible_combo_boxes')
            return True
        else:
            return False

    @QtCore.Slot(str, bool, result=list)
    def search(self, string: str, show_error: bool = True) -> list[list[Any]]:
        """
        Search for some Bible verses (by reference).
        :param string: search string
        :param show_error: do we show the error
        :return: the results of the search
        """
        log.debug('search (remote API): "{text}"'.format(text=string))
        if self.bible is None:
            return []
        reference = self.plugin.manager.parse_ref(self.bible.name, string)
        search_results = self.plugin.manager.get_verses(self.bible.name, reference, show_error)
        if search_results:
            verse_text = ' '.join([verse.text for verse in search_results])
            return [[string, verse_text]]
        return []

    def create_item_from_id(self, item_id):
        """
        Create a media item from an item id.
        """
        log.debug('create_item_from_id: {id}'.format(id=item_id))
        if self.bible is None:
            return []
        reference = self.plugin.manager.parse_ref(self.bible.name, item_id)
        search_results = self.plugin.manager.get_verses(self.bible.name, reference, False)
        items = self.build_display_results(self.bible, None, search_results)
        return self.build_list_widget_items(items)
