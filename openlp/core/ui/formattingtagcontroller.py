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
The :mod:`formattingtagform` provides an Tag Edit facility. The Base set are protected and included each time loaded.
Custom tags can be defined and saved. The Custom Tag arrays are saved in a pickle so QSettings works on them. Base Tags
cannot be changed.
"""
import re

from openlp.core.common.i18n import translate
from openlp.core.lib.formattingtags import FormattingTags


class FormattingTagController(object):
    """
    The :class:`FormattingTagController` manages the non UI functions .
    """
    def __init__(self):
        """
        Initiator
        """
        self.html_tag_regex = re.compile(
            r'<(?:(?P<close>/(?=[^\s/>]+>))?'
            r'(?P<tag>[^\s/!?>]+)(?:\s+[^\s=]+="[^"]*")*\s*(?P<empty>/)?'
            r'|(?P<cdata>!\[CDATA\[(?:(?!\]\]>).)*\]\])'
            r'|(?P<procinst>\?(?:(?!\?>).)*\?)'
            r'|(?P<comment>!--(?:(?!--!?\>).)*(?:--!?)\>))>')
        self.html_regex = re.compile(r'^(?:[^<>]*%s)*[^<>]*$' % self.html_tag_regex.pattern)

    def pre_save(self):
        """
        Cleanup the array before save validation runs
        """
        self.protected_tags = [tag for tag in FormattingTags.html_expands if tag.get('protected')]
        self.custom_tags = []

    def validate_for_save(self, desc, tag, start_html, end_html, hidden):
        """
        Validate a custom tag and add to the tags array if valid..

        `desc`
            Explanation of the tag.

        `tag`
            The tag in the song used to mark the text.

        `start_html`
            The start html tag.

        `end_html`
            The end html tag.

        `hidden`
            option to hide tag content from main window.

        """
        for line_number, html1 in enumerate(self.protected_tags):
            if self._strip(html1['start tag']) == tag:
                return translate('OpenLP.FormattingTagForm', 'Tag {tag} already defined.').format(tag=tag)
            if self._strip(html1['desc']) == desc:
                return translate('OpenLP.FormattingTagForm', 'Description {tag} already defined.').format(tag=tag)
        for line_number, html1 in enumerate(self.custom_tags):
            if self._strip(html1['start tag']) == tag:
                return translate('OpenLP.FormattingTagForm', 'Tag {tag} already defined.').format(tag=tag)
            if self._strip(html1['desc']) == desc:
                return translate('OpenLP.FormattingTagForm', 'Description {tag} already defined.').format(tag=tag)
        tag = {
            'desc': desc,
            'start tag': '{{{tag}}}'.format(tag=tag),
            'start html': start_html,
            'end tag': '{{/{tag}}}'.format(tag=tag),
            'end html': end_html,
            'protected': False,
            'temporary': False,
            'hidden': hidden
        }
        self.custom_tags.append(tag)

    def save_tags(self):
        """
        Save the new tags if they are valid.
        """
        FormattingTags.save_html_tags(self.custom_tags)
        FormattingTags.load_tags()

    def _strip(self, tag):
        """
        Remove tag wrappers for editing.

        `tag`
            Tag to be stripped
        """
        tag = tag.replace('{', '')
        tag = tag.replace('}', '')
        return tag

    def start_html_to_end_html(self, start_html):
        """
        Return the end HTML for a given start HTML or None if invalid.

        `start_html`
            The start html tag.

        """
        end_tags = []
        match = self.html_regex.match(start_html)
        if match:
            match = self.html_tag_regex.search(start_html)
            while match:
                if match.group('tag'):
                    tag = match.group('tag').lower()
                    if match.group('close'):
                        if match.group('empty') or not end_tags or end_tags.pop() != tag:
                            return
                    elif not match.group('empty'):
                        end_tags.append(tag)
                match = self.html_tag_regex.search(start_html, match.end())
            return ''.join(map(lambda tag: '</{tag}>'.format(tag=tag), reversed(end_tags)))

    def start_tag_changed(self, start_html, end_html):
        """
        Validate the HTML tags when the start tag has been changed.

        `start_html`
            The start html tag.

        `end_html`
            The end html tag.

        """
        end = self.start_html_to_end_html(start_html)
        if not end_html:
            if not end:
                return translate('OpenLP.FormattingTagForm',
                                 'Start tag {tag} is not valid HTML').format(tag=start_html), None
            return None, end
        return None, None

    def end_tag_changed(self, start_html, end_html):
        """
        Validate the HTML tags when the end tag has been changed.

        `start_html`
            The start html tag.

        `end_html`
            The end html tag.

        """
        end = self.start_html_to_end_html(start_html)
        if not end_html:
            return None, end
        if end and end != end_html:
            return (translate('OpenLP.FormattingTagForm',
                              'End tag {end} does not match end tag for start tag {start}').format(end=end,
                                                                                                   start=start_html),
                    None)
        return None, None
