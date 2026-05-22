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
from unittest.mock import MagicMock

from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
import pytest

from openlp.core.common.registry import Registry
from openlp.core.ui.media import MediaType
from openlp.core.ui.media.audioplayer import AudioPlayer


@pytest.fixture
def base_audio_player():
    """Local test setup - qapp need to allow tests to run standalone.
    """
    audio_player = AudioPlayer()
    audio_player.controller = MagicMock()
    audio_player.controller.is_live = True
    audio_player.media_player = MagicMock()
    audio_player.audio_output = QAudioOutput()
    yield audio_player


def test_init():
    """
    Test that the media player class initialises correctly
    """
    # WHEN: The AudioPlayer class is instantiated
    audio_player = AudioPlayer()

    # THEN: The correct variables are set
    assert audio_player is not None


def test_setup(base_audio_player, settings):
    """
    Test the setup method
    """
    # GIVEN: A bunch of mocked out stuff and a MediaPlayer object
    mocked_output_display = MagicMock()
    mocked_controller = MagicMock()
    mocked_controller.is_live = True

    # WHEN: setup() is run
    base_audio_player.setup(mocked_controller, mocked_output_display)

    # THEN: The live media widget should be set up correctly
    assert base_audio_player.media_player is not None
    assert base_audio_player.audio_output is not None


def test_load_audio(base_audio_player):
    """
    Test loading a media into MediaPlayer
    """
    # GIVEN: A mocked out audio_player method
    media_path = '/path/to/media.mp3'
    base_audio_player.controller.media_play_item.media_type = MediaType.Audio
    base_audio_player.controller.media_play_item.audio_file = media_path
    # WHEN: An audio file needs to be played
    result = base_audio_player.load()
    # THEN: The video should be loaded
    base_audio_player.media_player.setSource.assert_called_once()
    assert result is True


def test_load_no_audio(base_audio_player):
    """
    Test loading a media into MediaPlayer
    """
    # GIVEN: A mocked out audio_player method
    base_audio_player.controller.media_play_item.media_type = MediaType.Audio
    base_audio_player.controller.media_play_item.audio_file = None
    # WHEN: An audio file needs to be played
    result = base_audio_player.load()
    # THEN: The video should be loaded
    base_audio_player.media_player.setSource.assert_not_called()
    assert result is False


def test_play(base_audio_player):
    """
    Test the play() method
    """
    # GIVEN: A bunch of mocked out things
    base_audio_player.audio_player = MagicMock()
    # WHEN: play() is called
    base_audio_player.play()

    # THEN: A bunch of things should happen to play the media
    base_audio_player.media_player.play.assert_called_once()


def test_pause(base_audio_player):
    """
    Test that the pause method works correctly
    """
    # GIVEN: A mocked out audio_player method
    base_audio_player.media_player = MagicMock()
    # WHEN: The media is paused
    base_audio_player.pause()

    # THEN: The pause method should exit early
    base_audio_player.media_player.pause.assert_called_once()


def test_stop(base_audio_player):
    """
    Test stopping the current item
    """
    # GIVEN: A display object and a MediaPlayer instance and some mocked threads
    base_audio_player.media_player = MagicMock()

    # WHEN: stop is called
    base_audio_player.stop()

    # THEN: A thread should have been started to stop audio_player
    base_audio_player.media_player.stop.assert_called_once()


def test_media_status_changed_live_media(base_audio_player, registry):
    """
    Test the handing of QMediaPlayer event status changes for live
    """
    # GIVEN: A the lived set up
    base_audio_player.controller.media_play_item.media_type = MediaType.Dual
    base_audio_player.controller.is_live = True
    mocked_controller = MagicMock()
    registry.register("media_controller", mocked_controller)
    # WHEN: the media state changes and it is end of media
    base_audio_player.media_status_changed_event(QMediaPlayer.MediaStatus.EndOfMedia)
    # THEN: the live media status event is triggered
    mocked_controller.live_media_status_changed.emit.assert_called_once()
    mocked_controller.preview_media_status_changed.emit.assert_not_called()


