##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2025 OpenLP Developers                                   #
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
The :mod:`~openlp.plugins.obs_studio.lib.obsstudio_tab` module contains
the settings tab for the OBS Studio plugin
"""
from json import JSONDecodeError
from PyQt5 import QtCore, QtWidgets
import obsws_python.error

from openlp.core.common.i18n import translate
from openlp.core.lib.settingstab import SettingsTab
from openlp.plugins.obs_studio.lib.obs_studio_api import ObsStudioAPI


class ObsStudioTab(SettingsTab):
    """
    ObsStudioTab is the OBS Studio settings tab in the settings dialog.
    """
    def setup_ui(self):
        self.setObjectName('ObsStudioTab')
        tab_layout = QtWidgets.QVBoxLayout(self)
        tab_layout.setObjectName('tab_layout')
        tab_layout.setAlignment(QtCore.Qt.AlignTop)
        self.network_group_box = QtWidgets.QGroupBox(self)
        tab_layout.addWidget(self.network_group_box)
        network_layout = QtWidgets.QFormLayout(self.network_group_box)
        network_layout.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.AllNonFixedFieldsGrow
        )
        self.host_label = QtWidgets.QLabel(self.network_group_box)
        self.host_line_edit = QtWidgets.QLineEdit(self.network_group_box)
        self.host_line_edit.setMaxLength(64)
        network_layout.addRow(self.host_label, self.host_line_edit)
        self.port_label = QtWidgets.QLabel(self.network_group_box)
        self.port_line_edit = QtWidgets.QLineEdit(self.network_group_box)
        self.port_line_edit.setMaxLength(6)
        network_layout.addRow(self.port_label, self.port_line_edit)
        self.auth_group_box = QtWidgets.QGroupBox(self)
        tab_layout.addWidget(self.auth_group_box)
        auth_layout = QtWidgets.QFormLayout(self.auth_group_box)
        auth_layout.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.AllNonFixedFieldsGrow
        )
        self.password_label = QtWidgets.QLabel(self.auth_group_box)
        self.password_line_edit = QtWidgets.QLineEdit(self.auth_group_box)
        self.password_line_edit.setMaxLength(64)
        self.password_line_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        auth_layout.addRow(self.password_label, self.password_line_edit)
        self.test_group_box = QtWidgets.QGroupBox(self)
        tab_layout.addWidget(self.test_group_box)
        test_layout = QtWidgets.QFormLayout(self.test_group_box)
        test_layout.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.AllNonFixedFieldsGrow
        )
        self.message_label = QtWidgets.QLabel(self.test_group_box)
        self.message_line_edit = QtWidgets.QLineEdit(self.test_group_box)
        self.test_button = QtWidgets.QPushButton(self.test_group_box)
        self.message_line_edit.setMaxLength(64)
        test_layout.addRow(self.message_label, self.message_line_edit)
        button_layout = QtWidgets.QDialogButtonBox(self.test_group_box)
        button_layout.addButton(self.test_button, QtWidgets.QDialogButtonBox.AcceptRole)
        test_layout.addRow(button_layout)
        self.test_button.clicked.connect(self.on_test_button_clicked)

    def retranslate_ui(self):
        self.network_group_box.setTitle(
            translate('ObsStudioPlugin.ObsStudioTab', 'Network Settings')
        )
        self.host_label.setText(translate('ObsStudioPlugin.ObsStudioTab', 'Host:'))
        self.port_label.setText(translate('ObsStudioPlugin.ObsStudioTab', 'Port:'))
        self.auth_group_box.setTitle(
            translate('ObsStudioPlugin.ObsStudioTab', 'Authentication Settings')
        )
        self.password_label.setText(translate('ObsStudioPlugin.ObsStudioTab', 'Password:'))
        self.test_group_box.setTitle(translate('ObsStudioPlugin.ObsStudioTab', 'Test'))
        self.message_label.setText(translate('ObsStudioPlugin.ObsStudioTab', 'Message:'))
        self.test_button.setText(translate('ObsStudioPlugin.ObsStudioTab', 'Send'))

    def resizeEvent(self, event=None):
        """
        Don't call SettingsTab resize handler because we are not using left/right columns.
        """
        QtWidgets.QWidget.resizeEvent(self, event)

    def load(self):
        """
        Load the settings into the UI.
        """
        host = self.settings.value('obs_studio/host')
        port = self.settings.value('obs_studio/port')
        password = self.settings.value('obs_studio/password')
        self.host_line_edit.setText(host)
        self.port_line_edit.setText(str(port))
        self.password_line_edit.setText(password)

    def save(self):
        """
        Save the changes on exit of the Settings dialog.
        """
        host = self.host_line_edit.text()
        port = int(self.port_line_edit.text())
        password = self.password_line_edit.text()
        self.settings.setValue('obs_studio/host', host)
        self.settings.setValue('obs_studio/port', str(port))
        self.settings.setValue('obs_studio/password', password)

    def on_test_button_clicked(self):
        """
        Test the OBS Studio connection with the provided settings.
        """
        host = self.host_line_edit.text()
        port = int(self.port_line_edit.text())
        password = self.password_line_edit.text()
        message = self.message_line_edit.text()
        dialog_title = 'OBS Studio Connection Test'
        try:
            test_client = ObsStudioAPI(host, port, password)
            test_client.send_advanced_scene_switcher_message(message)
            test_client.disconnect()
            QtWidgets.QMessageBox.information(self, dialog_title,
                                              "Message was sent successfully.",
                                              QtWidgets.QMessageBox.Ok)
        except (ConnectionError, obsws_python.error.OBSSDKError, JSONDecodeError) as exception:
            QtWidgets.QMessageBox.warning(self, dialog_title,
                                          f"Message was not sent successfully: {exception}",
                                          QtWidgets.QMessageBox.Ok)
