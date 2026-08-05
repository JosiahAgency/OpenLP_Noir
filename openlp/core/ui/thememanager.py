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
The Theme Manager manages adding, deleteing and modifying of themes.
"""
import os
import shutil
import zipfile
from pathlib import Path
from xml.etree.ElementTree import XML, ElementTree

from PySide6 import QtCore, QtWidgets

from openlp.core.common import delete_file
from openlp.core.common.applocation import AppLocation
from openlp.core.common.i18n import UiStrings, get_locale_key, translate
from openlp.core.common.mixins import LogMixin, RegistryProperties
from openlp.core.common.path import create_paths
from openlp.core.common.registry import Registry, RegistryBase
from openlp.core.common.utils import wait_for
from openlp.core.lib import build_icon, check_item_selected, create_thumb, get_text_file_string, validate_thumb
from openlp.core.lib.exceptions import ValidationError
from openlp.core.lib.theme import Theme
from openlp.core.lib.ui import MultipleViewModeList, add_list_view_mode_items_to_toolbar, create_widget_action, \
    critical_error_message_box, set_list_view_mode_toolbar_state
from openlp.core.state import State
from openlp.core.ui.filerenameform import FileRenameForm
from openlp.core.ui.icons import UiIcons
from openlp.core.ui.themeform import ThemeForm
from openlp.core.ui.themeprogressform import ThemeProgressForm
from openlp.core.widgets.dialogs import FileDialog
from openlp.core.widgets.toolbar import OpenLPToolbar

THUMBNAIL_REBUILD_MARKER_SETTING = 'themes/theme thumbnails rebuilt'


class Ui_ThemeManager(object):
    """
    UI part of the Theme Manager
    """

    def setup_ui(self, widget):
        """
        Define the UI
        :param widget: The screen object the dialog is to be attached to.
        """
        # start with the layout
        self.layout = QtWidgets.QVBoxLayout(widget)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setObjectName('layout')
        self.toolbar = OpenLPToolbar(widget)
        self.toolbar.setObjectName('toolbar')
        self.toolbar.add_toolbar_action('newTheme',
                                        text=UiStrings().NewTheme, icon=UiIcons().new,
                                        tooltip=translate('OpenLP.ThemeManager', 'Create a new theme.'),
                                        triggers=self.on_add_theme)
        self.toolbar.add_toolbar_action('editTheme',
                                        text=translate('OpenLP.ThemeManager', 'Edit Theme'),
                                        icon=UiIcons().edit,
                                        tooltip=translate('OpenLP.ThemeManager', 'Edit a theme.'),
                                        triggers=self.on_edit_theme)
        self.delete_toolbar_action = self.toolbar.add_toolbar_action('delete_theme',
                                                                     text=translate('OpenLP.ThemeManager',
                                                                                    'Delete Theme'),
                                                                     icon=UiIcons().delete,
                                                                     tooltip=translate('OpenLP.ThemeManager',
                                                                                       'Delete a theme.'),
                                                                     triggers=self.on_delete_theme)
        self.toolbar.addSeparator()
        self.toolbar.add_toolbar_action('importTheme',
                                        text=translate('OpenLP.ThemeManager', 'Import Theme'),
                                        icon=UiIcons().download,
                                        tooltip=translate('OpenLP.ThemeManager', 'Import a theme.'),
                                        triggers=self.on_import_theme)
        self.toolbar.add_toolbar_action('exportTheme',
                                        text=translate('OpenLP.ThemeManager', 'Export Theme'),
                                        icon=UiIcons().upload,
                                        tooltip=translate('OpenLP.ThemeManager', 'Export a theme.'),
                                        triggers=self.on_export_theme)
        self.toolbar.addSeparator()
        add_list_view_mode_items_to_toolbar(self.toolbar, self)
        self.layout.addWidget(self.toolbar)
        self.theme_widget = QtWidgets.QWidgetAction(self.toolbar)
        self.theme_widget.setObjectName('theme_widget')
        # create theme manager list
        self.theme_list_widget = MultipleViewModeList(widget)
        self.theme_list_widget.setAlternatingRowColors(True)
        self.theme_list_widget.setIconSize(QtCore.QSize(88, 50))
        self.theme_list_widget.set_icon_size_by_view_mode(QtWidgets.QListView.ViewMode.ListMode, QtCore.QSize(88, 50))
        self.theme_list_widget.set_icon_size_by_view_mode(QtWidgets.QListView.ViewMode.IconMode,
                                                          QtCore.QSize(176, 100))
        self.theme_list_widget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.theme_list_widget.setObjectName('theme_list_widget')
        self.layout.addWidget(self.theme_list_widget)
        self.theme_list_widget.customContextMenuRequested.connect(self.context_menu)
        # build the context menu
        self.menu = QtWidgets.QMenu()
        self.edit_action = create_widget_action(self.menu,
                                                text=translate('OpenLP.ThemeManager', '&Edit Theme'),
                                                icon=UiIcons().edit, triggers=self.on_edit_theme)
        self.copy_action = create_widget_action(self.menu,
                                                text=translate('OpenLP.ThemeManager', '&Copy Theme'),
                                                icon=UiIcons().copy, triggers=self.on_copy_theme)
        self.rename_action = create_widget_action(self.menu,
                                                  text=translate('OpenLP.ThemeManager', '&Rename Theme'),
                                                  icon=UiIcons().edit, triggers=self.on_rename_theme)
        self.delete_action = create_widget_action(self.menu,
                                                  text=translate('OpenLP.ThemeManager', '&Delete Theme'),
                                                  icon=UiIcons().delete, triggers=self.on_delete_theme)
        self.menu.addSeparator()
        self.global_action = create_widget_action(self.menu,
                                                  text=translate('OpenLP.ThemeManager', 'Set As &Global Default'),
                                                  icon=UiIcons().default,
                                                  triggers=self.change_global_from_screen)
        self.export_action = create_widget_action(self.menu,
                                                  text=translate('OpenLP.ThemeManager', '&Export Theme'),
                                                  icon=UiIcons().upload, triggers=self.on_export_theme)
        # Signals
        self.theme_list_widget.doubleClicked.connect(self.change_global_from_screen)
        self.theme_list_widget.currentItemChanged.connect(self.check_list_state)

        Registry().register_function('get_theme_names', self.get_theme_names)


class ThemeManager(QtWidgets.QWidget, RegistryBase, Ui_ThemeManager, LogMixin, RegistryProperties):
    """
    Manages the orders of Theme.
    """
    # These signals are used by the web api to update the theme on the ui thread
    theme_update_global = QtCore.Signal()
    theme_level_updated = QtCore.Signal()

    def __init__(self, parent=None):
        """
        Constructor
        """
        super(ThemeManager, self).__init__(parent)
        # Variables
        self._theme_list = {}
        self.old_background_image_path = None
        Registry().register_function('config_screen_changed', self.screen_changed)

    def get_global_theme(self):
        return self.get_theme_data(self.global_theme)

    def get_theme_data(self, theme_name):
        """
        Gets a theme given a name, returns the default theme if missing
        """
        theme = Theme()
        if theme_name in self._theme_list:
            theme = self._theme_list[theme_name]
        else:
            self.log_warning('Missing requested theme data for "{}", using default theme'.format(theme_name))
        return theme

    def bootstrap_initialise(self):
        """
        process the bootstrap initialise setup request
        """
        self.setup_ui(self)
        self.global_theme = self.settings.value('themes/global theme')
        self.build_theme_path()
        Registry().register_function('reload_global_theme', self.on_update_global_theme)
        # These signals are used by the web api to update the theme on the ui thread
        self.theme_level_updated.connect(self.on_theme_level_updated)
        self.theme_update_global.connect(self.on_update_global_theme)

    def bootstrap_post_set_up(self):
        """
        process the bootstrap post setup request
        """
        self.load_settings()
        self.progress_form = ThemeProgressForm(self)
        self.theme_form = ThemeForm(self)
        self.theme_form.path = self.theme_path
        self.file_rename_form = FileRenameForm()
        self.upgrade_themes()
        self.load_themes()
        self.rebuild_theme_thumbnails_once()

    def rebuild_theme_thumbnails_once(self):
        """
        Rebuild cached theme thumbnails once after startup so existing broken previews are repaired.
        """
        if self.settings.value(THUMBNAIL_REBUILD_MARKER_SETTING):
            return
        theme_names = self.get_theme_names()
        if theme_names:
            self.log_info('Rebuilding theme thumbnails once')
            self.update_preview_images(theme_names)
        self.settings.setValue(THUMBNAIL_REBUILD_MARKER_SETTING, True)

    def load_settings(self):
        view_mode_value = None
        try:
            view_mode_value = self.settings.value('user interface/theme manager view mode')
            self.theme_list_widget.setViewMode(view_mode_value)
        except Exception:
            view_mode_value = QtWidgets.QListWidget.ViewMode.ListMode
            self.settings.setValue('user interface/theme manager view mode', view_mode_value)
        set_list_view_mode_toolbar_state(self.toolbar, view_mode_value)

    def save_settings(self):
        if self.theme_list_widget:
            self.settings.setValue('user interface/theme manager view mode', self.theme_list_widget.viewMode())

    def screen_changed(self):
        """
        Update the default theme location and size for when screen size changed
        """
        for theme_name in self._theme_list:
            theme_object = self._theme_list[theme_name]
            theme_object.set_default_header_footer()

    def upgrade_themes(self):
        """
        Upgrade the xml files to json.

        :rtype: None
        """
        xml_file_paths = [p for p in AppLocation.get_section_data_path('themes').glob('*/*.xml')]
        # Exit early if there are no themes to upgrade
        if not xml_file_paths:
            return
        # Wait for 2 seconds to allow some other things to start processing first
        wait_for(lambda: False, timeout=1)
        for xml_file_path in xml_file_paths:
            theme_data = get_text_file_string(xml_file_path)
            theme = self._create_theme_from_xml(theme_data, self.theme_path)
            self.save_theme(theme)
            xml_file_path.unlink()

    def build_theme_path(self):
        """
        Set up the theme path variables

        :rtype: None
        """
        self.theme_path = AppLocation.get_section_data_path('themes')
        self.thumb_path = self.theme_path / 'thumbnails'
        create_paths(self.theme_path, self.thumb_path)

    def check_list_state(self, item, field=None):
        """
        If Default theme selected remove delete button.
        Note for some reason a dummy field is required.  Nothing is passed!

        :param field:
        :param item: Service Item to process
        """
        if item is None:
            return
        real_theme_name = item.data(QtCore.Qt.ItemDataRole.UserRole)
        theme_name = item.text()
        # If default theme restrict actions
        if real_theme_name == theme_name:
            self.delete_toolbar_action.setVisible(True)
        else:
            self.delete_toolbar_action.setVisible(False)

    def context_menu(self, point):
        """
        Build the Right Click Context menu and set state depending on the type of theme.

        :param point: The position of the mouse so the correct item can be found.
        """
        item = self.theme_list_widget.itemAt(point)
        if item is None:
            return
        real_theme_name = item.data(QtCore.Qt.ItemDataRole.UserRole)
        theme_name = str(item.text())
        visible = real_theme_name == theme_name
        self.delete_action.setVisible(visible)
        self.rename_action.setVisible(visible)
        self.global_action.setVisible(visible)
        self.menu.exec(self.theme_list_widget.mapToGlobal(point))

    def on_update_global_theme(self):
        """
        Update the global theme to the theme set in the settings.
        """
        self.global_theme = self.settings.value('themes/global theme')
        self.log_debug('on_update_global_theme {text}'.format(text=self.global_theme))
        for count in range(0, self.theme_list_widget.count()):
            # reset the old name
            item = self.theme_list_widget.item(count)
            old_name = item.text()
            new_name = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if old_name != new_name:
                self.theme_list_widget.item(count).setText(new_name)
            # Set the new name
            if self.global_theme == new_name:
                name = translate('OpenLP.ThemeManager', '{text} (default)').format(text=new_name)
                self.theme_list_widget.item(count).setText(name)
                self.delete_toolbar_action.setVisible(item not in self.theme_list_widget.selectedItems())
        Registry().execute('theme_change_global')

    def on_set_view_mode_list(self):
        mode = QtWidgets.QListView.ViewMode.ListMode
        self.theme_list_widget.setViewMode(mode)
        set_list_view_mode_toolbar_state(self.toolbar, mode)

    def on_set_view_mode_grid(self):
        mode = QtWidgets.QListView.ViewMode.IconMode
        self.theme_list_widget.setViewMode(mode)
        set_list_view_mode_toolbar_state(self.toolbar, mode)

    def on_theme_level_updated(self):
        """
        Update the theme level, called from web controller.
        """
        Registry().execute('theme_level_changed')

    def change_global_from_screen(self, index=-1):
        """
        Change the global theme when a theme is double clicked upon in the Theme Manager list.

        :param index:
        """
        selected_row = self.theme_list_widget.currentRow()
        for count in range(0, self.theme_list_widget.count()):
            item = self.theme_list_widget.item(count)
            old_name = item.text()
            # reset the old name
            if old_name != item.data(QtCore.Qt.ItemDataRole.UserRole):
                self.theme_list_widget.item(count).setText(item.data(QtCore.Qt.ItemDataRole.UserRole))
            # Set the new name
            if count == selected_row:
                self.global_theme = self.theme_list_widget.item(count).text()
                name = translate('OpenLP.ThemeManager', '{text} (default)').format(text=self.global_theme)
                self.theme_list_widget.item(count).setText(name)
                self.settings.setValue('themes/global theme', self.global_theme)
        Registry().execute('theme_change_global')

    def on_add_theme(self, field=None):
        """
        Loads a new theme with the default settings and then launches the theme editing form for the user to make
        their customisations.
        :param field:
        """
        theme = Theme()
        self.theme_form.theme = theme
        self.theme_form.exec()
        self.load_themes()

    def on_rename_theme(self, field=None):
        """
        Renames an existing theme to a new name
        :param field:
        """
        if self._validate_theme_action(translate('OpenLP.ThemeManager', 'You must select a theme to rename.'),
                                       translate('OpenLP.ThemeManager', 'Rename Confirmation'),
                                       translate('OpenLP.ThemeManager', 'Rename {theme_name} theme?'), False, False):
            item = self.theme_list_widget.currentItem()
            old_theme_name = item.data(QtCore.Qt.ItemDataRole.UserRole)
            self.file_rename_form.file_name_edit.setText(old_theme_name)
            if self.file_rename_form.exec():
                new_theme_name = self.file_rename_form.file_name_edit.text()
                if old_theme_name == new_theme_name:
                    return
                if self.check_if_theme_exists(new_theme_name):
                    old_theme_data = self.get_theme_data(old_theme_name)
                    self.clone_theme_data(old_theme_data, new_theme_name)
                    self.delete_theme(old_theme_name)
                    for plugin in State().list_plugins():
                        if plugin.uses_theme(old_theme_name):
                            plugin.rename_theme(old_theme_name, new_theme_name)
                    self.renderer.set_theme(self.get_theme_data(new_theme_name))
                    self.load_themes()

    def on_copy_theme(self, field=None):
        """
        Copies an existing theme to a new name
        :param field:
        """
        item = self.theme_list_widget.currentItem()
        old_theme_name = item.data(QtCore.Qt.ItemDataRole.UserRole)
        self.file_rename_form.file_name_edit.setText(translate('OpenLP.ThemeManager',
                                                               'Copy of {name}',
                                                               'Copy of <theme name>').format(name=old_theme_name))
        if self.file_rename_form.exec(True):
            new_theme_name = self.file_rename_form.file_name_edit.text()
            if self.check_if_theme_exists(new_theme_name):
                theme_data = self.get_theme_data(old_theme_name)
                self.clone_theme_data(theme_data, new_theme_name)

    def clone_theme_data(self, theme_data, new_theme_name):
        """
        Takes a theme and makes a new copy of it as well as saving it.

        :param Theme theme_data: The theme to be used
        :param str new_theme_name: The new theme name of the theme
        :rtype: None
        """
        old_background = None
        if theme_data.background_type == 'image' or theme_data.background_type == 'video':
            old_background = theme_data.background_filename
            theme_data.background_filename = self.theme_path / new_theme_name / theme_data.background_filename.name
        theme_data.theme_name = new_theme_name
        theme_data.extend_image_filename(self.theme_path)
        self.save_theme(theme_data, background_file=old_background)
        self.update_preview_images([new_theme_name])
        self.load_themes()

    def on_edit_theme(self, field=None):
        """
        Loads the settings for the theme that is to be edited and launches the
        theme editing form so the user can make their changes.
        :param field:
        """
        if check_item_selected(self.theme_list_widget,
                               translate('OpenLP.ThemeManager', 'You must select a theme to edit.')):
            item = self.theme_list_widget.currentItem()
            theme = self.get_theme_data(item.data(QtCore.Qt.ItemDataRole.UserRole))
            if theme.background_type == 'image' or theme.background_type == 'video':
                self.old_background_image_path = theme.background_filename
            self.theme_form.theme = theme
            self.theme_form.exec(True)
            self.old_background_image_path = None
            self.renderer.set_theme(theme)
            self.load_themes()

    def on_delete_theme(self, field=None):
        """
        Delete a theme triggered by the UI.
        :param field:
        """
        if self._validate_theme_action(translate('OpenLP.ThemeManager', 'You must select a theme to delete.'),
                                       translate('OpenLP.ThemeManager', 'Delete Confirmation'),
                                       translate('OpenLP.ThemeManager', 'Delete {theme_name} theme?')):
            item = self.theme_list_widget.currentItem()
            theme = item.text()
            row = self.theme_list_widget.row(item)
            self.theme_list_widget.takeItem(row)
            self.delete_theme(theme)
            # self.renderer.set_theme(self.get_theme_data(item.data(QtCore.Qt.ItemDataRole.UserRole)))
            # As we do not reload the themes, push out the change. Reload the
            # list as the internal lists and events need to be triggered.
            self._push_themes()

    def delete_theme(self, theme):
        """
        Delete a theme.

        :param theme: The theme to delete.
        """
        self._theme_list.pop(theme)
        thumb = '{name}.png'.format(name=theme)
        delete_file(self.theme_path / thumb)
        delete_file(self.thumb_path / thumb)
        try:
            shutil.rmtree(self.theme_path / theme)
        except OSError:
            self.log_exception('Error deleting theme {name}'.format(name=theme))

    def on_export_theme(self, checked=None):
        """
        Export the theme to a zip file

        :param bool checked: Sent by the QAction.triggered signal. It's not used in this method.
        :rtype: None
        """
        item = self.theme_list_widget.currentItem()
        if item is None:
            critical_error_message_box(message=translate('OpenLP.ThemeManager', 'You have not selected a theme.'))
            return
        theme_name = item.data(QtCore.Qt.ItemDataRole.UserRole)
        export_path, filter_used = \
            FileDialog.getSaveFileName(self.main_window,
                                       translate('OpenLP.ThemeManager',
                                                 'Save Theme - ({name})').format(name=theme_name),
                                       self.settings.value('themes/last directory export'),
                                       translate('OpenLP.ThemeManager', 'OpenLP Themes (*.otz)'),
                                       translate('OpenLP.ThemeManager', 'OpenLP Themes (*.otz)'))
        self.application.set_busy_cursor()
        if export_path:
            self.settings.setValue('themes/last directory export', export_path.parent)
            if self._export_theme(export_path.with_suffix('.otz'), theme_name):
                QtWidgets.QMessageBox.information(self,
                                                  translate('OpenLP.ThemeManager', 'Theme Exported'),
                                                  translate('OpenLP.ThemeManager',
                                                            'Your theme has been successfully exported.'))
        self.application.set_normal_cursor()

    def _export_theme(self, theme_path, theme_name):
        """
        Create the zipfile with the theme contents.

        :param Path theme_path: Location where the zip file will be placed
        :param str theme_name: The name of the theme to be exported
        :return: The success of creating the zip file
        :rtype: bool
        """
        try:
            with zipfile.ZipFile(theme_path, 'w') as theme_zip:
                source_path = self.theme_path / theme_name
                for file_path in source_path.iterdir():
                    theme_zip.write(file_path, Path(theme_name, file_path.name))
            return True
        except OSError as ose:
            self.log_exception('Export Theme Failed')
            critical_error_message_box(translate('OpenLP.ThemeManager', 'Theme Export Failed'),
                                       translate('OpenLP.ThemeManager',
                                                 'The {theme_name} export failed because this error occurred: {err}')
                                       .format(theme_name=theme_name, err=ose.strerror))
            if theme_path.exists():
                shutil.rmtree(theme_path, ignore_errors=True)
            return False

    def on_import_theme(self, checked=None):
        """
        Opens a file dialog to select the theme file(s) to import before attempting to extract OpenLP themes from
        those files. This process will only load version 2 themes.

        :param bool checked: Sent by the QAction.triggered signal. It's not used in this method.
        :rtype: None
        """
        file_paths, filter_used = FileDialog.getOpenFileNames(
            self,
            translate('OpenLP.ThemeManager', 'Select Theme Import File'),
            self.settings.value('themes/last directory import'),
            translate('OpenLP.ThemeManager', 'OpenLP Themes (*.otz)'))
        self.log_info('New Themes {file_paths}'.format(file_paths=file_paths))
        if not file_paths:
            return
        self.application.set_busy_cursor()
        new_themes = []
        for file_path in file_paths:
            new_themes.append(self.unzip_theme(file_path))
        self.settings.setValue('themes/last directory import', file_path.parent)
        self.update_preview_images(new_themes)
        self.application.set_normal_cursor()

    def load_first_time_themes(self):
        """
        Imports any themes on start up and makes sure there is at least one theme
        """
        self.application.set_busy_cursor()
        theme_paths = AppLocation.get_files('themes', '.otz')
        new_themes = []
        for theme_path in theme_paths:
            theme_path = self.theme_path / theme_path
            new_themes.append(self.unzip_theme(theme_path))
            delete_file(theme_path)
        # No themes have been found so create one
        if not theme_paths:
            theme = Theme()
            theme.theme_name = UiStrings().Default
            self.save_theme(theme)
            self.settings.setValue('themes/global theme', theme.theme_name)
            new_themes = [theme.theme_name]
        if new_themes:
            self.update_preview_images(new_themes)
        self.application.set_normal_cursor()

    def load_themes(self):
        """
        Loads the theme lists and triggers updates across the whole system using direct calls or core functions and
        events for the plugins.
        The plugins will call back in to get the real list if they want it.
        """
        self._theme_list.clear()
        self.theme_list_widget.clear()
        files = AppLocation.get_files('themes', '/*.json')
        # Sort the themes by its name considering language specific
        files.sort(key=lambda file_name: get_locale_key(str(file_name)))
        # now process the file list of png files
        for file in files:
            # check to see file is in theme root directory
            theme_path = self.theme_path / file
            if theme_path.exists():
                text_name = theme_path.stem
                if text_name == self.global_theme:
                    name = translate('OpenLP.ThemeManager', '{name} (default)').format(name=text_name)
                else:
                    name = text_name
                thumb_path = self.thumb_path / '{name}.png'.format(name=text_name)
                item_name = QtWidgets.QListWidgetItem(name)
                if validate_thumb(theme_path, thumb_path):
                    icon = build_icon(thumb_path)
                else:
                    icon = create_thumb(theme_path, thumb_path)
                item_name.setIcon(icon)
                item_name.setData(QtCore.Qt.ItemDataRole.UserRole, text_name)
                self.theme_list_widget.addItem(item_name)
                self._theme_list[text_name] = self._get_theme_data(text_name)
        self._push_themes()

    def _push_themes(self):
        """
        Notify listeners that the theme list has been updated
        """
        Registry().execute('theme_update_list', self.get_theme_names())

    def get_theme_names(self):
        """
        Return the list of loaded themes
        """
        return [theme_name for theme_name in self._theme_list]

    def _get_theme_data(self, theme_name):
        """
        Returns a theme object from a JSON file

        :param str theme_name: Name of the theme to load from file
        :return:  The theme object.
        :rtype: Theme
        """
        theme_name = str(theme_name)
        theme_file_path = self.theme_path / theme_name / '{file_name}.json'.format(file_name=theme_name)
        theme_data = get_text_file_string(theme_file_path)
        if not theme_data:
            self.log_debug('No theme data - using default theme')
            return Theme()
        theme_object = self._create_theme_from_json(theme_data, self.theme_path)
        theme_object.set_default_header_footer()
        return theme_object

    def over_write_message_box(self, theme_name):
        """
        Display a warning box to the user that a theme already exists

        :param theme_name: Name of the theme.
        :return: Confirm if the theme is to be overwritten.
        """
        ret = QtWidgets.QMessageBox.question(self, translate('OpenLP.ThemeManager', 'Theme Already Exists'),
                                             translate('OpenLP.ThemeManager',
                                                       'Theme {name} already exists. '
                                                       'Do you want to replace it?').format(name=theme_name),
                                             defaultButton=QtWidgets.QMessageBox.StandardButton.No)
        return ret == QtWidgets.QMessageBox.StandardButton.Yes

    def unzip_theme(self, file_path):
        """
        Unzip the theme, remove the preview file if stored. Generate a new preview file. Check the XML theme version
        and upgrade if necessary.
        :param Path file_path:
        """
        self.log_debug('Unzipping theme {name}'.format(name=file_path))
        file_xml = None
        abort_import = True
        json_theme = False
        theme_name = ""
        try:
            with zipfile.ZipFile(file_path) as theme_zip:
                json_file = [name for name in theme_zip.namelist() if os.path.splitext(name)[1].lower() == '.json']
                if len(json_file) != 1:
                    xml_file = [name for name in theme_zip.namelist() if os.path.splitext(name)[1].lower() == '.xml']
                    if len(xml_file) != 1:
                        self.log_error('Theme contains "{val:d}" theme files'.format(val=len(xml_file)))
                        raise ValidationError
                    xml_tree = ElementTree(element=XML(theme_zip.read(xml_file[0]))).getroot()
                    theme_version = xml_tree.get('version', default=None)
                    if not theme_version or float(theme_version) < 2.0:
                        self.log_error('Theme version is less than 2.0')
                        raise ValidationError
                    theme_name = xml_tree.find('name').text.strip()
                else:
                    new_theme = Theme()
                    new_theme.load_theme(theme_zip.read(json_file[0]).decode("utf-8"))
                    theme_name = new_theme.theme_name
                    json_theme = True
                theme_folder = self.theme_path / theme_name
                if theme_folder.exists() and not self.over_write_message_box(theme_name):
                    abort_import = True
                    return
                else:
                    abort_import = False
                for zipped_file in theme_zip.namelist():
                    zipped_file_rel_path = Path(zipped_file)
                    split_name = zipped_file_rel_path.parts
                    if split_name[-1] == '' or len(split_name) == 1:
                        # is directory or preview file
                        continue
                    full_name = self.theme_path / zipped_file_rel_path
                    create_paths(full_name.parent)
                    if zipped_file_rel_path.suffix.lower() == '.xml':
                        # Legacy theme XML is converted to JSON below, so avoid
                        # persisting XML files on disk during import.
                        file_xml = str(theme_zip.read(zipped_file), 'utf-8')
                    elif zipped_file_rel_path.suffix.lower() == '.json':
                        file_xml = str(theme_zip.read(zipped_file), 'utf-8')
                        with full_name.open('w', encoding='utf-8') as out_file:
                            out_file.write(file_xml)
                    else:
                        with full_name.open('wb') as out_file:
                            out_file.write(theme_zip.read(zipped_file))
        except (OSError, ValidationError, zipfile.BadZipFile):
            self.log_exception('Importing theme from zip failed {name}'.format(name=file_path))
            critical_error_message_box(
                translate('OpenLP.ThemeManager', 'Import Error'),
                translate('OpenLP.ThemeManager', 'There was a problem importing {file_name}.\n\nIt is corrupt, '
                                                 'inaccessible or not a valid theme.').format(file_name=file_path))
        finally:
            ret = None
            if not abort_import:
                # As all files are closed, upgrade theme (xml to json) if needed.
                if file_xml and not json_theme:
                    theme_path = self.theme_path / theme_name
                    xml_file_paths = theme_path.glob('*.xml')
                    for xml_file_path in xml_file_paths:
                        xml_file_path.unlink()
                    theme = self._create_theme_from_xml(file_xml, self.theme_path)
                    self.save_theme(theme)
                ret = theme_name
        return ret

    def check_if_theme_exists(self, theme_name):
        """
        Check if theme already exists and displays error message

        :param str theme_name:  Name of the Theme to test
        :return: True or False if theme exists
        :rtype: bool
        """
        if (self.theme_path / theme_name).exists():
            critical_error_message_box(
                translate('OpenLP.ThemeManager', 'Validation Error'),
                translate('OpenLP.ThemeManager', 'A theme with this name already exists.'))
            return False
        return True

    def save_theme(self, theme, background_file=None):
        """
        Writes the theme to the disk and including the background image and thumbnail if necessary

        :param Theme theme: The theme data object.
        :param background_file: Background to use rather than background_source. Optional.
        :rtype: None
        """
        name = theme.theme_name
        theme_pretty = theme.export_theme(self.theme_path)
        theme_dir = self.theme_path / name
        create_paths(theme_dir)
        theme_path = theme_dir / '{file_name}.json'.format(file_name=name)
        try:
            theme_path.write_text(theme_pretty)
        except OSError:
            self.log_exception('Saving theme to file failed')
        if theme.background_filename and theme.background_type != 'stream':
            # Use theme source image if override doesn't exist
            if not background_file or not background_file.exists():
                background_file = theme.background_source
            if self.old_background_image_path and theme.background_filename != self.old_background_image_path:
                delete_file(self.old_background_image_path)
            if not background_file or not background_file.exists():
                self.log_warning('Background source does not exist, retaining cached background')
            elif background_file != theme.background_filename:
                try:
                    shutil.copyfile(background_file, theme.background_filename)
                except OSError:
                    self.log_exception('Failed to save theme image')

    def save_preview(self, theme_name, preview_pixmap):
        """
        Save the preview QPixmap object to a file
        """
        sample_path_name = self.theme_path / '{file_name}.png'.format(file_name=theme_name)
        if sample_path_name.exists():
            sample_path_name.unlink()
        preview_pixmap.save(str(sample_path_name), 'png')
        thumb_path = self.thumb_path / '{name}.png'.format(name=theme_name)
        create_thumb(sample_path_name, thumb_path, False)

    def update_preview_images(self, theme_name_list=None):
        """
        Called to update the themes' preview images.

        :param theme_name_list: A list of theme names in the theme data folder
        """
        theme_name_list = theme_name_list or self.get_theme_names()
        self.progress_form.theme_list = theme_name_list
        self.progress_form.show()
        for theme_name in theme_name_list:
            theme_data = self._get_theme_data(theme_name)
            preview_pixmap = self.progress_form.get_preview(theme_name, theme_data)
            if preview_pixmap is None:
                break
            self.save_preview(theme_name, preview_pixmap)
        self.progress_form.close()
        self.load_themes()

    def generate_image(self, theme_data, force_page=False):
        """
        Call the renderer to build a Sample Image

        :param theme_data: The theme to generated a preview for.
        :param force_page: Flag to tell message lines per page need to be generated.
        :rtype: QtGui.QPixmap
        """
        return self.renderer.generate_preview(theme_data, force_page)

    @staticmethod
    def _create_theme_from_xml(theme_xml, image_path):
        """
        Return a theme object using information parsed from XML

        :param theme_xml: The Theme data object.
        :param Path image_path: Where the theme image is stored
        :return: Theme data.
        :rtype: Theme
        """
        theme = Theme()
        theme.parse(theme_xml)
        theme.extend_image_filename(image_path)
        return theme

    def _create_theme_from_json(self, theme_json, image_path):
        """
        Return a theme object using information parsed from JSON

        :param theme_json: The Theme data object.
        :param Path image_path: Where the theme image is stored
        :return: Theme data.
        :rtype: Theme
        """
        theme = Theme()
        theme.load_theme(theme_json, self.theme_path)
        theme.extend_image_filename(image_path)
        return theme

    def _validate_theme_action(self, select_text, confirm_title, confirm_text, test_plugin=True, confirm=True):
        """
        Check to see if theme has been selected and the destructive action is allowed.

        :param select_text: Text for message box if no item selected.
        :param confirm_title: Confirm message title to be displayed.
        :param confirm_text: Confirm message text to be displayed.
        :param test_plugin: Do we check the plugins for theme usage.
        :param confirm: Do we display a confirm box before run checks.
        :return: True or False depending on the validity.
        """
        self.global_theme = self.settings.value('themes/global theme')
        if check_item_selected(self.theme_list_widget, select_text):
            item = self.theme_list_widget.currentItem()
            theme = item.text()
            # confirm deletion
            if confirm:
                answer = QtWidgets.QMessageBox.question(
                    self, confirm_title, confirm_text.format(theme_name=theme),
                    defaultButton=QtWidgets.QMessageBox.StandardButton.No)
                if answer == QtWidgets.QMessageBox.StandardButton.No:
                    return False
            # should be the same unless default
            if theme != item.data(QtCore.Qt.ItemDataRole.UserRole):
                critical_error_message_box(
                    message=translate('OpenLP.ThemeManager', 'You are unable to delete the default theme.'))
                return False
            # check for use in the system else where.
            if test_plugin:
                plugin_usage = ""
                for plugin in State().list_plugins():
                    used_count = plugin.uses_theme(theme)
                    if used_count:
                        plugin_usage = "{plug}{text}".format(plug=plugin_usage,
                                                             text=(translate('OpenLP.ThemeManager',
                                                                             '{count} time(s) by {plugin}'
                                                                             ).format(count=used_count,
                                                                                      plugin=plugin.name)))
                        plugin_usage = "{text}\n".format(text=plugin_usage)
                if plugin_usage:
                    critical_error_message_box(translate('OpenLP.ThemeManager', 'Unable to delete theme'),
                                               translate('OpenLP.ThemeManager',
                                                         'Theme is currently used \n\n{text}'
                                                         ).format(text=plugin_usage))

                    return False
            return True
        return False
