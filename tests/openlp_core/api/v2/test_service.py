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
from unittest.mock import MagicMock

from openlp.core.common.registry import Registry


def test_retrieve_service_items(flask_client, settings):
    mocked_live_controller = MagicMock()
    mocked_live_controller.service_item = MagicMock()
    fake_service_manager = MagicMock()
    Registry().register('service_manager', fake_service_manager)
    Registry().register('live_controller', mocked_live_controller)
    res = flask_client.get('/api/v2/service/items').get_json()
    assert len(res) == 0


def test_retrieve_service_items_requires_login_when_enabled(flask_client, settings):
    settings.setValue('api/authentication enabled', True)
    Registry().register('authentication_token', 'test-token')
    res = flask_client.get('/api/v2/service/items')
    settings.setValue('api/authentication enabled', False)
    assert res.status_code == 401


def test_service_set_requires_login(flask_client, settings):
    settings.setValue('api/authentication enabled', True)
    Registry().register('authentication_token', 'test-token')
    res = flask_client.post('/api/v2/service/show', json=dict())
    settings.setValue('api/authentication enabled', False)
    assert res.status_code == 401


def test_service_set_does_not_accept_get(flask_client, settings):
    res = flask_client.get('/api/v2/service/show')
    assert res.status_code == 405


def test_service_set_calls_service_manager(flask_client, settings):
    fake_service_manager = MagicMock()
    Registry().register('service_manager', fake_service_manager)
    res = flask_client.post('/api/v2/service/show', json=dict(id=400))
    assert res.status_code == 204
    fake_service_manager.servicemanager_set_item.emit.assert_called_once_with(400)


def test_service_set_with_path_item_id_and_no_json(flask_client, settings):
    fake_service_manager = MagicMock()
    Registry().register('service_manager', fake_service_manager)
    res = flask_client.post('/api/v2/service/show/400')
    assert res.status_code == 204
    fake_service_manager.servicemanager_set_item.emit.assert_called_once_with(400)


def test_service_direction_requires_login(flask_client, settings):
    settings.setValue('api/authentication enabled', True)
    Registry().register('authentication_token', 'test-token')
    res = flask_client.post('/api/v2/service/progress', json=dict())
    settings.setValue('api/authentication enabled', False)
    assert res.status_code == 401


def test_service_direction_does_not_accept_get(flask_client, settings):
    res = flask_client.get('/api/v2/service/progress')
    assert res.status_code == 405


def test_service_direction_does_fails_on_wrong_data(flask_client, settings):
    res = flask_client.post('/api/v2/service/progress', json=dict(action='foo'))
    assert res.status_code == 400


def test_service_direction_calls_service_manager(flask_client, settings):
    fake_service_manager = MagicMock()
    Registry().register('service_manager', fake_service_manager)
    res = flask_client.post('/api/v2/service/progress', json=dict(action='next'))
    assert res.status_code == 204
    fake_service_manager.servicemanager_next_item.emit.assert_called_once()


def test_delete_service_items(flask_client, settings):
    fake_service_manager = MagicMock()
    Registry().register('service_manager', fake_service_manager)
    res = flask_client.post('/api/v2/service/delete_item', json='')
    assert res.status_code == 204
    fake_service_manager.servicemanager_delete_item.emit.assert_called_once()
