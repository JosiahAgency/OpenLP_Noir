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
import logging

from flask import jsonify, request, abort, Blueprint

from openlp.core.api.lib import login_required
from openlp.core.common.registry import Registry
from openlp.core.common.utils import is_uuid


service_views = Blueprint('service', __name__)
log = logging.getLogger(__name__)


@service_views.route('/items')
@login_required
def service_items():
    log.debug('service/v2/items')
    live_controller = Registry().get('live_controller')
    service_items = []
    if live_controller.service_item:
        current_unique_identifier = live_controller.service_item.unique_identifier
    else:
        current_unique_identifier = None
    for item in Registry().get('service_manager').service_items:
        service_item = item['service_item']
        if 'ccli_number' in service_item.data_string:
            ccli_number = service_item.data_string['ccli_number']
        else:
            ccli_number = ''
        service_items.append({
            'id': str(service_item.unique_identifier),
            'title': str(service_item.get_display_title()),
            'plugin': str(service_item.name),
            'ccli_number': str(ccli_number),
            'notes': str(service_item.notes),
            'selected': (service_item.unique_identifier == current_unique_identifier),
            'is_valid': service_item.is_valid
        })
    return jsonify(service_items)


@service_views.route('/show', methods=['POST'])
@service_views.route('/show/<item_id>', methods=['POST'])
@login_required
def service_set(item_id=None):
    log.debug('service/v2/show')
    data = request.get_json(silent=True) or {}
    item_id = item_id or data.get('id') or data.get('uid')
    if not item_id:
        log.error('Missing item id')
        abort(400)
    if is_uuid(item_id):
        Registry().get('service_manager').servicemanager_set_item_by_uuid.emit(item_id)
        return '', 204
    try:
        id = int(item_id)
        Registry().get('service_manager').servicemanager_set_item.emit(id)
        return '', 204
    except ValueError:
        log.error('Invalid item id: ' + item_id)
        abort(400)


@service_views.route('/progress', methods=['POST'])
@login_required
def service_direction():
    log.debug('service/v2/progress')
    ALLOWED_ACTIONS = ['next', 'previous']
    data = request.json
    if not data:
        log.error('Missing request data')
        abort(400)
    action = data.get('action', '').lower()
    if action not in ALLOWED_ACTIONS:
        log.error('Invalid data passed ' + str(data))
        abort(400)
    getattr(Registry().get('service_manager'), 'servicemanager_{action}_item'.format(action=action)).emit()
    return '', 204


@service_views.route('/new', methods=['GET'])
@login_required
def new_service():
    log.debug('service/v2/new')
    getattr(Registry().get('service_manager'), 'servicemanager_new_file').emit()
    return '', 204


@service_views.route('/delete_item', methods=['POST'])
@login_required
def delete_item():
    log.debug('service/v2/delete_item')
    getattr(Registry().get('service_manager'), 'servicemanager_delete_item').emit()
    return '', 204
