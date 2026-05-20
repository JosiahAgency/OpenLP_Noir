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
The :mod:`~openlp.plugins.songs.lib` module contains a number of library functions and classes used in the Songs plugin.
"""
import logging
import os
import re

from PySide6 import QtWidgets

from openlp.core.common import CONTROL_CHARS
from openlp.core.common.applocation import AppLocation
from openlp.core.common.i18n import translate
from openlp.core.common.registry import Registry
from openlp.core.display.render import remove_tags
from openlp.plugins.songs.lib.db import Author, MediaFile, Song
from openlp.plugins.songs.lib.ui import SongStrings

log = logging.getLogger(__name__)

WHITESPACE = re.compile(r'[\W_]+')
APOSTROPHE = re.compile(r'[\'`’ʻ′]')
# PATTERN will look for the next occurence of one of these symbols:
#   \controlword - optionally preceded by \*, optionally followed by a number
#   \'## - where ## is a pair of hex digits, representing a single character
#   \# - where # is a single non-alpha character, representing a special symbol
#   { or } - marking the beginning/end of a group
#   a run of characters without any \ { } or end-of-line
PATTERN = re.compile(
    r"(\\\*)?\\([a-z]{1,32})(-?\d{1,10})?[ ]?|\\'([0-9a-f]{2})|\\([^a-z*])|([{}])|[\r\n]+|([^\\{}\r\n]+)", re.I)
# RTF control words which specify a "destination" to be ignored.
DESTINATIONS = frozenset((
    'aftncn', 'aftnsep', 'aftnsepc', 'annotation', 'atnauthor', 'atndate', 'atnicn', 'atnid', 'atnparent', 'atnref',
    'atntime', 'atrfend', 'atrfstart', 'author', 'background', 'bkmkend', 'bkmkstart', 'blipuid', 'buptim', 'category',
    'colorschememapping', 'colortbl', 'comment', 'company', 'creatim', 'datafield', 'datastore', 'defchp', 'defpap',
    'do', 'doccomm', 'docvar', 'dptxbxtext', 'ebcend', 'ebcstart', 'factoidname', 'falt', 'fchars', 'ffdeftext',
    'ffentrymcr', 'ffexitmcr', 'ffformat', 'ffhelptext', 'ffl', 'ffname', 'ffstattext', 'file', 'filetbl', 'fldinst',
    'fldtype', 'fname', 'fontemb', 'fontfile', 'footer', 'footerf', 'footerl', 'footerr', 'footnote', 'formfield',
    'ftncn', 'ftnsep', 'ftnsepc', 'g', 'generator', 'gridtbl', 'header', 'headerf', 'headerl', 'headerr', 'hl', 'hlfr',
    'hlinkbase', 'hlloc', 'hlsrc', 'hsv', 'htmltag', 'info', 'keycode', 'keywords', 'latentstyles', 'lchars',
    'levelnumbers', 'leveltext', 'lfolevel', 'linkval', 'list', 'listlevel', 'listname', 'listoverride',
    'listoverridetable', 'listpicture', 'liststylename', 'listtable', 'listtext', 'lsdlockedexcept', 'macc', 'maccPr',
    'mailmerge', 'maln', 'malnScr', 'manager', 'margPr', 'mbar', 'mbarPr', 'mbaseJc', 'mbegChr', 'mborderBox',
    'mborderBoxPr', 'mbox', 'mboxPr', 'mchr', 'mcount', 'mctrlPr', 'md', 'mdeg', 'mdegHide', 'mden', 'mdiff', 'mdPr',
    'me', 'mendChr', 'meqArr', 'meqArrPr', 'mf', 'mfName', 'mfPr', 'mfunc', 'mfuncPr', 'mgroupChr', 'mgroupChrPr',
    'mgrow', 'mhideBot', 'mhideLeft', 'mhideRight', 'mhideTop', 'mhtmltag', 'mlim', 'mlimloc', 'mlimlow', 'mlimlowPr',
    'mlimupp', 'mlimuppPr', 'mm', 'mmaddfieldname', 'mmath', 'mmathPict', 'mmathPr', 'mmaxdist', 'mmc', 'mmcJc',
    'mmconnectstr', 'mmconnectstrdata', 'mmcPr', 'mmcs', 'mmdatasource', 'mmheadersource', 'mmmailsubject', 'mmodso',
    'mmodsofilter', 'mmodsofldmpdata', 'mmodsomappedname', 'mmodsoname', 'mmodsorecipdata', 'mmodsosort', 'mmodsosrc',
    'mmodsotable', 'mmodsoudl', 'mmodsoudldata', 'mmodsouniquetag', 'mmPr', 'mmquery', 'mmr', 'mnary', 'mnaryPr',
    'mnoBreak', 'mnum', 'mobjDist', 'moMath', 'moMathPara', 'moMathParaPr', 'mopEmu', 'mphant', 'mphantPr', 'mplcHide',
    'mpos', 'mr', 'mrad', 'mradPr', 'mrPr', 'msepChr', 'mshow', 'mshp', 'msPre', 'msPrePr', 'msSub', 'msSubPr',
    'msSubSup', 'msSubSupPr', 'msSup', 'msSupPr', 'mstrikeBLTR', 'mstrikeH', 'mstrikeTLBR', 'mstrikeV', 'msub',
    'msubHide', 'msup', 'msupHide', 'mtransp', 'mtype', 'mvertJc', 'mvfmf', 'mvfml', 'mvtof', 'mvtol', 'mzeroAsc',
    'mzFrodesc', 'mzeroWid', 'nesttableprops', 'nextfile', 'nonesttables', 'objalias', 'objclass', 'objdata', 'object',
    'objname', 'objsect', 'objtime', 'oldcprops', 'oldpprops', 'oldsprops', 'oldtprops', 'oleclsid', 'operator',
    'panose', 'password', 'passwordhash', 'pgp', 'pgptbl', 'picprop', 'pict', 'pn', 'pnseclvl', 'pntext', 'pntxta',
    'pntxtb', 'printim', 'private', 'propname', 'protend', 'protstart', 'protusertbl', 'pxe', 'result', 'revtbl',
    'revtim', 'rsidtbl', 'rxe', 'shp', 'shpgrp', 'shpinst', 'shppict', 'shprslt', 'shptxt', 'sn', 'sp', 'staticval',
    'stylesheet', 'subject', 'sv', 'svb', 'tc', 'template', 'themedata', 'title', 'txe', 'ud', 'upr', 'userprops',
    'wgrffmtfilter', 'windowcaption', 'writereservation', 'writereservhash', 'xe', 'xform', 'xmlattrname',
    'xmlattrvalue', 'xmlclose', 'xmlname', 'xmlnstbl', 'xmlopen'
))
# Translation of some special characters.
SPECIAL_CHARS = {
    '\n': '\n',
    '\r': '\n',
    '~': '\u00A0',
    '-': '\u00AD',
    '_': '\u2011',
    'par': '\n',
    'sect': '\n\n',
    # Required page and column break.
    # Would be good if we could split verse into subverses here.
    'page': '\n\n',
    'column': '\n\n',
    # Soft breaks.
    'softpage': '[---]',
    'softcol': '[---]',
    'line': '\n',
    'tab': '\t',
    'emdash': '\u2014',
    'endash': '\u2013',
    'emspace': '\u2003',
    'enspace': '\u2002',
    'qmspace': '\u2005',
    'bullet': '\u2022',
    'lquote': '\u2018',
    'rquote': '\u2019',
    'ldblquote': '\u201C',
    'rdblquote': '\u201D',
    'ltrmark': '\u200E',
    'rtlmark': '\u200F',
    'zwj': '\u200D',
    'zwnj': '\u200C'
}
CHARSET_MAPPING = {
    '0': 'cp1252',
    '128': 'cp932',
    '129': 'cp949',
    '134': 'cp936',
    '161': 'cp1253',
    '162': 'cp1254',
    '163': 'cp1258',
    '177': 'cp1255',
    '178': 'cp1256',
    '186': 'cp1257',
    '204': 'cp1251',
    '222': 'cp874',
    '238': 'cp1250'
}


class VerseType(object):
    """
    VerseType provides an enumeration for the tags that may be associated with verses in songs.
    """
    Verse = 0
    Chorus = 1
    Bridge = 2
    PreChorus = 3
    Intro = 4
    Ending = 5
    Other = 6

    names = ['Verse', 'Chorus', 'Bridge', 'Pre-Chorus', 'Intro', 'Ending', 'Other']
    tags = [name[0].lower() for name in names]
    translated_names = names
    translated_tags = tags

    @staticmethod
    def translated_tag(verse_tag, default=Other):
        """
        Return the translated UPPERCASE tag for a given tag, used to show translated verse tags in UI

        :param verse_tag: The string to return a VerseType for
        :param default: Default return value if no matching tag is found
        :return: A translated UPPERCASE tag
        """
        verse_tag = verse_tag[0].lower()
        for num, tag in enumerate(VerseType.tags):
            if verse_tag == tag:
                return VerseType.translated_tags[num].upper()
        if len(VerseType.names) > default:
            return VerseType.translated_tags[default].upper()
        else:
            return VerseType.translated_tags[VerseType.Other].upper()

    @staticmethod
    def translated_name(verse_tag, default=Other):
        """
        Return the translated name for a given tag

        :param verse_tag: The string to return a VerseType for
        :param default: Default return value if no matching tag is found
        :return: Translated name for the given tag
        """
        verse_tag = verse_tag[0].lower()
        for num, tag in enumerate(VerseType.tags):
            if verse_tag == tag:
                return VerseType.translated_names[num]
        if len(VerseType.names) > default:
            return VerseType.translated_names[default]
        else:
            return VerseType.translated_names[VerseType.Other]

    @staticmethod
    def from_tag(verse_tag, default=Other):
        """
        Return the VerseType for a given tag

        :param verse_tag: The string to return a VerseType for
        :param default: Default return value if no matching tag is found (a valid VerseType or None)
        :return: A VerseType of the tag
        """
        verse_tag = verse_tag[0].lower()
        for num, tag in enumerate(VerseType.tags):
            if verse_tag == tag:
                return num
        if default in range(0, len(VerseType.names)) or default is None:
            return default
        else:
            return VerseType.Other

    @staticmethod
    def from_translated_tag(verse_tag, default=Other):
        """
        Return the VerseType for a given tag

        :param verse_tag: The string to return a VerseType for
        :param default: Default return value if no matching tag is found
        :return: The VerseType of a translated tag
        """
        verse_tag = verse_tag[0].lower()
        for num, tag in enumerate(VerseType.translated_tags):
            if verse_tag == tag:
                return num
        if default in range(0, len(VerseType.names)) or default is None:
            return default
        else:
            return VerseType.Other

    @staticmethod
    def from_string(verse_name, default=Other):
        """
        Return the VerseType for a given string

        :param verse_name: The string to return a VerseType for
        :param default: Default return value if no matching tag is found
        :return: The VerseType determined from the string
        """
        verse_name = verse_name.lower()
        for num, name in enumerate(VerseType.names):
            if verse_name == name.lower():
                return num
        return default

    @staticmethod
    def from_translated_string(verse_name):
        """
        Return the VerseType for a given string

        :param verse_name: The string to return a VerseType for
        :return: A VerseType
        """
        verse_name = verse_name.lower()
        for num, translation in enumerate(VerseType.translated_names):
            if verse_name == translation.lower():
                return num
        return None

    @staticmethod
    def from_loose_input(verse_name, default=Other):
        """
        Return the VerseType for a given string

        :param verse_name: The string to return a VerseType for
        :param default: Default return value if no matching tag is found
        :return: A VerseType
        """
        if len(verse_name) > 1:
            verse_index = VerseType.from_translated_string(verse_name)
            if verse_index is None:
                verse_index = VerseType.from_string(verse_name, default)
        elif len(verse_name) == 1:
            verse_index = VerseType.from_translated_tag(verse_name, None)
            if verse_index is None:
                verse_index = VerseType.from_tag(verse_name, default)
        else:
            return default
        return verse_index


def retrieve_windows_encoding(recommendation=None):
    """
    Determines which encoding to use on an information source. The process uses both automated detection, which is
    passed to this method as a recommendation, and user confirmation to return an encoding.

    :param recommendation: A recommended encoding discovered programmatically for the user to confirm.
    :return: A list of recommended encodings, or None
    """
    # map chardet result to compatible windows standard code page
    codepage_mapping = {'IBM866': 'cp866', 'TIS-620': 'cp874', 'SHIFT_JIS': 'cp932', 'GB2312': 'cp936',
                        'HZ-GB-2312': 'cp936', 'EUC-KR': 'cp949', 'Big5': 'cp950', 'ISO-8859-2': 'cp1250',
                        'windows-1250': 'cp1250', 'windows-1251': 'cp1251', 'windows-1252': 'cp1252',
                        'ISO-8859-7': 'cp1253', 'windows-1253': 'cp1253', 'ISO-8859-8': 'cp1255',
                        'windows-1255': 'cp1255'}
    if recommendation in codepage_mapping:
        recommendation = codepage_mapping[recommendation]

    # Show dialog for encoding selection
    encodings = [
        ('cp1256', translate('SongsPlugin', 'Arabic (CP-1256)')),
        ('cp1257', translate('SongsPlugin', 'Baltic (CP-1257)')),
        ('cp1250', translate('SongsPlugin', 'Central European (CP-1250)')),
        ('cp1251', translate('SongsPlugin', 'Cyrillic (CP-1251)')),
        ('cp1253', translate('SongsPlugin', 'Greek (CP-1253)')),
        ('cp1255', translate('SongsPlugin', 'Hebrew (CP-1255)')),
        ('cp932', translate('SongsPlugin', 'Japanese (CP-932)')),
        ('cp949', translate('SongsPlugin', 'Korean (CP-949)')),
        ('cp936', translate('SongsPlugin', 'Simplified Chinese (CP-936)')),
        ('cp874', translate('SongsPlugin', 'Thai (CP-874)')),
        ('cp950', translate('SongsPlugin', 'Traditional Chinese (CP-950)')),
        ('cp1254', translate('SongsPlugin', 'Turkish (CP-1254)')),
        ('cp1258', translate('SongsPlugin', 'Vietnam (CP-1258)')),
        ('cp1252', translate('SongsPlugin', 'Western European (CP-1252)'))
    ]
    recommended_index = -1
    if recommendation:
        for index, encoding in enumerate(encodings):
            if recommendation == encoding[0]:
                recommended_index = index
                break
    if recommended_index > -1:
        choice = QtWidgets.QInputDialog.getItem(
            None,
            translate('SongsPlugin', 'Character Encoding'),
            translate('SongsPlugin', 'The codepage setting is responsible\n'
                                     'for the correct character representation.\n'
                                     'Usually you are fine with the preselected choice.'),
            [pair[1] for pair in encodings], recommended_index, False)
    else:
        choice = QtWidgets.QInputDialog.getItem(
            None,
            translate('SongsPlugin', 'Character Encoding'),
            translate('SongsPlugin', 'Please choose the character encoding.\n'
                                     'The encoding is responsible for the correct character representation.'),
            [pair[1] for pair in encodings], 0, False)
    if not choice[1]:
        return None
    return next(filter(lambda item: item[1] == choice[0], encodings))[0]


def clean_string(string):
    """
    Strips punctuation from the passed string to assist searching.

    :param string: The string to clean
    :return: A clean string
    """
    return WHITESPACE.sub(' ', APOSTROPHE.sub('', string)).lower()


def clean_title(title):
    """
    Cleans the song title by removing Unicode control chars groups C0 & C1, as well as any trailing spaces.

    :param title: The song title to clean
    :return: A clean title
    """
    return CONTROL_CHARS.sub('', title).rstrip()


def clean_song(manager, song):
    """
    Cleans the search title, rebuilds the search lyrics, adds a default author if the song does not have one and other
    clean ups. This should always called when a new song is added or changed.

    :param manager: The song database manager object.
    :param song: The song object.
    """
    from .openlyricsxml import SongXML

    if song.title:
        song.title = clean_title(song.title)
    else:
        song.title = ''
    if song.alternate_title:
        song.alternate_title = clean_title(song.alternate_title)
    else:
        song.alternate_title = ''
    song.search_title = clean_string(song.title) + '@' + clean_string(song.alternate_title)
    if isinstance(song.lyrics, bytes):
        song.lyrics = str(song.lyrics, encoding='utf8')
    verses = SongXML().get_verses(song.lyrics)
    song.search_lyrics = ' '.join([clean_string(remove_tags(verse[1], True)) for verse in verses])
    # The song does not have any author, add one.
    if not song.authors_songs:
        name = SongStrings().AuthorUnknown
        author = manager.get_object_filtered(Author, Author.display_name == name)
        if author is None:
            author = Author(display_name=name, last_name='', first_name='')
        song.add_author(author)
    if song.copyright:
        song.copyright = CONTROL_CHARS.sub('', song.copyright).strip()


def get_encoding(font, font_table, default_encoding, failed=False):
    """
    Finds an encoding to use. Asks user, if necessary.

    :param font: The number of currently active font.
    :param font_table: Dictionary of fonts and respective encodings.
    :param default_encoding: The default encoding to use when font_table is empty or no font is used.
    :param failed: A boolean indicating whether the previous encoding didn't work.
    """
    encoding = None
    if font in font_table:
        encoding = font_table[font]
    if not encoding and default_encoding:
        encoding = default_encoding
    if not encoding or failed:
        encoding = retrieve_windows_encoding()
        default_encoding = encoding
    font_table[font] = encoding
    return encoding, default_encoding


def strip_rtf(text, default_encoding=None):
    """
    This function strips RTF control structures and returns an unicode string.

    Thanks to Markus Jarderot (MizardX) for this code, used by permission. http://stackoverflow.com/questions/188545

    :param text: RTF-encoded text, a string.
    :param default_encoding: Default encoding to use when no encoding is specified.
    :return: A tuple ``(text, encoding)`` where ``text`` is the clean text and ``encoding`` is the detected encoding
    """
    # Current font is the font tag we last met.
    font = ''
    # Character encoding is defined inside fonttable.
    # font_table could contain eg '0': u'cp1252'
    font_table = {'': ''}
    # Stack of things to keep track of when entering/leaving groups.
    stack = []
    # Whether this group (and all inside it) are "ignorable".
    ignorable = False
    # Number of ASCII characters to skip after an unicode character.
    ucskip = 1
    # Number of ASCII characters left to skip.
    curskip = 0
    # Output buffer.
    out = []
    # Encoded buffer.
    ebytes = bytearray()
    for match in PATTERN.finditer(text):
        iinu, word, arg, hex_, char, brace, tchar = match.groups()
        # \x (non-alpha character)
        if char:
            if char in '\\{}':
                tchar = char
            else:
                word = char
        # Flush encoded buffer to output buffer
        if ebytes and not hex_ and not tchar:
            failed = False
            while True:
                try:
                    encoding, default_encoding = get_encoding(font, font_table, default_encoding, failed=failed)
                    if not encoding:
                        return None
                    dbytes = ebytes.decode(encoding)
                    # Code 5C is a peculiar case with Windows Codepage 932
                    if encoding == 'cp932' and '\\' in dbytes:
                        dbytes = dbytes.replace('\\', '\u00A5')
                    out.append(dbytes)
                    ebytes.clear()
                except UnicodeDecodeError:
                    failed = True
                else:
                    break
        # {}
        if brace:
            curskip = 0
            if brace == '{':
                # Push state
                stack.append((ucskip, ignorable, font))
            elif brace == '}' and len(stack) > 0:
                # Pop state
                ucskip, ignorable, font = stack.pop()
        # \command
        elif word:
            curskip = 0
            if word in DESTINATIONS:
                ignorable = True
            elif word in SPECIAL_CHARS:
                if not ignorable:
                    out.append(SPECIAL_CHARS[word])
            elif word == 'uc':
                ucskip = int(arg)
            elif word == 'u':
                c = int(arg)
                if c < 0:
                    c += 0x10000
                if not ignorable:
                    out.append(chr(c))
                curskip = ucskip
            elif word == 'fonttbl':
                ignorable = True
            elif word == 'f':
                font = arg
            elif word == 'ansicpg':
                font_table[font] = 'cp' + arg
            elif word == 'fcharset' and font not in font_table and arg in CHARSET_MAPPING:
                font_table[font] = CHARSET_MAPPING[arg]
            elif word == 'fldrslt':
                pass
            # \* 'Ignore if not understood' marker
            elif iinu:
                ignorable = True
        # \'xx
        elif hex_:
            if curskip > 0:
                curskip -= 1
            elif not ignorable:
                ebytes.append(int(hex_, 16))
        elif tchar:
            if not ignorable:
                ebytes += tchar.encode()
                if len(ebytes) >= curskip:
                    ebytes = ebytes[curskip:]
                else:
                    curskip -= len(ebytes)
                    ebytes = ""
    text = ''.join(out)
    return text, default_encoding


def delete_song(song_id: int, trigger_event: bool = True):
    """
    Deletes a song from the database. Media files associated to the song are removed prior to the deletion of the song.

    :param song_id: The ID of the song to delete.
    :param trigger_event: If True the song_deleted event is triggered through the registry
    """
    save_path = ''
    songs_manager = Registry().get('songs_manager')
    media_files = songs_manager.get_all_objects(MediaFile, MediaFile.song_id == song_id)
    for media_file in media_files:
        try:
            if isinstance(media_file.file_path, str):
                os.unlink(media_file.file_path)
            else:
                media_file.file_path.unlink()
        except OSError:
            log.exception('Could not remove file: {name}'.format(name=media_file.file_path))
    try:
        save_path = AppLocation.get_section_data_path('songs') / 'audio' / str(song_id)
        if save_path.exists():
            save_path.rmdir()
    except OSError:
        log.exception('Could not remove directory: {path}'.format(path=save_path))
    songs_manager.delete_object(Song, song_id)
    if trigger_event:
        Registry().execute('song_deleted', song_id)


def transpose_lyrics(lyrics, transpose_value):
    """
    Transpose lyrics

    :param lyrics: The lyrics to be transposed
    :param transpose_value: The value to transpose the lyrics with
    :return: The transposed lyrics
    """
    # Split text by verse delimiter - both normal and optional
    verse_list = re.split(r'(---\[.+?:.+?\]---|\[---\])', lyrics)
    transposed_lyrics = ''
    notation = Registry().get('settings').value('songs/chord notation')
    key = None
    for verse in verse_list:
        if verse.startswith('---[') or verse == '[---]':
            transposed_lyrics += verse
        else:
            transposed_lyric, key = transpose_verse(verse, transpose_value, notation, key)
            transposed_lyrics += transposed_lyric
    return transposed_lyrics


def transpose_verse(verse_text, transpose_value, notation, key):
    """
    Transpose Verse

    :param verse_text: The lyrics to be transposed
    :param transpose_value: The value to transpose the lyrics with
    :param notation: which notation to use
    :return: The transposed lyrics
    """
    if '[' not in verse_text:
        return verse_text, key
    # Split the lyrics based on chord tags, based on this, chords and bass will be treated equally and separately,
    # 6/9 chords should be noted 6-9 or 69 or 6add9
    lyric_list = re.split(r'(\[|\]|/)', verse_text)
    transposed_lyrics = ''
    is_bass = False
    last_chord = None
    in_tag = False
    for word in lyric_list:
        if not in_tag:
            transposed_lyrics += word
            if word == '[':
                in_tag = True
        else:
            if word == ']':
                in_tag = False
                transposed_lyrics += word
            elif word == '/':
                is_bass = True
                transposed_lyrics += word
            elif word == '--}{--':
                transposed_lyrics += word
            else:
                # This MUST be a chord
                transposed_chord, key, last_chord = transpose_chord(word, transpose_value, notation, key, last_chord,
                                                                    is_bass)
                is_bass = False
                transposed_lyrics += transposed_chord
    # If still inside a chord tag something is wrong!
    if in_tag:
        return verse_text, key
    else:
        return transposed_lyrics, key


def transpose_chord(chord, transpose_value, notation, key, last_chord, is_bass):
    """
    Transpose chord according to the notation used.
    NOTE: This function has a javascript equivalent in chords.js - make sure to update both!

    :param chord: The chord to transpose.
    :param transpose_value: The value the chord should be transposed.
    :param notation: The notation to use when transposing.
    :return: The transposed chord.
    """
    # See https://en.wikipedia.org/wiki/Musical_note#12-tone_chromatic_scale
    notes_sharp_notation = {
        'german': ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'H'],
        'english': ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'],
        'neo-latin': ['Do', 'Do#', 'Re', 'Re#', 'Mi', 'Fa', 'Fa#', 'Sol', 'Sol#', 'La', 'La#', 'Si']
    }
    notes_flat_notation = {
        'german': ['C', 'Db', 'D', 'Eb', 'Fb', 'F', 'Gb', 'G', 'Ab', 'A', 'B', 'H'],
        'english': ['C', 'Db', 'D', 'Eb', 'Fb', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'],
        'neo-latin': ['Do', 'Reb', 'Re', 'Mib', 'Fab', 'Fa', 'Solb', 'Sol', 'Lab', 'La', 'Sib', 'Si']
    }
    scales = {
        'german': {
            'C': ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'B', 'H'],
            'Am': ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'B', 'H'],
            'C#': ['H#', 'C#', 'D', 'D#', 'E', 'E#', 'F#', 'G', 'G#', 'A', 'A#', 'H'],
            'A#m': ['H#', 'C#', 'D', 'D#', 'E', 'E#', 'F#', 'G', 'G#', 'A', 'A#', 'H'],
            'Db': ['C', 'Db', 'Ebb', 'Eb', 'Fb', 'F', 'Gb', 'Abb', 'Ab', 'Bb', 'B', 'Cb'],
            'Bm': ['C', 'Db', 'Ebb', 'Eb', 'Fb', 'F', 'Gb', 'Abb', 'Ab', 'Bb', 'B', 'Cb'],
            'D': ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'B', 'H'],
            'Hm': ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'B', 'H'],
            'D#': ['H#', 'C#', 'Cx', 'D#', 'E', 'E#', 'F#', 'Fx', 'G#', 'A', 'A#', 'H'],
            'H#m': ['H#', 'C#', 'Cx', 'D#', 'E', 'E#', 'F#', 'Fx', 'G#', 'A', 'A#', 'H'],
            'Eb': ['C', 'Db', 'D', 'Eb', 'Fb', 'F', 'Gb', 'G', 'Ab', 'Bb', 'B', 'Cb'],
            'Cm': ['C', 'Db', 'D', 'Eb', 'Fb', 'F', 'Gb', 'G', 'Ab', 'Bb', 'B', 'Cb'],
            'E': ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'B', 'H'],
            'C#m': ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'B', 'H'],
            'F': ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'B', 'Cb'],
            'Dm': ['C', 'C#', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'B', 'H'],
            'F#': ['C', 'C#', 'D', 'D#', 'E', 'E#', 'F#', 'G', 'G#', 'A', 'A#', 'H'],
            'D#m': ['C', 'C#', 'D', 'D#', 'E', 'E#', 'F#', 'G', 'G#', 'A', 'A#', 'H'],
            'Gb': ['Dbb', 'Db', 'Ebb', 'Eb', 'Fb', 'F', 'Gb', 'Abb', 'Ab', 'Bb', 'B', 'Cb'],
            'Ebm': ['Dbb', 'Db', 'Ebb', 'Eb', 'Fb', 'F', 'Gb', 'Abb', 'Ab', 'Bb', 'B', 'Cb'],
            'G': ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'B', 'H'],
            'Em': ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'B', 'H'],
            'G#': ['H#', 'C#', 'D', 'D#', 'E', 'E#', 'F#', 'Fx', 'G#', 'A', 'A#', 'H'],
            'E#m': ['H#', 'C#', 'D', 'D#', 'E', 'E#', 'F#', 'Fx', 'G#', 'A', 'A#', 'H'],
            'Ab': ['C', 'Db', 'Ebb', 'Eb', 'Fb', 'F', 'Gb', 'G', 'Ab', 'Bb', 'B', 'Cb'],
            'Fm': ['C', 'Db', 'Ebb', 'Eb', 'Fb', 'F', 'Gb', 'G', 'Ab', 'Bb', 'B', 'Cb'],
            'A': ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'G#', 'A', 'B', 'H'],
            'F#m': ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'G#', 'A', 'B', 'H'],
            'A#': ['H#', 'C#', 'Cx', 'D#', 'E', 'E#', 'F#', 'Fx', 'G#', 'Gx', 'A#', 'H'],
            'F##m': ['H#', 'C#', 'Cx', 'D#', 'E', 'E#', 'F#', 'Fx', 'G#', 'Gx', 'A#', 'H'],
            'Fxm': ['H#', 'C#', 'Cx', 'D#', 'E', 'E#', 'F#', 'Fx', 'G#', 'Gx', 'A#', 'H'],
            'B': ['C', 'Db', 'D', 'Eb', 'Fb', 'F', 'Gb', 'G', 'Ab', 'A', 'B', 'Cb'],
            'Gm': ['C', 'Db', 'D', 'Eb', 'Fb', 'F', 'Gb', 'G', 'Ab', 'A', 'B', 'Cb'],
            'H': ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'H'],
            'G#m': ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'H'],
            'Cb': ['Dbb', 'Db', 'Ebb', 'Eb', 'Fb', 'Gbb', 'Gb', 'Abb', 'Ab', 'Bb', 'B', 'Cb'],
            'Abm': ['Dbb', 'Db', 'Ebb', 'Eb', 'Fb', 'Gbb', 'Gb', 'Abb', 'Ab', 'Bb', 'B', 'Cb']
        },
        'english': {
            'C': ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'],
            'Am': ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'],
            'C#': ['B#', 'C#', 'D', 'D#', 'E', 'E#', 'F#', 'G', 'G#', 'A', 'A#', 'B'],
            'A#m': ['B#', 'C#', 'D', 'D#', 'E', 'E#', 'F#', 'G', 'G#', 'A', 'A#', 'B'],
            'Db': ['C', 'Db', 'Ebb', 'Eb', 'Fb', 'F', 'Gb', 'Abb', 'Ab', 'Bbb', 'Bb', 'Cb'],
            'Bbm': ['C', 'Db', 'Ebb', 'Eb', 'Fb', 'F', 'Gb', 'Abb', 'Ab', 'Bbb', 'Bb', 'Cb'],
            'D': ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'],
            'Bm': ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'],
            'D#': ['B#', 'C#', 'Cx', 'D#', 'E', 'E#', 'F#', 'Fx', 'G#', 'A', 'A#', 'B'],
            'B#m': ['B#', 'C#', 'Cx', 'D#', 'E', 'E#', 'F#', 'Fx', 'G#', 'A', 'A#', 'B'],
            'Eb': ['C', 'Db', 'D', 'Eb', 'Fb', 'F', 'Gb', 'G', 'Ab', 'Bbb', 'Bb', 'Cb'],
            'Cm': ['C', 'Db', 'D', 'Eb', 'Fb', 'F', 'Gb', 'G', 'Ab', 'Bbb', 'Bb', 'Cb'],
            'E': ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'Bb', 'B'],
            'C#m': ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'Bb', 'B'],
            'F': ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'Cb'],
            'Dm': ['C', 'C#', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'],
            'F#': ['C', 'C#', 'D', 'D#', 'E', 'E#', 'F#', 'G', 'G#', 'A', 'A#', 'B'],
            'D#m': ['C', 'C#', 'D', 'D#', 'E', 'E#', 'F#', 'G', 'G#', 'A', 'A#', 'B'],
            'Gb': ['Dbb', 'Db', 'Ebb', 'Eb', 'Fb', 'F', 'Gb', 'Abb', 'Ab', 'Bbb', 'Bb', 'Cb'],
            'Ebm': ['Dbb', 'Db', 'Ebb', 'Eb', 'Fb', 'F', 'Gb', 'Abb', 'Ab', 'Bbb', 'Bb', 'Cb'],
            'G': ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'],
            'Em': ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'],
            'G#': ['B#', 'C#', 'D', 'D#', 'E', 'E#', 'F#', 'Fx', 'G#', 'A', 'A#', 'B'],
            'E#m': ['B#', 'C#', 'D', 'D#', 'E', 'E#', 'F#', 'Fx', 'G#', 'A', 'A#', 'B'],
            'Ab': ['C', 'Db', 'Ebb', 'Eb', 'Fb', 'F', 'Gb', 'G', 'Ab', 'Bbb', 'Bb', 'Cb'],
            'Fm': ['C', 'Db', 'Ebb', 'Eb', 'Fb', 'F', 'Gb', 'G', 'Ab', 'Bbb', 'Bb', 'Cb'],
            'A': ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'G#', 'A', 'Bb', 'B'],
            'F#m': ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'G#', 'A', 'Bb', 'B'],
            'A#': ['B#', 'C#', 'Cx', 'D#', 'E', 'E#', 'F#', 'Fx', 'G#', 'Gx', 'A#', 'B'],
            'F##m': ['B#', 'C#', 'Cx', 'D#', 'E', 'E#', 'F#', 'Fx', 'G#', 'Gx', 'A#', 'B'],
            'Fxm': ['B#', 'C#', 'Cx', 'D#', 'E', 'E#', 'F#', 'Fx', 'G#', 'Gx', 'A#', 'B'],
            'Bb': ['C', 'Db', 'D', 'Eb', 'Fb', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'Cb'],
            'Gm': ['C', 'Db', 'D', 'Eb', 'Fb', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'Cb'],
            'B': ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'],
            'G#m': ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'],
            'Cb': ['Dbb', 'Db', 'Ebb', 'Eb', 'Fb', 'Gbb', 'Gb', 'Abb', 'Ab', 'Bbb', 'Bb', 'Cb'],
            'Abm': ['Dbb', 'Db', 'Ebb', 'Eb', 'Fb', 'Gbb', 'Gb', 'Abb', 'Ab', 'Bbb', 'Bb', 'Cb']
        },
        'neo-latin': {
            'Do': ['Do', 'Reb', 'Re', 'Mib', 'Mi', 'Fa', 'Fa#', 'Sol', 'Lab', 'La', 'Sib', 'Si'],
            'Lam': ['Do', 'Reb', 'Re', 'Mib', 'Mi', 'Fa', 'Fa#', 'Sol', 'Lab', 'La', 'Sib', 'Si'],
            'Do#': ['Si#', 'Do#', 'Re', 'Re#', 'Mi', 'Mi#', 'Fa#', 'Sol', 'Sol#', 'La', 'La#', 'Si'],
            'La#m': ['Si#', 'Do#', 'Re', 'Re#', 'Mi', 'Mi#', 'Fa#', 'Sol', 'Sol#', 'La', 'La#', 'Si'],
            'Reb': ['Do', 'Reb', 'Mibb', 'Mib', 'Fab', 'Fa', 'Solb', 'Labb', 'Lab', 'Sibb', 'Sib', 'Dob'],
            'Sibm': ['Do', 'Reb', 'Mibb', 'Mib', 'Fab', 'Fa', 'Solb', 'Labb', 'Lab', 'Sibb', 'Sib', 'Dob'],
            'Re': ['Do', 'Do#', 'Re', 'Mib', 'Mi', 'Fa', 'Fa#', 'Sol', 'Lab', 'La', 'Sib', 'Si'],
            'Sim': ['Do', 'Do#', 'Re', 'Mib', 'Mi', 'Fa', 'Fa#', 'Sol', 'Lab', 'La', 'Sib', 'Si'],
            'Re#': ['Si#', 'Do#', 'Dox', 'Re#', 'Mi', 'Mi#', 'Fa#', 'Fax', 'Sol#', 'La', 'La#', 'Si'],
            'Si#m': ['Si#', 'Do#', 'Dox', 'Re#', 'Mi', 'Mi#', 'Fa#', 'Fax', 'Sol#', 'La', 'La#', 'Si'],
            'Mib': ['Do', 'Reb', 'Re', 'Mib', 'Fab', 'Fa', 'Solb', 'Sol', 'Lab', 'Sibb', 'Sib', 'Dob'],
            'Dom': ['Do', 'Reb', 'Re', 'Mib', 'Fab', 'Fa', 'Solb', 'Sol', 'Lab', 'Sibb', 'Sib', 'Dob'],
            'Mi': ['Do', 'Do#', 'Re', 'Re#', 'Mi', 'Fa', 'Fa#', 'Sol', 'Sol#', 'La', 'Sib', 'Si'],
            'Do#m': ['Do', 'Do#', 'Re', 'Re#', 'Mi', 'Fa', 'Fa#', 'Sol', 'Sol#', 'La', 'Sib', 'Si'],
            'Fa': ['Do', 'Reb', 'Re', 'Mib', 'Mi', 'Fa', 'Solb', 'Sol', 'Lab', 'La', 'Sib', 'Dob'],
            'Rem': ['Do', 'Do#', 'Re', 'Mib', 'Mi', 'Fa', 'Solb', 'Sol', 'Lab', 'La', 'Sib', 'Si'],
            'Fa#': ['Do', 'Do#', 'Re', 'Re#', 'Mi', 'Mi#', 'Fa#', 'Sol', 'Sol#', 'La', 'La#', 'Si'],
            'Re#m': ['Do', 'Do#', 'Re', 'Re#', 'Mi', 'Mi#', 'Fa#', 'Sol', 'Sol#', 'La', 'La#', 'Si'],
            'Solb': ['Rebb', 'Reb', 'Mibb', 'Mib', 'Fab', 'Fa', 'Solb', 'Labb', 'Lab', 'Sibb', 'Sib', 'Dob'],
            'Mibm': ['Rebb', 'Reb', 'Mibb', 'Mib', 'Fab', 'Fa', 'Solb', 'Labb', 'Lab', 'Sibb', 'Sib', 'Dob'],
            'Sol': ['Do', 'Reb', 'Re', 'Mib', 'Mi', 'Fa', 'Fa#', 'Sol', 'Lab', 'La', 'Sib', 'Si'],
            'Mim': ['Do', 'Reb', 'Re', 'Mib', 'Mi', 'Fa', 'Fa#', 'Sol', 'Lab', 'La', 'Sib', 'Si'],
            'Sol#': ['Si#', 'Do#', 'Re', 'Re#', 'Mi', 'Mi#', 'Fa#', 'Fax', 'Sol#', 'La', 'La#', 'Si'],
            'Mi#m': ['Si#', 'Do#', 'Re', 'Re#', 'Mi', 'Mi#', 'Fa#', 'Fax', 'Sol#', 'La', 'La#', 'Si'],
            'Lab': ['Do', 'Reb', 'Mibb', 'Mib', 'Fab', 'Fa', 'Solb', 'Sol', 'Lab', 'Sibb', 'Sib', 'Dob'],
            'Fam': ['Do', 'Reb', 'Mibb', 'Mib', 'Fab', 'Fa', 'Solb', 'Sol', 'Lab', 'Sibb', 'Sib', 'Dob'],
            'La': ['Do', 'Do#', 'Re', 'Mib', 'Mi', 'Fa', 'Fa#', 'Sol', 'Sol#', 'La', 'Sib', 'Si'],
            'Fa#m': ['Do', 'Do#', 'Re', 'Mib', 'Mi', 'Fa', 'Fa#', 'Sol', 'Sol#', 'La', 'Sib', 'Si'],
            'La#': ['Si#', 'Do#', 'Dox', 'Re#', 'Mi', 'Mi#', 'Fa#', 'Fax', 'Sol#', 'Solx', 'La#', 'Si'],
            'Fa##m': ['Si#', 'Do#', 'Dox', 'Re#', 'Mi', 'Mi#', 'Fa#', 'Fax', 'Sol#', 'Solx', 'La#', 'Si'],
            'Faxm': ['Si#', 'Do#', 'Dox', 'Re#', 'Mi', 'Mi#', 'Fa#', 'Fax', 'Sol#', 'Solx', 'La#', 'Si'],
            'Sib': ['Do', 'Reb', 'Re', 'Mib', 'Fab', 'Fa', 'Solb', 'Sol', 'Lab', 'La', 'Sib', 'Dob'],
            'Solm': ['Do', 'Reb', 'Re', 'Mib', 'Fab', 'Fa', 'Solb', 'Sol', 'Lab', 'La', 'Sib', 'Dob'],
            'Si': ['Do', 'Do#', 'Re', 'Re#', 'Mi', 'Fa', 'Fa#', 'Sol', 'Sol#', 'La', 'La#', 'Si'],
            'Sol#m': ['Do', 'Do#', 'Re', 'Re#', 'Mi', 'Fa', 'Fa#', 'Sol', 'Sol#', 'La', 'La#', 'Si'],
            'Dob': ['Rebb', 'Reb', 'Mibb', 'Mib', 'Fab', 'Solbb', 'Solb', 'Labb', 'Lab', 'Sibb', 'Sib', 'Dob'],
            'Labm': ['Rebb', 'Reb', 'Mibb', 'Mib', 'Fab', 'Solbb', 'Solb', 'Labb', 'Lab', 'Sibb', 'Sib', 'Dob']
        }
    }
    note_numbers = {
        'german': {
            'C': 0, 'H#': 0, 'B##': 0, 'Bx': 0, 'Dbb': 0,
            'C#': 1, 'Db': 1,
            'D': 2, 'C##': 2, 'Cx': 2, 'Ebb': 2,
            'D#': 3, 'Eb': 3,
            'E': 4, 'D##': 4, 'Dx': 4, 'Fb': 4,
            'F': 5, 'E#': 5, 'Gbb': 5,
            'F#': 6, 'Gb': 6,
            'G': 7, 'F##': 7, 'Fx': 7, 'Abb': 7,
            'G#': 8, 'Ab': 8,
            'A': 9, 'G##': 9, 'Gx': 9, 'Bb': 9, 'Hbb': 9,
            'B': 10, 'A#': 10, 'Hb': 10,
            'H': 11, 'B#': 11, 'A##': 11, 'Ax': 11, 'Cb': 11
        },
        'english': {
            'C': 0, 'B#': 0, 'Dbb': 0,
            'C#': 1, 'Db': 1, 'B##': 1, 'Bx': 1,
            'D': 2, 'C##': 2, 'Cx': 2, 'Ebb': 2,
            'D#': 3, 'Eb': 3, 'Fbb': 3,
            'E': 4, 'D##': 4, 'Dx': 4, 'Fb': 4,
            'F': 5, 'E#': 5, 'Gbb': 5,
            'F#': 6, 'Gb': 6, 'E##': 6, 'Ex': 6,
            'G': 7, 'F##': 7, 'Fx': 7, 'Abb': 7,
            'G#': 8, 'Ab': 8,
            'A': 9, 'G##': 9, 'Gx': 9, 'Bbb': 9,
            'Bb': 10, 'A#': 10, 'Cbb': 10,
            'B': 11, 'A##': 11, 'Ax': 11, 'Cb': 11
        },
        'neo-latin': {
            'Do': 0, 'Si#': 0, 'Rebb': 0,
            'Do#': 1, 'Reb': 1, 'Si##': 1, 'Six': 1,
            'Re': 2, 'Do##': 2, 'Dox': 2, 'Mibb': 2,
            'Re#': 3, 'Mib': 3, 'Fabb': 3,
            'Mi': 4, 'Re##': 4, 'Rex': 4, 'Fab': 4,
            'Fa': 5, 'Mi#': 5, 'Solbb': 5,
            'Fa#': 6, 'Solb': 6, 'Mi##': 6, 'Mix': 6,
            'Sol': 7, 'Fa##': 7, 'Fax': 7, 'Labb': 7,
            'Sol#': 8, 'Lab': 8,
            'La': 9, 'Sol##': 9, 'Solx': 9, 'Sibb': 9,
            'Sib': 10, 'La#': 10, 'Dobb': 10,
            'Si': 11, 'La##': 11, 'Lax': 11, 'Dob': 11
        }
    }
    chord = chord.replace('♭', 'b').replace('♯', '#')
    transposed_chord = ''
    minor = ''
    note = ''
    is_key_change_chord = False
    notes_sharp = notes_sharp_notation[notation]
    notes_flat = notes_flat_notation[notation]
    notes_preferred = ['b', '#', '#', 'b', '#', 'b', '#', '#', 'b', '#', 'b', '#']
    if chord and chord[0] == '(':
        transposed_chord += '('
        if len(chord) > 1:
            chord = chord[1:]
        else:
            chord = ''
    if chord and chord[0] == '=':
        transposed_chord += '='
        if len(chord) > 1:
            chord = chord[1:]
            is_key_change_chord = True
        else:
            chord = ''
    if chord and chord[0] == '|':
        transposed_chord += '|'
        if len(chord) > 1:
            chord = chord[1:]
        else:
            chord = ''
    if len(chord) > 0:
        if notation == 'neo-latin':
            if len(chord) > 2 and chord[0:3].lower() == 'sol':
                note = chord[0:3]
                chord = chord[3:] if len(chord) > 3 else ''
            elif len(chord) > 1:
                note = chord[0:2]
                chord = chord[2:] if len(chord) > 2 else ''
        else:
            note = chord[0]
        chord = chord[1:] if len(chord) > 1 else ''
        while len(chord) > 0 and '#bx'.find(chord[0]) > -1:
            note += chord[0]
            chord = chord[1:] if len(chord) > 0 else ''
        if len(chord) > 0:
            if 'm-'.find(chord[0]) > -1 or (len(chord) > 1 and chord[0:2].lower() == 'mi'):
                minor = chord[0]
                chord = chord[1:] if len(chord) > 1 else ''
            else:
                minor = ''
        note_number = note_numbers[notation][note]
        note_number += transpose_value
        while note_number > 11:
            note_number -= 12
        while note_number < 0:
            note_number += 12
        if is_bass:
            if last_chord:
                note = scales[notation][last_chord][note_number]
            elif key:
                note = scales[notation][key][note_number]
            else:
                note = notes_sharp[note_number] if notes_preferred[note_number] == '#' else notes_flat[note_number]
        else:
            if not key or is_key_change_chord:
                note = notes_sharp[note_number] if notes_preferred[note_number] == '#' else notes_flat[note_number]
            else:
                note = scales[notation][key][note_number]
        transposed_chord += note + minor + chord
        if is_key_change_chord:
            key = note + minor
        else:
            if not is_bass:
                last_chord = note + minor
    return transposed_chord, key, last_chord
