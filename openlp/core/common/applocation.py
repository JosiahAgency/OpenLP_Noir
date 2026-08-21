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
The :mod:`openlp.core.common.applocation` module provides an utility for OpenLP receiving the data path etc.
"""
import logging
import os
import sys
from pathlib import Path

from platformdirs import PlatformDirs

import openlp
from openlp.core.common import get_frozen_path
from openlp.core.common.path import create_paths, resolve
from openlp.core.common.platform import is_macosx, is_win
from openlp.core.common.registry import Registry


log = logging.getLogger(__name__)

FROZEN_APP_PATH = Path(sys.argv[0]).parent
APP_PATH = Path(openlp.__file__).parent


def _get_frozen_plugins_path():
    """
    Return the plugin directory for frozen builds, accounting for macOS app bundles and
    PyInstaller onedir layouts.
    """
    candidates = [FROZEN_APP_PATH / 'plugins']
    if is_macosx():
        candidates.append(FROZEN_APP_PATH.parent / 'Resources' / 'openlp' / 'plugins')
    candidates.append(FROZEN_APP_PATH / '_internal' / 'openlp' / 'plugins')
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidates.append(Path(meipass) / 'openlp' / 'plugins')
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


class AppLocation(object):
    """
    The :class:`AppLocation` class is a static class which retrieves a directory based on the directory type.
    """
    AppDir = 1
    DataDir = 2
    PluginsDir = 3
    VersionDir = 4
    CacheDir = 5
    LanguageDir = 6

    @staticmethod
    def get_directory(dir_type=AppDir):
        """
        Return the appropriate directory according to the directory type.

        :param dir_type: The directory type you want, for instance the data directory. Default *AppLocation.AppDir*
        :return: The requested path
        :rtype: Path
        """
        if dir_type == AppLocation.AppDir or dir_type == AppLocation.VersionDir:
            path = get_frozen_path(FROZEN_APP_PATH, APP_PATH)
        elif dir_type == AppLocation.PluginsDir:
            if getattr(sys, 'frozen', False) == 1:
                path = _get_frozen_plugins_path()
            else:
                path = APP_PATH / 'plugins'
        elif dir_type == AppLocation.LanguageDir:
            path = get_frozen_path(FROZEN_APP_PATH, _get_os_dir_path(dir_type)) / 'i18n'
        else:
            path = _get_os_dir_path(dir_type)
        return resolve(path)

    @staticmethod
    def get_data_path():
        """
        Return the path OpenLP stores all its data under.

        :return: The data path to use.
        :rtype: Path
        """
        # Check if we have a different data location.
        if Registry().get('settings').contains('advanced/data path'):
            path = Path(Registry().get('settings').value('advanced/data path'))
        else:
            path = AppLocation.get_directory(AppLocation.DataDir)
            create_paths(path)
        return path

    @staticmethod
    def get_files(section=None, extension=''):
        """
        Get a list of files from the data files path.

        :param None | str section: Defaults to *None*. The section of code getting the files - used to load from a
        section's data subdirectory.
        :param str extension: Defaults to ''. The extension to search for. For example::
            '.png'
        :return: List of files found.
        :rtype: list[Path]
        """
        path = AppLocation.get_data_path()
        if section:
            path = path / section
        try:
            file_paths = path.glob('*' + extension)
            return [file_path.relative_to(path) for file_path in file_paths]
        except OSError:
            return []

    @staticmethod
    def get_section_data_path(section):
        """
        Return the path a particular module stores its data under.

        :param str section:
        :rtype: Path
        """
        path = AppLocation.get_data_path() / section
        create_paths(path)
        return path


def _get_os_dir_path(dir_type):
    """
    Return a path based on which OS and environment we are running in.

    :param dir_type: AppLocation Enum of the requested path type
    :return: The requested path
    :rtype: Path
    """
    # If running from source, return the language directory from the source directory
    if dir_type == AppLocation.LanguageDir:
        directory = resolve(Path(openlp.__file__, '..', '..')) / 'resources'
        if directory.exists():
            return directory
    if is_win():
        openlp_folder_path = Path(os.getenv('APPDATA'), 'openlp')
        if dir_type == AppLocation.DataDir:
            return openlp_folder_path / 'data'
        elif dir_type == AppLocation.LanguageDir:
            return Path(openlp.__file__).parent
        return openlp_folder_path

    dirs = PlatformDirs('openlp', multipath=True)
    if is_macosx():
        openlp_folder_path = Path(dirs.user_data_dir)
        if dir_type == AppLocation.DataDir:
            return openlp_folder_path / 'Data'
        elif dir_type == AppLocation.LanguageDir:
            return Path(openlp.__file__).parent
        return openlp_folder_path
    else:
        if dir_type == AppLocation.LanguageDir:
            site_dirs = dirs.site_data_dir.split(os.pathsep)
            for site_dir in site_dirs:
                if 'share/openlp' not in site_dir:
                    continue
                directory = Path(site_dir)
                if (directory / 'i18n').exists():
                    return directory
            return Path(site_dirs[0])
        if dir_type == AppLocation.DataDir:
            return Path(dirs.user_data_dir)
        elif dir_type == AppLocation.CacheDir:
            return Path(dirs.user_cache_dir)
        if dir_type == AppLocation.DataDir:
            return Path(os.getenv('HOME'), '.openlp', 'data')
        return Path(os.getenv('HOME'), '.openlp')
