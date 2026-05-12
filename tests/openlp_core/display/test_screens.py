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
Package to test the openlp.core.lib.screenlist package.
"""
from unittest.mock import MagicMock, patch

from PySide6 import QtCore

from openlp.core.display.screens import Screen, ScreenList


def test_current_display_screen():
    """
    Test that the "current" property returns the first display screen
    """
    # GIVEN: A new ScreenList object with some screens
    screen_list = ScreenList()
    screen_list.screens = [
        Screen(number=0, geometry=QtCore.QRect(0, 0, 1024, 768), is_primary=True),
        Screen(number=1, geometry=QtCore.QRect(1024, 0, 1024, 768), is_primary=False, is_display=True)
    ]

    # WHEN: The current property is accessed
    screen = screen_list.current

    # THEN: It should be the display screen
    assert screen.number == 1
    assert screen.geometry == QtCore.QRect(1024, 0, 1024, 768)
    assert screen.is_primary is False
    assert screen.is_display is True


def test_current_primary_screen():
    """
    Test that the "current" property returns the first primary screen
    """
    # GIVEN: A new ScreenList object with some screens
    screen_list = ScreenList()
    screen_list.screens = [
        Screen(number=0, geometry=QtCore.QRect(0, 0, 1024, 768), is_primary=True)
    ]

    # WHEN: The current property is accessed
    screen = screen_list.current

    # THEN: It should be the display screen
    assert screen.number == 0
    assert screen.geometry == QtCore.QRect(0, 0, 1024, 768)
    assert screen.is_primary is True
    assert screen.is_display is False


@patch('openlp.core.display.screens.QtWidgets.QApplication.screens')
def test_create_screen_list(mocked_screens, settings):
    """
    Create the screen list
    """
    # GIVEN: Mocked application
    mocked_application = MagicMock()
    mocked_screen1 = MagicMock(**{'geometry.return_value': QtCore.QRect(0, 0, 1024, 768)})
    mocked_screen2 = MagicMock(**{'geometry.return_value': QtCore.QRect(1024, 0, 1024, 768)})
    mocked_application.screens.return_value = [mocked_screen1, mocked_screen2]
    mocked_application.primaryScreen.return_value = mocked_screen1

    # WHEN: create() is called
    screen_list = ScreenList.create(mocked_application)

    # THEN: The correct screens have been set up
    assert screen_list.screens[0].number == 0
    assert screen_list.screens[0].geometry == QtCore.QRect(0, 0, 1024, 768)
    assert screen_list.screens[0].is_primary is True
    assert screen_list.screens[0].is_display is False
    assert screen_list.screens[1].number == 1
    assert screen_list.screens[1].geometry == QtCore.QRect(1024, 0, 1024, 768)
    assert screen_list.screens[1].is_primary is False
    assert screen_list.screens[1].is_display is True


@patch('openlp.core.display.screens.QtWidgets.QApplication.screens')
def test_create_screen_list_with_settings_matching(mocked_screens, settings):
    """
    Create the screen list and match with saved settings
    """
    # GIVEN: Mocked application and saved screen settings
    mocked_application = MagicMock()
    settings.setValue('core/screens', {'0': {'number': 0, 'geometry': {'x': 0, 'y': 0, 'width': 1024, 'height': 768},
                                             'is_primary': True, 'is_display': False,
                                             'custom_geometry': {'x': 50, 'y': 50, 'width': 924, 'height': 668}},
                                       '1': {'number': 0, 'geometry': {'x': 1024, 'y': 0, 'width': 1024, 'height': 768},
                                             'is_primary': False, 'is_display': True,
                                             'custom_geometry': {'x': 50, 'y': 50, 'width': 924, 'height': 568}}})
    mocked_screen1 = MagicMock(**{'geometry.return_value': QtCore.QRect(0, 0, 1024, 768)})
    mocked_screen2 = MagicMock(**{'geometry.return_value': QtCore.QRect(1024, 0, 1024, 768)})
    mocked_application.screens.return_value = [mocked_screen1, mocked_screen2]
    mocked_application.primaryScreen.return_value = mocked_screen1

    # WHEN: create() is called
    screen_list = ScreenList.create(mocked_application)

    # THEN: The correct screens have been set up, matching the saved settings
    assert screen_list.screens[0].number == 0
    assert screen_list.screens[0].geometry == QtCore.QRect(0, 0, 1024, 768)
    assert screen_list.screens[0].is_primary is True
    assert screen_list.screens[0].is_display is False
    assert screen_list.screens[0].custom_geometry == QtCore.QRect(50, 50, 924, 668)
    assert screen_list.screens[1].number == 1
    assert screen_list.screens[1].geometry == QtCore.QRect(1024, 0, 1024, 768)
    assert screen_list.screens[1].is_primary is False
    assert screen_list.screens[1].is_display is True
    assert screen_list.screens[1].custom_geometry == QtCore.QRect(50, 50, 924, 568)


@patch('openlp.core.display.screens.QtWidgets.QApplication.screens')
@patch('openlp.core.display.screens.QtWidgets.QMessageBox.warning')
def test_create_screen_list_with_screen_unplugged(screen_warning, mocked_screens, settings):
    """
    Create the screen list where saved screens > os screens (ie display unplugged)
    """
    # GIVEN: Mocked application and saved screen settings
    mocked_application = MagicMock()
    settings.setValue('core/screens', {'0': {'number': 0,
                                             'geometry': {'x': -1024, 'y': 0, 'width': 1024, 'height': 768},
                                             'is_primary': False,
                                             'is_display': True,
                                             'custom_geometry': {'x': 50, 'y': 50, 'width': 924, 'height': 668}},
                                       '1': {'number': 0,
                                             'geometry': {'x': 0, 'y': 0, 'width': 1024, 'height': 768},
                                             'is_primary': True,
                                             'is_display': False,
                                             'custom_geometry': {'x': 50, 'y': 50, 'width': 924, 'height': 568}}})
    # set up mocked_screen to match the 2nd screen in the settings
    mocked_screen1 = MagicMock(**{'geometry.return_value': QtCore.QRect(0, 0, 1024, 768)})
    mocked_application.screens.return_value = [mocked_screen1]
    mocked_application.primaryScreen.return_value = mocked_screen1

    # WHEN: create() is called
    screen_list = ScreenList.create(mocked_application)

    # THEN: The correct screens have been set up
    assert len(screen_list.screens) == 1
    assert screen_list.screens[0].number == 0
    assert screen_list.screens[0].geometry == QtCore.QRect(0, 0, 1024, 768)
    assert screen_list.screens[0].is_primary is True
    # find_new_display_screen() sets this screen's is_display to True
    assert screen_list.screens[0].is_display is True
    assert screen_list.screens[0].custom_geometry == QtCore.QRect(50, 50, 924, 568)


@patch('openlp.core.display.screens.QtWidgets.QApplication.screens')
def test_create_screen_list_with_screen_replugged_1(mocked_screens, settings):
    """
    Create the screen list where saved screens < os screens (ie display plugged in again)
    with saved screen matching the first screen
    """
    # GIVEN: Mocked application and saved screen settings
    mocked_application = MagicMock()
    settings.setValue('core/screens', {'0': {'number': 0,
                                             'geometry': {'x': 0, 'y': 0, 'width': 1024, 'height': 768},
                                             'is_primary': True,
                                             'is_display': True,
                                             'custom_geometry': {'x': 50, 'y': 50, 'width': 924, 'height': 668}}})
    # set up mocked_screen so that mocked_screen1 matches saved screen
    mocked_screen1 = MagicMock(**{'geometry.return_value': QtCore.QRect(0, 0, 1024, 768)})
    mocked_screen2 = MagicMock(**{'geometry.return_value': QtCore.QRect(1024, 0, 1024, 768)})
    mocked_application.screens.return_value = [mocked_screen1, mocked_screen2]
    mocked_application.primaryScreen.return_value = mocked_screen1

    # WHEN: create() is called
    screen_list = ScreenList.create(mocked_application)

    # THEN: The correct screens have been set up
    assert screen_list.screens[0].number == 0
    assert screen_list.screens[0].geometry == QtCore.QRect(0, 0, 1024, 768)
    assert screen_list.screens[0].is_primary is True
    assert screen_list.screens[0].is_display is True
    assert screen_list.screens[0].custom_geometry == QtCore.QRect(50, 50, 924, 668)
    assert screen_list.screens[1].number == 1
    assert screen_list.screens[1].geometry == QtCore.QRect(1024, 0, 1024, 768)
    assert screen_list.screens[1].is_primary is False
    assert screen_list.screens[1].is_display is False
    assert screen_list.screens[1].custom_geometry is None


@patch('openlp.core.display.screens.QtWidgets.QApplication.screens')
def test_create_screen_list_with_screen_replugged_2(mocked_screens, settings):
    """
    Create the screen list where saved screens < os screens (ie display plugged in again)
    with saved screen matching the second screen
    """
    # GIVEN: Mocked application and saved screen settings
    mocked_application = MagicMock()
    settings.setValue('core/screens', {'0': {'number': 0,
                                             'geometry': {'x': 0, 'y': 0, 'width': 1024, 'height': 768},
                                             'is_primary': True,
                                             'is_display': True,
                                             'custom_geometry': {'x': 50, 'y': 50, 'width': 924, 'height': 668}}})
    # set up mocked_screen so that mocked_screen2 matches saved screen
    mocked_screen1 = MagicMock(**{'geometry.return_value': QtCore.QRect(-1024, 0, 1024, 768)})
    mocked_screen2 = MagicMock(**{'geometry.return_value': QtCore.QRect(0, 0, 1024, 768)})
    mocked_application.screens.return_value = [mocked_screen1, mocked_screen2]
    mocked_application.primaryScreen.return_value = mocked_screen2

    # WHEN: create() is called
    screen_list = ScreenList.create(mocked_application)

    # THEN: The correct screens have been set up
    assert screen_list.screens[0].number == 0
    assert screen_list.screens[0].geometry == QtCore.QRect(-1024, 0, 1024, 768)
    assert screen_list.screens[0].is_primary is False
    assert screen_list.screens[0].is_display is False
    assert screen_list.screens[0].custom_geometry is None
    assert screen_list.screens[1].number == 1
    assert screen_list.screens[1].geometry == QtCore.QRect(0, 0, 1024, 768)
    assert screen_list.screens[1].is_primary is True
    assert screen_list.screens[1].is_display is True
    assert screen_list.screens[1].custom_geometry == QtCore.QRect(50, 50, 924, 668)


@patch('openlp.core.display.screens.QtWidgets.QApplication.screens')
def test_screen_list_on_primary_changed(mocked_screens, settings, registry):
    """Test that the screen is correctly updated when a primary screen is changed"""
    # GIVEN: Mocked application
    mocked_application = MagicMock()
    mocked_screen1 = MagicMock(**{'geometry.return_value': QtCore.QRect(0, 0, 1024, 768)})
    mocked_screen2 = MagicMock(**{'geometry.return_value': QtCore.QRect(1024, 0, 1024, 768)})
    mocked_application.screens.return_value = [mocked_screen1, mocked_screen2]
    mocked_application.primaryScreen.return_value = mocked_screen1
    screen_list = ScreenList.create(mocked_application)

    # WHEN: on_primary_screen_changed() is called
    mocked_application.primaryScreen.return_value = mocked_screen2
    screen_list.on_primary_screen_changed()

    # THEN: The primary screen should have changed
    assert screen_list.screens[0].is_primary is False
    assert screen_list.screens[1].is_primary is True


def test_screen_list_get_screen_number():
    """Test ScreenList().get_screen_number() method works with a given dictionary"""
    # GIVEN: A screen list with an incomplete screen
    screen_list = ScreenList()
    screen_list.screens = [
        Screen(1, QtCore.QRect(0, 0, 1024, 768), is_primary=True),
        Screen(2, QtCore.QRect(0, 1024, 1024, 768), is_primary=False)
    ]

    # When searching for a screen number
    result = screen_list.get_screen_number({"geometry": {"x": 0, "y": 1024, "width": 1024, "height": 768},
                                            "is_primary": False})

    # THEN: The result should be None
    assert result == 2, 'ScreenList.get_screen_number() should return 2'


def test_screen_list_get_screen_number_incomplete():
    """Test that when the settings are incomplete (don't have a geometry) that the has_number method still works"""
    # GIVEN: A screen list with an incomplete screen
    screen_list = ScreenList()
    screen_list.screens = [
        Screen(1, QtCore.QRect(0, 0, 1024, 768), is_primary=True),
        Screen(2, QtCore.QRect(0, 1024, 1024, 768), is_primary=False)
    ]

    # When searching for a screen number
    result = screen_list.get_screen_number({"is_primary": True})

    # THEN: The result should be None
    assert result is None, 'ScreenList.get_screen_number() should return None'


def test_screen_from_dict():
    """Test that all the correct attributes are set when creating a screen from a dictionary"""
    # GIVEN: A dictionary of values
    screen_dict = {
        'number': 1,
        'geometry': {'x': 0, 'y': 0, 'width': 1920, 'height': 1080},
        'custom_geometry': {'x': 10, 'y': 10, 'width': 1900, 'height': 1060},
        'is_primary': True,
        'is_display': False
    }

    # WHEN: A screen object is created from a dictionary
    screen = Screen.from_dict(screen_dict)

    # THEN: A screen object with the correct attributes is created
    assert screen.number == 1
    assert screen.is_primary is True
    assert screen.is_display is False
    assert screen.geometry == QtCore.QRect(0, 0, 1920, 1080)
    assert screen.custom_geometry == QtCore.QRect(10, 10, 1900, 1060)


def test_screen_to_dict():
    """Test that the correct dictionary is generated"""
    # GIVEN: A screen object
    screen = Screen(1, QtCore.QRect(0, 0, 1920, 1080), QtCore.QRect(10, 10, 1900, 1060), True, False)

    # WHEN: A dictionary is generated
    screen_dict = screen.to_dict()

    # THEN: The dictionary should be correct
    expected_screen = {
        'number': 1,
        'geometry': {'x': 0, 'y': 0, 'width': 1920, 'height': 1080},
        'custom_geometry': {'x': 10, 'y': 10, 'width': 1900, 'height': 1060},
        'is_primary': True,
        'is_display': False
    }
    assert screen_dict == expected_screen


def test_screen_update():
    """Test that updating a screen object from a dictionary results in the correct attributes"""
    # GIVEN: A screen object and a dictionary with updated values
    screen = Screen(1, QtCore.QRect(0, 0, 1920, 1080), is_primary=True, is_display=False)
    updated_screen = {
        'geometry': {'x': 0, 'y': 0, 'width': 3840, 'height': 2160},
        'custom_geometry': {'x': 10, 'y': 10, 'width': 1900, 'height': 1060},
        'is_primary': False,
        'is_display': True
    }

    # WHEN: screen.update() is called
    screen.update(updated_screen)

    # Then the screen attributes should be correct
    assert screen.is_primary is False
    assert screen.is_display is True
    assert screen.geometry == QtCore.QRect(0, 0, 3840, 2160)
    assert screen.custom_geometry == QtCore.QRect(10, 10, 1900, 1060)


def test_screen_update_bad_geometry():
    """Test that updating a screen object from a dictionary results in the correct attributes"""
    # GIVEN: A screen object and a dictionary with updated values
    screen = Screen(1, QtCore.QRect(0, 0, 1920, 1080), is_primary=True, is_display=False)
    updated_screen = {
        'geometry': {'x': 0, 'y': 0, 'x2': 3840, 'y2': 2160},
        'custom_geometry': {'x': 10, 'y': 10, 'width': 1900, 'height': 1060},
        'is_primary': False,
        'is_display': True
    }

    # WHEN: screen.update() is called
    screen.update(updated_screen)

    # Then the screen attributes should be correct
    assert screen.is_primary is False
    assert screen.is_display is True
    assert screen.geometry == QtCore.QRect(0, 0, 1920, 1080)
    assert screen.custom_geometry == QtCore.QRect(10, 10, 1900, 1060)


def test_screen_to_str():
    """Test that the correct string is generated"""
    # GIVEN: A screen object
    screen = Screen(1, QtCore.QRect(0, 0, 1920, 1080), QtCore.QRect(10, 10, 1900, 1060), True, False)

    # WHEN: A string is generated
    screen_str = str(screen)

    # THEN: The string should be correct (screens are 0-based)
    assert screen_str == 'Screen 2 (primary)'


def test_screen_display_geometry():
    """Test that the display_geometry property returns the geometry when no custom geometry exists"""
    # GIVEN: A screen object
    screen = Screen(1, QtCore.QRect(0, 0, 1920, 1080), is_primary=True, is_display=False)

    # WHEN: The display_geometry property is accessed
    display_geometry = screen.display_geometry

    # THEN: The display geometry is correct
    assert display_geometry == QtCore.QRect(0, 0, 1920, 1080)


def test_screen_display_geometry_custom():
    """Test that the display_geometry property returns the custom geometry when it exists"""
    # GIVEN: A screen object
    screen = Screen(1, QtCore.QRect(0, 0, 1920, 1080), QtCore.QRect(10, 10, 1900, 1060), True, False)

    # WHEN: The display_geometry property is accessed
    display_geometry = screen.display_geometry

    # THEN: The display geometry is correct
    assert display_geometry == QtCore.QRect(10, 10, 1900, 1060)


def test_screen_repr():
    """Test that the correct screen representation is generated"""
    # GIVEN: A screen object
    screen = Screen(1, QtCore.QRect(0, 0, 1920, 1080), QtCore.QRect(10, 10, 1900, 1060), True, False)

    # WHEN: A string is generated
    screen_str = screen.__repr__()

    # THEN: The string should be correct (screens are 0-based)
    assert screen_str == '<Screen 2 (primary)>'


@patch('openlp.core.display.screens.QtWidgets.QApplication.screens')
def test_screen_removed(mocked_screens, settings):
    """Test that the screen list is correct after a new screen is removed"""
    # GIVEN: A screenlist of a mocked application with two screens
    mocked_application = MagicMock()
    mocked_screen1 = MagicMock(**{'geometry.return_value': QtCore.QRect(0, 0, 1024, 768)})
    mocked_screen2 = MagicMock(**{'geometry.return_value': QtCore.QRect(1024, 0, 1024, 768)})
    mocked_application.screens.return_value = [mocked_screen1, mocked_screen2]
    mocked_application.primaryScreen.return_value = mocked_screen1

    screen_list = ScreenList.create(mocked_application)

    # WHEN: Screen 2 is removed from the application
    mocked_application.screens.return_value = [mocked_screen1]
    screen_list.on_screen_removed(mocked_screen2)

    # THEN: We have 1 primary screen left in the list
    assert len(screen_list.screens) == 1
    assert screen_list.screens[0].number == 0
    assert screen_list.screens[0].geometry == QtCore.QRect(0, 0, 1024, 768)
    assert screen_list.screens[0].is_primary is True
    assert screen_list.screens[0].is_display is True


@patch('openlp.core.display.screens.QtWidgets.QApplication.screens')
def test_screen_removed_when_geometry_changed(mocked_screens, settings):
    """Test that screen removal matches by raw screen identity when geometry has changed"""
    # GIVEN: A screenlist of a mocked application with two screens
    mocked_application = MagicMock()
    mocked_screen1 = MagicMock(**{'geometry.return_value': QtCore.QRect(0, 0, 1024, 768)})
    mocked_screen2 = MagicMock(**{'geometry.return_value': QtCore.QRect(1024, 0, 1024, 768)})
    mocked_application.screens.return_value = [mocked_screen1, mocked_screen2]
    mocked_application.primaryScreen.return_value = mocked_screen1

    screen_list = ScreenList.create(mocked_application)

    # WHEN: Screen 2 is removed but Qt reports a changed geometry on the removed screen
    mocked_screen2.geometry.return_value = QtCore.QRect(0, 0, 800, 600)
    mocked_application.screens.return_value = [mocked_screen1]
    screen_list.on_screen_removed(mocked_screen2)

    # THEN: The correct screen is removed and the remaining one is display
    assert len(screen_list.screens) == 1
    assert screen_list.screens[0].number == 0
    assert screen_list.screens[0].geometry == QtCore.QRect(0, 0, 1024, 768)
    assert screen_list.screens[0].is_primary is True
    assert screen_list.screens[0].is_display is True


@patch('openlp.core.display.screens.QtWidgets.QApplication.screens')
def test_screen_added(mocked_screens, settings):
    """Test that the screen list is correct after a screen is added"""
    # GIVEN: A screenlist of a mocked application with one screen
    mocked_application = MagicMock()
    mocked_screen1 = MagicMock(**{'geometry.return_value': QtCore.QRect(0, 0, 1024, 768)})
    mocked_application.screens.return_value = [mocked_screen1]
    mocked_application.primaryScreen.return_value = mocked_screen1

    screen_list = ScreenList.create(mocked_application)

    # WHEN: Screen 2 is added to the application
    mocked_screen2 = MagicMock(**{'geometry.return_value': QtCore.QRect(1024, 0, 1024, 768)})
    mocked_application.screens.return_value = [mocked_screen1, mocked_screen2]
    screen_list.on_screen_added(mocked_screen2)

    # THEN: We have 2 screens, one primary, one display
    assert len(screen_list.screens) == 2
    assert screen_list.screens[0].number == 0
    assert screen_list.screens[0].geometry == QtCore.QRect(0, 0, 1024, 768)
    assert screen_list.screens[0].is_primary is True
    assert screen_list.screens[0].is_display is False
    assert screen_list.screens[1].number == 1
    assert screen_list.screens[1].geometry == QtCore.QRect(1024, 0, 1024, 768)
    assert screen_list.screens[1].is_primary is False
    assert screen_list.screens[1].is_display is True


@patch('openlp.core.display.screens.QtWidgets.QApplication.screens')
def test_screen_removed_added(mocked_screens, settings):
    """
    Test that the screen list is correct after a screen disappears and reappears again.
    This is a common scenario when a secondary screen (possibly a projector) is turned on and off, goes into standby
    or has a unstable connection. When the secondary screen returns it should also be marked display as before.
    """
    # GIVEN: A screenlist of a mocked application with two screens
    mocked_application = MagicMock()
    mocked_screen1 = MagicMock(**{'geometry.return_value': QtCore.QRect(0, 0, 1024, 768)})
    mocked_screen2 = MagicMock(**{'geometry.return_value': QtCore.QRect(1024, 0, 1024, 768)})
    mocked_application.screens.return_value = [mocked_screen1, mocked_screen2]
    mocked_application.primaryScreen.return_value = mocked_screen1

    # Create the screenlist with both screens present
    screen_list = ScreenList.create(mocked_application)

    # WHEN: Screen 2 is removed and added again
    # Remove screen 2
    mocked_application.screens.return_value = [mocked_screen1]
    screen_list.on_screen_removed(mocked_screen2)
    # Add screen 2
    mocked_application.screens.return_value = [mocked_screen1, mocked_screen2]
    screen_list.on_screen_added(mocked_screen2)

    # THEN: We have 2 screens, one primary, one display
    assert len(screen_list.screens) == 2
    assert screen_list.screens[0].number == 0
    assert screen_list.screens[0].geometry == QtCore.QRect(0, 0, 1024, 768)
    assert screen_list.screens[0].is_primary is True
    assert screen_list.screens[0].is_display is False
    assert screen_list.screens[1].number == 1
    assert screen_list.screens[1].geometry == QtCore.QRect(1024, 0, 1024, 768)
    assert screen_list.screens[1].is_primary is False
    assert screen_list.screens[1].is_display is True


@patch('openlp.core.display.screens.QtWidgets.QApplication.screens')
def test_third_screen_added(mocked_screens, settings):
    """Test that the screen list is correct after a third screen is added"""
    # GIVEN: A screenlist of a mocked application with one screen
    mocked_application = MagicMock()
    mocked_screen1 = MagicMock(**{'geometry.return_value': QtCore.QRect(0, 0, 1024, 768)})
    mocked_screen2 = MagicMock(**{'geometry.return_value': QtCore.QRect(1024, 0, 1024, 768)})
    mocked_application.screens.return_value = [mocked_screen1, mocked_screen2]
    mocked_application.primaryScreen.return_value = mocked_screen1

    screen_list = ScreenList.create(mocked_application)

    # WHEN: Screen 2 is added to the application
    mocked_screen3 = MagicMock(**{'geometry.return_value': QtCore.QRect(2048, 0, 1024, 768)})
    mocked_application.screens.return_value = [mocked_screen1, mocked_screen2, mocked_screen3]
    screen_list.on_screen_added(mocked_screen3)

    # THEN: We have 3 screens, one primary, one display, one that is neither.
    assert len(screen_list.screens) == 3
    assert screen_list.screens[0].number == 0
    assert screen_list.screens[0].geometry == QtCore.QRect(0, 0, 1024, 768)
    assert screen_list.screens[0].is_primary is True
    assert screen_list.screens[0].is_display is False
    assert screen_list.screens[1].number == 1
    assert screen_list.screens[1].geometry == QtCore.QRect(1024, 0, 1024, 768)
    assert screen_list.screens[1].is_primary is False
    assert screen_list.screens[1].is_display is True
    assert screen_list.screens[2].number == 2
    assert screen_list.screens[2].geometry == QtCore.QRect(2048, 0, 1024, 768)
    assert screen_list.screens[2].is_primary is False
    assert screen_list.screens[2].is_display is False


@patch('openlp.core.display.screens.QtWidgets.QApplication.screens')
def test_third_screen_removed(mocked_screens, settings):
    """Test that the screen list is correct after a third screen is removed"""
    # GIVEN: A screenlist of a mocked application with one screen
    mocked_application = MagicMock()
    mocked_screen1 = MagicMock(**{'geometry.return_value': QtCore.QRect(0, 0, 1024, 768)})
    mocked_screen2 = MagicMock(**{'geometry.return_value': QtCore.QRect(1024, 0, 1024, 768)})
    mocked_screen3 = MagicMock(**{'geometry.return_value': QtCore.QRect(2048, 0, 1024, 768)})
    mocked_application.screens.return_value = [mocked_screen1, mocked_screen2, mocked_screen3]
    mocked_application.primaryScreen.return_value = mocked_screen1

    screen_list = ScreenList.create(mocked_application)

    # WHEN: Screen 2 is added to the application
    mocked_application.screens.return_value = [mocked_screen1, mocked_screen2]
    screen_list.on_screen_removed(mocked_screen3)

    # THEN: We have 3 screens, one primary, one display, one that is neither.
    assert len(screen_list.screens) == 2
    assert screen_list.screens[0].number == 0
    assert screen_list.screens[0].geometry == QtCore.QRect(0, 0, 1024, 768)
    assert screen_list.screens[0].is_primary is True
    assert screen_list.screens[0].is_display is False
    assert screen_list.screens[1].number == 1
    assert screen_list.screens[1].geometry == QtCore.QRect(1024, 0, 1024, 768)
    assert screen_list.screens[1].is_primary is False
    assert screen_list.screens[1].is_display is True


@patch('openlp.core.display.screens.QtWidgets.QApplication.screens')
def test_swap_primary_screen(mocked_screens, settings):
    """Test that the screen list is correct after a different screen becomes a primary screen"""
    # GIVEN: A screenlist of a mocked application with two screens
    mocked_application = MagicMock()
    mocked_screen1 = MagicMock(**{'geometry.return_value': QtCore.QRect(0, 0, 1024, 768)})
    mocked_screen2 = MagicMock(**{'geometry.return_value': QtCore.QRect(1024, 0, 1024, 768)})
    mocked_application.screens.return_value = [mocked_screen1, mocked_screen2]
    mocked_application.primaryScreen.return_value = mocked_screen1

    # Create the screenlist with the initial state
    screen_list = ScreenList.create(mocked_application)

    # THEN: Make screen 2 the primary screen
    mocked_application.primaryScreen.return_value = mocked_screen2
    screen_list.on_primary_screen_changed()

    # THEN: The second screen is now primary
    assert len(screen_list.screens) == 2
    assert screen_list.screens[0].number == 0
    assert screen_list.screens[0].geometry == QtCore.QRect(0, 0, 1024, 768)
    assert screen_list.screens[0].is_primary is False
    assert screen_list.screens[0].is_display is True
    assert screen_list.screens[1].number == 1
    assert screen_list.screens[1].geometry == QtCore.QRect(1024, 0, 1024, 768)
    assert screen_list.screens[1].is_primary is True
    assert screen_list.screens[1].is_display is False
