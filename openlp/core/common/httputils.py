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
The :mod:`openlp.core.common.httputils` module provides the utility methods for downloading stuff.
"""
import hashlib
import logging
import sys
import time
from pathlib import Path
from random import randint
from tempfile import gettempdir

import requests
from PySide6 import QtCore

from openlp.core.common import trace_error_handler
from openlp.core.common.registry import Registry
from openlp.core.common.settings import ProxyMode
from openlp.core.threading import ThreadWorker


log = logging.getLogger(__name__ + '.__init__')

USER_AGENTS = {
    'win32': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/117.0.5938.132 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.132 '
        'Safari/537.36 Edg/117.0.2045.43',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0'
    ],
    'darwin': [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.0; rv:109.0) Gecko/20100101 Firefox/118.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/117.0.5938.132 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) '
        'Version/16.5 Safari/605.1.15',
    ],
    'linux2': [
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.132 Safari/537.36',
        'Mozilla/5.0 (X11; CrOS armv7l 2913.260.0) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/117.0.5938.132 '
        'Safari/537.11',
        'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0'
    ],
    'default': [
        'Mozilla/5.0 (X11; NetBSD amd64; rv:109.0) Gecko/20100101 Firefox/118.0'
    ]
}
CONNECTION_TIMEOUT = 30
CONNECTION_RETRIES = 2


def get_proxy_settings(mode=None):
    """
    Create a dictionary containing the proxy settings.

    :param ProxyMode | None mode: Specify the source of the proxy settings
    :return: A dict using the format expected by the requests library.
    :rtype: dict | None
    """
    settings = Registry().get('settings')
    if mode is None:
        mode = settings.value('advanced/proxy mode')
    if mode == ProxyMode.NO_PROXY:
        return {'http': None, 'https': None}
    elif mode == ProxyMode.SYSTEM_PROXY:
        # The requests library defaults to using the proxy settings in the environment variables
        return
    elif mode == ProxyMode.MANUAL_PROXY:
        http_addr = settings.value('advanced/proxy http')
        https_addr = settings.value('advanced/proxy https')
        username = settings.value('advanced/proxy username')
        password = settings.value('advanced/proxy password')
        basic_auth = ''
        if username:
            basic_auth = '{username}:{password}@'.format(username=username, password=password)
        http_value = None
        https_value = None
        if http_addr:
            http_value = 'http://{basic_auth}{http_addr}'.format(basic_auth=basic_auth, http_addr=http_addr)
        if https_addr:
            https_value = 'https://{basic_auth}{https_addr}'.format(basic_auth=basic_auth, https_addr=https_addr)
        return {'http': http_value, 'https': https_value}


def get_random_user_agent():
    """
    Return a random user agent customised for the platform the user is on.
    """
    browser_list = USER_AGENTS.get(sys.platform, None)
    if not browser_list:
        browser_list = USER_AGENTS['default']
    random_index = randint(0, len(browser_list) - 1)
    return browser_list[random_index]


def get_openlp_user_agent():
    """
    Return the OpenLP user agent
    """
    return 'OpenLP/' + Registry().get('application-qt').applicationVersion()


def get_web_page(url, headers=None, update_openlp=False, proxy=None):
    """
    Attempts to download the webpage at url and returns that page or None.

    :param url: The URL to be downloaded.
    :param dict | None headers:  An optional HTTP header to pass in the request to the web server.
    :param update_openlp: Tells OpenLP to update itself if the page is successfully downloaded. Defaults to False.
    :param dict | ProxyMode | None proxy: ProxyMode enum or a dictionary containing the proxy servers, with their types
        as the key e.g. {'http': 'http://proxyserver:port', 'https': 'https://proxyserver:port'}
    """
    if not url:
        return None
    if not headers:
        headers = {}
    if 'user-agent' not in [key.lower() for key in headers.keys()]:
        headers['User-Agent'] = get_random_user_agent()
    if not isinstance(proxy, dict):
        proxy = get_proxy_settings(mode=proxy)
    log.debug('Downloading URL = %s' % url)
    response = None
    for retries in range(CONNECTION_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, proxies=proxy, timeout=float(CONNECTION_TIMEOUT))
            log.debug('Downloaded page {url}'.format(url=response.url))
            break
        except OSError:
            # For now, catch OSError. All requests errors inherit from OSError
            log.exception('Unable to connect to {url}'.format(url=url))
            if retries >= CONNECTION_RETRIES:
                break
        except:                                                                # noqa
            # Don't know what's happening, so reraise the original
            log.exception('Unknown error when trying to connect to {url}'.format(url=url))
            raise
    if update_openlp:
        Registry().get('application').process_events()
    if not response or not response.text:
        log.error('{url} could not be downloaded'.format(url=url))
        return None
    return response.text


def get_url_file_size(url, proxy=None):
    """
    Get the size of a file.

    :param url: The URL of the file we want to download.
    :param dict | ProxyMode | None proxy: ProxyMode enum or a dictionary containing the proxy servers, with their types
        as the key e.g. {'http': 'http://proxyserver:port', 'https': 'https://proxyserver:port'}
    """
    if not isinstance(proxy, dict):
        proxy = get_proxy_settings(mode=proxy)
    for retries in range(CONNECTION_RETRIES + 1):
        try:
            response = requests.head(url, proxies=proxy, timeout=float(CONNECTION_TIMEOUT), allow_redirects=True)
            return int(response.headers['Content-Length'])
        except OSError:
            if retries >= CONNECTION_RETRIES:
                raise ConnectionError('Unable to download {url}'.format(url=url))
            time.sleep(0.1)


def download_file(update_object, url, file_path, sha256=None, proxy=None):
    """"
    Download a file given a URL.  The file is retrieved in chunks, giving the ability to cancel the download at any
    point. Returns False on download error.

    :param update_object: the object which needs to be updated
    :param url: URL to download
    :param file_path: Destination file
    :param sha256: The check sum value to be checked against the download value
    :param dict | ProxyMode | None proxy: ProxyMode enum or a dictionary containing the proxy servers, with their types
        as the key e.g. {'http': 'http://proxyserver:port', 'https': 'https://proxyserver:port'}
    """
    block_count = 0
    block_size = 4096
    if not isinstance(proxy, dict):
        proxy = get_proxy_settings(mode=proxy)
    log.debug('url_get_file: %s', url)
    for retries in range(CONNECTION_RETRIES + 1):
        try:
            with file_path.open('wb') as saved_file:
                response = requests.get(url, proxies=proxy, timeout=float(CONNECTION_TIMEOUT), stream=True)
                if sha256:
                    hasher = hashlib.sha256()
                # Download until finished or canceled.
                for chunk in response.iter_content(chunk_size=block_size):
                    if hasattr(update_object, 'is_cancelled') and update_object.is_cancelled:
                        break
                    saved_file.write(chunk)
                    if sha256:
                        hasher.update(chunk)
                    block_count += 1
                    if hasattr(update_object, 'update_progress'):
                        update_object.update_progress(block_count, block_size)
                response.close()
            if sha256 and hasher.hexdigest() != sha256:
                log.error('sha256 sums did not match for file %s, got %s, expected %s', file_path, hasher.hexdigest(),
                          sha256)
                if file_path.exists():
                    file_path.unlink()
                return False
            break
        except OSError:
            trace_error_handler(log)
            if retries >= CONNECTION_RETRIES:
                if file_path.exists():
                    file_path.unlink()
                return False
            time.sleep(0.1)
    else:
        if file_path.exists():
            file_path.unlink()
        return False
    if hasattr(update_object, 'is_cancelled') and update_object.is_cancelled and file_path.exists():
        file_path.unlink()
    return True


class DownloadWorker(ThreadWorker):
    """
    This worker allows a file to be downloaded in a thread
    """
    download_failed = QtCore.Signal()
    download_succeeded = QtCore.Signal(Path)

    def __init__(self, base_url, file_name):
        """
        Set up the worker object
        """
        self._base_url = base_url
        self._file_name = file_name
        self.is_cancelled = False
        super().__init__()

    def start(self):
        """
        Download the url to the temporary directory
        """
        if self.is_cancelled:
            self.quit.emit()
            return
        try:
            dest_path = Path(gettempdir()) / 'openlp' / self._file_name
            url = '{url}{name}'.format(url=self._base_url, name=self._file_name)
            is_success = download_file(self, url, dest_path)
            if is_success and not self.is_cancelled:
                self.download_succeeded.emit(dest_path)
            else:
                self.download_failed.emit()
        except Exception:
            log.exception('Unable to download %s', url)
            self.download_failed.emit()
        finally:
            time.sleep(1)
            self.quit.emit()

    @QtCore.Slot()
    def cancel_download(self):
        """
        A slot to allow the download to be cancelled from outside of the thread
        """
        self.is_cancelled = True
