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
The :mod:`websockets` module contains the websockets server. This is a server used by remotes to listen for stage
changes from within OpenLP. It uses JSON to communicate with the remotes.
"""
import asyncio
import json
import logging
import uuid
from dataclasses import asdict, dataclass

from PySide6 import QtCore

try:
    # New way to do websockets stuff
    from websockets.asyncio.server import ServerConnection, serve
except ImportError:
    try:
        from websockets.server import ServerConnection, serve
    except ImportError:
        from websockets import ServerConnection, serve

from openlp.core.common.mixins import LogMixin, RegistryProperties
from openlp.core.common.registry import Registry, RegistryBase
from openlp.core.threading import ThreadWorker, run_thread
from openlp.core.api.websocketspoll import WebSocketPoller

USERS = set()
poller = WebSocketPoller()


log = logging.getLogger(__name__)
# Disable DEBUG logs for the websockets lib
ws_logger = logging.getLogger('websockets')
ws_logger.setLevel(logging.ERROR)


@dataclass
class WebSocketMessage:
    plugin: str | None
    key: str
    value: int | str | dict | list


class WebSocketWorker(ThreadWorker, RegistryProperties, LogMixin):
    """
    A special Qt thread class to allow the WebSockets server to run at the same time as the UI.

    There's now two queues for websockets: one that handle queues for state changes, and another for messages.
    The main idea is that state-based websocket connections will be removed in future, in favour of message-based
    connections (this will also help save some bandwidth on busy networks)
    """

    def start(self):
        """
        Run the worker.
        """
        self.state_queues = set()
        self.message_queues = set()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.serve())
        finally:
            self.loop.run_until_complete(self._cancel_tasks())
            self.loop.close()
        self.quit.emit()

    async def serve(self):
        """
        Coroutine for starting websocket server
        """
        settings = Registry().get('settings_thread')
        address = settings.value('api/ip address')
        port = settings.value('api/websocket port')
        self.loop = asyncio.get_running_loop()
        self._stop_future = self.loop.create_future()
        for _ in range(3):
            try:
                server = await serve(self.handle_websocket, address, port)
                log.debug(f'WebSocket server listening on {address}:{port}')
                await self._stop_future
                server.close(close_connections=False)
                await server.wait_closed()
                log.debug('WebSocket server stopped')
                break
            except Exception:
                log.exception(f'Failed to start WebSocket server on {address}:{port}')
                await asyncio.sleep(0.2)
        else:
            log.error(f'Giving up starting WebSocket server on {address}:{port}')

    async def _cancel_tasks(self):
        """Cancel all running tasks"""
        for task in asyncio.all_tasks(self.loop):
            if task.done():
                continue
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        log.debug('All WebSocket asyncio tasks cancelled')

    def stop(self):
        """
        Stop the websocket server
        """
        try:
            if self.loop.is_running():
                self.loop.call_soon_threadsafe(self._stop_future.set_result, None)
        except BaseException:
            log.exception('Unable to stop websockets server')

    async def handle_websocket(self, websocket: ServerConnection):
        """
        Handle web socket requests and return the state information
        Waits for information to come over queue

        :param websocket: request from client
        """
        client_id = str(uuid.uuid4() if log.getEffectiveLevel() == logging.DEBUG else 0)
        log.debug(f'(client_id={client_id}) WebSocket handle_websocket connection')
        queue = asyncio.Queue()
        is_state_queue = not websocket.request.path.startswith('/messages')
        await self.register(websocket, client_id, queue, is_state_queue)
        try:
            if is_state_queue:
                reply = poller.get_state()
                if reply:
                    await self.send_reply(websocket, client_id, reply)
            while True:
                done, pending = await asyncio.wait(
                    [asyncio.create_task(queue.get()), asyncio.create_task(websocket.wait_closed())],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
                # If there is a new item in client's queue, await_result will contain an item, if the connection is
                # closed, it will be None.
                await_result = done.pop().result()
                if await_result is not None:
                    await self.send_reply(websocket, client_id, await_result)
                else:
                    break
        finally:
            await self.unregister(websocket, client_id, queue, is_state_queue)

    async def register(self, websocket: ServerConnection, client_id: str, queue: asyncio.Queue,
                       is_state_queue: bool = True):
        """
        Register Clients
        :param websocket: The client details
        :param queue: The Command Queue
        :return:
        """
        log.debug(f'(client_id={client_id}) WebSocket handler register')
        USERS.add(websocket)
        if is_state_queue:
            self.state_queues.add(queue)
        else:
            self.message_queues.add(queue)
        log.debug('WebSocket clients count: {client_count}'.format(client_count=len(USERS)))

    async def unregister(self, websocket: ServerConnection, client_id: str, queue: asyncio.Queue,
                         is_state_queue: bool = True):
        """
        Unregister Clients
        :param websocket: The client details
        :return:
        """
        log.debug(f'(client_id={client_id}) WebSocket handler unregister')
        USERS.discard(websocket)
        if is_state_queue:
            self.state_queues.discard(queue)
        else:
            self.message_queues.discard(queue)
        log.debug('WebSocket clients count: {client_count}'.format(client_count=len(USERS)))

    async def send_reply(self, websocket: ServerConnection, client_id: str, reply: dict):
        json_reply = json.dumps(reply).encode()
        await websocket.send(json_reply)
        log.debug(f'(client_id={client_id}) WebSocket send reply: {json_reply}')

    def add_state_to_queues(self, state):
        """
        Inserts the state in each connection message queue
        :param state: OpenLP State
        """
        if not self.loop.is_running():
            # Sometimes the event loop doesn't run when we call this method -- probably because it is shutting down
            # See https://gitlab.com/openlp/openlp/-/issues/1618
            return
        for queue in self.state_queues.copy():
            self.loop.call_soon_threadsafe(queue.put_nowait, state)

    def add_message_to_queues(self, message: WebSocketMessage):
        """
        Inserts the message in each connection message queue
        :param state: OpenLP State
        """
        if not self.loop.is_running():
            # Sometimes the event loop doesn't run when we call this method -- probably because it is shutting down
            # See https://gitlab.com/openlp/openlp/-/issues/1618
            return
        for queue in self.message_queues.copy():
            self.loop.call_soon_threadsafe(queue.put_nowait, asdict(message))


class WebSocketServer(RegistryBase, RegistryProperties, QtCore.QObject, LogMixin):
    """
    Wrapper round a server instance
    """

    _send_message_signal = QtCore.Signal(WebSocketMessage)

    def __init__(self):
        """
        Initialise the WebSockets server
        """
        super(WebSocketServer, self).__init__()
        self.worker = None
        self._send_message_signal.connect(self.__handle_message_signal)

    def bootstrap_post_set_up(self):
        self.start()

    def start(self):
        """
        Starts the WebSockets server
        """
        if self.worker is None and not Registry().get_flag('no_web_server'):
            self.worker = WebSocketWorker()
            run_thread(self.worker, 'websocket_server')
            poller.poller_changed.connect(self.handle_poller_signal)
            # Only hooking poller signals after all UI is available
            Registry().register_function('bootstrap_completion', self.try_poller_hook_signals)

    @QtCore.Slot()
    def handle_poller_signal(self):
        if self.worker is not None:
            self.worker.add_state_to_queues(poller.get_state())

    def send_message(self, message: WebSocketMessage):
        # Using a signal to run emission on this thread
        self._send_message_signal.emit(message)

    def __handle_message_signal(self, message: WebSocketMessage):
        if self.worker is not None:
            self.worker.add_message_to_queues(message)

    def try_poller_hook_signals(self):
        try:
            poller.hook_signals()
        except Exception:
            log.error('Failed to hook poller signals!')

    def close(self):
        """
        Closes the WebSocket server and detach associated signals
        """
        if Registry().get_flag('no_web_server'):
            return
        try:
            poller.poller_changed.disconnect(self.handle_poller_signal)
            poller.unhook_signals()
            self.worker.stop()
        finally:
            self.worker = None


def websocket_send_message(message: WebSocketMessage):
    """
    Sends a message over websocket to all connected clients.
    """
    try:
        if ws := Registry().get('web_socket_server'):
            ws.send_message(message)
            return True
    except KeyError:
        pass
    return False
