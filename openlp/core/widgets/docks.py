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

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.display.screens import ScreenList
from openlp.core.lib import build_icon
from openlp.core.lib.plugin import StringContent
from openlp.core.ui.style import NOIR_CUE, UiThemes, get_noir_toolbox_icon, is_ui_theme


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

    def setWindowTitle(self, title):
        """
        The Noir theme renders dock titles as uppercase panel labels. The View
        menu keeps its own action text, so only the title bar is affected.
        """
        if is_ui_theme(UiThemes.Noir):
            title = title.upper()
        super().setWindowTitle(title)


class LibraryRail(QtWidgets.QWidget):
    """
    The icon rail of the LibrarySidebar. On top of the stylesheet background
    it paints a small cue-colored bar on the rail edge beside the active
    section's button — a "you are here" marker that reads at a glance, distinct
    from the pressed/checked fill of the button itself.
    """
    INDICATOR_WIDTH = 3
    INDICATOR_HEIGHT = 18

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_button = None

    def set_active_button(self, button):
        """Move the active-section indicator beside the given button"""
        self._active_button = button
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._active_button:
            return
        painter = QtGui.QPainter(self)
        # The painter must always be ended before this method returns: an active painter left on the widget
        # corrupts the backing store and crashes a later, unrelated repaint (see ListWidgetWithDnD.paintEvent
        # in widgets/views.py). self._active_button.geometry() can also raise RuntimeError if the button was
        # deleted out from under us, which the try/finally covers too.
        try:
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            center_y = self._active_button.geometry().center().y()
            bar = QtCore.QRectF(0, center_y - self.INDICATOR_HEIGHT / 2,
                                self.INDICATOR_WIDTH, self.INDICATOR_HEIGHT)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(NOIR_CUE))
            painter.drawRoundedRect(bar, self.INDICATOR_WIDTH / 2, self.INDICATOR_WIDTH / 2)
        finally:
            painter.end()


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
        self._fade_animation = None
        self._fade_widget = None
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # Icon rail
        self.rail = LibraryRail(self)
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
        self.rail.set_active_button(self._buttons[index] if 0 <= index < len(self._buttons) else None)

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
        if widget is self._fade_widget:
            self._clear_fade()
        self.stack.removeWidget(widget)
        button = self._buttons.pop(index)
        self._titles.pop(index)
        self.rail_layout.removeWidget(button)
        button.deleteLater()
        current = self.stack.currentIndex()
        if current != -1:
            self._apply_current(current)
            self.currentChanged.emit(current)
        else:
            # The last page went away: drop the dangling indicator reference
            # before the deleted button is painted
            self.header.setText('')
            self.rail.set_active_button(None)

    def setCurrentIndex(self, index):
        if not 0 <= index < self.stack.count() or index == self.stack.currentIndex():
            self._apply_current(self.stack.currentIndex())
            return
        self.stack.setCurrentIndex(index)
        self._fade_in_current()
        self._apply_current(index)
        self.currentChanged.emit(index)

    def _fade_in_current(self):
        """
        Fade the newly shown section in over ~120ms. Feedback, not decoration:
        the brief transition confirms the section actually switched. The
        opacity effect is removed as soon as the animation finishes so it
        cannot slow down normal painting.
        """
        widget = self.stack.currentWidget()
        if widget is None or not widget.isVisible():
            return
        # Only one fade may be in flight. Applying a second effect while the
        # previous animation still runs deletes the old effect under the live
        # animation, which crashes inside the effect on the next repaint.
        self._clear_fade()
        effect = QtWidgets.QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        self._fade_widget = widget
        self._fade_animation = QtCore.QPropertyAnimation(effect, b'opacity', widget)
        self._fade_animation.setDuration(120)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._fade_animation.finished.connect(self._clear_fade)
        self._fade_animation.start()

    def _clear_fade(self):
        """
        Stop any running fade and detach its opacity effect. Reentrancy-safe:
        the references are dropped before the objects are torn down.
        """
        animation = self._fade_animation
        self._fade_animation = None
        if animation is not None:
            animation.stop()
            animation.deleteLater()
        widget = self._fade_widget
        self._fade_widget = None
        if widget is not None:
            try:
                widget.setGraphicsEffect(None)
            except RuntimeError:
                # The page was deleted while fading (e.g. plugin unloaded)
                pass

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
