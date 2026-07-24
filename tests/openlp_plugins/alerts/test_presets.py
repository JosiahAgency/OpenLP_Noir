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
This module contains tests for the alert style presets.
"""
import json

from openlp.plugins.alerts.lib.presets import (DEFAULT_PRESETS, PRIORITY_KEYS, AlertPriority, get_alert_presets,
                                               resolve_alert_settings, save_alert_presets)


def test_default_presets_cover_all_priorities(settings):
    """Without saved overrides, every priority gets its built-in preset"""
    # WHEN: The presets are loaded with no overrides saved
    presets = get_alert_presets(settings)

    # THEN: All four priorities are present and match the defaults
    assert sorted(presets.keys()) == sorted(PRIORITY_KEYS)
    assert presets['info'] == DEFAULT_PRESETS['info']
    assert presets['critical']['alertType'] == 'fullscreen'


def test_presets_merge_user_overrides(settings):
    """Saved overrides are merged over the defaults, unknown keys dropped"""
    # GIVEN: A saved override for the info preset
    settings.setValue('alerts/presets', json.dumps({'info': {'fontSize': 60, 'bogusKey': True}}))

    # WHEN: The presets are loaded
    presets = get_alert_presets(settings)

    # THEN: The override applies, unknown keys are dropped, other keys keep defaults
    assert presets['info']['fontSize'] == 60
    assert 'bogusKey' not in presets['info']
    assert presets['info']['alertType'] == DEFAULT_PRESETS['info']['alertType']


def test_presets_survive_invalid_json(settings):
    """Bad JSON in the setting falls back to the defaults"""
    # GIVEN: Garbage in the presets setting
    settings.setValue('alerts/presets', 'this is {not json')

    # WHEN: The presets are loaded
    presets = get_alert_presets(settings)

    # THEN: The defaults are returned
    assert presets['notice'] == DEFAULT_PRESETS['notice']


def test_save_presets_stores_only_differences(settings):
    """Saving presets only persists values that differ from the defaults"""
    # GIVEN: Presets where only one value was changed
    presets = get_alert_presets(settings)
    presets['important']['fontSize'] = 99

    # WHEN: The presets are saved
    save_alert_presets(settings, presets)

    # THEN: Only the changed value is stored
    stored = settings.value('alerts/presets')
    if isinstance(stored, str):
        stored = json.loads(stored)
    assert stored == {'important': {'fontSize': 99}}


def test_save_unchanged_presets_clears_setting(settings):
    """Saving unchanged presets stores an empty value"""
    # GIVEN: A previously stored override
    settings.setValue('alerts/presets', json.dumps({'info': {'fontSize': 60}}))

    # WHEN: Unchanged (default) presets are saved
    save_alert_presets(settings, {key: dict(DEFAULT_PRESETS[key]) for key in PRIORITY_KEYS})

    # THEN: The setting is cleared
    assert settings.value('alerts/presets') == ''


def test_resolve_alert_settings_includes_priority(settings):
    """The resolved settings carry the priority key for the display"""
    # WHEN: Settings are resolved for the critical priority
    resolved = resolve_alert_settings(settings, AlertPriority.Critical)

    # THEN: The dict is the critical preset plus its priority key
    assert resolved['priority'] == 'critical'
    assert resolved['alertType'] == DEFAULT_PRESETS['critical']['alertType']
