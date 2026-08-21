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
import re

from openlp.plugins.songs.lib import VerseType, retrieve_windows_encoding, strip_rtf
from openlp.plugins.songs.lib.importers.songimport import SongImport


HOTKEY_TO_VERSE_TYPE = {
    '1': 'v1',
    '2': 'v2',
    '3': 'v3',
    '4': 'v4',
    '5': 'v5',
    '6': 'v6',
    '7': 'v7',
    '8': 'v8',
    '9': 'v9',
    'C': 'c',
    '+': 'b',
    'Z': 'o'}


class SundayPlusImport(SongImport):
    """
    Import Sunday Plus songs

    The format examples can be found attached to bug report at <http://support.openlp.org/issues/395>
    """

    def __init__(self, manager, **kwargs):
        """
        Initialise the class.
        """
        super(SundayPlusImport, self).__init__(manager, **kwargs)
        self.encoding = 'cp1252'

    def do_import(self):
        self.import_wizard.progress_bar.setMaximum(len(self.import_source))
        for file_path in self.import_source:
            if self.stop_import_flag:
                return
            self.do_import_file(file_path)

    def do_import_file(self, file_path):
        """
        Process the Sunday Plus song file

        :param pathlib.Path file_path: The song file to import
        :rtype: None
        """
        with file_path.open('rb') as song_file:
            self.set_defaults()
            if not self.parse(song_file.read()):
                self.log_error(file_path.name)
                return
            if self.title == '':
                self.title = self.title_from_file_path(file_path)
            if not self.finish():
                self.log_error(file_path.name)

    def parse(self, data, cell=False):
        """
        Process the records

        :param data: The data to be processed
        :param cell: ?
        :return:
        """
        if not cell and (len(data) == 0 or data[0:1] != b'[' or data.strip()[-1:] != b']'):
            self.log_error('File is malformed')
            return False
        i = 1
        verse_type = VerseType.tags[VerseType.Verse]
        while i < len(data):
            # Data is held as #name: value pairs inside groups marked as [].
            # Now we are looking for the name.
            if data[i:i + 1] == b'#':
                name_end = data.find(b':', i + 1)
                name = data[i + 1:name_end].decode(self.encoding).upper()
                i = name_end + 1
                while data[i:i + 1] == b' ':
                    i += 1
                if data[i:i + 1] == b'"':
                    end = data.find(b'"', i + 1)
                    value = data[i + 1:end]
                elif data[i:i + 1] == b'[':
                    j = i
                    inside_quotes = False
                    while j < len(data):
                        char = data[j:j + 1]
                        if char == b'"':
                            inside_quotes = not inside_quotes
                        elif not inside_quotes and char == b']':
                            end = j + 1
                            break
                        j += 1
                    value = data[i:end]
                else:
                    end = data.find(b',', i + 1)
                    if data.find(b'(', i, end) != -1:
                        end = data.find(b')', i) + 1
                    value = data[i:end]
                # If we are in the main group.
                if not cell:
                    if name == 'TITLE':
                        self.title = self.decode(self.unescape(value))
                    elif name == 'AUTHOR':
                        author = self.decode(self.unescape(value))
                        if len(author):
                            self.add_author(author)
                    elif name == 'COPYRIGHT':
                        self.add_copyright(self.decode(self.unescape(value)))
                    elif name[0:4] == 'CELL':
                        self.parse(value, cell=name[4:])
                # We are in a verse group.
                else:
                    if name == 'MARKER_NAME':
                        value = self.decode(value).strip()
                        if len(value):
                            verse_type = VerseType.tags[VerseType.from_loose_input(value[0])]
                            if len(value) >= 2 and value[-1] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
                                verse_type = "{verse}{value}".format(verse=verse_type, value=value[-1])
                    elif name == 'HOTKEY':
                        value = self.decode(value).strip()
                        # HOTKEY always appears after MARKER_NAME, so it
                        # effectively overrides MARKER_NAME, if present.
                        if len(value) and value in list(HOTKEY_TO_VERSE_TYPE.keys()):
                            verse_type = HOTKEY_TO_VERSE_TYPE[value]
                    if name == 'RTF':
                        value = self.unescape(value)
                        value = self.decode(value)
                        result = strip_rtf(value, self.encoding)
                        if result is None:
                            return False
                        verse, self.encoding = result
                        lines = verse.strip().split('\n')
                        # If any line inside any verse contains CCLI or
                        # only Public Domain, we treat this as special data:
                        # we remove that line and add data to specific field.
                        processed_lines = []
                        for i in range(len(lines)):
                            line = lines[i].strip()
                            if line[:3].lower() == 'ccl':
                                m = re.search(r'[0-9]+', line)
                                if m:
                                    self.ccli_number = int(m.group(0))
                                    continue
                            elif line.lower() == 'public domain':
                                self.add_copyright('Public Domain')
                                continue
                            processed_lines.append(line)
                        self.add_verse('\n'.join(processed_lines).strip(), verse_type)
                if end == -1:
                    break
                i = end + 1
            i += 1
        return True

    def title_from_file_path(self, file_path):
        """
        Extract the title from the filename

        :param pathlib.Path file_path: File being imported
        :return: The song title
        :rtype: str
        """
        title = file_path.stem
        # For some strange reason all example files names ended with 1-7.
        if title.endswith('1-7'):
            title = title[:-3]
        return title.replace('_', ' ')

    def decode(self, blob):
        attempted_encodings = set()
        while self.encoding and self.encoding not in attempted_encodings:
            attempted_encodings.add(self.encoding)
            try:
                return blob.decode(self.encoding)
            except (LookupError, UnicodeDecodeError):
                self.encoding = retrieve_windows_encoding()
        return blob.decode('utf-8', errors='replace')

    def unescape(self, text):
        text = text.replace(b'^^', b'"')
        text = text.replace(b'^', b'\'')
        return text.strip()