def test_media_status_changed_preview_media(base_audio_player, registry):
    """
    Test the handing of QMediaPlayer event status changes for preview
    """
    # GIVEN: A the lived set up
    base_audio_player.controller.media_play_item.media_type = MediaType.Dual
    base_audio_player.controller.is_live = False
    mocked_controller = MagicMock()
    Registry().register("media_controller", mocked_controller)
    # WHEN: the media state changes and it is end of media
    base_audio_player.media_status_changed_event(QMediaPlayer.MediaStatus.EndOfMedia)
    # THEN: the live media status event is triggered
    mocked_controller.live_media_status_changed.emit.assert_not_called()
    mocked_controller.preview_media_status_changed.emit.assert_called_once()


def test_media_status_changed_video(base_audio_player, registry):
    """
    Test the handing of QMediaPlayer event status changes for Dual media
    """
    # GIVEN: A the lived set up
    base_audio_player.controller.media_play_item.media_type = MediaType.Video
    base_audio_player.controller.is_live = False
    mocked_controller = MagicMock()
    Registry().register("media_controller", mocked_controller)
    # WHEN: the media state changes and it is end of media
    base_audio_player.media_status_changed_event(QMediaPlayer.MediaStatus.EndOfMedia)
    # THEN: the live media status event is triggered
    mocked_controller.live_media_status_changed.emit.assert_not_called()
    mocked_controller.preview_media_status_changed.emit.assert_not_called()


def test_media_status_changed_not_end(base_audio_player, registry):
    """
    Test the handing of QMediaPlayer event status changes when not end of media
    """
    # GIVEN: A the lived set up
    base_audio_player.controller.media_play_item.media_type = MediaType.Dual
    base_audio_player.controller.is_live = False
    mocked_controller = MagicMock()
    Registry().register("media_controller", mocked_controller)
    # WHEN: the media state changes and it is end of media
    base_audio_player.media_status_changed_event(QMediaPlayer.MediaStatus.LoadedMedia)
    # THEN: the live media status event is triggered
    mocked_controller.live_media_status_changed.emit.assert_not_called()
    mocked_controller.preview_media_status_changed.emit.assert_not_called()


def test_position_changed_live(base_audio_player, registry):
    """
    Test the handing of QMediaPlayer when the position changes
    """
    # GIVEN: The live set up
    base_audio_player.controller.media_play_item.media_type = MediaType.Dual
    base_audio_player.controller.is_live = True
    base_audio_player.controller.media_play_item.timer = 0
    mocked_controller = MagicMock()
    Registry().register("media_controller", mocked_controller)
    # WHEN: the media position changes and it is end of media
    base_audio_player.position_changed_event(400)
    # THEN: the live position changed event is triggered
    mocked_controller.live_media_tick.emit.assert_called_once()
    mocked_controller.preview_media_tick.emit.assert_not_called()
    assert base_audio_player.controller.media_play_item.timer == 400


def test_position_changed_preview(base_audio_player, registry):
    """
    Test the handing of QMediaPlayer when the position changes Preview
    """
    # GIVEN: The live set up
    base_audio_player.controller.media_play_item.media_type = MediaType.Dual
    base_audio_player.controller.is_live = False
    base_audio_player.controller.media_play_item.timer = 0
    mocked_controller = MagicMock()
    Registry().register("media_controller", mocked_controller)
    # WHEN: the media position changes and it is end of media
    base_audio_player.position_changed_event(400)
    # THEN: the live position changed event is triggered
    mocked_controller.live_media_tick.emit.assert_not_called()
    mocked_controller.preview_media_tick.emit.assert_called_once()
    assert base_audio_player.controller.media_play_item.timer == 400


def test_position_changed_video(base_audio_player, registry):
    """
    Test the handing of QMediaPlayer when the position changes - Video
    """
    # GIVEN: The live set up
    base_audio_player.controller.media_play_item.media_type = MediaType.Video
    base_audio_player.controller.is_live = True
    base_audio_player.controller.media_play_item.timer = 0
    mocked_controller = MagicMock()
    Registry().register("media_controller", mocked_controller)
    # WHEN: the media position changes and it is end of media
    base_audio_player.position_changed_event(400)
    # THEN: the live position changed event is triggered
    mocked_controller.live_media_tick.emit.assert_not_called()
    mocked_controller.preview_media_tick.emit.assert_not_called()
    assert base_audio_player.controller.media_play_item.timer == 0
