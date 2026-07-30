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
Package to test the openlp.core.ui.firsttimeform package.
"""
import datetime
from unittest.mock import patch

from openlp.core.ui.aboutform import AboutForm


@patch('openlp.core.ui.aboutform.webbrowser')
def test_on_contribute_button_clicked(mocked_webbrowser, mock_settings):
    """
    Test that clicking on the "Volunteer" button opens a web page.
    """
    # GIVEN: A new About dialog and a mocked out webbrowser module
    about_form = AboutForm(None)

    # WHEN: The "Volunteer" button is "clicked"
    about_form.on_contribute_button_clicked()

    # THEN: A web browser is opened
    mocked_webbrowser.open_new.assert_called_with('http://openlp.org/contribute')


@patch('openlp.core.ui.aboutform.get_version')
def test_about_form_build_number(mocked_get_version, mock_settings):
    """
    Test that the build number is added to the about form
    """
    # GIVEN: A mocked out get_version function
    mocked_get_version.return_value = {'version': '3.1.5', 'build': '3000'}

    # WHEN: The about form is created
    about_form = AboutForm(None)

    # THEN: The build number should be in the text
    assert 'OpenLP 3.1.5 build 3000' in about_form.about_text_edit.toPlainText(), \
        "The build number should be set correctly"


def test_about_form_ncsda_attribution(mock_settings):
    """
    Test that the NCSDA Version notice and developer attribution are shown
    """
    # WHEN: The about form is created
    about_form = AboutForm(None)
    about_text = about_form.about_text_edit.toPlainText()
    credits_text = about_form.credits_text_edit.toPlainText()

    # THEN: Both the About and Credits tabs should identify this as the NCSDA Version by George Josiah
    assert 'NCSDA Version' in about_text, "The About tab should state this is the NCSDA Version"
    assert 'George Josiah' in about_text, "The About tab should credit George Josiah"
    assert 'NCSDA Version' in credits_text, "The Credits tab should state this is the NCSDA Version"
    assert 'George Josiah' in credits_text, "The Credits tab should credit George Josiah"


def test_about_form_date(mock_settings):
    """
    Test that the copyright date is included correctly
    """
    # GIVEN: A correct application date
    date_string = '2004-{year}'.format(year=datetime.date.today().year)

    # WHEN: The about form is created
    about_form = AboutForm(None)
    about_text = about_form.about_text_edit.toPlainText()

    # THEN: The date should be in the text twice.
    assert about_text.count(date_string, 0) == 1, "The text string should be added twice to the license string"


@patch('openlp.core.ui.aboutform.is_ui_theme', return_value=True)
def test_about_form_logo_background_noir(mocked_is_ui_theme, mock_settings):
    """
    Test that the logo background is transparent under the Noir theme, not a hardcoded white box
    """
    # WHEN: The about form is created with the Noir theme active
    about_form = AboutForm(None)

    # THEN: The logo label should have a transparent background
    assert 'background-color: transparent' in about_form.logo_label.styleSheet()


@patch('openlp.core.ui.aboutform.is_ui_theme', return_value=False)
def test_about_form_logo_background_legacy(mocked_is_ui_theme, mock_settings):
    """
    Test that the logo background stays white under non-Noir themes, unchanged from before
    """
    # WHEN: The about form is created with a non-Noir theme active
    about_form = AboutForm(None)

    # THEN: The logo label should keep its original white background
    assert 'background-color: #fff' in about_form.logo_label.styleSheet()
