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
import pytest

from openlp.plugins.alerts.lib.alertstab import AlertsTab
from openlp.plugins.alerts.lib.presets import DEFAULT_PRESETS, AlertPriority, get_alert_presets


@pytest.fixture
def alerts_tab(qapp, settings):
    """An AlertsTab instance"""
    return AlertsTab(None, 'Alerts')


def test_tab_loads_default_presets(alerts_tab):
    """The tab starts editing the Info preset with default values"""
    # THEN: The info preset is loaded into the widgets
    assert alerts_tab.current_priority_key == 'info'
    assert alerts_tab.font_size_spin_box.value() == DEFAULT_PRESETS['info']['fontSize']
    assert alerts_tab.timeout_spin_box.value() == DEFAULT_PRESETS['info']['timeout']


def test_switching_priority_loads_other_preset(alerts_tab):
    """Selecting another priority shows that priority's preset"""
    # WHEN: The critical priority is selected
    alerts_tab.priority_combo_box.setCurrentIndex(AlertPriority.Critical.value)

    # THEN: The critical preset is loaded
    assert alerts_tab.current_priority_key == 'critical'
    assert alerts_tab.font_size_spin_box.value() == DEFAULT_PRESETS['critical']['fontSize']


def test_editing_and_saving_persists_preset(alerts_tab, settings):
    """A changed value survives the save/load round trip"""
    # WHEN: The font size is changed and the tab is saved
    alerts_tab.font_size_spin_box.setValue(77)
    alerts_tab.save()

    # THEN: The change is persisted in the settings
    presets = get_alert_presets(settings)
    assert presets['info']['fontSize'] == 77
    assert presets['notice'] == DEFAULT_PRESETS['notice']


def test_reset_button_restores_defaults(alerts_tab):
    """The reset button reverts the edited preset to its defaults"""
    # GIVEN: A modified preset
    alerts_tab.font_size_spin_box.setValue(77)

    # WHEN: The preset is reset
    alerts_tab.on_reset_clicked()

    # THEN: The default value is back
    assert alerts_tab.font_size_spin_box.value() == DEFAULT_PRESETS['info']['fontSize']


def test_zone_buttons_reflect_preset(alerts_tab):
    """The zone grid mirrors the preset's screen position"""
    # THEN: The info preset's bottom-right zone button is checked
    assert alerts_tab.zone_buttons[('right', 'bottom')].isChecked()

    # WHEN: Another zone is chosen and values are stored
    alerts_tab.zone_buttons[('center', 'top')].setChecked(True)

    # THEN: The preset follows
    assert alerts_tab.presets['info']['zoneH'] == 'center'
    assert alerts_tab.presets['info']['zoneV'] == 'top'
