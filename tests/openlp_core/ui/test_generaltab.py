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
Package to test the openlp.core.ui.generaltab package.
"""
from unittest.mock import patch

from openlp.core.ui.generaltab import GeneralTab
from openlp.core.ui.settingsform import SettingsForm
from openlp.core.ui.style import UiThemes

from PySide6 import QtCore, QtTest


def test_creation(settings):
    """
    Test that General Tab is created.
    """
    # GIVEN: A new General Tab
    settings_form = SettingsForm(None)

    # WHEN: I create an general tab
    general_tab = GeneralTab(settings_form)

    # THEN:
    assert "Core" == general_tab.tab_title, 'The tab title should be Core'


def test_change_search_as_type(settings):
    """
    Test that when search as type is changed custom and song configs are updated
    """
    # GIVEN: A new General Tab
    settings_form = SettingsForm(None)
    general_tab = GeneralTab(settings_form)

    # WHEN: I change search as type check box
    general_tab.on_search_as_type_check_box_changed(True)

    # THEN: we should have two post save processed to run
    assert 2 == len(settings_form.processes), 'Two post save processes should be created'
    assert "songs_config_updated" in settings_form.processes, 'The songs plugin should be called'
    assert "custom_config_updated" in settings_form.processes, 'The custom plugin should be called'


@patch('openlp.core.ui.generaltab.has_ui_theme')
def test_get_ui_theme_index_noir_with_qdarkstyle(mocked_has_ui_theme):
    """
    Test that the Noir theme maps to combo box index 4 when QDarkStyle is available
    """
    # GIVEN: QDarkStyle is available
    mocked_has_ui_theme.return_value = True

    # WHEN: the index for the Noir theme is requested
    index = GeneralTab.get_ui_theme_index(UiThemes.Noir)

    # THEN: the index should be 4
    assert index == 4


@patch('openlp.core.ui.generaltab.has_ui_theme')
def test_get_ui_theme_index_noir_without_qdarkstyle(mocked_has_ui_theme):
    """
    Test that the Noir theme maps to combo box index 3 when QDarkStyle is not available
    """
    # GIVEN: QDarkStyle is not available
    mocked_has_ui_theme.return_value = False

    # WHEN: the index for the Noir theme is requested
    index = GeneralTab.get_ui_theme_index(UiThemes.Noir)

    # THEN: the index should be 3
    assert index == 3


@patch('openlp.core.ui.generaltab.has_ui_theme')
def test_get_ui_theme_name_noir_with_qdarkstyle(mocked_has_ui_theme):
    """
    Test that combo box index 4 maps to the Noir theme when QDarkStyle is available
    """
    # GIVEN: QDarkStyle is available
    mocked_has_ui_theme.return_value = True

    # WHEN: the theme names for indexes 3, 4 and 5 are requested
    theme_at_3 = GeneralTab.get_ui_theme_name(3)
    theme_at_4 = GeneralTab.get_ui_theme_name(4)
    theme_at_5 = GeneralTab.get_ui_theme_name(5)

    # THEN: index 3 should be QDarkStyle, index 4 Noir and index 5 Noir Light
    assert theme_at_3 == UiThemes.QDarkStyle
    assert theme_at_4 == UiThemes.Noir
    assert theme_at_5 == UiThemes.NoirLight


@patch('openlp.core.ui.generaltab.has_ui_theme')
def test_get_ui_theme_name_noir_without_qdarkstyle(mocked_has_ui_theme):
    """
    Test that combo box index 3 maps to the Noir theme when QDarkStyle is not available
    """
    # GIVEN: QDarkStyle is not available
    mocked_has_ui_theme.return_value = False

    # WHEN: the theme names for indexes 3 and 4 are requested
    theme = GeneralTab.get_ui_theme_name(3)
    theme_light = GeneralTab.get_ui_theme_name(4)

    # THEN: index 3 should be Noir and index 4 should be Noir Light
    assert theme == UiThemes.Noir
    assert theme_light == UiThemes.NoirLight


@patch('openlp.core.ui.generaltab.has_ui_theme')
def test_get_ui_theme_index_noir_light_with_qdarkstyle(mocked_has_ui_theme):
    """
    Test that the Noir Light theme maps to combo box index 5 when QDarkStyle is available
    """
    mocked_has_ui_theme.return_value = True
    index = GeneralTab.get_ui_theme_index(UiThemes.NoirLight)
    assert index == 5


@patch('openlp.core.ui.generaltab.has_ui_theme')
def test_get_ui_theme_index_noir_light_without_qdarkstyle(mocked_has_ui_theme):
    """
    Test that the Noir Light theme maps to combo box index 4 when QDarkStyle is not available
    """
    mocked_has_ui_theme.return_value = False
    index = GeneralTab.get_ui_theme_index(UiThemes.NoirLight)
    assert index == 4


def test_slide_numbers_in_footer(settings):
    """
    Test that when the slide number in footers option is changed then the settings are updated
    """
    # GIVEN: Settings, a settings form and a general tab
    settings.setValue('advanced/slide numbers in footer', False)
    settings_form = SettingsForm(None)
    general_tab = GeneralTab(settings_form)
    settings_form.insert_tab(general_tab, is_visible=True)

    # WHEN: I click the checkbox and then save
    QtTest.QTest.mouseClick(general_tab.slide_no_in_footer_checkbox, QtCore.Qt.MouseButton.LeftButton)
    settings_form.accept()

    # THEN: the settings should be updated
    assert settings.value('advanced/slide numbers in footer') is True


def test_new_service_message(settings):
    """
    Test that when the new service message option is changed then the settings are updated
    """
    # GIVEN: Settings, a settings form and a general tab
    settings.setValue('advanced/new service message', True)
    settings_form = SettingsForm(None)
    general_tab = GeneralTab(settings_form)
    settings_form.insert_tab(general_tab, is_visible=True)

    # WHEN: I click the checkbox and then save
    QtTest.QTest.mouseClick(general_tab.new_service_message_check_box, QtCore.Qt.MouseButton.LeftButton)
    settings_form.accept()

    # THEN: the settings should be updated
    assert settings.value('advanced/new service message') is False
