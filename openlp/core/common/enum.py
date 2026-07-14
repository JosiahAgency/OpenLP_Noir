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
The :mod:`enumm` module provides enumm functions.
"""
from enum import IntEnum, unique


@unique
class AlertLocation(IntEnum):
    """
    This is an enumeration class which controls where Alerts are placed on the screen.

    ``Top``
        Place the text at the top of the screen.

    ``Middle``
        Place the text in the middle of the screen.

    ``Bottom``
        Place the text at the bottom of the screen.
    """
    Top = 0
    Middle = 1
    Bottom = 2


@unique
class BibleSearch(IntEnum):
    """
    Enumeration class for the different search types for the "Search" tab.
    """
    Reference = 1
    Text = 2
    Combined = 3


@unique
class CustomSearch(IntEnum):
    """
    An enumeration for custom search methods.
    """
    Titles = 1
    Themes = 2


@unique
class DisplayStyle(IntEnum):
    """
    An enumeration for bible text bracket display styles.
    """
    NoBrackets = 0
    Round = 1
    Curly = 2
    Square = 3


@unique
class EGWSearch(IntEnum):
    """
    An enumeration for the EGW Library search methods.
    """
    Smart = 1
    Reference = 2
    Text = 3


@unique
class ImageThemeMode(IntEnum):
    """
    An enumeration for image background settings.
    """
    Black = 1
    CustomTheme = 2


@unique
class LayoutStyle(IntEnum):
    """
    An enumeration for bible screen layout styles.
    """
    VersePerSlide = 0
    VersePerLine = 1
    Continuous = 2
    WholeVerseContinuous = 3


@unique
class LanguageSelection(IntEnum):
    """
    An enumeration for bible bookname language. And standard strings for use throughout the bibles plugin.
    """
    Bible = 0
    Application = 1
    English = 2


@unique
class ServiceItemType(IntEnum):
    """
    Defines the type of service item
    """
    Text = 1
    Image = 2
    Command = 3

    @staticmethod
    def parse(value):
        if value in [1, '1', 'Text', 'ServiceItemType.Text']:
            return ServiceItemType.Text
        elif value in [2, '2', 'Image', 'ServiceItemType.Image']:
            return ServiceItemType.Image
        elif value in [3, '3', 'Command', 'ServiceItemType.Command']:
            return ServiceItemType.Command


@unique
class PluginStatus(IntEnum):
    """
    Defines the status of the plugin
    """
    Active = 1
    Inactive = 0
    Disabled = -1


@unique
class SongSearch(IntEnum):
    """
    An enumeration for song search methods.
    """
    Entire = 1
    Titles = 2
    Lyrics = 3
    Authors = 4
    Topics = 5
    Books = 6
    Themes = 7
    Copyright = 8
    CCLInumber = 9


@unique
class SongFirstSlideMode(IntEnum):
    """
    An enumeration for song first slide types.
    """
    Default = 0  # No cover
    Songbook = 1
    Footer = 2


@unique
class HiDPIMode(IntEnum):
    Default = 0,
    # Legacy HiDPI mode is the default Qt behavior, without any OpenLP-specific HiDPI modifications
    Legacy = 1,
    # (Windows only) Make the OpenLP run unaware of any screen scaling.
    Windows_Unaware = 2
