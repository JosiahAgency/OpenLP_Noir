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
from pathlib import Path
from unittest.mock import MagicMock, patch

from flask.testing import FlaskClient

from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings


def test_retrieve_live_items(flask_client: FlaskClient, registry: Registry, settings: Settings):
    """
    Test the live-item endpoint with a mocked service item
    """
    # GIVEN: A mocked controller with a mocked service item
    fake_live_controller = MagicMock()
    fake_live_controller.service_item = MagicMock()
    fake_live_controller.selected_row = 0
    fake_live_controller.service_item.unique_identifier = 42
    fake_live_controller.service_item.to_dict.return_value = {'slides': [{'selected': False}]}
    Registry().register('live_controller', fake_live_controller)

    # WHEN: The live-item endpoint is called
    res = flask_client.get('/api/v2/controller/live-items').get_json()

    # THEN: The correct item data should be returned
    assert res == {'slides': [{'selected': True}], 'id': '42'}


def test_retrieve_live_items_requires_login_when_enabled(flask_client: FlaskClient, settings: Settings):
    settings.setValue('api/authentication enabled', True)
    Registry().register('authentication_token', 'foobar')
    res = flask_client.get('/api/v2/controller/live-items')
    settings.setValue('api/authentication enabled', False)
    assert res.status_code == 401


def test_controller_set_requires_login(flask_client: FlaskClient, registry: Registry, settings: Settings):
    settings.setValue('api/authentication enabled', True)
    Registry().register('authentication_token', 'foobar')
    res = flask_client.post('/api/v2/controller/show', json=dict())
    settings.setValue('api/authentication enabled', False)
    assert res.status_code == 401


def test_controller_set_does_not_accept_get(flask_client: FlaskClient, registry: Registry, settings: Settings):
    res = flask_client.get('/api/v2/controller/show')
    assert res.status_code == 405


def test_controller_set_aborts_on_unspecified_controller(flask_client: FlaskClient, registry: Registry,
                                                         settings: Settings):
    res = flask_client.post('/api/v2/controller/show', json={})
    assert res.status_code == 400


def test_controller_set_calls_live_controller(flask_client: FlaskClient, registry: Registry, settings: Settings):
    fake_live_controller = MagicMock()
    Registry().register('live_controller', fake_live_controller)
    res = flask_client.post('/api/v2/controller/show', json={'id': 400})
    assert res.status_code == 204
    fake_live_controller.slidecontroller_live_set.emit.assert_called_once_with([400])


def test_controller_direction_requires_login(flask_client: FlaskClient, registry: Registry, settings: Settings):
    settings.setValue('api/authentication enabled', True)
    Registry().register('authentication_token', 'foobar')
    res = flask_client.post('/api/v2/controller/progress', json=dict())
    settings.setValue('api/authentication enabled', False)
    assert res.status_code == 401


def test_controller_direction_does_not_accept_get(flask_client: FlaskClient, registry: Registry, settings: Settings):
    res = flask_client.get('/api/v2/controller/progress')
    assert res.status_code == 405


def test_controller_direction_does_fails_on_wrong_data(flask_client: FlaskClient, registry: Registry,
                                                       settings: Settings):
    res = flask_client.post('/api/v2/controller/progress', json={'action': 'foo'})
    assert res.status_code == 400


def test_controller_direction_does_fails_on_missing_data(flask_client: FlaskClient, registry: Registry,
                                                         settings: Settings):
    res = flask_client.post('/api/v2/controller/progress', json={})
    assert res.status_code == 400


def test_controller_direction_calls_service_manager(flask_client: FlaskClient, registry: Registry, settings: Settings):
    fake_live_controller = MagicMock()
    Registry().register('live_controller', fake_live_controller)
    res = flask_client.post('/api/v2/controller/progress', json=dict(action='next'))
    assert res.status_code == 204
    fake_live_controller.slidecontroller_live_next.emit.assert_called_once()


# Themes tests
def test_controller_get_theme_level_returns_valid_theme_level_global(flask_client: FlaskClient, registry: Registry,
                                                                     settings: Settings):
    settings.setValue('themes/theme level', 1)
    res = flask_client.get('/api/v2/controller/theme-level').get_json()
    assert res == 'global'


