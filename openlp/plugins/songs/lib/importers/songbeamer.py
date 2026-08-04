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
The :mod:`songbeamer` module provides the functionality for importing SongBeamer songs into the OpenLP database.
"""
import base64
import logging
import math
import os
import re
from pathlib import Path

from openlp.core.common import get_file_encoding
from openlp.core.common.i18n import translate
from openlp.core.common.platform import is_macosx, is_win
from openlp.plugins.songs.lib import VerseType
from openlp.plugins.songs.lib.importers.songimport import SongImport


log = logging.getLogger(__name__)


class SongBeamerTypes(object):
    MarkTypes = {
        'refrain': VerseType.tags[VerseType.Chorus],
        'chorus': VerseType.tags[VerseType.Chorus],
        'vers': VerseType.tags[VerseType.Verse],
        'verse': VerseType.tags[VerseType.Verse],
        'strophe': VerseType.tags[VerseType.Verse],
        'intro': VerseType.tags[VerseType.Intro],
        'coda': VerseType.tags[VerseType.Ending],
        'ending': VerseType.tags[VerseType.Ending],
        'bridge': VerseType.tags[VerseType.Bridge],
        'interlude': VerseType.tags[VerseType.Bridge],
        'zwischenspiel': VerseType.tags[VerseType.Bridge],
        'pre-chorus': VerseType.tags[VerseType.PreChorus],
        'pre-refrain': VerseType.tags[VerseType.PreChorus],
        'misc': VerseType.tags[VerseType.Other],
        'pre-bridge': VerseType.tags[VerseType.Other],
        'pre-coda': VerseType.tags[VerseType.Other],
        'part': VerseType.tags[VerseType.Other],
        'teil': VerseType.tags[VerseType.Other],
        'unbekannt': VerseType.tags[VerseType.Other],
        'unknown': VerseType.tags[VerseType.Other],
        'unbenannt': VerseType.tags[VerseType.Other],
        '$$m=': VerseType.tags[VerseType.Other]
    }


class SongBeamerImport(SongImport):
    """
    Import Song Beamer files(s). Song Beamer file format is text based in the beginning are one or more control tags
    written.
    """
    HTML_TAG_PAIRS = [
        (re.compile('<b>'), '{st}'),
        (re.compile('</b>'), '{/st}'),
        (re.compile('<i>'), '{it}'),
        (re.compile('</i>'), '{/it}'),
        (re.compile('<u>'), '{u}'),
        (re.compile('</u>'), '{/u}'),
        (re.compile('<p>'), '{p}'),
        (re.compile('</p>'), '{/p}'),
        (re.compile('<super>'), '{su}'),
        (re.compile('</super>'), '{/su}'),
        (re.compile('<sub>'), '{sb}'),
        (re.compile('</sub>'), '{/sb}'),
        (re.compile('<br.*?>'), '{br}'),
        (re.compile('<[/]?wordwrap>'), ''),
        (re.compile('<[/]?strike>'), ''),
        (re.compile('<[/]?h.*?>'), ''),
        (re.compile(r'</?s(?:\s[^<>]*?)?>', re.IGNORECASE), ''),
        (re.compile('<[/]?linespacing.*?>'), ''),
        (re.compile('<[/]?c.*?>'), ''),
        (re.compile('<align.*?>'), ''),
        (re.compile('<valign.*?>'), '')
    ]

    def __init__(self, manager, **kwargs):
        """
        Initialise the Song Beamer importer.
        """
        super(SongBeamerImport, self).__init__(manager, **kwargs)

    def do_import(self):
        """
        Receive a single file or a list of files to import.
        """
        if not isinstance(self.import_source, list):
            return
        self.import_wizard.progress_bar.setMaximum(len(self.import_source))
        for file_path in self.import_source:
            # TODO: check that it is a valid SongBeamer file
            if self.stop_import_flag:
                return
            self.set_defaults()
            self.current_verse = ''
            self.current_verse_type = VerseType.tags[VerseType.Verse]
            self.chord_table = None
            self.chord_key = None
            if file_path.is_file():
                # Detect the encoding
                self.input_file_encoding = get_file_encoding(file_path)
                # The encoding should only be ANSI (cp1252), UTF-8, Unicode, Big-Endian-Unicode.
                # So if it doesn't start with 'u' we default to cp1252. See:
                # https://forum.songbeamer.com/viewtopic.php?p=419&sid=ca4814924e37c11e4438b7272a98b6f2
                if self.input_file_encoding and not self.input_file_encoding.lower().startswith('u'):
                    self.input_file_encoding = 'cp1252'
                with file_path.open(encoding=self.input_file_encoding) as song_file:
                    try:
                        song_data = song_file.readlines()
                    except UnicodeDecodeError:
                        log.exception('Unreadable characters in {name}'.format(name=file_path))
                        self.log_error(file_path, translate('SongsPlugin.SongBeamerImport',
                                                            'File is not a valid SongBeamer file.'))
                        continue
            else:
                continue
            self.title = file_path.stem
            read_verses = False
            # The first verse separator doesn't count, but the others does, so line count starts at -1
            line_number = -1
            idx = -1
            while idx + 1 < len(song_data):
                idx = idx + 1
                line = song_data[idx].rstrip()
                stripped_line = line.strip()
                if line.startswith('#') and not read_verses:
                    self.parse_tags(line)
                elif stripped_line.startswith('---'):
                    # '---' is a verse breaker
                    if self.current_verse:
                        self.replace_html_tags()
                        self.add_verse(self.current_verse, self.current_verse_type)
                        self.current_verse = ''
                        self.current_verse_type = VerseType.tags[VerseType.Verse]
                    read_verses = True
                    verse_start = True
                    # Songbeamer allows chord on line "-1", meaning the first line has only chords
                    if line_number == -1:
                        first_line = self.insert_chords(line_number, '')
                        if first_line:
                            # if present, insert chord key before the very first chord
                            if self.chord_key:
                                first_line = '[=%s]%s' % (self.chord_key, first_line)
                            self.current_verse = first_line.strip() + '\n'
                    line_number += 1
                elif stripped_line.startswith('--'):
                    # '--' is a page breaker, we convert to optional page break
                    self.current_verse += '[---]\n'
                    line_number += 1
                elif read_verses:
                    if verse_start:
                        verse_start = False
                        verse_mark = self.check_verse_marks(line)
                        # if present, insert chord key before the very first chord
                        if line_number == 0 and self.current_verse == '' and self.chord_key:
                            self.current_verse = '[=%s]' % self.chord_key
                        if not verse_mark:
                            line = self.insert_chords(line_number, line)
                            self.current_verse += line.strip() + '\n'
                        line_number += 1
                    else:
                        line = self.insert_chords(line_number, line)
                        self.current_verse += line.strip() + '\n'
                        line_number += 1
            if self.current_verse:
                self.replace_html_tags()
                self.add_verse(self.current_verse, self.current_verse_type)
            if not self.finish():
                self.log_error(file_path)

    def insert_chords(self, line_number, line):
        """
        Insert chords into text if any exists and chords import is enabled

        :param linenumber: Number of the current line
        :param line: The line of lyrics to insert chords
        """
        if self.chord_table and self.settings.value('songs/enable chords') and not self.settings.value(
                'songs/disable chords import') and line_number in self.chord_table:
            line_idx = sorted(self.chord_table[line_number].keys(), reverse=True)
            for idx in line_idx:
                # In SongBeamer the column position of the chord can be a decimal, we just round it up.
                int_idx = int(math.ceil(idx))
                if int_idx < 0:
                    int_idx = 0
                elif int_idx > len(line):
                    # If a chord is placed beyond the current end of the line, extend the line with spaces.
                    line += ' ' * (int_idx - len(line))
                chord = self.chord_table[line_number][idx]
                chord = chord.replace('<', '♭')
                line = line[:int_idx] + '[' + chord + ']' + line[int_idx:]
        return line

    def replace_html_tags(self):
        """
        This can be called to replace SongBeamer's specific (html) tags with OpenLP's specific (html) tags.
        """
        for pair in SongBeamerImport.HTML_TAG_PAIRS:
            self.current_verse = pair[0].sub(pair[1], self.current_verse)

    def parse_tags(self, line):
        """
        Parses a meta data line.

        :param line: The line in the file. It should consist of a tag and a value for this tag (unicode)::

                '#Title=Nearer my God to Thee'
        """
        tag_val = line.split('=', 1)
        if len(tag_val) == 1:
            return
        if not tag_val[0] or not tag_val[1]:
            return
        if tag_val[0] == '#(c)':
            self.add_copyright(tag_val[1])
        elif tag_val[0] == '#AddCopyrightInfo':
            pass
        elif tag_val[0] == '#AudioFile':
            self.parse_audio_file(tag_val[1])
        elif tag_val[0] == '#Author':
            self.parse_author(tag_val[1], 'words')
        elif tag_val[0] == '#BackgroundImage':
            pass
        elif tag_val[0] == '#Bible':
            pass
        elif tag_val[0] == '#Categories':
            self.topics = tag_val[1].split(',')
        elif tag_val[0] == '#CCLI':
            self.ccli_number = tag_val[1]
        elif tag_val[0] == '#Chords':
            self.chord_table = self.parse_chords(tag_val[1])
        elif tag_val[0] == '#ChurchSongID':
            pass
        elif tag_val[0] == '#ColorChords':
            pass
        elif tag_val[0] == '#Comments':
            try:
                self.comments = base64.b64decode(tag_val[1]).decode(self.input_file_encoding)
            except ValueError:
                self.comments = tag_val[1]
        elif tag_val[0] == '#Editor':
            pass
        elif tag_val[0] == '#Font':
            pass
        elif tag_val[0] == '#FontLang2':
            pass
        elif tag_val[0] == '#FontSize':
            pass
        elif tag_val[0] == '#Format':
            pass
        elif tag_val[0] == '#Format_PreLine':
            pass
        elif tag_val[0] == '#Format_PrePage':
            pass
        elif tag_val[0] == '#ID':
            pass
        elif tag_val[0] == '#Key':
            self.chord_key = tag_val[1]
            if self.chord_key:
                self.chord_key = self.chord_key.replace('<', '♭')
        elif tag_val[0] == '#Keywords':
            pass
        elif tag_val[0] == '#LangCount':
            pass
        elif tag_val[0] == '#Melody':
            self.parse_author(tag_val[1], 'music')
        elif tag_val[0] == '#NatCopyright':
            pass
        elif tag_val[0] == '#OTitle':
            pass
        elif tag_val[0] == '#OutlineColor':
            pass
        elif tag_val[0] == '#OutlinedFont':
            pass
        elif tag_val[0] == '#QuickFind':
            pass
        elif tag_val[0] == '#Rights':
            # song_book_pub = tag_val[1]
            pass
        elif tag_val[0] == '#Songbook' or tag_val[0] == '#SongBook':
            book_data = tag_val[1].split('/')
            self.song_book_name = book_data[0].strip()
            if len(book_data) == 2:
                number = book_data[1].strip()
                self.song_number = number if number.isdigit() else ''
        elif tag_val[0] == '#Speed':
            pass
        elif tag_val[0] == 'Tempo':
            pass
        elif tag_val[0] == '#TextAlign':
            pass
        elif tag_val[0] == '#Title':
            self.title = tag_val[1].strip()
        elif tag_val[0] == '#TitleAlign':
            pass
        elif tag_val[0] == '#TitleFontSize':
            pass
        elif tag_val[0] == '#TitleLang2':
            pass
        elif tag_val[0] == '#TitleLang3':
            pass
        elif tag_val[0] == '#TitleLang4':
            pass
        elif tag_val[0] == '#Translation':
            pass
        elif tag_val[0] == '#Transpose':
            pass
        elif tag_val[0] == '#TransposeAccidental':
            pass
        elif tag_val[0] == '#Version':
            pass
        elif tag_val[0] == '#VerseOrder':
            verse_order = tag_val[1].strip()
            for verse_mark in verse_order.split(','):
                new_verse_mark = self.convert_verse_marks(verse_mark)
                if new_verse_mark:
                    self.verse_order_list.append(new_verse_mark)

    def check_verse_marks(self, line):
        """
        Check and add the verse's MarkType. Returns ``True`` if the given line contains a correct verse mark otherwise
        ``False``.

        :param line: The line to check for marks.
        """
        new_verse_mark = self.convert_verse_marks(line)
        if new_verse_mark:
            self.current_verse_type = new_verse_mark
            return True
        return False

    def convert_verse_marks(self, line):
        """
        Convert the verse's MarkType. Returns the OpenLP versemark if the given line contains a correct SongBeamer verse
        mark otherwise ``None``.

        :param line: The line to check for marks.
        """
        new_verse_mark = None
        marks = line.split(' ')
        if len(marks) <= 2 and marks[0].lower() in SongBeamerTypes.MarkTypes:
            new_verse_mark = SongBeamerTypes.MarkTypes[marks[0].lower()]
            if len(marks) == 2:
                # If we have a digit, we append it to the converted verse mark
                if marks[1].isdigit():
                    new_verse_mark += marks[1]
        elif marks[0].lower().startswith('$$m='):  # this verse-mark cannot be numbered
            new_verse_mark = SongBeamerTypes.MarkTypes['$$m=']
        return new_verse_mark

    def parse_chords(self, chords):
        """
        Parse chords. The chords are in a base64 encode string. The decoded string is an index of chord placement
        separated by "\r", like this: "<linecolumn>,<linenumber>,<chord>\r"

        :param chords: Chords in a base64 encoded string
        """
        chord_list = base64.b64decode(chords).decode(self.input_file_encoding).split('\r')
        chord_table = {}
        for chord_index in chord_list:
            if not chord_index:
                continue
            [col_str, line_str, chord] = chord_index.split(',')
            col = float(col_str)
            line = int(line_str)
            if line not in chord_table:
                chord_table[line] = {}
            chord_table[line][col] = chord
        return chord_table

    def parse_audio_file(self, audio_file_path):
        """
        Parse audio file. The path is relative to the SongsBeamer Songs folder.

        :param audio_file_path: Path to the audio file
        """
        # The path is relative to SongBeamers Song folder
        if is_win():
            user_doc_path = Path(os.path.expandvars('$DOCUMENTS'))
        elif is_macosx():
            user_doc_path = Path.home() / 'Documents'
        else:
            # SongBeamer only runs on mac and win...
            return
        audio_file_path = user_doc_path / 'SongBeamer' / 'Songs' / audio_file_path
        if audio_file_path.is_file():
            self.add_media_file(audio_file_path)
        else:
            log.debug('Could not import mediafile "{audio_file_path}" since it does not exist!'
                      .format(audio_file_path=audio_file_path))
