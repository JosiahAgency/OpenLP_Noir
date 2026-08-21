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
from flask.testing import FlaskClient

from openlp.core.common.registry import Registry
from openlp.core.common.settings import Settings
from openlp.core.state import State
from openlp.core.lib.plugin import PluginStatus, StringContent


def test_plugins_returns_list(flask_client: FlaskClient):
    State().load_settings()
    res = flask_client.get('/api/v2/core/plugins').get_json()
    assert len(res) == 0

    class FakeMediaItem:
        has_search = True

    class FakePlugin:
        name = 'Faked'
        is_plugin = True
        status = PluginStatus.Active
        media_item = FakeMediaItem()
        text_strings = {StringContent.Name: {'plural': 'just a text'}}
    plugin = FakePlugin()
    State().modules['testplug'] = plugin
    Registry.create().register('testplug_plugin', plugin)
    res = flask_client.get('/api/v2/core/plugins').get_json()
    assert len(res) == 1
    assert res[0]['key'] == plugin.name
    assert res[0]['name'] == plugin.text_strings[StringContent.Name]['plural']


def test_system_information(flask_client: FlaskClient, settings: Settings):
    Registry().get('settings_thread').setValue('api/authentication enabled', False)
    res = flask_client.get('/api/v2/core/system').get_json()
    assert res['websocket_port'] > 0
    assert not res['login_required']


def test_shortcuts(flask_client: FlaskClient, settings: Settings):
    action = 'shortcuts/aboutItem'
    shortcut = 'Ctrl+F1'
    Registry().get('settings_thread').setValue(action, shortcut)
    res = flask_client.get('/api/v2/core/shortcuts')
    assert res.status_code == 200
    assert res.get_json()[0]['action'] == action.removeprefix('shortcuts/')
    assert res.get_json()[0]['shortcut'] == shortcut


def test_language(flask_client: FlaskClient, settings: Settings):
    res = flask_client.get('/api/v2/core/language')
    assert res.status_code == 200
    assert res.get_json()['language']


def test_login_get_is_refused(flask_client: FlaskClient):
    res = flask_client.get('/api/v2/core/login')
    assert res.status_code == 405


def test_login_without_data_returns_400(flask_client: FlaskClient):
    res = flask_client.post('/api/v2/core/login', json={})
    assert res.status_code == 400


def test_login_with_invalid_credetials_returns_401(flask_client: FlaskClient, settings: Settings):
    res = flask_client.post('/api/v2/core/login', json=dict(username='openlp', password='invalid'))
    assert res.status_code == 401


def test_login_with_valid_credetials_returns_token(flask_client: FlaskClient, settings: Settings):
    Registry().register('authentication_token', 'foobar')
    Registry().get('settings_thread').setValue('api/password', 'password')
    res = flask_client.post('/api/v2/core/login', json=dict(username='openlp', password='password'))
    assert res.status_code == 200
    assert res.get_json()['token'] == 'foobar'


def test_retrieving_image(flask_client: FlaskClient):
    class FakeController:
        @property
        def staticMetaObject(self):
            class FakeMetaObject:
                def invokeMethod(self, obj, meth, conn_type, return_type):
                    return ''
            return FakeMetaObject()
    Registry.create().register('live_controller', FakeController())
    res = flask_client.get('/api/v2/core/live-image').get_json()
    assert res['binary_image'] != ''


def test_toggle_display_requires_login(flask_client: FlaskClient, settings: Settings):
    settings.setValue('api/authentication enabled', True)
    Registry().register('authentication_token', 'foobar')
    res = flask_client.post('/api/v2/core/display')
    settings.setValue('api/authentication enabled', False)
    assert res.status_code == 401


def test_system_information_requires_login_when_enabled(flask_client: FlaskClient, settings: Settings):
    settings.setValue('api/authentication enabled', True)
    Registry().register('authentication_token', 'foobar')
    res = flask_client.get('/api/v2/core/system')
    settings.setValue('api/authentication enabled', False)
    assert res.status_code == 401


def test_toggle_display_does_not_allow_get(flask_client: FlaskClient):
    res = flask_client.get('/api/v2/core/display')
    assert res.status_code == 405


def test_toggle_display_invalid_action(flask_client: FlaskClient, settings: Settings):
    res = flask_client.post('/api/v2/core/display', json={'display': 'foo'})
    assert res.status_code == 400


def test_toggle_display_no_data(flask_client: FlaskClient, settings: Settings):
    res = flask_client.post('/api/v2/core/display', json={})
    assert res.status_code == 400


def test_toggle_display_valid_action_updates_controller(flask_client: FlaskClient, settings: Settings):
    class FakeController:
        class Emitter:
            def emit(self, value):
                self.set = value
        slidecontroller_toggle_display = Emitter()
    controller = FakeController()
    Registry().register('live_controller', controller)
    res = flask_client.post('/api/v2/core/display', json={'display': 'show'})
    assert res.status_code == 204
    assert controller.slidecontroller_toggle_display.set == 'show'


def test_cors_headers_are_present(flask_client: FlaskClient, settings: Settings):
    res = flask_client.get('/api/v2/core/system')
    assert 'Access-Control-Allow-Origin' in res.headers
    assert res.headers['Access-Control-Allow-Origin'] == '*'
