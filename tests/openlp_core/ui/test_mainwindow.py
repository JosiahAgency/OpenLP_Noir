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
Package to test openlp.core.ui.mainwindow package.
"""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from shutil import rmtree
from tempfile import mkdtemp

import pytest
from PySide6 import QtCore, QtWidgets, QtGui

from openlp.core.common.i18n import UiStrings
from openlp.core.common.registry import Registry
from openlp.core.display.screens import ScreenList
from openlp.core.lib.plugin import PluginStatus
from openlp.core.state import State
from openlp.core.ui.mainwindow import MainWindow
from tests.utils.constants import TEST_RESOURCES_PATH, RESOURCE_PATH


JSON_RECENT_FILES = ('[{"parts": ["/", "path", "to", "service-1.osz"], "json_meta": {"class": "Path", "version": 1}},'
                     '{"parts": ["/", "path", "to", "service-2.osz"], "json_meta": {"class": "Path", "version": 1}}]')

QT_QPA_PLATFORM = os.environ.get("QT_QPA_PLATFORM", "")


def _create_mock_action(parent, name, **kwargs):
    """
    Create a fake action with some "real" attributes
    """
    action = QtGui.QAction(parent)
    action.setObjectName(name)
    if kwargs.get('triggers'):
        action.triggered.connect(kwargs.pop('triggers'))
    return action


@pytest.fixture()
def main_window(state, settings, mocked_qapp):
    app = Registry().get('application')
    app.set_busy_cursor = MagicMock()
    app.set_normal_cursor = MagicMock()
    app.process_events = MagicMock()
    app.args = []
    Registry().set_flag('no_web_server', True)
    add_toolbar_action_patcher = patch('openlp.core.ui.mainwindow.create_action')
    mocked_add_toolbar_action = add_toolbar_action_patcher.start()
    mocked_add_toolbar_action.side_effect = _create_mock_action
    renderer_patcher = patch('openlp.core.display.render.Renderer')
    renderer_patcher.start()
    mocked_screen = MagicMock()
    mocked_screen.geometry.return_value = QtCore.QRect(0, 0, 1024, 768)
    mocked_qapp.screens = MagicMock()
    mocked_qapp.screens.return_value = [mocked_screen]
    mocked_qapp.primaryScreen = MagicMock()
    mocked_qapp.primaryScreen.return_value = mocked_screen
    ScreenList.create(mocked_qapp)
    mainwindow = MainWindow()
    mainwindow.activateWindow = MagicMock()
    yield mainwindow
    del mainwindow
    renderer_patcher.stop()
    add_toolbar_action_patcher.stop()


@pytest.fixture()
def main_window_reduced(settings, state):
    """
    Create the UI
    """
    Registry().set_flag('no_web_server', True)
    mocked_plugin = MagicMock()
    mocked_plugin.status = PluginStatus.Active
    mocked_plugin.icon = QtGui.QIcon()
    Registry().register('mock_plugin', mocked_plugin)
    State().add_service("mock", 1, is_plugin=True, status=PluginStatus.Active)
    # Mock classes and methods used by mainwindow.
    with patch('openlp.core.ui.mainwindow.SettingsForm'), \
            patch('openlp.core.ui.mainwindow.OpenLPDockWidget'), \
            patch('openlp.core.ui.mainwindow.QtCore.QTimer.singleShot'), \
            patch('openlp.core.ui.mainwindow.QtWidgets.QToolBox'), \
            patch('openlp.core.ui.mainwindow.QtWidgets.QMainWindow.addDockWidget'), \
            patch('openlp.core.ui.mainwindow.QtGui.QActionGroup'), \
            patch('openlp.core.ui.mainwindow.ServiceManager'), \
            patch('openlp.core.ui.mainwindow.ThemeManager'), \
            patch('openlp.core.ui.mainwindow.ProjectorManager'), \
            patch('openlp.core.ui.mainwindow.LogViewerPanel'), \
            patch('openlp.core.ui.mainwindow.HttpServer'), \
            patch('openlp.core.ui.mainwindow.WebSocketServer'), \
            patch('openlp.core.ui.mainwindow.PluginForm'), \
            patch('openlp.core.ui.mainwindow.create_action'), \
            patch('openlp.core.ui.mainwindow.add_actions'):
        return MainWindow()


def test_cmd_line_file(main_window):
    """
    Test that passing a service file from the command line loads the service.
    """
    # GIVEN a service as an argument to openlp
    service = os.path.join(TEST_RESOURCES_PATH, 'service', 'test.osz')

    # WHEN the argument is processed
    with patch.object(main_window.service_manager, 'load_file') as mocked_load_file:
        main_window.open_cmd_line_files([service])

    # THEN the service from the arguments is loaded
    mocked_load_file.assert_called_with(Path(service))


def test_cmd_line_file_encoded(main_window):
    """
    Test that passing a service file from the command line loads the service where extra encoded quotes are added
    """
    # GIVEN a service as an argument to openlp
    service_base = os.path.join(TEST_RESOURCES_PATH, 'service', 'test.osz')
    service = f'&quot;{service_base}&quot;'

    # WHEN the argument is processed
    with patch.object(main_window.service_manager, 'load_file') as mocked_load_file:
        main_window.open_cmd_line_files([service])

    # THEN the service from the arguments is loaded
    mocked_load_file.assert_called_with(Path(service_base))


def test_cmd_line_arg_no_service(main_window):
    """
    Test that passing no service file does nothing.
    """
    # GIVEN a command line argument for openlp
    args = ['--disable-web-security']

    # WHEN the argument is processed
    with patch.object(main_window.service_manager, 'load_file') as mocked_load_file:
        main_window.open_cmd_line_files(args)

        # THEN the file should not be opened
        assert mocked_load_file.called is False, 'load_file should not have been called'


def test_cmd_line_arg_not_service_file(main_window):
    """
    Test that passing a file that is not a service does nothing.
    """
    # GIVEN a non service file as an argument to openlp
    args = ['run_openlp.py']

    # WHEN the argument is processed
    with patch.object(main_window.service_manager, 'load_file') as mocked_load_file:
        main_window.open_cmd_line_files(args)

        # THEN the file should not be opened
        assert mocked_load_file.called is False, 'load_file should not have been called'


def test_cmd_line_arg_service_file_does_not_exist(main_window):
    """
    Test that passing a file that does not exist does nothing.
    """
    # GIVEN a service file that does not exist
    args = ['Service 2022-02-06.osz']

    # WHEN the argument is processed
    with patch.object(main_window.service_manager, 'load_file') as mocked_load_file:
        main_window.open_cmd_line_files(args)

        # THEN the file should not be opened
        assert mocked_load_file.called is False, 'load_file should not have been called'


def test_cmd_line_arg_other_args(main_window):
    """
    Test that passing a service file with other command line arguments still opens the file
    """
    # GIVEN a valid existing service file and a command line argument
    service_file = os.path.join(TEST_RESOURCES_PATH, 'service', 'test.osz')
    args = ['--disable-web-security', service_file]

    # WHEN the argument is processed
    with patch.object(main_window.service_manager, 'load_file') as mocked_load_file:
        main_window.open_cmd_line_files(args)

        # THEN the file should not be opened
        assert mocked_load_file.called is True, 'load_file should have been called'
        mocked_load_file.assert_called_with(Path(service_file))


@patch('openlp.core.ui.mainwindow.resolve')
def test_cmd_line_filename_with_spaces(mocked_resolve, main_window):
    """
    Test that a service file with spaces that split across arguments loads the file properly
    """
    # GIVEN a set of arguments with a file separated by spaces
    mocked_path_is_file = MagicMock(**{'is_file.return_value': True, 'suffix': '.osz'})
    mocked_resolve.side_effect = [FileNotFoundError, FileNotFoundError, FileNotFoundError, mocked_path_is_file]
    args = ['Service', '2022-02-06.osz']

    # WHEN the argument is processed
    with patch.object(main_window.service_manager, 'load_file') as mocked_load_file:
        main_window.open_cmd_line_files(args)

        # THEN the file should be looked for
        assert mocked_resolve.call_count == 4
        mocked_load_file.assert_called_with(mocked_path_is_file)


@patch('openlp.core.ui.mainwindow.resolve')
def test_cmd_line_filename_with_spaces_and_security(mocked_resolve, main_window):
    """
    Test that passing a service file with spaces and a command line argument loads properly
    """
    # GIVEN a set of arguments with a file separated by spaces
    mocked_path_is_file = MagicMock(**{'is_file.return_value': True, 'suffix': '.osz'})
    mocked_resolve.side_effect = [FileNotFoundError, FileNotFoundError, FileNotFoundError, mocked_path_is_file]
    args = ['--disable-web-security', 'Service', '2022-02-06.osz']

    # WHEN the argument is processed
    with patch.object(main_window.service_manager, 'load_file') as mocked_load_file:
        main_window.open_cmd_line_files(args)

        # THEN the file should be looked for
        assert mocked_resolve.call_count == 4
        mocked_load_file.assert_called_with(mocked_path_is_file)


def test_main_window_title(main_window):
    """
    Test that running a new instance of OpenLP set the window title correctly
    """
    # GIVEN a newly opened OpenLP instance

    # WHEN no changes are made to the service

    # THEN the main window's title should be the same as the OpenLP string in the UiStrings class
    assert main_window.windowTitle() == UiStrings().OpenLP, \
        'The main window\'s title should be the same as the OpenLP string in UiStrings class'


def test_set_service_modified(main_window):
    """
    Test that when setting the service's title the main window's title is set correctly
    """
    # GIVEN a newly opened OpenLP instance

    # WHEN set_service_modified is called with with the modified flag set true and a file name
    main_window.set_service_modified(True, 'test.osz')

    # THEN the main window's title should be set to the
    assert main_window.windowTitle(), '%s - %s*' % (UiStrings().OpenLP, 'test.osz') == \
        'The main window\'s title should be set to "<the contents of UiStrings().OpenLP> - test.osz*"'


def test_set_service_unmodified(main_window):
    """
    Test that when setting the service's title the main window's title is set correctly
    """
    # GIVEN a newly opened OpenLP instance

    # WHEN set_service_modified is called with with the modified flag set False and a file name
    main_window.set_service_modified(False, 'test.osz')

    # THEN the main window's title should be set to the
    assert main_window.windowTitle(), '%s - %s' % (UiStrings().OpenLP, 'test.osz') == \
        'The main window\'s title should be set to "<the contents of UiStrings().OpenLP> - test.osz"'


@pytest.mark.skipif(QT_QPA_PLATFORM in ['offscreen', 'wayland'],
                    reason='This test does not work with the offscreen or wayland backends')
def test_load_settings_position_valid(main_window, settings):
    """
    Test that the position of the main window is restored when it's valid
    """
    # GIVEN a newly opened OpenLP instance, mocked screens and settings for a valid window position
    # mock out some other calls in load_settings()
    main_window.control_splitter = MagicMock()
    main_window._live_controller = MagicMock()
    main_window._preview_controller = MagicMock()
    # set up a window position and geometry to use in the settings
    main_window.move(QtCore.QPoint(10, 10))
    main_window.resize(1000, 500)
    # need to call show() to ensure the geometry works as expected
    # unfortunately this seems to work on Windows only, not on linux
    main_window.show()
    main_window.hide()
    # store the values in the settings
    settings.setValue('user interface/main window position', main_window.pos())
    settings.setValue('user interface/main window geometry', main_window.saveGeometry())
    settings.setValue('user interface/main window state', main_window.saveState())
    # change the position and size - then we can test if load_settings() sets it back correctly
    main_window.move(QtCore.QPoint(20, 20))
    main_window.resize(500, 300)

    # WHEN the settings are loaded
    main_window.load_settings()

    # THEN the main window's position and geometry should be set to the saved setting
    # on linux the tests works for the x position only
    assert main_window.pos().x() == 10


@pytest.mark.skipif(QT_QPA_PLATFORM == 'offscreen', reason='This test does not work with the offscreen backend')
def test_load_settings_position_invalid(main_window, settings):
    """
    Test that the position of the main window is not restored when it's invalid, but rather set to (0, 0)
    """
    # GIVEN a newly opened OpenLP instance, mocked screens and settings for a valid window position
    # mock out some other calls in load_settings()
    main_window.control_splitter = MagicMock()
    main_window._live_controller = MagicMock()
    main_window._preview_controller = MagicMock()
    # set up a window position outside the parameters of the main_window fixture
    # this can represent a monitor positioned above the primary display, but which has been unplugged
    main_window.move(QtCore.QPoint(-100, -800))
    main_window.resize(1000, 500)
    # need to call show() to ensure the geometry works as expected (works on Windows, but not linux)
    main_window.show()
    main_window.hide()
    # store the values in the settings
    settings.setValue('user interface/main window position', main_window.pos())
    settings.setValue('user interface/main window geometry', main_window.saveGeometry())
    settings.setValue('user interface/main window state', main_window.saveState())
    # change the position and size
    main_window.move(QtCore.QPoint(20, 20))
    main_window.resize(500, 300)

    # WHEN the settings are loaded
    main_window.load_settings()

    # THEN the main window's position should be a valid position such as (0, 0) or another valid postion,
    #      depending on the window system.
    # -202 is the value our GitLab CI/CD pipeline returns.
    assert main_window.pos().x() >= -202
    assert main_window.pos().y() >= -0


def test_mainwindow_configuration(main_window):
    """
    Check that the Main Window initialises the Registry Correctly
    """
    # GIVEN: A built main window

    # WHEN: you check the started functions

    # THEN: the following registry functions should have been registered
    expected_service_list = ['settings', 'settings_thread', 'application', 'main_window', 'settings_form',
                             'service_manager', 'theme_manager', 'projector_manager', 'http_server',
                             'authentication_token', 'web_socket_server']
    expected_functions_list = ['bootstrap_post_set_up', 'bootstrap_initialise', 'bootstrap_completion',
                               'config_screen_changed', 'theme_change_global']
    assert list(Registry().service_list.keys()) == expected_service_list, \
        'The service list should have been {}'.format(Registry().service_list.keys())
    assert list(Registry().functions_list.keys()) == expected_functions_list, \
        'The function list should have been {}'.format(Registry().functions_list.keys())
    assert 'application' in Registry().service_list, 'The application should have been registered.'
    assert 'main_window' in Registry().service_list, 'The main_window should have been registered.'
    assert 'settings' in Registry().service_list, 'The settings should have been registered.'


def test_projector_manager_hidden_on_startup(main_window):
    """
    Test that the projector manager is hidden on startup
    """
    # GIVEN: A built main window
    # WHEN: OpenLP is started
    # THEN: The projector manager should be hidden
    assert main_window.projector_manager_dock.isVisible() is False


def test_on_search_shortcut_triggered_shows_media_manager(main_window):
    """
    Test that the media manager is made visible when the search shortcut is triggered
    """
    # GIVEN: A build main window set up for testing
    with patch.object(main_window, 'media_manager_dock') as mocked_media_manager_dock, \
            patch.object(main_window, 'media_tool_box') as mocked_media_tool_box:
        mocked_media_manager_dock.isVisible.return_value = False
        mocked_media_tool_box.currentWidget.return_value = None

        # WHEN: The search shortcut is triggered
        main_window.on_search_shortcut_triggered()

        # THEN: The media manager dock is made visible
        mocked_media_manager_dock.setVisible.assert_called_with(True)


def test_on_search_shortcut_triggered_focuses_widget(main_window):
    """
    Test that the focus is set on the widget when the search shortcut is triggered
    """
    # GIVEN: A build main window set up for testing
    with patch.object(main_window, 'media_manager_dock') as mocked_media_manager_dock, \
            patch.object(main_window, 'media_tool_box') as mocked_media_tool_box:
        mocked_media_manager_dock.isVisible.return_value = True
        mocked_widget = MagicMock()
        mocked_media_tool_box.currentWidget.return_value = mocked_widget

        # WHEN: The search shortcut is triggered
        main_window.on_search_shortcut_triggered()

        # THEN: The media manager dock is made visible
        assert 0 == mocked_media_manager_dock.setVisible.call_count
        mocked_widget.on_focus.assert_called_with()


@patch('openlp.core.ui.mainwindow.FirstTimeForm')
@patch('openlp.core.ui.mainwindow.QtWidgets.QMessageBox.warning')
def test_on_first_time_wizard_clicked_show_projectors_after(mocked_warning, MockWizard, main_window):
    """Test that the projector manager is shown after the FTW is run"""
    # GIVEN: Main_window, patched things, patched "Yes" as confirmation to re-run wizard, settings to True.
    mocked_warning.return_value = QtWidgets.QMessageBox.StandardButton.Yes
    MockWizard.return_value.was_cancelled = False
    main_window.settings.setValue('projector/show after wizard', True)

    with patch.object(main_window, 'projector_manager_dock') as mocked_dock, \
            patch.object(Registry(), 'execute'), patch.object(main_window, 'theme_manager_contents'):
        # WHEN: on_first_time_wizard_clicked is called
        main_window.on_first_time_wizard_clicked()

    # THEN: projector_manager_dock.setVisible should had been called once
    mocked_dock.setVisible.assert_called_once_with(True)


@patch('openlp.core.ui.mainwindow.FirstTimeForm')
@patch('openlp.core.ui.mainwindow.QtWidgets.QMessageBox.warning')
def test_on_first_time_wizard_clicked_hide_projectors_after(mocked_warning, MockWizard, main_window):
    """Test that the projector manager is hidden after the FTW is run"""
    # GIVEN: Main_window, patched things, patched "Yes" as confirmation to re-run wizard, settings to False.
    mocked_warning.return_value = QtWidgets.QMessageBox.StandardButton.Yes
    MockWizard.return_value.was_cancelled = False
    main_window.settings.setValue('projector/show after wizard', False)

    # WHEN: on_first_time_wizard_clicked is called
    with patch.object(main_window, 'projector_manager_dock') as mocked_dock, \
            patch.object(Registry(), 'execute'), patch.object(main_window, 'theme_manager_contents'):
        main_window.on_first_time_wizard_clicked()

    # THEN: projector_manager_dock.setVisible should had been called once
    mocked_dock.setVisible.assert_called_once_with(False)


def test_increment_progress_bar_default_increment(main_window):
    """
    Test that increment_progress_bar increments the progress bar by 1 when called without the `increment` arg.
    """
    # GIVEN: A mocked progress bar
    with patch.object(main_window, 'load_progress_bar', **{'value.return_value': 0}) as mocked_progress_bar:

        # WHEN: Calling increment_progress_bar without the `increment` arg
        main_window.increment_progress_bar()

    # THEN: The progress bar value should have been incremented by 1
    mocked_progress_bar.setValue.assert_called_once_with(1)


def test_increment_progress_bar_custom_increment(main_window):
    """
    Test that increment_progress_bar increments the progress bar by the `increment` arg when called with the
    `increment` arg with a set value.
    """
    # GIVEN: A mocked progress bar
    with patch.object(main_window, 'load_progress_bar', **{'value.return_value': 0}) as mocked_progress_bar:

        # WHEN: Calling increment_progress_bar with `increment` set to 10
        main_window.increment_progress_bar(increment=10)

    # THEN: The progress bar value should have been incremented by 10
    mocked_progress_bar.setValue.assert_called_once_with(10)


def test_eventFilter(main_window):
    """
    Test the reimplemented event method
    """
    # GIVEN: A file path and a QEvent.
    file_path = str(RESOURCE_PATH / 'church.jpg')
    mocked_file_method = MagicMock(return_value=file_path)
    event = QtCore.QEvent(QtCore.QEvent.Type.FileOpen)
    event.file = mocked_file_method

    # WHEN: Call the vent method.
    result = main_window.eventFilter(MagicMock(), event)

    # THEN: The path should be inserted.
    assert result is True, "The method should have returned True."
    mocked_file_method.assert_called_once_with()
    assert Registry().get('application').args[0] == file_path, "The path should be in args."


@patch('openlp.core.ui.mainwindow.is_macosx')
def test_application_activate_event(mocked_is_macosx, main_window):
    """
    Test that clicking on the dock icon on Mac OS X restores the main window if it is minimized
    """
    # GIVEN: Mac OS X and an ApplicationActivate event
    mocked_is_macosx.return_value = True
    event = QtCore.QEvent(QtCore.QEvent.Type.ApplicationActivate)
    main_window.showMinimized()

    # WHEN: The icon in the dock is clicked
    result = main_window.eventFilter(MagicMock(), event)

    # THEN:
    assert result is True, "The method should have returned True."
    assert main_window.isMinimized() is False


@patch('openlp.core.app.QtWidgets.QMessageBox.critical')
@patch('openlp.core.common.applocation.AppLocation.get_data_path')
@patch('openlp.core.common.applocation.AppLocation.get_directory')
def test_change_data_directory(mocked_get_directory, mocked_get_data_path, mocked_critical_box, main_window):
    """
    Test that changing the data directory works if the folder already exists
    """
    # GIVEN: an existing old and new data directory.
    temp_folder = Path(mkdtemp())
    mocked_get_data_path.return_value = temp_folder
    main_window.copy_data = True
    temp_new_data_folder = Path(mkdtemp())
    main_window.new_data_path = temp_new_data_folder

    # WHEN: running change_data_directory
    result = main_window.change_data_directory()

    # THEN: No error shouuld have occured
    assert result is not False
    mocked_critical_box.assert_not_called()

    # Clean up
    rmtree(temp_folder)
    rmtree(temp_new_data_folder)


def test_restore_current_media_manager_item(main_window_reduced):
    """
    Regression test for bug #1152509.
    """
    # save current plugin: True; current media plugin: 2
    main_window_reduced.settings.setValue('advanced/save current plugin', True)
    main_window_reduced.settings.setValue('advanced/current media plugin', 2)

    # WHEN: Call the restore method.
    main_window_reduced.restore_current_media_manager_item()

    # THEN: The current widget should have been set.
    main_window_reduced.media_tool_box.setCurrentIndex.assert_called_with(2)


def test_set_lock_panel_locked(main_window_reduced):
    """
    Projector Manager enable UI options -  bug #1390702
    """
    # GIVEN: A mocked projector manager dock item:
    # WHEN: main_window.set_lock_panel is called
    main_window_reduced.set_lock_panel(True)

    # THEN: Projector manager dock should have been called with disable UI features
    no_dock_features = QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
    main_window_reduced.theme_manager_dock.setFeatures.assert_called_with(no_dock_features)
    main_window_reduced.service_manager_dock.setFeatures.assert_called_with(no_dock_features)
    main_window_reduced.media_manager_dock.setFeatures.assert_called_with(no_dock_features)
    main_window_reduced.projector_manager_dock.setFeatures.assert_called_with(no_dock_features)


def test_set_lock_panel_unlocked(main_window_reduced):
    """
    Projector Manager disable UI options -  bug #1390702
    """
    # GIVEN: A mocked projector manager dock item:
    # WHEN: main_window.lock_panel action is triggered
    main_window_reduced.set_lock_panel(False)

    # THEN: Projector manager dock should have been called with enable UI features
    all_dock_features = (QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable |
                         QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                         QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)
    main_window_reduced.theme_manager_dock.setFeatures.assert_called_with(all_dock_features)
    main_window_reduced.service_manager_dock.setFeatures.assert_called_with(all_dock_features)
    main_window_reduced.media_manager_dock.setFeatures.assert_called_with(all_dock_features)
    main_window_reduced.projector_manager_dock.setFeatures.assert_called_with(all_dock_features)


@patch('openlp.core.ui.mainwindow.MainWindow.open_cmd_line_files')
@patch('openlp.core.ui.mainwindow.MainWindow.set_view_mode')
def test_show_cmd_line_args(mocked_view_mode, mocked_open_cmd_line_files, main_window, settings):
    """Test that command line arguments are loaded on show"""
    # GIVEN: A newly opened OpenLP instance with some command line arguments
    main_window.application.args = ['-disable-web-security', 'new_file_name.osz']

    # WHEN: MainWindow.show() is called
    main_window.show()

    # THEN: The command line arguments are searched for a file name
    mocked_open_cmd_line_files.assert_called_once_with(main_window.application.args)


@patch('openlp.core.ui.mainwindow.MainWindow.set_view_mode')
def test_show_load_last_file(mocked_view_mode, main_window, settings):
    """Test that the last file opened is loaded on show"""
    # GIVEN: A newly opened OpenLP instance with some command line arguments
    main_window.service_manager_contents.load_last_file = MagicMock()
    main_window.settings.setValue('core/auto open', True)

    # WHEN: MainWindow.show() is called
    main_window.show()

    # THEN: The command line arguments are searched for a file name
    main_window.service_manager_contents.load_last_file.assert_called_once_with()


@patch('openlp.core.ui.mainwindow.MainWindow.set_view_mode')
def test_load_settings_custom_layout(mocked_view_mode, main_window, settings):
    """Test that the view mode is called with the correct parameters for default mode"""
    # GIVEN a newly opened OpenLP instance, mocked screens and settings for a valid window position
    # mock out some other calls in load_settings()
    main_window.control_splitter = MagicMock()
    main_window._live_controller = MagicMock()
    main_window._preview_controller = MagicMock()
    main_window.activateWindow = MagicMock()
    main_window.settings.setValue('core/view mode', 'default')
    main_window.settings.setValue('user interface/is preset layout', False)
    main_window.settings.setValue('user interface/show library', True)
    main_window.settings.setValue('user interface/show service', False)
    main_window.settings.setValue('user interface/show themes', True)
    main_window.settings.setValue('user interface/show projectors', False)
    main_window.settings.setValue('user interface/live panel', True)
    main_window.settings.setValue('user interface/preview panel', False)

    # WHEN: we call to show method
    main_window.show()

    # THEN:
    # The default mode should have been called.
    mocked_view_mode.assert_called_with(True, True, True, False, True, False)


@patch('openlp.core.ui.mainwindow.QtWidgets.QWidget.show')
@patch('openlp.core.ui.mainwindow.MainWindow.set_view_mode')
def test_load_settings_view_mode_default_mode(mocked_view_mode, mocked_show, main_window, settings):
    """
    Test that the view mode is called with the correct parameters for default mode
    """
    # GIVEN a newly opened OpenLP instance, mocked screens and settings for a valid window position
    # mock out some other calls in load_settings()
    main_window.control_splitter = MagicMock()
    main_window._live_controller = MagicMock()
    main_window._preview_controller = MagicMock()
    main_window.activateWindow = MagicMock()
    main_window.settings.setValue('core/view mode', 'default')
    main_window.settings.setValue('user interface/is preset layout', True)

    # WHEN: we call to show method
    main_window.show()

    # THEN:
    # The default mode should have been called.
    mocked_view_mode.assert_called_with(True, True, True, True, True, True)


@patch('openlp.core.ui.mainwindow.QtWidgets.QWidget.show')
@patch('openlp.core.ui.mainwindow.MainWindow.set_view_mode')
def test_load_settings_view_mode_setup_mode(mocked_view_mode, mocked_show, main_window, settings):
    """
    Test that the view mode is called with the correct parameters for setup mode

    Note: for some reason, only when the test is running, the QWidget.show() method resets the layout setting,
          so this is mocked out to prevent it from interferring in the loading of the view layout
    """
    # GIVEN a newly opened OpenLP instance, mocked screens and settings for a valid window position
    # mock out some other calls in load_settings()
    main_window.control_splitter = MagicMock()
    main_window._live_controller = MagicMock()
    main_window._preview_controller = MagicMock()
    main_window.settings.setValue('core/view mode', 'setup')
    main_window.settings.setValue('user interface/is preset layout', True)

    # WHEN: we call to show method
    main_window.show()

    # THEN:
    # The default mode should have been called.
    mocked_view_mode.assert_called_with(True, True, False, True, False, True)


@patch('openlp.core.ui.mainwindow.QtWidgets.QWidget.show')
@patch('openlp.core.ui.mainwindow.MainWindow.set_view_mode')
def test_load_settings_view_mode_live_mode(mocked_view_mode, mocked_show, main_window, settings):
    """
    Test that the view mode is called with the correct parameters for live mode

    Note: for some reason, only when the test is running, the QWidget.show() method resets the layout setting,
          so this is mocked out to prevent it from interferring in the loading of the view layout
    """
    # GIVEN a newly opened OpenLP instance, mocked screens and settings for a valid window position
    # mock out some other calls in load_settings()
    main_window.control_splitter = MagicMock()
    main_window._live_controller = MagicMock()
    main_window._preview_controller = MagicMock()
    main_window.settings.setValue('core/view mode', 'live')
    main_window.settings.setValue('user interface/is preset layout', True)

    # WHEN: we call to show method
    main_window.show()

    # THEN:
    # The default mode should have been called.
    mocked_view_mode.assert_called_with(False, True, False, False, True, True)


@patch('openlp.core.ui.mainwindow.MainWindow.set_view_mode')
def test_load_settings_view_mode_preview(mocked_view_mode, main_window, settings):
    """
    Test that the view mode is called with the correct parameters for default
    """
    # GIVEN a newly opened OpenLP instance, mocked screens and settings for a valid window position
    # mock out some other calls in load_settings()
    main_window.control_splitter = MagicMock()
    main_window._live_controller = MagicMock()
    main_window._preview_controller = MagicMock()
    main_window.activateWindow = MagicMock()
    main_window.settings.setValue('core/view mode', 'default')
    main_window.settings.setValue('user interface/is preset layout', False)
    main_window.settings.setValue('user interface/preview panel', False)

    # WHEN: we call to show method
    main_window.show()

    # THEN:
    # The default mode should have been called.
    mocked_view_mode.assert_called_with(True, True, True, False, True, True)


@patch('openlp.core.ui.mainwindow.MainWindow.set_view_mode')
def test_load_settings_view_mode_live(mocked_view_mode, main_window, settings):
    """
    Test that the view mode is called with the correct parameters for default
    """
    # GIVEN a newly opened OpenLP instance, mocked screens and settings for a valid window position
    # mock out some other calls in load_settings()
    main_window.control_splitter = MagicMock()
    main_window._live_controller = MagicMock()
    main_window._preview_controller = MagicMock()
    main_window.activateWindow = MagicMock()
    main_window.settings.setValue('core/view mode', 'default')
    main_window.settings.setValue('user interface/is preset layout', False)
    main_window.settings.setValue('user interface/live panel', False)

    # WHEN: we call to show method
    main_window.show()

    # THEN:
    # The default mode should have been called.
    mocked_view_mode.assert_called_with(True, True, True, True, False, True)


@patch('openlp.core.ui.mainwindow.QtCore.QTimer.singleShot')
@patch('openlp.core.ui.mainwindow.QtWidgets.QMessageBox.information')
def test_screen_changed_modal(mocked_information: MagicMock, mocked_timer_singleshot: MagicMock,
                              main_window: MainWindow):
    """
    Test that the screen changed modal is shown whether a 'config_screen_changed' event is dispatched
    """
    # GIVEN: a newly opened OpenLP instance, mocked screens and renderer
    main_window._live_controller = MagicMock()
    main_window._preview_controller = MagicMock()
    main_window._renderer = MagicMock()

    # WHEN: we trigger a 'config_screen_changed' event
    Registry().execute('config_screen_changed')

    # THEN: The modal should be called once
    mocked_information.assert_called_once()


@patch('openlp.core.ui.mainwindow.QtCore.QTimer.singleShot')
@patch('openlp.core.ui.mainwindow.QtWidgets.QMessageBox.information')
def test_screen_changed_modal_sets_timestamp_after_blocking_on_modal(mocked_information: MagicMock,
                                                                     mocked_timer_singleshot: MagicMock,
                                                                     main_window: MainWindow):
    """
    Test that the screen changed modal indicator is set back to True after showing warning message at the very end of
    the method, so that duplicate modals due to event spamming on 'config_screen_changed' is mitigated.
    """
    # GIVEN: a newly opened OpenLP instance, mocked screens, renderer and an special QMessageBox warning handler
    main_window._live_controller = MagicMock()
    main_window._preview_controller = MagicMock()
    main_window._renderer = MagicMock()

    # WHEN: we trigger a 'config_screen_changed' event
    Registry().execute('config_screen_changed')

    # THEN: main_window.should_show_screen_change_message should be true, indicating that the next time the screen is
    # changed the warning message will be displayed again
    mocked_information.assert_called_once()
    assert main_window.should_show_screen_change_message is True


@patch('openlp.core.ui.mainwindow.QtWidgets.QMessageBox.critical')
@patch('openlp.core.ui.mainwindow.FileDialog')
@patch('openlp.core.ui.mainwindow.shutil')
@patch('openlp.core.ui.mainwindow.Settings')
def test_on_settings_import_item_clicked(mock_settings, mock_shutil, mock_dialog, mock_crit, main_window_reduced):
    """
    Check we don't attempt to import incompatible settings from the future
    """
    # GIVEN: a
    settings_instance = MagicMock()
    mock_settings.return_value = settings_instance
    mock_dialog.getOpenFileName.return_value = [MagicMock(name='bob'), '']
    settings_instance.from_future.return_value = True
    Registry().register('plugin_manager', MagicMock())
    mock_crit.return_value = True

    # WHEN: the function is called
    main_window_reduced.on_settings_import_item_clicked()

    # THEN: The from_future should have been checked, but code should not have started to copy values
    settings_instance.from_future.assert_called_once_with()
    settings_instance.value.assert_not_called()


@patch('openlp.core.ui.mainwindow.Path')
@patch('openlp.core.ui.mainwindow.add_actions')
@patch('openlp.core.ui.mainwindow.create_action')
def test_update_recent_files_menu(mocked_create_action, mocked_add_actions, MockPath, settings, registry,
                                  main_window_reduced):
    """Test that the update_recent_files_menu() method works correctly"""
    # GIVEN: A mocked settings object, and some other fixtures
    MockPath.return_value.is_file.side_effect = [False, True]
    settings.setValue('advanced/recent file count', 5)
    main_window_reduced.recent_files = [None, '/fake/path', Path('/path/to/real/file')]
    main_window_reduced.recent_files_menu = MagicMock()

    # WHEN: update_recent_files_menu() is called
    main_window_reduced.update_recent_files_menu()

    # THEN: There should be no errors
    assert mocked_create_action.call_count == 2


@patch('openlp.core.ui.mainwindow.Path')
@patch('openlp.core.ui.mainwindow.add_actions')
@patch('openlp.core.ui.mainwindow.create_action')
def test_update_recent_files_menu_as_string(mocked_create_action, mocked_add_actions, MockPath, settings, registry,
                                            main_window_reduced):
    """Test that the update_recent_files_menu() method works correctly when the entry is a string instead of a list"""
    # GIVEN: A mocked settings object, and some other fixtures
    MockPath.return_value.is_file.side_effect = [False, True]
    settings.setValue('advanced/recent file count', 5)
    main_window_reduced.recent_files = JSON_RECENT_FILES
    main_window_reduced.recent_files_menu = MagicMock()

    # WHEN: update_recent_files_menu() is called
    main_window_reduced.update_recent_files_menu()

    # THEN: There should be no errors
    assert mocked_create_action.call_count == 2


@patch('openlp.core.ui.mainwindow.Path')
@patch('openlp.core.ui.mainwindow.add_actions')
@patch('openlp.core.ui.mainwindow.create_action')
def test_update_recent_files_menu_as_list_with_string(mocked_create_action, mocked_add_actions, MockPath, settings,
                                                      registry, main_window_reduced):
    """Test that the update_recent_files_menu() method works correctly when the entry is a string instead of a list"""
    # GIVEN: A mocked settings object, and some other fixtures
    MockPath.return_value.is_file.side_effect = [False, True]
    settings.setValue('advanced/recent file count', 5)
    main_window_reduced.recent_files = [JSON_RECENT_FILES]
    main_window_reduced.recent_files_menu = MagicMock()

    # WHEN: update_recent_files_menu() is called
    main_window_reduced.update_recent_files_menu()

    # THEN: There should be no errors
    assert mocked_create_action.call_count == 2


@patch('openlp.core.ui.mainwindow.QtWidgets.QProgressDialog')
def test_show_wait_dialog(MockProcessDialog, main_window_reduced):
    """Test that the show wait dialog context manager works correctly"""
    # GIVEN: A mocked out QProgressDialog and a minimal main window
    mocked_wait_dialog = MagicMock()
    MockProcessDialog.return_value = mocked_wait_dialog

    # WHEN: Calling _show_wait_dialog()
    with main_window_reduced._show_wait_dialog('Test', 'This is a test'):
        pass

    # THEN: The correct methods should have been called
    MockProcessDialog.assert_called_once_with('This is a test', '', 0, 0, main_window_reduced)
    mocked_wait_dialog.setWindowTitle.assert_called_once_with('Test')
    mocked_wait_dialog.setWindowFlag.assert_called_once_with(QtCore.Qt.WindowContextHelpButtonHint, False)
    mocked_wait_dialog.setWindowModality.assert_called_once_with(QtCore.Qt.WindowModal)
    mocked_wait_dialog.setAutoClose.assert_called_once_with(False)
    mocked_wait_dialog.setCancelButton.assert_called_once_with(None)
    mocked_wait_dialog.show.assert_called_once_with()
    mocked_wait_dialog.close.assert_called_once_with()


@patch('openlp.core.ui.mainwindow.QtWidgets.QApplication')
def test_wait_for_threads(MockApp, main_window_reduced):
    """Test that the wait_for_threads() method correctly stops the threads"""
    # GIVEN: A mocked application, and a reduced main window
    mocked_http_thread = MagicMock()
    mocked_http_thread.isRunning.side_effect = [True, True, False, False]
    mocked_http_worker = MagicMock()
    mocked_http_worker.stop = MagicMock()
    main_window_reduced.application.worker_threads = {
        'http': {'thread': mocked_http_thread, 'worker': mocked_http_worker}
    }

    # WHEN: _wait_for_threads() is called
    main_window_reduced._wait_for_threads()

    # THEN: The correct methods should have been called
    assert MockApp.processEvents.call_count == 2, 'processEvents() should have been called twice'
    mocked_http_worker.stop.assert_called_once()
    assert mocked_http_thread.isRunning.call_count == 4, 'isRunning() should have been called 4 times'
    mocked_http_thread.wait.assert_called_once_with(100)


@patch('openlp.core.ui.mainwindow.QtWidgets.QApplication')
def test_wait_for_threads_no_threads(MockApp, main_window_reduced):
    """Test that the wait_for_threads() method exits early when there are no threads"""
    # GIVEN: A mocked application, and a reduced main window
    main_window_reduced.application.worker_threads = {}

    # WHEN: _wait_for_threads() is called
    main_window_reduced._wait_for_threads()

    # THEN: The correct methods should have been called
    assert MockApp.processEvents.call_count == 0, 'processEvents() should not have been called'


@patch('openlp.core.ui.mainwindow.QtWidgets.QApplication')
def test_wait_for_threads_disappearing_thread(MockApp, main_window_reduced):
    """Test that the wait_for_threads() method correctly ignores threads that resolve themselves"""
    # GIVEN: A mocked application, and a reduced main window
    # WHEN: _wait_for_threads() is called
    with patch.object(main_window_reduced.application, 'worker_threads') as worker_threads_mock:
        worker_threads_mock.keys.side_effect = [['http'], []]
        main_window_reduced._wait_for_threads()

    # THEN: The correct methods should have been called
    assert MockApp.processEvents.call_count == 1, 'processEvents() should have only been called once'


@patch('openlp.core.ui.mainwindow.QtWidgets.QApplication')
def test_wait_for_threads_stuck_thread(MockApp, main_window_reduced):
    """Test that the wait_for_threads() method correctly stops the threads"""
    # GIVEN: A mocked application, and a reduced main window
    mocked_http_thread = MagicMock()
    mocked_http_thread.isRunning.return_value = True
    mocked_http_worker = MagicMock()
    mocked_http_worker.stop = MagicMock()
    main_window_reduced.application.worker_threads = {
        'http': {'thread': mocked_http_thread, 'worker': mocked_http_worker}
    }

    # WHEN: _wait_for_threads() is called
    main_window_reduced._wait_for_threads()

    # THEN: The correct methods should have been called
    assert MockApp.processEvents.call_count == 51, 'processEvents() should have been called 51 times'
    mocked_http_worker.stop.assert_called_once()
    assert mocked_http_thread.isRunning.call_count == 53, 'isRunning() should have been called 53 times'
    mocked_http_thread.wait.assert_called_with(100)
    mocked_http_thread.terminate.assert_called_once()


@patch('openlp.core.ui.mainwindow.QtWidgets.QApplication')
def test_wait_for_threads_runtime_error(MockApp, main_window_reduced):
    """Test that the wait_for_threads() method handles a runtime error"""
    # GIVEN: A mocked application, and a reduced main window
    mocked_http_thread = MagicMock()
    mocked_http_thread.isRunning.side_effect = RuntimeError
    mocked_http_worker = MagicMock()
    mocked_http_worker.stop = MagicMock()
    main_window_reduced.application.worker_threads = {
        'http': {'thread': mocked_http_thread, 'worker': mocked_http_worker}
    }

    # WHEN: _wait_for_threads() is called
    main_window_reduced._wait_for_threads()

    # THEN: The correct methods should have been called
    assert MockApp.processEvents.call_count == 1, 'processEvents() should have been called once'
    mocked_http_worker.stop.assert_called_once()
    assert mocked_http_thread.isRunning.call_count == 1, 'isRunning() should have been called once'
    mocked_http_thread.wait.assert_not_called()
    mocked_http_thread.terminate.assert_not_called()
