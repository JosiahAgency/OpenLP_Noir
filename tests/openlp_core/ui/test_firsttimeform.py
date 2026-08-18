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
Package to test the openlp.core.ui.firsttimeform package.
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, call, patch, DEFAULT

from PySide6 import QtCore, QtWidgets, QtTest

from openlp.core.app import OpenLP
from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings
from openlp.core.ui.firsttimeform import FirstTimeForm, ThemeListWidgetItem
from openlp.core.ui.firsttimewizard import RemotePage, ThemeListWidget
from openlp.core.ui.icons import UiIcons


INVALID_CONFIG = """
{
  "_comments": "The most recent version should be added to https://openlp.org/files/frw/download_3.0.json",
  "_meta": {
}
"""

sample_theme_data = {'file_name': 'BlueBurst.otz', 'sha256': 'sha_256_hash',
                     'thumbnail': 'BlueBurst.png', 'title': 'Blue Burst'}


@pytest.fixture()
def ftf_app(registry: Registry, qapp: OpenLP):
    Registry().register('application', qapp)


@pytest.fixture()
def download_env(registry: Registry):
    download_worker_patcher = patch('openlp.core.ui.firsttimeform.DownloadWorker')
    run_thread_patcher = patch('openlp.core.ui.firsttimeform.run_thread')
    mocked_download_worker = download_worker_patcher.start()
    mocked_run_thread = run_thread_patcher.start()
    yield mocked_download_worker, mocked_run_thread
    download_worker_patcher.stop()
    run_thread_patcher.stop()


@pytest.fixture()
def mocked_set_icon(mock_settings):
    move_to_thread_patcher = patch('openlp.core.ui.firsttimeform.DownloadWorker.moveToThread').start()
    set_icon_patcher = patch('openlp.core.ui.firsttimeform.ThemeListWidgetItem.setIcon').start()
    q_thread_patcher = patch('openlp.core.ui.firsttimeform.QtCore.QThread').start()
    mocked_app = MagicMock()
    mocked_app.worker_threads = {}
    mocked_main_window = MagicMock()
    Registry().remove('application')
    Registry().register('application', mocked_app)
    Registry().register('main_window', mocked_main_window)
    yield set_icon_patcher
    move_to_thread_patcher.stop()
    set_icon_patcher.stop()
    q_thread_patcher.stop()


def test_init_sample_data(download_env, mock_settings):
    """
    Test that the theme data is loaded correctly in to a ThemeListWidgetItem object when instantiated
    """
    # GIVEN: A sample theme dictionary object
    # WHEN: Creating an instance of `ThemeListWidgetItem`
    mocked_download_worker = download_env[0]
    instance = ThemeListWidgetItem('url', sample_theme_data, MagicMock())

    # THEN: The data should have been set correctly
    assert instance.file_name == 'BlueBurst.otz'
    assert instance.sha256 == 'sha_256_hash'
    assert instance.text() == 'Blue Burst'
    assert instance.toolTip() == 'Blue Burst'
    mocked_download_worker.assert_called_once_with('url', 'BlueBurst.png')


def test_init_download_worker(download_env, mock_settings):
    """
    Test that the `DownloadWorker` worker is set up correctly and that the thread is started.
    """
    # GIVEN: A sample theme dictionary object
    mocked_download_worker = download_env[0]
    mocked_run_thread = download_env[1]
    mocked_ftw = MagicMock(spec=FirstTimeForm)
    mocked_ftw.thumbnail_download_threads = []

    # WHEN: Creating an instance of `ThemeListWidgetItem`
    instance = ThemeListWidgetItem('url', sample_theme_data, mocked_ftw)

    # THEN: The `DownloadWorker` should have been set up and `run_thread` should have been handed the
    # download_failed/download_succeeded signals via `queued_connections` so they are wired up safely
    # on the GUI thread after the worker has been moved to its thread.
    mocked_download_worker.assert_called_once_with('url', 'BlueBurst.png')
    mocked_run_thread.assert_called_once()
    args, kwargs = mocked_run_thread.call_args
    assert args == (mocked_download_worker(), 'thumbnail_download_BlueBurst.png')
    assert kwargs['queued_connections'] == [
        (mocked_download_worker().download_failed, instance._thumbnail_receiver.on_failed),
        (mocked_download_worker().download_succeeded, instance._thumbnail_receiver.on_succeeded),
    ]
    assert mocked_ftw.thumbnail_download_threads == ['thumbnail_download_BlueBurst.png']


