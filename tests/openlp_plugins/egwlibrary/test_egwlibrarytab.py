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
This module contains tests for the lib submodule of the EGW Library plugin.
"""
import pytest
from unittest.mock import MagicMock

from openlp.core.common.enum import ReferencePlacement
from openlp.core.common.registry import Registry
from openlp.plugins.egwlibrary.lib.egwlibrarytab import EGWLibraryTab


@pytest.fixture()
def form(settings):
    Registry().register('settings_form', MagicMock())
    frm = EGWLibraryTab(None, 'egwlibrary')
    frm.settings_form.register_post_process = MagicMock()
    return frm


def test_load_footer_defaults(form):
    """
    Test that the footer checkboxes are all checked by default
    """
    # WHEN: Load is invoked
    form.load()

    # THEN: All footer checkboxes should be checked
    assert form.footer_reference_check_box.isChecked() is True
    assert form.footer_copyright_check_box.isChecked() is True


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

    # WHEN: Save is invoked
    form.save()

    # THEN: The setting should reflect the combo box state
    assert form.settings.value('egwlibrary/reference placement') == ReferencePlacement.Inline
