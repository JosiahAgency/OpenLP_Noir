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
Tests for the EGW Library reference parsing helpers.
"""
from types import SimpleNamespace

import pytest

from openlp.plugins.egwlibrary.lib import format_paragraph_reference, normalize_alias, parse_reference


@pytest.mark.parametrize('text, expected', [
    ('DA', 'da'),
    ('d.a.', 'da'),
    ('  Desire of Ages ', 'desireofages'),
    ('1SM', '1sm'),
    ('', ''),
])
def test_normalize_alias(text, expected):
    """
    Test that book names and aliases normalise to the same key regardless of case and
    punctuation.
    """
    assert normalize_alias(text) == expected


def test_parse_reference_book_only():
    """
    Test that a bare book name parses with no chapter or page.
    """
    reference = parse_reference('Desire of Ages')
    assert reference['book'] == 'Desire of Ages'
    assert reference['chapter'] is None
    assert reference['from_page'] is None


@pytest.mark.parametrize('text, chapter', [
    ('DA ch 5', 5),
    ('DA chapter 12', 12),
    ('DA chap. 3', 3),
    ('Steps to Christ ch1', 1),
])
def test_parse_reference_chapter(text, chapter):
    """
    Test the chapter reference forms.
    """
    reference = parse_reference(text)
    assert reference['chapter'] == chapter
    assert reference['from_page'] is None


def test_parse_reference_page():
    """
    Test that "DA 83" is a page reference.
    """
    reference = parse_reference('DA 83')
    assert reference['book'] == 'DA'
    assert reference['from_page'] == 83
    assert reference['from_para'] is None
    assert reference['to_page'] is None


def test_parse_reference_page_range():
    """
    Test that "DA 83-85" is a page range.
    """
    reference = parse_reference('DA 83-85')
    assert reference['from_page'] == 83
    assert reference['to_page'] == 85
    assert reference['from_para'] is None


def test_parse_reference_paragraph():
    """
    Test the standard EGW citation "DA 83.2".
    """
    reference = parse_reference('DA 83.2')
    assert reference['book'] == 'DA'
    assert reference['from_page'] == 83
    assert reference['from_para'] == 2


def test_parse_reference_paragraph_range_same_page():
    """
    Test that "DA 83.2-4" means paragraphs 2 to 4 on page 83, not pages 83 to 4.
    """
    reference = parse_reference('DA 83.2-4')
    assert reference['from_page'] == 83
    assert reference['from_para'] == 2
    assert reference['to_page'] == 83
    assert reference['to_para'] == 4


def test_parse_reference_paragraph_range_cross_page():
    """
    Test the cross page range "DA 83.2-84.1".
    """
    reference = parse_reference('DA 83.2-84.1')
    assert reference['from_page'] == 83
    assert reference['from_para'] == 2
    assert reference['to_page'] == 84
    assert reference['to_para'] == 1


def test_parse_reference_multi_word_book():
    """
    Test that a multi-word book title keeps the reference part separate.
    """
    reference = parse_reference('Steps to Christ 12.1')
    assert reference['book'] == 'Steps to Christ'
    assert reference['from_page'] == 12
    assert reference['from_para'] == 1


def test_parse_reference_numeric_abbreviation():
    """
    Test that abbreviations starting with a digit, like "3T" for Testimonies volume 3,
    parse correctly.
    """
    reference = parse_reference('3T 45.2')
    assert reference['book'] == '3T'
    assert reference['from_page'] == 45
    assert reference['from_para'] == 2


def test_parse_reference_en_dash():
    """
    Test that an en dash pasted from a document works as a range separator.
    """
    reference = parse_reference('DA 83.2–84.1')
    assert reference['to_page'] == 84
    assert reference['to_para'] == 1


def test_parse_reference_plain_text():
    """
    Test that a plain sentence still "parses" as a book-only match (the alias lookup
    is what decides it is not a reference).
    """
    reference = parse_reference('love of God')
    assert reference['book'] == 'love of God'
    assert reference['chapter'] is None
    assert reference['from_page'] is None


def test_parse_reference_empty():
    """
    Test that an empty string does not parse.
    """
    assert parse_reference('') is None
    assert parse_reference('   ') is None


def test_format_paragraph_reference_with_page():
    """
    Test the citation format for a paragraph with a page number.
    """
    paragraph = SimpleNamespace(page=83, para_on_page=2, paragraph_number=14)
    assert format_paragraph_reference('DA', paragraph) == 'DA 83.2'


def test_format_paragraph_reference_without_page():
    """
    Test that books imported without page numbers are cited by paragraph number.
    """
    paragraph = SimpleNamespace(page=0, para_on_page=0, paragraph_number=14)
    assert format_paragraph_reference('DA', paragraph) == 'DA ¶14'