def test_firsttimeform_initialise(mock_settings):
    """
    Test if we can intialise the FirstTimeForm
    """
    # GIVEN: A First Time Wizard and an expected screen object
    frw = FirstTimeForm(None)
    expected_screens = MagicMock()

    # WHEN: The First Time Wizard is initialised
    frw.initialize(expected_screens)

    # THEN: The screens should be set up, and the default values initialised
    assert expected_screens == frw.screens, 'The screens should be correct'
    assert frw.has_web_access is True, 'The default value of self.web_access should be True'
    assert [] == frw.thumbnail_download_threads, 'The list of threads should be empty'
    assert frw.has_run_wizard is False, 'has_run_wizard should be False'


@patch('openlp.core.ui.firsttimeform.QtWidgets.QWizard.exec')
def test_firsttimeform_exec(mocked_qwizard_exec, mock_settings):

    # GIVEN: An instance of FirstTimeForm
    frw = FirstTimeForm(None)
    with patch.object(frw, 'set_defaults') as mocked_set_defaults:

        # WHEN: exec is called
        frw.exec()

        # THEN: The wizard should be reset and the exec methon on the super class should have been called
        mocked_set_defaults.assert_called_once()
        mocked_qwizard_exec.assert_called_once()


def test_set_defaults(mock_settings):
    """
    Test that the default values are set when set_defaults() is run
    """
    # GIVEN: An initialised FRW and a whole lot of stuff mocked out
    frw = FirstTimeForm(None)
    frw.initialize(MagicMock())
    mocked_settings = MagicMock()
    mocked_settings.value.side_effect = lambda key: {'core/has run wizard': False}[key]
    with patch.object(frw, 'restart') as mocked_restart, \
            patch.object(frw, 'currentIdChanged') as mocked_currentIdChanged, \
            patch.object(frw, 'theme_combo_box') as mocked_theme_combo_box, \
            patch.object(frw, 'songs_check_box') as mocked_songs_check_box, \
            patch.object(Registry, 'register_function') as mocked_register_function, \
            patch('openlp.core.ui.firsttimeform.gettempdir', return_value='temp') as mocked_gettempdir, \
            patch('openlp.core.ui.firsttimeform.create_paths') as mocked_create_paths, \
            patch.object(frw.application, 'set_normal_cursor'):
        mocked_theme_manager = MagicMock()
        Registry().register('theme_manager', mocked_theme_manager)
        Registry().remove('settings')
        Registry().register('settings', mocked_settings)

        # WHEN: The set_defaults() method is run
        frw.set_defaults()

        # THEN: The default values should have been set
        mocked_restart.assert_called_once()
        assert 'https://get.openlp.org/ftw/' == frw.web, 'The default URL should be set'
        mocked_currentIdChanged.connect.assert_called_once_with(frw.on_current_id_changed)
        mocked_register_function.assert_called_once_with('config_screen_changed', frw.screen_selection_widget.load)
        mocked_settings.value.assert_has_calls([call('core/has run wizard')])
        mocked_gettempdir.assert_called_once()
        mocked_create_paths.assert_called_once_with(Path('temp', 'openlp'))
        mocked_theme_combo_box.clear.assert_called_once()
        mocked_theme_manager.assert_not_called()
        mocked_songs_check_box.assert_not_called()


