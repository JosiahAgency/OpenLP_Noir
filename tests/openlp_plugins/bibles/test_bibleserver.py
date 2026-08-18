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
This module contains tests for the http module of the Bibles plugin.
"""
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from bs4 import BeautifulSoup

from openlp.plugins.bibles.lib.importers.http import BSExtract


@pytest.fixture
def bsextract() -> BSExtract:
    yield BSExtract()


@pytest.mark.skip('BSExtract does not currently use http for books')
@patch('openlp.plugins.bibles.lib.importers.http.get_soup_for_bible_ref')
@patch('openlp.plugins.bibles.lib.importers.http.log')
@patch('openlp.plugins.bibles.lib.importers.http.urllib')
def test_get_books_from_http_no_soup(mocked_urllib: MagicMock, mocked_log: MagicMock, mocked_get_soup: MagicMock,
                                     bsextract: BSExtract):
    """
    Test the get_books_from_http method when get_soup_for_bible_ref returns a falsey value
    """
    # GIVEN: An instance of BSExtract, and log, urllib & get_soup_for_bible_ref mocks
    mocked_urllib.parse.quote.return_value = 'NIV'
    mocked_get_soup.return_value = None

    # WHEN: get_books_from_http is called with 'NIV' and get_soup_for_bible_ref returns a None value
    result = bsextract.get_books_from_http('NIV')

    # THEN: The rest mocks should be called with known values and get_books_from_http should return None
    mocked_log.debug.assert_called_once_with('BSExtract.get_books_from_http("{book}")'.format(book='NIV'))
    mocked_urllib.parse.quote.assert_called_once_with(b'NIV')
    mocked_get_soup.assert_called_once_with('http://m.bibleserver.com/overlay/selectBook?translation=NIV')
    assert result is None, \
        'BSExtract.get_books_from_http should return None when get_soup_for_bible_ref returns a false value'


@pytest.mark.skip('BSExtract does not currently use http for books')
@patch('openlp.plugins.bibles.lib.importers.http.get_soup_for_bible_ref')
@patch('openlp.plugins.bibles.lib.importers.http.log')
@patch('openlp.plugins.bibles.lib.importers.http.urllib')
@patch('openlp.plugins.bibles.lib.importers.http.send_error_message')
def test_get_books_from_http_no_content(mocked_send_error_message: MagicMock, mocked_urllib: MagicMock,
                                        mocked_log: MagicMock, mocked_get_soup: MagicMock, bsextract: BSExtract):
    """
    Test the get_books_from_http method when the specified element cannot be found in the tag object returned from
    get_soup_for_bible_ref
    """
    # GIVEN: An instance of BSExtract, and log, urllib, get_soup_for_bible_ref & soup mocks
    mocked_urllib.parse.quote.return_value = 'NIV'
    mocked_soup = MagicMock(**{'find.return_value': None})
    mocked_get_soup.return_value = mocked_soup

    # WHEN: get_books_from_http is called with 'NIV', get_soup_for_bible_ref returns a mocked_soup object and
    #       mocked_soup.find returns None
    result = bsextract.get_books_from_http('NIV')

    # THEN: The rest mocks should be called with known values and get_books_from_http should return None
    mocked_log.debug.assert_called_once_with('BSExtract.get_books_from_http("{book}")'.format(book='NIV'))
    mocked_urllib.parse.quote.assert_called_once_with(b'NIV')
    mocked_get_soup.assert_called_once_with(
        'http://m.bibleserver.com/overlay/selectBook?translation=NIV')
    mocked_soup.find.assert_called_once_with('ul')
    mocked_log.error.assert_called_once_with('No books found in the Bibleserver response.')
    mocked_send_error_message.assert_called_once_with('parse')
    assert result is None, \
        'BSExtract.get_books_from_http should return None when get_soup_for_bible_ref returns a false value'


@pytest.mark.skip('BSExtract does not currently use http for books')
@patch('openlp.plugins.bibles.lib.importers.http.get_soup_for_bible_ref')
@patch('openlp.plugins.bibles.lib.importers.http.log')
@patch('openlp.plugins.bibles.lib.importers.http.urllib')
@patch('openlp.plugins.bibles.lib.importers.http.send_error_message')
def test_get_books_from_http_content(mocked_send_error_message: MagicMock, mocked_urllib: MagicMock,
                                     mocked_log: MagicMock, mocked_get_soup: MagicMock, bsextract: BSExtract):
    """
    Test the get_books_from_http method with sample HTML
    Also a regression test for bug #1184869. (The anchor tag in the second list item is empty)
    """
    # GIVEN: An instance of BSExtract, and reset log, urllib & get_soup_for_bible_ref mocks and sample HTML data
    test_html = '<ul><li><a href="/overlay/selectChapter?tocBook=1">Genesis</a></li>' \
        '<li><a href="/overlay/selectChapter?tocBook=2"></a></li>' \
        '<li><a href="/overlay/selectChapter?tocBook=3">Leviticus</a></li></ul>'
    test_soup = BeautifulSoup(test_html, 'lxml')

    # WHEN: get_books_from_http is called with 'NIV' and get_soup_for_bible_ref returns tag object based on the
    #       supplied test data.
    mocked_urllib.parse.quote.return_value = 'NIV'
    mocked_get_soup.return_value = test_soup
    result = bsextract.get_books_from_http('NIV')

    # THEN: The rest mocks should be called with known values and get_books_from_http should return the two books
    #       in the test data
    mocked_log.debug.assert_called_once_with('BSExtract.get_books_from_http("{book}")'.format(book='NIV'))
    mocked_urllib.parse.quote.assert_called_once_with(b'NIV')
    mocked_get_soup.assert_called_once_with(
        'http://m.bibleserver.com/overlay/selectBook?translation=NIV')
    assert mocked_log.error.called is False, 'log.error should not have been called'
    assert mocked_send_error_message.called is False, 'send_error_message should not have been called'
    assert result == ['Genesis', 'Leviticus']


@patch('openlp.plugins.bibles.lib.importers.http.get_soup_for_bible_ref')
@patch('openlp.plugins.bibles.lib.importers.http.send_error_message')
@patch.object(BSExtract, 'application', new_callable=PropertyMock)
def test_get_bible_chapter_skips_malformed_verse_rows(mocked_application: PropertyMock,
                                                      mocked_send_error_message: MagicMock,
                                                      mocked_get_soup: MagicMock,
                                                      bsextract: BSExtract):
    """
    Test that malformed verse rows are skipped instead of raising errors.
    """
    # GIVEN: A chapter response with one valid verse and malformed entries
    test_html = (
        '<article class="chapter">'
        '<span class="verse"><span class="verse-number__group">1</span>'
        '<span class="verse-content--hover">In the beginning</span></span>'
        '<span class="verse"><span class="verse-content--hover">Missing number</span></span>'
        '<span class="verse"><span class="verse-number__group">abc</span>'
        '<span class="verse-content--hover">Bad number</span></span>'
        '</article>'
    )
    mocked_get_soup.return_value = BeautifulSoup(test_html, 'lxml')
    mocked_application.return_value = MagicMock()

    # WHEN: Parsing the chapter
    result = bsextract.get_bible_chapter('NIV', 'Genesis', 1)

    # THEN: Only valid verses are returned, and no parse error dialog is shown
    assert result is not None
    assert result.verse_list == {1: 'In the beginning'}
    assert mocked_send_error_message.called is False


@patch('openlp.plugins.bibles.lib.importers.http.get_soup_for_bible_ref')
@patch('openlp.plugins.bibles.lib.importers.http.send_error_message')
@patch.object(BSExtract, 'application', new_callable=PropertyMock)
def test_get_bible_chapter_errors_when_no_valid_verses(mocked_application: PropertyMock,
                                                       mocked_send_error_message: MagicMock,
                                                       mocked_get_soup: MagicMock,
                                                       bsextract: BSExtract):
    """
    Test that chapter parsing reports an error when no valid verse rows remain.
    """
    # GIVEN: A chapter where every verse row is malformed
    test_html = (
        '<article class="chapter">'
        '<span class="verse"><span class="verse-number__group">abc</span>'
        '<span class="verse-content--hover">Bad number</span></span>'
        '<span class="verse"><span class="verse-number__group">2</span>'
        '<span class="verse-content--hover"></span></span>'
        '</article>'
    )
    mocked_get_soup.return_value = BeautifulSoup(test_html, 'lxml')
    mocked_application.return_value = MagicMock()

    # WHEN: Parsing the chapter
    result = bsextract.get_bible_chapter('NIV', 'Genesis', 1)

    # THEN: No result is returned and parse error is reported
    assert result is None
    mocked_send_error_message.assert_called_once_with('parse')
