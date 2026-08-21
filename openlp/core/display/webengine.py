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
Subclass of QWebEngineView. Adds some special eventhandling needed for screenshots/previews
Heavily inspired by https://stackoverflow.com/questions/33467776/qt-qwebengine-render-after-scrolling/33576100#33576100
"""
import logging
import os.path
import sys

from PySide6 import QtCore, QtWebEngineCore, QtWebEngineWidgets, QtWidgets
from typing import Tuple

from openlp.core.common import Singleton
from openlp.core.common.applocation import AppLocation
from openlp.core.common.mime import get_mime_type
from openlp.core.common.platform import is_win


LOG_LEVELS = {
    QtWebEngineCore.QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel: logging.INFO,
    QtWebEngineCore.QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel: logging.WARNING,
    QtWebEngineCore.QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel: logging.ERROR
}


log = logging.getLogger(__name__)


class WebEnginePage(QtWebEngineCore.QWebEnginePage):
    """
    A custom WebEngine page to capture Javascript console logging
    """
    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        """
        Override the parent method in order to log the messages in OpenLP
        """
        # The JS log has the entire file location, which we don't really care about
        app_dir = AppLocation.get_directory(AppLocation.AppDir).parent
        if str(app_dir) in source_id:
            source_id = source_id.replace('file://{app_dir}/'.format(app_dir=app_dir), '')
        # Log the JS messages to the Python logger
        log.log(LOG_LEVELS[level], '{source_id}:{line_number} {message}'.format(source_id=source_id,
                                                                                line_number=line_number,
                                                                                message=message))


class WebEngineView(QtWebEngineWidgets.QWebEngineView):
    """
    A sub-classed QWebEngineView to handle paint events of OpenGL (does not seem to work)
    and set some attributtes.
    """
    _child = None  # QtWidgets.QOpenGLWidget or QWidget?
    delegatePaint = QtCore.Signal()

    def __init__(self, parent=None):
        """
        Constructor
        """
        super(WebEngineView, self).__init__(parent)
        self.setPage(WebEnginePage(self))
        self.settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        self.settings().setAttribute(
            QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        self.settings().setAttribute(
            QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.page().settings().setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        self.page().settings().setAttribute(
            QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        self.page().settings().setAttribute(
            QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.PreventContextMenu)

    def eventFilter(self, obj, ev):
        """
        Emit delegatePaint on paint event of the last added QOpenGLWidget child
        """
        if obj == self._child:
            if ev.type() == QtCore.QEvent.Type.MouseButtonPress or ev.type() == QtCore.QEvent.Type.TouchBegin:
                self.display_clicked()
            if ev.type() == QtCore.QEvent.Type.Paint:
                self.delegatePaint.emit()
        return super(WebEngineView, self).eventFilter(obj, ev)

    def display_clicked(self):
        """
        Dummy method to be overridden
        """
        pass

    def event(self, ev):
        """
        Handle events
        """
        if ev.type() == QtCore.QEvent.Type.ChildAdded:
            # Only use QWidget child (used to be QOpenGLWidget)
            w = ev.child()
            if w and isinstance(w, QtWidgets.QWidget):
                self._child = w
                w.installEventFilter(self)
        return super(WebEngineView, self).event(ev)


class LocalSchemeHelper():
    def deny_access(self, request: QtWebEngineCore.QWebEngineUrlRequestJob, url: str, real_path: str):
        log.exception('{request} denied. Real Path: {path}'.format(request=url,
                                                                   path=real_path))
        request.fail(QtWebEngineCore.QWebEngineUrlRequestJob.Error.RequestDenied)

    def not_found(self, request: QtWebEngineCore.QWebEngineUrlRequestJob, url: str, real_path: str):
        log.exception('{request} not found. Real Path: {path}'.format(request=url,
                                                                      path=real_path))
        request.fail(QtWebEngineCore.QWebEngineUrlRequestJob.Error.UrlNotFound)

    def exception(self, request: QtWebEngineCore.QWebEngineUrlRequestJob, url: str, exception: Exception):
        log.exception('{request} failed: {error:d}; {message}'.format(request=url, error=str(type(exception)),
                                                                      message=str(exception)))
        request.fail(QtWebEngineCore.QWebEngineUrlRequestJob.Error.RequestFailed)

    def invalid(self, request: QtWebEngineCore.QWebEngineUrlRequestJob, url: str):
        log.exception('{request} is invalid.'.format(request=url))
        request.fail(QtWebEngineCore.QWebEngineUrlRequestJob.Error.UrlInvalid)

    def reply_file(self, request: QtWebEngineCore.QWebEngineUrlRequestJob, path: str) -> Tuple[QtCore.QBuffer, str]:
        raw_html = open(path, 'rb').read()
        buffer = QtCore.QBuffer(self)
        buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        buffer.write(raw_html)
        buffer.seek(0)
        buffer.close()
        mime_type = get_mime_type(path)
        request.reply(bytes(mime_type, 'utf-8'), buffer)

    def request_path_to_file(self, base_path: str, url_path: str):
        if is_win() and not base_path:
            while len(url_path) > 0 and url_path[0] == '/':
                url_path = url_path[1:]
        return os.path.realpath(base_path + os.path.normpath(url_path))


class OpenLPSchemeHandler(QtWebEngineCore.QWebEngineUrlSchemeHandler, LocalSchemeHelper):
    def __init__(self, root_paths, parent):
        super().__init__(parent)
        self.root_paths = {base_path: os.path.realpath(value) for base_path, value in root_paths.items()}

    def requestStarted(self, request: QtWebEngineCore.QWebEngineUrlRequestJob) -> None:
        url = request.requestUrl()
        try:
            request_base_key = url.host()
            # Checking root to forbid relative path attacks
            base_real_path = self.root_paths[request_base_key]
            request_real_path = self.request_path_to_file(base_real_path, url.path())
            if not request_real_path.startswith(base_real_path):
                return self.deny_access(request, url, request_real_path)
            if not os.path.exists(request_real_path):
                return self.not_found(request, url, request_real_path)
            self.reply_file(request, request_real_path)
            return
        except Exception as exception:
            self.exception(request, url, exception)


class OpenLPLibrarySchemeHandler(QtWebEngineCore.QWebEngineUrlSchemeHandler, LocalSchemeHelper):
    def __init__(self, parent):
        super().__init__(parent)

    def requestStarted(self, request: QtWebEngineCore.QWebEngineUrlRequestJob) -> None:
        url = request.requestUrl()
        try:
            request_base_key = url.host()
            if request_base_key == 'local-file':
                # Checking root to forbid relative path attacks
                request_real_path = self.request_path_to_file('', url.path())
                if not os.path.exists(request_real_path):
                    return self.not_found(request, url, request_real_path)
                return self.reply_file(request, request_real_path)
            return self.invalid(request, url)
        except Exception as exception:
            self.exception(request, url, exception)


class WebViewCustomScheme(QtCore.QObject):
    """
    Allows the registering of custom protocols inside WebView. Can be used mainly for
    circumventing default security measures placed on http(s):// or file:// protocols.
    """

    def __init__(self, parent):
        super().__init__(parent)
        scheme = QtWebEngineCore.QWebEngineUrlScheme(self.scheme_name)
        scheme.setSyntax(QtWebEngineCore.QWebEngineUrlScheme.Syntax.Host)
        self.set_scheme_flags(scheme)
        QtWebEngineCore.QWebEngineUrlScheme.registerScheme(scheme)

    def set_scheme_flags(self, scheme: QtWebEngineCore.QWebEngineUrlScheme):
        scheme.setFlags(QtWebEngineCore.QWebEngineUrlScheme.Flag.CorsEnabled
                        | QtWebEngineCore.QWebEngineUrlScheme.Flag.ContentSecurityPolicyIgnored
                        | QtWebEngineCore.QWebEngineUrlScheme.Flag.SecureScheme
                        | QtWebEngineCore.QWebEngineUrlScheme.Flag.LocalScheme
                        | QtWebEngineCore.QWebEngineUrlScheme.Flag.LocalAccessAllowed)

    def create_scheme_handler(self) -> QtWebEngineCore.QWebEngineUrlSchemeHandler:
        raise Exception('Needs to be implemented.')

    def init_handler(self, profile=None):
        if profile is None:
            profile = QtWebEngineCore.QWebEngineProfile.defaultProfile()
        handler = profile.urlSchemeHandler(self.scheme_name)
        if handler is not None:
            profile.removeUrlSchemeHandler(handler)
        self.handler = self.create_scheme_handler()
        profile.installUrlSchemeHandler(self.scheme_name, self.handler)


class OpenLPScheme(WebViewCustomScheme):
    scheme_name = b'openlp'

    def __init__(self, root_paths, parent=None):
        super().__init__(parent)
        self.root_paths = root_paths

    def create_scheme_handler(self):
        return OpenLPSchemeHandler(self.root_paths, self)

    def set_root_path(self, base: str, path: str):
        if hasattr(self, 'handler'):
            self.handler.root_paths[base] = path
        self.root_paths[base] = path


# Allows to circumvent default file-on-HTTP restrictions and/or provide remote/non-local file locations.
class OpenLPLibraryScheme(WebViewCustomScheme):
    scheme_name = b'openlp-library'

    def __init__(self, parent=None):
        super().__init__(parent)

    def set_scheme_flags(self, scheme: QtWebEngineCore.QWebEngineUrlScheme):
        scheme.setFlags(QtWebEngineCore.QWebEngineUrlScheme.Flag.ContentSecurityPolicyIgnored)

    def create_scheme_handler(self):
        return OpenLPLibrarySchemeHandler(self)


def init_webview_custom_schemes():
    """
    This inits the custom scheme protocols used in OpenLP WebEngines. It must happen before
    QApplication instantiation.
    """
    app_dir = AppLocation.get_directory(AppLocation.AppDir)
    display_path_candidates = [app_dir / 'core' / 'display' / 'html']
    if getattr(sys, 'frozen', False):
        display_path_candidates.append(app_dir.parent / 'Resources' / 'openlp' / 'core' / 'display' / 'html')
    openlp_root_paths = {
        "display": next((path for path in display_path_candidates if path.is_dir()), display_path_candidates[0])
    }
    # openlp:// protocol
    WebViewSchemes().register_scheme(OpenLPScheme(openlp_root_paths))
    # openlp-library:// protocol
    WebViewSchemes().register_scheme(OpenLPLibraryScheme())


def set_webview_display_path(path):
    scheme = WebViewSchemes().get_scheme(OpenLPScheme.scheme_name)
    if (scheme):
        scheme.set_root_path('display', path)


class WebViewSchemes(metaclass=Singleton):
    def __init__(self) -> None:
        self._registered_schemes = {}

    def get_scheme(self, name) -> WebViewCustomScheme:
        if isinstance(name, bytes):
            name = name.decode('utf-8')
        return self._registered_schemes[name] if name in self._registered_schemes else None

    def register_scheme(self, scheme: WebViewCustomScheme):
        name = scheme.scheme_name
        if isinstance(name, bytes):
            name = name.decode('utf-8')
        self._registered_schemes[name] = scheme
