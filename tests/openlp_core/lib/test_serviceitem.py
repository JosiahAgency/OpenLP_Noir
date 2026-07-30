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
Package to test the openlp.core.lib package.
"""
import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from openlp.core.common import ThemeLevel
from openlp.core.common.enum import ServiceItemType
from openlp.core.common.json import OpenLPJSONEncoder
from openlp.core.common.platform import is_win
from openlp.core.common.registry import Registry
from openlp.core.lib.formattingtags import FormattingTags
from openlp.core.lib.serviceitem import ItemCapabilities, ServiceItem
from openlp.core.lib.theme import TransitionSpeed
from openlp.core.state import State
from openlp.core.ui.icons import UiIcons
from tests.utils import convert_file_service_item
from tests.utils.constants import RESOURCE_PATH


VERSE = 'The Lord said to {r}Noah{/r}: \n'\
        'There\'s gonna be a {su}floody{/su}, {sb}floody{/sb}\n'\
        'The Lord said to {g}Noah{/g}:\n'\
        'There\'s gonna be a {st}floody{/st}, {it}floody{/it}\n'\
        'Get those children out of the muddy, muddy \n'\
        '{r}C{/r}{b}h{/b}{bl}i{/bl}{y}l{/y}{g}d{/g}{pk}'\
        'r{/pk}{o}e{/o}{pp}n{/pp} of the Lord\n'
CLEANED_VERSE = 'Amazing Grace! how sweet the sound\n'\
                'That saved a wretch like me;\n'\
                'I once was lost, but now am found,\n'\
                'Was blind, but now I see.\n'
RENDERED_VERSE = 'The Lord said to <span style="-webkit-text-fill-color:red">Noah</span>: \n'\
                 'There&#x27;s gonna be a <sup>floody</sup>, <sub>floody</sub>\n'\
                 'The Lord said to <span style="-webkit-text-fill-color:green">Noah</span>:\n'\
                 'There&#x27;s gonna be a <strong>floody</strong>, <em>floody</em>\n'\
                 'Get those children out of the muddy, muddy \n'\
                 '<span style="-webkit-text-fill-color:red">C</span><span style="-webkit-text-fill-color:black">h' \
                 '</span><span style="-webkit-text-fill-color:blue">i</span>'\
                 '<span style="-webkit-text-fill-color:yellow">l</span><span style="-webkit-text-fill-color:green">d'\
                 '</span><span style="-webkit-text-fill-color:#FFC0CB">r</span>'\
                 '<span style="-webkit-text-fill-color:#FFA500">e</span><span style="-webkit-text-fill-color:#800080">'\
                 'n</span> of the Lord\n'
FOOTER = ['Arky Arky (Unknown)', 'Public Domain', 'CCLI 123456']
TEST_PATH = RESOURCE_PATH / 'service'


@pytest.fixture()
def service_item_env(state):
    # Mock the renderer and its format_slide method
    mocked_renderer = MagicMock()

    def side_effect_return_arg(arg1, arg2):
        return [arg1]

    mocked_slide_formater = MagicMock(side_effect=side_effect_return_arg)
    mocked_renderer.format_slide = mocked_slide_formater
    Registry().register('renderer', mocked_renderer)


def test_service_item_basic(settings):
    """
    Test creating a new Service Item without a plugin
    """
    # GIVEN: A new service item
    # WHEN: A service item is created (without a plugin)
    service_item = ServiceItem(None)

    # THEN: We should get back a valid service item
    assert service_item.is_valid is True, 'The new service item should be valid'
    assert service_item.missing_frames() is True, 'There should not be any frames in the service item'


def test_service_item_with_plugin(settings):
    """
    Test creating a new Service Item with a plugin
    """
    # GIVEN: A new service item
    mocked_plugin = MagicMock()
    mocked_plugin.name = 'songs'
    # WHEN: A service item is created (with a plugin)
    service_item = ServiceItem(mocked_plugin)

    # THEN: We should get back a valid service item
    assert service_item.name == 'songs', 'The service item name should be the same as the plugin name'
    assert service_item.is_valid is True, 'The new service item should be valid'
    assert service_item.missing_frames() is True, 'There should not be any frames in the service item'


def test_service_item_load_custom_from_service(state_media, settings, service_item_env):
    """
    Test the Service Item - adding a custom slide from a saved service
    """
    # GIVEN: A new service item and a mocked add icon function
    service_item = ServiceItem(None)
    service_item.add_icon = MagicMock()
    FormattingTags.load_tags()

    # WHEN: We add a custom from a saved serviceand set the media state
    line = convert_file_service_item(TEST_PATH, 'serviceitem_custom_1.osj')
    service_item.set_from_service(line)

    # THEN: We should get back a valid service item
    assert service_item.is_valid is True, 'The new service item should be valid'
    assert len(service_item.get_frames()) == 2, 'The service item should have 2 display frames'
    assert len(service_item.capabilities) == 5, 'There should be 5 default custom item capabilities'

    # THEN: The frames should also be valid
    assert 'Test Custom' == service_item.get_display_title(), 'The title should be "Test Custom"'
    assert 'Slide 1' == service_item.get_frames()[0]['text']
    assert 'Slide 2' == service_item.get_rendered_frame(1)
    assert 'Slide 1' == service_item.get_frame_title(0), '"Slide 1" has been returned as the title'
    assert 'Slide 2' == service_item.get_frame_title(1), '"Slide 2" has been returned as the title'
    assert '' == service_item.get_frame_title(2), 'Blank has been returned as the title of slide 3'


def test_service_item_load_image_from_service(state_media, settings):
    """
    Test the Service Item - adding an image from a saved service
    tests a version 3 service file serviceitem (openlp-servicefile-version == 3)
    """
    # GIVEN: A new service item (pre encoded from the json format) and a mocked add icon function
    image_name1 = 'BrightDots.png'
    fake_hash1 = 'abcd'
    image_name2 = 'DullDots.png'
    fake_hash2 = 'asdf'
    extracted_file = Path(TEST_PATH) / '{base}{ext}'.format(base=fake_hash1, ext=os.path.splitext(image_name1)[1])
    frame_array = {'path': extracted_file, 'title': image_name1, 'file_hash': fake_hash1,
                   'thumbnail': Path("/path/images/thumbnails/abcd.png")}
    service_item = ServiceItem(None)
    service_item.add_icon = MagicMock()
    item = {'serviceitem': {'header': {'name': 'images', 'plugin': 'images', 'theme': -1, 'title': 'My Images',
                                       'footer': [], 'type': 2, 'audit': '', 'notes': '', 'from_plugin': False,
                                       'capabilities': [3, 1, 5, 6, 17, 21], 'search': '', 'data': '',
                                       'xml_version': None, 'auto_play_slides_once': False,
                                       'auto_play_slides_loop': False, 'timed_slide_interval': 0, 'start_time': 0,
                                       'end_time': 0, 'media_length': 0, 'background_audio': [],
                                       'theme_overwritten': False, 'will_auto_start': False, 'processor': None,
                                       'metadata': [], 'sha256_file_hash': None, 'stored_filename': None},
                            'data': [{'title': image_name1,
                                      'image': Path('images/thumbnails/{}.png'.format(fake_hash1)),
                                      'file_hash': fake_hash1},
                                     {'title': image_name2,
                                      'image': None,
                                      'file_hash': fake_hash2}]}}

    # WHEN: adding an image from a saved Service and mocked exists
    with patch('openlp.core.ui.servicemanager.os.path.exists') as mocked_exists, \
            patch('openlp.core.lib.serviceitem.AppLocation.get_section_data_path') as mocked_get_section_data_path, \
            patch('openlp.core.lib.serviceitem.AppLocation.get_data_path') as mocked_get_data_path, \
            patch('openlp.core.lib.serviceitem.sha256_file_hash') as mocked_sha256_file_hash, \
            patch('openlp.core.lib.serviceitem.copy'), \
            patch('openlp.core.lib.serviceitem.move'):
        mocked_sha256_file_hash.side_effect = [fake_hash1, fake_hash2]
        mocked_exists.return_value = True
        mocked_get_section_data_path.return_value = Path('/path/')
        mocked_get_data_path.return_value = Path('/path/')
        service_item.set_from_service(item, TEST_PATH, 3)

    # THEN: We should get back a valid service item,
    # and the second item with no preview image should not have crashed the program
    assert service_item.is_valid is True, 'The new service item should be valid'
    assert extracted_file == service_item.get_rendered_frame(0), 'The first frame should match the path to the image'
    assert frame_array == service_item.get_frames()[0], 'The return should match frame array1'
    assert extracted_file == service_item.get_frame_path(0), \
        'The frame path should match the full path to the image'
    assert image_name1 == service_item.get_frame_title(0), 'The frame title should match the image name'
    assert image_name2 == service_item.get_frame_title(1), 'The 2nd frame title should match the image name'
    assert 'My Images' == service_item.get_display_title(), 'The display title should match the provided title'
    assert service_item.is_image() is True, 'This service item should be of an "image" type'


def test_old_service_item_load_image_from_service(state_media, settings):
    """
    Test the Service Item - adding an image from a saved service
    tests a old service file serviceitem (openlp-servicefile-version < 3)
    """
    # GIVEN: A new service item and a mocked add icon function
    image_name = 'image_1.jpg'
    fake_hash = 'abcd'
    extracted_file = Path(TEST_PATH) / '{base}{ext}'.format(base=fake_hash, ext=os.path.splitext(image_name)[1])
    frame_array = {'path': extracted_file, 'title': image_name, 'file_hash': fake_hash}
    service_item = ServiceItem(None)
    service_item.add_icon = MagicMock()

    # WHEN: adding an image from a saved Service and mocked exists
    line = convert_file_service_item(TEST_PATH, 'serviceitem_image_1.osj')
    with patch('openlp.core.lib.serviceitem.os.path.exists') as mocked_exists, \
            patch('openlp.core.lib.serviceitem.AppLocation.get_section_data_path') as mocked_get_section_data_path, \
            patch('openlp.core.lib.serviceitem.sha256_file_hash') as mocked_sha256_file_hash, \
            patch('openlp.core.lib.serviceitem.move'):
        mocked_sha256_file_hash.return_value = fake_hash
        # The image itself "exists" so the item validates, but the thumbnail probe
        # must miss. The probe uses Path.exists(), which on Python 3.12+ delegates
        # to the (globally patched) os.path.exists, so a plain return_value=True
        # would wrongly give the loaded item a thumbnail.
        mocked_exists.side_effect = lambda file_path: 'thumbnails' not in str(file_path)
        mocked_get_section_data_path.return_value = Path('/path/')
        service_item.set_from_service(line, TEST_PATH)

    # THEN: We should get back a valid service item
    assert service_item.is_valid is True, 'The new service item should be valid'
    assert extracted_file == service_item.get_rendered_frame(0), 'The first frame should match the path to the image'
    assert frame_array == service_item.get_frames()[0], 'The return should match frame array1'
    assert extracted_file == service_item.get_frame_path(0), \
        'The frame path should match the full path to the image'
    assert image_name == service_item.get_frame_title(0), 'The frame title should match the image name'
    assert image_name == service_item.get_display_title(), 'The display title should match the first image name'
    assert service_item.is_image() is True, 'This service item should be of an "image" type'
    assert service_item.is_capable(ItemCapabilities.CanMaintain) is True, \
        'This service item should be able to be Maintained'
    assert service_item.is_capable(ItemCapabilities.CanPreview) is True, \
        'This service item should be able to be be Previewed'
    assert service_item.is_capable(ItemCapabilities.CanLoop) is True, \
        'This service item should be able to be run in a can be made to Loop'
    assert service_item.is_capable(ItemCapabilities.CanAppend) is True, \
        'This service item should be able to have new items added to it'


@patch('openlp.core.lib.serviceitem.os.path.exists')
@patch('openlp.core.lib.serviceitem.AppLocation.get_section_data_path')
def test_service_item_load_image_from_local_service(mocked_get_section_data_path, mocked_exists, settings, state_media):
    """
    Test the Service Item - adding an image from a saved local service
    """
    # GIVEN: A new service item and a mocked add icon function
    mocked_get_section_data_path.return_value = Path('/path')
    mocked_exists.return_value = True
    image_name1 = 'image_1.jpg'
    image_name2 = 'image_2.jpg'
    test_file1 = Path('/home/openlp') / image_name1
    test_file2 = Path('/home/openlp') / image_name2
    frame_array1 = {'path': test_file1, 'title': image_name1, 'file_hash': 'abcd'}
    frame_array2 = {'path': test_file2, 'title': image_name2, 'file_hash': 'abcd'}
    service_item = ServiceItem(None)
    service_item.add_icon = MagicMock()
    service_item2 = ServiceItem(None)
    service_item2.add_icon = MagicMock()

    # WHEN: adding an image from a saved Service and mocked exists
    line = convert_file_service_item(TEST_PATH, 'serviceitem_image_2.osj')
    line2 = convert_file_service_item(TEST_PATH, 'serviceitem_image_2.osj', 1)
    with patch('openlp.core.lib.serviceitem.sha256_file_hash') as mocked_sha256_file_hash:
        mocked_sha256_file_hash.return_value = 'abcd'
        service_item2.set_from_service(line2)
        service_item.set_from_service(line)

    # THEN: We should get back a valid service item
    assert service_item.is_valid is True, 'The first service item should be valid'
    assert service_item2.is_valid is True, 'The second service item should be valid'
    # These test will fail on windows due to the difference in folder seperators
    if os.name != 'nt':
        assert test_file1 == service_item.get_rendered_frame(0), \
            'The first frame should match the path to the image'
        assert test_file2 == service_item2.get_rendered_frame(0), \
            'The Second frame should match the path to the image'
        assert frame_array1 == service_item.get_frames()[0], 'The return should match the frame array1'
        assert frame_array2 == service_item2.get_frames()[0], 'The return should match the frame array2'
        assert test_file1 == service_item.get_frame_path(0), \
            'The frame path should match the full path to the image'
        assert test_file2 == service_item2.get_frame_path(0), \
            'The frame path should match the full path to the image'
    assert image_name1 == service_item.get_frame_title(0), 'The 1st frame title should match the image name'
    assert image_name2 == service_item2.get_frame_title(0), 'The 2nd frame title should match the image name'
    assert service_item.name == service_item.title.lower(), \
        'The plugin name should match the display title, as there are > 1 Images'
    assert service_item.is_image() is True, 'This service item should be of an "image" type'
    assert service_item.is_capable(ItemCapabilities.CanMaintain) is True, \
        'This service item should be able to be Maintained'
    assert service_item.is_capable(ItemCapabilities.CanPreview) is True, \
        'This service item should be able to be be Previewed'
    assert service_item.is_capable(ItemCapabilities.CanLoop) is True, \
        'This service item should be able to be run in a can be made to Loop'
    assert service_item.is_capable(ItemCapabilities.CanAppend) is True, \
        'This service item should be able to have new items added to it'


def test_add_from_text_no_verse_tag():
    """
    Test the Service Item - adding text slides with no verse tag
    """
    # GIVEN: A service item and two slides
    service_item = ServiceItem(None)
    slide1 = "This is the first slide"
    slide2 = "This is the second slide"

    # WHEN: adding text slides to service_item
    service_item.add_from_text(slide1)
    service_item.add_from_text(slide2)

    # THEN: Slides should be added with correctly numbered verse tags (Should start at 1)
    assert service_item.slides == [
        {'text': 'This is the first slide', 'title': 'This is the first slide', 'verse': '1'},
        {'text': 'This is the second slide', 'title': 'This is the second slide', 'verse': '2'}
    ]


def test_add_from_command_for_a_presentation():
    """
    Test the Service Item - adding a presentation
    """
    # GIVEN: A service item, a mocked icon and presentation data
    service_item = ServiceItem(None)
    service_item.name = 'presentations'
    presentation_name = 'test.pptx'
    image = Path('thumbnails/abcd/slide1.png')
    display_title = 'DisplayTitle'
    notes = 'Note1\nNote2\n'
    frame = {'title': presentation_name, 'image': image, 'path': TEST_PATH,
             'display_title': display_title, 'notes': notes, 'thumbnail': image}

    # WHEN: adding presentation to service_item
    with patch('openlp.core.lib.serviceitem.sha256_file_hash') as mocked_sha256_file_hash, \
            patch('openlp.core.lib.serviceitem.AppLocation.get_section_data_path') as mocked_get_section_data_path:
        mocked_sha256_file_hash.return_value = 'abcd'
        mocked_get_section_data_path.return_value = Path('.')
        service_item.add_from_command(TEST_PATH, presentation_name, image, display_title, notes)

    # THEN: verify that it is setup as a Command and that the frame data matches
    assert service_item.service_item_type == ServiceItemType.Command, 'It should be a Command'
    assert service_item.get_frames()[0] == frame, 'Frames should match'


def test_add_from_command_without_display_title_and_notes():
    """
    Test the Service Item - add from command, but not presentation
    """
    # GIVEN: A new service item, a mocked icon and image data
    service_item = ServiceItem(None)
    service_item.name = 'presentations'
    image_name = 'test.img'
    image = Path('thumbnails/abcd/slide1.png')
    frame = {'title': image_name, 'image': image, 'path': TEST_PATH,
             'display_title': None, 'notes': None, 'thumbnail': image}

    # WHEN: adding image to service_item
    with patch('openlp.core.lib.serviceitem.sha256_file_hash') as mocked_sha256_file_hash, \
            patch('openlp.core.lib.serviceitem.AppLocation.get_section_data_path') as mocked_get_section_data_path:
        mocked_sha256_file_hash.return_value = 'abcd'
        mocked_get_section_data_path.return_value = Path('.')
        service_item.add_from_command(TEST_PATH, image_name, image)

    # THEN: verify that it is setup as a Command and that the frame data matches
    assert service_item.service_item_type == ServiceItemType.Command, 'It should be a Command'
    assert service_item.get_frames()[0] == frame, 'Frames should match'


@patch('openlp.core.lib.serviceitem.AppLocation.get_section_data_path')
def test_add_from_command_for_a_presentation_thumb(mocked_get_section_data_path):
    """
    Test the Service Item - adding a presentation, updating the thumb path & adding the thumb
    """
    # GIVEN: A service item, a mocked AppLocation and presentation data
    mocked_get_section_data_path.return_value = Path('mocked') / 'section' / 'path'
    service_item = ServiceItem(None)
    service_item.add_capability(ItemCapabilities.HasThumbnails)
    service_item.has_original_files = False
    service_item.name = 'presentations'
    presentation_name = 'test.pptx'
    thumb = Path('tmp') / 'test' / 'thumb.png'
    display_title = 'DisplayTitle'
    notes = 'Note1\nNote2\n'
    expected_thumb_path = Path('mocked') / 'section' / 'path' / 'thumbnails' / 'abcd' / 'thumb.png'
    frame = {'title': presentation_name, 'image': expected_thumb_path, 'path': str(TEST_PATH),
             'display_title': display_title, 'notes': notes, 'thumbnail': expected_thumb_path}

    # WHEN: adding presentation to service_item
    with patch('openlp.core.lib.serviceitem.sha256_file_hash') as mocked_sha256_file_hash:
        mocked_sha256_file_hash.return_value = 'abcd'
        service_item.add_from_command(str(TEST_PATH), presentation_name, thumb, display_title, notes)

    # THEN: verify that it is setup as a Command and that the frame data matches
    assert service_item.service_item_type == ServiceItemType.Command, 'It should be a Command'
    assert service_item.get_frames()[0] == frame, 'Frames should match'


def test_service_item_load_duplicate_presentation_from_24x_service(state_media, settings):
    """
    Test the Service Item - simulate loading the same presentation file from a 2.4.x service file twice
    """
    presentation_service_time_246 = \
        {'serviceitem':
            {'data': [{'display_title': 'test1 ',
                       'image': 'C:\\OpenLPPortable-246\\Data\\presentations\\thumbnails\\prøve.odp\\slide1.png',
                       'notes': '\n',
                       'path': 'C:/Documents',
                       'title': 'prøve.odp'},
                      {'display_title': 'Thats all ',
                       'image': 'C:\\OpenLPPortable-246\\Data\\presentations\\thumbnails\\prøve.odp\\slide2.png',
                       'notes': '\n',
                       'path': 'C:/Documents',
                       'title': 'prøve.odp'}],
             'header': {'audit': '',
                        'auto_play_slides_loop': False,
                        'auto_play_slides_once': False,
                        'background_audio': [],
                        'capabilities': [17, 10, 19, 20, 21],
                        'data': '',
                        'end_time': 0,
                        'footer': [],
                        'from_plugin': False,
                        'icon': ':/plugins/plugin_presentations.png',
                        'media_length': 0,
                        'name': 'presentations',
                        'notes': '',
                        'plugin': 'presentations',
                        'processor': 'Impress',
                        'search': '',
                        'start_time': 0,
                        'theme': None,
                        'theme_overwritten': False,
                        'timed_slide_interval': 0,
                        'title': 'prøve.odp',
                        'type': 3,
                        'will_auto_start': False,
                        'xml_version': None}}}

    # GIVEN: 2 new service items and a mocked add icon and add_from_command function
    service_item1 = ServiceItem(None)
    service_item1.add_icon = MagicMock()
    service_item2 = ServiceItem(None)
    service_item2.add_icon = MagicMock()

    # create a temp folder with a dummy presentation file
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_folder:
        open(tmp_folder + '/prøve.odp', 'a').close()

        # WHEN: We add a custom from a saved service, twice
        service_item1.set_from_service(presentation_service_time_246, Path(tmp_folder))
        service_item2.set_from_service(presentation_service_time_246, Path(tmp_folder))

    # THEN: Loading should have succeeded and service items should be valid
    assert service_item1.is_valid is True, 'The new service item should be valid'
    assert service_item2.is_valid is True, 'The new service item should be valid'
    assert len(service_item1.slides) == 2, 'The service item should have 2 slides'
    assert len(service_item2.slides) == 2, 'The service item should have 2 slides'


@patch('openlp.core.lib.serviceitem.sha256_file_hash')
def test_service_item_load_song_and_audio_from_service(mock_sha256_file_hash, state_media, settings, service_item_env):
    """
    Test the Service Item - adding a song slide from a saved service
    """
    # GIVEN: A new service item and a mocked add icon function
    service_item = ServiceItem(None)
    service_item.add_icon = MagicMock()
    FormattingTags.load_tags()
    mock_sha256_file_hash.return_value = 'abcd'

    # WHEN: We add a custom from a saved service
    line = convert_file_service_item(TEST_PATH, 'serviceitem-song-linked-audio.osj')
    service_item.set_from_service(line, Path('/test/'))

    # THEN: We should get back a valid service item
    assert service_item.is_valid is True, 'The new service item should be valid'
    assert len(service_item.display_slides) == 6, 'The service item should have 6 display slides'
    assert len(service_item.capabilities) == 7, 'There should be 7 default custom item capabilities'
    assert 'Amazing Grace' == service_item.get_display_title(), 'The title should be "Amazing Grace"'
    assert CLEANED_VERSE[:-1] == service_item.get_frames()[0]['text'], \
        'The returned text matches the input, except the last line feed'
    assert 'Amazing Grace! how sweet the s' == service_item.get_frame_title(0), \
        '"Amazing Grace! how sweet the s" has been returned as the title'
    assert '’Twas grace that taught my hea' == service_item.get_frame_title(1), \
        '"’Twas grace that taught my hea" has been returned as the title'
    assert (Path('/test/amazing_grace.mp3'), 'abcd') == service_item.background_audio[0], \
        'The tuple ("/test/abcd.mp3", "abcd") should be in the background_audio list'


@patch('openlp.core.lib.serviceitem.sha256_file_hash')
def test_service_item_load_song_and_audio_from_service_no_media(mock_sha256_file_hash, state_media,
                                                                settings, service_item_env):
    """
    Test the Service Item - adding a song slide from a saved service
    """
    # GIVEN: A new service item and a mocked add icon function
    service_item = ServiceItem(None)
    service_item.add_icon = MagicMock()
    FormattingTags.load_tags()
    mock_sha256_file_hash.return_value = 'abcd'
    State().modules["media"].pass_preconditions = False

    # WHEN: We add a custom from a saved service
    line = convert_file_service_item(TEST_PATH, 'serviceitem-song-linked-audio.osj')
    service_item.set_from_service(line, Path('/test/'))

    # THEN: We should get back a valid service item
    assert service_item.is_valid is True, 'The new service item should not be valid'
    assert len(service_item.display_slides) == 6, 'The service item should have 6 display slides'
    assert len(service_item.capabilities) == 7, 'There should be 7 default custom item capabilities'
    assert 'Amazing Grace' == service_item.get_display_title(), 'The title should be "Amazing Grace"'
    assert CLEANED_VERSE[:-1] == service_item.get_frames()[0]['text'], \
        'The returned text matches the input, except the last line feed'
    assert 'Amazing Grace! how sweet the s' == service_item.get_frame_title(0), \
        '"Amazing Grace! how sweet the s" has been returned as the title'
    assert '’Twas grace that taught my hea' == service_item.get_frame_title(1), \
        '"’Twas grace that taught my hea" has been returned as the title'
    assert service_item.background_audio == [], 'The background_audio list is not populated'


@patch('openlp.core.lib.serviceitem.sha256_file_hash')
def test_service_item_to_dict_is_valid_json(mock_sha256_file_hash, state_media, settings, service_item_env):
    """
    Test the Service Item - Converting to to_dict response to json
    """
    # GIVEN: A new service item with song slide
    service_item = ServiceItem(None)
    service_item.add_icon = MagicMock()
    FormattingTags.load_tags()
    mock_sha256_file_hash.return_value = 'abcd'
    line = convert_file_service_item(TEST_PATH, 'serviceitem-song-linked-audio.osj')
    service_item.set_from_service(line, Path('/test/'))

    # WHEN: Generating a service item
    service_dict = service_item.to_dict()

    # THEN: We should get back a valid json object
    assert json.dumps(service_dict, cls=OpenLPJSONEncoder) is not None


def test_service_item_get_theme_data_global_level(settings):
    """
    Test the service item - get theme data when set to global theme level
    """
    # GIVEN: A service item with a theme and theme level set to global
    service_item = ServiceItem(None)
    service_item.theme = 'song_theme'
    mocked_theme_manager = MagicMock()
    mocked_theme_manager.global_theme = 'global_theme'
    mocked_theme_manager.get_theme_data = Mock(side_effect=lambda value: value)
    Registry().register('theme_manager', mocked_theme_manager)
    settings.setValue('servicemanager/service theme', 'service_theme')
    settings.setValue('themes/theme level', ThemeLevel.Global)

    # WHEN: Get theme data is run
    theme = service_item.get_theme_data()

    # THEN: theme should be the global theme
    assert theme == mocked_theme_manager.global_theme


def test_service_item_get_theme_data_service_level_service_undefined(settings):
    """
    Test the service item - get theme data when set to service theme level
    """
    # GIVEN: A service item with a theme and theme level set to service
    service_item = ServiceItem(None)
    service_item.theme = 'song_theme'
    mocked_theme_manager = MagicMock()
    mocked_theme_manager.global_theme = 'global_theme'
    mocked_theme_manager.get_theme_data = Mock(side_effect=lambda value: value)
    Registry().register('theme_manager', mocked_theme_manager)
    settings.setValue('servicemanager/service theme', 'service_theme')
    settings.setValue('themes/theme level', ThemeLevel.Service)

    # WHEN: Get theme data is run
    theme = service_item.get_theme_data()

    # THEN: theme should be the global theme
    assert theme == mocked_theme_manager.global_theme


def test_service_item_get_theme_data_service_level_service_defined(settings):
    """
    Test the service item - get theme data when set to service theme level
    """
    # GIVEN: A service item with a theme and theme level set to service
    service_item = ServiceItem(None)
    service_item.theme = 'song_theme'
    service_item.from_service = True
    mocked_theme_manager = MagicMock()
    mocked_theme_manager.global_theme = 'global_theme'
    mocked_theme_manager.get_theme_data = Mock(side_effect=lambda value: value)
    Registry().register('theme_manager', mocked_theme_manager)
    settings.setValue('servicemanager/service theme', 'service_theme')
    settings.setValue('themes/theme level', ThemeLevel.Service)

    # WHEN: Get theme data is run
    theme = service_item.get_theme_data()

    # THEN: theme should be the service theme
    assert theme == settings.value('servicemanager/service theme')


def test_service_item_get_theme_data_song_level(settings):
    """
    Test the service item - get theme data when set to song theme level
    """
    # GIVEN: A service item with a theme and theme level set to song
    service_item = ServiceItem(None)
    service_item.theme = 'song_theme'
    mocked_theme_manager = MagicMock()
    mocked_theme_manager.global_theme = 'global_theme'
    mocked_theme_manager.get_theme_data = Mock(side_effect=lambda value: value)
    Registry().register('theme_manager', mocked_theme_manager)
    settings.setValue('servicemanager/service theme', 'service_theme')
    settings.setValue('themes/theme level', ThemeLevel.Song)

    # WHEN: Get theme data is run
    theme = service_item.get_theme_data()

    # THEN: theme should be the song theme
    assert theme == service_item.theme


def test_service_item_get_theme_data_song_level_service_fallback(settings):
    """
    Test the service item - get theme data when set to song theme level
                            but the song theme doesn't exist
    """
    # GIVEN: A service item with no theme and theme level set to song
    service_item = ServiceItem(None)
    service_item.from_service = True
    mocked_theme_manager = MagicMock()
    mocked_theme_manager.global_theme = 'global_theme'
    mocked_theme_manager.get_theme_data = Mock(side_effect=lambda value: value)
    Registry().register('theme_manager', mocked_theme_manager)
    settings.setValue('servicemanager/service theme', 'service_theme')
    settings.setValue('themes/theme level', ThemeLevel.Song)

    # WHEN: Get theme data is run
    theme = service_item.get_theme_data()

    # THEN: theme should be the serice theme
    assert theme == settings.value('servicemanager/service theme')


def test_service_item_get_theme_data_song_level_global_fallback(settings):
    """
    Test the service item - get theme data when set to song theme level
                            but the song and service theme don't exist
    """
    # GIVEN: A service item with no theme and theme level set to song
    service_item = ServiceItem(None)
    mocked_theme_manager = MagicMock()
    mocked_theme_manager.global_theme = 'global_theme'
    mocked_theme_manager.get_theme_data = Mock(side_effect=lambda value: value)
    Registry().register('theme_manager', mocked_theme_manager)
    settings.setValue('servicemanager/service theme', 'service_theme')
    settings.setValue('themes/theme level', ThemeLevel.Song)

    # WHEN: Get theme data is run
    theme = service_item.get_theme_data()

    # THEN: theme should be the global theme
    assert theme == mocked_theme_manager.global_theme


def test_service_item_get_theme_data_theme_override(settings):
    """
    Test the service item - get theme data when set to global theme level
                            but the service item has the `ProvidesOwnTheme`
                            capability overriding the global theme
    """
    # GIVEN: A service item with a theme and theme level set to global
    service_item = ServiceItem(None)
    service_item.theme = 'item_theme'
    service_item.add_capability(ItemCapabilities.ProvidesOwnTheme)
    mocked_theme_manager = MagicMock()
    mocked_theme_manager.global_theme = 'global_theme'
    mocked_theme_manager.get_theme_data = Mock(side_effect=lambda value: value)
    Registry().register('theme_manager', mocked_theme_manager)
    settings.setValue('servicemanager/service theme', 'service_theme')
    settings.setValue('themes/theme level', ThemeLevel.Global)

    # WHEN: Get theme data is run
    theme = service_item.get_theme_data()

    # THEN: theme should be the service item's theme
    assert theme == service_item.theme


def test_remove_capability(settings):
    # GIVEN: A service item with a capability
    service_item = ServiceItem(None)
    service_item.add_capability(ItemCapabilities.CanEdit)
    assert ItemCapabilities.CanEdit in service_item.capabilities

    # WHEN: A capability is removed
    service_item.remove_capability(ItemCapabilities.CanEdit)

    # THEN: The capability should no longer be there
    assert ItemCapabilities.CanEdit not in service_item.capabilities, 'The capability should not be in the list'


def test_get_transition_delay_own_display(settings):
    """
    Test the service item - get approx transition delay from theme
    """
    # GIVEN: A service item with a theme and theme level set to global
    service_item = ServiceItem(None)
    service_item.add_capability(ItemCapabilities.ProvidesOwnDisplay)
    service_item.theme = 'song_theme'
    mocked_theme_manager = MagicMock()
    mocked_theme_manager.global_theme = 'global_theme'
    Registry().register('theme_manager', mocked_theme_manager)
    settings.setValue('servicemanager/service theme', 'service_theme')
    settings.setValue('themes/theme level', ThemeLevel.Global)

    # WHEN: Get theme data is run
    delay = service_item.get_transition_delay()

    # THEN: theme should be 0.5s
    assert delay == 0.5


def test_get_transition_delay_no_transition(settings):
    """
    Test the service item - get approx transition delay from theme
    """
    # GIVEN: A service item with a theme and theme level set to global
    service_item = ServiceItem(None)
    mocked_theme_manager = MagicMock()
    mocked_theme_manager.global_theme = 'global_theme'
    mocked_theme_manager.get_theme_data = Mock(return_value=MagicMock(**{
        'display_slide_transition': False,
        'display_slide_transition_speed': TransitionSpeed.Normal
    }))
    Registry().register('theme_manager', mocked_theme_manager)
    settings.setValue('themes/theme level', ThemeLevel.Global)

    # WHEN: Get theme data is run
    delay = service_item.get_transition_delay()

    # THEN: theme should be 0.5s
    assert delay == 0.5


def test_get_transition_delay_normal(settings):
    """
    Test the service item - get approx transition delay from theme
    """
    # GIVEN: A service item with a theme and theme level set to global
    service_item = ServiceItem(None)
    mocked_theme_manager = MagicMock()
    mocked_theme_manager.global_theme = 'global_theme'
    mocked_theme_manager.get_theme_data = Mock(return_value=MagicMock(**{
        'display_slide_transition': True,
        'display_slide_transition_speed': TransitionSpeed.Normal
    }))
    Registry().register('theme_manager', mocked_theme_manager)
    settings.setValue('themes/theme level', ThemeLevel.Global)

    # WHEN: Get theme data is run
    delay = service_item.get_transition_delay()

    # THEN: theme should be 1s
    assert delay == 1


def test_get_transition_delay_slow(settings):
    """
    Test the service item - get approx transition delay from theme
    """
    # GIVEN: A service item with a theme and theme level set to global
    service_item = ServiceItem(None)
    mocked_theme_manager = MagicMock()
    mocked_theme_manager.global_theme = 'global_theme'
    mocked_theme_manager.get_theme_data = Mock(return_value=MagicMock(**{
        'display_slide_transition': True,
        'display_slide_transition_speed': TransitionSpeed.Slow
    }))
    Registry().register('theme_manager', mocked_theme_manager)
    settings.setValue('themes/theme level', ThemeLevel.Global)

    # WHEN: Get theme data is run
    delay = service_item.get_transition_delay()

    # THEN: theme should be 2s
    assert delay == 2


@patch('openlp.core.lib.serviceitem.sha256_file_hash')
def test_to_dict_text_item(mocked_sha256_file_hash, state_media, settings, service_item_env):
    """
    Test that the to_dict() method returns the correct data for the service item
    """
    # GIVEN: A ServiceItem with a service loaded from file
    mocked_plugin = MagicMock()
    mocked_plugin.name = 'songs'
    service_item = ServiceItem(mocked_plugin)
    service_item.add_icon = MagicMock()
    mocked_sha256_file_hash.return_value = 'abcd'
    FormattingTags.load_tags()
    line = convert_file_service_item(TEST_PATH, 'serviceitem-song-linked-audio.osj')
    if is_win():
        fake_path = Path('c:\\test\\')
    else:
        fake_path = Path('/test/')
    service_item.set_from_service(line, fake_path)

    # WHEN: to_dict() is called
    result = service_item.to_dict()

    # THEN: The correct dictionary should be returned
    expected_fake_path = fake_path / 'amazing_grace.mp3'
    expected_dict = {

        'audit': ['Amazing Grace', ['John Newton'], '', ''],
        'backgroundAudio': [(expected_fake_path, 'abcd')],
        'capabilities': [2, 1, 5, 8, 9, 13, 15],
        'footer': ['Amazing Grace', 'Written by: John Newton'],
        'fromPlugin': False,
        'isThemeOverwritten': False,
        'name': 'songs',
        'notes': '',
        'slides': [
            {
                'chords': 'Amazing Grace! how sweet the sound\n'
                          'That saved a wretch like me;\n'
                          'I once was lost, but now am found,\n'
                          'Was blind, but now I see.',
                'html': 'Amazing Grace! how sweet the sound\n'
                        'That saved a wretch like me;\n'
                        'I once was lost, but now am found,\n'
                        'Was blind, but now I see.',
                'selected': False,
                'tag': 'V1',
                'text': 'Amazing Grace! how sweet the sound\n'
                        'That saved a wretch like me;\n'
                        'I once was lost, but now am found,\n'
                        'Was blind, but now I see.',
                'title': 'Amazing Grace',
                'footer': 'Amazing Grace<br>Written by: John Newton'
            },
            {
                'chords': '’Twas grace that taught my heart to fear,\n'
                          'And grace my fears relieved;\n'
                          'How precious did that grace appear,\n'
                          'The hour I first believed!',
                'html': '’Twas grace that taught my heart to fear,\n'
                        'And grace my fears relieved;\n'
                        'How precious did that grace appear,\n'
                        'The hour I first believed!',
                'selected': False,
                'tag': 'V2',
                'text': '’Twas grace that taught my heart to fear,\n'
                        'And grace my fears relieved;\n'
                        'How precious did that grace appear,\n'
                        'The hour I first believed!',
                'title': 'Amazing Grace',
                'footer': 'Amazing Grace<br>Written by: John Newton'
            },
            {
                'chords': 'Through many dangers, toils and snares\n'
                          'I have already come;\n'
                          '’Tis grace that brought me safe thus far,\n'
                          'And grace will lead me home.',
                'html': 'Through many dangers, toils and snares\n'
                        'I have already come;\n'
                        '’Tis grace that brought me safe thus far,\n'
                        'And grace will lead me home.',
                'selected': False,
                'tag': 'V3',
                'text': 'Through many dangers, toils and snares\n'
                        'I have already come;\n'
                        '’Tis grace that brought me safe thus far,\n'
                        'And grace will lead me home.',
                'title': 'Amazing Grace',
                'footer': 'Amazing Grace<br>Written by: John Newton'
            },
            {
                'chords': 'The Lord has promised good to me,\n'
                          'His word my hope secures;\n'
                          'He will my shield and portion be\n'
                          'As long as life endures.',
                'html': 'The Lord has promised good to me,\n'
                        'His word my hope secures;\n'
                        'He will my shield and portion be\n'
                        'As long as life endures.',
                'selected': False,
                'tag': 'V4',
                'text': 'The Lord has promised good to me,\n'
                        'His word my hope secures;\n'
                        'He will my shield and portion be\n'
                        'As long as life endures.',
                'title': 'Amazing Grace',
                'footer': 'Amazing Grace<br>Written by: John Newton'
            },
            {
                'chords': 'Yes, when this heart and flesh shall fail,\n'
                          'And mortal life shall cease,\n'
                          'I shall possess within the veil\n'
                          'A life of joy and peace.',
                'html': 'Yes, when this heart and flesh shall fail,\n'
                        'And mortal life shall cease,\n'
                        'I shall possess within the veil\n'
                        'A life of joy and peace.',
                'selected': False,
                'tag': 'V5',
                'text': 'Yes, when this heart and flesh shall fail,\n'
                        'And mortal life shall cease,\n'
                        'I shall possess within the veil\n'
                        'A life of joy and peace.',
                'title': 'Amazing Grace',
                'footer': 'Amazing Grace<br>Written by: John Newton'
            },
            {
                'chords': 'When we’ve been there a thousand years,\n'
                          'Bright shining as the sun,\n'
                          'We’ve no less days to sing God’s praise\n'
                          'Than when we first begun.',
                'html': 'When we’ve been there a thousand years,\n'
                        'Bright shining as the sun,\n'
                        'We’ve no less days to sing God’s praise\n'
                        'Than when we first begun.',
                'selected': False,
                'tag': 'V6',
                'text': 'When we’ve been there a thousand years,\n'
                        'Bright shining as the sun,\n'
                        'We’ve no less days to sing God’s praise\n'
                        'Than when we first begun.',
                'title': 'Amazing Grace',
                'footer': 'Amazing Grace<br>Written by: John Newton'
            }
        ],
        'theme': None,
        'title': 'Amazing Grace',
        'type': ServiceItemType.Text,
        'data': {'authors': 'John Newton', 'title': 'amazing grace@'}
    }
    assert result == expected_dict


def test_to_dict_image_item(state_media, settings, service_item_env):
    """
    Test that the to_dict() method returns the correct data for the service item
    """
    # GIVEN: A ServiceItem with a service loaded from file
    mocked_plugin = MagicMock()
    mocked_plugin.name = 'image'
    service_item = ServiceItem(mocked_plugin)
    service_item.add_icon = MagicMock()
    FormattingTags.load_tags()
    line = convert_file_service_item(TEST_PATH, 'serviceitem_image_2.osj')
    service_item.set_from_service(line)

    # WHEN: to_dict() is called
    result = service_item.to_dict()

    # THEN: The correct dictionary should be returned
    expected_dict = {
        'audit': '',
        'backgroundAudio': [],
        'capabilities': [3, 1, 5, 6],
        'footer': [],
        'fromPlugin': False,
        'isThemeOverwritten': False,
        'name': 'images',
        'notes': '',
        'slides': [
            {
                'html': 'image_1.jpg',
                'selected': False,
                'tag': 1,
                'text': 'image_1.jpg',
                'title': 'Images'
            }
        ],
        'theme': -1,
        'title': 'Images',
        'type': ServiceItemType.Image,
        'data': {}
    }
    assert result == expected_dict


@patch('openlp.core.lib.serviceitem.AppLocation.get_data_path')
@patch('openlp.core.lib.serviceitem.image_to_data_uri')
def test_to_dict_presentation_item(mocked_image_uri, mocked_get_data_path, state_media, settings, service_item_env):
    """
    Test that the to_dict() method returns the correct data for the service item
    """
    # GIVEN: A ServiceItem with a service loaded from file
    mocked_plugin = MagicMock()
    mocked_plugin.name = 'presentations'
    service_item = ServiceItem(mocked_plugin)
    service_item.capabilities = [ItemCapabilities.HasThumbnails]
    presentation_name = 'test.pptx'
    mocked_get_data_path.return_value = Path('/path/to/')
    image = Path('thumbnails/abcd/slide1.png')
    display_title = 'DisplayTitle'
    notes = 'Note1\nNote2\n'
    mocked_image_uri.side_effect = lambda x: 'your img uri at: {}'.format(x.as_posix())

    # WHEN: adding presentation to service_item
    with patch('openlp.core.lib.serviceitem.sha256_file_hash') as mocked_sha256_file_hash, \
            patch('openlp.core.lib.serviceitem.AppLocation.get_section_data_path') as mocked_get_section_data_path:
        mocked_sha256_file_hash.return_value = '4a067fed6834ea2bc4b8819f11636365'
        mocked_get_section_data_path.return_value = Path('/path/to/presentations/')
        service_item.add_from_command(TEST_PATH, presentation_name, image, display_title, notes)

    # WHEN: to_dict() is called
    result = service_item.to_dict()

    # THEN: The correct dictionary should be returned
    expected_dict = {
        'audit': '',
        'backgroundAudio': [],
        'capabilities': [21],
        'footer': [],
        'fromPlugin': False,
        'isThemeOverwritten': False,
        'name': 'presentations',
        'notes': '',
        'slides': [
            {
                'html': 'test.pptx',
                'selected': False,
                'tag': 1,
                'text': 'test.pptx',
                'title': '',
                'img': 'your img uri at: /path/to/presentations/thumbnails/4a067fed6834ea2bc4b8819f11636365/slide1.png'
            }
        ],
        'theme': None,
        'title': '',
        'type': ServiceItemType.Command,
        'data': {}
    }
    assert result == expected_dict


def test_add_from_text_adds_per_slide_footer_html():
    """
    Test the Service Item - adding text slides with per slide footer_html
    """
    # GIVEN: A service item and two slides
    service_item = ServiceItem(None)
    slide1 = "This is the first slide"
    slide1FooterHtml = '<small>First Footer</small>'
    slide2 = "This is the second slide"
    slide2FooterHtml = '<small>Second Footer</small>'

    # WHEN: adding text slides to service_item
    service_item.add_from_text(slide1, footer_html=slide1FooterHtml)
    service_item.add_from_text(slide2, footer_html=slide2FooterHtml)

    # THEN: Slides should be added with correctly numbered verse tags (Should start at 1)
    assert service_item.slides == [
        {'text': slide1, 'title': slide1, 'verse': '1', 'footer_html': slide1FooterHtml},
        {'text': slide2, 'title': slide2, 'verse': '2', 'footer_html': slide2FooterHtml}
    ]


@patch('openlp.core.lib.serviceitem.UiIcons')
def test_add_from_text_per_slide_footer_html_is_honoured(mock_uiicons, settings, registry):
    """
    Test the Service Item - adding text slides with per slide footer_html is honoured
    """
    # GIVEN: A service item, mocked live_controller and renderer, and two slides
    renderer_mock = MagicMock()
    Registry().register('live_controller', MagicMock())
    Registry().register('renderer', renderer_mock)
    Registry().register('service_list', MagicMock())
    renderer_mock.format_slide.side_effect = lambda text, item: [text]
    service_item = ServiceItem(None)
    slide1 = "This is the first slide"
    slide1FooterHtml = '<small>First Footer</small>'
    slide2 = "This is the second slide"
    slide2FooterHtml = '<small>Second Footer</small>'

    # WHEN: adding text slides to service_item
    service_item.add_from_text(slide1, footer_html=slide1FooterHtml)
    service_item.add_from_text(slide2, footer_html=slide2FooterHtml)

    service_item._create_slides()

    # THEN: Slides should be added with correctly numbered verse tags (Should start at 1)
    assert service_item._rendered_slides[0]['footer'] == slide1FooterHtml
    assert service_item._rendered_slides[1]['footer'] == slide2FooterHtml


@pytest.mark.parametrize('plugin_name,icon', [('songs', 'music'), ('bibles', 'bible'),
                                              ('presentations', 'presentation'), ('images', 'picture'),
                                              ('media', 'video'), ('egwlibrary', 'library')])
def test_add_icon(registry, plugin_name, icon):
    """Test that adding an icon works according to the plugin name"""
    # GIVEN: A service item
    service_item = ServiceItem()
    service_item.name = plugin_name

    # WHEN: add_icon() is called
    service_item.add_icon()

    # THEN: The icon should be correct
    assert service_item.icon.name() == getattr(UiIcons(), icon).name()


def test_get_service_repr_song(registry: Registry):
    """Test the get_service_repr() method with a song"""
    # GIVEN: A service item
    registry.register('renderer', MagicMock())
    service_item = ServiceItem()
    service_item.name = 'songs'
    service_item.theme = 'Default'
    service_item.title = 'Test Song'
    service_item.add_from_text('This is the first slide')
    service_item.add_from_text('This is the second slide')
    service_item._create_slides()
    service_item.add_icon()

    # WHEN: get_service_repr() is called
    rep = service_item.get_service_repr(False)

    # THEN: The correct repr should have been made
    assert rep['header'].get('name') == 'songs'
    assert rep['header'].get('plugin') == 'songs'
    assert rep['header'].get('theme') == 'Default'
    assert rep['header'].get('title') == 'Test Song'


@pytest.mark.parametrize('is_text, is_clear_called', ((True, True), (False, False)))
def test_update_theme(registry: Registry, is_text: bool, is_clear_called: bool):
    """Test that the update_theme() method invalidates the cache when the theme changes for text items"""
    # GIVEN: A service item
    registry.register('renderer', MagicMock())
    service_item = ServiceItem()
    service_item._clear_slides_cache = MagicMock()
    if is_text:
        service_item.service_item_type = ServiceItemType.Text
    else:
        service_item.service_item_type = ServiceItemType.Image

    # WHEN: update_theme() is called
    service_item.update_theme('Snow')

    # THEN: The clear method should or should not have been called
    if is_clear_called:
        service_item._clear_slides_cache.assert_called_once()
    else:
        service_item._clear_slides_cache.assert_not_called()
