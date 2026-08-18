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
The :mod:`http` module enables OpenLP to retrieve scripture from bible websites.
"""
import json
import logging
import re
import socket
import urllib.error
import urllib.parse

from bs4 import BeautifulSoup, NavigableString, Tag

from openlp.core.common.httputils import get_web_page
from openlp.core.common.i18n import translate
from openlp.core.common.mixins import RegistryProperties
from openlp.core.common.registry import Registry
from openlp.core.lib.ui import critical_error_message_box
from openlp.plugins.bibles.lib import SearchResults
from openlp.plugins.bibles.lib.bibleimport import BibleImport
from openlp.plugins.bibles.lib.db import BibleDB, BiblesResourcesDB


CLEANER_REGEX = re.compile(r'&nbsp;|<br />|\'\+\'')
FIX_PUNKCTUATION_REGEX = re.compile(r'[ ]+([.,;])')
REDUCE_SPACES_REGEX = re.compile(r'[ ]{2,}')
UGLY_CHARS = {
    '\u2014': ' - ',
    '\u2018': '\'',
    '\u2019': '\'',
    '\u201c': '"',
    '\u201d': '"',
    '&nbsp;': ' '
}
VERSE_NUMBER_REGEX = re.compile(r'v(\d{1,2})(\d{3})(\d{3}) verse.*')


# Manually extracted from https://www.bibleserver.com/webmasters
BIBLESERVER_TRANSLATIONS = {
    'ESV': {'name': 'English Standard Version', 'lang': 'English', 'sections': ['OT', 'NT']},
    'NIV': {'name': 'New International Version', 'lang': 'English', 'sections': ['OT', 'NT']},
    'NIRV': {'name': 'New Int. Readers Version', 'lang': 'English', 'sections': ['OT', 'NT']},
    'KJV': {'name': 'King James Version', 'lang': 'English', 'sections': ['OT', 'NT']},
    'LUT': {'name': 'Lutherbibel 2017', 'lang': 'German', 'sections': ['OT', 'NT', 'Apocrypha']},
    'ELB': {'name': 'Elberfelder Bibel', 'lang': 'German', 'sections': ['OT', 'NT']},
    'HFA': {'name': 'Hoffnung für Alle', 'lang': 'German', 'sections': ['OT', 'NT']},
    'SLT': {'name': 'Schlachter 2000', 'lang': 'German', 'sections': ['OT', 'NT']},
    'ZB': {'name': 'Zürcher Bibel', 'lang': 'German', 'sections': ['OT', 'NT']},
    'NGÜ': {'name': 'Neue Genfer Übersetzung', 'lang': 'German', 'sections': ['OT', 'NT']},
    'GNB': {'name': 'Gute Nachricht Bibel', 'lang': 'German', 'sections': ['OT', 'NT', 'Apocrypha']},
    'EU': {'name': 'Einheitsübersetzung 2016', 'lang': 'German', 'sections': ['OT', 'NT', 'Apocrypha']},
    'NLB': {'name': 'Neues Leben. Die Bibel', 'lang': 'German', 'sections': ['OT', 'NT']},
    'NeÜ': {'name': 'Neue evangelistische Übersetzung', 'lang': 'German', 'sections': ['OT', 'NT']},
    'MENG': {'name': 'Menge Bibel', 'lang': 'German', 'sections': ['OT', 'NT', 'Apocrypha']},
    'BDS': {'name': 'Bible du Semeur', 'lang': 'French', 'sections': ['OT', 'NT']},
    'S21': {'name': 'Segond 21', 'lang': 'French', 'sections': ['OT', 'NT']},
    'ITA': {'name': 'La Parola è Vita', 'lang': 'Italian', 'sections': ['OT', 'NT']},
    'NRS': {'name': 'Nuova Riveduta 2006', 'lang': 'Italian', 'sections': ['OT', 'NT']},
    'HTB': {'name': 'Het Boek', 'lang': 'Dutch', 'sections': ['OT', 'NT']},
    'LSG': {'name': 'Louis Segond 1910', 'lang': 'French', 'sections': ['OT', 'NT']},
    'CST': {'name': 'Nueva Versión Internacional (Castilian) ', 'lang': 'Spanish', 'sections': ['OT', 'NT']},
    'NVI': {'name': 'Nueva Versión Internacional', 'lang': 'Spanish', 'sections': ['OT', 'NT']},
    'BTX': {'name': 'La Biblia Textual', 'lang': 'Spanish', 'sections': ['OT', 'NT']},
    'PRT': {'name': 'O Livro', 'lang': 'Portuguese', 'sections': ['OT', 'NT']},
    'NOR': {'name': 'En Levende Bok', 'lang': 'Norwegian', 'sections': ['OT', 'NT']},
    'BSV': {'name': 'Nya Levande Bibeln', 'lang': 'Swedish', 'sections': ['OT', 'NT']},
    'DK': {'name': 'Bibelen på hverdagsdansk', 'lang': 'Danish', 'sections': ['OT', 'NT']},
    'PSZ': {'name': 'Słowo Życia', 'lang': 'Polish', 'sections': ['OT', 'NT']},
    'CEP': {'name': 'Český ekumenický překlad', 'lang': 'Czech', 'sections': ['OT', 'NT', 'Apocrypha']},
    'SNC': {'name': 'Slovo na cestu', 'lang': 'Czech', 'sections': ['OT', 'NT']},
    'B21': {'name': 'Bible, překlad 21. století', 'lang': 'Czech', 'sections': ['OT', 'NT', 'Apocrypha']},
    'BKR': {'name': 'Bible Kralická', 'lang': 'Czech', 'sections': ['OT', 'NT']},
    'NPK': {'name': 'Nádej pre kazdého', 'lang': 'Slovak', 'sections': ['OT', 'NT']},
    'KAR': {'name': 'IBS-fordítás (Új Károli) ', 'lang': 'Hungarian', 'sections': ['OT']},
    'HUN': {'name': 'Hungarian', 'lang': 'Hungarian', 'sections': ['OT', 'NT']},
    'NTR': {'name': 'Noua traducere în limba românã', 'lang': 'Romanian', 'sections': ['OT', 'NT']},
    'BGV': {'name': 'Верен', 'lang': 'Bulgarian', 'sections': ['OT', 'NT']},
    'CBT': {'name': 'Библия, нов превод от оригиналните езици', 'lang': 'Bulgarian', 'sections': ['OT', 'NT',
                                                                                                  'Apocrypha']},
    'CKK': {'name': 'Knjiga O Kristu', 'lang': 'Croatian', 'sections': ['OT', 'NT']},
    'RSZ': {'name': 'Новый перевод на русский язык', 'lang': 'Russian', 'sections': ['OT', 'NT']},
    'CARS': {'name': 'Священное Писание, Восточный перевод', 'lang': 'Russian', 'sections': ['OT', 'NT']},
    'TR': {'name': 'Türkçe', 'lang': 'Turkish', 'sections': ['OT', 'NT']},
    'NAV': {'name': 'Ketab El Hayat', 'lang': 'Arabic', 'sections': ['OT', 'NT']},
    'FCB': {'name': 'کتاب مقدس، ترجمه تفسیری', 'lang': 'Persian', 'sections': ['OT', 'NT']},
    'CUVS': {'name': '中文和合本（简体） ', 'lang': 'Chinese (Simplified)', 'sections': ['OT', 'NT']},
    'CCBT': {'name': '聖經當代譯本修訂版', 'lang': 'Chinese (Simplified)', 'sections': ['OT', 'NT']},
}

BIBLESERVER_LANGUAGE_CODE = {
    'German': 'de',
    'English': 'en',
    'French': 'fr',
    'Italian': 'it',
    'Spanish': 'es',
    'Portuguese': 'pt',
    'Russian': 'ru',
    'Swedish': 'sv',
    'Norwegian': 'no',
    'Dutch': 'nl',
    'Czech': 'cs',
    'Slovak': 'sk',
    'Romanian': 'ro',
    'Croatian': 'hr',
    'Hungarian': 'hu',
    'Bulgarian': 'bg',
    'Arabic': 'ar',
    'Turkish': 'tr',
    'Polish': 'pl',
    'Danish': 'da',
    'Chinese (Simplified)': 'zh',
    'Persian': 'fa'
}

CROSSWALK_LANGUAGES = {
    'Portuguese': 'pt',
    'German': 'de',
    'Italian': 'it',
    'Español': 'es',
    'French': 'fr',
    'Dutch': 'nl'
}

log = logging.getLogger(__name__)


def parse_verse_number(verse):
    """
    Parse a verse number from raw HTML text.

    :param verse: The raw verse marker string from the source HTML.
    :return: The verse number as int, or None if it cannot be parsed.
    """
    if verse is None:
        return None
    verse = str(verse).strip()
    if not verse:
        return None
    if '-' in verse:
        # Some translations bundle verses together, for example 17-18.
        verse = verse.split('-', 1)[0]
    try:
        return int(verse)
    except ValueError:
        log.warning('Illegal verse number: %s', verse)
        return None


class BGExtract(RegistryProperties):
    """
    Extract verses from BibleGateway
    """
    NAME = 'BibleGateway'

    def __init__(self):
        log.debug('BGExtract.__init__()')
        socket.setdefaulttimeout(30)

    def _remove_elements(self, parent, tag, class_=None):
        """
        Remove a particular element from the BeautifulSoup tree.

        :param parent: The element from which items need to be removed.
        :param tag: A string of the tab type, e.g. "div"
        :param class_: An HTML class attribute for further qualification.
        """
        if class_:
            all_tags = parent.find_all(tag, class_)
        else:
            all_tags = parent.find_all(tag)
        for element in all_tags:
            element.extract()

    def _extract_verse(self, tag):
        """
        Extract a verse (or part of a verse) from a tag.

        :param tag: The BeautifulSoup Tag element with the stuff we want.
        """
        if isinstance(tag, NavigableString):
            return None, str(tag)
        elif tag.get('class') and (tag.get('class')[0] == 'versenum' or tag.get('class')[0] == 'versenum mid-line'):
            verse = str(tag.string).replace('[', '').replace(']', '').strip()
            return verse, None
        elif tag.get('class') and tag.get('class')[0] == 'chapternum':
            verse = '1'
            return verse, None
        else:
            verse = None
            text = ''
            for child in tag.contents:
                c_verse, c_text = self._extract_verse(child)
                if c_verse:
                    verse = c_verse
                if text and c_text:
                    text += c_text
                elif c_text is not None:
                    text = c_text
            return verse, text

    def _clean_soup(self, tag):
        """
        Remove all the rubbish from the HTML page.

        :param tag: The base tag within which we want to remove stuff.
        """
        self._remove_elements(tag, 'sup', 'crossreference')
        self._remove_elements(tag, 'sup', 'footnote')
        self._remove_elements(tag, 'div', 'footnotes')
        self._remove_elements(tag, 'div', 'crossrefs')
        self._remove_elements(tag, 'h3')
        self._remove_elements(tag, 'h4')
        self._remove_elements(tag, 'h5')

    def _extract_verses(self, tags):
        """
        Extract all the verses from a pre-prepared list of HTML tags.

        :param tags: A list of BeautifulSoup Tag elements.
        """
        verses = []
        tags = tags[::-1]
        current_text = ''
        for tag in tags:
            verse = None
            text = ''
            for child in tag.contents:
                c_verse, c_text = self._extract_verse(child)
                if c_verse:
                    verse = c_verse
                if text and c_text:
                    text += c_text
                elif c_text is not None:
                    text = c_text
            if not verse:
                current_text = text + ' ' + current_text
            else:
                text += ' ' + current_text
                current_text = ''
            if text:
                for old, new in UGLY_CHARS.items():
                    text = text.replace(old, new)
                text = ' '.join(text.split())
            if verse and text:
                verse = parse_verse_number(verse)
                if verse is None:
                    continue
                verses.append((verse, text))
        verse_list = {}
        for verse, text in verses[::-1]:
            verse_list[verse] = text
        return verse_list

    def _extract_verses_old(self, div):
        """
        Use the old style of parsing for those Bibles on BG who mysteriously have not been migrated to the new (still
        broken) HTML.

        :param div:  The parent div.
        """
        verse_list = {}
        # Cater for inconsistent mark up in the first verse of a chapter.
        first_verse = div.find('versenum')
        if first_verse and first_verse.contents:
            verse_list[1] = str(first_verse.contents[0])
        for verse in div('sup', 'versenum'):
            raw_verse_num = verse.next_element
            clean_verse_num = 0
            # Not all verses exist in all translations and may or may not be represented by a verse number. If they are
            # not fine, if they are it will probably be in a format that breaks int(). We will then have no idea what
            # garbage may be sucked in to the verse text so if we do not get a clean int() then ignore the verse
            # completely.
            try:
                clean_verse_num = int(str(raw_verse_num))
            except ValueError:
                verse_parts = str(raw_verse_num).split('-')
                if len(verse_parts) > 1:
                    clean_verse_num = int(verse_parts[0])
            except TypeError:
                log.warning('Illegal verse number: %s', raw_verse_num)
            if clean_verse_num:
                verse_text = raw_verse_num.next_element
                part = raw_verse_num.next_element.next_element
                while not (isinstance(part, Tag) and part.get('class')[0] == 'versenum'):
                    # While we are still in the same verse grab all the text.
                    if isinstance(part, NavigableString):
                        verse_text += part
                    if isinstance(part.next_element, Tag) and part.next_element.name == 'div':
                        # Run out of verses so stop.
                        break
                    part = part.next_element
                verse_list[clean_verse_num] = str(verse_text)
        return verse_list

    def get_bible_chapter(self, version, book_name, chapter):
        """
        Access and decode Bibles via the BibleGateway website.

        :param version: The version of the Bible like 31 for New International version.
        :param book_name: Name of the Book.
        :param chapter: Chapter number.
        """
        log.debug('BGExtract.get_bible_chapter("{version}", "{name}", "{chapter}")'.format(version=version,
                                                                                           name=book_name,
                                                                                           chapter=chapter))
        url_book_name = urllib.parse.quote(book_name.encode("utf-8"))
        url_params = 'search={name}+{chapter}&version={version}'.format(name=url_book_name,
                                                                        chapter=chapter,
                                                                        version=version)
        soup = get_soup_for_bible_ref(
            'http://www.biblegateway.com/passage/?{url}'.format(url=url_params),
            pre_parse_regex=r'<meta name.*?/>', pre_parse_substitute='')
        if not soup:
            return None
        div = soup.find('div', 'result-text-style-normal')
        if not div:
            return None
        self._clean_soup(div)
        span_list = div.find_all('span', 'text')
        log.debug('Span list: {span}'.format(span=span_list))
        if not span_list:
            # If we don't get any spans then we must have the old HTML format
            verse_list = self._extract_verses_old(div)
        else:
            verse_list = self._extract_verses(span_list)
        if not verse_list:
            log.debug('No content found in the BibleGateway response.')
            send_error_message('parse')
            return None
        return SearchResults(book_name, chapter, verse_list)

    def get_books_from_http(self, version):
        """
        Load a list of all books a Bible contains from BibleGateway website.

        :param version: The version of the Bible like NIV for New International Version
        """
        log.debug('BGExtract.get_books_from_http("{version}")'.format(version=version))
        url_params = urllib.parse.urlencode({'action': 'getVersionInfo', 'vid': '{version}'.format(version=version)})
        reference_url = 'http://www.biblegateway.com/versions/?{url}#books'.format(url=url_params)
        page_source = get_web_page(reference_url)
        if not page_source:
            send_error_message('download')
            return None
        try:
            soup = BeautifulSoup(page_source, 'lxml')
        except Exception:
            log.error('BeautifulSoup could not parse the Bible page.')
            send_error_message('parse')
            return None
        if not soup:
            send_error_message('parse')
            return None
        self.application.process_events()
        content = soup.find('table', 'infotable')
        if content:
            content = content.find_all('tr')
        if not content:
            log.error('No books found in the Biblegateway response.')
            send_error_message('parse')
            return None
        books = []
        for book in content:
            td_element = book.find('td', {'class': 'book-name'})
            if not td_element:
                continue
            strings = [text.strip() for text in td_element.stripped_strings if text.strip()]
            if not strings:
                continue
            book_name = strings[-1]
            if book_name:
                books.append(book_name)
        if not books:
            log.error('No books found in the Biblegateway response.')
            send_error_message('parse')
            return None
        return books

    def get_bibles_from_http(self):
        """
        Load a list of bibles from BibleGateway website.

        returns a list in the form [(biblename, biblekey, language_code)]
        """
        log.debug('BGExtract.get_bibles_from_http')
        bible_url = 'https://www.biblegateway.com/versions/'
        soup = get_soup_for_bible_ref(bible_url)
        if not soup:
            return None
        bible_select = soup.find('select', {'class': 'search-dropdown'})
        if not bible_select:
            log.debug('No select tags found - did site change?')
            return None
        option_tags = bible_select.find_all('option')
        if not option_tags:
            log.debug('No option tags found - did site change?')
            return None
        current_lang = ''
        bibles = []
        for ot in option_tags:
            tag_class = ''
            try:
                tag_class = ot['class'][0]
            except KeyError:
                tag_class = ''
            tag_text = ot.get_text()
            if tag_class == 'lang':
                current_lang = tag_text[tag_text.find('(') + 1:tag_text.find(')')].lower()
            elif tag_class == 'spacer':
                continue
            else:
                bibles.append((tag_text, ot['value'], current_lang))
        return bibles


class BSExtract(RegistryProperties):
    """
    Extract verses from Bibleserver.com
    """
    NAME = 'BibleServer'

    def __init__(self):
        log.debug('BSExtract.__init__()')
        socket.setdefaulttimeout(30)

    def get_bible_chapter(self, version, book_name, chapter):
        """
        Access and decode bibles via Bibleserver website

        :param version: The version of the bible like NIV for New International Version
        :param book_name: Text name of bible book e.g. Genesis, 1. John, 1John or Offenbarung
        :param chapter: Chapter number
        """
        log.debug('BSExtract.get_bible_chapter("{version}", "{book}", "{chapter}")'.format(version=version,
                                                                                           book=book_name,
                                                                                           chapter=chapter))
        url_version = urllib.parse.quote(version.encode("utf-8"))
        url_book_name = urllib.parse.quote(book_name.encode("utf-8"))
        chapter_url = 'https://bibleserver.com/{version}/{name}{chapter:d}'.format(version=url_version,
                                                                                   name=url_book_name,
                                                                                   chapter=chapter)
        soup = get_soup_for_bible_ref(chapter_url)
        if not soup:
            return None
        self.application.process_events()
        content = soup.find('article', 'chapter')
        if not content:
            log.error('No verses found in the Bibleserver response.')
            send_error_message('parse')
            return None
        # remove spans with footnotes
        for span in soup.find_all('span', 'footnote-tooltip'):
            span.decompose()
        # remove noscript tags
        for noscript in soup.find_all('noscript'):
            noscript.decompose()
        content = soup.find_all('span', 'verse')
        verses = {}
        for verse in content:
            self.application.process_events()
            verse_number_tag = verse.find('span', 'verse-number__group')
            verse_content_tag = verse.find('span', 'verse-content--hover')
            if not verse_number_tag or not verse_content_tag:
                log.debug('Skipping malformed verse in Bibleserver response')
                continue
            verse_number = parse_verse_number(verse_number_tag.get_text())
            if verse_number is None:
                continue
            verse_text = verse_content_tag.get_text().strip()
            if not verse_text:
                continue
            verses[verse_number] = verse_text
        if not verses:
            log.error('No valid verses found in the Bibleserver response.')
            send_error_message('parse')
            return None
        return SearchResults(book_name, chapter, verses)

    def get_books_from_http(self, version):
        """
        Load a list of all books a Bible contains from BiblesResourcesDB.

        :param version: The version of the Bible like NIV for New International Version
        """
        log.debug('BSExtract.get_books_from_http("{version}")'.format(version=version))
        # Parsing the book list from the website is near impossible, so we use the list from BiblesResourcesDB
        bible = BIBLESERVER_TRANSLATIONS.get(version)
        if not bible:
            log.error('Unknown Bibleserver translation: %s', version)
            return []
        all_books = BiblesResourcesDB.get_books()
        books = []
        for book in all_books:
            if book['testament_id'] == 1 and 'OT' in bible['sections']:
                books.append(book['name'])
            elif book['testament_id'] == 2 and 'NT' in bible['sections']:
                books.append(book['name'])
            elif book['testament_id'] == 3 and 'Apocrypha' in bible['sections']:
                books.append(book['name'])
        return books

    def get_bibles_from_http(self):
        """
        Load a list of bibles from Bibleserver website.

        returns a list in the form [(biblename, biblekey, language_code)]
        """
        log.debug('BSExtract.get_bibles_from_http')
        # we need to cheat a bit and load it from a hardcoded list since the website is not parsable anymore...
        bibles = []
        for bible in BIBLESERVER_TRANSLATIONS.keys():
            bible_item = BIBLESERVER_TRANSLATIONS[bible]
            bible_tuple = (bible_item['name'], bible, BIBLESERVER_LANGUAGE_CODE[bible_item['lang']])
            bibles.append(bible_tuple)
        return bibles


class CWExtract(RegistryProperties):
    """
    Extract verses from CrossWalk/BibleStudyTools
    """
    NAME = 'Crosswalk'

    def __init__(self):
        log.debug('CWExtract.__init__()')
        socket.setdefaulttimeout(30)

    def get_bible_chapter(self, version, book_name, chapter):
        """
        Access and decode bibles via the Crosswalk website

        :param version: The version of the Bible like niv for New International Version
        :param book_name:  Text name of in english e.g. 'gen' for Genesis
        :param chapter: Chapter number
        """
        log.debug('CWExtract.get_bible_chapter("{version}", "{book}", "{chapter}")'.format(version=version,
                                                                                           book=book_name,
                                                                                           chapter=chapter))
        url_book_name = book_name.replace(' ', '-')
        url_book_name = url_book_name.lower()
        url_book_name = urllib.parse.quote(url_book_name.encode("utf-8"))
        chapter_url = 'https://www.biblestudytools.com/{version}/{book}/{chapter}.html'.format(version=version,
                                                                                               book=url_book_name,
                                                                                               chapter=chapter)
        soup = get_soup_for_bible_ref(chapter_url)
        if not soup:
            return None
        self.application.process_events()
        verses_div = soup.find_all('div', {'data-verse-id': True})
        if not verses_div:
            log.error('No verses found in the CrossWalk response.')
            send_error_message('parse')
            return None
        verses = {}
        for verse in verses_div:
            self.application.process_events()
            verse_number = int(verse['data-verse-id'])
            tags_to_remove = verse.find_all(['a', 'sup', 'h3'])
            for tag in tags_to_remove:
                tag.decompose()
            verse_text = verse.get_text()
            self.application.process_events()
            # Fix up leading and trailing spaces, multiple spaces, and spaces between text and , and .
            verse_text = verse_text.strip('\n\r\t ')
            verse_text = REDUCE_SPACES_REGEX.sub(' ', verse_text)
            verse_text = FIX_PUNKCTUATION_REGEX.sub(r'\1', verse_text)
            verses[verse_number] = verse_text
        return SearchResults(book_name, chapter, verses)

    def get_books_from_http(self, version):
        """
        Load a list of all books a Bible contain from the Crosswalk website.

        :param version: The version of the bible like NIV for New International Version
        """
        log.debug('CWExtract.get_books_from_http("{version}")'.format(version=version))
        books_url = 'https://www.biblestudytools.com/api/bible/books-selection/?translationCode={version}'
        books_url = books_url.format(version=version)
        books = []
        books_page = get_web_page(books_url)
        if not books_page:
            log.error('No books found in the CrossWalk response.')
            send_error_message('parse')
            return books
        try:
            books_json = json.loads(books_page)
        except ValueError:
            log.exception('Unable to parse the CrossWalk books response.')
            send_error_message('parse')
            return books
        for book in books_json:
            if not isinstance(book, dict):
                continue
            # the link looks like this: https://www.biblestudytools.com/bla/2-corintios/
            link = book.get('link')
            if not isinstance(link, str):
                continue
            # remove trailing forward slash
            link = link.strip('/')
            # remove everything before the book name/code
            book_name = link[link.rfind('/') + 1:]
            # replace dash with space
            book_name = book_name.replace('-', ' ')
            books.append(book_name)
        return books

    def get_bibles_from_http(self):
        """
        Load a list of bibles from Crosswalk website.
        returns a list in the form [(biblename, biblekey, language_code)]
        """
        log.debug('CWExtract.get_bibles_from_http')
        bible_url = 'https://www.biblestudytools.com/'
        soup = get_soup_for_bible_ref(bible_url)
        if not soup:
            return None
        # Get all <option class="log-translation" ...> on the page
        options = soup.find_all('option', {'class': 'log-translation'})
        bibles = []
        for option in options:
            short_name = option['value']
            tag_text = str(option.contents[0]).strip()
            # The names of non-english bibles has their language in parentheses at the end
            if tag_text.endswith(')'):
                language = tag_text[tag_text.rfind('(') + 1:-1]
                if language in CROSSWALK_LANGUAGES:
                    language_code = CROSSWALK_LANGUAGES[language]
                else:
                    language_code = ''
            # ... except for those that don't...
            elif 'latin' in tag_text.lower():
                language_code = 'la'
            elif 'la biblia' in tag_text.lower() or 'nueva' in tag_text.lower():
                language_code = 'es'
            elif 'chinese' in tag_text.lower():
                language_code = 'zh'
            elif 'greek' in tag_text.lower():
                language_code = 'el'
            elif 'nova' in tag_text.lower():
                language_code = 'pt'
            else:
                language_code = 'en'
            bibles.append((tag_text, short_name, language_code))
        return bibles


class HTTPBible(BibleImport, RegistryProperties):
    log.info('{name} HTTPBible loaded'.format(name=__name__))

    def __init__(self, *args, **kwargs):
        """
        Finds all the bibles defined for the system. Creates an Interface Object for each bible containing connection
        information.

        Throws Exception if no Bibles are found.

        Init confirms the bible exists and stores the database path.
        """
        super().__init__(*args, **kwargs)
        self.download_source = kwargs['download_source']
        self.download_name = kwargs['download_name']
        self.language_id = None
        if 'path' in kwargs:
            self.path = kwargs['path']
        if 'language_id' in kwargs:
            self.language_id = kwargs['language_id']

    def do_import(self, bible_name=None):
        """
        Run the import. This method overrides the parent class method. Returns ``True`` on success, ``False`` on
        failure.
        """
        self.wizard.progress_bar.setMaximum(68)
        self.wizard.increment_progress_bar(translate('BiblesPlugin.HTTPBible',
                                                     'Registering Bible and loading books...'))
        self.save_meta('download_source', self.download_source)
        self.save_meta('download_name', self.download_name)
        if self.download_source.lower() == 'crosswalk':
            handler = CWExtract()
        elif self.download_source.lower() == 'biblegateway':
            handler = BGExtract()
        elif self.download_source.lower() == 'bibleserver':
            handler = BSExtract()
        books = handler.get_books_from_http(self.download_name)
        if not books:
            log.error('Importing books from {source} - download name: "{name}" '
                      'failed'.format(source=self.download_source, name=self.download_name))
            return False
        self.wizard.progress_bar.setMaximum(len(books) + 2)
        self.wizard.increment_progress_bar(translate('BiblesPlugin.HTTPBible', 'Registering Language...'))
        self.language_id = self.get_language_id(bible_name=bible_name)
        if not self.language_id:
            return False
        for book in books:
            if self.stop_import_flag:
                break
            self.wizard.increment_progress_bar(translate('BiblesPlugin.HTTPBible',
                                                         'Importing {book}...',
                                                         'Importing <book name>...').format(book=book))
            book_ref_id = self.get_book_ref_id_by_name(book, len(books), self.language_id)
            if not book_ref_id:
                log.error('Importing books from {source} - download name: "{name}" '
                          'failed'.format(source=self.download_source, name=self.download_name))
                return False
            book_details = BiblesResourcesDB.get_book_by_id(book_ref_id)
            log.debug('Book details: Name:{book}; id:{ref}; '
                      'testament_id:{detail}'.format(book=book,
                                                     ref=book_ref_id,
                                                     detail=book_details['testament_id']))
            self.create_book(book, book_ref_id, book_details['testament_id'])
        if self.stop_import_flag:
            return False
        else:
            return True

    def get_verses(self, reference_list, show_error=True):
        """
        A reimplementation of the ``BibleDB.get_verses`` method, this one is specifically for web Bibles. It first
        checks to see if the particular chapter exists in the DB, and if not it pulls it from the web. If the chapter
        DOES exist, it simply pulls the verses from the DB using the ancestor method.

        ``reference_list``
            This is the list of references the media manager item wants. It is a list of tuples, with the following
            format::

                (book_reference_id, chapter, start_verse, end_verse)

            Therefore, when you are looking for multiple items, simply break them up into references like this, bundle
            them into a list. This function then runs through the list, and returns an amalgamated list of ``Verse``
            objects. For example::

                [('35', 1, 1, 1), ('35', 2, 2, 3)]
        """
        log.debug('HTTPBible.get_verses("{ref}")'.format(ref=reference_list))
        for reference in reference_list:
            book_id = reference[0]
            db_book = self.get_book_by_book_ref_id(book_id)
            if not db_book:
                if show_error:
                    critical_error_message_box(
                        translate('BiblesPlugin', 'No Book Found'),
                        translate('BiblesPlugin', 'No matching book could be found in this Bible. Check that you have '
                                  'spelled the name of the book correctly.'))
                return []
            book = db_book.name
            if BibleDB.get_verse_count(self, book_id, reference[1]) == 0:
                self.application.set_busy_cursor()
                search_results = self.get_chapter(book, reference[1])
                if search_results and search_results.has_verse_list():
                    # We have found a book of the bible lets check to see
                    # if it was there. By reusing the returned book name
                    # we get a correct book. For example it is possible
                    # to request ac and get Acts back.
                    book_name = search_results.book
                    self.application.process_events()
                    # Check to see if book/chapter exists.
                    db_book = self.get_book(book_name)
                    self.create_chapter(db_book.id, search_results.chapter, search_results.verse_list)
                    self.application.process_events()
                self.application.set_normal_cursor()
            self.application.process_events()
        return BibleDB.get_verses(self, reference_list, show_error)

    def get_chapter(self, book, chapter):
        """
        Receive the request and call the relevant handler methods.
        """
        log.debug('HTTPBible.get_chapter("{book}", "{chapter}")'.format(book=book, chapter=chapter))
        log.debug('source = {source}'.format(source=self.download_source))
        if self.download_source.lower() == 'crosswalk':
            handler = CWExtract()
        elif self.download_source.lower() == 'biblegateway':
            handler = BGExtract()
        elif self.download_source.lower() == 'bibleserver':
            handler = BSExtract()
        return handler.get_bible_chapter(self.download_name, book, chapter)

    def get_chapter_count(self, book):
        """
        Return the number of chapters in a particular book.

        :param book: The book object to get the chapter count for.
        """
        log.debug('HTTPBible.get_chapter_count("{name}")'.format(name=book.name))
        return BiblesResourcesDB.get_chapter_count(book.book_reference_id)

    def get_verse_count(self, book_id, chapter):
        """
        Return the number of verses for the specified chapter and book.

        :param book_id: The name of the book.
        :param chapter: The chapter whose verses are being counted.
        """
        log.debug('HTTPBible.get_verse_count("{ref}", {chapter})'.format(ref=book_id, chapter=chapter))
        return BiblesResourcesDB.get_verse_count(book_id, chapter)


def get_soup_for_bible_ref(reference_url, headers=None, pre_parse_regex=None, pre_parse_substitute=None):
    """
    Gets a webpage and returns a parsed and optionally cleaned soup or None.

    :param reference_url: The URL to obtain the soup from.
    :param header: An optional HTTP header to pass to the bible web server.
    :param pre_parse_regex: A regular expression to run on the webpage. Allows manipulation of the webpage before
        passing to BeautifulSoup for parsing.
    :param pre_parse_substitute: The text to replace any matches to the regular expression with.
    """
    if not reference_url:
        return None
    try:
        page_source = get_web_page(reference_url, headers, update_openlp=True)
    except Exception:
        log.exception('Unable to download Bible %s, unknown exception occurred', reference_url)
        page_source = None
    if not page_source:
        send_error_message('download')
        return None
    if pre_parse_regex and pre_parse_substitute is not None:
        page_source = re.sub(pre_parse_regex, pre_parse_substitute, page_source)
    soup = None
    try:
        soup = BeautifulSoup(page_source, 'lxml')
        CLEANER_REGEX.sub('', str(soup))
    except Exception:
        log.exception('BeautifulSoup could not parse the bible page.')
    if not soup:
        send_error_message('parse')
        return None
    Registry().get('application').process_events()
    return soup


def send_error_message(error_type):
    """
    Send a standard error message informing the user of an issue.

    :param error_type: The type of error that occurred for the issue.
    """
    if error_type == 'download':
        critical_error_message_box(
            translate('BiblesPlugin.HTTPBible', 'Download Error'),
            translate('BiblesPlugin.HTTPBible', 'There was a problem downloading your verse selection. Please check '
                      'your Internet connection, and if this error continues to occur, please consider reporting a bug'
                      '.'))
    elif error_type == 'parse':
        critical_error_message_box(
            translate('BiblesPlugin.HTTPBible', 'Parse Error'),
            translate('BiblesPlugin.HTTPBible', 'There was a problem extracting your verse selection. If this error '
                      'continues to occur please consider reporting a bug.'))
