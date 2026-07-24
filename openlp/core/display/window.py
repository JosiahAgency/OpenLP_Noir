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
The :mod:`~openlp.core.display.window` module contains the display window
"""
import json
import logging
import os
import copy
import re
import time

from PySide6 import QtCore, QtWebChannel, QtWidgets

from openlp.core.common.enum import ServiceItemType
from openlp.core.common.i18n import translate
from openlp.core.common.mixins import LogMixin, RegistryProperties
from openlp.core.common.path import path_to_str
from openlp.core.common.platform import is_win, is_macosx
from openlp.core.common.registry import Registry
from openlp.core.common.utils import wait_for
from openlp.core.display.screens import ScreenList
from openlp.core.ui import HideMode


FONT_FOUNDRY = re.compile(r'(.*?) \[(.*?)\]')
TRANSITION_END_EVENT_NAME = 'transparent_transition_end'
log = logging.getLogger(__name__)


class DisplayWatcher(QtCore.QObject):
    """
    This facilitates communication from the Display object in the browser back to the Python
    """
    initialised = QtCore.Signal(bool)

    def __init__(self, parent, window_title=None):
        super().__init__()
        self._display_window = parent
        self._transient_dispatch_events = {}
        self._permanent_dispatch_events = {}
        self._event_counter = 0
        self._window_title = window_title

    @QtCore.Slot(result=str)
    def getWindowTitle(self):
        return self._window_title

    @QtCore.Slot(bool)
    def setInitialised(self, is_initialised):
        """
        This method is called from the JS in the browser to set the _is_initialised attribute
        """
        log.info('Display is initialised: {init}'.format(init=is_initialised))
        self.initialised.emit(is_initialised)

    @QtCore.Slot()
    def pleaseRepaint(self):
        """
        Called from the js in the webengine view when it's requesting a repaint by Qt
        """
        self._display_window.webview.update()

    @QtCore.Slot(str, QtCore.QJsonValue)
    def dispatchEvent(self, event_name: str, event_data: QtCore.QJsonValue):
        """
        Called from the js in the webengine view for event dispatches
        """
        transient_dispatch_events = self._transient_dispatch_events
        permanent_dispatch_events = self._permanent_dispatch_events
        if event_name in transient_dispatch_events:
            event = transient_dispatch_events[event_name]
            del transient_dispatch_events[event_name]
            event(event_data)
        if event_name in permanent_dispatch_events:
            permanent_dispatch_events[event_name](event_data)

    def register_event_listener(self, event_name, callback, transient=True):
        """
        Register an event listener from webengine view
        :param event_name: Event name
        :param callback: Callback listener when event happens
        :param transient: If the event listener should be unregistered after being run
        """
        if transient:
            events = self._transient_dispatch_events
        else:
            events = self._permanent_dispatch_events

        events[event_name] = callback

    def unregister_event_listener(self, event_name, transient=True):
        """
        Unregisters an event listener from webengine view
        :param event_name: Event name
        :param transient: If the event listener was registered as transient
        """
        if transient:
            events = self._transient_dispatch_events
        else:
            events = self._permanent_dispatch_events

        if event_name in events:
            del events[event_name]

    def get_unique_event_name(self):
        """
        Generates an unique event name
        :returns: Unique event name
        """
        event_count = self._event_counter
        self._event_counter += 1
        return 'event_' + str(event_count)


class DisplayWindow(QtWidgets.QWidget, RegistryProperties, LogMixin):
    """
    This is a window to show the output
    """
    def __init__(self, parent=None, screen=None, can_show_startup_screen=True, start_hidden=False,
                 after_loaded_callback=None, window_title=None):
        """
        Create the display window
        """
        super(DisplayWindow, self).__init__(parent)
        # Scripts must not be injected into the page before it has loaded (requestAction()
        # would not exist yet), so they are queued and run from after_loaded() instead.
        self._is_page_loaded = False
        self._pending_javascript = []
        self.after_loaded_callback = after_loaded_callback
        # Gather all flags for the display window
        flags = QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool |\
            QtCore.Qt.WindowType.WindowStaysOnTopHint
        if self.settings.value('advanced/x11 bypass wm'):
            flags |= QtCore.Qt.WindowType.X11BypassWindowManagerHint
        else:
            # This helps the window not being hidden by KDE's "Hide utility windows for inactive applications" option
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_X11NetWmWindowTypeDialog)
        if is_macosx():
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)
        self._is_initialised = False
        self._is_manual_close = False
        self._can_show_startup_screen = can_show_startup_screen
        self._fbo = None
        self.window_title = window_title
        self.setWindowTitle(translate('OpenLP.DisplayWindow', 'Display Window'))
        self.setWindowFlags(flags)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.webview = self.init_webengine()
        self.webview.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.webview.page().setBackgroundColor(QtCore.Qt.GlobalColor.transparent)
        self.webview.display_clicked = self.disable_display
        self.layout.addWidget(self.webview)
        self.webview.loadFinished.connect(self.after_loaded)
        self.channel = QtWebChannel.QWebChannel(self)
        if not window_title and screen and screen.is_display:
            window_title = 'Display Window'
        self.display_watcher = DisplayWatcher(self, window_title)
        self.channel.registerObject('displayWatcher', self.display_watcher)
        self.webview.page().setWebChannel(self.channel)
        self.display_watcher.initialised.connect(self.on_initialised)
        self.display_watcher.register_event_listener("runJavascriptCallback", self.handle_javascript_result, False)
        self.openlp_splash_screen_path = 'openlp://display/openlp-splash-screen.png'
        # Using custom display if provided
        if Registry().has('display_custom_url') and Registry().get('display_custom_url') is not None:
            display_custom_url = Registry().get('display_custom_url')
            self.display_path = display_custom_url + '/display.html'
            self.checkerboard_path = display_custom_url + '/checkerboard.png'
            qUrl = QtCore.QUrl(display_custom_url)
        else:
            self.display_path = 'openlp://display/display.html'
            self.checkerboard_path = 'openlp://display/checkerboard.png'
            qUrl = QtCore.QUrl(self.display_path)
        self.set_url(qUrl)
        self.is_display = False
        self.scale = 1
        self.hide_mode = None
        self.__script_done = True
        self.__script_result = None
        self._last_theme_json = None
        if screen and screen.is_display:
            # use log_debug to set up function wrapping before registering functions
            self.log_debug('registering live display show/hide functions')
            Registry().register_function('live_display_hide', self.hide_display)
            Registry().register_function('live_display_show', self.show_display)
            self.update_from_screen(screen)
            self.is_display = True
            # Only make visible on single monitor setup if setting enabled.
            if not start_hidden and (len(ScreenList()) > 1 or self.settings.value('core/display on monitor')):
                self.auto_show(screen.custom_geometry is not None)

    def closeEvent(self, event):
        """
        Override the closeEvent method to prevent the window from being closed by the user
        """
        if not self._is_manual_close:
            event.ignore()

    def init_webengine(self):
        # Need to import this inline to get around a QtWebEngine issue
        from openlp.core.display.webengine import WebEngineView, WebViewSchemes, OpenLPScheme, OpenLPLibraryScheme
        webview = WebEngineView(self)
        profile = webview.page().profile()
        WebViewSchemes().get_scheme(OpenLPScheme.scheme_name).init_handler(profile)
        WebViewSchemes().get_scheme(OpenLPLibraryScheme.scheme_name).init_handler(profile)

        return webview

    def _fix_font_name(self, font_name):
        """
        Do some font machinations to see if we can fix the font name
        """
        # Some fonts on Windows that end in "Bold" are made into a base font that is bold
        if is_win() and font_name.endswith(' Bold'):
            font_name = font_name.split(' Bold')[0]
        # Some fonts may have the Foundry name in their name. Remove the foundry name
        match = FONT_FOUNDRY.match(font_name)
        if match:
            font_name = match.group(1)
        return font_name

    def deregister_display(self):
        """
        De-register this displays callbacks in the registry to be able to remove it
        """
        if self.is_display:
            Registry().remove_function('live_display_hide', self.hide_display)
            Registry().remove_function('live_display_show', self.show_display)
        self._is_manual_close = True

    @property
    def is_initialised(self):
        return self._is_initialised

    def on_initialised(self, is_initialised):
        """
        Update the initialised status
        """
        self._is_initialised = is_initialised

    def update_from_screen(self, screen):
        """
        Update the number and the geometry from the screen.

        :param Screen screen: A `~openlp.core.display.screens.Screen` instance
        """
        self.setGeometry(screen.display_geometry)
        self.screen_number = screen.number

    def auto_show(self, has_custom_geometry: bool):
        """
        Displays the window using the fullscreen function if using the whole screen (allows drawing over system UI)

        :param bool has_custom_geometry: Whether the display a custom geometry
        """

        if has_custom_geometry:
            self.show()
        else:
            self.showFullScreen()

    def set_background_image(self, image_path):
        image_uri = image_path.as_uri()
        self.run_in_display('setBackgroundImage', image_uri)

    def set_single_image(self, bg_color, image_path):
        """
        :param str bg_color: Background color
        :param Path image_path: Path to the image
        """
        image_uri = image_path.as_uri()
        self.run_in_display('setFullscreenImage', bg_color, image_uri)

    def set_single_image_data(self, bg_color, image_data):
        self.run_in_display('setFullscreenImageFromData', bg_color, image_data)

    def set_startup_screen(self):
        bg_color = self.settings.value('core/logo background color')
        image = self.settings.value('core/logo file')
        if path_to_str(image).startswith(':'):
            image_uri = self.openlp_splash_screen_path
        else:
            try:
                image_uri = image.as_uri().replace('file://', 'openlp-library://local-file/')
            except Exception:
                image_uri = ''
        # if set to hide logo on startup, do not send the logo
        if self.settings.value('core/logo hide on startup'):
            image_uri = ''
        self.run_in_display('setStartupSplashScreen', bg_color, image_uri)

    def set_url(self, url):
        """
        Set the URL of the webview

        :param QtCore.QUrl | str url: The URL to set
        """
        if not isinstance(url, QtCore.QUrl):
            url = QtCore.QUrl(url)
        self._is_page_loaded = False
        self.webview.setUrl(url)

    def set_html(self, html):
        """
        Set the html
        """
        self._is_page_loaded = False
        self.webview.setHtml(html)

    def after_loaded(self):
        """
        Add stuff after page initialisation
        """
        self._is_page_loaded = True
        # The page has (re)loaded, so any theme sent previously is gone from the JS side
        self._last_theme_json = None
        item_transitions = self.settings.value('themes/item transitions')
        hide_mouse = (self.settings.value('advanced/hide mouse') and self.is_display)
        slide_numbers_in_footer = self.settings.value('advanced/slide numbers in footer')
        self.run_in_display('init', {
                            'isDisplay': self.is_display,
                            'doItemTransitions': item_transitions,
                            'slideNumbersInFooter': slide_numbers_in_footer,
                            'hideMouse': hide_mouse,
                            'displayTitle': self.window_title
                            })
        wait_for(lambda: self._is_initialised)
        if self.scale != 1:
            self.set_scale(self.scale)
        if self._can_show_startup_screen:
            self.set_startup_screen()
        # Run any scripts that were requested before the page had loaded, in their original
        # order, now that requestAction() exists and the display has been initialised.
        if self._pending_javascript:
            pending_javascript = self._pending_javascript
            self._pending_javascript = []
            log.debug('display page loaded, running %d queued script(s)', len(pending_javascript))
            for script in pending_javascript:
                self._run_javascript(script)
        if self.after_loaded_callback:
            self.after_loaded_callback()

    def run_in_display(self, action, *parameters, raw_parameters=None, is_sync=False, return_event_name=None):
        if len(parameters):
            raw_parameters = ''
            first = True
            for parameter in parameters:
                if not first:
                    raw_parameters += ', '
                else:
                    first = False
                raw_parameters += json.dumps(parameter)
        action_name = 'requestAction'
        action_async = ''
        if return_event_name:
            action_name = 'requestActionAsync'
            action_async = ', \'{event_name}\''.format(event_name=return_event_name)
        if not raw_parameters:
            return self._run_javascript('{action_name}(\'{action}\'{action_async})'.format(action_name=action_name,
                                                                                           action=action,
                                                                                           action_async=action_async),
                                        is_sync)
        else:
            return self._run_javascript('{action_name}(\'{action}\'{action_async}, {raw_parameters})'
                                        .format(action_name=action_name, action=action, action_async=action_async,
                                                raw_parameters=raw_parameters),
                                        is_sync)

    def _run_javascript(self, script, is_sync=False):
        """
        Run some Javascript in the WebView

        :param script: The script to run, a string
        :param is_sync: Run the script synchronously. Defaults to False
        """
        log.debug((script[:80] + '..') if len(script) > 80 else script)
        if not self._is_page_loaded:
            # The page has not finished loading, so requestAction() does not exist yet and
            # injecting the script now would throw "ReferenceError: requestAction is not
            # defined" inside the page and the action would be silently lost.
            if not is_sync:
                log.debug('display page not loaded yet, queueing script: %s',
                          (script[:60] + '..') if len(script) > 60 else script)
                self._pending_javascript.append(script)
                return
            if not wait_for(lambda: self._is_page_loaded,
                            error_message='Timed out waiting for the display page to load'):
                return None
        # Wait for previous scripts to finish
        wait_for(lambda: self.__script_done)
        if is_sync:
            start_time = time.perf_counter()
            self.__script_done = False
            self.__script_result = None
            self.webview.page().runJavaScript(
                "window.displayWatcher.dispatchEvent(\"runJavascriptCallback\", " + script + ")")
            # Wait for script to finish
            if not wait_for(lambda: self.__script_done):
                self.__script_done = True
            log.debug('sync javascript timing: %.1f ms for %s',
                      (time.perf_counter() - start_time) * 1000,
                      (script[:60] + '..') if len(script) > 60 else script)
            return self.__script_result
        else:
            self.webview.page().runJavaScript(script)
        self.raise_()

    @QtCore.Slot()
    def handle_javascript_result(self, result):
        """
        Handle the result from the asynchronous call
        """
        # Depending on the PySide6 version the web channel may deliver a QJsonValue instead of a
        # plain Python value. A QJsonValue object is always truthy, which (amongst others) broke
        # the doesContentFit check and stopped slides from ever being split. Unwrap it.
        if isinstance(result, QtCore.QJsonValue):
            result = result.toVariant()
        self.__script_result = result
        self.__script_done = True

    def go_to_slide(self, verse):
        """
        Go to a particular slide.

        :param str verse: The verse to go to, e.g. "V1" for songs, or just "0" for other types
        """
        self.run_in_display('goToSlide', verse)

    def load_verses(self, verses, is_sync=False):
        """
        Set verses in the display
        """
        self.run_in_display('setTextSlides', verses, is_sync=is_sync)

    def load_images(self, images):
        """
        Set images in the display
        """
        imagesr = copy.deepcopy(images)
        for image in imagesr:
            image['path'] = image['path'].as_uri()
            # Not all images has a dedicated thumbnail (such as images loaded from old or local servicefiles),
            # in that case reuse the image
            if image.get('thumbnail', None):
                image['thumbnail'] = image['thumbnail'].as_uri()
            else:
                image['thumbnail'] = image['path']
        self.run_in_display('setImageSlides', imagesr)

    def save_screenshot(self, fname=None):
        """
        Save a screenshot, either returning it or saving it to file
        """
        pixmap = self.grab()
        if fname:
            ext = os.path.splitext(fname)[-1][1:]
            pixmap.save(fname, ext)
        else:
            return pixmap

    def set_theme(self, theme, is_sync=False, service_item_type=False):
        """
        Set the theme of the display
        """
        theme_copy = copy.deepcopy(theme)
        if self.is_display:
            if service_item_type == ServiceItemType.Text:
                if theme.background_type == 'video' or theme.background_type == 'stream':
                    theme_copy.background_type = 'transparent'
        else:
            # If preview Display with media background we just show the background color, no media
            if theme.background_type == 'stream' or theme.background_type == 'video':
                theme_copy.background_type = 'solid'
                theme_copy.background_start_color = theme.background_border_color
                theme_copy.background_end_color = theme.background_border_color
                theme_copy.background_main_color = theme.background_border_color
                theme_copy.background_footer_color = theme.background_border_color
                theme_copy.background_color = theme.background_border_color
            # If preview Display for media so we need to display black box.
            elif service_item_type == ServiceItemType.Command or theme.background_type == 'live':
                theme_copy.background_type = 'solid'
                theme_copy.background_start_color = '#590909'
                theme_copy.background_end_color = '#590909'
                theme_copy.background_main_color = '#090909'
                theme_copy.background_footer_color = '#090909'
        # Do some font-checking, see https://gitlab.com/openlp/openlp/-/issues/39
        theme_copy.font_main_name = self._fix_font_name(theme.font_main_name)
        theme_copy.font_footer_name = self._fix_font_name(theme.font_footer_name)
        exported_theme = theme_copy.export_theme(is_js=True)
        if exported_theme == self._last_theme_json:
            # The display already has this exact theme. Resending it would make the JS side
            # re-apply it on the next slide load (and cost a round trip), so skip it. This
            # matters for pagination, where the theme is sent once per formatted slide.
            log.debug('set_theme: theme unchanged, not resending to the display')
            return
        self._last_theme_json = exported_theme
        self.run_in_display('setTheme', raw_parameters=exported_theme, is_sync=is_sync)

    def reload_theme(self):
        """
        Applies the set theme
        DO NOT use this when changing slides. Only use this if you need to force an update
        to the current visible slides.
        """
        self.run_in_display('resetTheme')

    def get_video_types(self):
        """
        Get the types of videos playable by the embedded media player
        """
        return self.run_in_display('getVideoTypes', is_sync=True)

    def show_display(self):
        """
        Show the display
        """
        log.debug('show_display (%s): previous hide_mode=%s, window hidden=%s, page loaded=%s',
                  self.window_title, self.hide_mode, self.isHidden(), self._is_page_loaded)
        if self.is_display:
            # Only make visible on single monitor setup if setting enabled.
            if len(ScreenList()) == 1 and not self.settings.value('core/display on monitor'):
                log.debug('show_display (%s): ignored, single screen setup without "display on monitor"',
                          self.window_title)
                return
        # Aborting setVisible(False) call in case the display modes are changed quickly
        self.display_watcher.unregister_event_listener(TRANSITION_END_EVENT_NAME)
        if self.isHidden():
            self.setVisible(True)
        self.run_in_display('show')
        self.hide_mode = None

    def hide_display(self, mode=HideMode.Screen):
        """
        Hide the display by making all layers transparent Store the images so they can be replaced when required

        :param mode: How the screen is to be hidden
        """
        log.debug('hide_display (%s): requested mode=%s, previous hide_mode=%s, window hidden=%s, page loaded=%s',
                  self.window_title, mode, self.hide_mode, self.isHidden(), self._is_page_loaded)
        if self.is_display:
            # Only make visible on single monitor setup if setting enabled.
            if len(ScreenList()) == 1 and not self.settings.value('core/display on monitor'):
                log.debug('hide_display (%s): ignored, single screen setup without "display on monitor"',
                          self.window_title)
                return
        # Aborting setVisible(False) call in case the display modes are changed quickly
        self.display_watcher.unregister_event_listener(TRANSITION_END_EVENT_NAME)
        # Update display to the selected mode
        if mode != HideMode.Screen:
            if self.isHidden():
                self.setVisible(True)
        if mode == HideMode.Screen:
            if self.settings.value('advanced/disable transparent display'):
                # Hide window only after all webview CSS ransitions are done
                log.debug('hide_display (%s): hiding the window once the transparent transition ends',
                          self.window_title)
                self.display_watcher.register_event_listener(TRANSITION_END_EVENT_NAME,
                                                             self._hide_window_after_transparent_transition)
                self.run_in_display('toTransparent', return_event_name=TRANSITION_END_EVENT_NAME)
            else:
                self.run_in_display('toTransparent')
        elif mode == HideMode.Blank:
            self.run_in_display('toBlack')
        elif mode == HideMode.Theme:
            self.run_in_display('toTheme')
        self.hide_mode = mode

    def _hide_window_after_transparent_transition(self, _event_data=None):
        """
        Called via the display watcher once the JS toTransparent transition has finished,
        so that the (now fully transparent) window can be taken off the screen.
        """
        log.debug('hide_display (%s): transparent transition finished, hiding the window', self.window_title)
        self.setVisible(False)

    def disable_display(self):
        """
        Removes the display if showing desktop
        This allows users to click though the screen even if the screen is only transparent
        """
        if self.is_display and self.hide_mode == HideMode.Screen:
            self.setVisible(False)

    def finish_with_current_item(self):
        """
        This is called whenever the song/image display is followed by eg a presentation or video which
        has its own display.
        This function ensures that the current item won't flash momentarily when the webengineview
        is displayed for a subsequent song or image.
        """
        self.run_in_display('finishWithCurrentItem', is_sync=True)
        self.webview.update()

    def set_scale(self, scale):
        """
        Set the HTML scale
        """
        self.scale = scale
        # Only scale if initialised (scale run again once initialised)
        if self._is_initialised:
            self.run_in_display('setScale', scale * 100)

    def alert(self, text, settings):
        """
        Set an alert
        """
        # json.dumps the text so quotes and backslashes survive the round trip
        # into Javascript
        self._run_javascript('Display.alert({text}, {settings});'.format(text=json.dumps(text), settings=settings))

    def hide_alert(self):
        """
        Hide the currently showing alert, playing its exit animation
        """
        self._run_javascript('Display.hideAlert();')

    @QtCore.Slot(result='QPixmap')
    def _grab_screenshot_safe_signal(self):
        return self.save_screenshot()

    def grab_screenshot_safe(self):
        # Using internal Qt's messaging/event system to invoke the function.
        return QtCore.QMetaObject.invokeMethod(self, '_grab_screenshot_safe_signal',
                                               QtCore.Qt.ConnectionType.AutoConnection,
                                               QtCore.Q_RETURN_ARG('QPixmap'))
