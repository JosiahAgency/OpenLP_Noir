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
The :mod:`~openlp.plugins.obs_studio.lib.obs_studio_api` module contains
an API interface for the OBS Studio WebSocket protocol
"""
import logging
import obsws_python as obs

log = logging.getLogger(__name__)


class ObsStudioAPI:
    """
    The :class:`ObsStudioAPI` class is an API interface for the OBS Studio WebSocket protocol.
    """
    def __init__(self, host, port, password, timeout=3):
        """
        Initialize.

        :param host: The host address of the OBS Studio WebSocket server.
        :param port: The port number of the OBS Studio WebSocket server.
        :param password: The password for the OBS Studio WebSocket server.
        :param timeout: The timeout for the OBS Studio WebSocket client.
        """
        self.__client = obs.ReqClient(host=host, port=port, password=password, timeout=timeout)

    def send_advanced_scene_switcher_message(self, message):
        """
        Send a Advanced Scene Switcher message to OBS Studio.

        :param message: The message to send to OBS Studio.
        """
        request = {
            "requestData": {
                "message": message
            },
            "requestType": "AdvancedSceneSwitcherMessage",
            "vendorName": "AdvancedSceneSwitcher"
        }
        self.__client.send("CallVendorRequest", data=request, raw=True)

    def disconnect(self):
        """
        Disconnect from the OBS Studio WebSocket server.
        """
        self.__client.disconnect()
