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
from unittest.mock import MagicMock

from openlp.plugins.alerts.lib.presets import (DEFAULT_PRESETS, PRIORITY_KEYS, AlertPriority, get_alert_presets,
                                               new_template_style, resolve_alert_settings, resolve_template_style,
                                               save_alert_presets)


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


def test_new_template_style_copies_the_current_default(settings):
    """A new template starts from an independent copy of the chosen priority's live default"""
    # GIVEN: A customized Important default
    settings.setValue('alerts/presets', json.dumps({'important': {'fontSize': 77}}))

    # WHEN: A new template style is built for Important
    style = new_template_style(settings, AlertPriority.Important)

    # THEN: It reflects the live default, tagged with the priority key
    assert style['fontSize'] == 77
    assert style['priority'] == 'important'

    # AND: Mutating it does not affect the live presets
    style['fontSize'] = 1
    assert get_alert_presets(settings)['important']['fontSize'] == 77


def test_resolve_template_style_uses_the_templates_own_style(settings):
    """A template with its own saved style uses it, filtered to known keys"""
    # GIVEN: An AlertItem-like object with its own style, including a stale key
    own_style = dict(DEFAULT_PRESETS['notice'])
    own_style['fontSize'] = 99
    own_style['bogusKey'] = True
    alert_item = MagicMock(priority=int(AlertPriority.Notice), style=json.dumps(own_style))

    # WHEN: The template's style is resolved
    resolved = resolve_template_style(alert_item, settings)

    # THEN: The saved style applies, the stale key is dropped, and priority is stamped
    assert resolved['fontSize'] == 99
    assert 'bogusKey' not in resolved
    assert resolved['priority'] == 'notice'


def test_resolve_template_style_falls_back_without_a_saved_style(settings):
    """A template with no saved style (e.g. pre-dating per-template styling) falls back to its priority default"""
    # GIVEN: An AlertItem-like object with no style of its own
    alert_item = MagicMock(priority=int(AlertPriority.Critical), style=None)

    # WHEN: The template's style is resolved
    resolved = resolve_template_style(alert_item, settings)

    # THEN: It matches the live Critical default
    assert resolved == resolve_alert_settings(settings, AlertPriority.Critical)
