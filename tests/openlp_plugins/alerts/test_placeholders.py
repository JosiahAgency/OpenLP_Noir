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
This module contains tests for the named-placeholder helpers used by
reusable alert templates.
"""
from openlp.plugins.alerts.lib.placeholders import find_placeholders, substitute_placeholders


def test_find_placeholders_returns_names_in_first_seen_order():
    """Placeholder names come back without braces, in the order they first appear"""
    names = find_placeholders('Car {plate} is blocking {location}, owned by {name}')

    assert names == ['plate', 'location', 'name']


def test_find_placeholders_deduplicates():
    """A placeholder used more than once is only reported once"""
    names = find_placeholders('{name}, please move your car. Thank you, {name}.')

    assert names == ['name']


def test_find_placeholders_none_present():
    """Text with no placeholders yields an empty list"""
    assert find_placeholders('No parameters here') == []


def test_find_placeholders_empty_text():
    """Empty/falsy text does not error"""
    assert find_placeholders('') == []
    assert find_placeholders(None) == []


def test_find_placeholders_ignores_malformed_braces():
    """Unclosed or empty braces are not treated as placeholders"""
    assert find_placeholders('{ } {} {unclosed') == []


def test_substitute_placeholders_replaces_known_values():
    """Known placeholders are swapped for their values"""
    result = substitute_placeholders('Car {plate} is blocking {location}',
                                     {'plate': 'KDA 123B', 'location': 'the exit'})

    assert result == 'Car KDA 123B is blocking the exit'


def test_substitute_placeholders_leaves_missing_values_untouched():
    """A placeholder with no supplied value is left as-is, visibly, rather than blanked"""
    result = substitute_placeholders('Car {plate} is blocking {location}', {'plate': 'KDA 123B'})

    assert result == 'Car KDA 123B is blocking {location}'


def test_substitute_placeholders_repeated_placeholder():
    """Every occurrence of a repeated placeholder is substituted"""
    result = substitute_placeholders('{name}, please move your car. Thank you, {name}.', {'name': 'Sam'})

    assert result == 'Sam, please move your car. Thank you, Sam.'


def test_substitute_placeholders_no_placeholders():
    """Plain text with no placeholders is returned unchanged"""
    assert substitute_placeholders('No parameters here', {'unused': 'value'}) == 'No parameters here'
