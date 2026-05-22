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
The :mod:`~openlp.core.ui.media.audioplayer` module for secondary background audio.
"""
import logging

from openlp.core.common.mixins import LogMixin
from openlp.core.common.registry import Registry
from openlp.core.display.window import DisplayWindow
from openlp.core.ui.slidecontroller import SlideController
from openlp.core.ui.media import MediaType
from openlp.core.ui.media.mediabase import MediaBase

from PySide6.QtMultimedia import QMediaDevices, QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl

log = logging.getLogger(__name__)


class AudioPlayer(MediaBase, LogMixin):
    """
    A specialised version of the MediaPlayer class, which provides an audio player for media when the main media class
    is also in use.
    """

    def __init__(self, parent=None):
        """
        Constructor
        """
        super(AudioPlayer, self).__init__(parent, "qt6")
        self.parent = parent

    def setup(self, controller: SlideController, display: DisplayWindow) -> None:
        """
        Set up an audio player and bind it to a controller and display

        :param controller: The controller where the media is
        :param display: The display where the media is.
        :return:
        """

        self.media_player = QMediaPlayer(None)
        self.audio_output = QAudioOutput()
        if controller.is_live:
            audio_out_set = self.settings.value('media/live audio out')
        else:
            audio_out_set = self.settings.value('media/preview audio out')
        if audio_out_set:
            for au_dev in QMediaDevices().audioOutputs():
                if audio_out_set == au_dev.description():
                    self.audio_output.setDevice(au_dev)
                    break
        self.media_player.setAudioOutput(self.audio_output)
        self.controller = controller
        self.display = display
        self.media_player.positionChanged.connect(self.position_changed_event)
        self.media_player.mediaStatusChanged.connect(self.media_status_changed_event)

    def position_changed_event(self, position) -> None:
        """
        Media callback for position changed event.  Saves position and calls UI updates.
        :param event: The media position has changed
        :return: None
        """
        if self.controller.media_play_item.media_type != MediaType.Dual:
            return
        self.controller.media_play_item.timer = position
        if self.controller.is_live:
            Registry().get("media_controller").live_media_tick.emit()
        else:
            Registry().get("media_controller").preview_media_tick.emit()

    def media_status_changed_event(self, event):
        """
        Handle the end of Media event and update UI
        """
        if self.controller.media_play_item.media_type != MediaType.Dual:
            return
        if event == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.controller.is_live:
                Registry().get("media_controller").live_media_status_changed.emit()
            else:
                Registry().get("media_controller").preview_media_status_changed.emit()

    def load(self) -> bool:
        """
        Load a audio file into the player

        :param controller: The controller where the media is
        :param output_display: The display where the media is
        :return:  Success or Failure
        """
        self.log_debug("load audio in Audio Player")
        # The media player moved here to clear the playlist between uses.
        if self.controller.media_play_item.audio_file:
            self.media_player.setSource(QUrl.fromLocalFile(str(self.controller.media_play_item.audio_file)))
            return True
        return False

    def play(self) -> None:
        """
        Play the current loaded audio item
        :return:
        """
        self.media_player.play()

    def pause(self) -> None:
        """
        Pause the current item

        :param controller: The controller which is managing the display
        :return:
        """
        self.media_player.pause()

    def stop(self) -> None:
        """
        Stop the current item

        :param controller: The controller where the media is
        :return:
        """
        self.media_player.stop()
