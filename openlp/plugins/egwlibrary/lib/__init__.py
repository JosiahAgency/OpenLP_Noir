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
The :mod:`~openlp.plugins.egwlibrary.lib` module contains shared helpers for the EGW
Library plugin, most importantly the parsing of EGW references.

The reference grammar follows the citation format that is standard for the writings of
Ellen G. White, where ``DA 83.2`` means "The Desire of Ages, page 83, second paragraph
starting on that page"::

    DA              the whole book (browse its chapters)
    DA ch 5         chapter 5 (also "chap 5", "chapter 5", "ch. 5")
    DA 83           all paragraphs on page 83
    DA 83-85        all paragraphs on pages 83 to 85
    DA 83.2         page 83, paragraph 2
    DA 83.2-4       page 83, paragraphs 2 to 4
    DA 83.2-84.1    page 83 paragraph 2, through page 84 paragraph 1
"""
import re


# The book part is lazy so that a trailing reference is recognised whenever possible.
# No character restrictions are placed on the book part (EGW abbreviations such as
# "3T" or "1SM" start with a digit); the alias lookup decides whether it is a book.
REFERENCE_PATTERN = re.compile(r'''
    ^\s*
    (?P<book>\S+(?:\s+\S+)*?)
    (?:\s+(?:
        ch(?:ap(?:ter)?)?\.?\s*(?P<chapter>\d+)
        |
        (?P<from_page>\d+)(?:\.(?P<from_para>\d+))?
        (?:\s*-\s*(?P<to_page>\d+)(?:\.(?P<to_para>\d+))?)?
    ))?
    \s*$
''', re.IGNORECASE | re.VERBOSE)


def normalize_alias(text):
    """
    Normalise a book name or alias for lookups, so that "D.A.", "da" and "DA" all map
    to the same key.

    :param text: The book name, abbreviation or alias to normalise.
    :return: The normalised key, containing only lowercase letters and digits.
    """
    return re.sub(r'[^a-z0-9]', '', text.lower())


def parse_reference(text):
    """
    Try to parse a search string as an EGW reference.

    :param text: The search string, e.g. "DA 83.2" or "Desire of Ages ch 5".
    :return: A dict with the keys ``book``, ``chapter``, ``from_page``, ``from_para``,
        ``to_page`` and ``to_para`` (all except ``book`` may be None), or None if the
        string does not look like a reference at all.
    """
    # Normalise en/em dashes so "83.2–84.1" pasted from a document still parses.
    text = text.replace('–', '-').replace('—', '-')
    match = REFERENCE_PATTERN.match(text)
    if not match:
        return None
    reference = {
        'book': match.group('book').strip(),
        'chapter': None,
        'from_page': None,
        'from_para': None,
        'to_page': None,
        'to_para': None
    }
    if not reference['book']:
        return None
    for key in ['chapter', 'from_page', 'from_para', 'to_page', 'to_para']:
        if match.group(key) is not None:
            reference[key] = int(match.group(key))
    # "83.2-4" means paragraphs 2 to 4 on page 83, not pages 83 to 4.
    if reference['from_para'] is not None and reference['to_page'] is not None and reference['to_para'] is None:
        reference['to_para'] = reference['to_page']
        reference['to_page'] = reference['from_page']
    return reference


def format_paragraph_reference(abbreviation, paragraph):
    """
    Format the standard citation for a paragraph, e.g. "DA 83.2". Falls back to the
    paragraph number within the chapter when the book was imported without page numbers.

    :param abbreviation: The book abbreviation.
    :param paragraph: A Paragraph model instance.
    :return: The formatted reference string.
    """
    if paragraph.page:
        return '{abbr} {page}.{para}'.format(abbr=abbreviation, page=paragraph.page, para=paragraph.para_on_page)
    return '{abbr} ¶{number}'.format(abbr=abbreviation, number=paragraph.paragraph_number)
