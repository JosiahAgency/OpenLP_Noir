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
Package to test the openlp.core.ui package.
"""
from unittest.mock import MagicMock, patch
from PySide6 import QtCore, QtGui

from openlp.core.ui.splashscreen import SplashScreen
from openlp.core.ui.style import NOIR_INK_0


def test_splashscreen(mock_settings: MagicMock):
    """
    Test that the SpashScreen is created correctly
    """
    # GIVEN: the SplashScreen class
    # WHEN: An object is created

    ss = SplashScreen()
    # THEN: Nothing should go wrong and the instance should have the correct values
    assert ss.objectName() == 'splashScreen', 'The ObjectName should have be ' \
        'splashScreen'
    assert ss.frameSize() == QtCore.QSize(370, 370), 'The frameSize should be (370, 370)'
    assert ss.contextMenuPolicy() == QtCore.Qt.ContextMenuPolicy.PreventContextMenu, 'The ContextMenuPolicy ' \
        'should have been QtCore.Qt.ContextMenuPolicy.PreventContextMenu or 4'


@patch('openlp.core.ui.splashscreen.is_ui_theme', return_value=True)
def test_splashscreen_noir_background(mocked_is_ui_theme, mock_settings: MagicMock):
    """
    Test that the Noir theme bakes a dark ink background into the splash pixmap
    """
    # WHEN: A SplashScreen is created with the Noir theme active
    ss = SplashScreen()

    # THEN: A corner of the pixmap should be the Noir ink background, not transparent
    corner_color = ss.pixmap().toImage().pixelColor(0, 0)
    assert corner_color == QtGui.QColor(NOIR_INK_0)


@patch('openlp.core.ui.splashscreen.is_ui_theme', return_value=False)
def test_splashscreen_legacy_background_unchanged(mocked_is_ui_theme, mock_settings: MagicMock):
    """
    Test that non-Noir themes keep today's pixmap untouched (no ink background baked in)
    """
    # WHEN: A SplashScreen is created with a non-Noir theme active
    ss = SplashScreen()

    # THEN: The corner of the pixmap should not be the Noir ink background
    corner_color = ss.pixmap().toImage().pixelColor(0, 0)
    assert corner_color != QtGui.QColor(NOIR_INK_0)
