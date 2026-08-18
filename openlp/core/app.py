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
The :mod:`core` module provides all core application functions

All the core functions of the OpenLP application including the GUI, settings,
logging and a plugin framework are contained within the openlp.core module.
"""
import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from shutil import copytree, move
from traceback import format_exception

from PySide6 import QtCore, QtGui, QtWebEngineCore, QtWidgets  # noqa

from openlp.core.api.deploy import check_for_remote_update
from openlp.core.common.applocation import AppLocation
from openlp.core.common.enum import HiDPIMode
from openlp.core.common.i18n import LanguageManager, UiStrings, translate
from openlp.core.common.mixins import LogMixin
from openlp.core.common.path import create_paths, resolve
from openlp.core.common.platform import is_macosx, is_wayland_compositor, is_win
from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings, check_for_variant_migration
from openlp.core.display.screens import ScreenList
from openlp.core.display.webengine import init_webview_custom_schemes, set_webview_display_path
from openlp.core.lib.filelock import FileLock
from openlp.core.loader import loader
from openlp.core.resources import qInitResources
from openlp.core.server import Server
from openlp.core.state import State
from openlp.core.ui.exceptionform import ExceptionForm
from openlp.core.ui.firsttimeform import FirstTimeForm
from openlp.core.ui.firsttimelanguageform import FirstTimeLanguageForm
from openlp.core.ui.mainwindow import MainWindow
from openlp.core.ui.splashscreen import SplashScreen
from openlp.core.ui.style import get_application_stylesheet, set_default_theme, is_ui_theme, is_ui_theme_dark, UiThemes
from openlp.core.version import get_version


__all__ = ['OpenLP', 'main']


log = logging.getLogger()


class OpenLP(QtCore.QObject, LogMixin):
    """
    The core worker class. This class that holds the whole system together.
    """
    args = []
    worker_threads = {}
    settings = None

    def exec(self):
        """
        Override exec method to allow the shared memory to be released on exit
        """
        self.is_event_loop_active = True
        result = QtWidgets.QApplication.exec()
        if self.data_dir_lock:
            self.data_dir_lock.release()
        if hasattr(self, 'server'):
            self.server.close_server()
        return result

    def run(self, args, app):
        """
        Run the OpenLP application.

        :param args: Some Args
        """
        self.is_event_loop_active = False
        # On Windows, the args passed into the constructor are ignored. Not very handy, so set the ones we want to use.
        # On Linux and FreeBSD, in order to set the WM_CLASS property for X11, we pass "OpenLP" in as a command line
        # argument. This interferes with files being passed in as command line arguments, so we remove it from the list.
        if 'OpenLP' in args:
            args.remove('OpenLP')
        self.args.extend(args)
        # set desktop file name, which is used to display the proper window icon on Wayland
        QtGui.QGuiApplication.setDesktopFileName("openlp")
        # Decide how many screens we have and their size
        screens = ScreenList.create(app)
        # First time checks in settings
        has_run_wizard = self.settings.value('core/has run wizard')
        if not has_run_wizard:
            ftw = FirstTimeForm()
            ftw.initialize(screens)
            if ftw.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                self.settings.setValue('core/has run wizard', True)
            else:
                QtCore.QCoreApplication.exit()
                sys.exit()
        can_show_splash = self.settings.value('core/show splash')
        if can_show_splash:
            self.splash = SplashScreen()
            self.splash.show()
        # make sure Qt really display the splash screen
        QtWidgets.QApplication.processEvents()
        # Check if OpenLP has been upgrade and if a backup of data should be created
        self.backup_on_upgrade(has_run_wizard, can_show_splash)
        # start the main app window
        Registry().toggle_suppressing()
        loader()
        Registry().toggle_suppressing()
        # Set the darkmode based on theme
        set_default_theme(app)
        self.main_window = MainWindow()
        self.main_window.installEventFilter(self.main_window)
        # Correct stylesheet bugs
        application_stylesheet = get_application_stylesheet()
        if application_stylesheet:
            self.main_window.setStyleSheet(application_stylesheet)
        Registry().execute('bootstrap_initialise')
        State().flush_preconditions()
        Registry().execute('bootstrap_post_set_up')
        self.main_window.show()
        if can_show_splash:
            # now kill the splashscreen
            log.debug('Splashscreen closing')
            self.splash.close()
            log.debug('Splashscreen closed')
        # make sure Qt really display the splash screen
        QtWidgets.QApplication.processEvents()
        self.main_window.repaint()
        QtWidgets.QApplication.processEvents()
        if not has_run_wizard:
            self.main_window.first_time()
        if self.settings.value('api/update check'):
            check_for_remote_update(self.main_window)
        self.main_window.is_display_blank()
        Registry().execute('bootstrap_completion')
        return self.exec()

    @staticmethod
    def is_already_running():
        """
        Tell the user there is a 2nd instance running.
        """
        QtWidgets.QMessageBox.critical(None, UiStrings().Error, UiStrings().OpenLPStart,
                                       QtWidgets.QMessageBox.StandardButton(QtWidgets.QMessageBox.StandardButton.Ok))

    def is_data_path_missing(self):
        """
        Check if the data folder path exists.
        """
        data_folder_path = AppLocation.get_data_path()
        if not data_folder_path.exists():
            log.critical('Database was not found in: %s', data_folder_path)
            status = QtWidgets.QMessageBox.critical(
                None, translate('OpenLP', 'Data Directory Error'),
                translate('OpenLP', 'OpenLP data folder was not found in:\n\n{path}\n\nThe location of the data folder '
                                    'was previously changed from the OpenLP\'s default location. If the data was '
                                    'stored on removable device, that device needs to be made available.\n\nYou may '
                                    'reset the data location back to the default location, or you can try to make the '
                                    'current location available.\n\nDo you want to reset to the default data location? '
                                    'If not, OpenLP will be closed so you can try to fix the problem.')
                .format(path=data_folder_path),
                QtWidgets.QMessageBox.StandardButton(QtWidgets.QMessageBox.StandardButton.Yes |
                                                     QtWidgets.QMessageBox.StandardButton.No),
                QtWidgets.QMessageBox.StandardButton.No)
            if status == QtWidgets.QMessageBox.StandardButton.No:
                # If answer was "No", return "True", it will shutdown OpenLP in def main
                log.info('User requested termination')
                return True
            # If answer was "Yes", remove the custom data path thus resetting the default location.
            self.settings.remove('advanced/data path')
            log.info('Database location has been reset to the default settings.')
            return False

    def hook_exception(self, exc_type, value, traceback):
        """
        Add an exception hook so that any uncaught exceptions are displayed in this window rather than somewhere where
        users cannot see it and cannot report when we encounter these problems.

        :param exc_type: The class of exception.
        :param value: The actual exception object.
        :param traceback: A traceback object with the details of where the exception occurred.
        """
        # We can't log.exception here because the last exception no longer exists, we're actually busy handling it.
        log.critical(''.join(format_exception(exc_type, value, traceback)))
        if not hasattr(self, 'exception_form'):
            self.exception_form = ExceptionForm()
        self.exception_form.exception_text_edit.setPlainText(''.join(format_exception(exc_type, value, traceback)))
        self.set_normal_cursor()
        is_splash_visible = False
        if hasattr(self, 'splash') and self.splash.isVisible():
            is_splash_visible = True
            self.splash.hide()
        self.exception_form.exec()
        if is_splash_visible:
            self.splash.show()

    def backup_on_upgrade(self, has_run_wizard, can_show_splash):
        """
        Check if OpenLP has been upgraded, and ask if a backup of data should be made

        :param has_run_wizard: OpenLP has been run before
        :param can_show_splash: Should OpenLP show the splash screen
        """
        data_version = self.settings.value('core/application version')
        openlp_version = get_version()['version']
        # New installation, no need to create backup
        if not has_run_wizard:
            self.settings.setValue('core/application version', openlp_version)
        # If data_version is different from the current version ask if we should backup the data folder
        elif data_version != openlp_version:
            if can_show_splash and self.splash.isVisible():
                self.splash.hide()
            if (QtWidgets.QMessageBox.question(None, translate('OpenLP', 'Backup'),
                                               translate('OpenLP', 'OpenLP has been upgraded, do you want to create\n'
                                                                   'a backup of the old data folder?'),
                                               defaultButton=QtWidgets.QMessageBox.StandardButton.Yes) ==
                    QtWidgets.QMessageBox.StandardButton.Yes):
                # Create copy of data folder
                data_folder_path = AppLocation.get_data_path()
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                data_folder_backup_path = data_folder_path.with_name(data_folder_path.name + '-' + timestamp)
                try:
                    copytree(data_folder_path, data_folder_backup_path)
                except OSError:
                    QtWidgets.QMessageBox.warning(None, translate('OpenLP', 'Backup'),
                                                  translate('OpenLP', 'Backup of the data folder failed!'))
                    return
                message = translate('OpenLP',
                                    'A backup of the data folder has been created at:\n\n'
                                    '{text}').format(text=data_folder_backup_path)
                QtWidgets.QMessageBox.information(None, translate('OpenLP', 'Backup'), message)

            # Update the version in the settings
            self.settings.setValue('core/application version', openlp_version)
            if can_show_splash:
                self.splash.show()

    @staticmethod
    def process_events():
        """
        Wrapper to make ProcessEvents visible and named correctly
        """
        QtWidgets.QApplication.processEvents()

    @staticmethod
    def set_busy_cursor():
        """
        Sets the Busy Cursor for the Application
        """
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.BusyCursor)
        QtWidgets.QApplication.processEvents()

    @staticmethod
    def set_normal_cursor():
        """
        Sets the Normal Cursor for the Application
        """
        QtWidgets.QApplication.restoreOverrideCursor()
        QtWidgets.QApplication.processEvents()


def parse_options():
    """
    Parse the command line arguments

    :return: An :object:`argparse.Namespace` insatnce containing the parsed args.
    :rtype: argparse.Namespace
    """
    # Set up command line options.
    parser = argparse.ArgumentParser(prog='openlp')
    parser.add_argument('-e', '--no-error-form', dest='no_error_form', action='store_true',
                        help='Disable the error notification form.')
    # The packaged (frozen) app defaults to full debug logging so that openlp.log always
    # carries the detailed pipeline/transition instrumentation; development runs keep the
    # quiet default. Both can still be overridden with -l on the command line.
    parser.add_argument('-l', '--log-level', dest='loglevel',
                        default='debug' if getattr(sys, 'frozen', False) else 'warning', metavar='LEVEL',
                        help='Set logging to LEVEL level. Valid values are "debug", "info", "warning".')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        help='Print logging output to the console.')
    parser.add_argument('-p', '--portable', dest='portable', action='store_true',
                        help='Specify if this should be run as a portable app, ')
    parser.add_argument('-P', '--portable-path', dest='portablepath', default=None,
                        help='Specify the path of the portable data, defaults to "{dir_name}".'.format(
                            dir_name=os.path.join('<AppDir>', '..', '..')))
    parser.add_argument('-w', '--no-web-server', dest='no_web_server', action='store_true',
                        help='Turn off the Web and Socket Server ')
    parser.add_argument('--display-custom-path', dest='display_custom_path', default=None,
                        help='Specify the custom path for display renderer (HTML). Useful for development.')
    parser.add_argument('rargs', nargs='*', default=[])
    # Parse command line options and deal with them.
    return parser.parse_args()


def set_up_logging(log_path: str, display_on_console: bool = False):
    """
    Setup our logging using log_path

    :param Path log_path: The file to save the log to.
    :param bool display_on_console: If True, log messages will be displayed on the console as well.
    :rtype: None
    """
    create_paths(log_path, do_not_log=True)
    file_path = log_path / 'openlp.log'
    logfile = logging.FileHandler(file_path, 'w', encoding='UTF-8')
    formatter = logging.Formatter('%(asctime)s %(threadName)s %(name)-55s %(levelname)-8s %(message)s')
    logfile.setFormatter(formatter)
    log.addHandler(logfile)
    # Send warnings to the log file
    logging.captureWarnings(True)
    print(f'Logging to: {file_path} and level {log.level}')
    if display_on_console:
        console_log = logging.StreamHandler(sys.stdout)
        console_log.setFormatter(formatter)
        log.addHandler(console_log)


def set_up_web_engine_cache(web_cache_path):
    """
    Setup path for the qt web engine to dump it's files

    :param Path web_cache_path: The folder for the web engine files
    :rtype: None
    """
    web_engine_profile = QtWebEngineCore.QWebEngineProfile.defaultProfile()
    web_engine_profile.setCachePath(str(web_cache_path))
    web_engine_profile.setPersistentStoragePath(str(web_cache_path))


def backup_if_version_changed(settings):
    """
    Check version of settings and the application version and backup if the version is different.
    Returns true if a backup was not required or the backup succeeded,
    false if backup required but was cancelled or failed.

    :param Settings settings: The settings object
    :rtype: bool
    """
    is_downgrade = get_version()['version'] < settings.value('core/application version')
    # No need to backup if version matches and we're not downgrading
    if not (settings.version_mismatched() and settings.value('core/has run wizard')) and not is_downgrade:
        return True
    now = datetime.now()
    data_folder_path = AppLocation.get_data_path()
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    data_folder_backup_path = data_folder_path.with_name(data_folder_path.name + '-' + timestamp)
    # Warning if OpenLP is downgrading
    if is_downgrade:
        close_result = QtWidgets.QMessageBox.warning(
            None, translate('OpenLP', 'Downgrade'),
            translate('OpenLP', 'OpenLP has found a configuration file created by a newer version of OpenLP. '
                      'OpenLP will start with a fresh install as downgrading data is not supported. Any existing data '
                      'will be backed up to:\n\n{data_folder_backup_path}\n\n'
                      'Do you want to continue?').format(data_folder_backup_path=data_folder_backup_path),
            QtWidgets.QMessageBox.StandardButton(QtWidgets.QMessageBox.StandardButton.Yes |
                                                 QtWidgets.QMessageBox.StandardButton.No),
            QtWidgets.QMessageBox.StandardButton.No)
        if close_result == QtWidgets.QMessageBox.StandardButton.No:
            # Return false as backup failed.
            return False
    # Backup the settings
    if settings.version_mismatched() or is_downgrade:
        settings_back_up_path = data_folder_path / (now.strftime('%Y-%m-%d %H-%M') + '.conf')
        log.info(f'Settings are being backed up to {settings_back_up_path}')
        if not is_downgrade:
            # Inform user of settings backup location
            QtWidgets.QMessageBox.information(
                None, translate('OpenLP', 'Settings Backup'),
                translate('OpenLP', 'Your settings are about to be upgraded. A backup will be created at '
                                    '{settings_back_up_path}').format(settings_back_up_path=settings_back_up_path))
        # Backup the settings
        try:
            settings.export(settings_back_up_path)
        except OSError:
            QtWidgets.QMessageBox.warning(
                None, translate('OpenLP', 'Settings Backup'),
                translate('OpenLP', 'Settings back up failed.\n\nOpenLP will attempt to continue.'))
    # Backup and remove data folder if downgrading
    if is_downgrade:
        log.info(f'Data folder being backed up to {data_folder_backup_path}')
        try:
            # We don't want to use data from newer versions, so rather than a copy, we'll just move/rename
            move(data_folder_path, data_folder_backup_path)
        except OSError:
            log.exception('Failed to backup data for downgrade')
            QtWidgets.QMessageBox.critical(None, translate('OpenLP', 'OpenLP Backup'),
                                           translate('OpenLP', 'Backup of the data folder failed during downgrade.'))
            return False
    # Reset all the settings if we're downgrading
    if is_downgrade:
        settings.clear()
    settings.upgrade_settings()
    return True


def apply_dpi_adjustments_stage_qt(hidpi_mode, qt_args):
    if hidpi_mode == HiDPIMode.Windows_Unaware:
        os.environ['QT_SCALE_FACTOR'] = '1'
        os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '0'
        os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '0'
        if is_win():
            try:
                platform_index = qt_args.index('-platform')
                qt_args[platform_index + 1] += ' windows:dpiawareness=0'
            except ValueError:
                qt_args.extend(['-platform', 'windows:dpiawareness=0'])


def apply_dpi_adjustments_stage_application(hidpi_mode: HiDPIMode, application: QtWidgets.QApplication):
    """
    Apply OpenLP DPI adjustments to bypass Windows and QT bugs (unless disabled on settings)

    :param args: OpenLP startup arguments
    :param settings: The settings object
    :param stage: The stage of app
    """
    if hidpi_mode == HiDPIMode.Default and is_win() and application.devicePixelRatio() > 1.0:
        # Increasing font size to match pixel ratio (Windows only)
        # TODO: Review on Qt6 migration
        font = application.font()
        font.setPointSizeF(font.pointSizeF() * application.devicePixelRatio())
        application.setFont(font)


def setup_portable_settings(portable_path: Path | str | None) -> Settings:
    """Set up the portable settings"""
    Settings.setDefaultFormat(Settings.IniFormat)
    # Get location OpenLPPortable.ini
    if portable_path:
        if os.path.isabs(portable_path):
            portable_path = Path(portable_path)
        else:
            portable_path = AppLocation.get_directory(AppLocation.AppDir) / '..' / portable_path
    else:
        portable_path = AppLocation.get_directory(AppLocation.AppDir) / '..' / '..'
    portable_path = resolve(portable_path)
    portable_settings_path = portable_path / 'Data' / 'OpenLP.ini'
    # Make this our settings file
    log.info(f'INI file: {portable_settings_path}')
    Settings.set_filename(portable_settings_path)
    return portable_path, Settings()


def main():
    """
    The main function which parses command line options and then runs
    """
    args = parse_options()
    qt_args = ['--disable-web-security']
    # qt_args = []
    if args and args.loglevel.lower() in ['d', 'debug']:
        log.setLevel(logging.DEBUG)
    elif args and args.loglevel.lower() in ['w', 'warning']:
        log.setLevel(logging.WARNING)
    else:
        log.setLevel(logging.INFO)
    # Throw the rest of the arguments at Qt, just in case.
    qt_args.extend(args.rargs)
    # Bug #1018855: Set the WM_CLASS property in X11
    if not is_win() and not is_macosx():
        qt_args.append('OpenLP')
    elif is_macosx() and getattr(sys, 'frozen', False) and not os.environ.get('QTWEBENGINEPROCESS_PATH'):
        # Set the location to the QtWebEngineProcess binary, normally set by PyInstaller, but it moves around...
        os.environ['QTWEBENGINEPROCESS_PATH'] = str((AppLocation.get_directory(AppLocation.AppDir) / 'PySide6' /
                                                     'Qt6' / 'lib' / 'QtWebEngineCore.framework' / 'Versions' /
                                                     '6' / 'Helpers' / 'QtWebEngineProcess.app' / 'Contents' /
                                                     'MacOS' / 'QtWebEngineProcess').resolve())
    # Prevent the use of wayland, use xcb instead
    if is_wayland_compositor():
        qt_args.extend(['-platform', 'xcb'])
    # Initialise the resources
    qInitResources()
    # Initialise OpenLP
    app = OpenLP()
    Registry.create()
    QtWidgets.QApplication.setOrganizationName('OpenLP')
    QtWidgets.QApplication.setApplicationName('OpenLP')
    QtWidgets.QApplication.setOrganizationDomain('openlp.org')
    if args.portable:
        # This has to be done here so that we can load the settings before instantiating the application object
        QtWidgets.QApplication.setApplicationName('OpenLPPortable')
        portable_path, settings = setup_portable_settings(args.portablepath)
    else:
        settings = Settings()
    settings = check_for_variant_migration(settings)
    Registry().register('settings', settings)
    app.settings = settings
    if is_win():
        # If OpenLP is set to run in dark mode or automatic mode, this sets the title bar to dark.
        # This only takes effect when the system style is also set to dark mode.
        # The rest of the UI is configured later via set_windows_darkmode.
        # Note: With QDarkStyle, the title bar will still appear light.
        if is_ui_theme(UiThemes.DefaultLight) or (is_ui_theme(UiThemes.Automatic) and not is_ui_theme_dark()):
            qt_args.extend(['-platform', 'windows:darkmode=0'])
        else:
            qt_args.extend(['-platform', 'windows:darkmode=2'])
    # Doing HiDPI adjustments that need to be done before QCoreApplication instantiation.
    hidpi_mode = settings.value('advanced/hidpi mode')
    apply_dpi_adjustments_stage_qt(hidpi_mode, qt_args)
    # Instantiating QCoreApplication
    init_webview_custom_schemes()
    application = QtWidgets.QApplication(qt_args)
    application.setAttribute(QtCore.Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings, True)
    # Doing HiDPI adjustments that need to be done after QCoreApplication instantiation.
    apply_dpi_adjustments_stage_application(hidpi_mode, application)
    if is_win() and application.devicePixelRatio() > 1.0:
        # Increasing font size to match pixel ratio (Windows only)
        font = application.font()
        # font.setPointSizeF(font.pointSizeF() * application.devicePixelRatio())
        font.setPointSizeF(font.pointSizeF() * application.devicePixelRatio())
        application.setFont(font)
    verbose = getattr(args, 'verbose', False)
    cache_path = portable_path / 'Other' if args.portable else AppLocation.get_directory(AppLocation.CacheDir)
    set_up_logging(cache_path, verbose)
    set_up_web_engine_cache(cache_path / 'web_cache')
    if args.portable:
        log.info('Running portable')
        # Set our data path
        data_path = portable_path / 'Data'
        log.info(f'Data path: {data_path}')
        settings.setValue('advanced/data path', data_path)
        settings.setValue('advanced/is portable', True)
        settings.sync()
    settings.init_default_shortcuts()
    if settings.value('advanced/protect data directory'):
        # attempt to create a file lock
        app.data_dir_lock = FileLock(AppLocation.get_data_path(), get_version()['full'])
        if not app.data_dir_lock.lock():
            # not good! A message will have been presented to the user explaining why we're quitting.
            sys.exit()
    else:
        app.data_dir_lock = None
    log.info(f'Arguments passed {args}')
    # Need settings object for the threads.
    settings_thread = Settings()
    Registry().register('settings_thread', settings_thread)
    Registry().register('application-qt', application)
    Registry().register('application', app)
    if args.display_custom_path:
        if (args.display_custom_path.startswith('http:') or args.display_custom_path.startswith('https:')):
            Registry().register('display_custom_url', args.display_custom_path)
        else:
            set_webview_display_path(args.display_custom_path)
    Registry().set_flag('no_web_server', args.no_web_server)
    application.setApplicationVersion(get_version()['version'])
    # Check if an instance of OpenLP is already running. Quit if there is a running instance and the user only wants one
    server = Server()
    if server.is_another_instance_running():
        app.is_already_running()
        server.post_to_server(qt_args)
        sys.exit()
    else:
        server.start_server()
        app.server = server
    # If the custom data path is missing and the user wants to restore the data path, quit OpenLP.
    if app.is_data_path_missing():
        server.close_server()
        sys.exit()
    # Do a backup
    if not backup_if_version_changed(settings):
        # Backup failed, stop before we damage data.
        server.close_server()
        sys.exit()
    # First time checks in settings
    if not settings.value('core/has run wizard'):
        if not FirstTimeLanguageForm().exec():
            # if cancel then stop processing
            server.close_server()
            sys.exit()
    # i18n Set Language
    language = LanguageManager.get_language()
    translators = LanguageManager.get_translators(language)
    for translator in translators:
        if not translator.isEmpty():
            application.installTranslator(translator)
    if not translators:
        log.debug('Could not find translators.')
    if args and not args.no_error_form:
        sys.excepthook = app.hook_exception
    sys.exit(app.run(qt_args, application))
