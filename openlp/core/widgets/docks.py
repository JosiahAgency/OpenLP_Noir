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
The :mod:`~openlp.core.widgets.docks` module contains a customised base dock widget and dock widgets
"""
import logging

from PySide6 import QtCore, QtWidgets

from openlp.core.display.screens import ScreenList
from openlp.core.lib import build_icon
from openlp.core.lib.plugin import StringContent
from openlp.core.ui.style import UiThemes, get_noir_toolbox_icon, is_ui_theme


log = logging.getLogger(__name__)


class OpenLPDockWidget(QtWidgets.QDockWidget):
    """
    Custom DockWidget class to handle events
    """
    def __init__(self, parent=None, name=None, icon=None):
        """
        Initialise the DockWidget
        """
        log.debug('Initialise the %s widget' % name)
        super(OpenLPDockWidget, self).__init__(parent)
        if name:
            self.setObjectName(name)
        if icon:
            self.setWindowIcon(build_icon(icon))
        # Sort out the minimum width.
        screens = ScreenList()
        main_window_docbars = screens.current.display_geometry.width() // 5
        if main_window_docbars > 300:
            self.setMinimumWidth(300)
        else:
            self.setMinimumWidth(main_window_docbars)


class LibrarySidebar(QtWidgets.QWidget):
    """
    A modern replacement for the media manager QToolBox, used by the Noir
    theme: a slim icon rail down the left edge with one button per plugin, a
    section header with the active plugin's name, and a stacked content area.

    It implements the subset of the QToolBox API that OpenLP uses (addItem,
    removeItem, widget, count, currentIndex, setCurrentIndex, currentWidget,
    itemText, setItemText, setItemEnabled and the currentChanged signal), so
    MediaDockManager and MainWindow can drive either widget interchangeably.
    """
    currentChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buttons = []
        self._titles = []
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # Icon rail
        self.rail = QtWidgets.QWidget(self)
        self.rail.setObjectName('library_rail')
        self.rail.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.rail.setFixedWidth(52)
        self.rail_layout = QtWidgets.QVBoxLayout(self.rail)
        self.rail_layout.setContentsMargins(6, 8, 6, 8)
        self.rail_layout.setSpacing(4)
        self.rail_layout.addStretch()
        layout.addWidget(self.rail)
        # Header + content stack
        content = QtWidgets.QWidget(self)
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.header = QtWidgets.QLabel(content)
        self.header.setObjectName('library_header')
        content_layout.addWidget(self.header)
        self.stack = QtWidgets.QStackedWidget(content)
        content_layout.addWidget(self.stack, 1)
        layout.addWidget(content, 1)

    def _on_button_clicked(self, button):
        try:
            self.setCurrentIndex(self._buttons.index(button))
        except ValueError:
            pass

    def _apply_current(self, index):
        """Check the rail button and update the header for the given index"""
        for position, button in enumerate(self._buttons):
            button.setChecked(position == index)
        self.header.setText(self._titles[index] if 0 <= index < len(self._titles) else '')

    def addItem(self, widget, icon, text):
        """
        Add a plugin page with its rail button. Mirrors QToolBox.addItem().
        """
        button = QtWidgets.QToolButton(self.rail)
        button.setObjectName('library_rail_button')
        button.setIcon(icon)
        button.setIconSize(QtCore.QSize(20, 20))
        button.setFixedSize(40, 40)
        button.setCheckable(True)
        button.setToolTip(text)
        button.clicked.connect(lambda checked=False, clicked_button=button: self._on_button_clicked(clicked_button))
        self.rail_layout.insertWidget(len(self._buttons), button)
        self._buttons.append(button)
        self._titles.append(text)
        self.stack.addWidget(widget)
        index = len(self._buttons) - 1
        if index == 0:
            self._apply_current(0)
            self.currentChanged.emit(0)
        return index

    def removeItem(self, index):
        """Remove a plugin page and its rail button. Mirrors QToolBox.removeItem()."""
        if not 0 <= index < self.stack.count():
            return
        widget = self.stack.widget(index)
        self.stack.removeWidget(widget)
        button = self._buttons.pop(index)
        self._titles.pop(index)
        self.rail_layout.removeWidget(button)
        button.deleteLater()
        current = self.stack.currentIndex()
        if current != -1:
            self._apply_current(current)
            self.currentChanged.emit(current)

    def setCurrentIndex(self, index):
        if not 0 <= index < self.stack.count() or index == self.stack.currentIndex():
            self._apply_current(self.stack.currentIndex())
            return
        self.stack.setCurrentIndex(index)
        self._apply_current(index)
        self.currentChanged.emit(index)

    def count(self):
        return self.stack.count()

    def widget(self, index):
        return self.stack.widget(index)

    def currentWidget(self):
        return self.stack.currentWidget()

    def currentIndex(self):
        return self.stack.currentIndex()

    def itemText(self, index):
        return self._titles[index] if 0 <= index < len(self._titles) else ''

    def setItemText(self, index, text):
        if 0 <= index < len(self._titles):
            self._titles[index] = text
            self._buttons[index].setToolTip(text)
            if index == self.stack.currentIndex():
                self.header.setText(text)

    def setItemEnabled(self, index, enabled):
        if 0 <= index < len(self._buttons):
            self._buttons[index].setEnabled(enabled)


class MediaDockManager(object):
    """
    Provide a repository for MediaManagerItems
    """
    def __init__(self, media_dock):
        """
        Initialise the media dock
        """
        self.media_dock = media_dock

    def add_item_to_dock(self, media_item):
        """
        Add a MediaManagerItem to the dock
        If the item has been added before, it's silently skipped

        :param media_item: The item to add to the dock
        """
        visible_title = media_item.plugin.get_string(StringContent.VisibleName)
        log.debug('Inserting %s dock' % visible_title['title'])
        match = False
        for dock_index in range(self.media_dock.count()):
            if self.media_dock.widget(dock_index).settings_section == media_item.plugin.name:
                match = True
                break
        if not match:
            icon = media_item.plugin.icon
            if is_ui_theme(UiThemes.Noir) and isinstance(self.media_dock, QtWidgets.QToolBox):
                # The headroom compensation is only needed by QToolBox tabs;
                # the LibrarySidebar rail centers its icons natively
                icon = get_noir_toolbox_icon(icon)
            self.media_dock.addItem(media_item, icon, visible_title['title'])

    def remove_dock(self, media_item):
        """
        Removes a MediaManagerItem from the dock

        :param media_item: The item to add to the dock
        """
        visible_title = media_item.plugin.get_string(StringContent.VisibleName)
        log.debug('remove %s dock' % visible_title['title'])
        for dock_index in range(self.media_dock.count()):
            if self.media_dock.widget(dock_index):
                if self.media_dock.widget(dock_index).settings_section == media_item.plugin.name:
                    self.media_dock.widget(dock_index).setVisible(False)
                    self.media_dock.removeItem(dock_index)
