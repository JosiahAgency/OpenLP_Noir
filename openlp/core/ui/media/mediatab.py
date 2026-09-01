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
The :mod:`~openlp.core.ui.media.mediatab` module holds the configuration tab for the media stuff.
"""
import logging

from PySide6 import QtCore, QtWidgets
from PySide6.QtMultimedia import QMediaDevices

from openlp.core.common.i18n import translate
from openlp.core.lib.settingstab import SettingsTab
from openlp.core.ui.icons import UiIcons


log = logging.getLogger(__name__)


class MediaTab(SettingsTab):
    """
    MediaTab is the Media settings tab in the settings dialog.
    """
    def __init__(self, parent):
        """
        Constructor
        """
        self.icon_path = UiIcons().video
        player_translated = translate('OpenLP.MediaTab', 'Media')
        super(MediaTab, self).__init__(parent, 'Media', player_translated)

    def setup_ui(self):
        """
        Set up the UI
        """
        self.setObjectName('MediaTab')
        super(MediaTab, self).setup_ui()
        # Start live items automatically
        self.live_media_group_box = QtWidgets.QGroupBox(self.left_column)
        self.live_media_group_box.setObjectName('live_media_group_box')
        self.media_layout = QtWidgets.QVBoxLayout(self.live_media_group_box)
        self.media_layout.setObjectName('live_media_layout')
        self.auto_start_check_box = QtWidgets.QCheckBox(self.live_media_group_box)
        self.auto_start_check_box.setObjectName('auto_start_check_box')
        self.media_layout.addWidget(self.auto_start_check_box)
        self.left_layout.addWidget(self.live_media_group_box)
        # Select audio output
        self.audio_output_group_box = QtWidgets.QGroupBox(self.left_column)
        self.audio_output_group_box.setObjectName('audio_output_group_box')
        self.audio_output_layout = QtWidgets.QVBoxLayout(self.audio_output_group_box)
        self.audio_output_layout.setObjectName('audio_output_layout')
        # Select live audio output
        self.live_output_layout = QtWidgets.QHBoxLayout()
        self.live_output_layout.setObjectName('live_output_layout')
        self.live_output_layout.setContentsMargins(0, 0, 0, 0)
        self.live_output_label = QtWidgets.QLabel(self.audio_output_group_box)
        self.live_output_label.setObjectName('live_output_label')
        self.live_output_combobox = QtWidgets.QComboBox(self.audio_output_group_box)
        self.live_output_combobox.setObjectName('live_output_combobox')
        self.live_output_layout.addWidget(self.live_output_label)
        self.live_output_layout.addWidget(self.live_output_combobox)
        # Select preview audio output
        self.audio_output_layout.addLayout(self.live_output_layout)
        self.preview_output_layout = QtWidgets.QHBoxLayout()
        self.preview_output_layout.setObjectName('preview_output_layout')
        self.preview_output_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_output_label = QtWidgets.QLabel(self.audio_output_group_box)
        self.preview_output_label.setObjectName('preview_output_label')
        self.preview_output_combobox = QtWidgets.QComboBox(self.audio_output_group_box)
        self.preview_output_combobox.setObjectName('preview_output_combobox')
        self.preview_output_layout.addWidget(self.preview_output_label)
        self.preview_output_layout.addWidget(self.preview_output_combobox)
        self.audio_output_layout.addLayout(self.preview_output_layout)
        self.left_layout.addWidget(self.audio_output_group_box)
        self.left_layout.addStretch()
        self.right_layout.addStretch()

    def retranslate_ui(self):
        """
        Translate the UI on the fly
        """
        self.live_media_group_box.setTitle(translate('MediaPlugin.MediaTab', 'Live Media'))
        self.auto_start_check_box.setText(translate('MediaPlugin.MediaTab', 'Start Live items automatically'))
        self.audio_output_group_box.setTitle(translate('MediaPlugin.MediaTab', 'Audio output (requires restart)'))
        self.live_output_label.setText(translate('MediaPlugin.MediaTab', 'Live audio output device'))
        self.preview_output_label.setText(translate('MediaPlugin.MediaTab', 'Preview audio output device'))

    def load(self):
        """
        Load the settings
        """
        self.auto_start_check_box.setChecked(self.settings.value('media/media auto start') ==
                                             QtCore.Qt.CheckState.Checked)
        # insert audio devices to live and preview audio output comboboxes
        self.live_output_combobox.clear()
        self.preview_output_combobox.clear()
        self.live_output_combobox.addItem(translate('MediaPlugin.MediaTab', 'System default audio output'))
        self.preview_output_combobox.addItem(translate('MediaPlugin.MediaTab', 'System default audio output'))
        for au_out in QMediaDevices().audioOutputs():
            au_out_desc = au_out.description()
            self.live_output_combobox.addItem(au_out_desc)
            if au_out_desc == self.settings.value('media/live audio out'):
                self.live_output_combobox.setCurrentText(au_out_desc)
            self.preview_output_combobox.addItem(au_out_desc)
            if au_out_desc == self.settings.value('media/preview audio out'):
                self.preview_output_combobox.setCurrentText(au_out_desc)

    def save(self):
        """
        Save the settings
        """
        setting_key = 'media/media auto start'
        if self.settings.value(setting_key) != self.auto_start_check_box.checkState():
            self.settings.setValue(setting_key, self.auto_start_check_box.checkState())
        # When saving the default output (default system out for live and none for preview), save blank string
        # to settings to make it independent of translation changes.
        live_output_dev = self.live_output_combobox.currentText()
        if live_output_dev == translate('MediaPlugin.MediaTab', 'System default audio output'):
            self.settings.setValue('media/live audio out', '')
        else:
            self.settings.setValue('media/live audio out', live_output_dev)
        preview_output_dev = self.preview_output_combobox.currentText()
        if preview_output_dev == translate('MediaPlugin.MediaTab', 'System default audio output'):
            self.settings.setValue('media/preview audio out', '')
        else:
            self.settings.setValue('media/preview audio out', preview_output_dev)

    def post_set_up(self, post_update=False):
        """
        Late setup for players as the MediaController has to be initialised first.

        :param post_update: Indicates if called before or after updates.
        """
        pass
