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
Package to test the openlp.core.ui.thememanager package.
"""
import pytest
import os
import shutil
from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import ANY, Mock, MagicMock, patch, call, sentinel

from PySide6 import QtWidgets

from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings
from openlp.core.lib.theme import Theme
from openlp.core.ui.thememanager import ThemeManager, THUMBNAIL_REBUILD_MARKER_SETTING
from tests.utils.constants import RESOURCE_PATH


@pytest.fixture()
def theme_manager(registry: Registry, settings: Settings) -> ThemeManager:
    registry.register('main_window', None)
    thm = ThemeManager()
    return thm


@patch('openlp.core.ui.thememanager.zipfile.ZipFile.__init__')
@patch('openlp.core.ui.thememanager.zipfile.ZipFile.write')
def test_export_theme(mocked_zipfile_write: MagicMock, mocked_zipfile_init: MagicMock, theme_manager: ThemeManager):
    """
    Test exporting a theme .
    """
    # GIVEN: A new ThemeManager instance.
    theme_manager.theme_path = RESOURCE_PATH / 'themes'
    mocked_zipfile_init.return_value = None

    # WHEN: The theme is exported
    theme_manager._export_theme(Path('some', 'path', 'Default.otz'), 'Default')

    # THEN: The zipfile should be created at the given path
    mocked_zipfile_init.assert_called_with(Path('some', 'path', 'Default.otz'), 'w')
    mocked_zipfile_write.assert_called_with(RESOURCE_PATH / 'themes' / 'Default' / 'Default.xml',
                                            Path('Default', 'Default.xml'))


def test_initial_theme_manager(theme_manager: ThemeManager):
    """
    Test the instantiation of theme manager.
    """
    # GIVEN: A new service manager instance.
    # WHEN: the default theme manager is built.
    # THEN: The the controller should be registered in the registry.
    assert Registry().get('theme_manager') is not None, 'The base theme manager should be registered'


@patch('openlp.core.ui.thememanager.Theme')
def test_get_global_theme(mocked_theme: MagicMock, theme_manager: ThemeManager):
    """
    Test the global theme method returns the theme data for the global theme
    """
    # GIVEN: A service manager instance and the global theme
    theme_manager.global_theme = 'global theme name'
    theme_manager._theme_list = {'global theme name': sentinel.global_theme}

    # WHEN: Calling get_global_theme
    result = theme_manager.get_global_theme()

    # THEN: Returned global theme
    assert result == sentinel.global_theme


@patch('openlp.core.ui.thememanager.Theme')
def test_get_theme_data(mocked_theme: MagicMock, theme_manager: ThemeManager):
    """
    Test that the get theme data method returns the requested theme data
    """
    # GIVEN: A service manager instance and themes
    theme_manager._theme_list = {'theme1': sentinel.theme1, 'theme2': sentinel.theme2}

    # WHEN: Get theme data is called with 'theme2'
    result = theme_manager.get_theme_data('theme2')

    # THEN: Should return theme2's data
    assert result == sentinel.theme2


@patch('openlp.core.ui.thememanager.Theme')
def test_get_theme_data_missing(mocked_theme: MagicMock, theme_manager: ThemeManager):
    """
    Test that the get theme data method returns the default theme when theme name not found
    """
    # GIVEN: A service manager instance and themes
    theme_manager._theme_list = {'theme1': sentinel.theme1, 'theme2': sentinel.theme2}
    mocked_theme.return_value = sentinel.default_theme

    # WHEN: Get theme data is called with None
    result = theme_manager.get_theme_data(None)

    # THEN: Should return default theme's data
    assert result == sentinel.default_theme


@patch('openlp.core.ui.thememanager.shutil')
@patch('openlp.core.ui.thememanager.create_paths')
def test_save_theme_same_image(mocked_create_paths: MagicMock, mocked_shutil: MagicMock, theme_manager: ThemeManager):
    """
    Test that we don't try to overwrite a theme background image with itself
    """
    # GIVEN: A new theme manager instance, with mocked builtins.open, copyfile,
    #        theme, create_paths, thememanager-attributes and background
    #       .filename path is the same as the source path.
    theme_manager.old_background_image_path = None
    theme_manager.update_preview_images = MagicMock()
    theme_manager.theme_path = MagicMock()
    mocked_theme = MagicMock()
    mocked_theme.theme_name = 'themename'
    mocked_theme.extract_formatted_xml = MagicMock()
    mocked_theme.extract_formatted_xml.return_value = 'fake_theme_xml'.encode()
    file_path_1 = RESOURCE_PATH / 'church.jpg'
    mocked_theme.background_filename = file_path_1
    mocked_theme.background_source = file_path_1

    # WHEN: Calling save_theme with both background paths to the same image
    theme_manager.save_theme(mocked_theme)

    # THEN: The mocked_copyfile should not have been called
    assert mocked_shutil.copyfile.called is False, 'copyfile should not be called'


@patch('openlp.core.ui.thememanager.shutil')
@patch('openlp.core.ui.thememanager.create_paths')
def test_save_theme_diff_images(mocked_create_paths, mocked_shutil, theme_manager: ThemeManager):
    """
    Test that we do overwrite a theme background image when a new is submitted
    """
    # GIVEN: A new theme manager instance, with mocked builtins.open, copyfile,
    #        theme, create_paths, thememanager-attributes and background
    #       .filename path is the same as the source path.
    theme_manager.old_background_image_path = None
    theme_manager.update_preview_images = MagicMock()
    theme_manager.theme_path = MagicMock()
    mocked_theme = MagicMock()
    mocked_theme.theme_name = 'themename'
    mocked_theme.background_filename = RESOURCE_PATH / 'church.jpg'
    mocked_theme.background_source = RESOURCE_PATH / 'church2.jpg'

    # WHEN: Calling save_theme with both background paths to different images
    theme_manager.save_theme(mocked_theme)

    # THEN: The mocked_copyfile should have been called
    assert mocked_shutil.copyfile.called is True, 'copyfile should be called'


@patch('openlp.core.ui.thememanager.shutil')
@patch('openlp.core.ui.thememanager.delete_file')
@patch('openlp.core.ui.thememanager.create_paths')
def test_save_theme_delete_old_image(mocked_create_paths, mocked_del_file, mocked_shutil, theme_manager: ThemeManager):
    """
    Test that we do delete a old theme background image when a new is submitted
    """
    # GIVEN: A new theme manager instance, with mocked builtins.open,
    #        theme, create_paths, thememanager-attributes and background
    #       .filename path is the same as the source path.
    theme_manager.old_background_image_path = RESOURCE_PATH / 'old_church.png'
    theme_manager.update_preview_images = MagicMock()
    theme_manager.theme_path = MagicMock()
    mocked_theme = MagicMock()
    mocked_theme.theme_name = 'themename'
    mocked_theme.background_filename = RESOURCE_PATH / 'church.jpg'
    mocked_theme.background_source = RESOURCE_PATH / 'church2.jpg'

    # WHEN: Calling save_theme with both background paths to different images
    theme_manager.save_theme(mocked_theme)

    # THEN: The mocked_delete_file should have been called to delete the old cached background
    assert mocked_del_file.called is True, 'delete_file should be called'


@patch.object(ThemeManager, 'log_exception')
@patch('openlp.core.ui.thememanager.delete_file')
@patch('openlp.core.ui.thememanager.create_paths')
def test_save_theme_missing_original(mocked_paths, mocked_delete, mocked_log_exception, theme_manager: ThemeManager):
    """
    Test that we revert to the old theme background image if the source is missing
    when changing the theme. (User doesn't change background but the original is
    missing)
    """
    # GIVEN: A new theme manager instance, with invalid files. Setup as if the user
    # has left the background the same, or reselected the same path.
    # Not using resource dir because I could potentially copy a file
    folder_path = Path(mkdtemp())
    theme_manager.old_background_image_path = folder_path / 'old.png'
    theme_manager.update_preview_images = MagicMock()
    theme_manager.theme_path = MagicMock()
    mocked_theme = MagicMock()
    mocked_theme.theme_name = 'themename'
    mocked_theme.background_filename = folder_path / 'old.png'
    mocked_theme.background_source = folder_path / 'non_existent_original.png'

    # WHEN: Calling save_theme with a invalid background_filename
    # Although all filenames are considered invalid in this test,
    # it is important it reverts to the old background path as this in reality is always
    # valid unless someone has messed with the cache.
    theme_manager.save_theme(mocked_theme)

    # THEN: The old background should not have bee deleted
    #       AND the filename should have been replaced with the old cached background
    #       AND there is no exception
    assert mocked_delete.called is False, 'delete_file should not be called'
    assert mocked_theme.background_filename == theme_manager.old_background_image_path, \
        'Background path should be reverted'
    assert mocked_log_exception.called is False, \
        'Should not have been an exception as the file wasn\'t changed'


@patch.object(ThemeManager, 'log_warning')
@patch('openlp.core.ui.thememanager.delete_file')
@patch('openlp.core.ui.thememanager.create_paths')
def test_save_theme_missing_new(mocked_paths, mocked_delete, mocked_log_warning, theme_manager: ThemeManager):
    """
    Test that we log a warning if the new background is missing
    """
    # GIVEN: A new theme manager instance, with invalid files. Setup as if the user
    # has changed the background to a invalid path.
    # Not using resource dir because I could potentially copy a file
    folder_path = Path(mkdtemp())
    theme_manager.old_background_image_path = folder_path / 'old.png'
    theme_manager.update_preview_images = MagicMock()
    theme_manager.theme_path = MagicMock()
    mocked_theme = MagicMock()
    mocked_theme.theme_name = 'themename'
    mocked_theme.background_filename = folder_path / 'new_cached.png'
    mocked_theme.background_source = folder_path / 'new_original.png'

    # WHEN: Calling save_theme with a invalid background_filename
    theme_manager.save_theme(mocked_theme)

    # THEN: A warning should have happened due to attempting to copy a missing file
    mocked_log_warning.assert_called_once_with('Background source does not exist, retaining cached background')


@patch('openlp.core.ui.thememanager.shutil')
@patch('openlp.core.ui.thememanager.delete_file')
@patch('openlp.core.ui.thememanager.create_paths')
def test_save_theme_background_override(mocked_paths, mocked_delete, mocked_shutil, theme_manager: ThemeManager):
    """
    Test that we log a warning if the new background is missing
    """
    # GIVEN: A new theme manager instance, with invalid files. Setup as if the user
    # has changed the background to a invalid path.
    # Not using resource dir because I could potentially copy a file
    folder_path = Path(mkdtemp())
    theme_manager.old_background_image_path = folder_path / 'old.png'
    theme_manager.update_preview_images = MagicMock()
    theme_manager.theme_path = MagicMock()
    mocked_theme = MagicMock()
    mocked_theme.theme_name = 'themename'
    mocked_theme.background_filename = folder_path / 'new_cached.png'
    # mocked_theme.background_source.exists() will return True
    mocked_theme.background_source = MagicMock()
    # override_background.exists() will return True
    override_background = MagicMock()

    # WHEN: Calling save_theme with a background override
    theme_manager.save_theme(mocked_theme, background_file=override_background)

    # THEN: The override_background should have been copied rather than the background_source
    mocked_shutil.copyfile.assert_called_once_with(override_background, mocked_theme.background_filename)


def test_save_theme_special_char_name(registry, temp_folder, theme_manager: ThemeManager):
    """
    Test that we can save themes with special characters in the name
    """
    # GIVEN: A new theme manager instance, with mocked theme and thememanager-attributes.
    theme_manager.old_background_image_path = None
    theme_manager.update_preview_images = MagicMock()
    theme_manager.theme_path = Path(temp_folder)
    mocked_theme = MagicMock()
    mocked_theme.theme_name = 'theme 愛 name'
    mocked_theme.export_theme.return_value = "{}"

    # WHEN: Calling save_theme with a theme with a name with special characters in it
    theme_manager.save_theme(mocked_theme)

    # THEN: It should have been created
    assert os.path.exists(os.path.join(temp_folder, 'theme 愛 name', 'theme 愛 name.json')) is True, \
        'Theme with special characters should have been created!'


@patch('openlp.core.ui.thememanager.QtWidgets.QMessageBox.question',
       return_value=QtWidgets.QMessageBox.StandardButton.Yes)
@patch('openlp.core.ui.thememanager.translate')
def test_over_write_message_box_yes(mocked_translate, mocked_qmessagebox_question, theme_manager: ThemeManager):
    """
    Test that theme_manager.over_write_message_box returns True when the user clicks yes.
    """
    # GIVEN: A patched QMessageBox.question and an instance of ThemeManager
    mocked_translate.side_effect = lambda context, text: text

    # WHEN: Calling over_write_message_box with 'Theme Name'
    result = theme_manager.over_write_message_box('Theme Name')

    # THEN: over_write_message_box should return True and the message box should contain the theme name
    assert result is True
    mocked_qmessagebox_question.assert_called_once_with(
        theme_manager, 'Theme Already Exists', 'Theme Theme Name already exists. Do you want to replace it?',
        defaultButton=ANY)


@patch('openlp.core.ui.thememanager.QtWidgets.QMessageBox.question',
       return_value=QtWidgets.QMessageBox.StandardButton.No)
@patch('openlp.core.ui.thememanager.translate')
def test_over_write_message_box_no(mocked_translate, mocked_qmessagebox_question, theme_manager: ThemeManager):
    """
    Test that theme_manager.over_write_message_box returns False when the user clicks no.
    """
    # GIVEN: A patched QMessageBox.question and an instance of ThemeManager
    mocked_translate.side_effect = lambda context, text: text

    # WHEN: Calling over_write_message_box with 'Theme Name'
    result = theme_manager.over_write_message_box('Theme Name')

    # THEN: over_write_message_box should return False and the message box should contain the theme name
    assert result is False
    mocked_qmessagebox_question.assert_called_once_with(
        theme_manager, 'Theme Already Exists', 'Theme Theme Name already exists. Do you want to replace it?',
        defaultButton=ANY)


@patch('openlp.core.lib.theme.Theme.set_default_header_footer')
def test_unzip_theme(mocked_theme_set_defaults, theme_manager: ThemeManager):
    """
    Test that unzipping of themes works
    """
    # GIVEN: A theme file, a output folder and some mocked out internal functions
    with patch('openlp.core.ui.thememanager.critical_error_message_box') \
            as mocked_critical_error_message_box:
        theme_manager.update_preview_images = MagicMock()
        theme_manager.theme_path = Path(mkdtemp())
        theme_file_path = RESOURCE_PATH / 'themes' / 'Moss_on_tree.otz'

        # WHEN: We try to unzip it
        ret_theme_name = theme_manager.unzip_theme(theme_file_path)

        # THEN: Files should be unpacked AND xml file should be upgraded to json
        assert (theme_manager.theme_path / 'Moss on tree' / 'Moss on tree.xml').exists() is False
        assert (theme_manager.theme_path / 'Moss on tree' / 'Moss on tree.json').exists() is True
        assert mocked_critical_error_message_box.call_count == 0, 'No errors should have happened'
        assert ret_theme_name == "Moss on tree", "The theme name should have been returned"
        shutil.rmtree(theme_manager.theme_path)


def test_unzip_theme_invalid_version(theme_manager: ThemeManager):
    """
    Test that themes with invalid (< 2.0) or with no version attributes are rejected
    """
    # GIVEN: An instance of ThemeManager whilst mocking a theme that returns a theme with no version attribute
    with patch('openlp.core.ui.thememanager.zipfile.ZipFile') as mocked_zip_file, \
            patch('openlp.core.ui.thememanager.ElementTree.getroot') as mocked_getroot, \
            patch('openlp.core.ui.thememanager.XML'), \
            patch('openlp.core.ui.thememanager.critical_error_message_box') as mocked_critical_error_message_box:

        mocked_zip_file.return_value = MagicMock(**{'namelist.return_value': [os.path.join('theme', 'theme.xml')]})
        mocked_getroot.return_value = MagicMock(**{'get.return_value': None})
        theme_manager.theme_path = Path('folder')

        # WHEN: unzip_theme is called
        ret_theme_name = theme_manager.unzip_theme(Path('theme.file'))

        # THEN: The critical_error_message_box should have been called
        assert mocked_critical_error_message_box.call_count == 1, 'Should have been called once'
        assert ret_theme_name is None, 'No theme name should have been returned'


def test_update_preview_images(theme_manager: ThemeManager):
    """
    Test that the update_preview_images() method works correctly
    """
    # GIVEN: A ThemeManager
    def get_theme_data(value):
        return '{}_theme_data'.format(value)
    theme_manager.save_preview = MagicMock()
    theme_manager._get_theme_data = Mock(side_effect=get_theme_data)
    theme_manager.progress_form = MagicMock(**{'get_preview.return_value': 'preview'})
    theme_manager.load_themes = MagicMock()
    theme_list = {'Default': get_theme_data('Default'), 'Test': get_theme_data('Test')}

    # WHEN: ThemeManager.update_preview_images() is called
    theme_manager.update_preview_images(theme_list)

    # THEN: Things should work right
    assert theme_manager.progress_form.theme_list == theme_list
    theme_manager.progress_form.show.assert_called_once_with()
    assert theme_manager.progress_form.get_preview.call_args_list == [call('Default', get_theme_data('Default')),
                                                                      call('Test', get_theme_data('Test'))]
    assert theme_manager.save_preview.call_args_list == [call('Default', 'preview'), call('Test', 'preview')]
    theme_manager.progress_form.close.assert_called_once_with()
    theme_manager.load_themes.assert_called_once_with()


def test_rebuild_theme_thumbnails_once(theme_manager: ThemeManager):
    """
    Test that thumbnails are rebuilt once when marker setting is not set.
    """
    # GIVEN: A ThemeManager with existing theme names and marker not set
    Settings().setValue(THUMBNAIL_REBUILD_MARKER_SETTING, False)
    theme_manager.get_theme_names = MagicMock(return_value=['Default', 'Test'])
    theme_manager.update_preview_images = MagicMock()

    # WHEN: rebuild is requested
    theme_manager.rebuild_theme_thumbnails_once()

    # THEN: previews should be rebuilt and marker should be persisted
    theme_manager.update_preview_images.assert_called_once_with(['Default', 'Test'])
    assert Settings().value(THUMBNAIL_REBUILD_MARKER_SETTING) is True


def test_rebuild_theme_thumbnails_once_skips_when_done(theme_manager: ThemeManager):
    """
    Test that thumbnails are not rebuilt again when marker setting is already set.
    """
    # GIVEN: A ThemeManager with marker already set
    Settings().setValue(THUMBNAIL_REBUILD_MARKER_SETTING, True)
    theme_manager.update_preview_images = MagicMock()
    theme_manager.get_theme_names = MagicMock(return_value=['Default'])

    # WHEN: rebuild is requested
    theme_manager.rebuild_theme_thumbnails_once()

    # THEN: no rebuild should happen
    theme_manager.update_preview_images.assert_not_called()
    assert Settings().value(THUMBNAIL_REBUILD_MARKER_SETTING) is True


def test_theme_manager_initialise(theme_manager):
    """
    Test the thememanager initialise - basic test
    """
    # GIVEN: A new a call to initialise
    theme_manager.setup_ui = MagicMock()
    theme_manager.build_theme_path = MagicMock()
    Settings().setValue('themes/global theme', 'my_theme')

    # WHEN: the initialisation is run
    theme_manager.bootstrap_initialise()

    # THEN:
    theme_manager.setup_ui.assert_called_once_with(theme_manager)
    assert theme_manager.global_theme == 'my_theme'
    theme_manager.build_theme_path.assert_called_once_with()


@patch('openlp.core.ui.thememanager.create_paths')
@patch('openlp.core.ui.thememanager.AppLocation.get_section_data_path')
def test_build_theme_path(mocked_get_section_data_path, mocked_create_paths, theme_manager):
    """
    Test the thememanager build_theme_path
    """
    # GIVEN: A mocked out AppLocation.get_directory() and mocked create_paths
    mocked_get_section_data_path.return_value = Path('tests/my_theme')

    # WHEN: the build_theme_path is run
    theme_manager.build_theme_path()

    #  THEN: The theme path and the thumb path should be correct
    assert theme_manager.theme_path == Path('tests/my_theme')
    assert theme_manager.thumb_path == Path('tests/my_theme/thumbnails')
    mocked_create_paths.assert_called_once_with(Path('tests/my_theme'), Path('tests/my_theme/thumbnails'))


def test_click_on_new_theme(theme_manager):
    """
    Test the on_add_theme event handler is called by the UI
    """
    # GIVEN: An initial form
    Settings().setValue('themes/global theme', 'my_theme')
    mocked_event = MagicMock()
    theme_manager.on_add_theme = mocked_event
    theme_manager.setup_ui(theme_manager)

    # WHEN displaying the UI and pressing cancel
    new_theme = theme_manager.toolbar.actions_map['newTheme']
    new_theme.trigger()

    assert mocked_event.call_count == 1, 'The on_add_theme method should have been called once'


@patch('openlp.core.ui.themeform.ThemeForm._setup')
@patch('openlp.core.ui.filerenameform.FileRenameForm._setup')
def test_bootstrap_post(mocked_rename_form, mocked_theme_form, theme_manager):
    """
    Test the functions of bootstrap_post_setup are called.
    """
    # GIVEN:
    theme_manager.toolbar = MagicMock()
    theme_manager.theme_path = MagicMock()
    theme_manager.load_themes = MagicMock()
    theme_manager.upgrade_themes = MagicMock()

    # WHEN:
    with patch('openlp.core.ui.thememanager.ThemeProgressForm'):
        theme_manager.bootstrap_post_set_up()

    # THEN:
    assert theme_manager.progress_form is not None
    assert theme_manager.theme_form is not None
    assert theme_manager.file_rename_form is not None
    theme_manager.upgrade_themes.assert_called_once()
    theme_manager.load_themes.assert_called_once()


@patch('openlp.core.lib.theme.Theme.set_default_header')
@patch('openlp.core.lib.theme.Theme.set_default_footer')
def test_clone_theme_data(mock_set_default_header, mock_set_default_footer, theme_manager):
    """Test that cloning the theme data works correctly"""
    # GIVEN: A theme manager, a theme (without a background source) and a new theme name
    existing_theme = Theme()
    existing_theme.theme_name = 'Existing Theme'
    existing_theme.background_type = 'image'
    existing_theme.background_filename = Path('Existing Theme', 'background.jpg')

    theme_manager.theme_path = Path('openlp', 'themes')
    theme_manager.save_theme = MagicMock()
    theme_manager.update_preview_images = MagicMock()
    theme_manager.load_themes = MagicMock()

    # WHEN: The theme is cloned
    theme_manager.clone_theme_data(existing_theme, 'New Theme')

    # THEN: The theme data should have been updated
    assert existing_theme.theme_name == 'New Theme'
    theme_manager.save_theme.assert_called_once_with(existing_theme, background_file=Path('Existing Theme',
                                                                                          'background.jpg'))
    theme_manager.update_preview_images.assert_called_once_with(['New Theme'])
    theme_manager.load_themes.assert_called_once_with()


@patch('openlp.core.ui.thememanager.check_item_selected')
def test_on_copy_theme_requires_selection(mocked_check_item_selected, theme_manager: ThemeManager):
    """
    Test that copy action exits early when no theme is selected.
    """
    # GIVEN: No selected item
    mocked_check_item_selected.return_value = False
    theme_manager.file_rename_form = MagicMock()
    theme_manager.theme_list_widget = MagicMock()

    # WHEN: copy is requested
    theme_manager.on_copy_theme()

    # THEN: No rename dialog should be shown
    theme_manager.file_rename_form.exec.assert_not_called()


@patch('openlp.core.ui.thememanager.FileDialog.getOpenFileNames')
def test_on_import_theme_ignores_failed_imports(mocked_get_open_file_names, theme_manager: ThemeManager):
    """
    Test that import only rebuilds previews for successfully imported themes.
    """
    # GIVEN: two selected files where one fails to import
    file_1 = Path('/tmp/invalid.otz')
    file_2 = Path('/tmp/valid.otz')
    mocked_get_open_file_names.return_value = ([file_1, file_2], '')
    Registry().remove('application')
    Registry().register('application', MagicMock())
    theme_manager.unzip_theme = MagicMock(side_effect=[None, 'Valid Theme'])
    theme_manager.update_preview_images = MagicMock()

    # WHEN: importing themes
    theme_manager.on_import_theme()

    # THEN: only successful imports should be used
    theme_manager.update_preview_images.assert_called_once_with(['Valid Theme'])
    assert theme_manager.settings.value('themes/last directory import') == file_1.parent


@patch('openlp.core.ui.thememanager.AppLocation.get_files')
def test_load_first_time_themes_ignores_failed_imports(mocked_get_files, theme_manager: ThemeManager):
    """
    Test that startup import ignores failed theme archives.
    """
    # GIVEN: startup theme archives with one failing import
    mocked_get_files.return_value = [Path('invalid.otz'), Path('valid.otz')]
    Registry().remove('application')
    Registry().register('application', MagicMock())
    theme_manager.theme_path = Path('/tmp/themes')
    theme_manager.unzip_theme = MagicMock(side_effect=[None, 'Valid Theme'])
    theme_manager.update_preview_images = MagicMock()

    # WHEN: first-time theme load runs
    theme_manager.load_first_time_themes()

    # THEN: only valid imported themes are passed to preview generation
    theme_manager.update_preview_images.assert_called_once_with(['Valid Theme'])
