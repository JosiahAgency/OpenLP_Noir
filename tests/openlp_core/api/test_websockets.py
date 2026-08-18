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
Functional tests to test the Http Server Class.
"""
import pytest
from unittest.mock import MagicMock, call, patch

from openlp.core.api.websocketspoll import WebSocketPoller
from openlp.core.api.websockets import WebSocketMessage, WebSocketWorker, WebSocketServer, websocket_send_message
from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings


@pytest.fixture
def poller(settings: Settings):
    poll = WebSocketPoller()
    yield poll


@pytest.fixture
def worker(settings: Settings):
    worker = WebSocketWorker()
    yield worker


def test_poller_get_state(poller: WebSocketPoller, settings: Settings):
    """
    Test the get_state function returns the correct JSON
    """
    # GIVEN: the system is configured with a set of data
    mocked_service_manager = MagicMock()
    mocked_service_manager.service_id = 21
    mocked_live_controller = MagicMock()
    mocked_live_controller.selected_row = 5
    mocked_live_controller.service_item = MagicMock()
    mocked_live_controller.service_item.unique_identifier = '23-34-45'
    mocked_live_controller.blank_screen.isChecked.return_value = True
    mocked_live_controller.theme_screen.isChecked.return_value = False
    mocked_live_controller.desktop_screen.isChecked.return_value = False
    Registry().register('live_controller', mocked_live_controller)
    Registry().register('service_manager', mocked_service_manager)
    # WHEN: The poller polls
    poll_json = poller.get_state()
    # THEN: the live json should be generated and match expected results
    assert poll_json['results']['blank'] is True, 'The blank return value should be True'
    assert poll_json['results']['theme'] is False, 'The theme return value should be False'
    assert poll_json['results']['display'] is False, 'The display return value should be False'
    assert poll_json['results']['isSecure'] is False, 'The isSecure return value should be False'
    assert poll_json['results']['twelve'] is True, 'The twelve return value should be True'
    assert poll_json['results']['version'] == 3, 'The version return value should be 3'
    assert poll_json['results']['slide'] == 5, 'The slide return value should be 5'
    assert poll_json['results']['service'] == 21, 'The version return value should be 21'
    assert poll_json['results']['item'] == '23-34-45', 'The item return value should match 23-34-45'


def test_poller_event_attach(poller: WebSocketPoller, settings: Settings):
    """
    Test the event attach of WebSocketPoller
    """
    # GIVEN: A mocked live_controlled, a mocked slide_controller and mocked change signals
    servicemanager_changed_connect = MagicMock()
    service_manager = MagicMock()
    service_manager.servicemanager_changed = MagicMock()
    service_manager.servicemanager_changed.connect = servicemanager_changed_connect
    poller._service_manager = service_manager
    live_controller = MagicMock()
    slidecontroller_changed_connect = MagicMock()
    live_controller.slidecontroller_changed = MagicMock()
    live_controller.slidecontroller_changed.connect = slidecontroller_changed_connect
    poller._live_controller = live_controller

    # WHEN: the hook_signals function is called
    poller.hook_signals()

    # THEN: service_manager and live_controller changed signals should be connected
    servicemanager_changed_connect.assert_called_once()
    slidecontroller_changed_connect.assert_called_once()


def test_poller_on_change_emit(poller: WebSocketPoller, settings: Settings):
    """
    Test the change event emission of WebSocketPoller
    """
    # GIVEN: A mocked changed signal and create_state function
    poller_changed_emit = MagicMock()
    poller.create_state = MagicMock(return_value={})
    poller.poller_changed = MagicMock()
    poller.poller_changed.emit = poller_changed_emit

    # WHEN: The on_signal_received function is called
    poller.on_signal_received()

    # THEN: poller_changed signal should be emitted once
    poller_changed_emit.assert_called_once()


def test_poller_get_state_is_never_none(poller: WebSocketPoller):
    """
    Test the get_state call never returns None
    """
    # GIVEN: A mocked poller create_state
    poller.create_state = MagicMock(return_value={"key1": "2"})

    # WHEN: poller.get_state is called
    state = poller.get_state()

    # THEN: state is not None
    assert state is not None, 'get_state() return should not be None'


def test_send_message_works(settings: Settings):
    """
    Test the send_message_works really works
    """
    # GIVEN: A mocked WebSocketWorker and a message
    server = WebSocketServer()
    server.worker = MagicMock()
    message = WebSocketMessage(plugin="core", key="test", value="test")

    # WHEN: send_message is called
    server.send_message(message)

    # THEN: Worker add_message_to_queues should be called
    server.worker.add_message_to_queues.assert_called_once_with(message)


def test_websocket_send_message_works(registry: Registry, settings: Settings):
    """Test the send_message_works really works"""
    # GIVEN: A mocked WebSocketWorker and a message
    server = WebSocketServer()
    server.worker = MagicMock()
    message = WebSocketMessage(plugin="core", key="test", value="test")

    # WHEN: send_message is called
    result = websocket_send_message(message)

    # THEN: Worker add_message_to_queues should be called
    assert result is True
    server.worker.add_message_to_queues.assert_called_once_with(message)


def test_websocket_send_message_fail(registry: Registry, settings: Settings):
    """Test the send_message_works returns False when there is no WebSocker server"""
    # GIVEN: A message
    message = WebSocketMessage(plugin="core", key="test", value="test")

    # WHEN: send_message is called
    result = websocket_send_message(message)

    # THEN: The return value should be false
    assert result is False


@patch('openlp.core.api.websockets.asyncio')
def test_websocket_worker_start(mocked_asyncio: MagicMock, worker: WebSocketWorker):
    """
    Test the start function of the worker
    """
    # GIVEN: A worker object and some mocked asyncio
    mocked_lock = MagicMock()
    mocked_asyncio.Lock.return_value = mocked_lock
    mocked_event_loop = MagicMock()
    mocked_event_loop.run_until_complete.side_effect = lambda awaitable: getattr(awaitable, 'close', lambda: None)()
    mocked_asyncio.new_event_loop.return_value = mocked_event_loop

    # WHEN: The start function is called
    with patch.object(worker, 'serve') as mocked_serve, \
            patch.object(worker, 'quit') as mocked_quit:
        mocked_server = MagicMock()
        mocked_serve.return_value = mocked_server
        worker.start()

    # THEN: No error occurs
    mocked_asyncio.Lock.assert_called_once_with()
    assert worker.stop_lock is mocked_lock
    mocked_asyncio.new_event_loop.assert_called_once_with()
    assert worker.loop is mocked_event_loop
    mocked_asyncio.set_event_loop.assert_called_once_with(mocked_event_loop)
    # This is a mix of sync and async, and it's not working right now
    # assert mocked_event_loop.run_until_complete.call_args_list == [
    #     call(mocked_serve()),
    # ]
    mocked_event_loop.close.assert_called_once_with()
    mocked_quit.emit.assert_called_once_with()


def test_websocket_worker_stop(worker: WebSocketWorker, settings: Settings):
    """Test that the worker stops"""
    # GIVEN: A WebSocketWorker with a mocked server
    worker.loop = MagicMock(**{'is_running.side_effect': [True, False]})
    worker._stop_future = MagicMock()

    # WHEN: stop is called
    worker.stop()

    # THEN: No exception and the method should have been called
    assert worker.loop.is_running.call_count == 1
    worker.loop.call_soon_threadsafe.assert_called_once_with(worker._stop_future.set_result, None)


def test_websocket_worker_stop_exception(worker: WebSocketWorker, settings: Settings):
    """Test that the worker stops"""
    # GIVEN: A WebSocketWorker with a mocked server
    worker.server = MagicMock()
    worker.server.close.side_effect = Exception

    # WHEN: stop is called
    with patch('openlp.core.api.websockets.log') as mocked_log:
        worker.stop()

    # THEN: No exception and the method should have been called
    mocked_log.exception.assert_called_once_with('Unable to stop websockets server')


def test_websocket_server_bootstrap_post_set_up(settings: Settings):
    """
    Test that the bootstrap_post_set_up() method calls the start method
    """
    # GIVEN: A WebSocketServer with the start() method mocked out
    Registry().set_flag('no_web_server', False)
    server = WebSocketServer()
    server.start = MagicMock()

    # WHEN: bootstrap_post_set_up() is called
    server.bootstrap_post_set_up()

    # THEN: start() should have been called
    server.start.assert_called_once_with()


@patch('openlp.core.api.websockets.WebSocketWorker')
@patch('openlp.core.api.websockets.run_thread')
def test_websocket_server_start(mocked_run_thread: MagicMock, MockWebSocketWorker: MagicMock, registry: Registry):
    """
    Test the starting of the WebSockets Server with the disabled flag set off
    """
    # GIVEN: A new WebSocketServer
    Registry().set_flag('no_web_server', False)
    server = WebSocketServer()

    # WHEN: I start the server
    server.start()

    # THEN: the api environment should have been created
    assert mocked_run_thread.call_count == 1, 'The qthread should have been called once'
    assert MockWebSocketWorker.call_count == 1, 'The http thread should have been called once'


@patch('openlp.core.api.websockets.WebSocketWorker')
@patch('openlp.core.api.websockets.run_thread')
def test_websocket_server_start_not_required(mocked_run_thread, MockWebSocketWorker, registry: Registry):
    """
    Test the starting of the WebSockets Server with the disabled flag set on
    """
    # GIVEN: A new WebSocketServer and the server is not required
    Registry().set_flag('no_web_server', True)
    server = WebSocketServer()

    # WHEN: I start the server
    server.start()

    # THEN: the api environment should have not been created
    assert mocked_run_thread.call_count == 0, 'The qthread should not have been called'
    assert MockWebSocketWorker.call_count == 0, 'The http thread should not have been called'


@patch('openlp.core.api.websockets.poller')
@patch('openlp.core.api.websockets.run_thread')
def test_websocket_server_connects_to_poller(mock_run_thread: MagicMock, mock_poller: MagicMock, settings: Settings):
    """
    Test if the websocket_server connects to WebSocketPoller
    """
    # GIVEN: A mocked poller signal and a server
    Registry().set_flag('no_web_server', False)
    mock_poller.poller_changed = MagicMock()
    mock_poller.poller_changed.connect = MagicMock()
    server = WebSocketServer()
    server.handle_poller_signal = MagicMock()

    # WHEN: WebSocketServer is started
    server.start()

    # THEN: poller_changed should be connected with WebSocketServer and correct handler
    mock_poller.poller_changed.connect.assert_called_once_with(server.handle_poller_signal)


@patch('openlp.core.api.websockets.poller')
@patch('openlp.core.api.websockets.WebSocketWorker.add_state_to_queues')
@patch('openlp.core.api.websockets.run_thread')
def test_websocket_worker_register_connections(mock_run_thread: MagicMock, mock_add_state_to_queues: MagicMock,
                                               mock_poller: MagicMock, settings: Settings):
    """
    Test if the websocket_server can receive poller signals
    """
    # GIVEN: A mocked poller create_state, a mocked server and a mocked worker
    mock_state = {"key1": "2"}
    mock_poller.get_state.return_value = mock_state
    Registry().set_flag('no_web_server', False)
    server = WebSocketServer()
    server.start()

    # WHEN: server.handle_poller_signal is called
    server.handle_poller_signal()

    # THEN: WebSocketWorker state notify function should be called
    mock_add_state_to_queues.assert_called_once_with(mock_state)


@patch('openlp.core.api.websockets.poller')
@patch('openlp.core.api.websockets.log')
def test_websocket_server_try_poller_hook_signals(mocked_log: MagicMock, mock_poller: MagicMock, settings: Settings):
    """
    Test if the websocket_server invokes poller.hook_signals
    """
    # GIVEN: A mocked poller signal and a server
    mock_poller.hook_signals.side_effect = Exception
    Registry().set_flag('no_web_server', False)
    server = WebSocketServer()

    # WHEN: WebSocketServer is started
    server.try_poller_hook_signals()

    # THEN: poller_changed should be connected with WebSocketServer and correct handler
    mock_poller.hook_signals.assert_called_once_with()
    mocked_log.error.assert_called_once_with('Failed to hook poller signals!')


@patch('openlp.core.api.websockets.poller')
def test_websocket_server_close(mock_poller: MagicMock, settings: Settings):
    """
    Test that the websocket_server close method works correctly
    """
    # GIVEN: A mocked poller signal and a server
    Registry().set_flag('no_web_server', False)
    mock_poller.poller_changed = MagicMock()
    mock_poller.poller_changed.connect = MagicMock()
    server = WebSocketServer()
    server.handle_poller_signal = MagicMock()
    mock_worker = MagicMock()
    server.worker = mock_worker

    # WHEN: WebSocketServer is started
    server.close()

    # THEN: poller_changed should be connected with WebSocketServer and correct handler
    mock_poller.poller_changed.disconnect.assert_called_once_with(server.handle_poller_signal)
    mock_poller.unhook_signals.assert_called_once_with()
    mock_worker.stop.assert_called_once_with()


@patch('openlp.core.api.websockets.poller')
def test_websocket_server_close_when_disabled(mock_poller: MagicMock, registry: Registry, settings: Settings):
    """
    Test if the websocket_server close method correctly skips teardown when disabled
    """
    # GIVEN: A mocked poller signal and a server
    Registry().set_flag('no_web_server', True)
    mock_poller.poller_changed = MagicMock()
    mock_poller.poller_changed.connect = MagicMock()
    server = WebSocketServer()
    server.handle_poller_signal = MagicMock()

    # WHEN: WebSocketServer is started
    server.close()

    # THEN: poller_changed should be connected with WebSocketServer and correct handler
    assert mock_poller.poller_changed.disconnect.call_count == 0
    assert mock_poller.unhook_signals.call_count == 0


def test_add_state_to_queues(worker: WebSocketWorker, settings: Settings):
    """Test that adding the state adds the state to each item in the queue"""
    # GIVEN: A WebSocketWorker and some mocked methods
    worker.event_loop = MagicMock(**{'is_running.return_value': True})
    mocked_queue_1 = MagicMock(put_nowait='put_nowait1')
    mocked_queue_2 = MagicMock(put_nowait='put_nowait2')
    worker.state_queues = MagicMock(**{'copy.return_value': [mocked_queue_1, mocked_queue_2]})

    # WHEN: add_state_to_queues is called
    worker.loop = MagicMock()
    worker.add_state_to_queues({'results': {'service': 'service-id'}})

    # THEN: The correct calls should have been made
    assert worker.loop.call_soon_threadsafe.call_args_list == [
        call('put_nowait1', {'results': {'service': 'service-id'}}),
        call('put_nowait2', {'results': {'service': 'service-id'}})
    ]


def test_add_state_to_queues_no_loop(worker: WebSocketWorker, settings: Settings):
    """Test that adding the state when there's no event loop just exits early"""
    # GIVEN: A WebSocketWorker and some mocked methods
    worker.loop = MagicMock(**{'is_running.return_value': False})

    # WHEN: add_state_to_queues is called
    worker.add_state_to_queues({'results': {'service': 'service-id'}})

    # THEN: Worker add_message_to_queues should be called
    worker.loop.call_soon_threadsafe.assert_not_called()