@patch('openlp.core.ui.firsttimeform.QtWidgets.QWizard.accept')
def test_accept_method(mocked_qwizard_accept):
    """
    Test the FirstTimeForm.accept method
    """
    # GIVEN: An instance of FirstTimeForm
    ftw = FirstTimeForm(None)
    with patch.object(ftw, '_set_plugin_status') as mocked_set_plugin_status, \
            patch.multiple(ftw, songs_check_box=DEFAULT, bible_check_box=DEFAULT, presentation_check_box=DEFAULT,
                           image_check_box=DEFAULT, media_check_box=DEFAULT, custom_check_box=DEFAULT,
                           song_usage_check_box=DEFAULT, alert_check_box=DEFAULT, egw_library_check_box=DEFAULT,
                           timer_check_box=DEFAULT, obs_studio_check_box=DEFAULT) \
            as mocked_check_boxes, \
            patch.object(ftw, 'screen_selection_widget') as mocked_screen_selection_widget:
        # WHEN: Calling accept
        ftw.accept()

        # THEN: The selected plugins should be enabled, the screen selection saved and the super method called
        mocked_set_plugin_status.assert_has_calls([
            call(mocked_check_boxes['songs_check_box'], 'songs/status'),
            call(mocked_check_boxes['bible_check_box'], 'bibles/status'),
            call(mocked_check_boxes['presentation_check_box'], 'presentations/status'),
            call(mocked_check_boxes['image_check_box'], 'images/status'),
            call(mocked_check_boxes['media_check_box'], 'media/status'),
            call(mocked_check_boxes['custom_check_box'], 'custom/status'),
            call(mocked_check_boxes['song_usage_check_box'], 'songusage/status'),
            call(mocked_check_boxes['alert_check_box'], 'alerts/status'),
            call(mocked_check_boxes['egw_library_check_box'], 'egwlibrary/status'),
            call(mocked_check_boxes['timer_check_box'], 'timer/status'),
            call(mocked_check_boxes['obs_studio_check_box'], 'obs_studio/status')
        ])
        mocked_screen_selection_widget.save.assert_called_once()
        mocked_qwizard_accept.assert_called_once()


def test_accept_method_theme_not_selected(mock_settings):
    """
    Test the FirstTimeForm.accept method when there is no default theme selected
    """
    # GIVEN: An instance of FirstTimeForm
    mock_settings = Registry().get('settings')
    frw = FirstTimeForm(None)
    with patch.object(frw, '_set_plugin_status'), patch.object(frw, 'screen_selection_widget'), \
            patch.object(frw, 'theme_combo_box', **{'currentIndex.return_value': -1}):     # type: ignore[call-overload]

        # WHEN: Calling accept and the currentIndex method of the theme_combo_box returns -1
        frw.accept()

        # THEN: OpenLP should not try to save a theme name
        mock_settings().setValue.assert_not_called()


@patch('openlp.core.ui.firsttimeform.QtWidgets.QWizard.reject')
@patch('openlp.core.ui.firsttimeform.time')
@patch('openlp.core.ui.firsttimeform.get_thread_worker')
@patch('openlp.core.ui.firsttimeform.is_thread_finished')
def test_reject_method(mocked_is_thread_finished, mocked_get_thread_worker,
                       mocked_time, mocked_qwizard_reject, ftf_app):
    """
    Test that the reject method shuts down the threads correctly
    """
    # GIVEN: A FRW, some mocked threads and workers (that isn't quite done) and other mocked stuff
    mocked_worker = MagicMock()
    mocked_get_thread_worker.return_value = mocked_worker
    mocked_is_thread_finished.side_effect = [False, True]
    frw = FirstTimeForm(None)
    frw.initialize(MagicMock())
    frw.thumbnail_download_threads = ['test_thread']
    with patch.object(frw.application, 'set_normal_cursor') as mocked_set_normal_cursor:

        # WHEN: the reject method is called
        frw.reject()

        # THEN: The right things should be called in the right order
        mocked_get_thread_worker.assert_called_once_with('test_thread')
        mocked_worker.cancel_download.assert_called_once()
        mocked_is_thread_finished.assert_called_with('test_thread')
        assert mocked_is_thread_finished.call_count == 2, 'isRunning() should have been called twice'
        mocked_time.sleep.assert_called_once_with(0.1)
        mocked_set_normal_cursor.assert_called_once()
        mocked_qwizard_reject.assert_called_once()


@patch('openlp.core.ui.firsttimeform.ProxyDialog')
def test_on_custom_button_clicked(mocked_proxy_dialog):
    """
    Test _on_custom_button when it is called whe the 'internet settings' (CustomButton1) button is not clicked.
    """
    # GIVEN: An instance of the FirstTimeForm
    frw = FirstTimeForm(None)

    # WHEN: Calling _on_custom_button_clicked with a different button to the 'internet settings button.
    frw._on_custom_button_clicked(QtWidgets.QWizard.WizardButton.CustomButton2)

    # THEN: The ProxyDialog should not be shown.
    mocked_proxy_dialog.assert_not_called()


