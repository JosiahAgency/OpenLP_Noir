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
Package to test the openlp.core.widgets.docks package.
"""
import pytest

from PySide6 import QtGui, QtWidgets

from openlp.core.widgets.docks import LibrarySidebar


@pytest.fixture()
def sidebar(settings):
    return LibrarySidebar()


def _page(title):
    widget = QtWidgets.QWidget()
    widget.setObjectName(title)
    return widget


def test_sidebar_add_item(sidebar):
    """
    Test that adding items mirrors the QToolBox behavior
    """
    # GIVEN: An empty sidebar and a listener on currentChanged
    emitted = []
    sidebar.currentChanged.connect(emitted.append)

    # WHEN: Two pages are added
    first = sidebar.addItem(_page('songs'), QtGui.QIcon(), 'Songs')
    second = sidebar.addItem(_page('bibles'), QtGui.QIcon(), 'Bibles')

    # THEN: The indexes, count, titles and current page should match, and the
    #       first addition should have announced itself
    assert (first, second) == (0, 1)
    assert sidebar.count() == 2
    assert sidebar.itemText(0) == 'Songs'
    assert sidebar.itemText(1) == 'Bibles'
    assert sidebar.currentIndex() == 0
    assert sidebar.currentWidget().objectName() == 'songs'
    assert emitted == [0]


def test_sidebar_set_current_index(sidebar):
    """
    Test that switching pages updates the stack, header and buttons
    """
    # GIVEN: A sidebar with two pages
    sidebar.addItem(_page('songs'), QtGui.QIcon(), 'Songs')
    sidebar.addItem(_page('bibles'), QtGui.QIcon(), 'Bibles')
    emitted = []
    sidebar.currentChanged.connect(emitted.append)

    # WHEN: The second page is selected, then selected again
    sidebar.setCurrentIndex(1)
    sidebar.setCurrentIndex(1)

    # THEN: The page should change once, with the header and buttons following
    assert emitted == [1]
    assert sidebar.currentIndex() == 1
    assert sidebar.header.text() == 'Bibles'
    assert sidebar._buttons[1].isChecked() is True
    assert sidebar._buttons[0].isChecked() is False


def test_sidebar_remove_item(sidebar):
    """
    Test that removing a page keeps the sidebar consistent
    """
    # GIVEN: A sidebar with two pages, the second one current
    sidebar.addItem(_page('songs'), QtGui.QIcon(), 'Songs')
    sidebar.addItem(_page('bibles'), QtGui.QIcon(), 'Bibles')
    sidebar.setCurrentIndex(1)

    # WHEN: The first page is removed
    sidebar.removeItem(0)

    # THEN: One page should remain, current and title tracking should survive
    assert sidebar.count() == 1
    assert sidebar.itemText(0) == 'Bibles'
    assert sidebar.currentIndex() == 0
    assert sidebar.currentWidget().objectName() == 'bibles'
    assert sidebar.header.text() == 'Bibles'


def test_sidebar_item_enabled_and_text(sidebar):
    """
    Test the item enabled toggle and title updates used by the service manager
    """
    # GIVEN: A sidebar with one page
    sidebar.addItem(_page('custom'), QtGui.QIcon(), 'Custom Slides')

    # WHEN: The item is disabled and renamed
    sidebar.setItemEnabled(0, False)
    sidebar.setItemText(0, 'Custom')

    # THEN: The button and titles should follow
    assert sidebar._buttons[0].isEnabled() is False
    assert sidebar.itemText(0) == 'Custom'
    assert sidebar.header.text() == 'Custom'