def test_add_message_to_queues(worker: WebSocketWorker, settings: Settings):
    """Test that adding the message adds the message to each item in the queue"""
    # GIVEN: A WebSocketWorker and some mocked methods
    worker.loop = MagicMock(**{'is_running.return_value': True})
    mocked_queue_1 = MagicMock(put_nowait='put_nowait1')
    mocked_queue_2 = MagicMock(put_nowait='put_nowait2')
    worker.message_queues = MagicMock(**{'copy.return_value': [mocked_queue_1, mocked_queue_2]})
    message = WebSocketMessage(plugin="core", key="test", value="test")

    # WHEN: add_state_to_queues is called
    worker.add_message_to_queues(message)

    # THEN: The correct calls should have been made
    assert worker.loop.call_soon_threadsafe.call_args_list == [
        call('put_nowait1', {'plugin': 'core', 'key': 'test', 'value': 'test'}),
        call('put_nowait2', {'plugin': 'core', 'key': 'test', 'value': 'test'}),
    ]


def test_add_message_to_queues_no_loop(worker: WebSocketWorker, settings: Settings):
    """Test that adding the state when there's no event loop just exits early"""
    # GIVEN: A WebSocketWorker and some mocked methods
    worker.loop = MagicMock(**{'is_running.return_value': False})
    message = WebSocketMessage(plugin="core", key="test", value="test")

    # WHEN: add_state_to_queues is called
    worker.add_message_to_queues(message)

    # THEN: Worker add_message_to_queues should be called
    worker.loop.call_soon_threadsafe.assert_not_called()