@patch('openlp.core.ui.firsttimeform.ProxyDialog')
def test_on_custom_button_clicked_internet_settings(mocked_proxy_dialog):
    """
    Test _on_custom_button when it is called when the 'internet settings' (CustomButton1) button is clicked.
    """
    # GIVEN: An instance of the FirstTimeForm
    frw = FirstTimeForm(None)

    # WHEN: Calling _on_custom_button_clicked with the constant for the 'internet settings' button (CustomButton1)
    frw._on_custom_button_clicked(QtWidgets.QWizard.WizardButton.CustomButton1)

    # THEN: The ProxyDialog should be shown.
    mocked_proxy_dialog.assert_called_with(frw)
    mocked_proxy_dialog().retranslate_ui.assert_called_once()
    mocked_proxy_dialog().exec.assert_called_once()


@patch('openlp.core.ui.firsttimeform.QtWidgets.QMessageBox')
def test__parse_config_invalid_config(mocked_message_box):
    """
    Test `FirstTimeForm._parse_config` when called with invalid data
    """
    # GIVEN: An instance of `FirstTimeForm`
    first_time_form = FirstTimeForm(None)

    # WHEN: Calling _parse_config with a string containing invalid data
    result = first_time_form._parse_config(INVALID_CONFIG)

    # THEN: _parse_data should return False and the user should have should have been informed.
    assert result is False
    mocked_message_box.critical.assert_called_once_with(
        first_time_form, 'Invalid index file',
        'OpenLP was unable to read the resource index file. Please try again later.')


@patch('openlp.core.ui.firsttimeform.get_web_page')
@patch('openlp.core.ui.firsttimeform.QtWidgets.QMessageBox')
def test_network_error(mocked_message_box, mocked_get_web_page, mock_settings):
    """
    Test we catch a network error in First Time Wizard - bug 1409627
    """
    # GIVEN: Initial setup and mocks
    first_time_form = FirstTimeForm(None)
    first_time_form.initialize(MagicMock())
    mocked_get_web_page.side_effect = ConnectionError('')

    # WHEN: the First Time Wizard calls to get the initial configuration
    first_time_form._download_index()

    # THEN: the critical_error_message_box should have been called
    mocked_message_box.critical.assert_called_once_with(
        first_time_form, 'Network Error',
        'There was a network error attempting to connect to retrieve initial configuration information',
        mocked_message_box.StandardButton.Ok)


def test_accept_method_theme_selected(mock_settings):
    """
    Test the FirstTimeForm.accept method when a default theme is selected
    """
    # GIVEN: An instance of FirstTimeForm
    frw = FirstTimeForm(None)
    mock_settings.value.return_value = True

    with patch.object(frw, '_set_plugin_status'), \
            patch.object(                                           # type: ignore[call-overload]
                frw,
                'theme_combo_box',
                **{'currentIndex.return_value': 0, 'currentText.return_value': 'Test Item'}
            ), \
            patch.object(frw, 'screen_selection_widget'):

        # WHEN: Calling accept and the currentIndex method of the theme_combo_box returns 0
        frw.accept()

        # THEN: The 'currentItem' in the combobox should have been set as the default theme.
        mock_settings.setValue.assert_called_once_with('themes/global theme', 'Test Item')


def test_on_projectors_check_box_checked(mock_settings):
    """
    Test that the projector panel is shown when the checkbox in the first time wizard is checked
    """
    # GIVEN: A First Time Wizard and a mocked settings object
    frw = FirstTimeForm(None)
    mock_settings.value.return_value = True

    # WHEN: on_projectors_check_box_clicked() is called
    frw.on_projectors_check_box_clicked()

    # THEN: The visibility of the projects panel should have been set
    mock_settings.value.assert_called_once_with('projector/show after wizard')
    mock_settings.setValue.assert_called_once_with('projector/show after wizard', False)


def test_on_projectors_check_box_unchecked(mock_settings):
    """
    Test that the projector panel is shown when the checkbox in the first time wizard is checked
    """
    # GIVEN: A First Time Wizard and a mocked settings object
    frw = FirstTimeForm(None)
    mock_settings.value.return_value = False

    # WHEN: on_projectors_check_box_clicked() is called
    frw.on_projectors_check_box_clicked()

    # THEN: The visibility of the projects panel should have been set
    mock_settings.value.assert_called_once_with('projector/show after wizard')
    mock_settings.setValue.assert_called_once_with('projector/show after wizard', True)


def test_remote_page_get_can_download_remote(ftf_app):
    """
    Test that the `can_download_remote` property returns the correct value
    """
    # GIVEN: A RemotePage object with a mocked out download_checkbox
    remote_page = RemotePage(None)
    remote_page.download_checkbox = MagicMock(**{"isChecked.return_value": True})

    # WHEN: The can_download_remote property is accessed
    result = remote_page.can_download_remote

    # THEN: The result should be True
    assert result is True


