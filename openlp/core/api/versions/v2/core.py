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
Core API v2 endpoints.
"""

import logging

from flask import jsonify, request, abort, Blueprint
from PySide6 import QtCore

from openlp.core.api.lib import login_required
from openlp.core.common.i18n import LanguageManager
from openlp.core.common.registry import Registry
from openlp.core.lib.plugin import PluginStatus, StringContent
from openlp.core.state import State

core = Blueprint('core', __name__)
log = logging.getLogger(__name__)


@core.route('/display', methods=['POST'])
@login_required
def toggle_display():
    """
    Toggle the display state of the main display.

    returns: Empty response with status code 204.
    rtype: flask.Response
    """
    data = request.json
    if not data:
        log.error('Missing request data')
        abort(400)
    display = data.get('display', '').lower()
    if display not in ['hide', 'show', 'blank', 'theme', 'desktop']:
        abort(400)
    Registry().get('live_controller').slidecontroller_toggle_display.emit(display)
    return '', 204


@core.route('/plugins')
@login_required
def plugin_list():
    """
    Get a list of active plugins that support searching.

    returns: JSON response containing the list of plugins.
    rtype: flask.Response
    """
    searches = []
    for plugin in State().list_plugins():
        if plugin.status == PluginStatus.Active and plugin.media_item and plugin.media_item.has_search:
            searches.append({'key': plugin.name, 'name': str(plugin.text_strings[StringContent.Name]['plural'])})
    return jsonify(searches)


@core.route('/shortcuts')
@login_required
def shortcuts():
    """
    Get a list of all keyboard shortcuts.

    returns: JSON response containing the list of shortcuts.
    rtype: flask.Response
    """
    data = []
    settings = Registry().get('settings_thread')
    shortcut_prefix = 'shortcuts/'
    for key in settings.allKeys():
        if key.startswith(shortcut_prefix):
            data.append(
                {
                    'action': key.removeprefix(shortcut_prefix),
                    'shortcut': settings.value(key)
                }
            )
    return jsonify(data)


@core.route('/system')
@login_required
def system_information():
    """
    Get system information.

    returns: JSON response containing system information.
    rtype: flask.Response
    """
    data = {}
    data['websocket_port'] = Registry().get('settings_thread').value('api/websocket port')
    data['login_required'] = Registry().get('settings_thread').value('api/authentication enabled')
    data['api_version'] = 2
    data['api_revision'] = 7
    return jsonify(data)


@core.route('/language')
@login_required
def language():
    """
    Get the current language.

    returns: JSON response containing the current language.
    rtype: flask.Response
    """
    current_language = LanguageManager.get_language()
    return jsonify({'language': current_language})


@core.route('/login', methods=['POST'])
def login():
    """
    Login to the API and get an authentication token.

    returns: JSON response containing the authentication token.
    rtype: flask.Response
    """
    data = request.json
    if not data:
        log.error('Missing request data')
        abort(400)
    username = data.get('username', '')
    password = data.get('password', '')
    if username == Registry().get('settings_thread').value('api/user id') and \
            password == Registry().get('settings_thread').value('api/password'):
        return jsonify({'token': Registry().get('authentication_token')})
    log.error('Unauthorised Request for %s', username)
    return '', 401


@core.route('/live-image')
@login_required
def main_image():
    """
    Get a base64 encoded image of the current main display.

    returns: JSON response containing the base64 encoded image.
    rtype: flask.Response
    """
    live_controller = Registry().get('live_controller')
    img_data = live_controller.staticMetaObject.invokeMethod(
        live_controller, 'grab_maindisplay', QtCore.Qt.ConnectionType.DirectConnection, QtCore.Q_RETURN_ARG(str))
    img = f'data:image/jpeg;base64,{img_data}'
    return jsonify({'binary_image': img})
