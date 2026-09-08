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
Package to test the openlp.core.pages.alignment package.
"""

from unittest.mock import MagicMock

from openlp.core.pages.areaposition import AreaPositionPage


def test_init_(settings):
    """
    Test the initialisation of AreaPositionPage
    """
    # GIVEN: The AreaPositionPage class
    # WHEN: Initialising AreaPositionPage
    # THEN: We should have an instance of the widget with no errors
    AreaPositionPage()


def test_get_use_main_default_location(settings):
    """
    Test the use_main_default_location getter
    """
    # GIVEN: A AreaPositionPage instance with the combobox set to index 1
    page = AreaPositionPage()
    page.main_position_check_box.setChecked(False)

    # WHEN: The property is accessed
    result = page.use_main_default_location

    # THEN: The result should be correct
    assert result is False


def test_set_use_main_default_location(settings):
    """
    Test the use_main_default_location setter with an int
    """
    # GIVEN: A AreaPositionPage instance
    page = AreaPositionPage()

    # WHEN: The property is set
    page.use_main_default_location = True

    # THEN: The combobox should be correct
    assert page.main_position_check_box.isChecked() is True


def test_get_main_x(settings):
    """
    Test the main_x getter
    """
    # GIVEN: A AreaPositionPage instance with the combobox set to index 1
    page = AreaPositionPage()
    page.main_x_spin_box.setValue(10)

    # WHEN: The property is accessed
    result = page.main_x

    # THEN: The result should be correct
    assert result == 10


def test_set_main_x(settings):
    """
    Test the main_x setter with an int
    """
    # GIVEN: A AreaPositionPage instance
    page = AreaPositionPage()

    # WHEN: The property is set
    page.main_x = 20

    # THEN: The combobox should be correct
    assert page.main_x_spin_box.value() == 20


def test_get_main_y(settings):
    """
    Test the main_y getter
    """
    # GIVEN: A AreaPositionPage instance with the combobox set to indey 1
    page = AreaPositionPage()
    page.main_y_spin_box.setValue(10)

    # WHEN: The property is accessed
    result = page.main_y

    # THEN: The result should be correct
    assert result == 10


def test_set_main_y(settings):
    """
    Test the main_y setter with an int
    """
    # GIVEN: A AreaPositionPage instance
    page = AreaPositionPage()

    # WHEN: The property is set
    page.main_y = 20

    # THEN: The combobox should be correct
    assert page.main_y_spin_box.value() == 20


def test_get_main_width(settings):
    """
    Test the main_width getter
    """
    # GIVEN: A AreaPositionPage instance with the combobox set to indewidth 1
    page = AreaPositionPage()
    page.main_width_spin_box.setValue(10)

    # WHEN: The property is accessed
    result = page.main_width

    # THEN: The result should be correct
    assert result == 10


def test_set_main_width(settings):
    """
    Test the main_width setter with an int
    """
    # GIVEN: A AreaPositionPage instance
    page = AreaPositionPage()

    # WHEN: The property is set
    page.main_width = 20

    # THEN: The combobox should be correct
    assert page.main_width_spin_box.value() == 20


def test_get_main_height(settings):
    """
    Test the main_height getter
    """
    # GIVEN: A AreaPositionPage instance with the combobox set to indeheight 1
    page = AreaPositionPage()
    page.main_height_spin_box.setValue(10)

    # WHEN: The property is accessed
    result = page.main_height

    # THEN: The result should be correct
    assert result == 10


def test_set_main_height(settings):
    """
    Test the main_height setter with an int
    """
    # GIVEN: A AreaPositionPage instance
    page = AreaPositionPage()

    # WHEN: The property is set
    page.main_height = 20

    # THEN: The combobox should be correct
    assert page.main_height_spin_box.value() == 20


def test_get_footer_x(settings):
    """
    Test the footer_x getter
    """
    # GIVEN: A AreaPositionPage instance with the combobox set to index 1
    page = AreaPositionPage()
    page.footer_x_spin_box.setValue(10)

    # WHEN: The property is accessed
    result = page.footer_x

    # THEN: The result should be correct
    assert result == 10


def test_set_footer_x(settings):
    """
    Test the footer_x setter with an int
    """
    # GIVEN: A AreaPositionPage instance
    page = AreaPositionPage()

    # WHEN: The property is set
    page.footer_x = 20

    # THEN: The combobox should be correct
    assert page.footer_x_spin_box.value() == 20


def test_get_footer_y(settings):
    """
    Test the footer_y getter
    """
    # GIVEN: A AreaPositionPage instance with the combobox set to indey 1
    page = AreaPositionPage()
    page.footer_y_spin_box.setValue(10)

    # WHEN: The property is accessed
    result = page.footer_y

    # THEN: The result should be correct
    assert result == 10


def test_set_footer_y(settings):
    """
    Test the footer_y setter with an int
    """
    # GIVEN: A AreaPositionPage instance
    page = AreaPositionPage()

    # WHEN: The property is set
    page.footer_y = 20

    # THEN: The combobox should be correct
    assert page.footer_y_spin_box.value() == 20


def test_get_footer_width(settings):
    """
    Test the footer_width getter
    """
    # GIVEN: A AreaPositionPage instance with the combobox set to indewidth 1
    page = AreaPositionPage()
    page.footer_width_spin_box.setValue(1900)

    # WHEN: The property is accessed
    result = page.footer_width

    # THEN: The result should be correct
    assert result == 1900


def test_set_footer_width(settings):
    """
    Test the footer_width setter with an int
    """
    # GIVEN: A AreaPositionPage instance
    page = AreaPositionPage()

    # WHEN: The property is set
    page.footer_width = 1900

    # THEN: The combobox should be correct
    assert page.footer_width_spin_box.value() == 1900


def test_get_footer_height(settings):
    """
    Test the footer_height getter
    """
    # GIVEN: A AreaPositionPage instance with the combobox set to indeheight 1
    page = AreaPositionPage()
    page.footer_height_spin_box.setValue(1080)

    # WHEN: The property is accessed
    result = page.footer_height

    # THEN: The result should be correct
    assert result == 1080


def test_set_footer_height(settings):
    """
    Test the footer_height setter with an int
    """
    # GIVEN: A AreaPositionPage instance
    page = AreaPositionPage()

    # WHEN: The property is set
    page.footer_height = 1080

    # THEN: The combobox should be correct
    assert page.footer_height_spin_box.value() == 1080


def test_get_use_footer_default_location(settings):
    """
    Test the use_footer_default_location getter
    """
    # GIVEN: A AreaPositionPage instance with the combobox set to index 1
    page = AreaPositionPage()
    page.footer_position_check_box.setChecked(False)

    # WHEN: The property is accessed
    result = page.use_footer_default_location

    # THEN: The result should be correct
    assert result is False


def test_set_use_footer_default_location(settings):
    """
    Test the use_footer_default_location setter with an int
    """
    # GIVEN: A AreaPositionPage instance
    page = AreaPositionPage()

    # WHEN: The property is set
    page.use_footer_default_location = True

    # THEN: The combobox should be correct
    assert page.footer_position_check_box.isChecked() is True


def test_changed_signal_emitted_on_spin_box_value_change(settings):
    """
    Test that the changed signal fires when a position/size spin box value changes
    """
    # GIVEN: An AreaPositionPage instance with a slot connected to the changed signal
    page = AreaPositionPage()
    mocked_slot = MagicMock()
    page.changed.connect(mocked_slot)

    # WHEN: A spin box value is changed
    page.main_x_spin_box.setValue(page.main_x_spin_box.value() + 1)

    # THEN: The changed signal should have fired
    mocked_slot.assert_called_once()


def test_changed_signal_emitted_on_checkbox_toggle(settings):
    """
    Test that the changed signal fires when a "use default location" checkbox is toggled
    """
    # GIVEN: An AreaPositionPage instance with a slot connected to the changed signal
    page = AreaPositionPage()
    mocked_slot = MagicMock()
    page.changed.connect(mocked_slot)

    # WHEN: The main position checkbox is toggled
    page.main_position_check_box.setChecked(not page.main_position_check_box.isChecked())

    # THEN: The changed signal should have fired
    mocked_slot.assert_called_once()
