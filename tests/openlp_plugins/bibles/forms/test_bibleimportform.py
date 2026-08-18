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
Package to test the openlp.plugins.bibles.forms.bibleimportform package.
"""
from unittest.mock import MagicMock, patch

import pytest
from PySide6 import QtWidgets, QtTest, QtCore

from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings
from openlp.plugins.bibles.forms.bibleimportform import BibleImportForm, PYSWORD_AVAILABLE
from openlp.plugins.bibles.lib.manager import BibleFormat
from openlp.plugins.bibles.lib.bibleimport import ImportFailure


@pytest.fixture
def import_form(registry: Registry, settings: Settings) -> BibleImportForm:
    registry.register('main_window', MagicMock())
    yield BibleImportForm(None, MagicMock(), MagicMock())


@patch('openlp.plugins.bibles.forms.bibleimportform.CWExtract.get_bibles_from_http')
@patch('openlp.plugins.bibles.forms.bibleimportform.BGExtract.get_bibles_from_http')
@patch('openlp.plugins.bibles.forms.bibleimportform.BSExtract.get_bibles_from_http')
def test_on_web_update_button_clicked(mocked_bsextract: MagicMock, mocked_bgextract: MagicMock,
                                      mocked_cwextract: MagicMock, import_form: BibleImportForm):
    """
    Test that on_web_update_button_clicked handles problems correctly
    """
    # GIVEN: Some mocked GUI components and mocked bibleextractors
    with patch.object(import_form, 'web_source_combo_box'), \
            patch.object(import_form, 'web_translation_combo_box'), \
            patch.object(import_form, 'web_update_button'), \
            patch.object(import_form, 'web_progress_bar'):
        mocked_bsextract.return_value = None
        mocked_bgextract.return_value = None
        mocked_cwextract.return_value = None

        # WHEN: Running on_web_update_button_clicked
        import_form.on_web_update_button_clicked()

    # THEN: The webbible list should still be empty
    assert import_form.web_bible_list == {}, 'The webbible list should be empty'


def test_custom_init(import_form: BibleImportForm):
    """
    Test that custom_init works as expected if pysword is unavailable
    """
    # GIVEN: A mocked sword_tab_widget
    with patch.object(import_form, 'sword_tab_widget') as mocked_tab_widget:

        # WHEN: Running custom_init
        import_form.custom_init()

    # THEN: sword_tab_widget.setDisabled(True) should have been called
    if not PYSWORD_AVAILABLE:
        mocked_tab_widget.setDisabled.assert_called_with(True)
    else:
        mocked_tab_widget.setDisabled.assert_not_called()


def test_help(import_form: BibleImportForm):
    """
    Test the help button
    """
    # WHEN: The Help button is clicked
    with patch.object(import_form, 'provide_help') as mocked_help:
        QtTest.QTest.mouseClick(import_form.button(QtWidgets.QWizard.WizardButton.HelpButton),
                                QtCore.Qt.MouseButton.LeftButton)

    # THEN: The Help function should be called
    mocked_help.assert_called_once()


def test_get_failure_feedback_with_actions(import_form: BibleImportForm):
    """
    Test that detailed failure feedback includes summary and action items.
    """
    importer = MagicMock()
    importer.stop_import_flag = False
    importer.import_failure = ImportFailure(
        code='csv-parse-failed',
        summary='Books CSV file could not be parsed.',
        details='Invalid delimiter detected.',
        actions=('Check CSV delimiter.', 'Re-export the source file.')
    )

    result = import_form.get_failure_feedback(importer, None)

    assert 'Your Bible import failed.' in result
    assert 'Books CSV file could not be parsed.' in result
    assert '- Check CSV delimiter.' in result
    assert '- Re-export the source file.' in result


def test_get_failure_feedback_for_cancelled_import(import_form: BibleImportForm):
    """
    Test that cancelled imports are reported as cancelled instead of failed.
    """
    importer = MagicMock()
    importer.stop_import_flag = False
    importer.import_failure = ImportFailure(
        code='language-selection-cancelled',
        summary='Import cancelled while selecting language.',
        is_user_cancelled=True
    )

    result = import_form.get_failure_feedback(importer, None)

    assert 'Bible import was cancelled.' in result
    assert 'Your Bible import failed.' not in result


@patch('openlp.plugins.bibles.forms.bibleimportform.delete_database')
def test_cleanup_failed_import_uses_file_path(mocked_delete_database: MagicMock, import_form: BibleImportForm):
    """
    Test that failed import cleanup removes cache entry and deletes DB using importer.file_path.
    """
    importer = MagicMock()
    importer.name = 'TestBible'
    importer.file_path = 'test-bible.sqlite'
    mocked_session = MagicMock()
    importer.session = mocked_session
    import_form.manager.db_cache = {'TestBible': importer}

    import_form.cleanup_failed_import(importer)

    assert 'TestBible' not in import_form.manager.db_cache
    mocked_session.rollback.assert_called_once()
    mocked_session.close.assert_called_once()
    mocked_delete_database.assert_called_once_with(import_form.plugin.settings_section, importer.file_path)


@pytest.mark.parametrize('file_name, xml_root, expected_format', [
    ('test.xml', '<osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace"></osis>', BibleFormat.OSIS),
    ('test.xml', '<bible></bible>', BibleFormat.OpenSong),
    ('test.xml', '<xmlbible></xmlbible>', BibleFormat.Zefania),
    ('test.xmm', '<xmlbible></xmlbible>', BibleFormat.Zefania),
])
def test_detect_bible_format_from_path(file_name: str, xml_root: str, expected_format: int,
                                       import_form: BibleImportForm, tmp_path):
    """
    Test XML format detection from root tags.
    """
    xml_path = tmp_path / file_name
    xml_path.write_text(xml_root, encoding='utf-8')

    detected_format, detected_name = import_form.detect_bible_format_from_path(xml_path)

    assert detected_format == expected_format
    assert detected_name is not None


def test_detect_bible_format_from_txt_csv_content(import_form: BibleImportForm, tmp_path):
    """
    Test CSV detection for .txt content.
    """
    txt_path = tmp_path / 'bible-books.txt'
    txt_path.write_text('1,1,Genesis,Gen\n2,1,Exodus,Exod\n', encoding='utf-8')

    detected_format, detected_name = import_form.detect_bible_format_from_path(txt_path)

    assert detected_format == BibleFormat.CSV
    assert detected_name == 'CSV text'


def test_on_format_source_path_changed_auto_switches_mismatch(import_form: BibleImportForm, tmp_path):
    """
    Test format auto-switch when selected source does not match expected format.
    """
    xml_path = tmp_path / 'test.xml'
    xml_path.write_text('<xmlbible></xmlbible>', encoding='utf-8')
    with patch.object(import_form, 'format_combo_box') as mocked_combo:
        import_form.on_format_source_path_changed(xml_path, BibleFormat.OSIS)

    mocked_combo.setCurrentIndex.assert_called_once_with(BibleFormat.Zefania)
    assert 'switched automatically' in import_form.format_hint_label.text()
