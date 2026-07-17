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
This is the main window, where all the action happens.
"""
import json
import shutil
import webbrowser
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from tempfile import gettempdir
from threading import Lock

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.api.http.server import HttpServer
from openlp.core.api.websockets import WebSocketServer
from openlp.core.common import add_actions
from openlp.core.common.actions import ActionList, CategoryOrder
from openlp.core.common.applocation import AppLocation
from openlp.core.common.i18n import LanguageManager, UiStrings, translate
from openlp.core.common.json import OpenLPJSONDecoder
from openlp.core.common.mixins import LogMixin, RegistryProperties
from openlp.core.common.path import create_paths, resolve
from openlp.core.common.platform import is_macosx, is_win
from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings
from openlp.core.display.screens import ScreenList
from openlp.core.lib.plugin import PluginStatus
from openlp.core.lib.ui import create_action
from openlp.core.projectors.manager import ProjectorManager
from openlp.core.state import State
from openlp.core.ui.aboutform import AboutForm
from openlp.core.ui.firsttimeform import FirstTimeForm
from openlp.core.ui.formattingtagform import FormattingTagForm
from openlp.core.ui.icons import UiIcons
from openlp.core.ui.logviewer import LogViewerPanel
from openlp.core.ui.pluginform import PluginForm
from openlp.core.ui.printserviceform import PrintServiceForm
from openlp.core.ui.servicemanager import ServiceManager
from openlp.core.ui.settingsform import SettingsForm
from openlp.core.ui.shortcutlistform import ShortcutListForm
from openlp.core.ui import HideMode
from openlp.core.ui.style import PROGRESSBAR_STYLE, UiThemes, get_library_stylesheet, is_ui_theme
from openlp.core.ui.thememanager import ThemeManager
from openlp.core.version import get_version
from openlp.core.widgets.dialogs import FileDialog
from openlp.core.widgets.docks import LibrarySidebar, MediaDockManager, OpenLPDockWidget


class Ui_MainWindow(object):
    """
    This is the UI part of the main window.
    """
    def setup_ui(self, main_window):
        """
        Set up the user interface
        """
        main_window.setObjectName('MainWindow')
        main_window.setWindowIcon(UiIcons().main_icon)
        main_window.setDockNestingEnabled(True)
        if is_macosx():
            main_window.setDocumentMode(True)
        # Set up the main container, which contains all the other form widgets.
        self.main_content = QtWidgets.QWidget(main_window)
        self.main_content.setObjectName('main_content')
        self.main_content_layout = QtWidgets.QHBoxLayout(self.main_content)
        self.main_content_layout.setSpacing(0)
        self.main_content_layout.setContentsMargins(0, 0, 0, 0)
        self.main_content_layout.setObjectName('main_content_layout')
        main_window.setCentralWidget(self.main_content)
        self.control_splitter = QtWidgets.QSplitter(self.main_content)
        self.control_splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.control_splitter.setObjectName('control_splitter')
        self.main_content_layout.addWidget(self.control_splitter)
        preview_visible = self.settings.value('user interface/preview panel')
        live_visible = self.settings.value('user interface/live panel')
        panel_locked = self.settings.value('user interface/lock panel')
        # Create menu
        self.menu_bar = QtWidgets.QMenuBar(main_window)
        self.menu_bar.setObjectName('menu_bar')
        self.file_menu = QtWidgets.QMenu(self.menu_bar)
        self.file_menu.setObjectName('fileMenu')
        self.recent_files_menu = QtWidgets.QMenu(self.file_menu)
        self.recent_files_menu.setObjectName('recentFilesMenu')
        self.file_import_menu = QtWidgets.QMenu(self.file_menu)
        if not is_macosx():
            self.file_import_menu.setIcon(UiIcons().download)
        self.file_import_menu.setObjectName('file_import_menu')
        self.file_export_menu = QtWidgets.QMenu(self.file_menu)
        if not is_macosx():
            self.file_export_menu.setIcon(UiIcons().upload)
        self.file_export_menu.setObjectName('file_export_menu')
        # View Menu
        self.view_menu = QtWidgets.QMenu(self.menu_bar)
        self.view_menu.setObjectName('viewMenu')
        self.view_mode_menu = QtWidgets.QMenu(self.view_menu)
        self.view_mode_menu.setObjectName('viewModeMenu')
        # Tools Menu
        self.tools_menu = QtWidgets.QMenu(self.menu_bar)
        self.tools_menu.setObjectName('tools_menu')
        # Settings Menu
        self.settings_menu = QtWidgets.QMenu(self.menu_bar)
        self.settings_menu.setObjectName('settingsMenu')
        self.settings_language_menu = QtWidgets.QMenu(self.settings_menu)
        self.settings_language_menu.setObjectName('settingsLanguageMenu')
        # Help Menu
        self.help_menu = QtWidgets.QMenu(self.menu_bar)
        self.help_menu.setObjectName('helpMenu')
        main_window.setMenuBar(self.menu_bar)
        self.status_bar = QtWidgets.QStatusBar(main_window)
        self.status_bar.setObjectName('status_bar')
        main_window.setStatusBar(self.status_bar)
        self.load_progress_bar = QtWidgets.QProgressBar(self.status_bar)
        self.load_progress_bar.setObjectName('load_progress_bar')
        self.status_bar.addPermanentWidget(self.load_progress_bar)
        self.load_progress_bar.hide()
        self.load_progress_bar.setValue(0)
        self.load_progress_bar.setStyleSheet(PROGRESSBAR_STYLE)
        self.default_theme_label = QtWidgets.QLabel(self.status_bar)
        self.default_theme_label.setObjectName('default_theme_label')
        self.status_bar.addPermanentWidget(self.default_theme_label)
        if is_ui_theme(UiThemes.Noir):
            # Persistent output-state segment: what the projector is showing right
            # now, readable from anywhere in the app. Driven by the live
            # controller through the 'live_output_state_changed' registry event.
            self.output_state_label = QtWidgets.QLabel(self.status_bar)
            self.output_state_label.setObjectName('output_state_label')
            self.output_state_label.setText(translate('OpenLP.MainWindow', 'ON AIR'))
            self.output_state_label.setProperty('outputState', 'onair')
            self.status_bar.addPermanentWidget(self.output_state_label)
        # Create the MediaManager
        self.media_manager_dock = OpenLPDockWidget(main_window, 'media_manager_dock',
                                                   UiIcons().box)
        self.media_manager_dock.setStyleSheet(get_library_stylesheet())
        # Create the media toolbox. The Noir theme replaces the stacked QToolBox
        # tabs with an icon-rail sidebar that exposes the same API.
        if is_ui_theme(UiThemes.Noir):
            self.media_tool_box = LibrarySidebar(self.media_manager_dock)
        else:
            self.media_tool_box = QtWidgets.QToolBox(self.media_manager_dock)
        self.media_tool_box.setObjectName('media_tool_box')
        self.media_manager_dock.setWidget(self.media_tool_box)
        main_window.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.media_manager_dock)
        # Create the service manager
        self.service_manager_dock = OpenLPDockWidget(main_window, 'service_manager_dock',
                                                     UiIcons().live)
        self.service_manager_contents = ServiceManager(self.service_manager_dock)
        self.service_manager_dock.setWidget(self.service_manager_contents)
        main_window.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.service_manager_dock)
        # Create the theme manager
        self.theme_manager_dock = OpenLPDockWidget(main_window, 'theme_manager_dock',
                                                   UiIcons().theme)
        self.theme_manager_contents = ThemeManager(self.theme_manager_dock)
        self.theme_manager_contents.setObjectName('theme_manager_contents')
        self.theme_manager_dock.setWidget(self.theme_manager_contents)
        main_window.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.theme_manager_dock)
        # Create the projector manager
        self.projector_manager_dock = OpenLPDockWidget(parent=main_window,
                                                       name='projector_manager_dock',
                                                       icon=UiIcons().projector)
        self.projector_manager_contents = ProjectorManager(self.projector_manager_dock)
        self.projector_manager_contents.setObjectName('projector_manager_contents')
        self.projector_manager_dock.setWidget(self.projector_manager_contents)
        self.projector_manager_dock.setVisible(False)
        main_window.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.projector_manager_dock)
        # Create the log viewer
        self.log_viewer_dock = OpenLPDockWidget(parent=main_window,
                                                name='log_viewer_dock',
                                                icon=UiIcons().text)
        self.log_viewer_contents = LogViewerPanel(self.log_viewer_dock)
        self.log_viewer_contents.setObjectName('log_viewer_contents')
        self.log_viewer_dock.setWidget(self.log_viewer_contents)
        self.log_viewer_dock.setVisible(False)
        main_window.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.log_viewer_dock)
        # Create the menu items
        action_list = ActionList.get_instance()
        action_list.add_category(UiStrings().File, CategoryOrder.standard_menu)
        self.file_new_item = create_action(main_window, 'fileNewItem', icon=UiIcons().new,
                                           can_shortcuts=True, category=UiStrings().File,
                                           triggers=self.service_manager_contents.on_new_service_clicked)
        self.file_open_item = create_action(main_window, 'fileOpenItem', icon=UiIcons().open,
                                            can_shortcuts=True, category=UiStrings().File,
                                            triggers=self.service_manager_contents.on_load_service_clicked)
        self.file_save_item = create_action(main_window, 'fileSaveItem', icon=UiIcons().save,
                                            can_shortcuts=True, category=UiStrings().File,
                                            triggers=self.service_manager_contents.decide_save_method)
        self.file_save_as_item = create_action(main_window, 'fileSaveAsItem', can_shortcuts=True,
                                               category=UiStrings().File,
                                               triggers=self.service_manager_contents.save_file_as)
        self.print_service_order_item = create_action(main_window, 'printServiceItem', can_shortcuts=True,
                                                      category=UiStrings().File,
                                                      triggers=lambda x: PrintServiceForm().exec())
        self.file_exit_item = create_action(main_window, 'fileExitItem', icon=UiIcons().exit,
                                            can_shortcuts=True,
                                            category=UiStrings().File, triggers=main_window.close)
        # Give QT Extra Hint that this is the Exit Menu Item
        self.file_exit_item.setMenuRole(QtGui.QAction.MenuRole.QuitRole)
        action_list.add_category(UiStrings().Import, CategoryOrder.standard_menu)
        self.import_theme_item = create_action(main_window, 'importThemeItem', category=UiStrings().Import,
                                               can_shortcuts=True)
        self.import_language_item = create_action(main_window, 'importLanguageItem')
        action_list.add_category(UiStrings().Export, CategoryOrder.standard_menu)
        self.export_theme_item = create_action(main_window, 'exportThemeItem', category=UiStrings().Export,
                                               can_shortcuts=True)
        self.export_language_item = create_action(main_window, 'exportLanguageItem')
        action_list.add_category(UiStrings().View, CategoryOrder.standard_menu)
        # Projector items
        self.import_projector_item = create_action(main_window, 'importProjectorItem', category=UiStrings().Import,
                                                   can_shortcuts=False)
        action_list.add_category(UiStrings().Import, CategoryOrder.standard_menu)
        self.view_projector_manager_item = create_action(main_window, 'viewProjectorManagerItem',
                                                         icon=UiIcons().projector,
                                                         checked=self.projector_manager_dock.isVisible(),
                                                         can_shortcuts=True,
                                                         category=UiStrings().View,
                                                         triggers=self.toggle_projector_manager)
        self.view_media_manager_item = create_action(main_window, 'viewMediaManagerItem',
                                                     icon=UiIcons().box,
                                                     checked=self.media_manager_dock.isVisible(),
                                                     can_shortcuts=True,
                                                     category=UiStrings().View, triggers=self.toggle_media_manager)
        self.view_theme_manager_item = create_action(main_window, 'viewThemeManagerItem', can_shortcuts=True,
                                                     icon=UiIcons().theme,
                                                     checked=self.theme_manager_dock.isVisible(),
                                                     category=UiStrings().View, triggers=self.toggle_theme_manager)
        self.view_service_manager_item = create_action(main_window, 'viewServiceManagerItem', can_shortcuts=True,
                                                       icon=UiIcons().live,
                                                       checked=self.service_manager_dock.isVisible(),
                                                       category=UiStrings().View, triggers=self.toggle_service_manager)
        self.view_log_viewer_item = create_action(main_window, 'viewLogViewerItem', can_shortcuts=True,
                                                  icon=UiIcons().text,
                                                  checked=self.log_viewer_dock.isVisible(),
                                                  category=UiStrings().View, triggers=self.toggle_log_viewer)
        self.view_preview_panel = create_action(main_window, 'viewPreviewPanel', can_shortcuts=True,
                                                checked=preview_visible, category=UiStrings().View,
                                                triggers=self.set_preview_panel_visibility)
        self.view_live_panel = create_action(main_window, 'viewLivePanel', can_shortcuts=True, checked=live_visible,
                                             category=UiStrings().View, triggers=self.set_live_panel_visibility)
        self.lock_panel = create_action(main_window, 'lockPanel', can_shortcuts=True, checked=panel_locked,
                                        category=UiStrings().View, triggers=self.set_lock_panel)
        action_list.add_category(UiStrings().ViewMode, CategoryOrder.standard_menu)
        self.mode_default_item = create_action(
            main_window, 'modeDefaultItem', checked=False, category=UiStrings().ViewMode, can_shortcuts=True)
        self.mode_setup_item = create_action(main_window, 'modeSetupItem', checked=False, category=UiStrings().ViewMode,
                                             can_shortcuts=True)
        self.mode_live_item = create_action(main_window, 'modeLiveItem', checked=True, category=UiStrings().ViewMode,
                                            can_shortcuts=True)
        self.mode_group = QtGui.QActionGroup(main_window)
        self.mode_group.addAction(self.mode_default_item)
        self.mode_group.addAction(self.mode_setup_item)
        self.mode_group.addAction(self.mode_live_item)
        self.mode_default_item.setChecked(True)
        action_list.add_category(UiStrings().Tools, CategoryOrder.standard_menu)
        self.tools_add_tool_item = create_action(main_window,
                                                 'toolsAddToolItem', icon=UiIcons().add,
                                                 category=UiStrings().Tools, can_shortcuts=True)
        self.tools_open_data_folder = create_action(main_window,
                                                    'toolsOpenDataFolder', icon=UiIcons().open,
                                                    category=UiStrings().Tools, can_shortcuts=True)
        self.tools_first_time_wizard = create_action(main_window,
                                                     'toolsFirstTimeWizard', icon=UiIcons().undo,
                                                     category=UiStrings().Tools, can_shortcuts=True)
        self.update_theme_images = create_action(main_window,
                                                 'updateThemeImages', category=UiStrings().Tools, can_shortcuts=True)
        action_list.add_category(UiStrings().Settings, CategoryOrder.standard_menu)
        self.settings_plugin_list_item = create_action(main_window,
                                                       'settingsPluginListItem',
                                                       icon=UiIcons().plugin_list,
                                                       can_shortcuts=True,
                                                       category=UiStrings().Settings,
                                                       triggers=self.on_plugin_item_clicked)
        # i18n Language Items
        self.auto_language_item = create_action(main_window, 'autoLanguageItem', checked=LanguageManager.auto_language)
        self.language_group = QtGui.QActionGroup(main_window)
        self.language_group.setExclusive(True)
        self.language_group.setObjectName('languageGroup')
        add_actions(self.language_group, [self.auto_language_item])
        qm_list = LanguageManager.get_qm_list()
        saved_language = LanguageManager.get_language()
        for key in sorted(qm_list.keys()):
            language_item = create_action(main_window, key, checked=qm_list[key] == saved_language)
            add_actions(self.language_group, [language_item])
        self.settings_shortcuts_item = create_action(main_window, 'settingsShortcutsItem',
                                                     icon=UiIcons().shortcuts,
                                                     category=UiStrings().Settings, can_shortcuts=True)
        # Formatting Tags were also known as display tags.
        self.formatting_tag_item = create_action(main_window, 'displayTagItem',
                                                 icon=UiIcons().edit, category=UiStrings().Settings,
                                                 can_shortcuts=True)
        self.settings_configure_item = create_action(main_window, 'settingsConfigureItem',
                                                     icon=UiIcons().settings, can_shortcuts=True,
                                                     category=UiStrings().Settings)
        # Give Qt Extra Hint that this is the Preferences Menu Item
        self.settings_configure_item.setMenuRole(QtGui.QAction.MenuRole.PreferencesRole)
        self.settings_import_item = create_action(main_window, 'settingsImportItem',
                                                  category=UiStrings().Import, can_shortcuts=True)
        self.settings_export_item = create_action(main_window, 'settingsExportItem',
                                                  category=UiStrings().Export, can_shortcuts=True)
        action_list.add_category(UiStrings().Help, CategoryOrder.standard_menu)
        self.about_item = create_action(main_window, 'aboutItem', icon=UiIcons().info,
                                        can_shortcuts=True, category=UiStrings().Help,
                                        triggers=self.on_about_item_clicked)
        # Give Qt Extra Hint that this is an About Menu Item
        self.about_item.setMenuRole(QtGui.QAction.MenuRole.AboutRole)
        if is_win():
            self.local_help_file = AppLocation.get_directory(AppLocation.AppDir) / 'OpenLP.chm'
        elif is_macosx():
            self.local_help_file = AppLocation.get_directory(AppLocation.AppDir) / '..' / 'Resources' / 'OpenLP.help'
        self.user_manual_item = create_action(main_window, 'userManualItem', icon=UiIcons().manual,
                                              can_shortcuts=True, category=UiStrings().Help,
                                              triggers=self.on_help_clicked)
        self.web_site_item = create_action(main_window, 'webSiteItem', can_shortcuts=True, category=UiStrings().Help)
        # Shortcuts not connected to buttons or menu entries.
        self.search_shortcut_action = create_action(main_window,
                                                    'searchShortcut', can_shortcuts=True,
                                                    category=translate('OpenLP.MainWindow', 'General'),
                                                    triggers=self.on_search_shortcut_triggered)
        '''
        Leave until the import projector options are finished
        add_actions(self.file_import_menu, (self.settings_import_item, self.import_theme_item,
                    self.import_projector_item, self.import_language_item, None))
        '''
        add_actions(self.file_import_menu, (self.settings_import_item, self.import_theme_item,
                    self.import_language_item, None))
        add_actions(self.file_export_menu, (self.settings_export_item, self.export_theme_item,
                    self.export_language_item, None))
        add_actions(self.file_menu, (self.file_new_item, self.file_open_item,
                    self.file_save_item, self.file_save_as_item, self.recent_files_menu.menuAction(), None,
                    self.file_import_menu.menuAction(), self.file_export_menu.menuAction(), None,
                    self.print_service_order_item, self.file_exit_item))
        add_actions(self.view_mode_menu, (self.mode_default_item, self.mode_setup_item, self.mode_live_item))
        add_actions(self.view_menu, (self.view_mode_menu.menuAction(), None, self.view_media_manager_item,
                    self.view_projector_manager_item, self.view_service_manager_item, self.view_theme_manager_item,
                    self.view_log_viewer_item, None, self.view_preview_panel, self.view_live_panel, None,
                    self.lock_panel))
        # i18n add Language Actions
        add_actions(self.settings_language_menu, (self.auto_language_item, None))
        add_actions(self.settings_language_menu, self.language_group.actions())
        # Qt on OS X looks for keywords in the menu items title to determine which menu items get added to the main
        # menu. If we are running on Mac OS X the menu items whose title contains those keywords but don't belong in the
        # main menu need to be marked as such with QAction.MenuRole.NoRole.
        if is_macosx():
            self.settings_shortcuts_item.setMenuRole(QtGui.QAction.MenuRole.NoRole)
            self.formatting_tag_item.setMenuRole(QtGui.QAction.MenuRole.NoRole)
        add_actions(self.settings_menu, (self.settings_plugin_list_item, self.settings_language_menu.menuAction(),
                    None, self.formatting_tag_item, self.settings_shortcuts_item, self.settings_configure_item))
        add_actions(self.tools_menu, (self.tools_add_tool_item, None))
        add_actions(self.tools_menu, (self.tools_open_data_folder, None))
        add_actions(self.tools_menu, (self.tools_first_time_wizard, None))
        add_actions(self.tools_menu, [self.update_theme_images])
        add_actions(self.help_menu, (self.user_manual_item, None, self.web_site_item, self.about_item))
        add_actions(self.menu_bar, (self.file_menu.menuAction(), self.view_menu.menuAction(),
                    self.tools_menu.menuAction(), self.settings_menu.menuAction(), self.help_menu.menuAction()))
        add_actions(self, [self.search_shortcut_action])
        # Initialise the translation
        self.retranslate_ui(main_window)
        self.media_tool_box.setCurrentIndex(0)
        # Connect up some signals and slots
        self.file_menu.aboutToShow.connect(self.update_recent_files_menu)
        # Hide the entry, as it does not have any functionality yet.
        self.tools_add_tool_item.setVisible(False)
        self.import_language_item.setVisible(False)
        self.export_language_item.setVisible(False)
        self.set_lock_panel(panel_locked)
        self.settings_imported = False

    def retranslate_ui(self, main_window):
        """
        Set up the translation system
        """
        main_window.setWindowTitle(UiStrings().OpenLP)
        self.file_menu.setTitle(translate('OpenLP.MainWindow', '&File'))
        self.file_import_menu.setTitle(translate('OpenLP.MainWindow', '&Import'))
        self.file_export_menu.setTitle(translate('OpenLP.MainWindow', '&Export'))
        self.recent_files_menu.setTitle(translate('OpenLP.MainWindow', '&Recent Services'))
        self.view_menu.setTitle(translate('OpenLP.MainWindow', '&View'))
        self.view_mode_menu.setTitle(translate('OpenLP.MainWindow', '&Layout Presets'))
        self.tools_menu.setTitle(translate('OpenLP.MainWindow', '&Tools'))
        self.settings_menu.setTitle(translate('OpenLP.MainWindow', '&Settings'))
        self.settings_language_menu.setTitle(translate('OpenLP.MainWindow', '&Language'))
        self.help_menu.setTitle(translate('OpenLP.MainWindow', '&Help'))
        self.media_manager_dock.setWindowTitle(translate('OpenLP.MainWindow', 'Library'))
        self.service_manager_dock.setWindowTitle(translate('OpenLP.MainWindow', 'Service'))
        self.theme_manager_dock.setWindowTitle(translate('OpenLP.MainWindow', 'Themes'))
        self.projector_manager_dock.setWindowTitle(translate('OpenLP.MainWindow', 'Projector Controller'))
        self.log_viewer_dock.setWindowTitle(translate('OpenLP.MainWindow', 'Logs'))
        self.file_new_item.setText(translate('OpenLP.MainWindow', '&New Service'))
        self.file_new_item.setToolTip(UiStrings().NewService)
        self.file_new_item.setStatusTip(UiStrings().CreateService)
        self.file_open_item.setText(translate('OpenLP.MainWindow', '&Open Service'))
        self.file_open_item.setToolTip(UiStrings().OpenService)
        self.file_open_item.setStatusTip(translate('OpenLP.MainWindow', 'Open an existing service.'))
        self.file_save_item.setText(translate('OpenLP.MainWindow', '&Save Service'))
        self.file_save_item.setToolTip(UiStrings().SaveService)
        self.file_save_item.setStatusTip(translate('OpenLP.MainWindow', 'Save the current service to disk.'))
        self.file_save_as_item.setText(translate('OpenLP.MainWindow', 'Save Service &As...'))
        self.file_save_as_item.setToolTip(translate('OpenLP.MainWindow', 'Save Service As'))
        self.file_save_as_item.setStatusTip(translate('OpenLP.MainWindow',
                                            'Save the current service under a new name.'))
        self.print_service_order_item.setText(UiStrings().PrintService)
        self.print_service_order_item.setStatusTip(translate('OpenLP.MainWindow', 'Print the current service.'))
        self.file_exit_item.setText(translate('OpenLP.MainWindow', 'E&xit'))
        self.file_exit_item.setStatusTip(translate('OpenLP.MainWindow', 'Close OpenLP - Shut down the program.'))
        self.import_theme_item.setText(translate('OpenLP.MainWindow', '&Theme'))
        self.import_language_item.setText(translate('OpenLP.MainWindow', '&Language'))
        self.export_theme_item.setText(translate('OpenLP.MainWindow', '&Theme'))
        self.export_language_item.setText(translate('OpenLP.MainWindow', '&Language'))
        self.settings_shortcuts_item.setText(translate('OpenLP.MainWindow', 'Configure &Shortcuts...'))
        self.formatting_tag_item.setText(translate('OpenLP.MainWindow', 'Configure &Formatting Tags...'))
        self.settings_configure_item.setText(translate('OpenLP.MainWindow', '&Configure OpenLP...'))
        self.settings_export_item.setStatusTip(
            translate('OpenLP.MainWindow', 'Export settings to a *.config file.'))
        self.settings_export_item.setText(translate('OpenLP.MainWindow', 'Settings'))
        self.settings_import_item.setStatusTip(
            translate('OpenLP.MainWindow', 'Import settings from a *.config file previously exported from '
                                           'this or another machine.'))
        self.settings_import_item.setText(translate('OpenLP.MainWindow', 'Settings'))
        self.view_projector_manager_item.setText(translate('OpenLP.MainWindow', '&Projector Controller'))
        self.view_projector_manager_item.setToolTip(translate('OpenLP.MainWindow', 'Hide or show Projectors.'))
        self.view_projector_manager_item.setStatusTip(translate('OpenLP.MainWindow',
                                                                'Toggle visibility of the Projectors.'))
        self.view_media_manager_item.setText(translate('OpenLP.MainWindow', 'L&ibrary'))
        self.view_media_manager_item.setToolTip(translate('OpenLP.MainWindow', 'Hide or show the Library.'))
        self.view_media_manager_item.setStatusTip(translate('OpenLP.MainWindow',
                                                  'Toggle the visibility of the Library.'))
        self.view_theme_manager_item.setText(translate('OpenLP.MainWindow', '&Themes'))
        self.view_theme_manager_item.setToolTip(translate('OpenLP.MainWindow', 'Hide or show themes'))
        self.view_theme_manager_item.setStatusTip(translate('OpenLP.MainWindow',
                                                  'Toggle visibility of the Themes.'))
        self.view_service_manager_item.setText(translate('OpenLP.MainWindow', '&Service'))
        self.view_service_manager_item.setToolTip(translate('OpenLP.MainWindow', 'Hide or show Service.'))
        self.view_service_manager_item.setStatusTip(translate('OpenLP.MainWindow',
                                                    'Toggle visibility of the Service.'))
        self.view_log_viewer_item.setText(translate('OpenLP.MainWindow', '&Logs'))
        self.view_log_viewer_item.setToolTip(translate('OpenLP.MainWindow', 'Hide or show the Logs panel.'))
        self.view_log_viewer_item.setStatusTip(translate('OpenLP.MainWindow',
                                               'Toggle visibility of the Logs panel.'))
        self.view_preview_panel.setText(translate('OpenLP.MainWindow', '&Preview'))
        self.view_preview_panel.setToolTip(translate('OpenLP.MainWindow', 'Hide or show Preview.'))
        self.view_preview_panel.setStatusTip(
            translate('OpenLP.MainWindow', 'Toggle visibility of the Preview.'))
        self.view_live_panel.setText(translate('OpenLP.MainWindow', 'Li&ve'))
        self.view_live_panel.setToolTip(translate('OpenLP.MainWindow', 'Hide or show Live'))
        self.lock_panel.setText(translate('OpenLP.MainWindow', 'L&ock visibility of the panels'))
        self.lock_panel.setStatusTip(translate('OpenLP.MainWindow', 'Lock visibility of the panels.'))
        self.view_live_panel.setStatusTip(translate('OpenLP.MainWindow', 'Toggle visibility of the Live.'))
        self.settings_plugin_list_item.setText(translate('OpenLP.MainWindow', '&Manage Plugins'))
        self.settings_plugin_list_item.setStatusTip(translate('OpenLP.MainWindow', 'You can enable and disable plugins '
                                                                                   'from here.'))
        self.about_item.setText(translate('OpenLP.MainWindow', '&About'))
        self.about_item.setStatusTip(translate('OpenLP.MainWindow', 'More information about OpenLP.'))
        self.user_manual_item.setText(translate('OpenLP.MainWindow', '&User Manual'))
        self.search_shortcut_action.setText(UiStrings().Search)
        self.search_shortcut_action.setToolTip(
            translate('OpenLP.MainWindow', 'Jump to the search box of the current active plugin.'))
        self.web_site_item.setText(translate('OpenLP.MainWindow', '&Web Site'))
        for item in self.language_group.actions():
            item.setText(item.objectName())
            item.setStatusTip(translate('OpenLP.MainWindow',
                                        'Set the interface language to {name}').format(name=item.objectName()))
        self.auto_language_item.setText(translate('OpenLP.MainWindow', '&Autodetect'))
        self.auto_language_item.setStatusTip(translate('OpenLP.MainWindow', 'Use the system language, if available.'))
        self.tools_add_tool_item.setText(translate('OpenLP.MainWindow', 'Add &Tool...'))
        self.tools_add_tool_item.setStatusTip(translate('OpenLP.MainWindow',
                                                        'Add an application to the list of tools.'))
        self.tools_open_data_folder.setText(translate('OpenLP.MainWindow', 'Open &Data Folder...'))
        self.tools_open_data_folder.setStatusTip(translate('OpenLP.MainWindow',
                                                 'Open the folder where songs, bibles and other data resides.'))
        self.tools_first_time_wizard.setText(translate('OpenLP.MainWindow', 'Re-run First Time Wizard'))
        self.tools_first_time_wizard.setStatusTip(translate('OpenLP.MainWindow',
                                                  'Re-run the First Time Wizard, importing songs, Bibles and themes.'))
        self.update_theme_images.setText(translate('OpenLP.MainWindow', 'Update Theme Images'))
        self.update_theme_images.setStatusTip(translate('OpenLP.MainWindow',
                                                        'Update the preview images for all themes.'))
        self.mode_default_item.setText(translate('OpenLP.MainWindow', '&Show all'))
        self.mode_default_item.setStatusTip(translate('OpenLP.MainWindow', 'Reset the interface back to the '
                                                                           'default layout and show all the panels.'))
        self.mode_setup_item.setText(translate('OpenLP.MainWindow', '&Setup'))
        self.mode_setup_item.setStatusTip(translate('OpenLP.MainWindow', 'Use layout that focuses on setting'
                                                                         ' up the Service.'))
        self.mode_live_item.setText(translate('OpenLP.MainWindow', '&Live'))
        self.mode_live_item.setStatusTip(translate('OpenLP.MainWindow', 'Use layout that focuses on Live.'))


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow, LogMixin, RegistryProperties):
    """
    The main window.
    """
    def __init__(self):
        """
        This constructor sets up the interface, the various managers, and the plugins.
        """
        super(MainWindow, self).__init__()
        Registry().register('main_window', self)
        self.clipboard = QtWidgets.QApplication.clipboard()
        self.recent_files = []
        self.timer_id = 0
        self.new_data_path = None
        self.copy_data = False
        self.settings.set_up_default_values()
        self.about_form = AboutForm(self)
        SettingsForm(self)
        self.formatting_tag_form = FormattingTagForm(self)
        self.shortcut_form = ShortcutListForm(self)
        # Set up the interface
        self.setup_ui(self)
        # Define the media Dock Manager
        self.media_dock_manager = MediaDockManager(self.media_tool_box)
        # Load settings after setup_ui so default UI sizes are overwritten
        # Once settings are loaded update the menu with the recent files.
        self.update_recent_files_menu()
        self.plugin_form = PluginForm(self)
        # Set up signals and slots
        self.media_manager_dock.visibilityChanged.connect(self.toggle_media_manager)
        self.service_manager_dock.visibilityChanged.connect(self.toggle_service_manager)
        self.theme_manager_dock.visibilityChanged.connect(self.toggle_theme_manager)
        self.projector_manager_dock.visibilityChanged.connect(self.toggle_projector_manager)
        self.import_theme_item.triggered.connect(self.theme_manager_contents.on_import_theme)
        self.export_theme_item.triggered.connect(self.theme_manager_contents.on_export_theme)
        self.web_site_item.triggered.connect(self.on_help_web_site_clicked)
        self.tools_open_data_folder.triggered.connect(self.on_tools_open_data_folder_clicked)
        self.tools_first_time_wizard.triggered.connect(self.on_first_time_wizard_clicked)
        self.update_theme_images.triggered.connect(self.on_update_theme_images)
        self.formatting_tag_item.triggered.connect(self.on_formatting_tag_item_clicked)
        self.settings_configure_item.triggered.connect(self.on_settings_configure_item_clicked)
        self.settings_shortcuts_item.triggered.connect(self.on_settings_shortcuts_item_clicked)
        self.settings_import_item.triggered.connect(self.on_settings_import_item_clicked)
        self.settings_export_item.triggered.connect(self.on_settings_export_item_clicked)
        # i18n set signals for languages
        self.language_group.triggered.connect(LanguageManager.set_language)
        self.mode_default_item.triggered.connect(self.on_mode_default_item_clicked)
        self.mode_setup_item.triggered.connect(self.on_mode_setup_item_clicked)
        self.mode_live_item.triggered.connect(self.on_mode_live_item_clicked)
        # Media Manager
        self.media_tool_box.currentChanged.connect(self.on_media_tool_box_changed)
        self.application.set_busy_cursor()
        self.should_show_screen_change_message = True
        # Simple message boxes
        Registry().register_function('theme_change_global', self.default_theme_changed)
        Registry().register_function('config_screen_changed', self.screen_changed)
        Registry().register_function('bootstrap_post_set_up', self.bootstrap_post_set_up)
        if is_ui_theme(UiThemes.Noir):
            Registry().register_function('live_output_state_changed', self.on_live_output_state_changed)
        # Reset the cursor
        self.application.set_normal_cursor()
        # Starting up web services
        self.http_server = HttpServer(self)
        self.ws_server = WebSocketServer()
        self.screen_updating_lock = Lock()

    @contextmanager
    def _show_wait_dialog(self, title: str, message: str):
        """
        Show a wait dialog, wait for some tasks to complete, and then close it.
        """
        try:
            # Display a progress dialog with a message
            wait_dialog = QtWidgets.QProgressDialog(message, '', 0, 0, self)
            wait_dialog.setWindowTitle(title)
            for window_flag in [QtCore.Qt.WindowType.WindowContextHelpButtonHint]:
                wait_dialog.setWindowFlag(window_flag, False)
            wait_dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
            wait_dialog.setAutoClose(False)
            wait_dialog.setCancelButton(None)
            wait_dialog.show()
            QtWidgets.QApplication.processEvents()
            yield
        finally:
            # Finally close the message window
            wait_dialog.close()

    def _wait_for_threads(self):
        """
        Wait for the threads
        """
        # Sometimes the threads haven't finished, let's wait for them
        thread_names = list(self.application.worker_threads.keys())
        for thread_name in thread_names:
            self.log_debug('Waiting for thread %s' % thread_name)
            QtWidgets.QApplication.processEvents()
            if thread_name not in self.application.worker_threads.keys():
                continue
            thread = self.application.worker_threads[thread_name]['thread']
            worker = self.application.worker_threads[thread_name]['worker']
            try:
                if worker and hasattr(worker, 'stop'):
                    # If the worker has a stop method, run it
                    worker.stop()
                if thread and thread.isRunning():
                    # If the thread is running, let's wait 5 seconds for it
                    retry = 0
                    while thread.isRunning() and retry < 50:
                        # Make the GUI responsive while we wait
                        QtWidgets.QApplication.processEvents()
                        thread.wait(100)
                        retry += 1
                    if thread.isRunning():
                        # If the thread is still running after 5 seconds, kill it
                        thread.terminate()
            except RuntimeError:
                # Ignore the RuntimeError that is thrown when Qt has already deleted the C++ thread object
                pass

    def bootstrap_post_set_up(self):
        """
        process the bootstrap post setup request
        """
        self.load_settings()
        self.restore_current_media_manager_item()
        Registry().execute('theme_change_global')

    def restore_current_media_manager_item(self):
        """
        Called on start up to restore the last active media plugin.
        """
        self.log_info('Load data from Settings')
        if self.settings.value('advanced/save current plugin'):
            saved_plugin_id = self.settings.value('advanced/current media plugin')
            if saved_plugin_id != -1:
                self.media_tool_box.setCurrentIndex(saved_plugin_id)

    def on_search_shortcut_triggered(self):
        """
        Called when the search shortcut has been pressed.
        """
        # Make sure the media_dock is visible.
        if not self.media_manager_dock.isVisible():
            self.media_manager_dock.setVisible(True)
        widget = self.media_tool_box.currentWidget()
        if widget:
            widget.on_focus()

    def on_media_tool_box_changed(self, index: int):
        """
        Focus a widget when the media toolbox changes.
        """
        widget = self.media_tool_box.widget(index)
        if widget:
            widget.on_focus()

    def on_new_version(self, version: str):
        """
        Notifies the user that a newer version of OpenLP is available. Triggered by delay thread and cannot display
        popup.

        :param version: The Version to be displayed.
        """
        version_text = translate('OpenLP.MainWindow', 'Version {new} of OpenLP is now available for download (you are '
                                 'currently running version {current}). \n\nYou can download the latest version from '
                                 'https://openlp.org/.').format(new=version, current=get_version()[u'full'])
        QtWidgets.QMessageBox.question(self, translate('OpenLP.MainWindow', 'OpenLP Version Updated'), version_text)

    def on_new_remote_version(self, version: str):
        """
        Notifies the user that a newer version of the web remote is available. Triggered by delay thread and cannot
        display popup.

        :param version: The Version to be displayed.
        """
        Registry().get('settings').setValue('api/last version test', date.today().strftime('%Y-%m-%d'))
        Registry().get('settings_form').api_tab.master_version = version
        version_text = translate('OpenLP.MainWindow', 'Version {version} of the web remote is now available for '
                                 'download.\nTo download this version, go to the Remote settings and click the Upgrade '
                                 'button.').format(version=version)
        self.information_message(translate('OpenLP.MainWindow', 'New Web Remote Version Available'), version_text)

    def show(self):
        """
        Show the main form, as well as the display form
        """
        QtWidgets.QWidget.show(self)
        self.activateWindow()
        # We have -disable-web-security added by our code.
        # If a file is passed in we will have that as well so count of 2
        # If not we need to see if we want to use the previous file.so count of 1
        self.log_info(self.application.args)
        if self.application.args and len(self.application.args) > 1:
            self.open_cmd_line_files(self.application.args)
        elif self.settings.value('core/auto open'):
            self.service_manager_contents.load_last_file()
        # This will store currently used layout preset so it remains enabled on next startup.
        # If any panel is enabled/disabled after preset is set, this setting is not saved.
        view_mode = self.settings.value('core/view mode')
        # If we are using a default mode set accordingly
        if self.settings.value('user interface/is preset layout'):
            if view_mode == 'default':
                self.set_view_mode(True, True, True, True, True, True)
                self.mode_default_item.setChecked(True)
            elif view_mode == 'setup':
                self.set_view_mode(True, True, False, True, False, True)
                self.mode_setup_item.setChecked(True)
            elif view_mode == 'live':
                self.set_view_mode(False, True, False, False, True, True)
                self.mode_live_item.setChecked(True)
        else:
            self.set_view_mode(
                self.settings.value('user interface/show library'),
                self.settings.value('user interface/show service'),
                self.settings.value('user interface/show themes'),
                self.settings.value('user interface/preview panel'),
                self.settings.value('user interface/live panel'),
                self.settings.value('user interface/show projectors')
            )

    def first_time(self):
        """
        Import themes if first time
        """
        self.application.process_events()
        for plugin in State().list_plugins():
            if hasattr(plugin, 'first_time'):
                self.application.process_events()
                plugin.first_time()
        self.application.process_events()
        # Load the themes from files
        self.theme_manager_contents.load_first_time_themes()
        # Update the theme widget
        self.theme_manager_contents.load_themes()
        temp_path = Path(gettempdir(), 'openlp')
        shutil.rmtree(temp_path, True)

    def on_first_time_wizard_clicked(self):
        """
        Re-run the first time wizard.  Prompts the user for run confirmation.If wizard is run, songs, bibles and
        themes are imported.  The default theme is changed (if necessary).  The plugins in pluginmanager are
        set active/in-active to match the selection in the wizard.
        """
        answer = QtWidgets.QMessageBox.warning(self,
                                               translate('OpenLP.MainWindow', 'Re-run First Time Wizard?'),
                                               translate('OpenLP.MainWindow',
                                                         'Are you sure you want to re-run the First '
                                                         'Time Wizard?\n\nRe-running this wizard may make changes to '
                                                         'your current OpenLP configuration and possibly add songs to '
                                                         'your existing songs list and change your default theme.'),
                                               QtWidgets.QMessageBox.StandardButton(
                                                   QtWidgets.QMessageBox.StandardButton.Yes |
                                                   QtWidgets.QMessageBox.StandardButton.No),
                                               QtWidgets.QMessageBox.StandardButton.No)
        if answer == QtWidgets.QMessageBox.StandardButton.No:
            return
        first_run_wizard = FirstTimeForm(self)
        first_run_wizard.initialize(ScreenList())
        if first_run_wizard.exec() == QtWidgets.QDialog.DialogCode.Rejected:
            return
        self.application.set_busy_cursor()
        self.first_time()
        # Check if Projectors panel should be visible or not after wizard.
        if self.settings.value('projector/show after wizard'):
            self.projector_manager_dock.setVisible(True)
        else:
            self.projector_manager_dock.setVisible(False)
        for plugin in State().list_plugins():
            self.active_plugin = plugin
            old_status = self.active_plugin.status
            self.active_plugin.set_status()
            if old_status != self.active_plugin.status:
                if self.active_plugin.status == PluginStatus.Active:
                    self.active_plugin.toggle_status(PluginStatus.Active)
                    self.active_plugin.app_startup()
                else:
                    self.active_plugin.toggle_status(PluginStatus.Inactive)
        # Set global theme and
        Registry().execute('theme_change_global')
        # Check if any Bibles downloaded.  If there are, they will be processed.
        Registry().execute('bibles_load_list')
        self.application.set_normal_cursor()

    def is_display_blank(self):
        """
        Check and display message if screen blank on setup.
        """
        if self.settings.value('core/screen blank'):
            if self.settings.value('core/blank warning'):
                QtWidgets.QMessageBox.question(self, translate('OpenLP.MainWindow', 'OpenLP Main Display Blanked'),
                                               translate('OpenLP.MainWindow', 'The Main Display has been blanked out'))

    def error_message(self, title: str, message: str):
        """
        Display an error message

        :param title: The title of the warning box.
        :param message: The message to be displayed.
        """
        if hasattr(self.application, 'splash'):
            self.application.splash.close()
        QtWidgets.QMessageBox.critical(self, title, message)

    def warning_message(self, title: str, message: str):
        """
        Display a warning message

        :param title:  The title of the warning box.
        :param message: The message to be displayed.
        """
        if hasattr(self.application, 'splash'):
            self.application.splash.close()
        QtWidgets.QMessageBox.warning(self, title, message)

    def information_message(self, title: str, message: str):
        """
        Display an informational message

        :param title: The title of the warning box.
        :param message: The message to be displayed.
        """
        if hasattr(self.application, 'splash'):
            self.application.splash.close()
        QtWidgets.QMessageBox.information(self, title, message)

    @staticmethod
    def on_help_web_site_clicked():
        """
        Load the OpenLP website
        """
        webbrowser.open_new('https://openlp.org/')

    def on_help_clicked(self):
        """
        If is_macosx or is_win, open the local OpenLP help file.
        Use the Online manual in other cases. (Linux)
        """
        webbrowser.open_new('https://manual.openlp.org/')

    def on_about_item_clicked(self):
        """
        Show the About form
        """
        self.about_form.exec()

    def on_plugin_item_clicked(self):
        """
        Show the Plugin form
        """
        self.plugin_form.load()
        self.plugin_form.exec()

    @staticmethod
    def on_tools_open_data_folder_clicked():
        """
        Open data folder
        """
        path = str(AppLocation.get_data_path())
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))

    def on_update_theme_images(self):
        """
        Updates the new theme preview images.
        """
        self.theme_manager_contents.update_preview_images()

    def on_formatting_tag_item_clicked(self):
        """
        Show the Settings dialog
        """
        self.formatting_tag_form.exec()

    def on_settings_configure_item_clicked(self):
        """
        Show the Settings dialog
        """
        self.settings_form.exec()

    def on_settings_shortcuts_item_clicked(self):
        """
        Show the shortcuts dialog
        """
        if self.shortcut_form.exec():
            self.shortcut_form.save()

    def on_settings_import_item_clicked(self):
        """
        Import settings from an export INI file
        """
        answer = QtWidgets.QMessageBox.critical(self, translate('OpenLP.MainWindow', 'Import settings?'),
                                                translate('OpenLP.MainWindow', 'Are you sure you want to import '
                                                                               'settings?\n\n Importing settings will '
                                                                               'make permanent changes to your current '
                                                                               'OpenLP configuration.\n\n Importing '
                                                                               'incorrect settings may cause erratic '
                                                                               'behaviour or OpenLP to terminate '
                                                                               'abnormally.'),
                                                QtWidgets.QMessageBox.StandardButton(
                                                    QtWidgets.QMessageBox.StandardButton.Yes |
                                                    QtWidgets.QMessageBox.StandardButton.No),
                                                QtWidgets.QMessageBox.StandardButton.No)
        if answer == QtWidgets.QMessageBox.StandardButton.No:
            return
        import_file_path, filter_used = FileDialog.getOpenFileName(
            self,
            translate('OpenLP.MainWindow', 'Import settings'),
            None,
            translate('OpenLP.MainWindow', 'OpenLP Settings (*.conf)'))
        if import_file_path is None:
            return
        setting_sections = []
        # Add main sections.
        setting_sections.extend(['core'])
        setting_sections.extend(['advanced'])
        setting_sections.extend(['user interface'])
        setting_sections.extend(['shortcuts'])
        setting_sections.extend(['servicemanager'])
        setting_sections.extend(['themes'])
        setting_sections.extend(['projector'])
        setting_sections.extend(['players'])
        setting_sections.extend(['displayTags'])
        setting_sections.extend(['SettingsImport'])
        setting_sections.extend(['crashreport'])
        # Add plugin sections.
        setting_sections.extend([plugin.name for plugin in State().list_plugins()])
        # Copy the settings file to the tmp dir, because we do not want to change the original one.
        temp_dir_path = Path(gettempdir(), 'openlp')
        create_paths(temp_dir_path)
        temp_config_path = temp_dir_path / import_file_path.name
        shutil.copyfile(import_file_path, temp_config_path)
        import_settings = Settings(str(temp_config_path), QtCore.QSettings.Format.IniFormat)

        self.log_info('hook upgrade_plugin_settings')
        self.plugin_manager.hook_upgrade_plugin_settings(import_settings)
        # If settings are from the future, we can't import.
        if import_settings.from_future():
            QtWidgets.QMessageBox.critical(self, translate('OpenLP.MainWindow', 'Import settings'),
                                           translate('OpenLP.MainWindow', 'OpenLP cannot import settings '
                                                                          'from a newer version of OpenLP.\n\n'
                                                                          'Processing has terminated and '
                                                                          'no changes have been made.'),
                                           QtWidgets.QMessageBox.StandardButton(
                                               QtWidgets.QMessageBox.StandardButton.Ok))
            return
        # Upgrade settings to prepare the import.
        if import_settings.version_mismatched():
            import_settings.upgrade_settings()
        # Lets do a basic sanity check. If it contains this string we can assume it was created by OpenLP and so we'll
        # load what we can from it, and just silently ignore anything we don't recognise.
        if import_settings.value('SettingsImport/type') != 'OpenLP_settings_export':
            QtWidgets.QMessageBox.critical(self, translate('OpenLP.MainWindow', 'Import settings'),
                                           translate('OpenLP.MainWindow', 'The file you have selected does not appear '
                                                                          'to be a valid OpenLP settings file.\n\n'
                                                                          'Processing has terminated and '
                                                                          'no changes have been made.'),
                                           QtWidgets.QMessageBox.StandardButton(
                                               QtWidgets.QMessageBox.StandardButton.Ok))
            return
        import_keys = import_settings.allKeys()
        for section_key in import_keys:
            # We need to handle the really bad files.
            try:
                section, key = section_key.split('/')
            except ValueError:
                section = 'unknown'
                key = ''
            # Switch General back to lowercase.
            if section == 'General' or section == '%General':
                section = 'general'
                section_key = section + "/" + key
            # Make sure it's a valid section for us.
            if section not in setting_sections:
                continue
        # We have a good file, import it.
        for section_key in import_keys:
            if 'eneral' in section_key:
                section_key = section_key.lower()
            try:
                value = import_settings.value(section_key)
            except KeyError:
                value = None
                self.log_warning('The key "{key}" does not exist (anymore), so it will be skipped.'.
                                 format(key=section_key))
            if value is not None:
                self.settings.setValue('{key}'.format(key=section_key), value)
        now = datetime.now()
        self.settings.setValue('SettingsImport/file_imported', import_file_path)
        self.settings.setValue('SettingsImport/file_date_imported', now.strftime("%Y-%m-%d %H:%M"))
        self.settings.sync()
        # We must do an immediate restart or current configuration will overwrite what was just imported when
        # application terminates normally.   We need to exit without saving configuration.
        QtWidgets.QMessageBox.information(self, translate('OpenLP.MainWindow', 'Import settings'),
                                          translate('OpenLP.MainWindow',
                                                    'OpenLP will now close.  Imported settings will '
                                                    'be applied the next time you start OpenLP.'))
        self.settings_imported = True
        self.clean_up()
        QtCore.QCoreApplication.exit()

    def on_settings_export_item_clicked(self):
        """
        Export settings to a .conf file in INI format
        """
        export_file_path, filter_used = FileDialog.getSaveFileName(
            self,
            translate('OpenLP.MainWindow', 'Export Settings File'),
            None,
            translate('OpenLP.MainWindow', 'OpenLP Settings (*.conf)'))
        if not export_file_path:
            return
        # Make sure it's a .conf file.
        export_file_path = export_file_path.with_suffix('.conf')
        self.save_settings()
        try:
            self.settings.export(export_file_path)
        except OSError as ose:
            QtWidgets.QMessageBox.critical(self, translate('OpenLP.MainWindow', 'Export setting error'),
                                           translate('OpenLP.MainWindow',
                                                     'An error occurred while exporting the settings: {err}'
                                                     ).format(err=ose.strerror),
                                           QtWidgets.QMessageBox.StandardButton(
                                               QtWidgets.QMessageBox.StandardButton.Ok))

    def on_mode_default_item_clicked(self):
        """
        Put OpenLP into "Default" view mode.
        """
        self.set_view_mode(True, True, True, True, True, True, 'default')
        self.settings.setValue('user interface/is preset layout', True)
        self.settings.setValue('projector/show after wizard', True)

    def on_mode_setup_item_clicked(self):
        """
        Put OpenLP into "Setup" view mode.
        """
        self.set_view_mode(True, True, False, True, False, True, 'setup')
        self.settings.setValue('user interface/is preset layout', True)
        self.settings.setValue('projector/show after wizard', True)

    def on_mode_live_item_clicked(self):
        """
        Put OpenLP into "Live" view mode.
        """
        self.set_view_mode(False, True, False, False, True, True, 'live')
        self.settings.setValue('user interface/is preset layout', True)
        self.settings.setValue('projector/show after wizard', True)

    def set_view_mode(self, media: bool = True, service: bool = True, theme: bool = True, preview: bool = True,
                      live: bool = True, projector: bool = True, mode: str = '') -> None:
        """
        Set OpenLP to a different view mode.
        """
        if mode:
            self.settings.setValue('core/view mode', mode)
        self.media_manager_dock.setVisible(media)
        self.service_manager_dock.setVisible(service)
        self.theme_manager_dock.setVisible(theme)
        self.projector_manager_dock.setVisible(projector)
        self.set_preview_panel_visibility(preview)
        self.set_live_panel_visibility(live)

    def screen_changed(self):
        """
        The screen has changed so we have to update components such as the renderer.
        """
        try:
            # If a warning has been shown before, skip showing again to avoid spamming user.
            # Also do not show if the settings window is visible.
            should_show_messagebox = self.settings_form.isHidden() and self.should_show_screen_change_message
            if should_show_messagebox:
                self.should_show_screen_change_message = False
                self.live_controller.toggle_display('desktop')
                QtWidgets.QMessageBox.information(self,
                                                  UiStrings().ScreenSetupHasChangedTitle,
                                                  UiStrings().ScreenSetupHasChanged,
                                                  QtWidgets.QMessageBox.StandardButtons(
                                                      QtWidgets.QMessageBox.StandardButton.Ok))
                self.screen_change_timestamp = datetime.now()
            self.screen_updating_lock.acquire()
            self.application.set_busy_cursor()
            self.renderer.resize(self.live_controller.screens.current.display_geometry.size())
            self.preview_controller.screen_size_changed()
            self.live_controller.setup_displays()
            self.live_controller.screen_size_changed()
            self.setFocus()
            self.activateWindow()
            self.application.set_normal_cursor()
            # Forcing application to process events to trigger display update
            # We need to wait a little of time as it would otherwise need a mouse move
            # to process the screen change, for example
            QtCore.QTimer.singleShot(150, lambda: self.application.process_events())
        finally:
            self.screen_updating_lock.release()
            self.should_show_screen_change_message = True

    def closeEvent(self, event: QtGui.QCloseEvent):
        """
        Hook to close the main window and display windows on exit
        """
        # The MainApplication did not even enter the event loop (this happens
        # when OpenLP is not fully loaded). Just ignore the event.
        if not self.application.is_event_loop_active:
            event.ignore()
            return
        if self.service_manager_contents.is_modified():
            ret = self.service_manager_contents.save_modified_service()
            if ret == QtWidgets.QMessageBox.StandardButton.Save:
                if self.service_manager_contents.decide_save_method():
                    event.accept()
                else:
                    event.ignore()
            elif ret == QtWidgets.QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            if self.settings.value('advanced/enable exit confirmation'):
                msg_box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Question,
                                                translate('OpenLP.MainWindow', 'Exit OpenLP'),
                                                translate('OpenLP.MainWindow', 'Are you sure you want to exit OpenLP?'),
                                                QtWidgets.QMessageBox.StandardButton(
                                                    QtWidgets.QMessageBox.StandardButton.Close |
                                                    QtWidgets.QMessageBox.StandardButton.Cancel),
                                                self)
                close_button = msg_box.button(QtWidgets.QMessageBox.StandardButton.Close)
                close_button.setText(translate('OpenLP.MainWindow', '&Exit OpenLP'))
                msg_box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Close)
                if msg_box.exec() == QtWidgets.QMessageBox.StandardButton.Close:
                    event.accept()
                else:
                    event.ignore()
            else:
                event.accept()
        if event.isAccepted():
            with self._show_wait_dialog(translate('OpenLP.MainWindow', 'Please Wait'),
                                        translate('OpenLP.MainWindow', 'Waiting for some things to finish...')):
                # Wait for all the threads to complete
                self._wait_for_threads()
                # If we just did a settings import, close without saving changes.
                self.clean_up(save_settings=not self.settings_imported)

    def eventFilter(self, obj, event: QtCore.QEvent):
        if event.type() == QtCore.QEvent.Type.FileOpen:
            file_name = event.file()
            self.log_debug('Got open file event for {name}!'.format(name=file_name))
            self.application.args.insert(0, file_name)
            return True
        # Mac OS X should restore app window when user clicked on the OpenLP icon
        # in the Dock bar. However, OpenLP consists of multiple windows and this
        # does not work. This workaround fixes that.
        # The main OpenLP window is restored when it was previously minimized.
        elif event.type() == QtCore.QEvent.Type.ApplicationActivate:
            if is_macosx() and hasattr(self, 'main_window'):
                if self.main_window.isMinimized():
                    # Copied from QWidget.setWindowState() docs on how to restore and activate a minimized window
                    # while preserving its maximized and/or full-screen state.
                    self.main_window.setWindowState(self.main_window.windowState() &
                                                    ~QtCore.Qt.WindowState.WindowMinimized |
                                                    QtCore.Qt.WindowState.WindowActive)
                    return True

        return super(MainWindow, self).eventFilter(obj, event)

    def clean_up(self, save_settings: bool = True):
        """
        Runs all the cleanup code before OpenLP shuts down.

        :param save_settings: Switch to prevent saving settings. Defaults to **True**.
        """
        if save_settings:
            if self.settings.value('advanced/save current plugin'):
                self.settings.setValue('advanced/current media plugin', self.media_tool_box.currentIndex())
        # Call the cleanup method to shutdown plugins.
        self.log_info('cleanup plugins')
        self.plugin_manager.finalise_plugins()
        if save_settings:
            # Save settings
            self.save_settings()
        # Check if we need to change the data directory
        if self.new_data_path:
            self.change_data_directory()
        # Close down WebSocketServer
        self.ws_server.close()
        # Close down the display
        self.live_controller.close_displays()
        # Clean temporary files used by services
        self.service_manager_contents.clean_up()
        if is_win():
            # Needed for Windows to stop crashes on exit
            Registry().remove('application')

    def set_service_modified(self, modified: bool, file_name: Path | str):
        """
        This method is called from the ServiceManager to set the title of the main window.

        :param modified: Whether or not this service has been modified.
        :param file_name: The file name of the service file.
        """
        if modified:
            title = '{title} - {name}*'.format(title=UiStrings().OpenLP, name=file_name)
        else:
            title = '{title} - {name}'.format(title=UiStrings().OpenLP, name=file_name)
        self.setWindowTitle(title)

    def show_status_message(self, message: str, timeout: int = 0):
        """
        Show a message in the status bar

        :param message: The message to show
        :param timeout: How long to show it for, in milliseconds; 0 keeps it
            until the next message replaces it
        """
        self.status_bar.showMessage(message, timeout)

    def default_theme_changed(self):
        """
        Update the default theme indicator in the status bar
        """
        theme_name = self.settings.value('themes/global theme')
        self.default_theme_label.setText(translate('OpenLP.MainWindow',
                                                   'Default Theme: {theme}').format(theme=theme_name))

    def on_live_output_state_changed(self, hide_mode=None):
        """
        Update the status bar output-state segment when the live output is
        shown or hidden (Noir theme only).

        :param hide_mode: The active HideMode, or None while output is showing
        """
        if hide_mode is None:
            self.output_state_label.setText(translate('OpenLP.MainWindow', 'ON AIR'))
            self.output_state_label.setProperty('outputState', 'onair')
        else:
            if hide_mode == HideMode.Theme:
                self.output_state_label.setText(translate('OpenLP.MainWindow', 'THEME ONLY'))
            elif hide_mode == HideMode.Screen:
                self.output_state_label.setText(translate('OpenLP.MainWindow', 'OUTPUT HIDDEN'))
            else:
                self.output_state_label.setText(translate('OpenLP.MainWindow', 'BLANKED'))
            self.output_state_label.setProperty('outputState', 'hidden')
        self.output_state_label.style().unpolish(self.output_state_label)
        self.output_state_label.style().polish(self.output_state_label)

    def toggle_media_manager(self):
        """
        Toggle the visibility of the media manager
        """
        if self.sender() is self.view_media_manager_item:
            self.media_manager_dock.setVisible(not self.media_manager_dock.isVisible())
        self.view_media_manager_item.setChecked(self.media_manager_dock.isVisible())
        self.settings.setValue('user interface/is preset layout', False)
        self.settings.setValue('user interface/show library', self.media_manager_dock.isVisible())

    def toggle_projector_manager(self):
        """
        Toggle visibility of the projector manager
        """
        if self.sender() is self.view_projector_manager_item:
            self.projector_manager_dock.setVisible(not self.projector_manager_dock.isVisible())
        self.view_projector_manager_item.setChecked(self.projector_manager_dock.isVisible())
        self.settings.setValue('user interface/is preset layout', False)
        self.settings.setValue('user interface/show projectors', self.projector_manager_dock.isVisible())
        # Check/uncheck checkbox on First time wizard based on visibility of this panel.
        if not self.settings.value('projector/show after wizard'):
            self.settings.setValue('projector/show after wizard', True)
        else:
            self.settings.setValue('projector/show after wizard', False)

    def toggle_service_manager(self):
        """
        Toggle the visibility of the service manager
        """
        if self.sender() is self.view_service_manager_item:
            self.service_manager_dock.setVisible(not self.service_manager_dock.isVisible())
        self.view_service_manager_item.setChecked(self.service_manager_dock.isVisible())
        self.settings.setValue('user interface/is preset layout', False)
        self.settings.setValue('user interface/show service', self.service_manager_dock.isVisible())

    def toggle_theme_manager(self):
        """
        Toggle the visibility of the theme manager
        """
        if self.sender() is self.view_theme_manager_item:
            self.theme_manager_dock.setVisible(not self.theme_manager_dock.isVisible())
        self.view_theme_manager_item.setChecked(self.theme_manager_dock.isVisible())
        self.settings.setValue('user interface/is preset layout', False)
        self.settings.setValue('user interface/show themes', self.theme_manager_dock.isVisible())

    def toggle_log_viewer(self):
        """
        Toggle the visibility of the log viewer
        """
        if self.sender() is self.view_log_viewer_item:
            self.log_viewer_dock.setVisible(not self.log_viewer_dock.isVisible())
        self.view_log_viewer_item.setChecked(self.log_viewer_dock.isVisible())

    def set_preview_panel_visibility(self, is_visible: bool):
        """
        Sets the visibility of the preview panel including saving the setting and updating the menu.

        :param is_visible: A bool giving the state to set the panel to
                True - Visible
                False - Hidden

        """
        self.preview_controller.panel.setVisible(is_visible)
        self.settings.setValue('user interface/preview panel', is_visible)
        self.view_preview_panel.setChecked(is_visible)
        self.settings.setValue('user interface/is preset layout', False)

    def set_lock_panel(self, is_locked: bool):
        """
        Sets the ability to stop the toolbars being changed.
        """
        if is_locked:
            self.theme_manager_dock.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
            self.service_manager_dock.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
            self.media_manager_dock.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
            self.projector_manager_dock.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
            self.log_viewer_dock.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
            self.view_mode_menu.setEnabled(False)
            self.view_media_manager_item.setEnabled(False)
            self.view_service_manager_item.setEnabled(False)
            self.view_theme_manager_item.setEnabled(False)
            self.view_projector_manager_item.setEnabled(False)
            self.view_log_viewer_item.setEnabled(False)
            self.view_preview_panel.setEnabled(False)
            self.view_live_panel.setEnabled(False)
        else:
            all_dock_features = (QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable |
                                 QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable |
                                 QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable)
            self.theme_manager_dock.setFeatures(all_dock_features)
            self.service_manager_dock.setFeatures(all_dock_features)
            self.media_manager_dock.setFeatures(all_dock_features)
            self.projector_manager_dock.setFeatures(all_dock_features)
            self.log_viewer_dock.setFeatures(all_dock_features)
            self.view_mode_menu.setEnabled(True)
            self.view_media_manager_item.setEnabled(True)
            self.view_service_manager_item.setEnabled(True)
            self.view_theme_manager_item.setEnabled(True)
            self.view_projector_manager_item.setEnabled(True)
            self.view_log_viewer_item.setEnabled(True)
            self.view_preview_panel.setEnabled(True)
            self.view_live_panel.setEnabled(True)
        self.settings.setValue('user interface/lock panel', is_locked)

    def set_live_panel_visibility(self, is_visible: bool):
        """
        Sets the visibility of the live panel including saving the setting and updating the menu.

        :param is_visible: A bool giving the state to set the panel to
                True - Visible
                False - Hidden
        """
        self.live_controller.panel.setVisible(is_visible)
        self.settings.setValue('user interface/live panel', is_visible)
        self.view_live_panel.setChecked(is_visible)
        self.settings.setValue('user interface/is preset layout', False)

    def load_settings(self):
        """
        Load the main window settings.
        """
        # Remove obsolete entries.
        self.settings.remove('custom slide')
        self.settings.remove('service')
        self.recent_files = self.settings.value('core/recent files')
        self.move(self.settings.value('user interface/main window position'))
        self.restoreGeometry(self.settings.value('user interface/main window geometry'))
        self.restoreState(self.settings.value('user interface/main window state'))
        # The log viewer dock's visibility comes from the restored window state
        self.view_log_viewer_item.setChecked(self.log_viewer_dock.isVisible())
        if not self._window_position_is_valid(self.pos(), self.geometry()):
            self.move(0, 0)
        self.live_controller.splitter.restoreState(self.settings.value('user interface/live splitter geometry'))
        self.preview_controller.splitter.restoreState(self.settings.value('user interface/preview splitter geometry'))
        self.control_splitter.restoreState(self.settings.value('user interface/main window splitter geometry'))
        # This needs to be called after restoreState(), because saveState() also saves the "Collapsible" property
        # which was True (by default) < OpenLP 2.1.
        self.control_splitter.setChildrenCollapsible(False)

    def _window_position_is_valid(self, position: QtCore.QPoint, geometry: QtCore.QRect):
        """
        Checks if the saved window position is still valid by checking if the bar at the top of the window
        (which allows the user to move the window) appears on one of the screens.
        This may not be the case if the user has unplugged the monitor where openlp was previously shown,
        or if the displays have been reconfigured.

        :param position: QtCore.QtPoint for the top left position of the window
        :param geometry: QtCore.QRect for the geometry of the window

        :return:    True or False
        """
        screens = ScreenList()
        for screen in screens:
            # window top bar y value must be between top and bottom of a screen
            # plus the left edge must be left of the right of the screen
            # and the right edge must be right of the left of the screen (allowing 50 pixels for control buttons)
            if ((screen.geometry.y() <= position.y() <= screen.geometry.y() + screen.geometry.height()) and
                    (position.x() < screen.geometry.x() + screen.geometry.width()) and
                    (position.x() + geometry.width() > screen.geometry.x() + 50)):
                return True
        return False

    def save_settings(self):
        """
        Save the main window settings.
        """
        # Exit if we just did a settings import.
        if self.settings_imported:
            return
        self.settings.setValue('core/recent files', self.recent_files)
        self.settings.setValue('user interface/main window position', self.pos())
        self.settings.setValue('user interface/main window state', self.saveState())
        self.settings.setValue('user interface/main window geometry', self.saveGeometry())
        self.settings.setValue('user interface/live splitter geometry', self.live_controller.splitter.saveState())
        self.settings.setValue('user interface/preview splitter geometry', self.preview_controller.splitter.saveState())
        self.settings.setValue('user interface/main window splitter geometry', self.control_splitter.saveState())
        self.theme_manager.save_settings()

    def update_recent_files_menu(self):
        """
        Updates the recent file menu with the latest list of service files accessed.
        """
        recent_file_count = self.settings.value('advanced/recent file count')
        # This is to get around a weird issue that we're seeing on macOS. We've not been able to reproduce it
        # ourselves, but hopefully this will catch the issue.
        # See https://gitlab.com/openlp/openlp/-/issues/1383
        if isinstance(self.recent_files, str):
            try:
                self.recent_files = json.loads(self.recent_files, cls=OpenLPJSONDecoder)
            except json.JSONDecodeError as e:
                self.log_exception(e)
                self.recent_files = []
        elif isinstance(self.recent_files, list) and self.recent_files and isinstance(self.recent_files[0], str) and \
                self.recent_files[0].startswith('['):
            try:
                self.recent_files = json.loads(self.recent_files[0], cls=OpenLPJSONDecoder)
            except json.JSONDecodeError as e:
                self.log_exception(e)
                self.recent_files = []
        # Now continue as usual...
        self.recent_files_menu.clear()
        count = 0
        for recent_path in self.recent_files:
            if not recent_path:
                continue
            recent_path = Path(recent_path)
            if not recent_path.is_file():
                continue
            count += 1
            self.log_debug('Recent file name: {name}'.format(name=recent_path))
            action = create_action(self, '',
                                   text='&{n} {name}'.format(n=count, name=recent_path.name),
                                   data=recent_path, triggers=self.service_manager_contents.on_recent_service_clicked)
            self.recent_files_menu.addAction(action)
            if count == recent_file_count:
                break
        clear_recent_files_action = \
            create_action(self, '', text=translate('OpenLP.MainWindow', 'Clear List', 'Clear List of recent files'),
                          statustip=translate('OpenLP.MainWindow', 'Clear the list of recent files.'),
                          enabled=bool(self.recent_files), triggers=self.clear_recent_file_menu)
        add_actions(self.recent_files_menu, (None, clear_recent_files_action))

    def add_recent_file(self, filename: Path | str):
        """
        Adds a service to the list of recently used files.

        :param filename: The service filename to add
        """
        # The max_recent_files value does not have an interface and so never gets
        # actually stored in the settings therefore the default value of 20 will
        # always be used.
        max_recent_files = self.settings.value('advanced/max recent files')
        file_path = Path(filename)
        # Some cleanup to reduce duplication in the recent file list
        file_path = resolve(file_path)
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:max_recent_files]

    def clear_recent_file_menu(self):
        """
        Clears the recent files.
        """
        self.recent_files = []

    def display_progress_bar(self, size: int):
        """
        Make Progress bar visible and set size
        """
        self.load_progress_bar.show()
        self.load_progress_bar.setMaximum(size)
        self.load_progress_bar.setValue(0)
        self.application.process_events()

    def increment_progress_bar(self, increment: int = 1):
        """
        Increase the Progress Bar by the value in increment.

        :param int increment: The value you to increase the progress bar by.
        """
        self.load_progress_bar.setValue(int(self.load_progress_bar.value() + increment))
        self.application.process_events()

    def finished_progress_bar(self):
        """
        Trigger it's removal after 2.5 second
        """
        self.timer_id = self.startTimer(2500)

    def timerEvent(self, event: QtCore.QTimerEvent):
        """
        Remove the Progress bar from view.
        """
        if event.timerId() == self.timer_id:
            self.timer_id = 0
            self.load_progress_bar.hide()
            # Sometimes the timer goes off as OpenLP is shutting down, and the application has already been deleted
            if self.application:
                self.application.process_events()

    def set_copy_data(self, copy_data):
        """
        Set the flag to copy the data
        """
        self.copy_data = copy_data

    def change_data_directory(self):
        """
        Change the data directory.
        """
        self.log_info('Changing data path to {newpath}'.format(newpath=self.new_data_path))
        old_data_path = AppLocation.get_data_path()
        # Copy OpenLP data to new location if requested.
        self.application.set_busy_cursor()
        if self.copy_data:
            self.log_info('Copying data to new path')
            try:
                self.show_status_message(
                    translate('OpenLP.MainWindow', 'Copying OpenLP data to new data directory location - {path} '
                              '- Please wait for copy to finish').format(path=self.new_data_path))
                shutil.copytree(str(old_data_path), str(self.new_data_path), dirs_exist_ok=True)
                self.log_info('Copy successful')
            except (OSError, shutil.Error) as why:
                self.application.set_normal_cursor()
                self.log_exception('Data copy failed {err}'.format(err=str(why)))
                err_text = translate('OpenLP.MainWindow',
                                     'OpenLP Data directory copy failed\n\n{err}').format(err=str(why))
                QtWidgets.QMessageBox.critical(self, translate('OpenLP.MainWindow', 'New Data Directory Error'),
                                               err_text,
                                               QtWidgets.QMessageBox.StandardButton(
                                                   QtWidgets.QMessageBox.StandardButton.Ok))
                return False
        else:
            self.log_info('No data copy requested')
        # Change the location of data directory in config file.
        self.settings.setValue('advanced/data path', self.new_data_path)
        # Check if the new data path is our default.
        if self.new_data_path == AppLocation.get_directory(AppLocation.DataDir):
            self.settings.remove('advanced/data path')
        self.application.set_normal_cursor()

    def open_cmd_line_files(self, args: list):
        """
        Open files passed in through command line arguments.

        :param list[str] args: List of remaining positional arguments
        """
        self.log_info("=" * 80)
        self.log_info("Starting command line file processing")
        self.log_info(f"Raw arguments: {args}")

        if not args:
            self.log_info("No command line arguments supplied. Skipping file loading.")
            return

        # ------------------------------------------------------------------
        # Remove special flags
        # ------------------------------------------------------------------
        if '--disable-web-security' in args:
            self.log_info("Removing '--disable-web-security' argument.")
            args.remove('--disable-web-security')

        try:
            platform_idx = args.index('-platform')
            self.log_info(
                f"Detected Qt platform argument: "
                f"-platform {args[platform_idx + 1] if platform_idx + 1 < len(args) else '<missing>'}"
            )

            args.pop(platform_idx)

            if platform_idx < len(args):
                args.pop(platform_idx)

        except (ValueError, IndexError):
            self.log_debug("No Qt platform argument detected.")

        self.log_info(f"Arguments after cleanup: {args}")

        # ------------------------------------------------------------------
        # Decode HTML encoded quotes
        # ------------------------------------------------------------------
        args = [arg.replace('&quot;', '') for arg in args]
        self.log_info(f"Arguments after HTML entity cleanup: {args}")

        # ------------------------------------------------------------------
        # Attempt 1: Treat each argument as an individual file
        # ------------------------------------------------------------------
        self.log_info("Attempt 1: Checking each argument individually.")

        file_path = None

        for index, arg in enumerate(args):
            self.log_info(f"[Attempt 1] Checking argument {index}: '{arg}'")

            try:
                resolved = resolve(Path(arg), is_strict=True)
                self.log_info(f"Resolved path: {resolved}")

                if resolved.is_file():
                    self.log_info("Resolved path is a valid file.")
                    file_path = resolved
                    break
                else:
                    self.log_warning(f"Resolved path exists but is not a file: {resolved}")

            except FileNotFoundError:
                self.log_warning(f"File not found: {arg}")

            except Exception as e:
                self.log_exception(f"Unexpected error resolving '{arg}': {e}")

        # ------------------------------------------------------------------
        # Attempt 2: Build paths containing spaces
        # ------------------------------------------------------------------
        if not file_path:
            self.log_info("Attempt 1 failed.")
            self.log_info("Attempt 2: Combining arguments into progressively longer paths.")

            path_so_far = []

            for arg in args:
                path_so_far.append(arg)

                candidate = " ".join(path_so_far)

                self.log_info(f"Trying combined path: '{candidate}'")

                try:
                    resolved = resolve(Path(candidate), is_strict=True)
                    self.log_info(f"Resolved candidate: {resolved}")

                    if resolved.is_file():
                        self.log_info("Combined path is a valid file.")
                        file_path = resolved
                        break
                    else:
                        self.log_warning(
                            f"Combined path exists but is not a file: {resolved}"
                        )

                except FileNotFoundError:
                    self.log_warning(f"Combined path not found: {candidate}")

                except Exception as e:
                    self.log_exception(
                        f"Unexpected error resolving combined path '{candidate}': {e}"
                    )

        # ------------------------------------------------------------------
        # Final result
        # ------------------------------------------------------------------
        if file_path:
            self.log_info(f"Candidate file located: {file_path}")
            self.log_info(f"File suffix: {file_path.suffix}")

            if file_path.suffix in ['.osz', '.oszl']:
                self.log_info("Recognized OpenLP service file. Loading service.")
                self.service_manager_contents.load_file(file_path)
                self.log_info("Service loaded successfully.")
            else:
                self.log_warning(
                    f"Unsupported file type '{file_path.suffix}'. "
                    "Expected '.osz' or '.oszl'."
                )
        else:
            self.log_warning("No valid file could be resolved from the supplied arguments.")
            self.log_warning(f"Processed arguments: {args}")

        self.log_info("Finished command line file processing.")
        self.log_info("=" * 80)

    # def open_cmd_line_files(self, args: list):
    #     """
    #     Open files passed in through command line arguments
    #
    #     :param list[str] args: List of remaining positional arguments
    #     """
    #     self.log_info(args)
    #     # Drop this argument, it's obvs not a filename
    #     if '--disable-web-security' in args:
    #         args.remove('--disable-web-security')
    #     # strip platform args, not a filename either
    #     try:
    #         platform_idx = args.index('-platform')
    #         if platform_idx >= 0:
    #             # remove the platform arg
    #             args.pop(platform_idx)
    #             # remove the platform input
    #             args.pop(platform_idx)
    #     except (ValueError, IndexError):
    #         pass
    #     # It has been known for Microsoft to double quote the path passed in and then encode one of the quotes.
    #     # Remove these to get the correct path.
    #     args = list(map(lambda x: x.replace('&quot;', ''), args))
    #     # Loop through the parameters, and see if we can pull a file out
    #     file_path = None
    #     for arg in args:
    #         try:
    #             # Resolve the file, and use strict mode to throw an exception if the file does not exist
    #             file_path = resolve(Path(arg), is_strict=True)
    #             # Check if this is actually a file
    #             if file_path.is_file():
    #                 break
    #             else:
    #                 file_path = None
    #         except FileNotFoundError:
    #             file_path = None
    #     # If none of the individual components are files, let's try pulling them together
    #     if not file_path:
    #         path_so_far = []
    #         for arg in args:
    #             path_so_far.append(arg)
    #             try:
    #                 file_path = resolve(Path(' '.join(path_so_far)), is_strict=True)
    #                 if file_path.is_file():
    #                     break
    #                 else:
    #                     file_path = None
    #             except FileNotFoundError:
    #                 file_path = None
    #         else:
    #             file_path = None
    #     if file_path and file_path.suffix in ['.osz', '.oszl']:
    #         self.log_info("File name found")
    #         self.service_manager_contents.load_file(file_path)
    #     else:
    #         self.log_error(f"File {file_path} not found for arg {args}")
