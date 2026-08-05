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
from typing import Any

from PySide6 import QtCore, QtWidgets
from sqlalchemy.sql import and_, func, or_

from openlp.core.common.enum import CustomSearch
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.registry import Registry
from openlp.core.lib import check_item_selected
from openlp.core.lib.mediamanageritem import MediaManagerItem
from openlp.core.lib.plugin import PluginStatus
from openlp.core.lib.serviceitem import ItemCapabilities
from openlp.core.lib.ui import create_widget_action
from openlp.core.ui.icons import UiIcons
from openlp.plugins.custom.forms.editcustomform import EditCustomForm
from openlp.plugins.custom.lib.customxmlhandler import CustomXML
from openlp.plugins.custom.lib.db import CustomSlide

log = logging.getLogger(__name__)


class CustomMediaItem(MediaManagerItem):
    """
    This is the custom media manager item for Custom Slides.
    """
    custom_go_live = QtCore.Signal(list)
    custom_add_to_service = QtCore.Signal(list)
    log.info('Custom Media Item loaded')

    def __init__(self, parent, plugin):
        self.icon_path = 'custom/custom'
        super(CustomMediaItem, self).__init__(parent, plugin)

    def setup_item(self):
        """
        Do some additional setup.
        """
        self.custom_go_live.connect(self.go_live_remote)
        self.custom_add_to_service.connect(self.add_to_service_remote)
        self.edit_custom_form = EditCustomForm(self, self.main_window, self.plugin.db_manager)
        self.single_service_item = False
        self.quick_preview_allowed = True
        self.has_search = True
        self.search_timer = self.create_debounce_timer(self.on_search_timer_timeout)
        # Holds information about whether the edit is remotely triggered and
        # which Custom is required.
        self.remote_custom = -1

    def add_end_header_bar(self):
        """
        Add the Custom End Head bar and register events and functions
        """
        self.toolbar.addSeparator()
        self.add_search_to_toolbar()
        # Signals and slots
        self.search_text_edit.searchTypeChanged.connect(self.on_search_text_button_clicked)
        Registry().register_function('custom_load_list', self.load_list)
        Registry().register_function('custom_preview', self.on_preview_click)
        Registry().register_function('custom_create_from_service', self.create_from_service_item)

    def add_custom_context_actions(self):
        create_widget_action(self.list_view, separator=True)
        create_widget_action(
            self.list_view, text=translate('OpenLP.MediaManagerItem', '&Clone'), icon=UiIcons().clone,
            triggers=self.on_clone_click)

    def config_update(self):
        """
        Config has been updated so reload values
        """
        log.debug('Config loaded')
        self.add_custom_from_service = self.settings.value('custom/add custom from service')
        self.is_search_as_you_type_enabled = self.settings.value('advanced/search as type')

    def retranslate_ui(self):
        """

        """
        self.search_text_label.setText('{text}:'.format(text=UiStrings().Search))
        self.search_text_button.setText(UiStrings().Search)

    def initialise(self):
        """
        Initialise the UI so it can provide Searches
        """
        self.search_text_edit.set_search_types(
            [(CustomSearch.Titles, UiIcons().search, translate('SongsPlugin.MediaItem', 'Titles'),
              translate('SongsPlugin.MediaItem', 'Search Titles...')),
             (CustomSearch.Themes, UiIcons().theme, UiStrings().Themes, UiStrings().SearchThemes)])
        self.load_list(self.plugin.db_manager.get_all_objects(CustomSlide, order_by_ref=CustomSlide.title))
        self.config_update()

    def load_list(self, custom_slides=None, target_group=None):
        # Sort out what custom we want to select after loading the list.
        """

        :param custom_slides:
        :param target_group:
        """
        self.save_auto_select_id()
        self.list_view.clear()
        if not custom_slides:
            custom_slides = self.plugin.db_manager.get_all_objects(CustomSlide, order_by_ref=CustomSlide.title)
        custom_slides.sort()
        for custom_slide in custom_slides:
            custom_name = QtWidgets.QListWidgetItem(custom_slide.title)
            custom_name.setData(QtCore.Qt.ItemDataRole.UserRole, custom_slide.id)
            self.list_view.addItem(custom_name)
            # Auto-select the custom.
            if custom_slide.id == self.auto_select_id:
                self.list_view.setCurrentItem(custom_name)
        self.auto_select_id = -1
        # Called to redisplay the custom list screen edith from a search
        # or from the exit of the Custom edit dialog. If remote editing is
        # active trigger it and clean up so it will not update again.

    def on_new_click(self):
        """
        Handle the New item event
        """
        self.edit_custom_form.load_custom(0)
        self.edit_custom_form.exec()
        self.on_clear_text_button_click()
        self.on_selection_change()

    def on_remote_edit(self, custom_id, preview=False):
        """
        Called by ServiceManager or SlideController by event passing the custom Id in the payload along with an
        indicator to say which type of display is required.

        :param custom_id: The id of the item to be edited
        :param preview: Do we need to update the Preview after the edit. (Default False)
        """
        custom_id = int(custom_id)
        valid = self.plugin.db_manager.get_object(CustomSlide, custom_id)
        if valid:
            self.edit_custom_form.load_custom(custom_id, preview)
            if self.edit_custom_form.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                self.remote_triggered = True
                self.remote_custom = custom_id
                self.auto_select_id = -1
                self.on_search_text_button_clicked()
                item = self.build_service_item(remote=True)
                self.remote_triggered = None
                self.remote_custom = 1
                if item:
                    if preview:
                        # A custom slide can only be edited if it comes from plugin,
                        # so we set it again for the new item.
                        item.from_plugin = True
                    return item
        return None

    def on_edit_click(self):
        """
        Edit a custom item
        """
        if check_item_selected(self.list_view, UiStrings().SelectEdit):
            item = self.list_view.currentItem()
            item_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
            self.edit_custom_form.load_custom(item_id, False)
            self.edit_custom_form.exec()
            self.auto_select_id = -1
            self.on_search_text_button_clicked()

    def on_delete_click(self):
        """
        Remove a custom item from the list and database
        """
        if check_item_selected(self.list_view, UiStrings().SelectDelete):
            items = self.list_view.selectedIndexes()
            if QtWidgets.QMessageBox.question(
                    self, UiStrings().ConfirmDelete,
                    translate('CustomPlugin.MediaItem',
                              'Are you sure you want to delete the "{items:d}" '
                              'selected custom slide(s)?').format(items=len(items)),
                    defaultButton=QtWidgets.QMessageBox.StandardButton.Yes) == QtWidgets.QMessageBox.StandardButton.No:
                return
            row_list = [item.row() for item in self.list_view.selectedIndexes()]
            row_list.sort(reverse=True)
            id_list = [(item.data(QtCore.Qt.ItemDataRole.UserRole)) for item in self.list_view.selectedIndexes()]
            for id in id_list:
                self.plugin.db_manager.delete_object(CustomSlide, id)
                Registry().execute('custom_deleted', id)
            self.on_search_text_button_clicked()

    def on_focus(self):
        """
        Set the focus
        """
        self.search_text_edit.setFocus()
        self.search_text_edit.selectAll()

    def generate_slide_data(self, service_item, *, item=None, **kwargs):
        """
        Generate the slide data. Needs to be implemented by the plugin.
        :param service_item: To be updated
        :param item: The custom database item to be used
        :param kwargs: Consume other unused args specified by the base implementation, but not use by this one.
        """
        item_id = self._get_id_of_item_to_generate(item, self.remote_custom)
        service_item.add_capability(ItemCapabilities.CanEdit)
        service_item.add_capability(ItemCapabilities.CanPreview)
        service_item.add_capability(ItemCapabilities.CanLoop)
        service_item.add_capability(ItemCapabilities.CanSoftBreak)
        service_item.add_capability(ItemCapabilities.OnLoadUpdate)
        service_item.add_capability(ItemCapabilities.CanWordSplit)
        custom_slide = self.plugin.db_manager.get_object(CustomSlide, item_id)
        title = custom_slide.title
        credit = custom_slide.credits
        service_item.edit_id = item_id
        theme = custom_slide.theme_name
        if theme:
            service_item.theme = theme
        custom_xml = CustomXML(custom_slide.text)
        verse_list = custom_xml.get_verses()
        raw_slides = [verse[1] for verse in verse_list]
        service_item.title = title
        for slide in raw_slides:
            service_item.add_from_text(slide)
        if self.settings.value('custom/display footer') or credit:
            service_item.raw_footer.append(' '.join([title, credit]))
        else:
            service_item.raw_footer.append('')
        return True

    def on_clone_click(self):
        """
        Clone the selected Custom item
        """
        item = self.list_view.currentItem()
        item_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        old_custom_slide = self.plugin.db_manager.get_object(CustomSlide, item_id)
        new_custom_slide = CustomSlide(title='{title} <{text}>'.format(title=old_custom_slide.title,
                                                                       text=translate('CustomPlugin.MediaItem',
                                                                                      'copy', 'For item cloning')),
                                       text=old_custom_slide.text,
                                       credits=old_custom_slide.credits,
                                       theme_name=old_custom_slide.theme_name)
        self.plugin.db_manager.save_object(new_custom_slide)
        Registry().execute('custom_changed', new_custom_slide.id)
        self.on_search_text_button_clicked()

    def on_search_text_button_clicked(self):
        """
        Search the plugin database
        """
        self.list_view.set_loading_state(True)
        # Reload the list considering the new search type.
        try:
            search_type = self.search_text_edit.current_search_type()
            search_keywords = '%{search}%'.format(search=self.whitespace.sub(' ', self.search_text_edit.displayText()))
            if search_type == CustomSearch.Titles:
                log.debug('Titles Search')
                search_results = self.plugin.db_manager.get_all_objects(CustomSlide,
                                                                        CustomSlide.title.like(search_keywords),
                                                                        order_by_ref=CustomSlide.title)
                self.load_list(search_results)
            elif search_type == CustomSearch.Themes:
                log.debug('Theme Search')
                search_results = self.plugin.db_manager.get_all_objects(CustomSlide,
                                                                        CustomSlide.theme_name.like(search_keywords),
                                                                        order_by_ref=CustomSlide.title)
                self.load_list(search_results)
        finally:
            self.list_view.set_loading_state(False)

    def on_search_text_edit_changed(self, text):
        """
        If search as type enabled invoke the search on each key press. If the Title is being searched do not start until
        2 characters have been entered.

        :param text: The search text
        """
        if self.is_search_as_you_type_enabled:
            search_length = 2
            if len(text) > search_length:
                self.start_debounced_search(self.search_timer)
            elif not text:
                self.search_timer.stop()
                self.on_clear_text_button_click()

    def on_search_timer_timeout(self):
        """
        Perform a debounced custom-item search.
        """
        self.on_search_text_button_clicked()

    def service_load(self, item):
        """
        Triggered by a custom item being loaded by the service manager.

        :param item: The service Item from the service to load found in the database.
        """
        log.debug('service_load')
        if self.plugin.status != PluginStatus.Active:
            return
        if item.theme:
            custom = self.plugin.db_manager.get_object_filtered(CustomSlide, and_(CustomSlide.title == item.title,
                                                                                  CustomSlide.theme_name == item.theme,
                                                                                  CustomSlide.credits ==
                                                                                  item.raw_footer[0][
                                                                                      len(item.title) + 1:]))
        else:
            custom = self.plugin.db_manager.get_object_filtered(CustomSlide, and_(CustomSlide.title == item.title,
                                                                                  CustomSlide.credits ==
                                                                                  item.raw_footer[0][
                                                                                      len(item.title) + 1:]))
        if custom:
            item.edit_id = custom.id
            return item
        else:
            if self.add_custom_from_service:
                self.create_from_service_item(item)

    def create_from_service_item(self, item):
        """
        Create a custom slide from a text service item

        :param item:  the service item to be converted to a Custom item
        """
        # Create the text
        custom_xml = CustomXML()
        for (idx, slide) in enumerate(item.slides):
            custom_xml.add_verse_to_lyrics('custom', str(idx + 1), slide['text'])
        # Create the credits from the footer
        credits = ''
        footer = ' '.join(item.raw_footer)
        if footer:
            if footer.startswith(item.title):
                credits = footer[len(item.title) + 1:]
            else:
                credits = footer
        custom = CustomSlide(title=item.title, text=str(custom_xml.extract_xml(), 'utf-8'),
                             theme_name=item.theme if item.theme else '', credits=credits)
        self.plugin.db_manager.save_object(custom)
        self.on_search_text_button_clicked()

    def on_clear_text_button_click(self):
        """
        Clear the search text.
        """
        self.search_text_edit.clear()
        self.on_search_text_button_clicked()

    @QtCore.Slot(str, bool, result=list)
    def search(self, string: str, show_error: bool = True) -> list[list[Any]]:
        """
        Search the database for a given item.

        :param string: The search string
        :param show_error: The error string to be show.
        """
        search = '%{search}%'.format(search=string.lower())
        search_results = self.plugin.db_manager.get_all_objects(CustomSlide,
                                                                or_(func.lower(CustomSlide.title).like(search),
                                                                    func.lower(CustomSlide.text).like(search)),
                                                                order_by_ref=CustomSlide.title)
        return [[custom.id, custom.title] for custom in search_results]
