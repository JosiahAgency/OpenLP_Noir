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
Provides additional classes for working in the library
"""
import os
from pathlib import Path
from typing import Any, List, Optional, Union

from PySide6 import QtCore, QtWidgets

from openlp.core.common import sha256_file_hash
from openlp.core.common.i18n import UiStrings, get_natural_key, translate
from openlp.core.lib import check_item_selected
from openlp.core.lib.mediamanageritem import MediaManagerItem
from openlp.core.lib.plugin import StringContent
from openlp.core.lib.ui import create_widget_action, critical_error_message_box
from openlp.core.ui.folders import AddFolderForm, ChooseFolderForm
from openlp.core.ui.icons import UiIcons
from openlp.core.widgets.views import TreeWidgetWithDnD


class FolderLibraryItem(MediaManagerItem):
    """
    This is a custom MediaManagerItem subclass with support for folders
    """
    def __init__(self, parent, plugin, folder_class, item_class):
        super(FolderLibraryItem, self).__init__(parent, plugin)
        self.manager = self.plugin.manager
        self.choose_folder_form = ChooseFolderForm(self, self.manager, folder_class)
        self.add_folder_form = AddFolderForm(self, self.manager, folder_class)
        self.folder_class = folder_class
        self.item_class = item_class

    @property
    def current_folder(self):
        """
        Returns the currently active folder, or None
        """
        selected_items = self.list_view.selectedItems()
        selected_folder = None
        if selected_items:
            selected_item = selected_items[0]
            if isinstance(selected_item.data(0, QtCore.Qt.ItemDataRole.UserRole), self.item_class):
                selected_item = selected_item.parent()
            if isinstance(selected_item, QtWidgets.QTreeWidgetItem) and \
                    isinstance(selected_item.data(0, QtCore.Qt.ItemDataRole.UserRole), self.folder_class):
                selected_folder = selected_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        return selected_folder

    def retranslate_ui(self):
        """
        This method is called automatically to provide OpenLP with the opportunity to translate the ``MediaManagerItem``
        to another language.
        """
        self.add_folder_action.setText(UiStrings().AddFolder)
        self.add_folder_action.setToolTip(UiStrings().AddFolderDot)

    def create_item_from_id(self, item_id: Any):
        """
        Create a media item from an item id.

        :param item_id: Id to make live
        """
        Item = self.item_class
        if isinstance(item_id, (str, Path)):
            # Probably a file name
            item_data = self.manager.get_object_filtered(Item, Item.file_path == str(item_id))
        else:
            item_data = item_id
        item = QtWidgets.QTreeWidgetItem()
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, item_data)
        return item

    def on_add_folder_click(self):
        """
        Called to add a new folder
        """
        # Syntactic sugar, plus a minor performance optimisation
        Item = self.item_class

        if self.add_folder_form.exec(show_top_level_folder=True, selected_folder=self.current_folder):
            new_folder = self.add_folder_form.new_folder
            if self.manager.save_object(new_folder):
                self.load_list(self.manager.get_all_objects(Item, order_by_ref=Item.file_path))
                self.expand_folder(new_folder.id)
            else:
                critical_error_message_box(
                    message=translate('OpenLP.FolderLibraryItem', 'Could not add the new folder.'))

    def on_delete_click(self):
        """
        Remove an item from the list.
        """
        # Syntactic sugar, plus a minor performance optimisation
        Folder, Item = self.folder_class, self.item_class

        # Turn off auto preview triggers.
        self.list_view.blockSignals(True)
        if check_item_selected(self.list_view,
                               translate('OpenLP.FolderLibraryItem', 'You must select an item or folder to delete.')):
            tree_item_list = self.list_view.selectedItems()
            self.application.set_busy_cursor()
            self.main_window.display_progress_bar(len(tree_item_list))
            for tree_item in tree_item_list:
                if not tree_item:
                    self.main_window.increment_progress_bar()
                    continue
                item = tree_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                if isinstance(item, Item):
                    self.delete_item(item)
                    if not item.folder_id or not tree_item.parent():
                        self.list_view.takeTopLevelItem(self.list_view.indexOfTopLevelItem(tree_item))
                    else:
                        tree_item.parent().removeChild(tree_item)
                    self.manager.delete_object(Item, item.id)
                elif isinstance(item, Folder):
                    if QtWidgets.QMessageBox.question(
                            self.list_view.parent(),
                            translate('OpenLP.FolderLibraryItem', 'Remove folder'),
                            translate('OpenLP.FolderLibraryItem',
                                      'Are you sure you want to remove "{name}" and everything in it?'
                                      ).format(name=item.name)
                    ) == QtWidgets.QMessageBox.StandardButton.Yes:
                        self.recursively_delete_folder(item)
                        self.manager.delete_object(Folder, item.id)
                        if item.parent_id is None:
                            self.list_view.takeTopLevelItem(self.list_view.indexOfTopLevelItem(tree_item))
                        else:
                            tree_item.parent().removeChild(tree_item)
                self.main_window.increment_progress_bar()
            self.main_window.finished_progress_bar()
            self.application.set_normal_cursor()
        self.list_view.blockSignals(False)

    def add_list_view_to_toolbar(self):
        """
        Creates the main widget for listing items.
        """
        # Add the List widget
        self.list_view = TreeWidgetWithDnD(self, self.plugin.name)
        self.list_view.setObjectName('{name}TreeView'.format(name=self.plugin.name))
        # Add to pageLayout
        self.page_layout.addWidget(self.list_view)
        # define and add the context menu
        self.list_view.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        if self.has_edit_icon:
            create_widget_action(
                self.list_view,
                text=self.plugin.get_string(StringContent.Edit)['title'],
                icon=UiIcons().edit,
                triggers=self.on_edit_click)
            create_widget_action(self.list_view, separator=True)
        if self.can_preview:
            create_widget_action(
                self.list_view,
                'listView{name}{preview}Item'.format(name=self.plugin.name.title(),
                                                     preview=StringContent.Preview.title()),
                text=self.plugin.get_string(StringContent.Preview)['title'],
                icon=UiIcons().preview,
                can_shortcuts=True,
                triggers=self.on_preview_click)
        if self.can_make_live:
            create_widget_action(
                self.list_view,
                'listView{name}{live}Item'.format(name=self.plugin.name.title(), live=StringContent.Live.title()),
                text=self.plugin.get_string(StringContent.Live)['title'],
                icon=UiIcons().live,
                can_shortcuts=True,
                category=self.title,
                triggers=self.on_live_click)
        if self.can_add_to_service:
            create_widget_action(
                self.list_view,
                'listView{name}{service}Item'.format(name=self.plugin.name.title(),
                                                     service=StringContent.Service.title()),
                can_shortcuts=True,
                text=self.plugin.get_string(StringContent.Service)['title'],
                icon=UiIcons().add,
                triggers=self.on_add_click)
        if self.add_to_service_item:
            create_widget_action(self.list_view, separator=True)
            create_widget_action(
                self.list_view,
                text=translate('OpenLP.MediaManagerItem', '&Add to selected Service Item'),
                icon=UiIcons().add,
                triggers=self.on_add_edit_click)
            create_widget_action(self.list_view, separator=True)
        if self.has_delete_icon:
            create_widget_action(
                self.list_view,
                'listView{name}{delete}Item'.format(name=self.plugin.name.title(), delete=StringContent.Delete.title()),
                text=self.plugin.get_string(StringContent.Delete)['title'],
                icon=UiIcons().delete,
                can_shortcuts=True, triggers=self.on_delete_click)
        self.add_custom_context_actions()
        # Create the context menu and add all actions from the list_view.
        self.menu = QtWidgets.QMenu()
        self.menu.addActions(self.list_view.actions())
        self.list_view.doubleClicked.connect(self.on_double_clicked)
        self.list_view.itemSelectionChanged.connect(self.on_selection_change)
        self.list_view.customContextMenuRequested.connect(self.context_menu)

    def add_custom_context_actions(self):
        """
        Override this method to add custom context actions
        """
        pass

    def add_middle_header_bar(self):
        """
        Add buttons after the main buttons
        """
        self.add_folder_action = self.toolbar.add_toolbar_action(
            'add_folder_action', icon=UiIcons().folder, triggers=self.on_add_folder_click)

    def add_sub_folders(self, folder_list: List[QtWidgets.QTreeWidgetItem], parent_id: Optional[int] = None):
        """
        Recursively add subfolders to the given parent folder in a QTreeWidget.

        :param folder_list: The List object that contains all QTreeWidgetItems.
        :param parent_folder_id: The ID of the folder that will be added recursively.
        """
        # Syntactic sugar, plus a minor performance optimisation
        Folder = self.folder_class

        folders = self.manager.get_all_objects(Folder, Folder.parent_id == parent_id)
        folders.sort(key=lambda folder_object: get_natural_key(folder_object.name))
        folder_icon = UiIcons().folder
        for folder in folders:
            folder_item = QtWidgets.QTreeWidgetItem()
            folder_item.setText(0, folder.name)
            folder_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, folder)
            folder_item.setIcon(0, folder_icon)
            if parent_id is None:
                self.list_view.addTopLevelItem(folder_item)
            else:
                folder_list[parent_id].addChild(folder_item)
            folder_list[folder.id] = folder_item
            self.add_sub_folders(folder_list, folder.id)

    def expand_folder(self, folder_id: int, root_item: Optional[QtWidgets.QTreeWidgetItem] = None):
        """
        Expand folders in the widget recursively.

        :param folder_id: The ID of the folder that will be expanded.
        :param root_item: This option is only used for recursion purposes.
        """
        return_value = False
        if root_item is None:
            root_item = self.list_view.invisibleRootItem()
        for i in range(root_item.childCount()):
            child = root_item.child(i)
            if self.expand_folder(folder_id, child):
                child.setExpanded(True)
                return_value = True
        if isinstance(root_item.data(0, QtCore.Qt.ItemDataRole.UserRole), self.folder_class):
            if root_item.data(0, QtCore.Qt.ItemDataRole.UserRole).id == folder_id:
                return True
        return return_value

    def recursively_delete_folder(self, folder):
        """
        Recursively deletes a folder and all folders and items in it.

        :param folder: The Folder instance of the folder that will be deleted.
        """
        # Syntactic sugar, plus a minor performance optimisation
        Folder, Item = self.folder_class, self.item_class

        items = self.manager.get_all_objects(Item, Item.folder_id == folder.id)
        for item in items:
            self.delete_item(item)
            self.manager.delete_object(Item, item.id)
        folders = self.manager.get_all_objects(Folder, Folder.parent_id == folder.id)
        for child in folders:
            self.recursively_delete_folder(child)
            self.manager.delete_object(Folder, child.id)

    def file_to_item(self, filename: Union[Path, str]):
        """
        This method allows the media item to convert a string filename into an item class

        Override this method to customise your plugin's loading method
        """
        if isinstance(filename, Path):
            name = filename.name
            filename = str(filename)
        else:
            name = os.path.basename(filename)
        item = self.item_class(name=name, file_path=filename)
        self.manager.save_object(item)
        return item

    def load_item(self, item, is_initial_load=False):
        """
        This method allows the media item to set up the QTreeWidgetItem the way it wants
        """
        raise NotImplementedError('load_item needs to be implemented by the descendant class')

    def delete_item(self, item):
        """
        This method allows the media item to delete the Item
        """
        raise NotImplementedError('delete_item needs to be implemented by the descendant class')

    def load_list(self, items, is_initial_load=False, target_folder=None):
        """
        Load the list of items into the tree view

        :param items: The items to load
        :param target_folder: The folder to load the items into
        """
        if not is_initial_load:
            self.application.set_busy_cursor()
            self.main_window.display_progress_bar(len(items))
        self.list_view.clear()
        # Load the list of folders and add them to the tree view
        folder_items = {}
        self.add_sub_folders(folder_items, parent_id=None)
        if target_folder is not None:
            self.expand_folder(target_folder.id)
        # Convert any filenames to items
        for counter, filename in enumerate(items):
            if isinstance(filename, (Path, str)):
                items[counter] = self.file_to_item(filename)
        # Sort the files by the filename
        items.sort(key=lambda item: get_natural_key(item if isinstance(item, str) else item.file_path))
        for item in items:
            self.log_debug('Loading item: {name}'.format(name=item.file_path))
            tree_item = self.load_item(item, is_initial_load)
            if not tree_item:
                continue
            elif not item.folder_id or item.folder_id not in folder_items:
                self.list_view.addTopLevelItem(tree_item)
            else:
                folder_items[item.folder_id].addChild(tree_item)
            if not is_initial_load:
                self.main_window.increment_progress_bar()
        if not is_initial_load:
            self.main_window.finished_progress_bar()
        self.application.set_normal_cursor()

    def format_search_result(self, item):
        """
        Format an item for the search results. The default implementation simply returns
        [item.file_path, item.file_path]

        :param Item item: An Item to be formatted
        :return list[str, str]: A list of two items containing the full path and a pretty name
        """
        return [item.file_path, item.file_path]

    @QtCore.Slot(str, bool, result=list)
    def search(self, string: str, show_error: bool = True) -> list[list[Any]]:
        """
        Performs a search for items containing ``string``

        :param string: String to be displayed
        :param show_error: Should the error be shown (True)
        :return: The search result.
        """
        string = string.lower()
        items = self.manager.get_all_objects(self.item_class, self.item_class.file_path.ilike('%' + string + '%'))
        return [self.format_search_result(item) for item in items]

    def validate_and_load(self, file_paths: List[Path], target_folder: Optional[QtWidgets.QTreeWidgetItem] = None):
        """
        Process a list for files either from the File Dialog or from Drag and Drop.
        This method is overloaded from MediaManagerItem.

        :param list[Path] file_paths: A List of paths  to be loaded
        :param target_folder: The QTreeWidgetItem of the folder that will be the parent of the added files
        """
        self.application.set_normal_cursor()
        if target_folder:
            target_folder = target_folder.data(0, QtCore.Qt.ItemDataRole.UserRole)
        elif self.current_folder:
            target_folder = self.current_folder
        if not target_folder and self.choose_folder_form.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            target_folder = self.choose_folder_form.folder
            if self.choose_folder_form.is_new_folder:
                self.manager.save_object(target_folder)
        existing_files = [item.file_path for item in self.manager.get_all_objects(self.item_class)]
        # Convert file paths to items
        for file_path in file_paths:
            if file_paths.count(file_path) > 1 or existing_files.count(file_path) > 0:
                # If a file already exists in the items or has been selected twice, show an error message
                critical_error_message_box(translate('OpenLP.FolderLibraryItem', 'File Exists'),
                                           translate('OpenLP.FolderLibraryItem',
                                                     'An item with that filename already exists.'))
                continue

            self.log_debug('Adding new item: {name}'.format(name=file_path))
            item = self.item_class(name=str(file_path), file_path=str(file_path))
            if isinstance(file_path, Path) and file_path.exists():
                item.file_hash = sha256_file_hash(file_path)
            if target_folder:
                item.folder_id = target_folder.id
            self.manager.save_object(item)
            self.main_window.increment_progress_bar()
        self.load_list(self.manager.get_all_objects(self.item_class, order_by_ref=self.item_class.file_path),
                       target_folder=target_folder)
        last_dir = Path(file_paths[0]).parent
        self.settings.setValue(self.settings_section + '/last directory', last_dir)

    def dnd_move_internal(self, target):
        """
        Handle drag-and-drop moving of items within the media manager

        :param target: This contains the QTreeWidget that is the target of the DnD action
        """
        items_to_move = self.list_view.selectedItems()
        # Determine group to move images to
        target_folder = target
        if target_folder is not None and isinstance(target_folder.data(0, QtCore.Qt.ItemDataRole.UserRole),
                                                    self.item_class):
            target_folder = target.parent()
        # Move to toplevel
        if target_folder is None:
            target_folder = self.list_view.invisibleRootItem()
            target_folder.setData(0, QtCore.Qt.ItemDataRole.UserRole, self.folder_class())
            target_folder.data(0, QtCore.Qt.ItemDataRole.UserRole).id = 0
        # Move images in the treeview
        items_to_save = []
        for item in items_to_move:
            if isinstance(item.data(0, QtCore.Qt.ItemDataRole.UserRole), self.item_class):
                if isinstance(item.parent(), QtWidgets.QTreeWidgetItem):
                    item.parent().removeChild(item)
                else:
                    self.list_view.invisibleRootItem().removeChild(item)
                target_folder.addChild(item)
                item.setSelected(True)
                item_data = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                item_data.folder_id = target_folder.data(0, QtCore.Qt.ItemDataRole.UserRole).id
                items_to_save.append(item_data)
        target_folder.setExpanded(True)
        # Update the folder ID's of the items in the database
        self.manager.save_objects(items_to_save)
        # Sort the target folder
        sort_folders = []
        sort_items = []
        for item in target_folder.takeChildren():
            if isinstance(item.data(0, QtCore.Qt.ItemDataRole.UserRole), self.folder_class):
                sort_folders.append(item)
            if isinstance(item.data(0, QtCore.Qt.ItemDataRole.UserRole), self.item_class):
                sort_items.append(item)
        sort_folders.sort(key=lambda item: get_natural_key(item.text(0)))
        target_folder.addChildren(sort_folders)
        sort_items.sort(key=lambda item: get_natural_key(item.text(0)))
        target_folder.addChildren(sort_items)