def test_controller_get_theme_level_returns_valid_theme_level_service(flask_client: FlaskClient, registry: Registry,
                                                                      settings: Settings):
    settings.setValue('themes/theme level', 2)
    res = flask_client.get('/api/v2/controller/theme-level').get_json()
    assert res == 'service'


def test_controller_get_theme_level_returns_valid_theme_level_song(flask_client: FlaskClient, registry: Registry,
                                                                   settings: Settings):
    settings.setValue('themes/theme level', 3)
    res = flask_client.get('/api/v2/controller/theme-level').get_json()
    assert res == 'song'


def test_controller_set_theme_level_aborts_if_no_theme_level(flask_client: FlaskClient, registry: Registry,
                                                             settings: Settings):
    res = flask_client.post('/api/v2/controller/theme-level', json={})
    assert res.status_code == 400


def test_controller_set_theme_level_aborts_if_invalid_theme_level(flask_client: FlaskClient, registry: Registry,
                                                                  settings: Settings):
    fake_theme_manager = MagicMock()
    Registry().register('theme_manager', fake_theme_manager)
    res = flask_client.post('/api/v2/controller/theme-level', json=dict(level='foo'))
    assert res.status_code == 400
    fake_theme_manager.theme_level_updated.emit.assert_not_called()


def test_controller_set_theme_level_sets_theme_level_global(flask_client: FlaskClient, registry: Registry,
                                                            settings: Settings):
    fake_theme_manager = MagicMock()
    Registry().register('theme_manager', fake_theme_manager)
    res = flask_client.post('/api/v2/controller/theme-level', json=dict(level='global'))
    assert res.status_code == 204
    assert Registry().get('settings').value('themes/theme level') == 1
    fake_theme_manager.theme_level_updated.emit.assert_called_once()


def test_controller_set_theme_level_sets_theme_level_service(flask_client: FlaskClient, registry: Registry,
                                                             settings: Settings):
    fake_theme_manager = MagicMock()
    Registry().register('theme_manager', fake_theme_manager)
    res = flask_client.post('/api/v2/controller/theme-level', json=dict(level='service'))
    assert res.status_code == 204
    assert Registry().get('settings').value('themes/theme level') == 2
    fake_theme_manager.theme_level_updated.emit.assert_called_once()


def test_controller_set_theme_level_sets_theme_level_song(flask_client: FlaskClient, registry: Registry,
                                                          settings: Settings):
    fake_theme_manager = MagicMock()
    Registry().register('theme_manager', fake_theme_manager)
    res = flask_client.post('/api/v2/controller/theme-level', json=dict(level='song'))
    assert res.status_code == 204
    assert Registry().get('settings').value('themes/theme level') == 3
    fake_theme_manager.theme_level_updated.emit.assert_called_once()


def test_controller_get_themes_retrieves_themes_list(flask_client: FlaskClient, registry: Registry, settings: Settings):
    Registry().register('theme_manager', MagicMock())
    Registry().register('service_manager', MagicMock())
    res = flask_client.get('api/v2/controller/themes').get_json()
    assert type(res) is list


@patch('openlp.core.api.versions.v2.controller.image_to_data_uri')
def test_controller_get_themes_retrieves_themes_list_service(mocked_image_to_data_uri: MagicMock,
                                                             flask_client: FlaskClient, registry: Registry,
                                                             settings: Settings):
    settings.setValue('themes/theme level', 2)
    mocked_theme_manager = MagicMock()
    mocked_theme_manager.theme_path = Path()
    mocked_service_manager = MagicMock()
    mocked_service_manager.service_theme = 'test_theme'
    Registry().register('theme_manager', mocked_theme_manager)
    Registry().register('service_manager', mocked_service_manager)
    Registry().register_function('get_theme_names', MagicMock(side_effect=[['theme1', 'test_theme', 'theme2']]))
    mocked_image_to_data_uri.return_value = ''
    res = flask_client.get('api/v2/controller/themes').get_json()
    assert res == [{'thumbnail': '', 'name': 'theme1', 'selected': False},
                   {'thumbnail': '', 'name': 'test_theme', 'selected': True},
                   {'thumbnail': '', 'name': 'theme2', 'selected': False}]


