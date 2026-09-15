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
This module contains tests for the manager submodule of the Bibles plugin.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

from openlp.plugins.bibles.lib.manager import BibleManager


def test_delete_bible_by_file_path(settings):
    """
    Test the BibleManager delete_bible method
    """
    # GIVEN: An instance of BibleManager and a mocked bible
    with patch.object(BibleManager, 'reload_bibles'), \
            patch('openlp.plugins.bibles.lib.manager.delete_file', return_value=True) as mocked_delete_file:
        instance = BibleManager(MagicMock())
        mocked_bible = MagicMock(file_path='KJV.sqlite', path=Path('bibles'))
        instance.db_cache = {'KJV': mocked_bible}

        # WHEN: Calling delete_bible with 'KJV'
        result = instance.delete_bible('KJV')

        # THEN: The bible's connection should have been closed, the bible file deleted, and the result of the
        #       deletion returned.
        assert result is True
        mocked_bible.close.assert_called_once_with()
        mocked_delete_file.assert_called_once_with(Path('bibles') / 'KJV.sqlite')


def test_delete_bible_by_name(settings):
    """
    Test the BibleManager delete_bible method
    """
    # GIVEN: An instance of BibleManager and a mocked bible
    with patch.object(BibleManager, 'reload_bibles'), \
            patch('openlp.plugins.bibles.lib.manager.delete_file', return_value=True) as mocked_delete_file:
        instance = BibleManager(MagicMock())
        mocked_bible = MagicMock(file_path=None, path=Path('bibles'))
        mocked_bible.name = 'KJV'
        instance.db_cache = {'KJV': mocked_bible}

        # WHEN: Calling delete_bible with 'KJV'
        result = instance.delete_bible('KJV')

        # THEN: The bible's connection should have been closed, the bible file deleted, and the result of the
        #       deletion returned.
        assert result is True
        mocked_bible.close.assert_called_once_with()
        mocked_delete_file.assert_called_once_with(Path('bibles') / 'KJV.sqlite')
