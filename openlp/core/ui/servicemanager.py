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
The service manager sets up, loads, saves and manages services.
"""
import html
import json
import shutil
import os
import zipfile
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common import ThemeLevel, delete_file, sha256_file_hash
from openlp.core.common.actions import ActionList, CategoryOrder
from openlp.core.common.applocation import AppLocation
from openlp.core.common.enum import ServiceItemType
from openlp.core.common.i18n import UiStrings, format_time, translate
from openlp.core.common.json import OpenLPJSONDecoder, OpenLPJSONEncoder
from openlp.core.common.mixins import LogMixin, RegistryProperties
from openlp.core.common.registry import Registry, RegistryBase
from openlp.core.lib import build_icon, ItemCapabilities
from openlp.core.lib.exceptions import ValidationError
from openlp.core.lib.plugin import PluginStatus
from openlp.core.lib.serviceitem import ServiceItem
from openlp.core.lib.ui import create_widget_action, critical_error_message_box, find_and_set_in_combo_box
from openlp.core.state import State
from openlp.core.ui.icons import UiIcons
from openlp.core.ui.media import get_supported_media_suffix
from openlp.core.ui.serviceitemeditform import ServiceItemEditForm
from openlp.core.ui.servicenoteform import ServiceNoteForm
from openlp.core.ui.starttimeform import StartTimeForm
from openlp.core.ui.style import UiThemes, is_ui_theme
from openlp.core.widgets.dialogs import FileDialog
from openlp.core.widgets.toolbar import OpenLPToolbar
from openlp.core.widgets.views import NoirServiceDelegate, SERVICE_LIVE_ROLE, SERVICE_META_ROLE


class ServiceManagerList(QtWidgets.QTreeWidget):
    """
    Set up key bindings and mouse behaviour for the service list
    """
    def __init__(self, service_manager, parent=None):
        """
        Constructor
        """
        super(ServiceManagerList, self).__init__(parent)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.setAlternatingRowColors(True)
        self.setHeaderHidden(True)
        self.setExpandsOnDoubleClick(False)
        self.service_manager = service_manager

    def dragEnterEvent(self, event):
        """
        React to a drag enter event
        """
        event.accept()

    def dragMoveEvent(self, event):
        """
        React to a drage move event
        """
        event.accept()

    def keyPressEvent(self, event):
        """
        Capture Key press and respond accordingly.
        :param event:
        """
        if isinstance(event, QtGui.QKeyEvent):
            # here accept the event and do something
            if event.key() == QtCore.Qt.Key.Key_Up:
                self.service_manager.on_move_selection_up()
                event.accept()
            elif event.key() == QtCore.Qt.Key.Key_Down:
                self.service_manager.on_move_selection_down()
                event.accept()
            elif event.key() == QtCore.Qt.Key.Key_Right:
                self.service_manager.on_expand_selection()
                event.accept()
            elif event.key() == QtCore.Qt.Key.Key_Left:
                self.service_manager.on_collapse_selection()
                event.accept()
            elif event.key() == QtCore.Qt.Key.Key_Delete:
                self.service_manager.on_delete_from_service()
                event.accept()
            event.ignore()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        """
        Drag and drop event does not care what data is selected as the recipient will use events to request the data
        move just tell it what plugin to call
        :param event:
        """
        if event.buttons() != QtCore.Qt.MouseButton.LeftButton:
            event.ignore()
            return
        if not self.itemAt(self.mapFromGlobal(QtGui.QCursor.pos())):
            event.ignore()
            return
        drag = QtGui.QDrag(self)
        mime_data = QtCore.QMimeData()
        drag.setMimeData(mime_data)
        mime_data.setText('ServiceManager')
        drag.exec(QtCore.Qt.DropAction.CopyAction)


class Ui_ServiceManager(object):
    """
    UI part of the Service Manager
    """
    def setup_ui(self, widget):
        """
        Define the UI
        :param widget:
        """
        # start with the layout
        self.layout = QtWidgets.QVBoxLayout(widget)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        # Create the top toolbar
        self.toolbar = OpenLPToolbar(self)
        self.toolbar.add_toolbar_action('newService', text=UiStrings().NewService, icon=UiIcons().new,
                                        tooltip=UiStrings().CreateService, triggers=self.on_new_service_clicked)
        self.toolbar.add_toolbar_action('openService', text=UiStrings().OpenService,
                                        icon=UiIcons().open,
                                        tooltip=translate('OpenLP.ServiceManager', 'Load an existing service.'),
                                        triggers=self.on_load_service_clicked)
        self.toolbar.add_toolbar_action('saveService', text=UiStrings().SaveService,
                                        icon=UiIcons().save,
                                        tooltip=translate('OpenLP.ServiceManager', 'Save this service.'),
                                        triggers=self.decide_save_method)
        self.toolbar.addSeparator()
        self.theme_label = QtWidgets.QLabel('{theme}:'.format(theme=UiStrings().Theme), widget)
        self.theme_label.setContentsMargins(3, 3, 3, 3)
        self.theme_label.setObjectName('theme_label')
        self.toolbar.add_toolbar_widget(self.theme_label)
        self.theme_combo_box = QtWidgets.QComboBox(self.toolbar)
        self.theme_combo_box.setToolTip(translate('OpenLP.ServiceManager', 'Select a theme for the service.'))
        self.theme_combo_box.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.theme_combo_box.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.theme_combo_box.setObjectName('theme_combo_box')
        self.toolbar.add_toolbar_widget(self.theme_combo_box)
        self.toolbar.setObjectName('toolbar')
        self.layout.addWidget(self.toolbar)
        # Create the service manager list
        self.service_manager_list = ServiceManagerList(widget)
        self.service_manager_list.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.CurrentChanged |
            QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked |
            QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed)
        self.service_manager_list.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.service_manager_list.customContextMenuRequested.connect(self.context_menu)
        self.service_manager_list.setObjectName('service_manager_list')
        if is_ui_theme(UiThemes.Noir):
            # The Noir theme paints service items as run-sheet cards with an
            # on-air marker; the delegate needs mouse tracking for hover states
            self.service_manager_list.setItemDelegate(NoirServiceDelegate(self.service_manager_list))
            self.service_manager_list.setMouseTracking(True)
            # The delegate paints all selection states itself; a transparent
            # highlight stops the view painting its own row underlay (which
            # shows beside the cards in the branch column).
            palette = self.service_manager_list.palette()
            palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtCore.Qt.GlobalColor.transparent)
            self.service_manager_list.setPalette(palette)
        # enable drop
        self.service_manager_list.dropEvent = self.drop_event
        self.layout.addWidget(self.service_manager_list)
        # Add the bottom toolbar
        self.order_toolbar = OpenLPToolbar(widget)
        action_list = ActionList.get_instance()
        action_list.add_category(UiStrings().Service, CategoryOrder.standard_toolbar)
        self.move_top_action = self.order_toolbar.add_toolbar_action(
            'moveTop',
            text=translate('OpenLP.ServiceManager', 'Move to &top'), icon=UiIcons().move_start,
            tooltip=translate('OpenLP.ServiceManager', 'Move item to the top of the service.'),
            can_shortcuts=True, category=UiStrings().Service, triggers=self.on_service_top)
        self.move_up_action = self.order_toolbar.add_toolbar_action(
            'moveUp',
            text=translate('OpenLP.ServiceManager', 'Move &up'), icon=UiIcons().move_up,
            tooltip=translate('OpenLP.ServiceManager', 'Move item up one position in the service.'),
            can_shortcuts=True, category=UiStrings().Service, triggers=self.on_service_up)
        self.move_down_action = self.order_toolbar.add_toolbar_action(
            'moveDown',
            text=translate('OpenLP.ServiceManager', 'Move &down'), icon=UiIcons().move_down,
            tooltip=translate('OpenLP.ServiceManager', 'Move item down one position in the service.'),
            can_shortcuts=True, category=UiStrings().Service, triggers=self.on_service_down)
        self.move_bottom_action = self.order_toolbar.add_toolbar_action(
            'moveBottom',
            text=translate('OpenLP.ServiceManager', 'Move to &bottom'), icon=UiIcons().move_end,
            tooltip=translate('OpenLP.ServiceManager', 'Move item to the end of the service.'),
            can_shortcuts=True, category=UiStrings().Service, triggers=self.on_service_end)
        self.order_toolbar.addSeparator()
        self.delete_action = self.order_toolbar.add_toolbar_action(
            'delete', can_shortcuts=True,
            text=translate('OpenLP.ServiceManager', '&Delete From Service'), icon=UiIcons().delete,
            tooltip=translate('OpenLP.ServiceManager', 'Delete the selected item from the service.'),
            triggers=self.on_delete_from_service)
        self.order_toolbar.addSeparator()
        self.expand_action = self.order_toolbar.add_toolbar_action(
            'expand', can_shortcuts=True,
            text=translate('OpenLP.ServiceManager', '&Expand all'), icon=UiIcons().plus,
            tooltip=translate('OpenLP.ServiceManager', 'Expand all the service items.'),
            category=UiStrings().Service, triggers=self.on_expand_all)
        self.collapse_action = self.order_toolbar.add_toolbar_action(
            'collapse', can_shortcuts=True,
            text=translate('OpenLP.ServiceManager', '&Collapse all'), icon=UiIcons().minus,
            tooltip=translate('OpenLP.ServiceManager', 'Collapse all the service items.'),
            category=UiStrings().Service, triggers=self.on_collapse_all)
        self.order_toolbar.addSeparator()
        self.make_live_action = self.order_toolbar.add_toolbar_action(
            'make_live', can_shortcuts=True,
            text=translate('OpenLP.ServiceManager', 'Go Live'), icon=UiIcons().live,
            tooltip=translate('OpenLP.ServiceManager', 'Send the selected item to Live.'),
            category=UiStrings().Service,
            triggers=self.on_make_live_action_triggered)
        self.layout.addWidget(self.order_toolbar)
        # Connect up our signals and slots
        self.theme_combo_box.activated.connect(self.on_theme_combo_box_selected)
        self.service_manager_list.doubleClicked.connect(self.on_double_click_live)
        self.service_manager_list.clicked.connect(self.on_single_click_preview)
        self.service_manager_list.itemCollapsed.connect(self.collapsed)
        self.service_manager_list.itemExpanded.connect(self.expanded)
        # Last little bits of setting up
        self.service_theme = self.settings.value('servicemanager/service theme')
        self.service_path = AppLocation.get_section_data_path('servicemanager')
        # build the drag and drop context menu
        self.dnd_menu = QtWidgets.QMenu()
        self.new_action = self.dnd_menu.addAction(translate('OpenLP.ServiceManager', '&Add New Item'))
        self.new_action.setIcon(UiIcons().edit)
        self.add_to_action = self.dnd_menu.addAction(translate('OpenLP.ServiceManager', '&Add to Selected Item'))
        self.add_to_action.setIcon(UiIcons().edit)
        # build the context menu
        self.menu = QtWidgets.QMenu()
        self.edit_action = create_widget_action(self.menu, text=translate('OpenLP.ServiceManager', '&Edit Item'),
                                                icon=UiIcons().edit, triggers=self.remote_edit)
        self.rename_action = create_widget_action(self.menu, text=translate('OpenLP.ServiceManager', '&Rename...'),
                                                  icon=UiIcons().edit,
                                                  triggers=self.on_service_item_rename)
        self.maintain_action = create_widget_action(self.menu, text=translate('OpenLP.ServiceManager', '&Reorder Item'),
                                                    icon=UiIcons().edit,
                                                    triggers=self.on_service_item_edit_form)
        self.notes_action = create_widget_action(self.menu, text=translate('OpenLP.ServiceManager', '&Notes'),
                                                 icon=UiIcons().notes,
                                                 triggers=self.on_service_item_note_form)
        self.time_action = create_widget_action(self.menu, text=translate('OpenLP.ServiceManager', '&Start Time'),
                                                icon=UiIcons().time, triggers=self.on_start_time_form)
        self.auto_start_action = create_widget_action(self.menu, text='',
                                                      icon=UiIcons().active,
                                                      triggers=self.on_auto_start)
        # Add already existing delete action to the menu.
        self.menu.addAction(self.delete_action)
        self.create_custom_action = create_widget_action(self.menu,
                                                         text=translate('OpenLP.ServiceManager', 'Create New &Custom '
                                                                                                 'Slide'),
                                                         icon=UiIcons().custom,
                                                         triggers=self.create_custom)
        self.menu.addSeparator()
        # Add AutoPlay menu actions
        self.auto_play_slides_menu = QtWidgets.QMenu(translate('OpenLP.ServiceManager', '&Auto play slides'))
        self.menu.addMenu(self.auto_play_slides_menu)
        auto_play_slides_group = QtGui.QActionGroup(self.auto_play_slides_menu)
        auto_play_slides_group.setExclusive(True)
        self.auto_play_slides_loop = create_widget_action(self.auto_play_slides_menu,
                                                          text=translate('OpenLP.ServiceManager', 'Auto play slides '
                                                                                                  '&Loop'),
                                                          checked=False, triggers=self.toggle_auto_play_slides_loop)
        auto_play_slides_group.addAction(self.auto_play_slides_loop)
        self.auto_play_slides_once = create_widget_action(self.auto_play_slides_menu,
                                                          text=translate('OpenLP.ServiceManager', 'Auto play slides '
                                                                                                  '&Once'),
                                                          checked=False, triggers=self.toggle_auto_play_slides_once)
        auto_play_slides_group.addAction(self.auto_play_slides_once)
        self.auto_play_slides_menu.addSeparator()
        self.timed_slide_interval = create_widget_action(self.auto_play_slides_menu,
                                                         text=translate('OpenLP.ServiceManager', '&Delay between '
                                                                                                 'slides'),
                                                         triggers=self.on_timed_slide_interval)
        self.menu.addSeparator()
        self.preview_action = create_widget_action(self.menu, text=translate('OpenLP.ServiceManager', 'Show &Preview'),
                                                   icon=UiIcons().preview, triggers=self.make_preview)
        # Add already existing make live action to the menu.
        self.menu.addAction(self.make_live_action)
        self.menu.addSeparator()
        self.theme_menu = QtWidgets.QMenu(translate('OpenLP.ServiceManager', '&Change Item Theme'))
        self.menu.addMenu(self.theme_menu)
        self.service_manager_list.addActions([self.move_down_action, self.move_up_action, self.make_live_action,
                                              self.move_top_action, self.move_bottom_action, self.expand_action,
                                              self.collapse_action])


class ServiceManager(QtWidgets.QWidget, RegistryBase, Ui_ServiceManager, LogMixin, RegistryProperties):
    """
    Manages the services. This involves taking text strings from plugins and adding them to the service. This service
    can then be zipped up with all the resources used into one OSZ or OSZL file for use on any OpenLP installation.
    Also handles the UI tasks of moving things up and down etc.
    """
    servicemanager_set_item = QtCore.Signal(int)
    servicemanager_set_item_by_uuid = QtCore.Signal(str)
    servicemanager_next_item = QtCore.Signal()
    servicemanager_previous_item = QtCore.Signal()
    servicemanager_delete_item = QtCore.Signal()
    servicemanager_new_file = QtCore.Signal()
    servicemanager_changed = QtCore.Signal()
    theme_update_service = QtCore.Signal()

    def __init__(self, parent=None):
        """
        Sets up the service manager, toolbars, list view, et al.
        """
        super().__init__(parent)
        self._save_lite = False
        self.service_items = []
        self.suffixes = set()
        self.add_media_suffixes()
        self.drop_position = -1
        self.service_id = 0
        # is a new service and has not been saved
        self._modified = False
        self._service_path = None
        self.service_has_all_original_files = True
        self.list_double_clicked = False
        self.servicefile_version = None
        self.tree_widget_items = []
        # unique_identifier of the service item currently on the live output,
        # painted with an on-air marker by the Noir service delegate
        self.live_item_identifier = None
        # repaint_service_list debouncer
        self.repaint_service_list_timer = QtCore.QTimer(self)
        self.repaint_service_list_timer.setInterval(100)
        self.repaint_service_list_timer.timeout.connect(self._try_run_repaint_service_list)
        self.is_running_repaint = False
        self.repaint_select_indexes = (None, None)

    def bootstrap_initialise(self):
        """
        To be called as part of initialisation
        """
        self.setup_ui(self)
        self.set_theme_visibility()
        # Need to use event as called across threads and UI is updated
        self.servicemanager_set_item.connect(self.on_set_item)
        self.servicemanager_set_item_by_uuid.connect(self.set_item_by_uuid)
        self.servicemanager_next_item.connect(self.next_item)
        self.servicemanager_previous_item.connect(self.previous_item)
        self.servicemanager_delete_item.connect(self.delete_item)
        self.servicemanager_new_file.connect(self.new_file)
        # This signal is used to update the theme on the ui thread from the web api thread
        self.theme_update_service.connect(self.on_service_theme_change)
        Registry().register_function('theme_update_list', self.update_theme_list)
        Registry().register_function('theme_level_changed', self.on_theme_level_changed)
        Registry().register_function('config_screen_changed', self.regenerate_service_items)
        Registry().register_function('theme_change_global', self.regenerate_service_items)
        Registry().register_function('theme_change_service', self.regenerate_changed_service_items)
        Registry().register_function('mediaitem_suffix_reset', self.reset_supported_suffixes)
        Registry().register_function('slidecontroller_live_started', self.on_live_item_started)

    def bootstrap_post_set_up(self):
        """
        Can be set up as a late setup
        """
        self.service_note_form = ServiceNoteForm()
        self.service_item_edit_form = ServiceItemEditForm()
        self.start_time_form = StartTimeForm()

    def _delete_confirmation_dialog(self):
        msg_box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Question,
                                        translate('OpenLP.ServiceManager', 'Delete item from service'),
                                        translate('OpenLP.ServiceManager', 'Are you sure you want to delete '
                                                  'this item from the service?'),
                                        QtWidgets.QMessageBox.StandardButton(
                                            QtWidgets.QMessageBox.StandardButton.Close |
                                            QtWidgets.QMessageBox.StandardButton.Cancel), self)
        del_button = msg_box.button(QtWidgets.QMessageBox.StandardButton.Close)
        del_button.setText(translate('OpenLP.ServiceManager', '&Delete item'))
        msg_box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Close)
        return msg_box.exec()

    def add_media_suffixes(self):
        """
        Add the suffixes supported by :mod:`openlp.core.ui.media.*player`
        """
        audio, video = get_supported_media_suffix()
        self.suffixes.update(audio)
        self.suffixes.update(video)

    def set_modified(self, modified=True):
        """
        Setter for property "modified". Sets whether or not the current service has been modified.

        :param modified: Indicates if the service has new or removed items.  Used to trigger a remote update.
        """
        if modified:
            self.service_id += 1
        self._modified = modified
        if self._service_path:
            service_file = self._service_path.name
        else:
            service_file = translate('OpenLP.ServiceManager', 'Untitled Service')
        self.main_window.set_service_modified(modified, service_file)
        self.servicemanager_changed.emit()

    def is_modified(self):
        """
        Getter for boolean property "modified".
        """
        return self._modified

    def set_file_name(self, file_path):
        """
        Setter for service file.

        :param Path file_path: The service file name
        :rtype: None
        """
        self._service_path = file_path
        self.set_modified(self.is_modified())
        self.settings.setValue('servicemanager/last file', file_path)
        if file_path and file_path.suffix == '.oszl':
            self._save_lite = True
        else:
            self._save_lite = False

    def file_name(self):
        """
        Return the current file name including path.

        :rtype: Path
        """
        return self._service_path

    def short_file_name(self):
        """
        Return the current file name, excluding the path.
        """
        if self._service_path:
            return self._service_path.name

    def reset_supported_suffixes(self):
        """
        Resets the Suffixes list.
        """
        self.suffixes.clear()

    def supported_suffixes(self, suffix_list):
        """
        Adds Suffixes supported to the master list. Called from Plugins.

        :param list[str] | str suffix_list: New suffix(s) to be supported
        """
        if isinstance(suffix_list, str):
            self.suffixes.add(suffix_list)
        else:
            self.suffixes.update(suffix_list)

    def set_theme_visibility(self):
        """Set the visibility of the theme items"""
        visible = self.settings.value('themes/theme level') != ThemeLevel.Global
        self.toolbar.actions_map['theme_combo_box'].setVisible(visible)
        self.toolbar.actions_map['theme_label'].setVisible(visible)

    def on_new_service_clicked(self):
        """
        Create a new service.
        """
        if self.is_modified():
            result = self.save_modified_service()
            if result == QtWidgets.QMessageBox.StandardButton.Cancel:
                return False
            elif result == QtWidgets.QMessageBox.StandardButton.Save:
                if not self.decide_save_method():
                    return False
        if not self.service_items and self.settings.value('advanced/new service message'):
            do_not_show_again = QtWidgets.QCheckBox(translate('OpenLP.Ui', 'Do not show this message again'), None)
            message_box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information,
                                                translate('OpenLP.Ui', 'Create a new service.'),
                                                translate('OpenLP.Ui', 'You already have a blank new service.\n'
                                                                       'Add some items to it then press Save'),
                                                QtWidgets.QMessageBox.StandardButton.Ok,
                                                self)
            message_box.setCheckBox(do_not_show_again)
            message_box.exec()
            if message_box.checkBox().isChecked():
                self.settings.setValue('advanced/new service message', False)
        self.new_file()

    def on_load_service_clicked(self, checked):
        """
        Handle the `fileOpenItem` action

        :param bool checked: Not used.
        :rtype: None
        """
        self.load_service()

    def load_service(self, file_path=None):
        """
        Loads the service file and saves the existing one it there is one unchanged.

        :param Path | None file_path: The service file to the loaded.
        """
        if self.is_modified():
            result = self.save_modified_service()
            if result == QtWidgets.QMessageBox.StandardButton.Cancel:
                return False
            elif result == QtWidgets.QMessageBox.StandardButton.Save:
                self.decide_save_method()
        if not file_path:
            file_path, filter_used = FileDialog.getOpenFileName(
                self.main_window,
                translate('OpenLP.ServiceManager', 'Open File'),
                self.settings.value('servicemanager/last directory'),
                translate('OpenLP.ServiceManager', 'OpenLP Service Files (*.osz *.oszl)'))
            if not file_path:
                return False
        self.settings.setValue('servicemanager/last directory', file_path.parent)
        self.load_file(file_path)

    def save_modified_service(self):
        """
        Check to see if a service needs to be saved.
        """
        return QtWidgets.QMessageBox.question(self.main_window,
                                              translate('OpenLP.ServiceManager', 'Modified Service'),
                                              translate('OpenLP.ServiceManager',
                                                        'The current service has been modified. Would you like to save '
                                                        'this service?'),
                                              QtWidgets.QMessageBox.StandardButton.Save |
                                              QtWidgets.QMessageBox.StandardButton.Discard |
                                              QtWidgets.QMessageBox.StandardButton.Cancel,
                                              QtWidgets.QMessageBox.StandardButton.Save)

    def on_recent_service_clicked(self, checked):
        """
        Load a recent file as the service triggered by mainwindow recent service list.

        :param bool checked: Not used
        """
        if self.is_modified():
            result = self.save_modified_service()
            if result == QtWidgets.QMessageBox.StandardButton.Cancel:
                return False
            elif result == QtWidgets.QMessageBox.StandardButton.Save:
                self.decide_save_method()
        sender = self.sender()
        self.load_file(Path(sender.data()))

    def new_file(self):
        """
        Create a blank new service file.
        """
        self.service_manager_list.clear()
        self.service_items = []
        self.set_file_name(None)
        self.service_id += 1
        self.set_modified(False)
        self.settings.setValue('servicemanager/last file', None)
        self.plugin_manager.new_service_created()
        self.live_controller.slide_count = 0
        self.servicemanager_changed.emit()

    def create_basic_service(self):
        """
        Create the initial service array with the base items to be saved.

        :return: service array
        """
        service = []
        # Regarding openlp-servicefile-version:
        #  1: OpenLP 1? Not used.
        #  2: OpenLP 2 (default when loading a service file without openlp-servicefile-version)
        #  3: The new format introduced in OpenLP 3.0.
        # Note that the servicefile-version numbering is not expected to follow the OpenLP version numbering.
        core = {
            'lite-service': self._save_lite,
            'service-theme': self.service_theme,
            'openlp-servicefile-version': 3
        }
        service.append({'openlp_core': core})
        return service

    def get_write_file_list(self):
        """
        Get a list of files used in the service and files that are missing.

        :return: A list of tuples with files used in the service that exist and their sha256-based name in the
                 servicefile, and a list of files that doesn't exists.
        :rtype: (list[(Path,str)], list[str])
        """
        write_list = []
        missing_list = []
        # Run through all items
        for item in self.service_items:
            # If the item has files, see if they exists
            if item['service_item'].uses_file():
                for frame in item['service_item'].get_frames():
                    frame_path = item['service_item'].get_frame_path(frame=frame)
                    if not frame_path.exists():
                        if 'thumbnail' not in frame_path.parts:
                            missing_list.append(str(frame_path))
                        continue
                    if item['service_item'].stored_filename:
                        sha256_file_name = Path(item['service_item'].stored_filename)
                    else:
                        sha256_file_name = Path(sha256_file_hash(frame_path) + frame_path.suffix)
                    bundle = (frame_path, sha256_file_name)
                    if bundle in write_list or str(frame_path) in missing_list:
                        continue
                    write_list.append(bundle)
                # For items that has thumbnails, add them to the list
                if item['service_item'].is_capable(ItemCapabilities.HasThumbnails):
                    thumbnail_path = item['service_item'].get_thumbnail_path()
                    if not thumbnail_path or not Path(thumbnail_path).exists():
                        continue
                    thumbnail_path_parent = Path(thumbnail_path).parent
                    if item['service_item'].is_command():
                        # Run through everything in the thumbnail folder and add pictures
                        for filename in os.listdir(thumbnail_path):
                            # Skip non-pictures
                            if os.path.splitext(filename)[1] not in ['.png', '.jpg', '.jpeg']:
                                continue
                            filename_path = Path(thumbnail_path) / Path(filename)
                            if not filename_path.exists():
                                continue
                            # Create a thumbnail path in the zip/service file
                            service_path = filename_path.relative_to(thumbnail_path_parent)
                            write_list.append((filename_path, service_path))
                    elif item['service_item'].is_image():
                        # Find all image thumbnails and store them
                        # All image thumbnails will be put in a folder named 'thumbnails'
                        for frame in item['service_item'].get_frames():
                            if 'thumbnail' in frame:
                                filename_path = Path(thumbnail_path) / frame['thumbnail']
                                if not filename_path.exists():
                                    continue
                                # Create a thumbnail path in the zip/service file
                                service_path = filename_path.relative_to(thumbnail_path_parent)
                                path_from_tuple = (filename_path, service_path)
                                if path_from_tuple in write_list:
                                    continue
                                write_list.append(path_from_tuple)
            for (audio_path, audio_file_hash) in item['service_item'].background_audio:
                if not audio_file_hash:
                    audio_file_hash = sha256_file_hash(audio_path)
                service_path = audio_file_hash + audio_path.suffix
                audio_path_tuple = (audio_path, service_path)
                if audio_path_tuple in write_list:
                    continue
                write_list.append(audio_path_tuple)
        return write_list, missing_list

    def save_file(self):
        """
        Save the current service file.

        A temporary file is created so that we don't overwrite the existing one and leave a mangled service file should
        there be an error when saving. Audio files are also copied into the service manager directory, and then packaged
        into the zip file.
        """
        file_path = self.file_name()
        self.log_debug('ServiceManager.save_file - {name}'.format(name=file_path))
        self.application.set_busy_cursor()

        service = self.create_basic_service()

        write_list = []
        missing_list = []

        if not self._save_lite:
            try:
                write_list, missing_list = self.get_write_file_list()
            except PermissionError as pe:
                self.main_window.error_message(UiStrings.PermissionError,
                                               UiStrings.UnableToRead + '\n\n' + pe.filename)
                return False
            if missing_list:
                self.application.set_normal_cursor()
                title = translate('OpenLP.ServiceManager', 'Service File(s) Missing')
                message = translate('OpenLP.ServiceManager',
                                    'The following file(s) in the service are missing: {name}\n\n'
                                    'These files will be removed if you continue to save.'
                                    ).format(name='\n\t'.join(missing_list))
                answer = QtWidgets.QMessageBox.critical(self, title, message,
                                                        QtWidgets.QMessageBox.StandardButton(
                                                            QtWidgets.QMessageBox.StandardButton.Ok |
                                                            QtWidgets.QMessageBox.StandardButton.Cancel))
                if answer == QtWidgets.QMessageBox.StandardButton.Cancel:
                    return False
        # Check if item contains a missing file.
        for item in list(self.service_items):
            if not self._save_lite:
                item['service_item'].remove_invalid_frames(missing_list)
                if item['service_item'].missing_frames():
                    self.service_items.remove(item)
                    continue
            service_item = item['service_item'].get_service_repr(self._save_lite)
            # Add the service item to the service.
            service.append({'serviceitem': service_item})
        self.repaint_service_list(-1, -1)
        service_content = json.dumps(service, cls=OpenLPJSONEncoder)
        service_content_size = len(bytes(service_content, encoding='utf-8'))
        total_size = service_content_size
        for local_file_item, zip_file_item in write_list:
            try:
                total_size += local_file_item.stat().st_size
            except FileNotFoundError:
                self.log_exception(f'Local file {local_file_item} not found')
        self.log_debug('ServiceManager.save_file - ZIP contents size is %i bytes' % total_size)
        self.main_window.display_progress_bar(1000)
        try:
            tmp_file_path = str(file_path) + ".saving"
            with zipfile.ZipFile(tmp_file_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # First we add service contents..
                zip_file.writestr('service_data.osj', service_content)
                self.main_window.increment_progress_bar(service_content_size / total_size * 1000)
                # Finally add all the listed media files.
                for local_file_item, zip_file_item in write_list:
                    zip_file.write(str(local_file_item), str(zip_file_item))
                    self.main_window.increment_progress_bar(local_file_item.stat().st_size / total_size * 1000)
                with suppress(FileNotFoundError):
                    file_path.unlink()
            # Move rather than copy to prevent writing another file if possible
            shutil.move(tmp_file_path, file_path)
            self.settings.setValue('servicemanager/last directory', file_path.parent)
        except (PermissionError, OSError) as error:
            self.log_exception('Failed to save service to disk: {name}'.format(name=file_path))
            self.main_window.error_message(
                translate('OpenLP.ServiceManager', 'Error Saving File'),
                translate('OpenLP.ServiceManager',
                          'There was an error saving your file.\n\n{error}').format(error=error))
            return self.save_file_as()
        self.main_window.finished_progress_bar()
        self.application.set_normal_cursor()
        self.main_window.add_recent_file(file_path)
        self.set_modified(False)
        return True

    def save_file_as(self):
        """
        Get a file name and then call :func:`ServiceManager.save_file` to save the file.
        """
        default_service_enabled = self.settings.value('advanced/default service enabled')
        if default_service_enabled:
            service_day = self.settings.value('advanced/default service day')
            if service_day == 7:
                local_time = datetime.now()
            else:
                service_hour = self.settings.value('advanced/default service hour')
                service_minute = self.settings.value('advanced/default service minute')
                now = datetime.now()
                day_delta = service_day - now.weekday()
                if day_delta < 0:
                    day_delta += 7
                time = now + timedelta(days=day_delta)
                local_time = time.replace(hour=service_hour, minute=service_minute)
            default_pattern = self.settings.value('advanced/default service name')
            default_file_name = format_time(default_pattern, local_time)
        else:
            default_file_name = ''
        default_file_path = Path(default_file_name)
        directory_path = self.settings.value('servicemanager/last directory')
        if directory_path:
            default_file_path = directory_path / default_file_path
        lite_filter = translate('OpenLP.ServiceManager', 'OpenLP Service Files - lite (*.oszl)')
        packaged_filter = translate('OpenLP.ServiceManager', 'OpenLP Service Files (*.osz)')
        if self._service_path and self._service_path.suffix == '.oszl':
            default_filter = lite_filter
        else:
            default_filter = packaged_filter
        # SaveAs from osz to oszl is not valid as the files will be deleted on exit which is not sensible or usable in
        # the long term.
        if self._service_path and self._service_path.suffix == '.oszl' or self.service_has_all_original_files:
            file_path, filter_used = FileDialog.getSaveFileName(
                self.main_window, UiStrings().SaveService, default_file_path,
                '{packaged};; {lite}'.format(packaged=packaged_filter, lite=lite_filter),
                default_filter)
        else:
            file_path, filter_used = FileDialog.getSaveFileName(
                self.main_window, UiStrings().SaveService, default_file_path,
                '{packaged};;'.format(packaged=packaged_filter))
        if not file_path:
            return False
        if filter_used == lite_filter:
            file_path = file_path.with_suffix('.oszl')
        else:
            file_path = file_path.with_suffix('.osz')
        self.set_file_name(file_path)
        self.decide_save_method()

    def decide_save_method(self):
        """
        Determine which type of save method to use.
        """
        if not self.file_name():
            return self.save_file_as()
        return self.save_file()

    def load_file(self, file_path):
        """
        Load an existing service file.

        :param Path file_path: The service file to load.
        """
        # If the file_path is a string, this method will fail. Typecase to Path
        file_path = Path(file_path)
        try:
            if not file_path.exists():
                return False
        except OSError:
            # if the filename, directory name, or volume label syntax is incorrect it can cause an exception
            return False
        service_data = None
        is_broken_file = False
        self.application.set_busy_cursor()
        try:
            # TODO: figure out a way to use the presentation thumbnails from the service file
            with zipfile.ZipFile(str(file_path)) as zip_file:
                compressed_size = 0
                for zip_info in zip_file.infolist():
                    compressed_size += zip_info.compress_size
                self.main_window.display_progress_bar(compressed_size // 1024)
                # First find the osj-file to find out how to handle the file
                for zip_info in zip_file.infolist():
                    # The json file has been called 'service_data.osj' since OpenLP 3.0
                    if zip_info.filename == 'service_data.osj' or zip_info.filename.endswith('osj'):
                        with zip_file.open(zip_info, 'r') as json_file:
                            service_data = json_file.read()
                        break
                if service_data:
                    items = json.loads(service_data, cls=OpenLPJSONDecoder)
                else:
                    raise ValidationError(msg='No service data found')
                # Extract the service file version
                for item in items:
                    if 'openlp_core' in item:
                        item = item['openlp_core']
                        self.servicefile_version = item.get('openlp-servicefile-version', 2)
                        break
                self.log_debug('Service format version: %{ver}'.format(ver=self.servicefile_version))
                for zip_info in zip_file.infolist():
                    self.log_debug('Extract file: {name}'.format(name=zip_info.filename))
                    # The json file has been called 'service_data.osj' since OpenLP 3.0
                    if zip_info.filename == 'service_data.osj' or zip_info.filename.endswith('osj'):
                        with zip_file.open(zip_info, 'r') as json_file:
                            service_data = json_file.read()
                    else:
                        # Service files from earlier versions than 3 expects that all files are extracted
                        # into the root of the service folder.
                        if self.servicefile_version and self.servicefile_version < 3:
                            zip_info.filename = os.path.basename(zip_info.filename.replace('/', os.path.sep))
                        else:
                            # Fix an issue with service files created in 2.9.x
                            fname, ext = os.path.splitext(zip_info.filename)
                            if not ext and os.path.basename(fname).startswith('.'):
                                zip_info.filename = fname.replace('/', '')
                                is_broken_file = True
                                self.log_debug(f'Fixing file {fname} => {zip_info.filename}')
                        zip_file.extract(zip_info, str(self.service_path))
                    self.main_window.increment_progress_bar(zip_info.compress_size // 1024)
                # Handle the content
                self.new_file()
                self.process_service_items(items)
                self.set_file_name(file_path)
                self.main_window.add_recent_file(file_path)
                self.set_modified(False)
                # If this file was broken due to a bug in 2.9.x, save the file to fix it.
                if is_broken_file:
                    self.save_file()
                self.settings.setValue('servicemanager/last file', file_path)
        except (NameError, OSError, ValidationError, zipfile.BadZipFile):
            self.application.set_normal_cursor()
            self.log_exception('Problem loading service file {name}'.format(name=file_path))
            critical_error_message_box(
                message=translate('OpenLP.ServiceManager',
                                  'The service file {file_path} could not be loaded because it is either corrupt, '
                                  'inaccessible, or not a valid OpenLP 2 or OpenLP 3 service file.'
                                  ).format(file_path=file_path))
        self.main_window.finished_progress_bar()
        self.application.set_normal_cursor()
        self.repaint_service_list(-1, -1)

    def process_service_items(self, service_items):
        """
        Process all the array of service items loaded from the saved service

        :param service_items: list of service_items
        """
        for item in service_items:
            self.main_window.increment_progress_bar()
            service_item = ServiceItem()
            if 'openlp_core' in item:
                item = item['openlp_core']
                self._save_lite = item.get('lite-service', False)
                if theme := item.get('service-theme', None):
                    find_and_set_in_combo_box(self.theme_combo_box, theme, set_missing=False)
                    if theme == self.theme_combo_box.currentText():
                        self.service_theme = theme
                        self.settings.setValue('servicemanager/service theme', theme)
                        Registry().execute('theme_change_service')
            else:
                if self._save_lite:
                    service_item.set_from_service(item, version=self.servicefile_version)
                else:
                    service_item.set_from_service(item, self.service_path, self.servicefile_version)
                service_item.validate_item()
                if service_item.is_capable(ItemCapabilities.OnLoadUpdate):
                    new_item = Registry().get(service_item.name).service_load(service_item)
                    if new_item:
                        service_item = new_item
                self.add_service_item(service_item, repaint=False)

    def load_last_file(self):
        """
        Load the last service item from the service manager when the service was last closed. Can be blank if there was
        no service present.
        """
        file_path = self.settings.value('servicemanager/last file')
        if file_path:
            self.load_file(file_path)

    def context_menu(self, point):
        """
        The Right click context menu from the Service item list

        :param point: The location of the cursor.
        """
        item = self.service_manager_list.itemAt(point)
        if item is None:
            return
        if item.parent():
            pos = item.parent().data(0, QtCore.Qt.ItemDataRole.UserRole)
        else:
            pos = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        service_item = self.service_items[pos - 1]
        self.edit_action.setVisible(False)
        self.rename_action.setVisible(False)
        self.create_custom_action.setVisible(False)
        self.maintain_action.setVisible(False)
        self.notes_action.setVisible(False)
        self.time_action.setVisible(False)
        self.auto_start_action.setVisible(False)
        if service_item['service_item'].is_capable(ItemCapabilities.CanEdit) and service_item['service_item'].edit_id:
            self.edit_action.setVisible(True)
        if service_item['service_item'].is_capable(ItemCapabilities.CanEditTitle):
            self.rename_action.setVisible(True)
        if service_item['service_item'].is_capable(ItemCapabilities.CanMaintain):
            self.maintain_action.setVisible(True)
        if item.parent() is None:
            self.notes_action.setVisible(True)
        if service_item['service_item'].is_capable(ItemCapabilities.CanLoop) and  \
                len(service_item['service_item'].get_frames()) > 1:
            self.auto_play_slides_menu.menuAction().setVisible(True)
            self.auto_play_slides_once.setChecked(service_item['service_item'].auto_play_slides_once)
            self.auto_play_slides_loop.setChecked(service_item['service_item'].auto_play_slides_loop)
            self.timed_slide_interval.setChecked(service_item['service_item'].timed_slide_interval > 0)
            if service_item['service_item'].timed_slide_interval > 0:
                delay_suffix = ' {text} s'.format(text=str(service_item['service_item'].timed_slide_interval))
            else:
                delay_suffix = ' ...'
            self.timed_slide_interval.setText(
                translate('OpenLP.ServiceManager', '&Delay between slides') + delay_suffix)
            # TODO for future: make group explains itself more visually
        else:
            self.auto_play_slides_menu.menuAction().setVisible(False)
        if service_item['service_item'].is_capable(ItemCapabilities.HasVariableStartTime) and \
                not service_item['service_item'].is_capable(ItemCapabilities.IsOptical):
            self.time_action.setVisible(True)
        if service_item['service_item'].is_capable(ItemCapabilities.CanAutoStartForLive):
            self.auto_start_action.setVisible(True)
            if service_item['service_item'].will_auto_start:
                self.auto_start_action.setText(translate('OpenLP.ServiceManager', '&Auto Start - active'))
                self.auto_start_action.setIcon(UiIcons().active)
            else:
                self.auto_start_action.setIcon(UiIcons().inactive)
                self.auto_start_action.setText(translate('OpenLP.ServiceManager', '&Auto Start - inactive'))
        if service_item['service_item'].is_text():
            for plugin in State().list_plugins():
                if plugin.name == 'custom' and plugin.status == PluginStatus.Active:
                    self.create_custom_action.setVisible(True)
                    break
        self.theme_menu.menuAction().setVisible(False)
        # Set up the theme menu.
        if service_item['service_item'].is_text() and self.renderer.theme_level == ThemeLevel.Song:
            self.theme_menu.menuAction().setVisible(True)
            # The service item does not have a theme, check the "Default".
            if service_item['service_item'].theme is None:
                theme_action = self.theme_menu.defaultAction()
            else:
                theme_action = self.theme_menu.findChild(QtGui.QAction, service_item['service_item'].theme)
            if theme_action is not None:
                theme_action.setChecked(True)
        self.menu.exec(self.service_manager_list.mapToGlobal(point))

    def on_service_item_note_form(self):
        """
        Allow the service note to be edited
        """
        item = self.find_service_item()[0]
        self.service_note_form.text_edit.setPlainText(self.service_items[item]['service_item'].notes)
        if self.service_note_form.exec():
            self.service_items[item]['service_item'].notes = self.service_note_form.text_edit.toPlainText()
            self.repaint_service_list(item, -1)
            self.set_modified()

    def on_start_time_form(self):
        """
        Opens a dialog to type in service item notes.
        """
        item = self.find_service_item()[0]
        self.start_time_form.item = self.service_items[item]
        if self.start_time_form.exec():
            self.repaint_service_list(item, -1)

    def toggle_auto_play_slides_once(self):
        """
        Toggle Auto play slide once. Inverts auto play once option for the item
        """
        item = self.find_service_item()[0]
        service_item = self.service_items[item]['service_item']
        service_item.auto_play_slides_once = not service_item.auto_play_slides_once
        if service_item.auto_play_slides_once:
            service_item.auto_play_slides_loop = False
            self.auto_play_slides_loop.setChecked(False)
        if service_item.auto_play_slides_once and service_item.timed_slide_interval == 0:
            service_item.timed_slide_interval = self.settings.value('core/loop delay')
        self.set_modified()

    def toggle_auto_play_slides_loop(self):
        """
        Toggle Auto play slide loop.
        """
        item = self.find_service_item()[0]
        service_item = self.service_items[item]['service_item']
        service_item.auto_play_slides_loop = not service_item.auto_play_slides_loop
        if service_item.auto_play_slides_loop:
            service_item.auto_play_slides_once = False
            self.auto_play_slides_once.setChecked(False)
        if service_item.auto_play_slides_loop and service_item.timed_slide_interval == 0:
            service_item.timed_slide_interval = self.settings.value('core/loop delay')
        self.set_modified()

    def on_timed_slide_interval(self):
        """
        Shows input dialog for enter interval in seconds for delay
        """
        item = self.find_service_item()[0]
        service_item = self.service_items[item]['service_item']
        if service_item.timed_slide_interval == 0:
            timed_slide_interval = self.settings.value('core/loop delay')
        else:
            timed_slide_interval = service_item.timed_slide_interval
        timed_slide_interval, ok = QtWidgets.QInputDialog.getInt(self, translate('OpenLP.ServiceManager',
                                                                 'Input delay'),
                                                                 translate('OpenLP.ServiceManager',
                                                                           'Delay between slides in seconds.'),
                                                                 timed_slide_interval, 0, 180, 1)
        if ok:
            service_item.timed_slide_interval = timed_slide_interval
        if service_item.timed_slide_interval != 0 and not service_item.auto_play_slides_loop \
                and not service_item.auto_play_slides_once:
            service_item.auto_play_slides_loop = True
        elif service_item.timed_slide_interval == 0:
            service_item.auto_play_slides_loop = False
            service_item.auto_play_slides_once = False
        self.set_modified()

    def on_auto_start(self):
        """
        Toggles to Auto Start Setting.
        """
        item = self.find_service_item()[0]
        self.service_items[item]['service_item'].will_auto_start = \
            not self.service_items[item]['service_item'].will_auto_start

    def on_service_item_edit_form(self):
        """
        Opens a dialog to edit the service item and update the service display if changes are saved.
        """
        item = self.find_service_item()[0]
        self.service_item_edit_form.set_service_item(self.service_items[item]['service_item'])
        if self.service_item_edit_form.exec():
            self.add_service_item(self.service_item_edit_form.get_service_item(),
                                  replace=item, expand=self.service_items[item]['expanded'])

    def preview_live(self, unique_identifier, row):
        """
        Called by the SlideController to request a preview item be made live and allows the next preview to be updated
        if relevant.

        :param unique_identifier: Reference to the service_item
        :param row: individual row number
        """
        for sitem in self.service_items:
            if sitem['service_item'].unique_identifier == unique_identifier:
                item = self.service_manager_list.topLevelItem(sitem['order'] - 1)
                self.service_manager_list.setCurrentItem(item)
                self.make_live(int(row))
                return

    def next_item(self):
        """
        Called by the SlideController to select the next service item.
        """
        if not self.service_manager_list.selectedItems():
            return
        selected = self.service_manager_list.selectedItems()[0]
        look_for = 0
        service_iterator = QtWidgets.QTreeWidgetItemIterator(self.service_manager_list)
        while service_iterator.value():
            if look_for == 1 and service_iterator.value().parent() is None:
                self.service_manager_list.setCurrentItem(service_iterator.value())
                self.make_live()
                return
            if service_iterator.value() == selected:
                look_for = 1
            service_iterator += 1

    def previous_item(self, last_slide=False):
        """
        Called by the SlideController to select the previous service item.

        :param last_slide: Is this the last slide in the service_item.
        """
        if not self.service_manager_list.selectedItems():
            return
        selected = self.service_manager_list.selectedItems()[0]
        prev_item = None
        prev_item_last_slide = None
        service_iterator = QtWidgets.QTreeWidgetItemIterator(self.service_manager_list)
        while service_iterator.value():
            # Found the selected/current service item
            if service_iterator.value() == selected:
                if last_slide and prev_item_last_slide:
                    # Go to the last slide of the previous service item
                    pos = prev_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                    check_expanded = self.service_items[pos - 1]['expanded']
                    self.service_manager_list.setCurrentItem(prev_item_last_slide)
                    if not check_expanded:
                        self.service_manager_list.collapseItem(prev_item)
                    self.make_live()
                    self.service_manager_list.setCurrentItem(prev_item)
                elif prev_item:
                    # Go to the first slide of the previous service item
                    self.service_manager_list.setCurrentItem(prev_item)
                    self.make_live()
                return
            # Found the previous service item root
            if service_iterator.value().parent() is None:
                prev_item = service_iterator.value()
            # Found the last slide of the previous item
            if service_iterator.value().parent() is prev_item:
                prev_item_last_slide = service_iterator.value()
            # Go to next item in the tree
            service_iterator += 1

    def on_set_item(self, message):
        """
        Called by a signal to select a specific item and make it live usually from remote.
        :param message: The data passed in from a remove message
        """
        self.log_debug(message)
        self.set_item(int(message))

    def set_item(self, index):
        """
        Makes a specific item in the service live.

        :param index: The index of the service item list to be actioned.
        """
        if 0 <= index < self.service_manager_list.topLevelItemCount():
            item = self.service_manager_list.topLevelItem(index)
            self.service_manager_list.setCurrentItem(item)
            self.make_live()

    def set_item_by_uuid(self, unique_identifier):
        """
        Makes a specific item in the service live.  Called directly by the API layer

        :param unique_identifier: Unique Identifier for the item.
        """
        for sitem in self.service_items:
            if sitem['service_item'].unique_identifier == unique_identifier:
                item = self.service_manager_list.topLevelItem(sitem['order'] - 1)
                self.service_manager_list.setCurrentItem(item)
                self.make_live()
                return

    def on_move_selection_up(self):
        """
        Moves the cursor selection up the window. Called by the up arrow.
        """
        item = self.service_manager_list.currentItem()
        item_before = self.service_manager_list.itemAbove(item)
        if item_before is None:
            return
        self.service_manager_list.setCurrentItem(item_before)

    def on_move_selection_down(self):
        """
        Moves the cursor selection down the window. Called by the down arrow.
        """
        item = self.service_manager_list.currentItem()
        item_after = self.service_manager_list.itemBelow(item)
        if item_after is None:
            return
        self.service_manager_list.setCurrentItem(item_after)

    def on_expand_selection(self):
        """
        Expands cursor selection on the window. Called by the right arrow
        """
        item = self.service_manager_list.currentItem()
        # Since we only have 2 levels we find them by checking for children
        if item and item.childCount():
            if not self.service_manager_list.isExpanded(self.service_manager_list.currentIndex()):
                self.service_manager_list.expandItem(item)
                self.service_manager.expanded(item)
                # If not expanded, Expand it
            self.service_manager_list.setCurrentItem(self.service_manager_list.itemBelow(item))
            # Then move selection down to child whether it needed to be expanded or not

    def on_collapse_selection(self):
        """
        Collapses cursor selection on the window Called by the left arrow
        """
        item = self.service_manager_list.currentItem()
        if item is not None:
            # Since we only have 2 levels we find them by checking for children
            if item.childCount():
                if self.service_manager_list.isExpanded(self.service_manager_list.currentIndex()):
                    self.service_manager_list.collapseItem(item)
                    self.service_manager.collapsed(item)
            else:  # If selection is lower level
                self.service_manager_list.collapseItem(item.parent())
                self.service_manager.collapsed(item.parent())
                self.service_manager_list.setCurrentItem(item.parent())

    def on_collapse_all(self):
        """
        Collapse all the service items.
        """
        for item in self.service_items:
            item['expanded'] = False
        self.service_manager_list.collapseAll()

    def collapsed(self, item):
        """
        Record if an item is collapsed. Used when repainting the list to get the correct state.

        :param item: The service item to be checked
        """
        pos = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        # Only set root items as collapsed, and since we only have 2 levels we find them by checking for children
        if item.childCount():
            self.service_items[pos - 1]['expanded'] = False

    def on_expand_all(self):
        """
        Collapse all the service items.
        """
        for item in self.service_items:
            item['expanded'] = True
        self.service_manager_list.expandAll()

    def expanded(self, item):
        """
        Record if an item is collapsed. Used when repainting the list to get the correct state.

        :param item: The service item to be checked
        """
        pos = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        # Only set root items as expanded, and since we only have 2 levels we find them by checking for children
        if item.childCount():
            self.service_items[pos - 1]['expanded'] = True

    def on_service_top(self):
        """
        Move the current ServiceItem to the top of the list.
        """
        item, child = self.find_service_item()
        if item < len(self.service_items) and item != -1:
            temp = self.service_items[item]
            self.service_items.remove(self.service_items[item])
            self.service_items.insert(0, temp)
            self.repaint_service_list(0, child)
            self.set_modified()

    def on_service_up(self):
        """
        Move the current ServiceItem one position up in the list.
        """
        item, child = self.find_service_item()
        if item > 0:
            temp = self.service_items[item]
            self.service_items.remove(self.service_items[item])
            self.service_items.insert(item - 1, temp)
            self.repaint_service_list(item - 1, child)
            self.set_modified()

    def on_service_down(self):
        """
        Move the current ServiceItem one position down in the list.
        """
        item, child = self.find_service_item()
        if item < len(self.service_items) and item != -1:
            temp = self.service_items[item]
            self.service_items.remove(self.service_items[item])
            self.service_items.insert(item + 1, temp)
            self.repaint_service_list(item + 1, child)
            self.set_modified()

    def on_service_end(self):
        """
        Move the current ServiceItem to the bottom of the list.
        """
        item, child = self.find_service_item()
        if item < len(self.service_items) and item != -1:
            temp = self.service_items[item]
            self.service_items.remove(self.service_items[item])
            self.service_items.insert(len(self.service_items), temp)
            self.repaint_service_list(len(self.service_items) - 1, child)
            self.set_modified()

    def on_delete_from_service(self):
        """
        Remove the current ServiceItem from the list.
        """
        need_confirmation: bool = self.settings.value('advanced/delete service item confirmation')
        if (
            not need_confirmation or
            self._delete_confirmation_dialog() == QtWidgets.QMessageBox.Close
        ):
            self.delete_item()

    def on_live_item_started(self, item):
        """
        The live controller started showing an item: remember it and move the
        on-air marker in the service list. Items sent live straight from the
        library match no service row, which correctly clears the marker.

        :param item: A list holding the service item that went live
        """
        service_item = item[0] if isinstance(item, list) and item else item
        self.live_item_identifier = getattr(service_item, 'unique_identifier', None)
        self._update_live_markers()

    def _update_live_markers(self):
        """Move the on-air marker to the service row matching the live item"""
        for index, item in enumerate(self.service_items):
            tree_item = self.service_manager_list.topLevelItem(index)
            if tree_item is not None:
                is_live_item = item['service_item'].unique_identifier == self.live_item_identifier
                tree_item.setData(0, SERVICE_LIVE_ROLE, is_live_item)
        self.service_manager_list.viewport().update()

    def _service_item_caption(self, service_item):
        """
        The metadata caption painted under the item title by the Noir service
        delegate: plugin, slide count, and a notes flag.

        :param service_item: The service item to describe
        """
        parts = []
        if service_item.name:
            parts.append(service_item.name.title())
        slide_count = len(service_item.get_frames())
        if slide_count == 1:
            parts.append(translate('OpenLP.ServiceManager', '1 slide'))
        else:
            parts.append(translate('OpenLP.ServiceManager', '{count} slides').format(count=slide_count))
        if service_item.theme and service_item.theme != -1:
            parts.append(str(service_item.theme))
        if service_item.notes:
            parts.append(translate('OpenLP.ServiceManager', 'Notes'))
        return ' · '.join(parts)

    def repaint_service_list(self, service_item: int, service_item_child: int):
        """
        Clear the existing service list and prepaint all the items. This is used when moving items as the move takes
        place in a supporting list, and when regenerating all the items due to theme changes.

        :param service_item: The item which changed. (int)
        :param service_item_child: The child of the ``service_item``, which will be selected. (int)
        """
        self.repaint_select_indexes = (service_item, service_item_child)
        self._try_run_repaint_service_list()

    def _try_run_repaint_service_list(self):
        if not self.is_running_repaint:
            self.repaint_service_list_timer.stop()
            self._repaint_service_list()
            if (self.repaint_select_indexes[0] is not None):
                self._select_item_after_repaint(self.repaint_select_indexes[0], self.repaint_select_indexes[1])
                self.repaint_select_indexes = (None, None)
        else:
            # Trying again later
            self.repaint_service_list_timer.stop()
            self.repaint_service_list_timer.start()

    def _select_item_after_repaint(self, service_item: int, service_item_child: int):
        """
        Selects the list active item after repaint.

        :param service_item: The item which changed. (int)
        :param service_item_child: The child of the ``service_item``, which will be selected. (int)
        """
        for item_index, item in enumerate(self.service_items):
            service_item_from_item = item['service_item']
            for slide_index, slide in enumerate(service_item_from_item.get_frames()):
                if service_item == item_index:
                    try:
                        if item['expanded'] and service_item_child == slide_index:
                            self.service_manager_list.setCurrentIndex(
                                self.service_manager_list.model().index(service_item, 0).child(service_item_child, 0)
                            )
                        elif service_item_child == -1:
                            self.service_manager_list.setCurrentIndex(
                                self.service_manager_list.model().index(service_item, 0)
                            )
                    except RuntimeError:
                        pass

    def _repaint_service_list(self) -> bool:
        """
        Clear the existing service list and prepaint all the items. This is used when moving items as the move takes
        place in a supporting list, and when regenerating all the items due to theme changes.

        :returns: Whether the call should be scheduled to be run again due to fail.
        """
        # Correct order of items in array
        self.is_running_repaint = True
        count = 1
        self.service_has_all_original_files = True
        for item in self.service_items:
            item['order'] = count
            count += 1
            if not item['service_item'].has_original_file_path:
                self.service_has_all_original_files = False
        # Repaint the screen
        self.tree_widget_items = []
        self.service_manager_list.clearSelection()
        self.service_manager_list.clear()
        for _, item in enumerate(self.service_items):
            service_item_from_item = item['service_item']
            tree_widget_item = QtWidgets.QTreeWidgetItem(self.service_manager_list)
            self.tree_widget_items.append(tree_widget_item)
            if service_item_from_item.is_valid:
                icon = service_item_from_item.icon.pixmap(80, 80).toImage()
                icon = icon.scaled(80, 80, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                   QtCore.Qt.TransformationMode.SmoothTransformation)
                if service_item_from_item.notes:
                    overlay = UiIcons().notes.pixmap(40, 40).toImage()
                    overlay = overlay.scaled(40, 40, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                             QtCore.Qt.TransformationMode.SmoothTransformation)
                    painter = QtGui.QPainter(icon)
                    painter.drawImage(0, 0, overlay)
                    painter.end()
                    tree_widget_item.setIcon(0, build_icon(icon))
                elif service_item_from_item.temporary_edit:
                    overlay = QtGui.QImage(UiIcons().upload)
                    overlay = overlay.scaled(40, 40, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                             QtCore.Qt.TransformationMode.SmoothTransformation)
                    painter = QtGui.QPainter(icon)
                    painter.drawImage(40, 0, overlay)
                    painter.end()
                    tree_widget_item.setIcon(0, build_icon(icon))
                else:
                    tree_widget_item.setIcon(0, service_item_from_item.icon)
            else:
                tree_widget_item.setIcon(0, UiIcons().delete)
            tree_widget_item.setText(0, service_item_from_item.get_display_title())
            tips = []
            if service_item_from_item.temporary_edit:
                text1 = translate('OpenLP.ServiceManager', 'Edit')
                text2 = translate('OpenLP.ServiceManager', 'Service copy only')
                tips.append('<strong>{text1}:</strong> <em>{text2}</em>'.format(text1=text1, text2=text2))
            if service_item_from_item.theme and service_item_from_item.theme != -1:
                text = translate('OpenLP.ServiceManager', 'Slide theme')
                tips.append('<strong>{text1}:</strong> <em>{text2}</em>'.format(text1=text,
                                                                                text2=service_item_from_item.theme))
            if service_item_from_item.notes:
                text1 = translate('OpenLP.ServiceManager', 'Notes')
                text2 = html.escape(service_item_from_item.notes)
                tips.append('<strong>{text1}: </strong> {text2}'.format(text1=text1, text2=text2))
            if item['service_item'].is_capable(ItemCapabilities.HasVariableStartTime):
                tips.append(item['service_item'].get_media_time())
            if item['service_item'].is_capable(ItemCapabilities.HasMetaData):
                for meta in item['service_item'].metadata:
                    tips.append(meta)
            tree_widget_item.setToolTip(0, '<br>'.join(tips))
            tree_widget_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, item['order'])
            tree_widget_item.setData(0, SERVICE_META_ROLE, self._service_item_caption(service_item_from_item))
            tree_widget_item.setData(0, SERVICE_LIVE_ROLE,
                                     service_item_from_item.unique_identifier == self.live_item_identifier)
            tree_widget_item.setSelected(item['selected'])
            # Add the children to their parent tree_widget_item.
            for slide_index, slide in enumerate(service_item_from_item.get_frames()):
                try:
                    child = QtWidgets.QTreeWidgetItem(tree_widget_item)
                    # prefer to use a display_title
                    if service_item_from_item.is_capable(ItemCapabilities.HasDisplayTitle) or \
                            service_item_from_item.service_item_type is not ServiceItemType.Text:
                        text = slide['title'].replace('\n', ' ')
                    else:
                        text = service_item_from_item.get_rendered_frame(slide_index, clean=True)
                    child.setText(0, text[:40])
                    child.setData(0, QtCore.Qt.ItemDataRole.UserRole, slide_index)
                except RuntimeError:
                    # it's probably a "wrapped C/C++ object of type QTreeWidgetItem has been deleted" due to
                    # consecutive/parallel repaint_service_list execution. We've added some mitigation to avoid this
                    # to happen, but it for any reason it happens again, we'll silent it and try to repaint the list
                    # again (to avoid a broken list presented to the user).
                    self.is_running_repaint = False
                    return True
            tree_widget_item.setExpanded(item['expanded'])
        self.is_running_repaint = False
        return False

    def clean_up(self):
        """
        Empties the service_path of temporary files on system exit.
        """
        for file_name in os.listdir(self.service_path):
            file_path = Path(self.service_path, file_name)
            if os.path.isdir(file_path):
                shutil.rmtree(file_path, True)
            else:
                delete_file(file_path)

    def on_theme_combo_box_selected(self, current_index):
        """
        Set the theme for the current service.

        :param current_index: The combo box index for the selected item
        """
        self.service_theme = self.theme_combo_box.currentText()
        self.settings.setValue('servicemanager/service theme', self.service_theme)
        Registry().execute('theme_change_service')

    def on_theme_level_changed(self):
        """
        The theme may have changed in the settings dialog so make sure the theme combo box is in the correct state.
        """
        self.set_theme_visibility()
        self.regenerate_service_items()

    def on_service_theme_change(self):
        """
        Set the theme for the current service from the settings
        """
        self.service_theme = self.settings.value('servicemanager/service theme')
        find_and_set_in_combo_box(self.theme_combo_box, self.service_theme)
        Registry().execute('theme_change_service')

    def regenerate_changed_service_items(self):
        """
        Regenerate the changed service items, marking the service as unsaved.
        """
        self.regenerate_service_items(changed=True)

    def regenerate_service_items(self, changed=False):
        """
        Rebuild the service list as things have changed and a repaint is the easiest way to do this.

        :param changed: True if the list has changed for new / removed items. False for a theme change.
        """
        self.application.set_busy_cursor()
        was_modified = self.is_modified()
        # force reset of renderer as theme data has changed
        self.service_has_all_original_files = True
        if self.service_items:
            for item in self.service_items:
                item['selected'] = False
            service_iterator = QtWidgets.QTreeWidgetItemIterator(self.service_manager_list)
            selected_item = None
            while service_iterator.value():
                if service_iterator.value().isSelected():
                    selected_item = service_iterator.value()
                service_iterator += 1
            if selected_item is not None:
                if selected_item.parent() is None:
                    pos = selected_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                else:
                    pos = selected_item.parent().data(0, QtCore.Qt.ItemDataRole.UserRole)
                self.service_items[pos - 1]['selected'] = True
            temp_service_items = self.service_items
            self.service_manager_list.clear()
            self.service_items = []
            self.is_new = True
            for item in temp_service_items:
                self.add_service_item(item['service_item'], False, expand=item['expanded'], repaint=False,
                                      selected=item['selected'])
            # Set to False as items may have changed rendering does not impact the saved song so True may also be valid
            self.set_modified(changed or was_modified)
            # Repaint it once only at the end
            self.repaint_service_list(-1, -1)
        self.application.set_normal_cursor()

    def replace_service_item(self, new_item):
        """
        Using the service item passed replace the one with the same edit id if found.

        :param new_item: a new service item to up date an existing one.
        """
        for item_count, item in enumerate(self.service_items):
            if item['service_item'].edit_id == new_item.edit_id and item['service_item'].name == new_item.name:
                new_item.merge(item['service_item'])
                item['service_item'] = new_item
                self.repaint_service_list(item_count + 1, 0)
                self.live_controller.replace_service_manager_item(new_item)
                self.set_modified()

    def add_service_item(self, item, rebuild=False, expand=None, replace=-1, repaint=True, selected=False,
                         position=-1):
        """
        Add a Service item to the list

        :param item: Service Item to be added
        :param rebuild: Do we need to rebuild the live display (Default False)
        :param expand: Override the default expand settings. (Tristate)
        :param replace: The service item to be replaced
        :param repaint: Do we need to repaint the service item list (Default True)
        :param selected: Has the item been selected (Default False)
        :param position: The position where the item is dropped (Default -1)
        """
        # if not passed set to config value
        if expand is None:
            expand = self.settings.value('advanced/expand service item')
        item.from_service = True
        if position != -1:
            self.drop_position = position
        if replace > -1:
            item.merge(self.service_items[replace]['service_item'])
            self.service_items[replace]['service_item'] = item
            self.repaint_service_list(replace, -1)
            self.live_controller.replace_service_manager_item(item)
        else:
            item.render_text_items()
            # nothing selected for dnd
            if self.drop_position == -1:
                if isinstance(item, list):
                    for ind_item in item:
                        self.service_items.append({'service_item': ind_item,
                                                   'order': len(self.service_items) + 1,
                                                   'expanded': expand, 'selected': selected})
                else:
                    self.service_items.append({'service_item': item,
                                               'order': len(self.service_items) + 1,
                                               'expanded': expand, 'selected': selected})
                if repaint:
                    self.repaint_service_list(len(self.service_items) - 1, -1)
            else:
                self.service_items.insert(self.drop_position,
                                          {'service_item': item, 'order': self.drop_position,
                                           'expanded': expand, 'selected': selected})
                self.repaint_service_list(self.drop_position, -1)
            # if rebuilding list make sure live is fixed.
            if rebuild:
                self.live_controller.replace_service_manager_item(item)
            if repaint:
                # Confirm the add where the operator can see it; a silent add is
                # the classic "did that do anything?" moment. Bulk loads pass
                # repaint=False, so they stay quiet.
                self._show_add_feedback(item)
        self.drop_position = -1
        self.set_modified()

    def _show_add_feedback(self, item):
        """
        Flash a short status bar confirmation that an item landed in the service.

        :param item: The service item (or list of items) that was added
        """
        try:
            if isinstance(item, list) and len(item) != 1:
                message = translate('OpenLP.ServiceManager',
                                    'Added {count} items to the service').format(count=len(item))
            else:
                single_item = item[0] if isinstance(item, list) else item
                message = translate('OpenLP.ServiceManager',
                                    'Added to service: {title}').format(title=single_item.get_display_title())
            self.main_window.show_status_message(message, 3000)
        except AttributeError:
            # No main window (or status bar) around, e.g. under test
            pass

    def delete_item(self):
        """
        Remove the current item from the service.
        """
        item = self.find_service_item()[0]
        if item != -1:
            self.service_items.remove(self.service_items[item])
            self.repaint_service_list(item - 1, -1)
            self.set_modified()
            self.servicemanager_changed.emit()

    def make_preview(self):
        """
        Send the current item to the Preview slide controller
        """
        self.application.set_busy_cursor()
        item, child = self.find_service_item()
        if self.service_items[item]['service_item'].is_valid:
            self.preview_controller.add_service_manager_item(self.service_items[item]['service_item'], child)
        else:
            critical_error_message_box(translate('OpenLP.ServiceManager', 'Missing Display Handler'),
                                       translate('OpenLP.ServiceManager',
                                                 'Your item cannot be displayed as there is no handler to display it'))
        self.application.set_normal_cursor()

    def get_service_item(self):
        """
        Send the current item to the Preview slide controller
        """
        item = self.find_service_item()[0]
        if item == -1:
            return False
        else:
            return self.service_items[item]['service_item']

    def on_double_click_live(self):
        """
        Send the current item to the Live slide controller but triggered by a tablewidget click event.
        """
        self.list_double_clicked = True
        self.make_live()

    def on_single_click_preview(self):
        """
        If single click previewing is enabled, and triggered by a tablewidget click event,
        start a timeout to verify a double-click hasn't triggered.
        """
        if self.settings.value('advanced/single click service preview'):
            if not self.list_double_clicked:
                # If a double click has not registered start a timer, otherwise wait for the existing timer to finish.
                QtCore.QTimer.singleShot(QtWidgets.QApplication.instance().doubleClickInterval(),
                                         self.on_single_click_preview_timeout)

    def on_single_click_preview_timeout(self):
        """
        If a single click ok, but double click not triggered, send the current item to the Preview slide controller.
        """
        if self.list_double_clicked:
            # If a double click has registered, clear it.
            self.list_double_clicked = False
        else:
            # Otherwise preview the item.
            self.make_preview()

    def make_live(self, row=-1):
        """
        Send the current item to the Live slide controller

        :param row: Row number to be displayed if from preview. -1 is passed if the value is not set
        """
        item, child = self.find_service_item()
        # No items in service
        if item == -1:
            return
        if row != -1:
            child = row
        self.application.set_busy_cursor()
        if self.service_items[item]['service_item'].is_valid:
            self.servicemanager_changed.emit()
            self.live_controller.add_service_manager_item(self.service_items[item]['service_item'], child)
            if self.settings.value('core/auto preview'):
                item += 1
                if self.service_items and item < len(self.service_items) and \
                        self.service_items[item]['service_item'].is_capable(ItemCapabilities.CanPreview):
                    self.preview_controller.add_service_manager_item(self.service_items[item]['service_item'], 0)
                    self.live_controller.preview_widget.setFocus()
        else:
            critical_error_message_box(translate('OpenLP.ServiceManager', 'Missing Display Handler'),
                                       translate('OpenLP.ServiceManager',
                                                 'Your item cannot be displayed as the plugin required to display it '
                                                 'is missing or inactive'))
        self.application.set_normal_cursor()

    def remote_edit(self):
        """
        Triggers a remote edit to a plugin to allow item to be edited.
        """
        item = self.find_service_item()[0]
        if self.service_items[item]['service_item'].is_capable(ItemCapabilities.CanEdit):
            new_item = Registry().get(self.service_items[item]['service_item'].name). \
                on_remote_edit(self.service_items[item]['service_item'].edit_id)
            if new_item:
                self.add_service_item(new_item, replace=item)

    def on_service_item_rename(self):
        """
        Opens a dialog to rename the service item.
        """
        item = self.find_service_item()[0]
        if not self.service_items[item]['service_item'].is_capable(ItemCapabilities.CanEditTitle):
            return
        title = self.service_items[item]['service_item'].title
        title, ok = QtWidgets.QInputDialog.getText(self, translate('OpenLP.ServiceManager', 'Rename item title'),
                                                   translate('OpenLP.ServiceManager', 'Title:'),
                                                   QtWidgets.QLineEdit.EchoMode.Normal, self.tr(title))
        if ok:
            self.service_items[item]['service_item'].title = title
            self.repaint_service_list(item, -1)
            self.set_modified()

    def create_custom(self):
        """
        Saves the current text item as a custom slide and opens the custom tab (if is not open)
        """
        item = self.find_service_item()[0]
        Registry().execute('custom_create_from_service', self.service_items[item]['service_item'])
        for pos in range(1, self.main_window.media_tool_box.count()):
            if self.main_window.media_tool_box.itemText(pos) == Registry().execute('custom_visible_name')[0]:
                self.main_window.media_tool_box.setItemEnabled(pos, True)
                self.main_window.media_tool_box.setCurrentIndex(pos)

    def find_service_item(self):
        """
        Finds the first selected ServiceItem in the list and returns the position of the service_item_from_item and its
        selected child item. For example, if the third child item (in the Slidecontroller known as slide) in the
        second service item is selected this will return::

            (1, 2)
        """
        items = self.service_manager_list.selectedItems()
        service_item = -1
        service_item_child = -1
        for item in items:
            parent_item = item.parent()
            if parent_item is None:
                service_item = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            else:
                service_item = parent_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                service_item_child = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            # Adjust for zero based arrays.
            service_item -= 1
            # Only process the first item on the list for this method.
            break
        return service_item, service_item_child

    def drop_event(self, event):
        """
        Receive drop event and trigger an internal event to get the plugins to build and push the correct service item.
        The drag event payload carries the plugin name

        :param event: Handle of the event passed
        """
        link = event.mimeData()
        if link.hasUrls():
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.accept()
            for url in link.urls():
                file_path = Path(url.toLocalFile())
                if file_path.suffix == '.osz':
                    self.load_service(file_path)
                elif file_path.suffix == '.oszl':
                    # todo correct
                    self.load_service(file_path)
        elif link.hasText():
            plugin = link.text()
            item = self.service_manager_list.itemAt(event.pos())
            # ServiceManager started the drag and drop
            if plugin == 'ServiceManager':
                start_pos, child = self.find_service_item()
                # If no items selected
                if start_pos == -1:
                    return
                if item is None:
                    end_pos = len(self.service_items) - 1
                else:
                    end_pos = get_parent_item_data(item) - 1
                service_item = self.service_items[start_pos]
                if start_pos != end_pos:
                    self.service_items.remove(service_item)
                    self.service_items.insert(end_pos, service_item)
                    self.repaint_service_list(end_pos, child)
                    self.set_modified()
            else:
                # we are not over anything so drop
                replace = False
                if item is None:
                    self.drop_position = len(self.service_items)
                else:
                    # we are over something so lets investigate
                    pos = get_parent_item_data(item) - 1
                    service_item = self.service_items[pos]
                    if (plugin == service_item['service_item'].name and
                            service_item['service_item'].is_capable(ItemCapabilities.CanAppend)):
                        action = self.dnd_menu.exec(QtGui.QCursor.pos())
                        # New action required
                        if action == self.new_action:
                            self.drop_position = get_parent_item_data(item)
                        # Append to existing action
                        if action == self.add_to_action:
                            self.drop_position = get_parent_item_data(item)
                            item.setSelected(True)
                            replace = True
                    else:
                        self.drop_position = get_parent_item_data(item) - 1
                Registry().execute('{plugin}_add_service_item'.format(plugin=plugin), replace)
        else:
            self.log_warning('Unrecognised item')

    def update_theme_list(self, theme_list):
        """
        Called from ThemeManager when the Themes have changed

        :param theme_list: A list of current themes to be displayed
        """
        self.theme_combo_box.clear()
        self.theme_menu.clear()
        self.theme_combo_box.addItem('')
        theme_group = QtGui.QActionGroup(self.theme_menu)
        theme_group.setExclusive(True)
        theme_group.setObjectName('theme_group')
        # Create a "Default" theme, which allows the user to reset the item's theme to the service theme or global
        # theme.
        default_theme = create_widget_action(self.theme_menu, text=UiStrings().Default, checked=False,
                                             triggers=self.on_theme_change_action)
        self.theme_menu.setDefaultAction(default_theme)
        theme_group.addAction(default_theme)
        self.theme_menu.addSeparator()
        for theme in theme_list:
            self.theme_combo_box.addItem(theme)
            theme_group.addAction(create_widget_action(self.theme_menu, theme, text=theme, checked=False,
                                  triggers=self.on_theme_change_action))
        find_and_set_in_combo_box(self.theme_combo_box, self.service_theme)

    def on_theme_change_action(self, field=None):
        """
        Handles theme change events
        """
        theme = self.sender().objectName()
        # No object name means that the "Default" theme is supposed to be used.
        if not theme:
            theme = None
        item = self.find_service_item()[0]
        service_item = self.service_items[item]['service_item']
        # Needs to be checked before updating theme on service, as it generates a new identifier
        is_selected_item_live = self.live_controller.service_item and \
            service_item.unique_identifier == self.live_controller.service_item.unique_identifier
        service_item.update_theme(theme)
        # self.regenerate_service_items(True)
        if self.settings.value('themes/hot reload') and is_selected_item_live:
            self.live_controller.refresh_service_item(service_item)

    def on_make_live_action_triggered(self, checked):
        """
        Handle `make_live_action` when the action is triggered.

        :param bool checked: Not Used.
        :rtype: None
        """
        self.make_live()

    def get_drop_position(self):
        """
        Getter for drop_position. Used in: MediaManagerItem
        """
        return self.drop_position


def get_parent_item_data(item):
    """
    Finds and returns the parent item for any item

    :param item: The service item list item to be checked.
    """
    parent_item = item.parent()
    if parent_item is None:
        return item.data(0, QtCore.Qt.ItemDataRole.UserRole)
    else:
        return parent_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
