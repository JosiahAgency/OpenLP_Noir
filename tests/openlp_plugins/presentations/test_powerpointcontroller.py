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
Functional tests to test the PowerPointController class and related methods.
"""
import json
from PySide6 import QtCore
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch, mock_open
import pytest

from openlp.core.common.platform import is_win
from openlp.core.common.registry import Registry
from openlp.plugins.presentations.lib.powerpointcontroller import PowerpointController, PowerpointDocument, \
    _get_text_from_shapes
from tests.utils.constants import RESOURCE_PATH

if is_win():
    import pywintypes


@pytest.fixture()
def presentation_setup(settings):
    """
    Fixture to patch the _setup method of PresentationDocument to prevent actual PowerPoint interaction during tests.
    """
    with patch('openlp.plugins.presentations.lib.powerpointcontroller.PresentationDocument._setup') as mocked_setup:
        yield mocked_setup


def test_constructor(settings, mock_plugin):
    """
    Test the Constructor from the PowerpointController
    """
    # GIVEN: No presentation controller
    controller = None

    # WHEN: The presentation controller object is created
    controller = PowerpointController(plugin=mock_plugin)

    # THEN: The name of the presentation controller should be correct
    assert 'Powerpoint' == controller.name, 'The name of the presentation controller should be correct'


def test_show_error_msg(presentation_setup):
    """
    Test the PowerpointDocument.show_error_msg() method gets called on com exception
    """
    if is_win():
        # GIVEN: A PowerpointDocument with mocked controller and presentation
        with patch('openlp.plugins.presentations.lib.powerpointcontroller.critical_error_message_box') as \
                mocked_critical_error_message_box:
            instance = PowerpointDocument(MagicMock(), MagicMock())
            instance.presentation = MagicMock()
            instance.presentation.SlideShowWindow.View.GotoSlide = MagicMock(side_effect=pywintypes.com_error('1'))
            instance.index_map[42] = 42

            # WHEN: Calling goto_slide which will throw an exception
            instance.goto_slide(42)

            # THEN: mocked_critical_error_message_box should have been called
            mocked_critical_error_message_box.assert_called_with('Error', 'An error occurred in the PowerPoint '
                                                                 'integration and the presentation will be stopped.'
                                                                 ' Restart the presentation if you wish to '
                                                                 'present it.')


def test_export_presentation_data_skips_if_already_exists(presentation_setup):
    """
    Test that export_presentation_data does nothing if data already exists.
    """
    # GIVEN: A document where export data already exists
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.check_exported_presentation_data_exists = MagicMock(return_value=True)
    doc.save_titles_and_notes = MagicMock()

    # WHEN: export_presentation_data is called
    doc.export_presentation_data()

    # THEN: It should return early without saving or processing
    doc.save_titles_and_notes.assert_not_called()


@patch('openlp.plugins.presentations.lib.powerpointcontroller._get_text_from_shapes', return_value='NoteText')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.PresentationDocument.get_thumbnail_folder')
def test_export_presentation_data_exports_all(mocked_get_thumb_folder, mock_get_text, presentation_setup):
    """
    Test that export_presentation_data creates thumbnails, saves titles and notes,
    updates index_map, and writes index_map.txt file.
    """
    # GIVEN: A presentation with 2 visible slides and titles/notes
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.check_exported_presentation_data_exists = MagicMock(return_value=False)
    doc.save_titles_and_notes = MagicMock()
    mocked_get_thumb_folder.return_value = Path('/mocked/thumb/folder')
    doc.index_map = {}
    slide1 = MagicMock()
    slide1.SlideShowTransition.Hidden = False
    slide1.Shapes.Title.TextFrame.TextRange.Text = 'Title 1'
    slide1.Export = MagicMock()
    slide2 = MagicMock()
    slide2.SlideShowTransition.Hidden = False
    slide2.Shapes.Title.TextFrame.TextRange.Text = 'Title 2'
    slide2.Export = MagicMock()
    doc.presentation = MagicMock()
    doc.presentation.Slides.Count = 2
    doc.presentation.Slides.side_effect = lambda i: [slide1, slide2][i - 1]
    doc.presentation.PageSetup.SlideWidth = 1280
    doc.presentation.PageSetup.SlideHeight = 720

    # WHEN: export_presentation_data is called
    with patch('builtins.open', mock_open()) as mock_file:
        doc.export_presentation_data()

    # THEN: Titles and notes are saved, thumbnails exported, index updated
    assert doc.index_map == {1: 1, 2: 2}
    assert doc.slide_count == 2
    doc.save_titles_and_notes.assert_called_once_with(['Title 1', 'Title 2'], ['NoteText', 'NoteText'])
    slide1.Export.assert_called_once()
    slide2.Export.assert_called_once()
    mock_file.assert_called_with(Path('/mocked/thumb/folder') / "index_map.txt", "w", encoding='utf-8')


@patch('openlp.plugins.presentations.lib.powerpointcontroller._get_text_from_shapes', return_value='Note')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.PresentationDocument.get_thumbnail_folder')
def test_export_presentation_data_skips_hidden_slides(mocked_get_thumb_folder, mock_get_text, presentation_setup):
    """
    Test that export_presentation_data skips hidden slides and only exports visible ones.
    """
    # GIVEN: A presentation with 3 slides, where 1 is hidden
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.check_exported_presentation_data_exists = MagicMock(return_value=False)
    doc.save_titles_and_notes = MagicMock()
    mocked_get_thumb_folder.return_value = Path('/mocked/thumb/folder')
    doc.index_map = {}
    slide1 = MagicMock()
    slide1.SlideShowTransition.Hidden = False
    slide1.Shapes.Title.TextFrame.TextRange.Text = 'Title 1'
    slide1.Export = MagicMock()
    slide2 = MagicMock()
    slide2.SlideShowTransition.Hidden = True
    slide3 = MagicMock()
    slide3.SlideShowTransition.Hidden = False
    slide3.Shapes.Title.TextFrame.TextRange.Text = 'Title 3'
    slide3.Export = MagicMock()
    slides = [slide1, slide2, slide3]
    doc.presentation = MagicMock()
    doc.presentation.Slides.Count = 3
    doc.presentation.Slides.side_effect = lambda i: slides[i - 1]
    doc.presentation.PageSetup.SlideWidth = 1280
    doc.presentation.PageSetup.SlideHeight = 720

    # WHEN: export_presentation_data is called
    with patch('builtins.open', mock_open()):
        doc.export_presentation_data()

    # THEN: Only visible slides are processed
    assert doc.index_map == {1: 1, 2: 3}
    assert doc.slide_count == 2
    doc.save_titles_and_notes.assert_called_once_with(['Title 1', 'Title 3'], ['Note', 'Note'])
    slide1.Export.assert_called_once()
    slide2.Export.assert_not_called()
    slide3.Export.assert_called_once()


@patch('openlp.plugins.presentations.lib.powerpointcontroller._get_text_from_shapes', return_value='NoteText')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.PresentationDocument.get_thumbnail_folder')
def test_export_presentation_data_title_exception_handled(mocked_get_thumb_folder, mock_get_text, presentation_setup):
    """
    Test that export_presentation_data handles exceptions when accessing slide title.
    """
    # GIVEN: A slide that raises exception when accessing title text
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.check_exported_presentation_data_exists = MagicMock(return_value=False)
    doc.save_titles_and_notes = MagicMock()
    mocked_get_thumb_folder.return_value = Path('/mocked/thumb/folder')
    doc.index_map = {}
    slide = MagicMock()
    slide.SlideShowTransition.Hidden = False
    type(slide.Shapes.Title.TextFrame.TextRange).Text = PropertyMock(side_effect=Exception("Title error"))
    slide.Export = MagicMock()
    doc.presentation = MagicMock()
    doc.presentation.Slides.Count = 1
    doc.presentation.Slides.side_effect = lambda i: slide
    doc.presentation.PageSetup.SlideWidth = 1280
    doc.presentation.PageSetup.SlideHeight = 720

    # WHEN: export_presentation_data is called
    with patch('builtins.open', mock_open()):
        doc.export_presentation_data()

    # THEN: Empty title should be handled and saved
    doc.save_titles_and_notes.assert_called_once_with([''], ['NoteText'])


def test_check_exported_data_returns_true_if_data_exists(presentation_setup):
    """
    Test that check_exported_presentation_data_exists returns True if index_map and slide_count are already set.
    """
    # GIVEN: A document with index_map and non-zero slide_count
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.index_map = {1: 1}
    doc.slide_count = 1

    # WHEN: check_exported_presentation_data_exists is called
    result = doc.check_exported_presentation_data_exists()

    # THEN: It should return True
    assert result is True


@patch('openlp.plugins.presentations.lib.powerpointcontroller.PresentationDocument.get_thumbnail_folder')
def test_check_exported_data_reads_index_map_as_dict(mock_get_thumb_folder, presentation_setup):
    """
    Test that check_exported_presentation_data_exists reads the index_map from file and ensures it's a dictionary.
    """
    # GIVEN: A valid index_map.txt file with dictionary data
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.index_map = None
    doc.slide_count = 0
    mock_folder = Path('/mocked/thumb/folder')
    mock_get_thumb_folder.return_value = mock_folder

    index_map_data = {'1': 1, '2': 2}
    with patch('pathlib.Path.is_file', return_value=True), \
         patch('builtins.open', mock_open(read_data=json.dumps(index_map_data))):

        # WHEN: check_exported_presentation_data_exists is called
        result = doc.check_exported_presentation_data_exists()

    # THEN: It should return True, and index_map should be a dictionary
    assert result is True
    assert isinstance(doc.index_map, dict), "Expected index_map to be a dictionary"
    assert doc.index_map == index_map_data
    assert doc.slide_count == 2


@patch('openlp.plugins.presentations.lib.powerpointcontroller.PresentationDocument.get_thumbnail_folder')
def test_check_exported_data_returns_false_on_file_error(mock_get_thumb_folder, presentation_setup):
    """
    Test that check_exported_presentation_data_exists returns False if index_map.txt is missing or causes an exception.
    """
    # GIVEN: No index_map and missing or broken index_map.txt
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.index_map = None
    doc.slide_count = 0
    mock_folder = Path('/mocked/thumb/folder')
    mock_get_thumb_folder.return_value = mock_folder

    # WHEN: File does not exist
    with patch('pathlib.Path.is_file', return_value=False):
        result = doc.check_exported_presentation_data_exists()

        # THEN: result should be False
        assert result is False

    # WHEN: File exists but reading it raises exception
    with patch('pathlib.Path.is_file', return_value=True), \
         patch('builtins.open', side_effect=IOError("boom")):
        result = doc.check_exported_presentation_data_exists()

        # THEN: result should be False
        assert result is False


def test_get_text_from_shapes():
    """
    Test getting text from powerpoint shapes
    """
    # GIVEN: mocked shapes
    shape = MagicMock()
    shape.PlaceholderFormat.Type = 2
    shape.HasTextFrame = shape.TextFrame.HasText = True
    shape.TextFrame.TextRange.Text = 'slideText'
    shapes = [shape, shape]

    # WHEN: getting the text
    result = _get_text_from_shapes(shapes)

    # THEN: it should return the text
    assert result == 'slideText\nslideText\n', 'result should match \'slideText\nslideText\n\''


def test_get_text_from_shapes_with_no_shapes():
    """
    Test getting text from powerpoint shapes with no shapes
    """
    # GIVEN: empty shapes array
    shapes = []

    # WHEN: getting the text
    result = _get_text_from_shapes(shapes)

    # THEN: it should not fail but return empty string
    assert result == '', 'result should be empty'


@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
def test_get_QRect_from_current_powerpoint_window_position(mocked_screen_list, presentation_setup):
    """
    Test that _get_QRect_from_current_powerpoint_window_position calculates QRect correctly based on DPI.
    """
    # GIVEN: A PowerPointDocument with a SlideShowWindow and the DPI of the current screen
    doc = PowerpointDocument(MagicMock(), MagicMock())
    mocked_presentation = MagicMock()
    mocked_slide_show_window = MagicMock()
    mocked_slide_show_window.Left = 100
    mocked_slide_show_window.Top = 150
    mocked_slide_show_window.Width = 1024
    mocked_slide_show_window.Height = 768
    doc.presentation = mocked_presentation
    doc.presentation.SlideShowWindow = mocked_slide_show_window
    mocked_dpi = 96
    mocked_screen = mocked_screen_list.return_value.current
    mocked_screen.raw_screen.logicalDotsPerInch.return_value = mocked_dpi

    # WHEN: Calling the method to get QRect
    rect = doc._get_QRect_from_current_powerpoint_window_position()

    # THEN: The returned QRect should have this values
    assert isinstance(rect, QtCore.QRect)
    assert rect.left() == int(100 * 96 / 72)
    assert rect.top() == int(150 * 96 / 72)
    assert rect.width() == int(1024 * 96 / 72)
    assert rect.height() == int(768 * 96 / 72)


def test_get_QRect_from_current_powerpoint_window_position_with_no_presentation(presentation_setup):
    """
    Test that _get_QRect_from_current_powerpoint_window_position returns False when presentation is None.
    """
    # GIVEN: A PowerPointDocument without a presentation
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.presentation = None

    # WHEN: Calling the method to get QRect
    result = doc._get_QRect_from_current_powerpoint_window_position()

    # THEN: It should return False, indicating it could not compute the position
    assert result is False


@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
def test_get_QRect_from_current_powerpoint_window_position_raises_exception(mocked_screen_list, presentation_setup):
    """
    Test that _get_QRect_from_current_powerpoint_window_position returns False if an exception is raised.
    """
    # GIVEN: A PowerPointDocument with a presentation that raises an exception when accessing SlideShowWindow
    doc = PowerpointDocument(MagicMock(), MagicMock())
    mocked_presentation = MagicMock()
    doc.presentation = mocked_presentation
    mocked_screen_list.return_value.current.raw_screen.logicalDotsPerInch.side_effect = AttributeError("DPI fail")

    # WHEN: Calling the method to get QRect
    result = doc._get_QRect_from_current_powerpoint_window_position()

    # THEN: It should return False due to the exception
    assert result is False


def test_goto_slide(presentation_setup):
    """
    Test that goto_slide goes to next effect if the slide is already displayed
    """
    # GIVEN: A Document with mocked controller, presentation, and mocked functions get_slide_number and next_step
    Registry().get('settings').setValue('presentations/powerpoint slide click advance', True)
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.presentation = MagicMock()
    doc.presentation.SlideShowWindow.View.GetClickIndex.return_value = 1
    doc.presentation.SlideShowWindow.View.GetClickCount.return_value = 2
    doc.get_slide_number = MagicMock()
    doc.get_slide_number.return_value = 1
    doc.next_step = MagicMock()
    doc.index_map[1] = 1

    # WHEN: Calling goto_slide
    doc.goto_slide(1)

    # THEN: next_step() should be call to try to advance to the next effect.
    assert doc.next_step.called is True, 'next_step() should have been called!'


def test_goto_slide_with_string_slide_number(presentation_setup):
    """
    Test that goto_slide accepts string slide numbers without raising KeyError.
    """
    # GIVEN: A document with a string index map and a mocked PowerPoint view
    Registry().get('settings').setValue('presentations/powerpoint slide click advance', False)
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.presentation = MagicMock()
    doc.index_map = {'1': 1}

    # WHEN: goto_slide is called
    doc.goto_slide(1)

    # THEN: The view should jump to the mapped slide index without crashing
    doc.presentation.SlideShowWindow.View.GotoSlide.assert_called_once_with(1)


def test_blank_screen(presentation_setup):
    """
    Test that blank_screen works as expected
    """
    # GIVEN: A Document with mocked controller, presentation, and mocked function get_slide_number
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.presentation = MagicMock()
    doc.presentation.SlideShowWindow.View.GetClickIndex.return_value = 3
    doc.presentation.Application.Version = 14.0
    doc.get_slide_number = MagicMock()
    doc.get_slide_number.return_value = 2

    # WHEN: Calling goto_slide
    doc.blank_screen()

    # THEN: The view state, doc.blank_slide and doc.blank_click should have new values
    assert doc.presentation.SlideShowWindow.View.State == 3, 'The View State should be 3'
    assert doc.blank_slide == 2, 'doc.blank_slide should be 2 because of the PowerPoint version'
    assert doc.blank_click == 3, 'doc.blank_click should be 3 because of the PowerPoint version'


def test_unblank_screen(presentation_setup):
    """
    Test that unblank_screen works as expected
    """
    # GIVEN: A Document with mocked controller, presentation, ScreenList, and mocked function get_slide_number
    with patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList') as mocked_screen_list:
        mocked_screen_list_ret = MagicMock()
        mocked_screen_list_ret.screen_list = [1]
        mocked_screen_list.return_value = mocked_screen_list_ret
        doc = PowerpointDocument(MagicMock(), MagicMock())
        doc.presentation = MagicMock()
        doc.presentation.SlideShowWindow.View.GetClickIndex.return_value = 3
        doc.presentation.Application.Version = 14.0
        doc.get_slide_number = MagicMock()
        doc.get_slide_number.return_value = 2
        doc.index_map[1] = 1
        doc.blank_slide = 1
        doc.blank_click = 1

        # WHEN: Calling goto_slide
        doc.unblank_screen()

        # THEN: The view state have new value, and several function should have been called
        assert doc.presentation.SlideShowWindow.View.State == 1, 'The View State should be 1'
        assert doc.presentation.SlideShowWindow.Activate.called is True, \
            'SlideShowWindow.Activate should have been called'
        assert doc.presentation.SlideShowWindow.View.GotoSlide.called is True, \
            'View.GotoSlide should have been called because of the PowerPoint version'
        assert doc.presentation.SlideShowWindow.View.GotoClick.called is True, \
            'View.GotoClick should have been called because of the PowerPoint version'


@pytest.mark.parametrize('file_path, expected_is_in_cloud, expected_same_file_name', [
    (RESOURCE_PATH / 'presentations' / 'test.pptx', False, True),
    (Path('test.pptx'), True, False)
])
def test_presentation_is_in_cloud(file_path, expected_is_in_cloud, expected_same_file_name,
                                  registry, settings):
    """
    Test that a presentation from a cloud drive is being detected.
    """
    # GIVEN: A Document with mocked controller and presentation.
    mocked_plugin = MagicMock()
    mocked_plugin.settings_section = 'presentations'
    ppc = PowerpointController(mocked_plugin)
    doc = PowerpointDocument(ppc, file_path)
    doc.presentation = MagicMock(FullName=file_path)
    if expected_is_in_cloud:
        doc.presentation = MagicMock(FullName='https://' + str(file_path))
    else:
        doc.presentation = MagicMock(FullName=str(file_path))
    assert doc.is_in_cloud == expected_is_in_cloud, \
        'is_in_cloud should be false because this file is locally stored'
    assert (doc.presentation_file == doc.presentation_controller_file) == expected_same_file_name, \
        'presentation_file should have the same value as presentation_controller_file'


def test_get_slide_count_returns_cached_count(presentation_setup):
    """
    Test get_slide_count returns precomputed slide count without triggering export.
    """
    # GIVEN: A loaded presentation with a precomputed slide_count and index_map
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.slide_count = 5
    doc.index_map = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
    doc.is_loaded = MagicMock(return_value=True)
    doc.export_presentation_data = MagicMock()

    # WHEN: get_slide_count is called
    count = doc.get_slide_count()

    # THEN: It should return the existing slide_count and not call export_presentation_data
    assert count == 5
    doc.export_presentation_data.assert_not_called()


def test_get_slide_count_triggers_export_when_needed(presentation_setup):
    """
    Test get_slide_count triggers export if slide_count is zero and index_map is empty.
    """
    # GIVEN: A presentation with no cached slide_count or index_map
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.slide_count = 0
    doc.index_map = {}
    doc.is_loaded = MagicMock(return_value=True)
    doc.export_presentation_data = MagicMock()
    doc.export_presentation_data.side_effect = lambda: setattr(doc, 'slide_count', 3)

    # WHEN: get_slide_count is called
    count = doc.get_slide_count()

    # THEN: It should call export_presentation_data and return the new slide_count
    doc.export_presentation_data.assert_called_once()
    assert count == 3


def test_get_slide_count_does_not_export_if_not_loaded(presentation_setup):
    """
    Test get_slide_count does not trigger export if presentation is not loaded.
    """
    # GIVEN: A presentation with no cached data and not loaded
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.slide_count = 0
    doc.index_map = {}
    doc.is_loaded = MagicMock(return_value=False)
    doc.export_presentation_data = MagicMock()

    # WHEN: get_slide_count is called
    count = doc.get_slide_count()

    # THEN: It should return 0 and not attempt to export data
    assert count == 0
    doc.export_presentation_data.assert_not_called()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32gui')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32con')
def test_is_active_view_state_paused(mocked_win32con, mocked_win32gui, presentation_setup):
    """
    Test that is_active calls Activate and FlashWindowEx when View.State is paused (2).
    """
    # GIVEN: A PowerpointDocument with paused View state
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.is_loaded = MagicMock(return_value=True)
    doc.presentation = MagicMock()
    slide_show_window = MagicMock()
    view = MagicMock()
    view.State = 2
    slide_show_window.View = view
    doc.presentation.SlideShowWindow = slide_show_window
    doc.presentation_hwnd = 123

    # WHEN: Calling is_active
    result = doc.is_active()

    # THEN: Activate should be called and FlashWindowEx should be called
    slide_show_window.Activate.assert_called_once()
    mocked_win32gui.FlashWindowEx.assert_called_once_with(123, mocked_win32con.FLASHW_STOP, 0, 0)
    assert result is True


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
def test_is_active_true(presentation_setup):
    """
    Test that is_active returns True when presentation and its slideshow window/view are all valid.
    """
    # GIVEN: A PowerpointDocument with a loaded presentation and valid SlideShowWindow and View
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.is_loaded = MagicMock(return_value=True)
    doc.presentation = MagicMock()
    doc.presentation.SlideShowWindow = MagicMock()
    doc.presentation.SlideShowWindow.View = MagicMock()

    # WHEN: Calling is_active
    result = doc.is_active()

    # THEN: It should return True
    assert result is True


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
def test_is_active_not_loaded(presentation_setup):
    """
    Test that is_active returns False when presentation is not loaded.
    """
    # GIVEN: A PowerpointDocument where is_loaded returns False
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.is_loaded = MagicMock(return_value=False)

    # WHEN: Calling is_active
    result = doc.is_active()

    # THEN: It should return False
    assert result is False


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
def test_is_active_no_slideshow_window(presentation_setup):
    """
    Test that is_active returns False when SlideShowWindow is None.
    """
    # GIVEN: A PowerpointDocument with a loaded presentation and no SlideShowWindow
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.is_loaded = MagicMock(return_value=True)
    doc.presentation = MagicMock()
    doc.presentation.SlideShowWindow = None

    # WHEN: Calling is_active
    result = doc.is_active()

    # THEN: It should return False
    assert result is False


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
def test_is_active_no_view(presentation_setup):
    """
    Test that is_active returns False when SlideShowWindow.View is None.
    """
    # GIVEN: A PowerpointDocument with SlideShowWindow but no View
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.is_loaded = MagicMock(return_value=True)
    doc.presentation = MagicMock()
    doc.presentation.SlideShowWindow = MagicMock()
    doc.presentation.SlideShowWindow.View = None

    # WHEN: Calling is_active
    result = doc.is_active()

    # THEN: It should return False
    assert result is False


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
def test_is_active_com_error_known(presentation_setup):
    """
    Test that is_active handles a known COM error (-2147188160) and returns False.
    """
    # GIVEN: A PowerpointDocument that raises a known COM error from SlideShowWindow
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.is_loaded = MagicMock(return_value=True)
    com_error = pywintypes.com_error()
    com_error.excepinfo = [None] * 5 + [-2147188160]
    doc.presentation = MagicMock()
    type(doc.presentation).SlideShowWindow = PropertyMock(side_effect=com_error)

    # WHEN: Calling is_active
    with patch('openlp.plugins.presentations.lib.powerpointcontroller.log') as mocked_log, \
            patch('openlp.plugins.presentations.lib.powerpointcontroller.trace_error_handler') \
            as mocked_trace_error_handler:
        result = doc.is_active()

    # THEN: It should return False and NOT log an exception
    assert result is False
    mocked_log.exception.assert_not_called()
    mocked_trace_error_handler.assert_not_called()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
def test_is_active_com_error_unknown(presentation_setup):
    """
    Test that is_active logs and traces unexpected COM errors and returns False.
    """
    # GIVEN: A PowerpointDocument that raises an unknown COM error from SlideShowWindow
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.is_loaded = MagicMock(return_value=True)
    com_error = pywintypes.com_error()
    com_error.excepinfo = [None] * 6
    doc.presentation = MagicMock()
    type(doc.presentation).SlideShowWindow = PropertyMock(side_effect=com_error)

    # WHEN: Calling is_active
    with patch('openlp.plugins.presentations.lib.powerpointcontroller.log') as mocked_log, \
            patch('openlp.plugins.presentations.lib.powerpointcontroller.trace_error_handler') \
            as mocked_trace_error_handler:
        result = doc.is_active()

    # THEN: It should return False, log the exception, and call the error handler
    assert result is False
    mocked_log.exception.assert_called_once()
    mocked_trace_error_handler.assert_called_once()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
def test_stop_presentation_success(presentation_setup):
    """
    Test that stop_presentation sets ShowType, exits the slideshow, and reloads presentation
    if ghost window was closed.
    """
    # GIVEN: A PowerPointDocument with a visible presentation and ghost window
    doc = PowerpointDocument(MagicMock(), MagicMock())
    mocked_presentation = MagicMock()
    mocked_slide_show_settings = MagicMock()
    mocked_slide_show_settings.ShowType = 2
    mocked_slide_show_window = MagicMock()
    mocked_slide_show_window.View = MagicMock()
    doc.presentation = mocked_presentation
    doc.presentation.SlideShowSettings = mocked_slide_show_settings
    doc.presentation.SlideShowWindow = mocked_slide_show_window

    # WHEN: Calling stop_presentation
    with patch.object(doc, '_get_QRect_from_current_powerpoint_window_position') as mocked_get_qrect, \
            patch.object(doc, 'close_powerpoint_ghost_window') as mocked_close, \
            patch.object(doc, 'load_presentation') as mocked_reload:
        mocked_get_qrect.return_value = QtCore.QRect(100, 100, 800, 600)
        doc.stop_presentation()

    # THEN: View should be exited, and ghost window logic should trigger reload
    assert mocked_slide_show_settings.ShowType == 4
    mocked_slide_show_window.View.Exit.assert_called_once()
    mocked_close.assert_called_once()
    mocked_reload.assert_called_once()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
def test_stop_presentation_no_ghost_window(mocked_screen_list, presentation_setup):
    """
    Test that stop_presentation exits the slideshow without checking for ghost windows when ShowType != 2.
    """
    # GIVEN: A PowerPointDocument with ShowType not triggering ghost window logic
    doc = PowerpointDocument(MagicMock(), MagicMock())
    mocked_presentation = MagicMock()
    mocked_slide_show_settings = MagicMock()
    mocked_slide_show_settings.ShowType = 1
    mocked_slide_show_window = MagicMock()
    mocked_slide_show_window.View = MagicMock()
    doc.presentation = mocked_presentation
    doc.presentation.SlideShowSettings = mocked_slide_show_settings
    doc.presentation.SlideShowWindow = mocked_slide_show_window

    # WHEN: Calling stop_presentation without triggering ghost window logic
    with patch.object(doc, 'close_powerpoint_ghost_window') as mocked_close, \
            patch.object(doc, 'load_presentation') as mocked_reload:
        doc.stop_presentation()

    # THEN: The slideshow should exit, but ghost window cleanup and reload should not be triggered
    assert mocked_slide_show_settings.ShowType == 4
    mocked_slide_show_window.View.Exit.assert_called_once()
    mocked_close.assert_not_called()
    mocked_reload.assert_not_called()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
def test_stop_presentation_ghost_window_not_closed(presentation_setup):
    """
    Test that load_presentation is NOT called if the ghost window exists but is not closed successfully.
    """
    # GIVEN: A PowerPointDocument with ShowType == 2 and a defined SlideShowWindow
    doc = PowerpointDocument(MagicMock(), MagicMock())
    mocked_presentation = MagicMock()
    mocked_slide_show_settings = MagicMock()
    mocked_slide_show_settings.ShowType = 2
    mocked_slide_show_window = MagicMock()
    mocked_slide_show_window.View = MagicMock()
    doc.presentation = mocked_presentation
    doc.presentation.SlideShowSettings = mocked_slide_show_settings
    doc.presentation.SlideShowWindow = mocked_slide_show_window

    # WHEN: Calling stop_presentation and ghost window is not closed
    with patch.object(doc, '_get_QRect_from_current_powerpoint_window_position') as mocked_get_qrect, \
            patch.object(doc, 'close_powerpoint_ghost_window', return_value=False) as mocked_close, \
            patch.object(doc, 'load_presentation') as mocked_reload:
        mocked_get_qrect.return_value = QtCore.QRect(100, 100, 800, 600)
        doc.stop_presentation()

    # THEN: Ghost window should be checked, but load_presentation should not be triggered
    mocked_slide_show_window.View.Exit.assert_called_once()
    mocked_close.assert_called_once()
    mocked_reload.assert_not_called()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
def test_stop_presentation_exception_handling(presentation_setup):
    """
    Test that stop_presentation handles exceptions and logs the error correctly.
    """
    # GIVEN: A PowerPointDocument with a SlideShowWindow that raises AttributeError
    doc = PowerpointDocument(MagicMock(), MagicMock())
    com_error = pywintypes.com_error()
    doc.presentation = MagicMock()
    type(doc.presentation).SlideShowWindow = PropertyMock(side_effect=com_error)

    # WHEN: Calling stop_presentation and encountering an exception
    with patch('openlp.plugins.presentations.lib.powerpointcontroller.log') as mocked_log, \
            patch('openlp.plugins.presentations.lib.powerpointcontroller.trace_error_handler') as mocked_trace, \
            patch.object(doc, 'show_error_msg') as mocked_error:
        doc.stop_presentation()

    # THEN: The error should be logged, traced, and the user should be notified
    mocked_log.exception.assert_called_once_with('Caught exception while in stop_presentation')
    mocked_trace.assert_called_once_with(mocked_log)
    mocked_error.assert_called_once()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.Registry')
def test_close_presentation_with_ghost_window(mocked_registry, mocked_screen_list,
                                              presentation_setup):
    """
    Test that close_presentation closes the presentation and handles ghost window detection when ShowType is 2.
    """
    # GIVEN: A presentation with ShowType 2 (indicating ghost window logic)
    doc = PowerpointDocument(MagicMock(), MagicMock())
    mocked_presentation = MagicMock()
    mocked_slide_show_settings = MagicMock()
    mocked_slide_show_settings.ShowType = 2
    doc.presentation = mocked_presentation
    mocked_presentation.SlideShowSettings = mocked_slide_show_settings
    mocked_controller = MagicMock()
    doc.controller = mocked_controller
    mocked_registry_instance = MagicMock()
    mocked_registry.return_value = mocked_registry_instance
    mocked_main_window = MagicMock()
    mocked_registry_instance.get.return_value = mocked_main_window
    mocked_screen_list.return_value.__len__.return_value = 2

    # WHEN: Calling close_presentation
    with patch.object(doc, '_get_QRect_from_current_powerpoint_window_position') as mocked_get_qrect, \
            patch.object(doc, 'close_powerpoint_ghost_window') as mocked_close_ghost:
        mocked_get_qrect.return_value = QtCore.QRect(100, 100, 800, 600)
        doc.close_presentation()

    # THEN: The presentation is closed and ghost window handling is called
    mocked_presentation.Close.assert_called_once()
    mocked_close_ghost.assert_called_once()
    assert doc.presentation is None
    mocked_controller.remove_doc.assert_called_once_with(doc)
    mocked_main_window.activateWindow.assert_called_once()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.Registry')
def test_close_presentation_without_ghost_window(mocked_registry, mocked_screen_list,
                                                 presentation_setup):
    """
    Test that close_presentation closes the presentation when ShowType is not 2,
    without calling ghost window handling.
    """
    # GIVEN: A presentation with ShowType other than 2
    doc = PowerpointDocument(MagicMock(), MagicMock())
    mocked_presentation = MagicMock()
    mocked_slide_show_settings = MagicMock()
    mocked_slide_show_settings.ShowType = 1
    mocked_presentation.SlideShowSettings = mocked_slide_show_settings
    doc.presentation = mocked_presentation
    mocked_controller = MagicMock()
    doc.controller = mocked_controller
    mocked_registry_instance = MagicMock()
    mocked_registry.return_value = mocked_registry_instance
    mocked_main_window = MagicMock()
    mocked_registry_instance.get.return_value = mocked_main_window
    mocked_screen_list.return_value.__len__.return_value = 2

    # WHEN: Calling close_presentation
    with patch.object(doc, 'close_powerpoint_ghost_window') as mocked_close_ghost:
        doc.close_presentation()

    # THEN: Presentation is closed but ghost window handler is not called
    mocked_presentation.Close.assert_called_once()
    mocked_close_ghost.assert_not_called()
    assert doc.presentation is None
    mocked_controller.remove_doc.assert_called_once_with(doc)
    mocked_main_window.activateWindow.assert_called_once()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.Registry')
def test_close_presentation_no_current_window_position(mocked_registry, mocked_screen_list,
                                                       presentation_setup):
    """
    Test that close_presentation closes the presentation and handles ghost window detection when ShowType is 2.
    """
    # GIVEN: A presentation with ShowType 2 (indicating ghost window logic)
    doc = PowerpointDocument(MagicMock(), MagicMock())
    mocked_presentation = MagicMock()
    mocked_slide_show_settings = MagicMock()
    mocked_slide_show_settings.ShowType = 2
    doc.presentation = mocked_presentation
    mocked_presentation.SlideShowSettings = mocked_slide_show_settings
    mocked_controller = MagicMock()
    doc.controller = mocked_controller
    mocked_registry_instance = MagicMock()
    mocked_registry.return_value = mocked_registry_instance
    mocked_main_window = MagicMock()
    mocked_registry_instance.get.return_value = mocked_main_window
    mocked_screen_list.return_value.__len__.return_value = 2

    # WHEN: Calling close_presentation
    with patch.object(doc, '_get_QRect_from_current_powerpoint_window_position') as mocked_get_qrect, \
            patch.object(doc, 'close_powerpoint_ghost_window') as mocked_close_ghost:
        mocked_get_qrect.return_value = False
        doc.close_presentation()

    # THEN: The presentation is closed and ghost window handling is called
    mocked_presentation.Close.assert_called_once()
    mocked_close_ghost.assert_not_called()
    assert doc.presentation is None
    mocked_controller.remove_doc.assert_called_once_with(doc)
    mocked_main_window.activateWindow.assert_called_once()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.Registry')
def test_close_presentation_with_exception(mocked_registry, mocked_screen_list,
                                           presentation_setup):
    """
    Test that close_presentation logs and handles an exception during presentation closing.
    """
    # GIVEN: A presentation that raises an exception during close
    doc = PowerpointDocument(MagicMock(), MagicMock())
    mocked_presentation = MagicMock()
    mocked_presentation.SlideShowSettings.ShowType = 2
    mocked_presentation.Close.side_effect = AttributeError('Close failure')
    mocked_presentation.SlideShowWindow = MagicMock()
    doc.presentation = mocked_presentation
    mocked_controller = MagicMock()
    doc.controller = mocked_controller
    mocked_registry_instance = MagicMock()
    mocked_registry.return_value = mocked_registry_instance
    mocked_registry_instance.get.return_value = MagicMock()
    mocked_screen_list.return_value.__len__.return_value = 2

    # WHEN: Calling close_presentation and expecting exception to be handled
    with patch('openlp.plugins.presentations.lib.powerpointcontroller.log') as mocked_log, \
            patch('openlp.plugins.presentations.lib.powerpointcontroller.trace_error_handler') as mocked_trace:
        doc.close_presentation()

    # THEN: Exception should be logged, and cleanup still performed
    mocked_log.exception.assert_called_once_with('Caught exception while closing powerpoint presentation')
    mocked_trace.assert_called_once_with(mocked_log)
    assert doc.presentation is None
    mocked_controller.remove_doc.assert_called_once_with(doc)


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.Registry')
def test_close_presentation_no_presentation(mocked_registry, mocked_screen_list,
                                            presentation_setup):
    """
    Test that close_presentation skips closing logic if no presentation is loaded.
    """
    # GIVEN: A document with no active presentation
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.presentation = None
    doc.controller = MagicMock()
    mocked_registry_instance = MagicMock()
    mocked_registry.return_value = mocked_registry_instance
    mocked_registry_instance.get.return_value = MagicMock()
    mocked_screen_list.return_value.__len__.return_value = 2

    # WHEN: Calling close_presentation
    with patch('openlp.plugins.presentations.lib.powerpointcontroller.log') as mocked_log:
        doc.close_presentation()

    # THEN: Nothing is closed, but cleanup proceeds
    doc.controller.remove_doc.assert_called_once_with(doc)
    mocked_log.debug.assert_called_once_with('close_presentation')


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32gui')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.Registry')
def test_start_presentation_success(mocked_registry, mocked_screen_list,
                                    mocked_win32gui, presentation_setup):
    """
    Test that start_presentation correctly initializes and starts the PowerPoint slideshow,
    and that modify_powerpoint_display_monitor and activateWindow are called correctly.
    """
    # GIVEN: A PowerPointDocument instance, mocked dependencies, and a presentation instance
    doc = PowerpointDocument(MagicMock(), MagicMock())
    ppt_window_mock = MagicMock()
    mocked_slide_show_settings = MagicMock()
    mocked_slide_show_settings.Run.return_value = ppt_window_mock
    mocked_presentation = MagicMock()
    mocked_presentation.SlideShowSettings = mocked_slide_show_settings
    mocked_presentation.SlideShowSettings.ShowType = None
    mocked_presentation.SlideShowSettings.ShowPresenterView = None
    doc.presentation = mocked_presentation
    mocked_registry_instance = MagicMock()
    mocked_registry.return_value = mocked_registry_instance
    mocked_main_window = MagicMock()
    mocked_settings = MagicMock()
    mocked_registry_instance.get.side_effect = (
        lambda key: mocked_main_window if key == 'main_window'
        else mocked_settings)
    mocked_main_window.activateWindow = MagicMock()
    mocked_settings.value.return_value = QtCore.Qt.CheckState.Unchecked
    mocked_geometry = MagicMock()
    mocked_geometry.x.return_value = 0
    mocked_geometry.y.return_value = 0
    mocked_geometry.width.return_value = 1920
    mocked_geometry.height.return_value = 1080
    mocked_screen_list.return_value.__len__.return_value = 2
    mocked_screen = mocked_screen_list.return_value.current
    mocked_screen.custom_geometry = None
    mocked_screen.display_geometry = mocked_geometry

    # WHEN: Calling start_presentation
    with patch.object(doc, 'modify_powerpoint_display_monitor') as mocked_modify_powerpoint_display_monitor:
        doc.start_presentation()

    # THEN: The slideshow should start, and COM and Setting modifications should be handled correctly
    assert mocked_presentation.SlideShowSettings.ShowType == 1, 'ShowType should be 1'
    assert mocked_presentation.SlideShowSettings.ShowPresenterView == 0, 'ShowPresenterView should be 0'
    mocked_presentation.SlideShowSettings.Run.assert_called_once()
    assert mocked_modify_powerpoint_display_monitor.call_count == 2, \
           'mocked_modify_powerpoint_display_monitor should be called twice'
    mocked_main_window.activateWindow.assert_called_once(), 'activateWindow should be called once'
    mocked_win32gui.EnumWindows.assert_called_once()
    mocked_win32gui.BringWindowToTop.assert_called()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32gui')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.Registry')
def test_start_presentation_failure(mocked_registry, mocked_screen_list,
                                    mocked_win32gui, presentation_setup):
    """
    Test that start_presentation handles exceptions correctly when an AttributeError or pywintypes.com_error occurs.
    """
    # GIVEN: A PowerPointDocument instance with failing SlideShowSettings.Run()
    doc = PowerpointDocument(MagicMock(), MagicMock())
    mocked_slide_show_settings = MagicMock()
    mocked_slide_show_settings.Run.side_effect = AttributeError('Mocked failure')
    mocked_presentation = MagicMock()
    mocked_presentation.SlideShowSettings = mocked_slide_show_settings
    doc.presentation = mocked_presentation
    mocked_registry_instance = MagicMock()
    mocked_registry.return_value = mocked_registry_instance
    mocked_main_window = MagicMock()
    mocked_settings = MagicMock()
    mocked_registry_instance.get.side_effect = (
        lambda key: mocked_main_window if key == 'main_window' else mocked_settings
    )
    mocked_main_window.activateWindow = MagicMock()
    mocked_settings.value.return_value = QtCore.Qt.CheckState.Unchecked

    # WHEN: Calling start_presentation, expecting an exception to be handled
    with patch.object(doc, 'modify_powerpoint_display_monitor') as mocked_modify_registry, \
            patch('openlp.plugins.presentations.lib.powerpointcontroller.log') as mocked_log, \
            patch.object(doc, 'show_error_msg') as mocked_show_error_msg, \
            patch('openlp.plugins.presentations.lib.powerpointcontroller.trace_error_handler') \
            as mocked_trace_error_handler:
        doc.start_presentation()

    # THEN: The exception should be logged and error handling functions should be called
    mocked_log.exception.assert_called_once_with('Caught exception while in start_presentation')
    mocked_trace_error_handler.assert_called_once_with(mocked_log)
    mocked_show_error_msg.assert_called_once()
    mocked_modify_registry.assert_not_called()
    mocked_win32gui.EnumWindows.assert_not_called()
    mocked_win32gui.BringWindowToTop.assert_not_called()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32gui')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.Registry')
def test_start_presentation_non_fullscreen(mocked_registry, mocked_screen_list,
                                           mocked_win32gui, presentation_setup):
    """
    Test that start_presentation handles non-fullscreen mode correctly.
    """
    # GIVEN: A PowerPointDocument instance in non-fullscreen mode
    doc = PowerpointDocument(MagicMock(), MagicMock())
    ppt_window_mock = MagicMock()
    mocked_slide_show_settings = MagicMock()
    mocked_slide_show_settings.Run.return_value = ppt_window_mock
    mocked_presentation = MagicMock()
    mocked_presentation.SlideShowSettings = mocked_slide_show_settings
    doc.presentation = mocked_presentation
    mocked_registry_instance = MagicMock()
    mocked_registry.return_value = mocked_registry_instance
    mocked_main_window = MagicMock()
    mocked_settings = MagicMock()
    mocked_registry_instance.get.side_effect = (
        lambda key: mocked_main_window if key == 'main_window'
        else mocked_settings)
    mocked_main_window.activateWindow = MagicMock()
    mocked_settings.value.return_value = QtCore.Qt.CheckState.Unchecked
    mocked_geometry = MagicMock()
    mocked_screen_list.return_value.__len__.return_value = 2
    mocked_screen = mocked_screen_list.return_value.current
    mocked_screen.custom_geometry = object()
    mocked_screen.display_geometry = mocked_geometry

    # WHEN: Calling start_presentation
    with patch.object(doc, 'modify_powerpoint_display_monitor') as mocked_modify, \
            patch.object(doc, 'adjust_powerpoint_window_position') as mocked_adjust_position:
        doc.start_presentation()

    # THEN: Presentation should be configured for non-fullscreen
    assert mocked_presentation.SlideShowSettings.ShowType == 2
    mocked_presentation.SlideShowSettings.ShowScrollbar = 0
    assert mocked_adjust_position.call_count == 2, 'mocked_adjust_position should be called twice'
    mocked_modify.assert_not_called()
    mocked_main_window.activateWindow.assert_called_once()
    mocked_win32gui.EnumWindows.assert_called_once()
    mocked_win32gui.BringWindowToTop.assert_called()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32gui')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.Registry')
def test_start_presentation_no_ppt_window(mocked_registry, mocked_screen_list,
                                          mocked_win32gui, presentation_setup):
    """
    Test that start_presentation skips window positioning logic if ppt_window is None.
    """
    # GIVEN: A PowerPointDocument instance returning None for ppt_window
    doc = PowerpointDocument(MagicMock(), MagicMock())
    mocked_slide_show_settings = MagicMock()
    mocked_slide_show_settings.Run.return_value = None
    mocked_presentation = MagicMock()
    mocked_presentation.SlideShowSettings = mocked_slide_show_settings
    doc.presentation = mocked_presentation
    mocked_registry_instance = MagicMock()
    mocked_registry.return_value = mocked_registry_instance
    mocked_main_window = MagicMock()
    mocked_settings = MagicMock()
    mocked_registry_instance.get.side_effect = (
        lambda key: mocked_main_window if key == 'main_window'
        else mocked_settings)
    mocked_main_window.activateWindow = MagicMock()
    mocked_settings.value.return_value = QtCore.Qt.CheckState.Unchecked
    mocked_geometry = MagicMock()
    mocked_screen_list.return_value.__len__.return_value = 2
    mocked_screen = mocked_screen_list.return_value.current
    mocked_screen.custom_geometry = None
    mocked_screen.display_geometry = mocked_geometry

    # WHEN: Calling start_presentation
    with patch.object(doc, 'modify_powerpoint_display_monitor') as mocked_modify, \
            patch.object(doc, 'adjust_powerpoint_window_position') as mocked_adjust_position:
        doc.start_presentation()

    # THEN: No window handling should occur
    mocked_win32gui.EnumWindows.assert_not_called()
    mocked_adjust_position.assert_not_called()
    mocked_modify.call_count == 2, 'mocked_modify should be called twice'
    mocked_win32gui.BringWindowToTop.assert_not_called()
    mocked_main_window.activateWindow.assert_called_once()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32gui')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.Registry')
def test_start_presentation_bring_to_top_fails(mocked_registry, mocked_screen_list,
                                               mocked_win32gui, presentation_setup):
    """
    Test that exceptions during BringWindowToTop are logged.
    """
    # GIVEN: A PowerPointDocument instance where BringWindowToTop will raise
    doc = PowerpointDocument(MagicMock(), MagicMock())
    ppt_window_mock = MagicMock()
    mocked_slide_show_settings = MagicMock()
    mocked_slide_show_settings.Run.return_value = ppt_window_mock
    mocked_presentation = MagicMock()
    mocked_presentation.SlideShowSettings = mocked_slide_show_settings
    doc.presentation = mocked_presentation
    mocked_registry_instance = MagicMock()
    mocked_registry.return_value = mocked_registry_instance
    mocked_main_window = MagicMock()
    mocked_settings = MagicMock()
    mocked_registry_instance.get.side_effect = (
        lambda key: mocked_main_window if key == 'main_window'
        else mocked_settings)
    mocked_main_window.activateWindow = MagicMock()
    mocked_settings.value.return_value = QtCore.Qt.CheckState.Unchecked
    mocked_geometry = MagicMock()
    mocked_geometry.x.return_value = 0
    mocked_geometry.y.return_value = 0
    mocked_geometry.width.return_value = 1920
    mocked_geometry.height.return_value = 1080
    mocked_screen_list.return_value.__len__.return_value = 2
    mocked_screen = mocked_screen_list.return_value.current
    mocked_screen.custom_geometry = None
    mocked_screen.display_geometry = mocked_geometry
    mocked_win32gui.BringWindowToTop.side_effect = Exception('win32gui exception')

    # WHEN: Calling start_presentation with BringWindowToTop failure
    with patch.object(doc, 'modify_powerpoint_display_monitor') as mocked_modify, \
            patch('openlp.plugins.presentations.lib.powerpointcontroller.log') as mocked_log:
        doc.start_presentation()

    # THEN: BringWindowToTop error is caught and logged
    mocked_win32gui.EnumWindows.assert_called()
    mocked_log.exception.assert_called()
    mocked_modify.call_count == 2, 'mocked_modify should be called twice'
    mocked_main_window.activateWindow.assert_called_once()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.Registry')
def test_start_presentation_single_screen(mocked_registry, mocked_screen_list,
                                          presentation_setup):
    """
    Test that start_presentation does not activate window on a single screen setup.
    """
    # GIVEN: A single screen setup
    doc = PowerpointDocument(MagicMock(), MagicMock())
    ppt_window_mock = MagicMock()
    mocked_slide_show_settings = MagicMock()
    mocked_slide_show_settings.Run.return_value = ppt_window_mock
    mocked_presentation = MagicMock()
    mocked_presentation.SlideShowSettings = mocked_slide_show_settings
    doc.presentation = mocked_presentation
    mocked_registry_instance = MagicMock()
    mocked_registry.return_value = mocked_registry_instance
    mocked_main_window = MagicMock()
    mocked_settings = MagicMock()
    mocked_registry_instance.get.side_effect = (
        lambda key: mocked_main_window if key == 'main_window'
        else mocked_settings)
    mocked_main_window.activateWindow = MagicMock()
    mocked_settings.value.return_value = QtCore.Qt.CheckState.Unchecked
    mocked_geometry = MagicMock()
    mocked_screen_list.return_value.__len__.return_value = 1
    mocked_screen = mocked_screen_list.return_value.current
    mocked_screen.custom_geometry = None
    mocked_screen.display_geometry = mocked_geometry

    # WHEN: Calling start_presentation
    with patch.object(doc, 'modify_powerpoint_display_monitor'), \
            patch.object(doc, 'adjust_powerpoint_window_position'), \
            patch('openlp.plugins.presentations.lib.powerpointcontroller.log'):
        doc.start_presentation()

    # THEN: activateWindow should not be called on single screen
    mocked_screen_list.return_value.__len__.assert_called_once()
    mocked_main_window.activateWindow.assert_not_called()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32gui')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ctypes')
def test_close_powerpoint_ghost_window_success(mocked_ctypes, mocked_win32gui,
                                               presentation_setup):
    """
    Test that close_powerpoint_ghost_window correctly closes a window identified by it's hwnd.
    """
    # GIVEN: A presentation_hwnd is set during window enumeration
    doc = PowerpointDocument(MagicMock(), MagicMock())
    hwnd = 12345
    size = MagicMock()
    doc.presentation_hwnd = None
    doc._window_enum_callback = MagicMock(side_effect=lambda hwnd, size, search_presentation_window: True)
    mocked_win32gui.EnumWindows.side_effect = lambda callback, _: setattr(doc, 'presentation_hwnd', hwnd)

    # WHEN: close_powerpoint_ghost_window is called
    result = doc.close_powerpoint_ghost_window(size)

    # THEN: The ghost window is closed using PostMessageW and True is returned
    mocked_ctypes.windll.user32.PostMessageW.assert_called_once_with(hwnd, 0x0010, 0, 0)
    assert result is True
    assert doc.presentation_hwnd is None


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32gui')
def test_close_powerpoint_ghost_window_no_ghost_window(mocked_win32gui, presentation_setup):
    """
    Test that close_powerpoint_ghost_window does nothing if no ghost PowerPoint window is found.
    """
    # GIVEN: presentation_hwnd remains None after window enumeration
    doc = PowerpointDocument(MagicMock(), MagicMock())
    size = MagicMock()
    doc.presentation_hwnd = None
    doc._window_enum_callback = MagicMock()

    # WHEN: Calling close_powerpoint_ghost_window
    result = doc.close_powerpoint_ghost_window(size)

    # THEN: The function should return None, and no PostMessageW should be attempted
    assert result is None
    mocked_win32gui.EnumWindows.assert_called_once()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ctypes')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32gui')
def test_close_powerpoint_ghost_window_postmessage_failure(mocked_win32gui, mocked_ctypes,
                                                           presentation_setup):
    """
    Test that close_powerpoint_ghost_window a warning is logged
    if closing ghost PowerPoint window raises an exception.
    """
    # GIVEN: presentation_hwnd is set and PostMessageW raises an exception
    doc = PowerpointDocument(MagicMock(), MagicMock())
    size = MagicMock()
    hwnd = 67890
    doc.presentation_hwnd = hwnd
    doc._window_enum_callback = MagicMock()
    mocked_win32gui.EnumWindows.side_effect = lambda callback, _: setattr(doc, 'presentation_hwnd', hwnd)
    mocked_ctypes.windll.user32.PostMessageW.side_effect = Exception('Simulated error')

    # WHEN: Calling close_powerpoint_ghost_window
    with patch('openlp.plugins.presentations.lib.powerpointcontroller.log') as mocked_log, \
            patch('openlp.plugins.presentations.lib.powerpointcontroller.trace_error_handler') \
            as mocked_trace_error_handler:
        result = doc.close_powerpoint_ghost_window(size)

    # THEN: The exception should be caught, logged, and presentation_hwnd should be reset
    mocked_log.warning.assert_called_once_with(
        'Caught exception while trying to close possible PowerPoint ghost window')
    mocked_trace_error_handler.assert_called_once_with(mocked_log)
    assert doc.presentation_hwnd is None
    assert result is None


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32api')
def test_get_win_display_name_by_geometry_match(mocked_win32api, presentation_setup):
    """
    Test that get_win_display_name_by_geometry returns the correct device name when monitor geometry matches.
    """
    # GIVEN: A PowerPointDocument instance and mocked monitor with matching geometry
    doc = PowerpointDocument(MagicMock(), MagicMock())
    mocked_geometry = MagicMock()
    mocked_geometry.x.return_value = 0
    mocked_geometry.y.return_value = 0
    mocked_geometry.width.return_value = 1920
    mocked_geometry.height.return_value = 1080
    qt_tuple = (0, 0, 1920, 1080)
    hMonitor = MagicMock()
    mocked_win32api.EnumDisplayMonitors.return_value = [(hMonitor, None, qt_tuple)]
    mocked_win32api.GetMonitorInfo.return_value = {'Device': r'\\.\DISPLAY2'}

    # WHEN: Calling get_win_display_name_by_geometry
    device_name = doc.get_win_display_name_by_geometry(mocked_geometry)

    # THEN: The correct device name should be returned
    assert device_name == r'\\.\DISPLAY2'
    mocked_win32api.GetMonitorInfo.assert_called_once_with(hMonitor)


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32api')
def test_get_win_display_name_by_geometry_no_match(mocked_win32api, presentation_setup):
    """
    Test that get_win_display_name_by_geometry returns None when there is no geometry match.
    """
    # GIVEN: A PowerPointDocument instance with mocked monitor that does not match geometry
    doc = PowerpointDocument(MagicMock(), MagicMock())
    mocked_geometry = MagicMock()
    mocked_geometry.x.return_value = 0
    mocked_geometry.y.return_value = 0
    mocked_geometry.width.return_value = 1920
    mocked_geometry.height.return_value = 1080
    non_matching_tuple = (100, 100, 1020, 1080)

    mocked_win32api.EnumDisplayMonitors.return_value = [(MagicMock(), None, non_matching_tuple)]

    # WHEN: Calling get_win_display_name_by_geometry
    device_name = doc.get_win_display_name_by_geometry(mocked_geometry)

    # THEN: None should be returned since no geometry matches
    assert device_name is None
    mocked_win32api.GetMonitorInfo.assert_not_called()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32api')
def test_get_win_display_name_by_geometry_exception(mocked_win32api, presentation_setup):
    """
    Test that get_win_display_name_by_geometry handles exceptions and logs a warning.
    """
    # GIVEN: A PowerPointDocument instance and mocked EnumDisplayMonitors that raises exception
    doc = PowerpointDocument(MagicMock(), MagicMock())
    mocked_geometry = MagicMock()
    mocked_win32api.EnumDisplayMonitors.side_effect = RuntimeError('Mocked error')

    # WHEN: Calling get_win_display_name_by_geometry
    with patch('openlp.plugins.presentations.lib.powerpointcontroller.log') as mocked_log, \
            patch('openlp.plugins.presentations.lib.powerpointcontroller.trace_error_handler') as mocked_trace:
        device_name = doc.get_win_display_name_by_geometry(mocked_geometry)

    # THEN: Should return None, log a warning, and call trace handler
    assert device_name is None
    mocked_log.warning.assert_called_once_with('Caught exception while in get_win_display_name_by_geometry')
    mocked_trace.assert_called_once_with(mocked_log)


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.winreg')
def test_modify_powerpoint_display_monitor_success(mocked_winreg, presentation_setup):
    """
    Test that modify_powerpoint_display_monitor correctly updates the registry key and returns the original value.
    """
    # GIVEN: A PowerPointDocument instance and mocked registry interactions
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.presentation = MagicMock()
    doc.presentation.Parent.Application.Version = '16.0'
    mocked_reg_key = MagicMock()
    mocked_winreg.OpenKey.return_value = mocked_reg_key
    mocked_winreg.QueryValueEx.return_value = ('original_value',)

    # WHEN: Calling modify_powerpoint_display_monitor with a new value different from the original
    original_value = doc.modify_powerpoint_display_monitor('new_value')

    # THEN: The registry key should be updated, and the original value should be returned
    mocked_winreg.SetValueEx.assert_called_once_with(mocked_reg_key, 'DisplayMonitor', 0,
                                                     mocked_winreg.REG_SZ, 'new_value')
    mocked_winreg.CloseKey.assert_called_once_with(mocked_reg_key)
    assert original_value == 'original_value'


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.winreg')
def test_modify_powerpoint_display_monitor_failure(mocked_winreg, presentation_setup):
    """
    Test that modify_powerpoint_display_monitor handles OSError gracefully and logs a warning.
    """
    # GIVEN: A PowerPointDocument instance and a registry access failure
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.presentation = MagicMock()
    doc.presentation.Parent.Application.Version = '16.0'
    mocked_winreg.OpenKey.side_effect = OSError

    # WHEN: Calling modify_powerpoint_display_monitor
    with patch('openlp.plugins.presentations.lib.powerpointcontroller.log') as mocked_log:
        original_value = doc.modify_powerpoint_display_monitor('new_value')

    # THEN: A warning should be logged, and no value should be returned
    mocked_log.warning.assert_called_once()
    assert original_value is None


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
def test_modify_powerpoint_display_monitor_none_value(presentation_setup):
    """
    Test that modify_powerpoint_display_monitor logs a warning
    and returns None when called with None as the new_value.
    """
    # GIVEN: A PowerPointDocument instance
    doc = PowerpointDocument(MagicMock(), MagicMock())

    # WHEN: Calling modify_powerpoint_display_monitor with None
    with patch('openlp.plugins.presentations.lib.powerpointcontroller.log.warning') as mocked_log:
        result = doc.modify_powerpoint_display_monitor(None)

    # THEN: A warning should be logged, and the function should return None
    mocked_log.assert_called_once_with(
        'modify_powerpoint_display_monitor called with a new value that is not a string.')
    assert result is None


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.winreg')
def test_modify_powerpoint_display_monitor_missing_registry_key(mocked_winreg, presentation_setup):
    """
    Test that modify_powerpoint_display_monitor handles the case where the 'DisplayMonitor' registry key is missing.
    """
    # GIVEN: A PowerPointDocument instance with missing 'DisplayMonitor' registry key
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.presentation = MagicMock()
    doc.presentation.Parent.Application.Version = '16.0'
    mocked_reg_key = MagicMock()
    mocked_winreg.OpenKey.return_value = mocked_reg_key
    mocked_winreg.QueryValueEx.side_effect = FileNotFoundError

    # WHEN: Calling modify_powerpoint_display_monitor
    original_value = doc.modify_powerpoint_display_monitor('new_value')

    # THEN: The function should return None since the registry key is missing
    mocked_winreg.SetValueEx.assert_called_once_with(mocked_reg_key, 'DisplayMonitor', 0,
                                                     mocked_winreg.REG_SZ, 'new_value')
    mocked_winreg.CloseKey.assert_called_once_with(mocked_reg_key)
    assert original_value is None


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.winreg')
def test_modify_powerpoint_display_monitor_no_change(mocked_winreg, presentation_setup):
    """
    Test that modify_powerpoint_display_monitor does not modify the registry
    if the new value is the same as the original.
    """
    # GIVEN: A PowerPointDocument instance and mocked registry interactions
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.presentation = MagicMock()
    doc.presentation.Parent.Application.Version = '16.0'
    mocked_reg_key = MagicMock()
    mocked_winreg.OpenKey.return_value = mocked_reg_key
    mocked_winreg.QueryValueEx.return_value = ['current_value',]

    # WHEN: Calling modify_powerpoint_display_monitor with the same value as the original
    original_value = doc.modify_powerpoint_display_monitor('current_value')

    # THEN: The registry key should not be updated, and the original value should be returned
    mocked_winreg.SetValueEx.assert_not_called()
    mocked_winreg.CloseKey.assert_called_once_with(mocked_reg_key)
    assert original_value == 'current_value'


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ctypes')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
def test_adjust_position_success_with_hwnd(mocked_screen_list, mocked_ctypes,
                                           presentation_setup):
    """
    Test that adjust_powerpoint_window_position sets ppt_window size and position
    correctly when hwnd_to_scale is provided and border calculation succeeds.
    """
    # GIVEN: A PowerPointDocument and a ppt_window with a hwnd to calculate borders
    doc = PowerpointDocument(MagicMock(), MagicMock())
    ppt_window = MagicMock()
    hwnd = 1234
    doc.presentation_hwnd = hwnd
    mocked_geometry = MagicMock()
    mocked_geometry.x.return_value = 100
    mocked_geometry.y.return_value = 50
    mocked_geometry.width.return_value = 1280
    mocked_geometry.height.return_value = 720
    mocked_screen = mocked_screen_list.return_value.current
    mocked_screen.display_geometry = mocked_geometry
    mocked_screen.raw_screen.logicalDotsPerInch.return_value = 96
    mocked_ctypes.windll.user32.GetWindowRect.side_effect = lambda hwnd, rect: \
        setattr(rect, 'right', 1040) or \
        setattr(rect, 'bottom', 800) or \
        setattr(rect, 'left', 0) or \
        setattr(rect, 'top', 0)
    mocked_ctypes.windll.user32.GetClientRect.side_effect = lambda hwnd, rect: \
        setattr(rect, 'right', 1000) or \
        setattr(rect, 'bottom', 760) or \
        setattr(rect, 'left', 0) or \
        setattr(rect, 'top', 0)
    mocked_ctypes.byref.side_effect = lambda x: x

    # WHEN: Calling adjust_powerpoint_window_position
    with patch('openlp.plugins.presentations.lib.powerpointcontroller.log') as mocked_log:
        doc.adjust_powerpoint_window_position(ppt_window, hwnd_to_scale=hwnd)

    # THEN: Window should be positioned and scaled correctly
    assert ppt_window.Top is not None
    assert ppt_window.Left is not None
    assert ppt_window.Width is not None
    assert ppt_window.Height is not None
    mocked_log.exception.assert_not_called()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ctypes')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
def test_adjust_position_border_calc_fails(mocked_screen_list, mocked_ctypes,
                                           presentation_setup):
    """
    Test that adjust_powerpoint_window_position handles failure to calculate border/caption size gracefully.
    """
    # GIVEN: A PowerPointDocument and a ppt_window; ctypes throws exception
    doc = PowerpointDocument(MagicMock(), MagicMock())
    ppt_window = MagicMock()
    doc.presentation_hwnd = 1234
    mocked_ctypes.windll.user32.GetWindowRect.side_effect = Exception('fail')
    mocked_ctypes.windll.user32.GetClientRect.side_effect = Exception('fail')
    mocked_ctypes.byref.side_effect = lambda x: x
    mocked_geometry = MagicMock()
    mocked_geometry.x.return_value = 0
    mocked_geometry.y.return_value = 0
    mocked_geometry.width.return_value = 800
    mocked_geometry.height.return_value = 600
    mocked_screen = mocked_screen_list.return_value.current
    mocked_screen.display_geometry = mocked_geometry
    mocked_screen.raw_screen.logicalDotsPerInch.return_value = 96

    # WHEN: Calling adjust_powerpoint_window_position and ctypes fails
    with patch('openlp.plugins.presentations.lib.powerpointcontroller.log') as mocked_log:
        doc.adjust_powerpoint_window_position(ppt_window, hwnd_to_scale=1234)

    # THEN: Error is logged, but window still positioned with default values
    mocked_log.exception.assert_any_call('Unable to calculate border and titlebar size.')
    assert ppt_window.Top is not None


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
def test_adjust_position_no_hwnd(mocked_screen_list, presentation_setup):
    """
    Test that adjust_powerpoint_window_position works when hwnd_to_scale is None (no border/caption calculation).
    """
    # GIVEN: A PowerPointDocument and a ppt_window; hwnd_to_scale is not set
    doc = PowerpointDocument(MagicMock(), MagicMock())
    ppt_window = MagicMock()
    mocked_geometry = MagicMock()
    mocked_geometry.x.return_value = 0
    mocked_geometry.y.return_value = 0
    mocked_geometry.width.return_value = 1920
    mocked_geometry.height.return_value = 1080
    mocked_screen = mocked_screen_list.return_value.current
    mocked_screen.display_geometry = mocked_geometry
    mocked_screen.raw_screen.logicalDotsPerInch.return_value = 96

    # WHEN: Calling adjust_powerpoint_window_position without hwnd_to_scale
    with patch('openlp.plugins.presentations.lib.powerpointcontroller.log') as mocked_log:
        doc.adjust_powerpoint_window_position(ppt_window)

    # THEN: Window is adjusted with no caption/border
    assert ppt_window.Top == 0
    assert ppt_window.Left == 0
    assert ppt_window.Width == (1920 * 72) / 96
    assert ppt_window.Height == (1080 * 72) / 96
    mocked_log.exception.assert_not_called()


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.ScreenList')
def test_adjust_position_attribute_error(mocked_screen_list, presentation_setup):
    """
    Test that adjust_powerpoint_window_position handles AttributeError gracefully (e.g. ScreenList fails).
    """
    # GIVEN: A PowerPointDocument and a ppt_window; ScreenList raises AttributeError
    doc = PowerpointDocument(MagicMock(), MagicMock())
    ppt_window = MagicMock()
    mocked_screen_list.side_effect = AttributeError('fail')
    # WHEN: Calling adjust_powerpoint_window_position and ScreenList fails
    with patch('openlp.plugins.presentations.lib.powerpointcontroller.log') as mocked_log:
        doc.adjust_powerpoint_window_position(ppt_window)

    # THEN: The error is caught and logged
    mocked_log.exception.assert_called_once_with('AttributeError while in adjust_powerpoint_window_position')


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32gui')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32con')
def test_window_enum_callback_finds_presentation_window(mocked_win32con, mocked_win32gui,
                                                        presentation_setup):
    """
    Test that _window_enum_callback correctly identifies and saves the presentation window handle
    when all window conditions and title match.
    """
    # GIVEN: A mock document with expected size and matching window title
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.file_path = MagicMock()
    doc.file_path.stem = 'Presentation'
    hwnd = 12345
    size = MagicMock()
    size.y.return_value = 100
    size.height.return_value = 800
    size.x.return_value = 200
    size.width.return_value = 1280
    mocked_win32gui.GetWindowRect.return_value = (200, 100, 1480, 900)
    mocked_win32gui.GetWindowText.return_value = 'PowerPoint - Presentation'

    # WHEN: _window_enum_callback is called with matching window and title
    result = doc._window_enum_callback(hwnd, size)

    # THEN: The window handle should be saved and FlashWindowEx should be called to stop flashing
    assert doc.presentation_hwnd == hwnd
    mocked_win32gui.FlashWindowEx.assert_called_once_with(hwnd, mocked_win32con.FLASHW_STOP, 0, 0)
    assert result is False


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32gui')
def test_window_enum_callback_ignores_non_matching_title(mocked_win32gui, presentation_setup):
    """
    Test that _window_enum_callback does not save the handle
    when the window title does not match the presentation file.
    """
    # GIVEN: A PowerPointDocument with a file name not present in the window title
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.file_path = MagicMock()
    doc.file_path.stem = 'MySlides'
    hwnd = 22222
    size = MagicMock()
    size.y.return_value = 100
    size.height.return_value = 800
    size.x.return_value = 200
    size.width.return_value = 1280
    mocked_win32gui.GetWindowRect.return_value = (200, 100, 1480, 900)
    mocked_win32gui.GetWindowText.return_value = 'Marketing Deck - PowerPoint'

    # WHEN: The title doesn't contain the file name
    result = doc._window_enum_callback(hwnd, size)

    # THEN: No handle should be saved and enumeration should continue
    assert doc.presentation_hwnd is None
    assert result is True


@pytest.mark.skipif(not is_win(), reason='This test only works on Windows')
@patch('openlp.plugins.presentations.lib.powerpointcontroller.win32gui')
def test_window_enum_callback_without_filename_check(mocked_win32gui, presentation_setup):
    """
    Test that _window_enum_callback finds a window even if the title doesn't contain the file name
    when search_presentation_window is False.
    """
    # GIVEN: Window matches size/position/title starts with 'PowerPoint' but not the file name
    doc = PowerpointDocument(MagicMock(), MagicMock())
    doc.file_path = MagicMock()
    doc.file_path.stem = 'OtherPresentation'
    hwnd = 67890
    size = MagicMock()
    size.y.return_value = 100
    size.height.return_value = 800
    size.x.return_value = 200
    size.width.return_value = 1280
    mocked_win32gui.GetWindowRect.return_value = (200, 100, 1480, 900)
    mocked_win32gui.GetWindowText.return_value = 'PowerPoint Fullscreen'

    # WHEN: search_presentation_window is False, so filename match isn't required
    result = doc._window_enum_callback(hwnd, size, search_presentation_window=False)

    # THEN: Handle should be saved and FlashWindowEx should NOT be called
    assert doc.presentation_hwnd == hwnd
    mocked_win32gui.FlashWindowEx.assert_not_called()
    assert result is False
