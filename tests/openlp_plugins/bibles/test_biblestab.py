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
This module contains tests for the lib submodule of the Bible plugin.
"""
import pytest
from unittest.mock import MagicMock, patch

from openlp.core.common.enum import ReferencePlacement
from openlp.core.common.registry import Registry
from openlp.plugins.bibles.lib.biblestab import BiblesTab

__default_settings__ = {
    'bibles/verse separator': 'verse separator',
    'bibles/range separator': 'range separator',
    'bibles/list separator': 'list separator',
    'bibles/end separator': 'end separator'
}


@pytest.fixture()
def form(settings):
    Registry().register('settings_form', MagicMock())
    Registry().get('settings').extend_default_settings(__default_settings__)
    frm = BiblesTab(None, 'Songs', None, None)
    frm.settings_form.register_post_process = MagicMock()
    return frm


def test_load_when_seperators_set_on_default(form):
    """
    Test that the separator checkboxes are still checked even when the default is used
    """
    # GIVEN: Seperator settings set as the default
    form.settings.setValue('bibles/verse separator', form.settings.value('bibles/verse separator'))
    form.settings.setValue('bibles/range separator', form.settings.value('bibles/range separator'))
    form.settings.setValue('bibles/list separator', form.settings.value('bibles/list separator'))
    form.settings.setValue('bibles/end separator', form.settings.value('bibles/end separator'))

    # WHEN: Load is invoked
    form.load()

    # THEN: The checkboxes should be checked
    assert form.verse_separator_check_box.isChecked() is True
    assert form.range_separator_check_box.isChecked() is True
    assert form.list_separator_check_box.isChecked() is True
    assert form.end_separator_check_box.isChecked() is True


def test_load_when_seperators_unset(form):
    """
    Test that the separator checkboxes are not checked when the setting is not set
    """
    # GIVEN: Seperator settings non existant
    form.settings.remove('bibles/verse separator')
    form.settings.remove('bibles/range separator')
    form.settings.remove('bibles/list separator')
    form.settings.remove('bibles/end separator')

    # WHEN: Load is invoked
    form.load()

    # THEN: The checkboxes should be checked
    assert form.verse_separator_check_box.isChecked() is False
    assert form.range_separator_check_box.isChecked() is False
    assert form.list_separator_check_box.isChecked() is False
    assert form.end_separator_check_box.isChecked() is False


def test_load_footer_defaults(form):
    """
    Test that the footer checkboxes are all checked by default
    """
    # WHEN: Load is invoked
    form.load()

    # THEN: All footer checkboxes should be checked
    assert form.footer_reference_check_box.isChecked() is True
    assert form.footer_version_check_box.isChecked() is True
    assert form.footer_copyright_check_box.isChecked() is True
    assert form.footer_permission_check_box.isChecked() is True


def test_save_footer_settings(form):
    """
    Test that the footer settings are saved from the checkboxes
    """
    # GIVEN: A loaded form with some footer checkboxes unchecked
    form.load()
    form.footer_version_check_box.setChecked(False)
    form.footer_copyright_check_box.setChecked(False)

    # WHEN: Save is invoked (without rebuilding the global reference separators)
    with patch('openlp.plugins.bibles.lib.biblestab.update_reference_separators'):
        form.save()

    # THEN: The settings should reflect the checkbox states
    assert form.settings.value('bibles/footer show reference') is True
    assert form.settings.value('bibles/footer show version') is False
    assert form.settings.value('bibles/footer show copyright') is False
    assert form.settings.value('bibles/footer show permission') is True


def test_load_reference_placement_default(form):
    """
    Test that reference placement defaults to Footer
    """
    # WHEN: Load is invoked
    form.load()

    # THEN: The combo box should default to Footer
    assert form.reference_placement_combo_box.currentIndex() == ReferencePlacement.Footer


def test_save_reference_placement(form):
    """
    Test that changing reference placement to Inline is saved
    """
    # GIVEN: A loaded form with the reference placement combo box set to Inline
    form.load()
    form.reference_placement_combo_box.setCurrentIndex(ReferencePlacement.Inline)
    form.on_reference_placement_combo_box_changed()

    # WHEN: Save is invoked (without rebuilding the global reference separators)
    with patch('openlp.plugins.bibles.lib.biblestab.update_reference_separators'):
        form.save()

    # THEN: The setting should reflect the combo box state
    assert form.settings.value('bibles/reference placement') == ReferencePlacement.Inline


def test_check_box_toggles_persist(form):
    """
    Test that checking a box back on is saved as True. The stateChanged signal
    delivers a plain int, so a naive comparison with Qt.CheckState.Checked is
    always False and every toggle would be stored (and saved) as False.
    """
    # GIVEN: A loaded form where checkboxes have been unchecked and re-checked by the user
    form.load()
    form.footer_version_check_box.setChecked(False)
    form.footer_version_check_box.setChecked(True)
    form.is_verse_number_visible_check_box.setChecked(False)
    form.is_verse_number_visible_check_box.setChecked(True)

    # WHEN: Save is invoked (without rebuilding the global reference separators)
    with patch('openlp.plugins.bibles.lib.biblestab.update_reference_separators'):
        form.save()

    # THEN: The re-checked boxes should be saved as True
    assert form.settings.value('bibles/footer show version') is True
    assert form.settings.value('bibles/is verse number visible') is True
