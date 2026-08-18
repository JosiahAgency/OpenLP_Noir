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
import json


def assert_length(expected, iterable, msg=None):
    if len(iterable) != expected:
        if not msg:
            msg = 'Expected length {expected}, ~got {got}'.format(expected=expected, got=len(iterable))
        raise AssertionError(msg)


def convert_file_service_item(test_path, name, row=0):
    service_file = test_path / name
    with service_file.open() as open_file:
        try:
            items = json.load(open_file)
            first_line = items[row]
        except OSError:
            first_line = ''
    return first_line


def load_external_result_data(file_path):
    """
    A method to load and return an object containing the song data from an external file.

    :param pathlib.Path file_path: The path of the file to load
    """
    return json.loads(file_path.read_bytes().decode())
