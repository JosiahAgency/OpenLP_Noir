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
The :mod:`~openlp.core.common.platform` module contains functions related to the platform that
OpenLP is currently running on.
"""
import os
import sys

try:
    from distro import id as distro_id
except ImportError:
    # The distro module is only valid for Linux, so if it doesn't exist, create a function that always
    # returns False
    def distro_id():
        return False


def is_win():
    """
    Returns true if running on a system with a nt kernel e.g. Windows, Wine

    :return: True if system is running a nt kernel false otherwise
    """
    return os.name.startswith('nt')


def is_macosx():
    """
    Returns true if running on a system with a darwin kernel e.g. Mac OS X

    :return: True if system is running a darwin kernel false otherwise
    """
    return sys.platform.startswith('darwin')


def is_linux(distro=None):
    """
    Returns true if running on a system with a linux kernel e.g. Ubuntu, Debian, etc

    :param distro: If not None, check if running that Linux distro
    :return: True if system is running a linux kernel false otherwise
    """
    result = sys.platform.startswith('linux')
    if result and distro:
        result = result and distro == distro_id()
    return result


def is_64bit_instance():
    """
    Returns true if the python/OpenLP instance running is 64 bit. If running a 32 bit instance on
    a 64 bit system this will return false.

    :return: True if the python/OpenLP instance running is 64 bit, otherwise False.
    """
    return (sys.maxsize > 2**32)


__IS_WAYLAND_COMPOSITOR = None


def is_wayland_compositor():
    """
    Returns true if the OpenLP/Qt instance is running in a Wayland compositor.
    NOTE: This checks is only about compositor. Returns True if the application is running in a Wayland compositor.
    Will also return True if application is running on X11/X.org mode in a Wayland compositor/desktop environment

    :return: True if the OpenLP/Qt instance is running in a Wayland compositor, otherwise False
    """
    global __IS_WAYLAND_COMPOSITOR
    if __IS_WAYLAND_COMPOSITOR is None:
        __IS_WAYLAND_COMPOSITOR = bool(os.getenv('WAYLAND_DISPLAY', False))
    return __IS_WAYLAND_COMPOSITOR
