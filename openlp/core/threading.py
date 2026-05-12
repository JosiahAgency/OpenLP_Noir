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
The :mod:`openlp.core.threading` module contains some common threading code
"""
import logging

from PySide6 import QtCore

from openlp.core.common.mixins import LogMixin
from openlp.core.common.registry import Registry

log = logging.getLogger(__name__)


class ThreadWorker(QtCore.QObject, LogMixin):
    """
    The :class:`~openlp.core.threading.ThreadWorker` class provides a base class for all worker objects
    """
    quit = QtCore.Signal()
    error = QtCore.Signal(str, str)

    def start(self):
        """
        The start method is how the worker runs. Basically, put your code here.
        """
        raise NotImplementedError('Your base class needs to override this method and run self.quit.emit() at the end.')


def run_thread(worker, thread_name, can_start=True):
    """
    Create a thread and assign a worker to it. This removes a lot of boilerplate code from the codebase.

    :param QObject worker: A QObject-based worker object which does the actual work.
    :param str thread_name: The name of the thread, used to keep track of the thread.
    :param bool can_start: Start the thread. Defaults to True.
    """
    if not thread_name:
        raise ValueError('A thread_name is required when calling the "run_thread" function')
    application = Registry().get('application')
    main_window = Registry().get('main_window')
    if thread_name in application.worker_threads:
        raise KeyError('A thread with the name "{}" has already been created, please use another'.format(thread_name))
    # Create the thread and add the thread and the worker to the parent
    thread = QtCore.QThread()
    application.worker_threads[thread_name] = {
        'thread': thread,
        'worker': worker
    }
    # Move the worker into the thread's context
    worker.moveToThread(thread)
    # Connect slots and signals
    thread.started.connect(worker.start)
    worker.quit.connect(thread.quit)
    worker.quit.connect(worker.deleteLater, QtCore.Qt.ConnectionType.QueuedConnection)
    # when used from the FTW the main window is not yet available
    if main_window:
        worker.error.connect(main_window.error_message)
    thread.finished.connect(thread.deleteLater, QtCore.Qt.ConnectionType.QueuedConnection)
    thread.finished.connect(make_remove_thread(thread_name), QtCore.Qt.ConnectionType.QueuedConnection)
    if can_start:
        thread.start()


def get_thread_worker(thread_name):
    """
    Get the worker by the thread name

    :param str thread_name: The name of the thread
    :returns: The worker for this thread name, or None
    """
    thread_info = Registry().get('application').worker_threads.get(thread_name)
    if not thread_info:
        return
    return thread_info.get('worker')


def is_thread_finished(thread_name):
    """
    Check if a thread is finished running.

    :param str thread_name: The name of the thread
    :returns: True if the thread is finished, False if it is still running
    """
    try:
        app = Registry().get('application')
        return thread_name not in app.worker_threads or app.worker_threads[thread_name]['thread'].isFinished()
    except KeyError:
        log.exception(f'Thread {thread_name} not found when checking for finished threads')
        return True


def make_remove_thread(thread_name):
    """
    Create a function to remove the thread once the thread is finished.

    :param str thread_name: The name of the thread which should be removed from the thread registry.
    :returns: A function which will remove the thread from the thread registry.
    """

    def remove_thread():                                                                        # pragma: nocover
        """
        Stop and remove a registered thread

        :param str thread_name: The name of the thread to stop and remove
        """
        application = Registry().get('application')
        if application and thread_name in application.worker_threads:
            log.debug(f'Removing thread {thread_name}')
            del application.worker_threads[thread_name]
    return remove_thread
