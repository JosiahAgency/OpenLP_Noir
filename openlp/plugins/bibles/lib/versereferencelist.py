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

from openlp.plugins.bibles.lib import get_reference_separator


class VerseReferenceList(object):
    """
    The VerseReferenceList class encapsulates a list of verse references, but maintains the order in which they were
    added.
    """

    def __init__(self):
        self.verse_list = []
        self.version_list = []
        self.current_index = -1

    def add(self, book, chapter, verse, version, copyright, permission):
        self.add_version(version, copyright, permission)
        if not self.verse_list or self.verse_list[self.current_index]['book'] != book:
            self.verse_list.append({'version': version, 'book': book, 'chapter': chapter, 'start': verse, 'end': verse})
            self.current_index += 1
        elif self.verse_list[self.current_index]['chapter'] != chapter:
            self.verse_list.append({'version': version, 'book': book, 'chapter': chapter, 'start': verse, 'end': verse})
            self.current_index += 1
        elif (self.verse_list[self.current_index]['end'] + 1) == verse:
            self.verse_list[self.current_index]['end'] = verse
        else:
            self.verse_list.append({'version': version, 'book': book, 'chapter': chapter, 'start': verse, 'end': verse})
            self.current_index += 1

    def add_version(self, version, copyright, permission):
        for bible_version in self.version_list:
            if bible_version['version'] == version:
                return
        self.version_list.append({'version': version, 'copyright': copyright, 'permission': permission})

    def format_verses(self):
        verse_sep = get_reference_separator('sep_v_display')
        range_sep = get_reference_separator('sep_r_display')
        list_sep = get_reference_separator('sep_l_display')
        result = ''
        for index, verse in enumerate(self.verse_list):
            if index == 0:
                result = '{book} {chapter}{sep}{verse}'.format(book=verse['book'],
                                                               chapter=verse['chapter'],
                                                               sep=verse_sep,
                                                               verse=verse['start'])
                if verse['start'] != verse['end']:
                    result = '{result}{sep}{end}'.format(result=result, sep=range_sep, end=verse['end'])
                continue
            prev = index - 1
            if self.verse_list[prev]['version'] != verse['version']:
                result = '{result} ({version})'.format(result=result, version=self.verse_list[prev]['version'])
            result += '{sep} '.format(sep=list_sep)
            if self.verse_list[prev]['book'] != verse['book']:
                result = '{result}{book} {chapter}{sep}'.format(result=result,
                                                                book=verse['book'],
                                                                chapter=verse['chapter'],
                                                                sep=verse_sep)
            elif self.verse_list[prev]['chapter'] != verse['chapter']:
                result = '{result}{chapter}{sep}'.format(result=result, chapter=verse['chapter'], sep=verse_sep)
            result += str(verse['start'])
            if verse['start'] != verse['end']:
                result = '{result}{sep}{end}'.format(result=result, sep=range_sep, end=verse['end'])
        if len(self.version_list) > 1:
            result = '{result} ({version})'.format(result=result, version=verse['version'])
        return result

    def format_versions(self, version=True, copyright=True, permission=True):
        """
        Format a string with the bible versions used

        :param version: If the version name should be included, default is true.
        :param copyright: If the copyright info should be included, default is true.
        :param permission: If the permission info should be included, default is true.
        :return: A formatted string with the bible versions used
        """
        result = ''
        for bible_version in self.version_list:
            parts = []
            if version:
                parts.append(bible_version['version'])
            if copyright and bible_version['copyright'].strip():
                parts.append(bible_version['copyright'])
            if permission and bible_version['permission'].strip():
                parts.append(bible_version['permission'])
            if not parts:
                continue
            if result:
                if result[-1] not in [';', ',', '.']:
                    result += ';'
                result += ' '
            result += ', '.join(parts)
        result = result.rstrip()
        if result.endswith(','):
            return result[:len(result) - 1]
        return result
