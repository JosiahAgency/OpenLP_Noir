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
This module contains tests for the CCLI SongSelect importer.
It needs re-writing at some point to load real HTML pages from disk and
then test the behaviour based on those. That way if and when CCLI change
their page layout, changing the tests would just be a case of
re-downloading the HTML pages and changing the code to use the new layout.
"""
from unittest.mock import MagicMock, patch, sentinel

import pytest
from PySide6 import QtCore

from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings
from openlp.plugins.songs.forms.songselectform import SongSelectForm
from openlp.plugins.songs.lib import Song
from openlp.plugins.songs.lib.songselect import BASE_URL, LOGIN_PAGE, Pages, SongSelectImport
from tests.helpers.songfileimport import SongImportTestHelper
from tests.utils.constants import RESOURCE_PATH


TEST_PATH = RESOURCE_PATH / 'songs' / 'songselect'


@pytest.fixture
def importer(registry: Registry, settings: Settings) -> SongSelectImport:
    """An importer object"""
    yield SongSelectImport(MagicMock(), MagicMock())


@pytest.fixture
def form(registry: Registry, settings: Settings) -> SongSelectForm:
    """A SongSelectForm object"""
    # registry.get('application').setApplicationVersion('0.0')
    # registry.get('application').processEvents = lambda: None
    with patch('openlp.plugins.songs.forms.songselectdialog.QtWidgets.QGridLayout'), \
            patch('openlp.plugins.songs.forms.songselectdialog.WebEngineView'), \
            patch('openlp.plugins.songs.forms.songselectdialog.QtWidgets.QVBoxLayout'):
        yield SongSelectForm(None, MagicMock(), MagicMock())


def test_constructor(registry: Registry, settings: Settings):
    """
    Test that constructing a basic SongSelectImport object works correctly
    """
    # GIVEN: The SongSelectImporter class and a mocked out build_opener
    # WHEN: An object is instantiated
    importer = SongSelectImport(sentinel.db_manager, sentinel.webview)

    # THEN: The object should have the correct properties
    assert importer.db_manager is sentinel.db_manager, 'The db_manager should be set'
    assert importer.webview is sentinel.webview, 'The webview should be set'


def test_get_page_type_login(importer: SongSelectImport):
    """
    Test get_page_type to spot the login page
    """
    # GIVEN: A importer object, and a mocked url
    url = QtCore.QUrl('https://profile.ccli.com/account/signin?appContext=SongSelect&'
                      'returnUrl=https%3a%2f%2fsongselect.ccli.com%2f')
    page = MagicMock(url=MagicMock(return_value=url))
    importer.webview = MagicMock(page=MagicMock(return_value=page))

    # WHEN: The method is run
    result = importer.get_page_type()

    # THEN: The correct type should be returned
    assert result == Pages.Login


def test_get_page_type_home(importer: SongSelectImport):
    """
    Test get_page_type to spot the home page
    """
    # GIVEN: A importer object, and a mocked url
    url = QtCore.QUrl('https://songselect.ccli.com')
    page = MagicMock(url=MagicMock(return_value=url))
    importer.webview = MagicMock(page=MagicMock(return_value=page))

    # WHEN: The method is run
    result = importer.get_page_type()

    # THEN: The correct type should be returned
    assert result == Pages.Home


def test_get_page_type_search(importer: SongSelectImport):
    """
    Test get_page_type to spot the search page
    """
    # GIVEN: A importer object, and a mocked url
    url = QtCore.QUrl('https://songselect.ccli.com/search/results?SearchText=test')
    page = MagicMock(url=MagicMock(return_value=url))
    importer.webview = MagicMock(page=MagicMock(return_value=page))

    # WHEN: The method is run
    result = importer.get_page_type()

    # THEN: The correct type should be returned
    assert result == Pages.Search


def test_get_page_type_song(importer: SongSelectImport):
    """
    Test get_page_type to spot the login page
    """
    # GIVEN: A importer object, and a mocked url
    url = QtCore.QUrl('https://songselect.ccli.com/Songs/7115744/song_name/view_lyrics')
    page = MagicMock(url=MagicMock(return_value=url))
    importer.webview = MagicMock(page=MagicMock(return_value=page))

    # WHEN: The method is run
    result = importer.get_page_type()

    # THEN: The correct type should be returned
    assert result == Pages.Song


def test_get_page_type_other(importer: SongSelectImport):
    """
    Test get_page_type to spot the login page
    """
    # GIVEN: A importer object, and a mocked url
    url = QtCore.QUrl('https://openlp.org')
    page = MagicMock(url=MagicMock(return_value=url))
    importer.webview = MagicMock(page=MagicMock(return_value=page))

    # WHEN: The method is run
    result = importer.get_page_type()

    # THEN: The correct type should be returned
    assert result == Pages.Other


@patch('openlp.plugins.songs.lib.songselect.wait_for')
def test_run_javascript(mocked_wait_for: MagicMock, importer: SongSelectImport):
    """
    Test run javascript calls the page object
    """
    # GIVEN: A importer object and mocked run js fn
    def runJs(script, handle_result):
        handle_result('processed_{}'.format(script))
    importer.webview = MagicMock()
    page = MagicMock()
    page.runJavaScript = runJs
    importer.webview.page.return_value = page

    # WHEN: The set login field method is called
    result = importer._run_javascript('2 + 2')

    # THEN: The javascript should have been called on the page object
    assert result == 'processed_2 + 2'


def test_reset_webview(importer: SongSelectImport):
    """
    Check that the setUrl method is called when the reset webview method is called
    """
    # GIVEN: A importer object and mock webview
    importer.webview = MagicMock()

    # WHEN: The reset_webview method is called
    importer.reset_webview()

    # THEN: The setUrl function should have been called
    importer.webview.setUrl.assert_called_with(QtCore.QUrl(LOGIN_PAGE))


@patch('openlp.plugins.songs.lib.songselect.SongSelectImport.set_page')
def test_set_home_page(mocked_set_page: MagicMock, importer: SongSelectImport):
    """
    Test that when the home method is called, it attempts to go to the home page
    """
    # GIVEN: A importer object
    # WHEN: The home method is called
    importer.set_home_page()

    # THEN: set_page is called once with the base url
    mocked_set_page.assert_called_with(BASE_URL)


@patch('openlp.plugins.songs.lib.songselect.SongSelectImport._run_javascript')
def test_set_page(mocked_run_js: MagicMock, importer: SongSelectImport):
    """
    Test set page runs the correct script
    """
    # GIVEN: A importer object
    # WHEN: The set login field method is called
    importer.set_page('my_new_page')

    # THEN: The javascript called should contain the correct values
    mocked_run_js.assert_called_with('document.location = "my_new_page"')


@patch('openlp.plugins.songs.lib.songselect.SongSelectImport._run_javascript')
def test_set_login_fields(mocked_run_js: MagicMock, importer: SongSelectImport):
    """
    Test correct js is sent to set login fields
    """
    # GIVEN: A importer object
    # WHEN: The set login field method is called
    importer.set_login_fields('my_username', 'my_password')

    # THEN: The javascript called should contain the correct values
    mocked_run_js.assert_called_with(('document.getElementById("EmailAddress").value = "my_username";'
                                      'document.getElementById("Password").value = "my_password";'
                                      ))


@patch('openlp.plugins.songs.lib.songselect.SongSelectImport._run_javascript')
@patch('openlp.plugins.songs.lib.songselect.wait_for')
def test_get_page(mocked_wait_for: MagicMock, mocked_run_js: MagicMock, importer: SongSelectImport):
    """
    Test get page sends js requests
    """
    # GIVEN: A importer object
    mocked_run_js.return_value = True

    # WHEN: The get page method is called
    importer.get_page("https://example.com")

    # THEN: The javascript should be run
    assert mocked_run_js.call_count == 2, 'Should be called once for request and once for fetch'
    mocked_wait_for.assert_called_once()


def test_get_song_number_from_url(importer: SongSelectImport):
    """
    Test the ccli number can be correctly obtained from a url
    """
    # GIVEN: A importer object
    # WHEN: The function is called with a valid url
    result = importer.get_song_number_from_url('https://songselect.ccli.com/songs/4755360/amazing-grace')

    # THEN: The ccli number is returned
    assert result == '4755360', 'Should have found the ccli number from the url'


def test_get_song_number_from_url_nonumber(importer: SongSelectImport):
    """
    Test the ccli number function returns None when no number is found
    """
    # GIVEN: A importer object
    # WHEN: The function is called with a valid url
    result = importer.get_song_number_from_url('https://songselect.ccli.com/search/results?SearchText=song+4755360')

    # THEN: The returned value should be None
    assert result is None


@patch('openlp.plugins.songs.lib.songselect.clean_song')
@patch('openlp.plugins.songs.lib.songselect.Topic')
@patch('openlp.plugins.songs.lib.songselect.Author')
def test_save_song_new_author(MockedAuthor: MagicMock, MockedTopic: MagicMock, mocked_clean_song: MagicMock,
                              importer: SongSelectImport):
    """
    Test that saving a song with a new author performs the correct actions
    """
    # GIVEN: A song to save, and some mocked out objects
    song_dict = {
        'title': 'Arky Arky',
        'authors': ['Public Domain'],
        'verses': [
            {'label': 'Verse 1', 'lyrics': 'The Lord told Noah: there\'s gonna be a floody, floody'},
            {'label': 'Chorus 1', 'lyrics': 'So, rise and shine, and give God the glory, glory'},
            {'label': 'Verse 2', 'lyrics': 'The Lord told Noah to build him an arky, arky'}
        ],
        'copyright': 'Public Domain',
        'ccli_number': '123456'
    }
    MockedAuthor.display_name.__eq__.return_value = False
    MockedTopic.name.__eq__.return_value = False
    importer.db_manager.get_object_filtered.return_value = None

    # WHEN: The song is saved to the database
    result = importer.save_song(song_dict)

    # THEN: The return value should be a Song class and the mocked_db_manager should have been called
    assert isinstance(result, Song), 'The returned value should be a Song object'
    mocked_clean_song.assert_called_with(importer.db_manager, result)
    assert 2 == importer.db_manager.save_object.call_count, 'The save_object() method should have been called twice'
    importer.db_manager.get_object_filtered.assert_called_with(MockedAuthor, False)
    MockedAuthor.assert_called_with(first_name='Public', last_name='Domain', display_name='Public Domain')
    assert 1 == len(result.authors_songs), 'There should only be one author'


@patch('openlp.plugins.songs.lib.songselect.clean_song')
@patch('openlp.plugins.songs.lib.songselect.Author')
def test_save_song_existing_author(MockedAuthor: MagicMock, mocked_clean_song: MagicMock, importer: SongSelectImport):
    """
    Test that saving a song with an existing author performs the correct actions
    """
    # GIVEN: A song to save, and some mocked out objects
    song_dict = {
        'title': 'Arky Arky',
        'authors': ['Public Domain'],
        'verses': [
            {'label': 'Verse 1', 'lyrics': 'The Lord told Noah: there\'s gonna be a floody, floody'},
            {'label': 'Chorus 1', 'lyrics': 'So, rise and shine, and give God the glory, glory'},
            {'label': 'Verse 2', 'lyrics': 'The Lord told Noah to build him an arky, arky'}
        ],
        'copyright': 'Public Domain',
        'ccli_number': '123456'
    }
    MockedAuthor.display_name.__eq__.return_value = False
    importer.db_manager.get_object_filtered.return_value = MagicMock()

    # WHEN: The song is saved to the database
    result = importer.save_song(song_dict)

    # THEN: The return value should be a Song class and the mocked_db_manager should have been called
    assert isinstance(result, Song), 'The returned value should be a Song object'
    mocked_clean_song.assert_called_with(importer.db_manager, result)
    assert 2 == importer.db_manager.save_object.call_count, 'The save_object() method should have been called twice'
    importer.db_manager.get_object_filtered.assert_called_with(MockedAuthor, False)
    assert 0 == MockedAuthor.call_count, 'A new author should not have been instantiated'
    assert 1 == len(result.authors_songs), 'There should only be one author'


@patch('openlp.plugins.songs.lib.songselect.clean_song')
@patch('openlp.plugins.songs.lib.songselect.Author')
def test_save_song_unknown_author(MockedAuthor: MagicMock, mocked_clean_song: MagicMock, importer: SongSelectImport):
    """
    Test that saving a song with an author name of only one word performs the correct actions
    """
    # GIVEN: A song to save, and some mocked out objects
    song_dict = {
        'title': 'Arky Arky',
        'authors': ['Unknown'],
        'verses': [
            {'label': 'Verse 1', 'lyrics': 'The Lord told Noah: there\'s gonna be a floody, floody'},
            {'label': 'Chorus 1', 'lyrics': 'So, rise and shine, and give God the glory, glory'},
            {'label': 'Verse 2', 'lyrics': 'The Lord told Noah to build him an arky, arky'}
        ],
        'copyright': 'Public Domain',
        'ccli_number': '123456'
    }
    MockedAuthor.display_name.__eq__.return_value = False
    importer.db_manager.get_object_filtered.return_value = None

    # WHEN: The song is saved to the database
    result = importer.save_song(song_dict)

    # THEN: The return value should be a Song class and the mocked_db_manager should have been called
    assert isinstance(result, Song), 'The returned value should be a Song object'
    mocked_clean_song.assert_called_with(importer.db_manager, result)
    assert 2 == importer.db_manager.save_object.call_count, 'The save_object() method should have been called twice'
    importer.db_manager.get_object_filtered.assert_called_with(MockedAuthor, False)
    MockedAuthor.assert_called_with(first_name='Unknown', last_name='', display_name='Unknown')
    assert 1 == len(result.authors_songs), 'There should only be one author'


@patch('openlp.plugins.songs.lib.songselect.clean_song')
@patch('openlp.plugins.songs.lib.songselect.Topic')
@patch('openlp.plugins.songs.lib.songselect.Author')
def test_save_song_topics(MockedAuthor: MagicMock, MockedTopic: MagicMock, mocked_clean_song: MagicMock,
                          importer: SongSelectImport):
    """
    Test that saving a song with topics performs the correct actions
    Also check that a verse with no number is retitled to 1
    """
    # GIVEN: A song to save, and some mocked out objects
    song_dict = {
        'title': 'Arky Arky',
        'authors': ['Public Domain'],
        'verses': [
            {'label': 'Verse', 'lyrics': 'The Lord told Noah: there\'s gonna be a floody, floody'},
            {'label': 'Chorus 1', 'lyrics': 'So, rise and shine, and give God the glory, glory'},
            {'label': 'Verse 2', 'lyrics': 'The Lord told Noah to build him an arky, arky'}
        ],
        'copyright': 'Public Domain',
        'ccli_number': '123456',
        'topics': ['Old Testement', 'Flood']
    }

    def save_object(b):
        b.topics = []

    MockedAuthor.display_name.__eq__.return_value = False
    MockedTopic.name.__eq__.return_value = False
    importer.db_manager.get_object_filtered.return_value = None
    importer.db_manager.save_object = save_object

    # WHEN: The song is saved to the database
    result = importer.save_song(song_dict)

    # THEN: The return value should be a Song class and the topics should have been added
    assert isinstance(result, Song), 'The returned value should be a Song object'
    mocked_clean_song.assert_called_with(importer.db_manager, result)
    assert MockedTopic.call_count == 2, 'Should have created 2 new topics'
    MockedTopic.assert_called_with(name='Flood')
    assert 1 == len(result.authors_songs), 'There should only be one author'


def test_create_form(form: SongSelectForm):
    """
    Test that we can create the SongSelect form
    """
    # GIVEN: The SongSelectForm class and a mocked db manager
    # WHEN: We create an instance
    # THEN: The correct properties should have been assigned
    assert isinstance(form.plugin, MagicMock), 'The correct plugin should have been assigned'
    assert isinstance(form.db_manager, MagicMock), 'The correct db_manager should have been assigned'


@patch('openlp.plugins.songs.lib.songselect.SongSelectImport')
def test_initialise(mocked_ss_import: MagicMock, form: SongSelectForm):
    """
    Test the initialise method
    """
    # GIVEN: The SongSelectForm
    # WHEN: The initialise method is run
    form.initialise()

    # THEN: The import object should exist, song var should be None, and the page hooked up
    assert form.song is None
    assert isinstance(form.song_select_importer, SongSelectImport), 'SongSelectImport object should be created'
    assert form.webview.page.call_count == 4, 'Page should be called 5 times, once for each load handler and ' \
                                              f'one for JS inject, instead {form.webview.page.call_count} calls ' \
                                              'were made'


@patch('openlp.plugins.songs.forms.songselectform.QtWidgets.QDialog.exec')
def test_exec(mocked_exec: MagicMock, form: SongSelectForm):
    """
    Test the exec method
    """
    # GIVEN: The SongSelectForm
    form.song_select_importer = MagicMock()
    form.stacked_widget = MagicMock()

    # WHEN: The initialise method is run
    form.exec()

    # THEN: Should have reset webview, set stack to 0 and pass on the event
    form.song_select_importer.reset_webview.assert_called_once()
    form.stacked_widget.setCurrentIndex.assert_called_with(0)
    mocked_exec.assert_called_once()


@patch('openlp.plugins.songs.forms.songselectform.QtWidgets.QDialog.done')
@patch('openlp.plugins.songs.forms.songselectform.QtWidgets.QProgressDialog')
def test_done(mocked_prog_dialog: MagicMock, mocked_done: MagicMock, form: SongSelectForm):
    """
    Test the done method closes th dialog
    """
    # GIVEN: The SongSelectForm
    form.song_select_importer = MagicMock()

    # WHEN: The initialise method is run
    form.done('result')

    # THEN: Should have passed on the event
    mocked_done.assert_called_once()


def test_page_load_started(form: SongSelectForm):
    """
    Test the page_load_started method
    """
    # GIVEN: The SongSelectForm
    form.back_button = MagicMock()
    form.url_bar = MagicMock()
    form.message_area = MagicMock()

    # WHEN: The method is run
    form.page_load_started()

    # THEN: The UI should be set up accordingly
    form.back_button.setEnabled.assert_called_with(False)
    form.message_area.setText.assert_called_with('Import songs by clicking the "Download" in the Lyrics tab '
                                                 'or "Download ChordPro" in the Chords tabs.')


def test_page_loaded_login(form: SongSelectForm):
    """
    Test the page_loaded method for a "Login" page
    """
    # GIVEN: The SongSelectForm and mocked login page
    form.song_select_importer = MagicMock()
    form.song_select_importer.get_page_type.return_value = Pages.Login
    form.signin_page_loaded = MagicMock()
    form.url_bar = MagicMock()

    # WHEN: The method is run
    form.page_loaded(True)

    # THEN: The signin page method should be called
    form.signin_page_loaded.assert_called_once()


def test_page_loaded_other(form: SongSelectForm):
    """
    Test the page_loaded method for an "Other" page
    """
    # GIVEN: The SongSelectForm and mocked other page
    form.song_select_importer = MagicMock()
    form.song_select_importer.get_page_type.return_value = Pages.Other
    form.song_progress_bar = MagicMock()
    form.back_button = MagicMock()
    form.url_bar = MagicMock()

    # WHEN: The method is run
    form.page_loaded(True)

    # THEN: Back button should be available
    form.back_button.setEnabled.assert_called_with(True)


def test_signin_page_loaded(form: SongSelectForm):
    """
    Test that the signin_page_loaded method calls the appropriate method
    """
    # GIVEN: The SongSelectForm and mocked settings
    form.song_select_importer = MagicMock()
    form.settings.value = MagicMock(side_effect=['user', 'pass'])

    # WHEN: The method is run
    form.signin_page_loaded()

    # THEN: Correct values should have been sent from the settings
    form.song_select_importer.set_login_fields.assert_called_with('user', 'pass')


@patch('openlp.plugins.songs.forms.songselectdialog.QtWidgets.QListWidgetItem')
def test_view_song(mock_qtlist: MagicMock, form: SongSelectForm):
    """
    Test that the _view_song method does the important stuff
    """
    # GIVEN: The SongSelectForm, mocks and a song
    form.stacked_widget = MagicMock()
    form.title_edit = MagicMock()
    form.copyright_edit = MagicMock()
    form.ccli_edit = MagicMock()
    form.lyrics_table_widget = MagicMock()
    form.author_list_widget = MagicMock()
    form.song = {
        'title': 'Song Title',
        'copyright': 'copy thing',
        'ccli_number': '1234',
        'authors': ['Bob', 'Jo'],
        'verses': [{'lyrics': 'hello', 'label': 'Verse 1'}]
    }

    # WHEN: The method is run
    form._view_song()

    # THEN: Page should have changed in the stacked widget and ui should have been updated
    form.stacked_widget.setCurrentIndex.assert_called_with(1)
    form.title_edit.setText.assert_called_with('Song Title')
    form.copyright_edit.setText.assert_called_with('copy thing')
    form.ccli_edit.setText.assert_called_with('1234')
    assert form.lyrics_table_widget.setItem.call_count > 0
    assert form.author_list_widget.addItem.call_count > 0


@patch('openlp.plugins.songs.forms.songselectform.QtWidgets.QMessageBox.critical')
def test_view_song_invalid(mock_message: MagicMock, form: SongSelectForm):
    """
    Test that the _view_song doesn't mess up when the song doesn't exist
    """
    # GIVEN: The SongSelectForm, mocks and a song
    form.stacked_widget = MagicMock()
    form.song = None

    # WHEN: The method is run
    form._view_song()

    # THEN: Page should not have changed and a warning should show
    assert form.stacked_widget.setCurrentIndex.call_count == 0
    mock_message.assert_called_once()


def test_on_url_bar_return_pressed(form: SongSelectForm):
    """
    Test that the on_url_bar_return_pressed method changes the page
    """
    # GIVEN: The SongSelectForm, mocks and a song
    form.url_bar = MagicMock()
    form.url_bar.text.return_value = "test"
    form.song_select_importer = MagicMock()

    # WHEN: The method is run
    form.on_url_bar_return_pressed()

    # THEN: Page should not have changed and a warning should show
    form.song_select_importer.set_page.assert_called_with("test")


def test_on_back_button_clicked_preview(form: SongSelectForm):
    """
    Test that when the back button is clicked on preview screen, the stacked widget is set back one page
    """
    # GIVEN: A SongSelect form, stacked widget on page 1
    ssimporter = MagicMock()
    form.song_select_importer = MagicMock()
    form.song_select_importer.set_home_page = ssimporter
    with patch.object(form, 'stacked_widget') as mocked_stacked_widget:
        mocked_stacked_widget.currentIndex.return_value = 1

    # WHEN: The preview back button is clicked
        form.on_back_button_clicked()

    # THEN: The stacked widget should be set back one page and webpage is NOT put back to the home page
    mocked_stacked_widget.setCurrentIndex.assert_called_with(0)
    ssimporter.assert_not_called()


def test_on_back_button_clicked_force(form: SongSelectForm):
    """
    Test that when the back button method is triggered with the force param set,
    the page should be changed
    """
    # GIVEN: A SongSelect form, stacked widget on page 1
    ssimporter = MagicMock()
    form.song_select_importer = MagicMock()
    form.song_select_importer.set_home_page = ssimporter
    with patch.object(form, 'stacked_widget') as mocked_stacked_widget:
        mocked_stacked_widget.currentIndex.return_value = 1

    # WHEN: The preview back button is clicked with force param
        form.on_back_button_clicked(True)

    # THEN: The stacked widget should be set back one page and webpage is NOT put back to the home page
    mocked_stacked_widget.setCurrentIndex.assert_called_with(0)
    ssimporter.assert_called_once()


def test_on_back_button_clicked(form: SongSelectForm):
    """
    Test that when the back button is clicked, the stacked widget is set to page 0
    and set to home page
    """
    # GIVEN: A SongSelect form, stacked widget on page 0
    ssimporter = MagicMock()
    form.song_select_importer = MagicMock()
    form.song_select_importer.set_home_page = ssimporter
    with patch.object(form, 'stacked_widget') as mocked_stacked_widget:
        mocked_stacked_widget.currentIndex.return_value = 0

        # WHEN: The back button is clicked
        form.on_back_button_clicked()

    # THEN: The stacked widget should be set back one page
    mocked_stacked_widget.setCurrentIndex.assert_called_with(0)
    ssimporter.assert_called_with()


def test_songselect_file_import(registry: Registry, settings: Settings):
    """
    Test that loading a SongSelect file works correctly on various files
    """
    with SongImportTestHelper('CCLIFileImport', 'cclifile') as helper:
        helper.file_import([TEST_PATH / 'TestSong.bin'],
                           helper.load_external_result_data(TEST_PATH / 'TestSong-bin.json'))
        helper.file_import([TEST_PATH / 'TestSong.txt'],
                           helper.load_external_result_data(TEST_PATH / 'TestSong-txt.json'))
        helper.file_import([TEST_PATH / 'TestSong2023.txt'],
                           helper.load_external_result_data(TEST_PATH / 'TestSong2023-txt.json'))
