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
The :mod:`~openlp.core.ui.media.mediaplayer` module for media playing.
"""
import logging
import os
import re
import sys
import sysconfig
from pathlib import Path

from PySide6 import QtCore, QtWidgets
from PySide6.QtMultimedia import QAudioInput, QAudioOutput, QCamera, QMediaDevices, QMediaCaptureSession, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import QUrl

from openlp.core.common.mixins import LogMixin
from openlp.core.common.platform import is_win
from openlp.core.common.registry import Registry
from openlp.core.display.window import DisplayWindow
from openlp.core.ui.slidecontroller import SlideController
from openlp.core.ui.media.mediabase import MediaBase
from openlp.core.ui.media import MediaType

log = logging.getLogger(__name__)

# A workaround for https://bugreports.qt.io/browse/PYSIDE-2935. In a frozen
# (PyInstaller) build there is no site-packages directory — the Qt DLLs sit
# next to the executable, which is already on the DLL search path.
if is_win() and not getattr(sys, 'frozen', False):
    pyside_dir = Path(sysconfig.get_path('purelib')) / 'PySide6'
    if pyside_dir.is_dir():
        os.add_dll_directory(str(pyside_dir))


class MediaPlayer(MediaBase, LogMixin):
    """
    A specialised version of the MediaPlayer class, which provides an media player for media when the main media class
    is also in use.
    """

    def __init__(self, parent=None):
        """
        Constructor
        """
        super(MediaPlayer, self).__init__(parent, "qt6")
        self.parent = parent

    def setup(self, controller: SlideController, display: DisplayWindow) -> None:
        """
        Set up an media and audio player and bind it to a controller and display

        :param controller: The controller where the media is
        :param display: The display where the media is.
        :return:
        """
        if controller.is_live:
            controller.media_widget = QtWidgets.QWidget(controller)
            controller.media_widget.setWindowFlags(
                QtCore.Qt.WindowType.FramelessWindowHint
                | QtCore.Qt.WindowType.Tool
                | QtCore.Qt.WindowType.WindowStaysOnTopHint)
            controller.media_widget.setAttribute(QtCore.Qt.WidgetAttribute.WA_X11NetWmWindowTypeDialog)
        else:
            controller.media_widget = QtWidgets.QWidget(display)
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
        self.video_widget = QVideoWidget()
        layout = QtWidgets.QVBoxLayout(controller.media_widget)
        layout.addWidget(self.video_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.controller = controller
        self.display = display
        self.media_player.positionChanged.connect(self.position_changed_event)
        self.media_player.mediaStatusChanged.connect(self.media_status_changed_event)
        # device stream objects. setVideoOutput is called when loading stream, video_widget can't be used by both
        # QMediaCaptureSession and QMediaPlayer
        self.media_capture_session = QMediaCaptureSession()
        self.media_capture_session.setAudioOutput(self.audio_output)
        self.device_video_input = None
        self.device_audio_input = None
        self.set_visible(False)  # Hide player till needed

    def media_status_changed_event(self, event):
        """
        Handle the end of Media event and update UI
        """
        if self.controller.media_play_item.media_type == MediaType.Dual:
            return
        if event == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.controller.is_live:
                Registry().get("media_controller").live_media_status_changed.emit()
            else:
                Registry().get("media_controller").preview_media_status_changed.emit()
        if event == QMediaPlayer.MediaStatus.LoadedMedia:
            if self.controller.is_live:
                Registry().get("media_controller").live_media_loaded.emit()
            else:
                Registry().get("media_controller").preview_media_loaded.emit()

    def position_changed_event(self, position) -> None:
        """
        Media callback for position changed event.  Saves position and calls UI updates.
        :param event: The media position has changed
        :return: None
        """
        if self.controller.media_play_item.media_type == MediaType.Dual:
            return
        self.controller.media_play_item.timer = position
        if self.controller.is_live:
            Registry().get("media_controller").live_media_tick.emit()
        else:
            Registry().get("media_controller").preview_media_tick.emit()

    def toggle_loop(self, loop_required: bool) -> None:
        """
        Switch the loop toggle setting

        :param loop_required: Do I need to loop
        """
        if loop_required:
            self.media_player.setLoops(QMediaPlayer.Loops.Infinite)
        else:
            self.media_player.setLoops(QMediaPlayer.Loops.Once)

    def load(self) -> bool:
        """
        Load a media file into the player

        :return:  Success or Failure
        """
        self.log_debug("load external media stream in Media Player")
        if self.controller.media_play_item.media_file:
            self.media_capture_session.setVideoOutput(None)
            self.media_player.setAudioOutput(self.audio_output)
            self.media_player.setVideoOutput(self.video_widget)
            self.media_player.setSource(QUrl.fromLocalFile(str(self.controller.media_play_item.media_file)))
            return True
        return False

    def load_stream(self) -> bool:
        """
        Load a media stream into the player
        :return:  Success or Failure
        """
        self.log_debug("load stream  in Media Player")

        if self.controller.media_play_item.external_stream:
            mrl = self.controller.media_play_item.external_stream[0]
            if self.controller.media_play_item.media_type == MediaType.DeviceStream:
                self.media_player.setVideoOutput(None)
                self.media_capture_session.setVideoOutput(self.video_widget)
                vdev_name = re.search(r'qt6video=(.+);', mrl)
                self.device_video_input = None
                if vdev_name:
                    for vdev in QMediaDevices.videoInputs():
                        if vdev.description() == vdev_name.group(1):
                            self.device_video_input = QCamera(vdev)
                            self.media_capture_session.setCamera(self.device_video_input)
                            break
                adev_name = re.search(r'qt6audio=(.+)', mrl)
                self.device_audio_input = None
                if adev_name:
                    for adev in QMediaDevices.audioInputs():
                        if adev.description() == adev_name.group(1):
                            self.device_audio_input = QAudioInput()
                            self.device_audio_input.setDevice(adev)
                            self.device_audio_input.setMuted(True)
                            self.media_capture_session.setAudioInput(self.device_audio_input)
                            break
                return True
            elif self.controller.media_play_item.media_type == MediaType.NetworkStream:
                self.media_capture_session.setVideoOutput(None)
                self.media_player.setVideoOutput(self.video_widget)
                self.media_player.setSource(QUrl(mrl))
                return True
        return False

    def play(self) -> None:
        """
        Play the current loaded audio item
        :return:
        """
        if self.controller.media_play_item.media_type == MediaType.DeviceStream:
            if self.device_video_input:
                self.device_video_input.start()
            if self.device_audio_input:
                self.device_audio_input.setMuted(False)
        else:
            self.media_player.play()
        # TODO handle variable start times for first play

    def pause(self) -> None:
        """
        Pause the current item

        :param controller: The controller which is managing the display
        :return:
        """
        if self.controller.media_play_item.media_type == MediaType.DeviceStream:
            if self.device_video_input:
                self.device_video_input.stop()
            if self.device_audio_input:
                self.device_audio_input.setMuted(True)
        else:
            self.media_player.pause()

    def stop(self) -> None:
        """
        Stop the current item

        :param controller: The controller where the media is
        :return:
        """
        if self.controller.media_play_item.media_type == MediaType.DeviceStream:
            if self.device_video_input:
                self.device_video_input.stop()
            if self.device_audio_input:
                self.device_audio_input.setMuted(True)
        else:
            self.media_player.stop()

    def duration(self) -> int:
        """
        Obtain the duration of the playing
        """
        return self.media_player.duration()
