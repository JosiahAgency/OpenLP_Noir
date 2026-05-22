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
Package to test the openlp.core.ui.media.mediaplayer package.
This class is for playing Media within OpenLP.
"""
from unittest.mock import MagicMock, call, patch

from PySide6 import QtCore
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
import pytest

from openlp.core.common.registry import Registry
from openlp.core.display.screens import Screen, ScreenList
from openlp.core.ui.media import MediaPlayItem, MediaType
from openlp.core.ui.media.mediaplayer import MediaPlayer


@pytest.fixture
def base_media_player(qapp):
    """Local test setup - qapp need to allow tests to run standalone.
    """
    media_player = MediaPlayer()
    media_player.controller = MagicMock()
    media_player.controller.is_live = True
    media_player.media_capture_session = MagicMock()
    media_player.media_player = MagicMock()
    media_player.audio_output = QAudioOutput()
    media_player.video_widget = MagicMock()
    yield media_player


def test_init(mock_settings):
    """
    Test that the media player class initialises correctly
    """
    # WHEN: The MediaPlayer class is instantiated
    media_player = MediaPlayer()

    # THEN: The correct variables are set
    assert media_player is not None


@patch('openlp.core.ui.media.mediaplayer.QtWidgets')
def test_setup_live(MockedQtWidgets, settings):
    """
    Test the setup method for Live Controller
    """
    # GIVEN: A bunch of mocked out stuff and a MediaPlayer object
    mocked_output_display = MagicMock()
    mocked_controller = MagicMock()
    mocked_controller.is_live = True
    mocked_output_display.size.return_value = (10, 10)
    media_player = MediaPlayer(None)

    # WHEN: setup() is run
    media_player.setup(mocked_controller, mocked_output_display)

    # THEN: The live media widget should be set up correctly
    mocked_controller.media_widget.setVisible.assert_called_once()
    mocked_controller.media_widget.setWindowFlags.assert_called_once()
    mocked_controller.media_widget.setAttribute.assert_called_once()
    assert media_player.media_player is not None
    assert media_player.audio_output is not None
    assert media_player.video_widget is not None
    assert media_player.video_widget.isVisible() is False


@patch('openlp.core.ui.media.mediaplayer.QtWidgets')
def test_setup_preview(MockedQtWidgets, settings):
    """
    Test the setup method for Preview controller
    """
    # GIVEN: A bunch of mocked out stuff and a MediaPlayer object
    mocked_output_display = MagicMock()
    mocked_controller = MagicMock()
    mocked_controller.is_live = False
    mocked_output_display.size.return_value = (10, 10)
    media_player = MediaPlayer(None)

    # WHEN: setup() is run
    media_player.setup(mocked_controller, mocked_output_display)

    # THEN: The live media widget should be set up correctly
    mocked_controller.media_widget.setVisible.assert_called_once()
    mocked_controller.media_widget.setWindowFlags.assert_not_called()
    mocked_controller.media_widget.setAttribute.assert_not_called()
    assert media_player.media_player is not None
    assert media_player.audio_output is not None
    assert media_player.video_widget is not None


def test_load_media(base_media_player):
    """
    Test loading a media into MediaPlayer
    """
    # GIVEN: A mocked out media_player
    media_path = '/path/to/media.mp4'
    base_media_player.controller.media_play_item.media_type = MediaType.Video
    base_media_player.controller.media_play_item.media_file = media_path
    # WHEN: A video is loaded
    result = base_media_player.load()
    # THEN: The video should be loaded
    base_media_player.media_player.setAudioOutput.assert_called_once()
    assert result is True


def test_load_with_stream(base_media_player):
    """
    Test send stream to load function - this is not valid!
    """
    # GIVEN: A stream load call with a missing stream
    base_media_player.controller.media_play_item.media_type = MediaType.DeviceStream
    base_media_player.controller.media_play_item.external_stream = None
    # WHEN: A video is loaded into media_player
    result = base_media_player.load_stream()
    # THEN: The media should fail
    base_media_player.media_player.setAudioOutput.assert_not_called()
    assert result is False


def test_load_network_stream(base_media_player):
    """
    Test loading a networkstream request
    """
    # GIVEN: A mocked out media devices object
    mrl = 'http://128.0.0.1'
    base_media_player.controller.media_play_item.external_stream = [mrl]
    base_media_player.controller.media_play_item.media_type = MediaType.NetworkStream
    # WHEN: A device stream is loaded
    result = base_media_player.load_stream()
    # THEN: The video should be loaded
    base_media_player.media_capture_session.setVideoOutput.assert_called_once()
    base_media_player.media_player.setAudioInput.assert_not_called()
    base_media_player.media_player.setVideoOutput.assert_called_with(base_media_player.video_widget)
    base_media_player.media_player.setSource.assert_called_with(mrl)
    assert result is True


def test_resize_live(base_media_player):
    """
    Test resizing the player
    """
    # GIVEN: A display object and a MediaPlayer instance
    base_media_player.media_widget = MagicMock()
    screen_list = ScreenList()
    screen_list.screens = [
        Screen(number=0, geometry=QtCore.QRect(0, 0, 1024, 768), is_primary=True),
        Screen(number=1, geometry=QtCore.QRect(1024, 0, 1024, 768), is_primary=False, is_display=True)
    ]
    base_media_player.controller.is_live = True

    # WHEN: resize is called
    base_media_player.resize()

    # THEN: The right methods should have been called
    base_media_player.controller.media_widget.setGeometry.assert_called_with(QtCore.QRect(1024, 0, 1024, 768))


def test_resize_not_live(base_media_player):
    """
    Test resizing the player
    """
    # GIVEN: A display object and a MediaPlayer instance
    base_media_player.media_widget = MagicMock()
    base_media_player.controller.preview_display.size.return_value = (10, 10)
    base_media_player.controller.is_live = False

    # WHEN: resize is called
    base_media_player.resize()

    # THEN: The right methods should have been called
    base_media_player.controller.media_widget.resize.assert_called_with((10, 10))


def test_play_media(base_media_player):
    """
    Test the play() method
    """
    # GIVEN: A bunch of mocked out things
    base_media_player.media_player = MagicMock()
    # WHEN: play() is called
    base_media_player.play()

    # THEN: A bunch of things should happen to play the media
    base_media_player.media_player.play.assert_called_once()


def test_play_stream(base_media_player):
    """
    Test the play() method
    """
    # GIVEN: A bunch of mocked out things
    base_media_player.controller.media_play_item.media_type = MediaType.DeviceStream
    base_media_player.device_video_input = MagicMock()
    base_media_player.device_audio_input = MagicMock()
    base_media_player.media_player = MagicMock()
    # WHEN: play() is called
    base_media_player.play()

    # THEN: A bunch of things should happen to play the media
    base_media_player.media_player.play.assert_not_called()
    base_media_player.device_video_input.start.assert_called_once()
    base_media_player.device_audio_input.setMuted.assert_called_with(False)


def test_pause_media(base_media_player):
    """
    Test that the pause method works correctly
    """
    # GIVEN: A mocked out media_player method
    base_media_player.media_player = MagicMock()
    # WHEN: The media is paused
    base_media_player.pause()

    # THEN: The pause method should exit early
    base_media_player.media_player.pause.assert_called_once()


def test_pause_stream(base_media_player):
    """
    Test that the pause method works correctly
    """
    # GIVEN: A mocked out media_player method
    base_media_player.controller.media_play_item.media_type = MediaType.DeviceStream
    base_media_player.device_video_input = MagicMock()
    base_media_player.device_audio_input = MagicMock()
    base_media_player.media_player = MagicMock()
    # WHEN: The media is paused
    base_media_player.pause()

    # THEN: The pause method should exit early
    base_media_player.media_player.pause.assert_not_called()
    base_media_player.device_video_input.stop.assert_called_once()
    base_media_player.device_audio_input.setMuted.assert_called_with(True)


def test_stop_media(base_media_player):
    """
    Test stopping the current item
    """
    # GIVEN: A display object and a MediaPlayer instance and some mocked threads
    base_media_player.media_player = MagicMock()

    # WHEN: stop is called
    base_media_player.stop()

    # THEN: the media player should have been asked to stop
    base_media_player.media_player.stop.assert_called_once()


def test_stop_stream(base_media_player):
    """
    Test stopping the current item
    """
    # GIVEN: A display object and a MediaPlayer instance and some mocked threads
    base_media_player.controller.media_play_item.media_type = MediaType.DeviceStream
    base_media_player.device_video_input = MagicMock()
    base_media_player.device_audio_input = MagicMock()
    base_media_player.media_player = MagicMock()

    # WHEN: stop is called
    base_media_player.stop()

    # THEN: A media_player should have been started to stop
    base_media_player.media_player.stop.assert_not_called()
    base_media_player.device_video_input.stop.assert_called_once()
    base_media_player.device_audio_input.setMuted.assert_called_with(True)


def test_volume(base_media_player):
    """
    Test setting the volume
    """
    # GIVEN: A display object and a MediaPlayer instance
    base_media_player.audio_output = MagicMock()
    # WHEN: The volume is set
    base_media_player.volume(10)

    # THEN: The volume should have been set
    base_media_player.audio_output.setVolume.assert_called_with(float(0.1))


def test_seek_seekable_media(base_media_player):
    """
    Test seeking something that can be seeked
    """
    # GIVEN: Unseekable media
    base_media_player.media_player = MagicMock()
    base_media_player.media_player.isSeekable.return_value = True
    # WHEN: seek() is called
    base_media_player.seek(100)

    # THEN: nothing should happen
    base_media_player.media_player.setPosition.assert_called_with(100)


def test_seek_unseekable_media(base_media_player):
    """
    Test seeking something that can't be seeked
    """
    # GIVEN: Unseekable media
    base_media_player.media_player = MagicMock()
    base_media_player.media_player.isSeekable.return_value = False
    # WHEN: seek() is called
    base_media_player.seek(100)

    # THEN: nothing should happen
    base_media_player.media_player.setPosition.assert_not_called()


def test_reset(base_media_player):
    """
    Test the reset() method
    """
    # GIVEN: Some mocked out stuff
    base_media_player.media_player = MagicMock()

    # WHEN: reset() is called
    base_media_player.reset()

    # THEN: The media should be stopped and invisible
    base_media_player.media_player.stop.assert_called_once()


def test_update_ui(base_media_player):
    """
    Test updating the UI
    """
    # GIVEN: A whole bunch of mocks
    base_media_player.controller.media_play_item = MediaPlayItem()
    base_media_player.media_player.position.return_value = 300
    base_media_player.controller.mediabar.seek_slider.isSliderDown.return_value = False

    # WHEN: update_ui() is called
    base_media_player.update_ui()

    # THEN: Certain methods should be called
    base_media_player.controller.mediabar.seek_slider.setSliderPosition.assert_called_with(300)
    expected_calls = [call(True), call(False)]
    assert expected_calls == base_media_player.controller.mediabar.seek_slider.blockSignals.call_args_list


def test_toggle_loop_true(base_media_player):
    """
    Test the toggling method updates media player correctly
    """
    # GIVEN: A the default test setup
    # WHEN: when you ask to toggle
    base_media_player.toggle_loop(True)
    # THEN: We should have and infinite loop
    base_media_player.media_player.setLoops.assert_called_with(QMediaPlayer.Loops.Infinite)


def test_toggle_loop_false(base_media_player):
    """
    Test the toggling method updates media player correctly
    """
    # GIVEN: A the default test setup
    # WHEN: when you ask to toggle
    base_media_player.toggle_loop(False)
    # THEN: We should have and infinite loop
    base_media_player.media_player.setLoops.assert_called_with(QMediaPlayer.Loops.Once)


def test_media_status_changed_live_media(base_media_player, registry):
    """
    Test the handing of QMediaPlayer event status changes for live
    """
    # GIVEN: A the lived set up
    base_media_player.controller.media_play_item.media_type = MediaType.Video
    base_media_player.controller.is_live = True
    mocked_controller = MagicMock()
    Registry().register("media_controller", mocked_controller)
    # WHEN: the media state changes and it is end of media
    base_media_player.media_status_changed_event(QMediaPlayer.MediaStatus.EndOfMedia)
    # THEN: the live media status event is triggered
    mocked_controller.live_media_status_changed.emit.assert_called_once()
    mocked_controller.preview_media_status_changed.emit.assert_not_called()


def test_media_status_changed_preview_media(base_media_player, registry):
    """
    Test the handing of QMediaPlayer event status changes for preview
    """
    # GIVEN: A the lived set up
    base_media_player.controller.media_play_item.media_type = MediaType.Video
    base_media_player.controller.is_live = False
    mocked_controller = MagicMock()
    Registry().register("media_controller", mocked_controller)
    # WHEN: the media state changes and it is end of media
    base_media_player.media_status_changed_event(QMediaPlayer.MediaStatus.EndOfMedia)
    # THEN: the live media status event is triggered
    mocked_controller.live_media_status_changed.emit.assert_not_called()
    mocked_controller.preview_media_status_changed.emit.assert_called_once()


def test_media_status_changed_dual(base_media_player, registry):
    """
    Test the handing of QMediaPlayer event status changes for Dual media
    """
    # GIVEN: A the lived set up
    base_media_player.controller.media_play_item.media_type = MediaType.Dual
    base_media_player.controller.is_live = False
    mocked_controller = MagicMock()
    Registry().register("media_controller", mocked_controller)
    # WHEN: the media state changes and it is end of media
    base_media_player.media_status_changed_event(QMediaPlayer.MediaStatus.EndOfMedia)
    # THEN: the live media status event is triggered
    mocked_controller.live_media_status_changed.emit.assert_not_called()
    mocked_controller.preview_media_status_changed.emit.assert_not_called()


def test_media_status_changed_not_end(base_media_player, registry):
    """
    Test the handing of QMediaPlayer event status changes when not end of media
    """
    # GIVEN: A the lived set up
    base_media_player.controller.media_play_item.media_type = MediaType.Video
    base_media_player.controller.is_live = False
    mocked_controller = MagicMock()
    Registry().register("media_controller", mocked_controller)
    # WHEN: the media state changes and it is end of media
    base_media_player.media_status_changed_event(QMediaPlayer.MediaStatus.LoadedMedia)
    # THEN: the live media status event is triggered
    mocked_controller.live_media_status_changed.emit.assert_not_called()
    mocked_controller.preview_media_status_changed.emit.assert_not_called()


def test_position_changed_live(base_media_player, registry):
    """
    Test the handing of QMediaPlayer when the position changes
    """
    # GIVEN: The live set up
    base_media_player.controller.media_play_item.media_type = MediaType.Video
    base_media_player.controller.is_live = True
    base_media_player.controller.media_play_item.timer = 0
    mocked_controller = MagicMock()
    Registry().register("media_controller", mocked_controller)
    # WHEN: the media position changes and it is end of media
    base_media_player.position_changed_event(400)
    # THEN: the live position changed event is triggered
    mocked_controller.live_media_tick.emit.assert_called_once()
    mocked_controller.preview_media_tick.emit.assert_not_called()
    assert base_media_player.controller.media_play_item.timer == 400


def test_position_changed_preview(base_media_player, registry):
    """
    Test the handing of QMediaPlayer when the position changes Preview
    """
    # GIVEN: The live set up
    base_media_player.controller.media_play_item.media_type = MediaType.Video
    base_media_player.controller.is_live = False
    base_media_player.controller.media_play_item.timer = 0
    mocked_controller = MagicMock()
    Registry().register("media_controller", mocked_controller)
    # WHEN: the media position changes and it is end of media
    base_media_player.position_changed_event(400)
    # THEN: the live position changed event is triggered
    mocked_controller.live_media_tick.emit.assert_not_called()
    mocked_controller.preview_media_tick.emit.assert_called_once()
    assert base_media_player.controller.media_play_item.timer == 400


def test_position_changed_dual(base_media_player, registry):
    """
    Test the handing of QMediaPlayer when the position changes - Dual
    """
    # GIVEN: The live set up
    base_media_player.controller.media_play_item.media_type = MediaType.Dual
    base_media_player.controller.is_live = True
    base_media_player.controller.media_play_item.timer = 0
    mocked_controller = MagicMock()
    Registry().register("media_controller", mocked_controller)
    # WHEN: the media position changes and it is end of media
    base_media_player.position_changed_event(400)
    # THEN: the live position changed event is triggered
    mocked_controller.live_media_tick.emit.assert_not_called()
    mocked_controller.preview_media_tick.emit.assert_not_called()
    assert base_media_player.controller.media_play_item.timer == 0
