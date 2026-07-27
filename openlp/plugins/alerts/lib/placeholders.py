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
The :mod:`~openlp.plugins.alerts.lib.placeholders` module finds and fills in
the named placeholders (e.g. ``{plate}``) that let one saved alert template
be reused with different details each time it is triggered.
"""
import re


PLACEHOLDER_RE = re.compile(r'\{(\w+)\}')


def find_placeholders(text):
    """
    The unique placeholder names in ``text``, in the order they first appear.

    :param text: The alert text.
    :return: A list of placeholder names, without the surrounding braces.
    """
    names = []
    for name in PLACEHOLDER_RE.findall(text or ''):
        if name not in names:
            names.append(name)
    return names


def substitute_placeholders(text, values):
    """
    Replace each ``{name}`` placeholder in ``text`` with its value. A
    placeholder with no matching entry in ``values`` is left untouched, so a
    missing value is visible rather than silently disappearing.

    :param text: The alert text.
    :param values: A dict of placeholder name -> replacement value.
    :return: The text with all known placeholders substituted.
    """
    def _replace(match):
        name = match.group(1)
        if name in values:
            return str(values[name])
        return match.group(0)
    return PLACEHOLDER_RE.sub(_replace, text or '')
