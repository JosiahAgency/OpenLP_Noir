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
import base64
import hashlib
import json
import logging
import uuid
import websocket

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
        self.__password = password
        self.__websocket = websocket.WebSocket()
        self.__websocket.connect(f"ws://{host}:{port}", timeout=timeout)
        self.__auth()

    def __build_auth_string(self, salt, challenge):
        secret = base64.b64encode(
            hashlib.sha256(
                (self.__password + salt).encode('utf-8')
            ).digest()
        )
        auth = base64.b64encode(
            hashlib.sha256(
                secret + challenge.encode('utf-8')
            ).digest()
        ).decode('utf-8')
        return auth

    def __auth(self):
        message = self.__websocket.recv()
        result = json.loads(message)
        server_version = result['d'].get('obsWebSocketVersion')
        log.info('Connected to OBS Studio WebSocket server version %s', server_version)
        auth = self.__build_auth_string(
            result['d']['authentication']['salt'], result['d']['authentication']['challenge']
        )
        payload = {
            "op": 1,
            "d": {
                "rpcVersion": 1,
                "authentication": auth,
                "eventSubscriptions": 1000
            }
        }
        self.__websocket.send(json.dumps(payload))
        message = self.__websocket.recv()
        result = json.loads(message) if message else None

    def send_advanced_scene_switcher_message(self, message):
        """
        Send a Advanced Scene Switcher message to OBS Studio.

        :param message: The message to send to OBS Studio.
        """
        unique_id = uuid.uuid4().hex
        payload = {
            "d": {
                "requestData": {
                    "requestData": {
                        "message": message
                    },
                    "requestType": "AdvancedSceneSwitcherMessage",
                    "vendorName": "AdvancedSceneSwitcher"
                },
                "requestId": unique_id,
                "requestType": "CallVendorRequest"
            },
            "op": 6
        }
        log.info(
            'Sending Advanced Scene Switcher message to OBS Studio: %s', message
        )
        self.__websocket.send(json.dumps(payload))

    def disconnect(self):
        """
        Disconnect from the OBS Studio WebSocket server.
        """
        self.__websocket.close()