def test_remote_page_set_can_download_remote(ftf_app):
    """
    Test that the `can_download_remote` property sets the correct value
    """
    # GIVEN: A RemotePage object with a mocked out download_checkbox
    remote_page = RemotePage(None)
    remote_page.download_checkbox = MagicMock()

    # WHEN: The can_download_remote property is set
    remote_page.can_download_remote = False

    # THEN: The result should be True
    remote_page.download_checkbox.setChecked.assert_called_once_with(False)


def test_remote_page_set_can_download_remote_not_bool(ftf_app):
    """
    Test that the `can_download_remote` property throws an exception when the value is not a boolean
    """
    # GIVEN: A RemotePage object with a mocked out download_checkbox
    remote_page = RemotePage(None)
    remote_page.download_checkbox = MagicMock()

    # WHEN: The can_download_remote property is set
    # THEN: An exception is thrown
    with pytest.raises(TypeError, match='Must be a bool'):
        remote_page.can_download_remote = 'not a bool'


def test_theme_list_widget_resize(ftf_app):
    """
    Test that the resizeEvent() method in the ThemeListWidget works correctly
    """
    # GIVEN: An instance of the ThemeListWidget
    widget = ThemeListWidget(None)

    # WHEN: resizeEvent() is called
    with patch.object(widget, 'viewport') as mocked_viewport, \
            patch.object(widget, 'setGridSize') as mocked_setGridSize:
        mocked_viewport.return_value.width.return_value = 600
        widget.resizeEvent(None)

    # THEN: Check that the correct calculations were done
    mocked_setGridSize.assert_called_once_with(QtCore.QSize(149, 140))


def test_failed_download(mocked_set_icon):
    """
    Test that icon get set to indicate a failure when `DownloadWorker` emits the download_failed signal
    """
    # GIVEN: An instance of `DownloadWorker`
    instance = ThemeListWidgetItem('url', sample_theme_data, MagicMock())       # noqa Overcome GC issue
    worker_threads = Registry().get('application').worker_threads               # type: ignore[union-attr]
    worker = worker_threads['thumbnail_download_BlueBurst.png']['worker']

    # WHEN: `DownloadWorker` emits the `download_failed` signal
    worker.download_failed.emit()
    # The signal is wired with Qt.QueuedConnection so we have to spin the event loop to deliver it.
    QtCore.QCoreApplication.processEvents()

    # THEN: Then the initial loading icon should have been replaced by the exception icon
    mocked_set_icon.assert_has_calls([call(UiIcons().get_icon_variant('picture')),
                                      call(UiIcons().get_icon_variant('exception'))])


@patch('openlp.core.ui.firsttimeform.build_icon')
def test_successful_download(mocked_build_icon, mocked_set_icon):
    """
    Test that the downloaded thumbnail is set as the icon when `DownloadWorker` emits the `download_succeeded`
    signal
    """
    # GIVEN: An instance of `DownloadWorker`
    instance = ThemeListWidgetItem('url', sample_theme_data, MagicMock())       # noqa Overcome GC issue
    worker_threads = Registry().get('application').worker_threads               # type: ignore[union-attr]
    worker = worker_threads['thumbnail_download_BlueBurst.png']['worker']
    test_path = Path('downlaoded', 'file')

    # WHEN: `DownloadWorker` emits the `download_succeeded` signal
    worker.download_succeeded.emit(test_path)
    # The signal is wired with Qt.QueuedConnection so we have to spin the event loop to deliver it.
    QtCore.QCoreApplication.processEvents()

    # THEN: An icon should have been built from the downloaded file and used to replace the loading icon
    mocked_build_icon.assert_called_once_with(test_path)
    mocked_set_icon.assert_has_calls([call(UiIcons().get_icon_variant('picture')), call(mocked_build_icon())])


def test_help(settings: Settings):
    """
    Test the help button
    """
    # GIVEN: A First Time Wizard and a patched help function
    ftw = FirstTimeForm(None)

    # WHEN: The Help button is clicked
    with patch.object(ftw, 'provide_help') as mocked_help:
        QtTest.QTest.mouseClick(ftw.button(QtWidgets.QWizard.WizardButton.HelpButton), QtCore.Qt.MouseButton.LeftButton)

    # THEN: The Help function should be called
    mocked_help.assert_called_once()
