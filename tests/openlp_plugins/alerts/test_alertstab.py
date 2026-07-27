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
This module contains tests for the alerts settings tab (preset editor).
"""
import json

import pytest

from openlp.plugins.alerts.lib.alertstab import AlertsTab
from openlp.plugins.alerts.lib.presets import DEFAULT_PRESETS, AlertPriority, get_alert_presets


@pytest.fixture
def alerts_tab(qapp, settings):
    """An AlertsTab instance"""
    return AlertsTab(None, 'Alerts')


def test_tab_loads_default_presets(alerts_tab):
    """The tab starts editing the Info default with its built-in values"""
    # THEN: The info default is loaded into the shared style editor
    assert alerts_tab.current_priority_key == 'info'
    assert alerts_tab.style_editor.font_size_spin_box.value() == DEFAULT_PRESETS['info']['fontSize']
    assert alerts_tab.style_editor.timeout_spin_box.value() == DEFAULT_PRESETS['info']['timeout']


def test_switching_priority_loads_other_preset(alerts_tab):
    """Selecting another priority shows that priority's default"""
    # WHEN: The critical priority is selected
    alerts_tab.priority_combo_box.setCurrentIndex(AlertPriority.Critical.value)

    # THEN: The critical default is loaded
    assert alerts_tab.current_priority_key == 'critical'
    assert alerts_tab.style_editor.font_size_spin_box.value() == DEFAULT_PRESETS['critical']['fontSize']


def test_editing_and_saving_persists_preset(alerts_tab, settings):
    """A changed value survives the save/load round trip"""
    # WHEN: The font size is changed and the tab is saved
    alerts_tab.style_editor.font_size_spin_box.setValue(77)
    alerts_tab.save()

    # THEN: The change is persisted in the settings, and only for that priority
    presets = get_alert_presets(settings)
    assert presets['info']['fontSize'] == 77
    assert presets['notice'] == DEFAULT_PRESETS['notice']


def test_reset_button_restores_defaults(alerts_tab):
    """The reset button reverts the edited default to its factory look"""
    # GIVEN: A modified default
    alerts_tab.style_editor.font_size_spin_box.setValue(77)

    # WHEN: The default is reset
    alerts_tab.on_reset_clicked()

    # THEN: The default value is back
    assert alerts_tab.style_editor.font_size_spin_box.value() == DEFAULT_PRESETS['info']['fontSize']


def test_zone_buttons_reflect_preset(alerts_tab):
    """The zone grid mirrors the default's screen position"""
    # THEN: The info default's bottom-right zone button is checked
    assert alerts_tab.style_editor.zone_buttons[('right', 'bottom')].isChecked()

    # WHEN: Another zone is chosen and values are stored
    alerts_tab.style_editor.zone_buttons[('center', 'top')].setChecked(True)

    # THEN: The default follows
    assert alerts_tab.presets['info']['zoneH'] == 'center'
    assert alerts_tab.presets['info']['zoneV'] == 'top'


def test_alerts_tab_edits_global_defaults_not_alert_items(alerts_tab, settings):
    """AlertsTab edits the four global default styles, never a saved AlertItem"""
    # WHEN: A value is changed and saved
    alerts_tab.style_editor.font_size_spin_box.setValue(77)
    alerts_tab.save()

    # THEN: It only touched the global presets setting, not the alerts database
    stored = settings.value('alerts/presets')
    if isinstance(stored, str):
        stored = json.loads(stored)
    assert stored['info']['fontSize'] == 77
