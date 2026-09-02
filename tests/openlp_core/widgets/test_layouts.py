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
Package to test the openlp.core.widgets.layouts module.
"""
from unittest.mock import MagicMock

from PySide6 import QtCore

from openlp.core.widgets.layouts import AspectRatioLayout


def test_set_geometry_applies_widget_geometry(settings):
    """
    Test that setGeometry() computes and applies a sane geometry to the child widget in the normal case
    """
    # GIVEN: An AspectRatioLayout with a mocked child widget
    layout = AspectRatioLayout(aspect_ratio=16.0 / 9.0)
    mocked_widget = MagicMock()
    mocked_item = MagicMock()
    mocked_item.widget.return_value = mocked_widget
    mocked_item.alignment.return_value = QtCore.Qt.AlignmentFlag.AlignCenter
    layout.addItem(mocked_item)

    # WHEN: setGeometry() is called with a normal, positive-size rect
    layout.setGeometry(QtCore.QRect(0, 0, 1920, 1080))

    # THEN: the child widget's geometry should have been set
    mocked_widget.setGeometry.assert_called_once()


def test_set_geometry_ignores_zero_size_rect(settings):
    """
    Test that setGeometry() does NOT touch the child widget when the available space collapses to zero.

    Regression test: during a transient layout pass (e.g. a media manager dock/tab switch briefly
    collapsing the panel that hosts the display preview), the incoming rect can have a zero (or negative)
    width/height. Previously this produced a zero/negative-size geometry that was applied directly to the
    child widget (a DisplayWindow wrapping a QWebEngineView), which has been linked to an intermittent
    native access violation in Qt's compositor (Qt6Gui.dll) on Windows.
    """
    # GIVEN: An AspectRatioLayout with a mocked child widget
    layout = AspectRatioLayout(aspect_ratio=16.0 / 9.0)
    mocked_widget = MagicMock()
    mocked_item = MagicMock()
    mocked_item.widget.return_value = mocked_widget
    mocked_item.alignment.return_value = QtCore.Qt.AlignmentFlag.AlignCenter
    layout.addItem(mocked_item)

    # WHEN: setGeometry() is called with a rect that has collapsed to zero size
    layout.setGeometry(QtCore.QRect(0, 0, 0, 0))

    # THEN: the child widget's geometry should NOT have been touched
    mocked_widget.setGeometry.assert_not_called()


def test_set_geometry_ignores_negative_size_rect(settings):
    """
    Test that setGeometry() does NOT touch the child widget when the available space is negative.
    """
    # GIVEN: An AspectRatioLayout with a mocked child widget and a non-zero margin
    layout = AspectRatioLayout(aspect_ratio=16.0 / 9.0)
    layout.margin = 10
    mocked_widget = MagicMock()
    mocked_item = MagicMock()
    mocked_item.widget.return_value = mocked_widget
    mocked_item.alignment.return_value = QtCore.Qt.AlignmentFlag.AlignCenter
    layout.addItem(mocked_item)

    # WHEN: setGeometry() is called with a rect smaller than the margins, so available space is negative
    layout.setGeometry(QtCore.QRect(0, 0, 5, 5))

    # THEN: the child widget's geometry should NOT have been touched
    mocked_widget.setGeometry.assert_not_called()
