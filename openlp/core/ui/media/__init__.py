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
The :mod:`~openlp.core.ui.media` module contains classes and objects for media player integration.
"""
import logging

from PySide6.QtMultimedia import QMediaFormat

from openlp.core.common.registry import Registry

log = logging.getLogger(__name__ + '.__init__')


def get_supported_media_suffix() -> tuple[list, list]:
    """
    Provide a list of suffixes the Media input dialog to use for selection
    """
    a_suffixes = ['']
    v_suffixes = ['']
    for f in QMediaFormat().supportedFileFormats(QMediaFormat.Decode):
        mime_type = QMediaFormat(f).mimeType()
        if 'video' in mime_type.name():
            v_suffixes += [f'*.{s}' for s in mime_type.suffixes()]
        else:
            a_suffixes += [f'*.{s}' for s in mime_type.suffixes()]
    return a_suffixes, v_suffixes


class MediaState(object):
    """
    An enumeration for possible States of the Media Player
    """
    Off = 0
    Loaded = 1
    Playing = 2
    Paused = 3
    Stopped = 4


class MediaType(object):
    """
    An enumeration of possible Media Types
    """
    Unused = 0
    Audio = 1
    Video = 2
    Dual = 3
    DeviceStream = 4
    NetworkStream = 5


class MediaPlayItem(object):
    """
    This class hold the media related info
    """
    external_stream = []  # for remote things like USB Cameras
    audio_file = None  # for song Audio files when we have background videos
    media_file = None  # for standalone media
    is_background = False
    is_theme_background = False
    length = 0
    start_time = 0
    end_time = 0
    is_playing = MediaState.Off
    timer = 1000
    media_type = MediaType.Unused
    media_autostart = False
    audio_autostart = False
    request_play = False  # On Load do I reun play


def media_state() -> int:
    """
    Evaluates and returns the current start of live media
    return: Returns the current live Media Media State
    """
    live = Registry().get('live_controller')
    if live.media_play_item.is_theme_background and \
            live.media_play_item.media_type is not MediaType.Dual:
        return MediaState.Off
    else:
        return live.media_play_item.is_playing


def get_volume(controller) -> int:
    """
    The volume needs to be retrieved

    :param controller: the controller in use
    :return: Are we looping
    """
    if controller.is_live:
        return Registry().get('settings').value('media/live volume')
    else:
        return Registry().get('settings').value('media/preview volume')


def save_volume(controller, volume: int) -> None:
    """
    The volume needs to be saved

    :param controller: the controller in use
    :param volume: The volume to use and save
    :return: Are we looping
    """
    if controller.is_live:
        return Registry().get('settings').setValue('media/live volume', volume)
    else:
        return Registry().get('settings').setValue('media/preview volume', volume)


def saved_looping_playback(controller) -> bool:
    """
    :param controller: the controller in use
    :return: Are we looping
    """
    if controller.is_live:
        return Registry().get('settings').value('media/live loop')
    else:
        return Registry().get('settings').value('media/preview loop')


def toggle_looping_playback(controller) -> None:
    """

    :param controller: the controller in use
    :return: None
    """
    if controller.is_live:
        Registry().get('settings').setValue('media/live loop', not Registry().get('settings').value('media/live loop'))
    else:
        Registry().get('settings').setValue('media/preview loop',
                                            not Registry().get('settings').value('media/preview loop'))


def parse_stream_path(input_string):
    """
    Split the device stream path info.

    :param input_string: The string to parse
    :return: The elements extracted from the string:  type, streamname, MRL, options
    """
    log.debug('parse_stream_path, about to parse: "{text}"'.format(text=input_string))
    # identify header: 'devicestream:' or 'networkstream:'
    type_str, data = input_string.split(':', 1)
    if type_str == 'devicestream':
        stream_type = MediaType.DeviceStream
    else:
        stream_type = MediaType.NetworkStream
    # split at '&&'
    stream_info = data.split('&&')
    name = stream_info[0]
    mrl = stream_info[1]
    options = stream_info[2]
    return stream_type, name, mrl, options


def format_milliseconds(milliseconds):
    """
    Format milliseconds into a human readable time string.
    :param milliseconds: Milliseconds to format
    :return: Time string in format: hh:mm:ss,ttt
    """
    milliseconds = int(milliseconds)
    seconds, millis = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def format_play_time(milliseconds):
    """
    Format milliseconds into a human readable time string.
    :param milliseconds: Milliseconds to format
    :return: Time string in format: hh:mm:ss,ttt
    """
    milliseconds = int(milliseconds)
    seconds, _ = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_play_seconds(seconds: float) -> str:
    """

    """
    secs, psec = divmod(seconds, 10)
    return f"{secs:01d}.{psec:01d}"


media_empty_song = [{"title": "", "text": "", "verse": 0, "footer": ""}]
