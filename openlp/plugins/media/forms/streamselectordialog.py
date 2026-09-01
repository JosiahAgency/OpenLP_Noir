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

import re
from PySide6 import QtWidgets
from PySide6.QtMultimedia import QMediaDevices

from openlp.core.common.i18n import translate
from openlp.core.common.platform import is_linux


class CaptureModeWidget(QtWidgets.QWidget):
    """
    Simple widget containing a groupbox to hold devices and a groupbox for options
    """
    def __init__(self, parent=None, disable_audio=False):
        super().__init__(parent)
        self.disable_audio = disable_audio
        self.setup_ui()
        self.callback = None

    def setup_ui(self):
        self.setObjectName('capture_mode_widget')
        self.capture_mode_widget_layout = QtWidgets.QVBoxLayout(self)
        self.capture_mode_widget_layout.setObjectName('capture_mode_widget_layout')
        self.device_group = QtWidgets.QGroupBox(self)
        self.device_group.setObjectName('device_group')
        self.device_group_layout = QtWidgets.QFormLayout(self.device_group)
        self.device_group_layout.setObjectName('device_group_layout')
        self.capture_mode_widget_layout.addWidget(self.device_group)
        # Video devices
        self.video_devices_label = QtWidgets.QLabel(self)
        self.video_devices_label.setObjectName('video_devices_label')
        self.video_devices_combo_box = QtWidgets.QComboBox(self)
        self.video_devices_combo_box.addItems([''])
        self.video_devices_combo_box.setObjectName('video_devices_combo_box')
        if is_linux():
            self.video_devices_combo_box.setEditable(True)
        self.device_group_layout.addRow(self.video_devices_label, self.video_devices_combo_box)
        # Audio devices
        self.audio_devices_label = QtWidgets.QLabel(self)
        self.audio_devices_label.setObjectName('audio_devices_label')
        self.audio_devices_combo_box = QtWidgets.QComboBox(self)
        self.audio_devices_combo_box.addItems([''])
        self.audio_devices_combo_box.setObjectName('audio_devices_combo_box')
        if is_linux():
            self.audio_devices_combo_box.setEditable(True)
        if self.disable_audio:
            self.audio_devices_combo_box.hide()
            self.audio_devices_label.hide()
        self.device_group_layout.addRow(self.audio_devices_label, self.audio_devices_combo_box)
        # connect
        self.video_devices_combo_box.currentIndexChanged.connect(self.update_mrl)
        self.audio_devices_combo_box.currentIndexChanged.connect(self.update_mrl)

    def set_callback(self, callback):
        self.callback = callback

    def retranslate_ui(self):
        self.device_group.setTitle(translate('MediaPlugin.StreamSelector', 'Device Selection'))
        self.video_devices_label.setText(translate('MediaPlugin.StreamSelector', 'Video device name'))
        self.audio_devices_label.setText(translate('MediaPlugin.StreamSelector', 'Audio device name'))

    def find_devices(self):
        """
        Insert devices detected by Qt
        """
        for cam in QMediaDevices.videoInputs():
            self.video_devices_combo_box.addItem(cam.description())
        for au in QMediaDevices.audioInputs():
            self.audio_devices_combo_box.addItem(au.description())

    def update_mrl(self):
        vdev = self.video_devices_combo_box.currentText()
        adev = self.audio_devices_combo_box.currentText()
        stream_string = 'qt6video={vdev};qt6audio={adev}'.format(vdev=vdev, adev=adev)
        self.callback(stream_string)

    def set_mrl(self, main, options):
        vdev = re.search(r'qt6video=(.+);', main)
        if vdev:
            for i in range(self.video_devices_combo_box.count()):
                if self.video_devices_combo_box.itemText(i) == vdev.group(1):
                    self.video_devices_combo_box.setCurrentIndex(i)
                    break
        adev = re.search(r'qt6audio=(.+)', main)
        if adev:
            for i in range(self.audio_devices_combo_box.count()):
                if self.audio_devices_combo_box.itemText(i) == adev.group(1):
                    self.audio_devices_combo_box.setCurrentIndex(i)
                    break


class Ui_StreamSelector(object):
    def setup_ui(self, stream_selector):
        self.main_layout.addWidget(self.top_widget)
        # the capture widget
        self.capture_widget = CaptureModeWidget(stream_selector, self.theme_stream)
        self.capture_widget.find_devices()
        self.capture_widget.retranslate_ui()
        self.main_layout.addWidget(self.capture_widget)
        # Save and close buttons
        self.button_box = QtWidgets.QDialogButtonBox(stream_selector)
        self.button_box.addButton(QtWidgets.QDialogButtonBox.StandardButton.Save)
        self.button_box.addButton(QtWidgets.QDialogButtonBox.StandardButton.Close)
        self.close_button = self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Close)
        self.save_button = self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Save)
        self.main_layout.addWidget(self.button_box)
        # translate
        self.retranslate_ui(stream_selector)
        # connect
        self.button_box.accepted.connect(stream_selector.accept)
        self.button_box.rejected.connect(stream_selector.reject)

    def retranslate_ui(self, stream_selector):
        stream_selector.setWindowTitle(translate('MediaPlugin.StreamSelector', 'Select Input Stream'))
        if not self.theme_stream:
            self.stream_name_label.setText(translate('MediaPlugin.StreamSelector', 'Stream name'))
