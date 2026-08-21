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
Provide Registry Services
"""
import logging
from typing import Any, Callable
from warnings import warn

from openlp.core.common import Singleton, de_hump, trace_error_handler


log = logging.getLogger(__name__)


class Registry(metaclass=Singleton):
    """
    This is the Component Registry.  It is a singleton object and is used to provide a look up service for common
    objects.
    """
    log.info('Registry loaded')

    # Try to get around the AttributeError in tests
    functions_list = {}

    @classmethod
    def create(cls) -> 'Registry':
        """
        The constructor for the component registry providing a single registry of objects.
        """
        log.info('Registry Initialising')
        registry = cls()
        registry.service_list = {}
        registry.functions_list = {}
        registry.working_flags = {}
        registry._is_suppressing = False
        return registry

    def toggle_suppressing(self) -> None:
        """
        Switch error message suppression during initialisation
        """
        self._is_suppressing = not self._is_suppressing

    def get(self, key: str) -> Any | None:
        """
        Extracts the registry value from the list based on the key passed in

        :param key: The service to be retrieved.
        """
        service_list = getattr(self, 'service_list', {})
        if key in service_list:
            return service_list[key]
        elif getattr(self, '_is_suppressing', False):
            return None
        else:
            warn(f'Service "{key}" not found in list', stacklevel=2)
            return None

    def register(self, key: str, reference: Any):
        """
        Registers a component against a key.

        :param key: The service to be created this is usually a major class like "renderer" or "main_window" .
        :param reference: The service address to be saved.
        """
        log.debug(f'Registering object {key}')
        if key in self.service_list:
            trace_error_handler(log)
            log.error('Duplicate service exception {key}'.format(key=key))
            raise KeyError('Duplicate service exception {key}'.format(key=key))
        else:
            self.service_list[key] = reference

    def remove(self, key: str):
        """
        Removes the registry value from the list based on the key passed in.

        :param key: The service to be deleted.
        """
        if key in self.service_list:
            del self.service_list[key]

    def register_function(self, event: str, function: Callable):
        """
        Register an event and associated function to be called

        :param event:  The function description like "live_display_hide" where a number of places in the code
            will/may need to respond to a single action and the caller does not need to understand or know about the
            recipients.
        :param function: The function to be called when the event happens.
        """
        log.debug(f'Registering event {event}')
        if event in self.functions_list:
            self.functions_list[event].append(function)
        else:
            self.functions_list[event] = [function]

    def remove_function(self, event: str, function: Callable):
        """
        Remove an event and associated handler

        :param event: The function description..
        :param function: The function to be called when the event happens.
        """
        if event in self.functions_list and function in self.functions_list[event]:
            self.functions_list[event].remove(function)

    def has_function(self, event: str) -> bool:
        """
        Returns whether there's any handler associated with the event.

        :param event: The function to be checked
        """
        return event in self.functions_list

    def has(self, service_name: str) -> bool:
        """
        Returns whether there's any service registered with provided name

        :param service_name: The service name to be checked
        """
        return service_name in self.service_list

    def execute(self, event: str, *args, **kwargs) -> Any | None:
        """
        Execute all the handlers associated with the event and return an array of results.

        :param event: The function to be processed
        :param args:  Parameters to be passed to the function.
        :param kwargs: Parameters to be passed to the function.
        """
        log.debug(f'Running function {event}')
        results = []
        if self.has_function(event):
            for function in self.functions_list[event]:
                try:
                    result = function(*args, **kwargs)
                    if result is not None:
                        results.append(result)
                except TypeError:
                    # Who has called me can help in debugging
                    trace_error_handler(log)
                    log.exception('Exception for function {function}'.format(function=function))
        else:
            if log.getEffectiveLevel() == logging.DEBUG:
                trace_error_handler(log)
                log.error('Event {event} called but not registered'.format(event=event))
        return results

    def get_flag(self, key: str) -> Any | None:
        """
        Extracts the working_flag value from the list based on the key passed in

        :param key: The flag to be retrieved.
        """
        if key in self.working_flags:
            return self.working_flags[key]
        elif self._is_suppressing:
            return None
        else:
            trace_error_handler(log)
            log.error('Working Flag {key} not found in list'.format(key=key))
            raise KeyError('Working Flag {key} not found in list'.format(key=key))

    def set_flag(self, key: str, reference: Any):
        """
        Sets a working_flag based on the key passed in.

        :param key: The working_flag to be created this is usually a major class like "renderer" or "main_window" .
        :param reference: The data to be saved.
        """
        self.working_flags[key] = reference

    def remove_flag(self, key: str):
        """
        Removes the working flags value from the list based on the key passed.

        :param key: The working_flag to be deleted.
        """
        if key in self.working_flags:
            del self.working_flags[key]


class RegistryBase(object):
    """
    This adds registry components to classes to use at run time.
    """
    def __init__(self, *args, **kwargs):
        """
        Register the class and bootstrap hooks.
        """
        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            super().__init__()
        Registry().register(de_hump(self.__class__.__name__), self)
        Registry().register_function('bootstrap_initialise', self.bootstrap_initialise)
        Registry().register_function('bootstrap_post_set_up', self.bootstrap_post_set_up)
        Registry().register_function('bootstrap_completion', self.bootstrap_completion)

    def bootstrap_initialise(self):
        """
        Dummy method to be overridden
        """
        pass

    def bootstrap_post_set_up(self):
        """
        Dummy method to be overridden
        """
        pass

    def bootstrap_completion(self):
        """
        Dummy method to be overridden
        """
        pass