def test_controller_get_theme_data(flask_client: FlaskClient, registry: Registry, settings: Settings):
    Registry().register_function('get_theme_names', MagicMock(side_effect=[['theme1', 'theme2']]))
    Registry().register('theme_manager', MagicMock())
    res = flask_client.get('api/v2/controller/themes/theme1')
    assert res.status_code == 200


def test_controller_get_theme_data_invalid_theme(flask_client: FlaskClient, registry: Registry, settings: Settings):
    Registry().register_function('get_theme_names', MagicMock(side_effect=[['theme1', 'theme2']]))
    Registry().register('theme_manager', MagicMock())
    res = flask_client.get('api/v2/controller/themes/imaginarytheme')
    assert res.status_code == 404


def test_controller_get_live_theme_data(flask_client: FlaskClient, registry: Registry, settings: Settings):
    fake_live_controller = MagicMock()
    theme = MagicMock()
    theme.export_theme_self_contained.return_value = '[[], []]'
    fake_live_controller.service_item.get_theme_data.return_value = theme
    Registry().register('live_controller', fake_live_controller)
    res = flask_client.get('api/v2/controller/live-theme')
    assert res.status_code == 200
    assert res.get_json() == [[], []]


def test_controller_get_live_theme_data_no_service_item(flask_client: FlaskClient, registry: Registry,
                                                        settings: Settings):
    fake_theme_manager = MagicMock()
    fake_live_controller = MagicMock()
    theme = MagicMock()
    theme.export_theme_self_contained.return_value = '[[], [], []]'
    fake_theme_manager.get_theme_data.return_value = theme
    fake_live_controller.service_item = None
    Registry().register('theme_manager', fake_theme_manager)
    Registry().register('live_controller', fake_live_controller)
    res = flask_client.get('api/v2/controller/live-theme')
    assert res.status_code == 200
    assert res.get_json() == [[], [], []]


def test_controller_get_theme_returns_current_theme_global(flask_client: FlaskClient, registry: Registry,
                                                           settings: Settings):
    settings.setValue('themes/theme level', 1)
    settings.setValue('themes/global theme', 'Default')
    res = flask_client.get('/api/v2/controller/theme')
    assert res.status_code == 200
    assert res.get_json() == 'Default'


def test_controller_get_theme_returns_current_theme_service(flask_client: FlaskClient, registry: Registry,
                                                            settings: Settings):
    settings.setValue('themes/theme level', 2)
    settings.setValue('servicemanager/service theme', 'Service')
    res = flask_client.get('/api/v2/controller/theme')
    assert res.status_code == 200
    assert res.get_json() == 'Service'


def test_controller_set_theme_aborts_if_no_theme(flask_client: FlaskClient, registry: Registry, settings: Settings):
    res = flask_client.post('/api/v2/controller/theme', json={})
    assert res.status_code == 400


def test_controller_set_theme_sets_global_theme(flask_client: FlaskClient, registry: Registry, settings: Settings):
    fake_theme_manager = MagicMock()
    Registry().register('theme_manager', fake_theme_manager)
    settings.setValue('themes/theme level', 1)
    res = flask_client.post('/api/v2/controller/theme', json=dict(theme='test'))
    assert res.status_code == 204


def test_controller_set_theme_sets_service_theme(flask_client: FlaskClient, registry: Registry, settings: Settings):
    fake_service_manager = MagicMock()
    Registry().register('service_manager', fake_service_manager)
    settings.setValue('themes/theme level', 2)
    res = flask_client.post('/api/v2/controller/theme', json=dict(theme='test'))
    assert res.status_code == 204


def test_controller_set_theme_returns_song_exception(flask_client: FlaskClient, registry: Registry, settings: Settings):
    settings.setValue('themes/theme level', 3)
    res = flask_client.post('/api/v2/controller/theme', json=dict(theme='test'))
    assert res.status_code == 501


def test_controller_clear_live(flask_client: FlaskClient, registry: Registry, settings: Settings):
    Registry().register('live_controller', MagicMock())
    res = flask_client.post('/api/v2/controller/clear/live')
    assert res.status_code == 204


def test_controller_clear_invalid(flask_client: FlaskClient, registry: Registry, settings: Settings):
    res = flask_client.post('/api/v2/controller/clear/my_screen')
    assert res.status_code == 404
