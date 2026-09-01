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
Provide Error Handling and login Services
"""
import inspect
import logging

from openlp.core.common import trace_error_handler
from openlp.core.common.platform import is_win
from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings


DO_NOT_TRACE_EVENTS = ['timerEvent', 'paintEvent', 'drag_enter_event', 'drop_event', 'on_controller_size_changed',
                       'preview_size_changed', 'resizeEvent', 'eventFilter', 'tick', 'resize', 'update_ui',
                       'get_time']


class LogMixin(object):
    """
    Base Calling object for OpenLP classes.
    """
    @property
    def logger(self):
        if hasattr(self, '_logger') and self._logger:
            return self._logger
        else:
            self._logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))
            if self._logger.getEffectiveLevel() == logging.DEBUG:
                for name, m in inspect.getmembers(self, inspect.ismethod):
                    if name not in DO_NOT_TRACE_EVENTS:
                        if not name.startswith("_") and not name.startswith("log"):
                            setattr(self, name, self.logging_wrapper(m, self))
            return self._logger

    @staticmethod
    def logging_wrapper(func, parent):
        """
        Code to added debug wrapper to work on called functions within a decorated class.
        """
        def wrapped(*args, **kwargs):
            parent.logger.debug("Entering {function}".format(function=func.__name__))
            try:
                if len(inspect.signature(func).parameters.values()):
                    return func(*args, **kwargs)
                else:
                    return func(*args)
            except Exception as e:
                if parent.logger.getEffectiveLevel() <= logging.ERROR:
                    parent.logger.error('Exception in {function} : {error}'.format(function=func.__name__,
                                                                                   error=e))
                raise e
        return wrapped

    def log_debug(self, message):
        """
        Common log debug handler
        """
        self.logger.debug(message)

    def log_info(self, message):
        """
        Common log info handler
        """
        self.logger.info(message)

    def log_warning(self, message):
        """
        Common log warning handler
        """
        self.logger.warning(message)

    def log_error(self, message):
        """
        Common log error handler which prints the calling path
        """
        trace_error_handler(self.logger)
        self.logger.error(message)

    def log_exception(self, message):
        """
        Common log exception handler which prints the calling path
        """
        trace_error_handler(self.logger)
        self.logger.exception(message)


class RegistryProperties(object):
    """
    This adds registry components to classes to use at run time.
    """
    _application = None
    _plugin_manager = None
    _media_controller = None
    _service_manager = None
    _preview_controller = None
    _live_controller = None
    _main_window = None
    _renderer = None
    _theme_manager = None
    _settings_form = None
    _alerts_manager = None
    _projector_manager = None
    _settings = None

    @property
    def application(self):
        """
        Adds the openlp to the class dynamically.
        Windows needs to access the application in a dynamic manner.
        """
        if is_win():
            return Registry().get('application')
        else:
            if not hasattr(self, '_application') or not self._application:
                self._application = Registry().get('application')
            return self._application

    @property
    def plugin_manager(self):
        """
        Adds the plugin manager to the class dynamically
        """
        if not hasattr(self, '_plugin_manager') or not self._plugin_manager:
            self._plugin_manager = Registry().get('plugin_manager')
        return self._plugin_manager

    @property
    def media_controller(self):
        """
        Adds the media controller to the class dynamically
        """
        if not hasattr(self, '_media_controller') or not self._media_controller:
            self._media_controller = Registry().get('media_controller')
        return self._media_controller

    @property
    def service_manager(self):
        """
        Adds the service manager to the class dynamically
        """
        if not hasattr(self, '_service_manager') or not self._service_manager:
            self._service_manager = Registry().get('service_manager')
        return self._service_manager

    @property
    def preview_controller(self):
        """
        Adds the preview controller to the class dynamically
        """
        if not hasattr(self, '_preview_controller') or not self._preview_controller:
            self._preview_controller = Registry().get('preview_controller')
        return self._preview_controller

    @property
    def live_controller(self):
        """
        Adds the live controller to the class dynamically
        """
        if not hasattr(self, '_live_controller') or not self._live_controller:
            self._live_controller = Registry().get('live_controller')
        return self._live_controller

    @property
    def main_window(self):
        """
        Adds the main window to the class dynamically
        """
        if not hasattr(self, '_main_window') or not self._main_window:
            self._main_window = Registry().get('main_window')
        return self._main_window

    @property
    def renderer(self):
        """
        Adds the Renderer to the class dynamically
        """
        if not hasattr(self, '_renderer') or not self._renderer:
            self._renderer = Registry().get('renderer')
        return self._renderer

    @property
    def theme_manager(self):
        """
        Adds the theme manager to the class dynamically
        """
        if not hasattr(self, '_theme_manager') or not self._theme_manager:
            self._theme_manager = Registry().get('theme_manager')
        return self._theme_manager

    @property
    def settings_form(self):
        """
        Adds the settings form to the class dynamically
        """
        if not hasattr(self, '_settings_form') or not self._settings_form:
            self._settings_form = Registry().get('settings_form')
        return self._settings_form

    @property
    def alerts_manager(self):
        """
        Adds the alerts manager to the class dynamically
        """
        if not hasattr(self, '_alerts_manager') or not self._alerts_manager:
            self._alerts_manager = Registry().get('alerts_manager')
        return self._alerts_manager

    @property
    def projector_manager(self):
        """
        Adds the projector manager to the class dynamically
        """
        if not hasattr(self, '_projector_manager') or not self._projector_manager:
            self._projector_manager = Registry().get('projector_manager')
        return self._projector_manager

    @property
    def settings(self) -> Settings:
        """
        Adds the settings object to the class dynamically
        """
        if not hasattr(self, '_settings') or not self._settings:
            self._settings = Registry().get('settings')
        return self._settings
