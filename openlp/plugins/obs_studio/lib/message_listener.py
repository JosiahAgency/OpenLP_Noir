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
The :mod:`~openlp.plugins.obs_studio.lib.message_listener` module contains
the MessageListener class for the OBS Studio plugin.
"""
import logging

from openlp.core.common.registry import Registry
from openlp.plugins.obs_studio.lib.obs_studio_api import ObsStudioAPI

log = logging.getLogger(__name__)


class MessageListener():
    """
    This is the OBS Studio message listener that acts on events from the slide controller and
    passes the messages.
    """
    log.info('MessageListener loaded')

    def __init__(self, host: str, port: int, password: str):
        self.client = None
        self.is_connected = False
        self.is_active = False
        self.__host = host
        self.__port = port
        self.__password = password
        self.__setup()

    def __setup(self):
        """
        Setup the message listener.
        """
        # Messages are sent from core.ui.slidecontroller
        Registry().register_function('slidecontroller_slide_selected', self.slide_selected)

    def connect(self):
        """
        Connect to the OBS Studio WebSocket server.
        """
        try:
            self.client = ObsStudioAPI(self.__host, self.__port, self.__password)
            self.is_connected = True
            log.info("Connected successfully to OBS Studio.")
        except ConnectionError as exception:
            log.error("Failed to make a connection to OBS Studio: %s", exception)

    def slide_selected(self, message):
        """
        Handle a message when a slide is selected for the live output.

        :param message: The message to handle.
        """
        if self.is_active:
            is_live = message[1]
            if is_live:
                if not self.is_connected:
                    self.connect()
                if self.is_connected:
                    slide = message[0]
                    slide_number = message[2] + 1
                    message = f"type: {slide.name}, title: {slide.title}, slide: {slide_number}, \
notes: {slide.notes}"
                    try:
                        self.client.send_advanced_scene_switcher_message(message)
                    except ConnectionError as exception:
                        log.error("Message could not be processed by OBS Studio: %s", exception)
                        self.is_connected = False

    def finalise(self):
        """
        Finalise the message listener.
        """
        if self.is_connected:
            self.client.disconnect()
            self.is_connected = False
            log.info("Disconnected from OBS Studio.")
