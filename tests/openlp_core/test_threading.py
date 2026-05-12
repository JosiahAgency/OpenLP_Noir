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
Package to test the openlp.core.threading package.
"""
from PySide6 import QtCore
from inspect import isfunction
from unittest.mock import MagicMock, call, patch

from openlp.core.threading import ThreadWorker, get_thread_worker, is_thread_finished, make_remove_thread, run_thread


def test_run_thread_no_name():
    """
    Test that trying to run a thread without a name results in an exception being thrown
    """
    # GIVEN: A fake worker
    # WHEN: run_thread() is called without a name
    try:
        run_thread(MagicMock(), '')
        assert False, 'A ValueError should have been thrown to prevent blank names'
    except ValueError:
        # THEN: A ValueError should have been thrown
        assert True, 'A ValueError was correctly thrown'


@patch('openlp.core.threading.Registry')
def test_run_thread_exists(MockRegistry):
    """
    Test that trying to run a thread with a name that already exists will throw a KeyError
    """
    # GIVEN: A mocked registry with a main window object
    mocked_application = MagicMock()
    mocked_application.worker_threads = {'test_thread': MagicMock()}
    MockRegistry.return_value.get.return_value = mocked_application

    # WHEN: run_thread() is called
    try:
        run_thread(MagicMock(), 'test_thread')
        assert False, 'A KeyError should have been thrown to show that a thread with this name already exists'
    except KeyError:
        assert True, 'A KeyError was correctly thrown'


@patch('openlp.core.threading.QtCore.QThread')
@patch('openlp.core.threading.Registry')
def test_run_thread(MockRegistry, MockQThread):
    """
    Test that running a thread works correctly
    """
    # GIVEN: A mocked registry with a main window object
    mocked_application = MagicMock()
    mocked_application.worker_threads = {}
    MockRegistry.return_value.get.return_value = mocked_application

    # WHEN: run_thread() is called
    run_thread(MagicMock(), 'test_thread')

    # THEN: The thread should be in the threads list and the correct methods should have been called
    assert len(mocked_application.worker_threads.keys()) == 1, 'There should be 1 item in the list of threads'
    assert list(mocked_application.worker_threads.keys()) == ['test_thread'], \
        'The test_thread item should be in the list'
    mocked_worker = mocked_application.worker_threads['test_thread']['worker']
    mocked_thread = mocked_application.worker_threads['test_thread']['thread']
    mocked_worker.moveToThread.assert_called_once_with(mocked_thread)
    mocked_thread.started.connect.assert_called_once_with(mocked_worker.start)
    expected_quit_calls = [
        call(mocked_thread.quit),
        call(mocked_worker.deleteLater, QtCore.Qt.ConnectionType.QueuedConnection)
    ]
    assert mocked_worker.quit.connect.call_args_list == expected_quit_calls, \
        'The workers quit signal should be connected twice'
    assert mocked_thread.finished.connect.call_args_list[0] == call(
        mocked_thread.deleteLater, QtCore.Qt.ConnectionType.QueuedConnection
    ), 'The threads finished signal should be connected to its deleteLater slot'
    assert mocked_thread.finished.connect.call_count == 2, 'The signal should have been connected twice'
    mocked_thread.start.assert_called_once_with()


def test_thread_worker():
    """
    Test that creating a thread worker object and calling start throws and NotImplementedError
    """
    # GIVEN: A ThreadWorker class
    worker = ThreadWorker()

    try:
        # WHEN: calling start()
        worker.start()
        assert False, 'A NotImplementedError should have been thrown'
    except NotImplementedError:
        # A NotImplementedError should be thrown
        pass
    except Exception:
        assert False, 'A NotImplementedError should have been thrown'


@patch('openlp.core.threading.Registry')
def test_get_thread_worker(MockRegistry):
    """
    Test that calling the get_thread_worker() function returns the correct worker
    """
    # GIVEN: A mocked thread worker
    mocked_worker = MagicMock()
    MockRegistry.return_value.get.return_value.worker_threads = {'test_thread': {'worker': mocked_worker}}

    # WHEN: get_thread_worker() is called
    worker = get_thread_worker('test_thread')

    # THEN: The mocked worker is returned
    assert worker is mocked_worker, 'The mocked worker should have been returned'


@patch('openlp.core.threading.Registry')
def test_get_thread_worker_mising(MockRegistry):
    """
    Test that calling the get_thread_worker() function raises a KeyError if it does not exist
    """
    # GIVEN: A mocked thread worker
    MockRegistry.return_value.get.return_value.worker_threads = {}

    # WHEN: get_thread_worker() is called
    result = get_thread_worker('test_thread')

    # THEN: None should have been returned
    assert result is None


@patch('openlp.core.threading.Registry')
def test_is_thread_finished(MockRegistry):
    """
    Test the is_thread_finished() function
    """
    # GIVEN: A mock thread and worker
    mocked_thread = MagicMock()
    mocked_thread.isFinished.return_value = False
    MockRegistry.return_value.get.return_value.worker_threads = {'test': {'thread': mocked_thread}}

    # WHEN: is_thread_finished() is called
    result = is_thread_finished('test')

    # THEN: The result should be correct
    assert result is False, 'is_thread_finished should have returned False'


@patch('openlp.core.threading.Registry')
def test_is_thread_finished_missing(MockRegistry):
    """
    Test that calling the is_thread_finished() function returns True if the thread doesn't exist
    """
    # GIVEN: A mocked thread worker
    MockRegistry.return_value.get.return_value.worker_threads = {}

    # WHEN: get_thread_worker() is called
    result = is_thread_finished('test_thread')

    # THEN: The result should be correct
    assert result is True, 'is_thread_finished should return True when a thread is missing'


def test_make_remove_thread():
    """
    Test the make_remove_thread() function
    """
    # GIVEN: A thread name
    thread_name = 'test_thread'

    # WHEN: make_remove_thread() is called
    rm_func = make_remove_thread(thread_name)

    # THEN: The result should be a function
    assert isfunction(rm_func), 'make_remove_thread should return a function'
    assert rm_func.__name__ == 'remove_thread'
