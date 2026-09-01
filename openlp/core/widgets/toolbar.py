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
Provide common toolbar handling for OpenLP
"""
import logging

from PySide6 import QtCore, QtGui, QtWidgets
from openlp.core.common.i18n import translate
from openlp.core.common.registry import Registry

from openlp.core.lib.ui import create_widget_action
from openlp.core.ui.icons import UiIcons


log = logging.getLogger(__name__)


class OpenLPToolbar(QtWidgets.QToolBar):
    """
    Lots of toolbars around the place, so it makes sense to have a common way to manage them. This is the base toolbar
    class.
    """
    def __init__(self, parent):
        """
        Initialise the toolbar.
        """
        super().__init__(parent)
        # useful to be able to reuse button icons...
        self.setIconSize(QtCore.QSize(20, 20))
        self.actions_map: dict[str, QtGui.QAction] = {}
        log.debug('Init done for %s' % parent.__class__.__name__)

    def add_toolbar_action(self, name, **kwargs):
        """
        A method to help developers easily add a button to the toolbar. A new QAction is created by calling
        ``create_action()``. The action is added to the toolbar and the toolbar is set as parent. For more details
        please look at openlp.core.lib.ui.create_action()
        """
        action = create_widget_action(self, name, **kwargs)
        self.actions_map[name] = action
        return action

    def add_toolbar_widget(self, widget):
        """
        Add a widget and store it's handle under the widgets object name.
        """
        action = self.addWidget(widget)
        self.actions_map[widget.objectName()] = action

    def set_widget_visible(self, widgets, visible=True):
        """
        Set the visibility for a widget or a list of widgets.

        :param widgets: A list of strings or individual string with widget object names.
        :param visible: The new state as bool.
        """
        if isinstance(widgets, list):
            for handle in widgets:
                if handle in self.actions_map:
                    self.actions_map[handle].setVisible(visible)
                else:
                    log.warning('No handle "%s" in actions list.', str(handle))
        else:
            if widgets in self.actions_map:
                self.actions_map[widgets].setVisible(visible)
            else:
                log.warning('No handle "%s" in actions list.', str(widgets))


    def set_widget_checked(self, widgets, checked=True):
        """
        Set the checked state for a widget or a list of widgets.

        :param widgets: A list of string with widget object names.
        :param enabled: The new state as bool.
        """
        if isinstance(widgets, list):
            for handle in widgets:
                if handle in self.actions_map:
                    self.actions_map[handle].setChecked(checked)
                else:
                    log.warning('No handle "%s" in actions list.', str(handle))
        else:
            if widgets in self.actions_map:
                self.actions_map[widgets].setChecked(checked)
            else:
                log.warning('No handle "%s" in actions list.', str(widgets))

    def remove_widget(self, name):
        """
        Find and remove an action from the toolbar
        :param name: The name of the action to me removed
        :return:
        """
        try:
            act = self.actions_map[name]
            self.removeAction(act)
        except KeyError:
            log.warning(f'No handle {name} in actions list.')

    def add_spacer(self):
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                            QtWidgets.QSizePolicy.Policy.Preferred)
        separator = QtWidgets.QWidget()
        separator.setSizePolicy(size_policy)
        self.addWidget(separator)
        pass


class MediaToolbar(OpenLPToolbar):
    def __init__(self, parent, hide_components=[], action_prefixes=''):
        super().__init__(parent)
        self.parent = parent
        self.on_action = lambda *args: None
        self.hide_components = hide_components
        self.action_prefixes = action_prefixes
        self.setup_ui()

    def setup_ui(self):
        # Build a Media ToolBar
        self.setObjectName('slide_controller_toolbar')
        self.identification_label = QtWidgets.QLabel()
        self.identification_label.setContentsMargins(0, 0, 8, 0)
        self.set_label(None)  # Hiding it by default
        self.add_toolbar_widget(self.identification_label)
        self.add_toolbar_action(self.action_prefixes + 'playbackPlay', text='media_playback_play',
                                icon=UiIcons().play,
                                tooltip=translate('OpenLP.SlideController', 'Start playing media.'),
                                triggers=self._on_action)
        self.add_toolbar_action(self.action_prefixes + 'playbackPause', text='media_playback_pause',
                                icon=UiIcons().pause,
                                tooltip=translate('OpenLP.SlideController', 'Pause playing media.'),
                                triggers=self._on_action)
        self.add_toolbar_action(self.action_prefixes + 'playbackStop', text='media_playback_stop',
                                icon=UiIcons().stop,
                                tooltip=translate('OpenLP.SlideController', 'Stop playing media.'),
                                triggers=self._on_action)
        if 'loop' not in self.hide_components:
            self.add_toolbar_action(self.action_prefixes + 'playbackLoop', text='media_playback_loop',
                                    icon=UiIcons().get_icon_variant_selected('repeat'), checked=False,
                                    tooltip=translate('OpenLP.SlideController', 'Loop playing media.'),
                                    triggers=self._on_action)
        self.position_label = QtWidgets.QLabel()
        self.position_label.setText(' 00:00 / 00:00')
        self.position_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.position_label.setToolTip(translate('OpenLP.SlideController', 'Media timer.'))
        self.position_label.setMinimumSize(90, 0)
        self.position_label.setObjectName(self.action_prefixes + 'position_label')
        self.add_toolbar_widget(self.position_label)
        if 'seek' not in self.hide_components:
            # Build the media seek_slider.
            self.seek_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            self.seek_slider.setMaximum(1000)
            self.seek_slider.setTracking(True)
            self.seek_slider.setMouseTracking(True)
            self.seek_slider.setToolTip(translate('OpenLP.SlideController', 'Video position.'))
            self.seek_slider.setGeometry(QtCore.QRect(90, 260, 221, 24))
            self.seek_slider.setObjectName(self.action_prefixes + 'seek_slider')
            self.add_toolbar_widget(self.seek_slider)
            self.seek_slider.valueChanged.connect(self._on_action)
        self.volume_label = QtWidgets.QLabel()
        self.volume_label.setText(' 00:00')
        self.volume_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.volume_label.setToolTip(translate('OpenLP.SlideController', 'Volume.'))
        self.volume_label.setMinimumSize(90, 0)
        self.volume_label.setObjectName(self.action_prefixes + 'volume_label')
        self.add_toolbar_widget(self.volume_label)
        if 'volume' not in self.hide_components:
            # Build the volume_slider.
            self.volume_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            self.volume_slider.setTickInterval(10)
            self.volume_slider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksAbove)
            self.volume_slider.setMinimum(0)
            self.volume_slider.setMaximum(100)
            self.volume_slider.setTracking(True)
            self.volume_slider.setToolTip(translate('OpenLP.SlideController', 'Audio Volume.'))
            self.volume_slider.setGeometry(QtCore.QRect(90, 160, 221, 24))
            self.volume_slider.setObjectName(self.action_prefixes + 'volume_slider')
            self.add_toolbar_widget(self.volume_slider)
            self.volume_slider.valueChanged.connect(self._on_action)

    def set_label(self, label):
        if label:
            self.identification_label.setText(label)
            self.identification_label.setVisible(True)
        else:
            self.identification_label.setText('')
            self.identification_label.setVisible(False)

    def _on_action(self, *args):
        sender = self.sender().objectName() if self.sender().objectName() else self.sender().text()
        Registry().execute("{text}".format(text=sender), [self.parent, args])
