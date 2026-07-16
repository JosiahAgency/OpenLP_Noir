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
The :mod:`~openlp.display.render` module contains functions for rendering.
"""
import html
import logging
import mako
import math
import os
import re

from PySide6 import QtWidgets, QtGui

from openlp.core.common import ThemeLevel
from openlp.core.common.enum import ServiceItemType
from openlp.core.common.i18n import translate
from openlp.core.common.mixins import LogMixin
from openlp.core.common.registry import Registry, RegistryBase
from openlp.core.common.utils import wait_for
from openlp.core.display.screens import ScreenList
from openlp.core.display.window import DisplayWindow
from openlp.core.lib import ItemCapabilities
from openlp.core.lib.formattingtags import FormattingTags


log = logging.getLogger(__name__)

ENGLISH_NOTES = '(C|D|E|F|G|A|B|N\\.C\\.)?'
GERMAN_NOTES = '(C|D|E|F|G|A|B|H|N\\.C\\.)?'
NEOLATIN_NOTES = '(Do|Re|Mi|Fa|Sol|La|Si|N\\.C\\.)?'
CHORD_PREFIXES = '(=|\\(|\\|)*?'
CHORD_SUFFIXES = '(b|#|x|\\+|-|M|m|Maj|maj|min|sus|dim|add|aug|dom|0|1|2|3|4|5|6|7|8|9|\\(|\\)|no|omit)*?'
SLIM_CHARS = 'fiíIÍjlĺľrtť.,;/ ()|"\'!:\\'
CHORD_TEMPLATE = '<span class="chordline">{chord}</span>'
FIRST_CHORD_TEMPLATE = '<span class="chordline">{chord}</span>'
NO_CHORD_TEMPLATE = '<span class="nochordline">{chord}</span>'
CHORD_LINE_TEMPLATE = '<span class="chord"><span><strong>{chord}</strong></span></span>{tail}{whitespace}{remainder}'
WHITESPACE_TEMPLATE = '<span class="ws">{whitespaces}</span>'
VERSE = 'The Lord said to {r}Noah{/r}: \n' \
    'There\'s gonna be a {su}floody{/su}, {sb}floody{/sb}\n' \
    'The Lord said to {g}Noah{/g}:\n' \
    'There\'s gonna be a {st}floody{/st}, {it}floody{/it}\n' \
    'Get those children out of the muddy, muddy \n' \
    '{r}C{/r}{b}h{/b}{bl}i{/bl}{y}l{/y}{g}d{/g}{pk}' \
    'r{/pk}{o}e{/o}{pp}n{/pp} of the Lord\n'
VERSE_FOR_LINE_COUNT = '\n'.join(map(str, range(100)))
TITLE = 'Arky Arky'
AUTHOR = 'John Doe'
FOOTER_COPYRIGHT = 'Public Domain'
CCLI_NO = '123456'

# Just so we can cache the regular expression objects
_chord_cache = {}
_line_cache = {}


def _construct_chord_regex(notes):
    """
    Create the regex for a particular set of notes

    :param notes: The regular expression for a set of valid notes
    :return: An expanded regular expression for valid chords
    """
    # chord = CHORD_PREFIXES + notes + CHORD_SUFFIXES
    return '(' + CHORD_PREFIXES + notes + CHORD_SUFFIXES + '(/' + notes + CHORD_SUFFIXES + ')?)'


def _construct_chord_match(notes):
    """
    Construct chord matching regular expression object

    :param notes: The regular expression for a set of valid notes
    :return: A compiled regular expression object
    """
    return re.compile(r'\[' + _construct_chord_regex(notes) + r'\]')


def _construct_chord_line_match(notes):
    """
    Construct a chord line matching regular expression object

    :param notes: The regular expression for a set of valid notes
    :return: A compiled regular expression object
    """
    return re.compile(r'\[' + _construct_chord_regex(notes) + r'\]([\u0080-\uFFFF,\w]*)'
                      r'([\u0080-\uFFFF\w\s\.\,\!\?\;\:\|\"\'\-\_]*)(\Z)?')


def _get_chord_match():
    """
    Get the right chord_match object based on the current chord notation
    """
    notation = Registry().get('settings').value('songs/chord notation')
    if notation not in _chord_cache.keys():
        if notation == 'german':
            _chord_cache[notation] = _construct_chord_match(GERMAN_NOTES)
        elif notation == 'neo-latin':
            _chord_cache[notation] = _construct_chord_match(NEOLATIN_NOTES)
        else:
            _chord_cache[notation] = _construct_chord_match(ENGLISH_NOTES)
    return _chord_cache[notation]


def _get_line_match():
    """
    Get the right chold line match based on the current chord notation
    """
    notation = Registry().get('settings').value('songs/chord notation')
    if notation not in _line_cache.keys():
        if notation == 'german':
            _line_cache[notation] = _construct_chord_line_match(GERMAN_NOTES)
        elif notation == 'neo-latin':
            _line_cache[notation] = _construct_chord_line_match(NEOLATIN_NOTES)
        else:
            _line_cache[notation] = _construct_chord_line_match(ENGLISH_NOTES)
    return _line_cache[notation]


def remove_chords(text):
    """
    Remove chords from the text

    :param text: Text to be cleaned
    """
    return _get_chord_match().sub(r'', text)


RE_HTML_STRIP = re.compile(r'<[^>]+>')


def remove_html_and_strip(text):
    """
    Removes all HTML from the text and strips the whitespace from the remaining lines.
    """
    lines = map(__clean_html_line, text.split('\n'))
    return '\n'.join(lines)


def __clean_html_line(line):
    line = RE_HTML_STRIP.sub('', line)
    return line.strip()


def remove_tags(text, can_remove_chords=False):
    """
    Remove Tags from text for display

    :param text: Text to be cleaned
    :param can_remove_chords: Can we remove the chords too?
    """
    text = text.replace('<br>', '\n')
    text = text.replace('<br/>', '\n')
    text = text.replace('<br />', '\n')
    text = text.replace('{br}', '\n')
    text = text.replace('&nbsp;', ' ')
    text = text.replace('<sup>', '')
    text = text.replace('</sup>', '')
    text = text.replace('<em>', '')
    text = text.replace('</em>', '')
    for tag in FormattingTags.get_html_tags():
        if tag.get('hidden'):
            text = re.sub(r'' + tag['start tag'] + ".*?" + tag['end tag'], '', text)
        else:
            text = text.replace(tag['start tag'], '')
            text = text.replace(tag['end tag'], '')
    # Remove ChordPro tags
    if can_remove_chords:
        text = remove_chords(text)
    return text


def has_valid_tags(text):
    """
    The :func:`~openlp.core.display.render.has_valid_tags` function validates the tags within ``text``.

    :param str text: The string with formatting tags in it.
    :returns bool: Returns True if tags are valid, False if there are parsing problems.
    """
    return True


def render_chords_in_line(match):
    """
    Render the chords in the line and align them using whitespaces.
    NOTE: There is equivalent javascript code in chords.js, in the updateSlide function. Make sure to update both!

    :param str match: The line which contains chords
    :returns str: The line with rendered html-chords
    """
    whitespaces = ''
    chord_length = 0
    tail_length = 0
    # The match could be "[G]sweet the " from a line like "A[D]mazing [D7]grace! How [G]sweet the [D]sound!"
    # The actual chord, would be "G" in match "[G]sweet the "
    chord = match.group(1)
    # The tailing word of the chord, would be "sweet" in match "[G]sweet the "
    tail = match.group(8)
    # The remainder of the line, until line end or next chord. Would be " the " in match "[G]sweet the "
    remainder = match.group(9)
    # Line end if found, else None
    end = match.group(10)
    # Based on char width calculate width of chord
    for chord_char in chord:
        if chord_char not in SLIM_CHARS:
            chord_length += 2
        else:
            chord_length += 1
    # Based on char width calculate width of tail
    for tail_char in tail:
        if tail_char not in SLIM_CHARS:
            tail_length += 2
        else:
            tail_length += 1
    # Based on char width calculate width of remainder
    for remainder_char in remainder:
        if remainder_char not in SLIM_CHARS:
            tail_length += 2
        else:
            tail_length += 1
    # If the chord is wider than the tail+remainder and the line goes on, some padding is needed
    if chord_length >= tail_length and end is None:
        # Decide if the padding should be "_" for drawing out words or spaces
        if tail:
            if not remainder:
                for c in range(math.ceil((chord_length - tail_length) / 2) + 2):
                    whitespaces += '_'
            else:
                for c in range(chord_length - tail_length + 1):
                    whitespaces += '&nbsp;'
        else:
            if not remainder:
                for c in range(math.floor((chord_length - tail_length) / 2)):
                    whitespaces += '_'
            else:
                for c in range(chord_length - tail_length + 1):
                    whitespaces += '&nbsp;'
    else:
        if not tail and remainder and remainder[0] == ' ':
            for c in range(chord_length):
                whitespaces += '&nbsp;'
    if whitespaces:
        if '_' in whitespaces:
            ws_length = len(whitespaces)
            if ws_length == 1:
                whitespaces = '&ndash;'
            else:
                wsl_mod = ws_length // 2
                ws_right = ws_left = ' ' * wsl_mod
                whitespaces = ws_left + '&ndash;' + ws_right
        whitespaces = WHITESPACE_TEMPLATE.format(whitespaces=whitespaces)
    return CHORD_LINE_TEMPLATE.format(chord=html.escape(chord), tail=html.escape(tail), whitespace=whitespaces,
                                      remainder=html.escape(remainder))


def render_chords(text):
    """
    Render ChordPro tags

    :param str text: The text containing the chords
    :returns str: The text containing the rendered chords
    """
    text_lines = text.split('{br}')
    chord_line_match = _get_line_match()
    rendered_lines = []
    chords_on_prev_line = False
    for line in text_lines:
        # If a ChordPro is detected in the line, replace it with a html-span tag and wrap the line in a span tag.
        if '[' in line and ']' in line:
            if chords_on_prev_line:
                chord_template = CHORD_TEMPLATE
            else:
                chord_template = FIRST_CHORD_TEMPLATE
                chords_on_prev_line = True
            # Matches a chord, a tail, a remainder and a line end. See expand_and_align_chords_in_line() for more info.
            new_line = chord_template.format(chord=chord_line_match.sub(render_chords_in_line, line))
            rendered_lines.append(new_line)
        else:
            chords_on_prev_line = False
            # rendered_lines.append(html.escape(line))
            chord_template = NO_CHORD_TEMPLATE
            new_line = chord_template.format(chord=line)
            rendered_lines.append(new_line)
    return '{br}'.join(rendered_lines)


def compare_chord_lyric_width(chord, lyric):
    """
    Compare the width of chord and lyrics. If chord width is greater than the lyric width the diff is returned.

    :param chord:
    :param lyric:
    :return:
    """
    chord_length = 0
    if chord == '&nbsp;':
        return 0
    chord = re.sub(r'\{.*?\}', r'', chord)
    lyric = re.sub(r'\{.*?\}', r'', lyric)
    for chord_char in chord:
        if chord_char not in SLIM_CHARS:
            chord_length += 2
        else:
            chord_length += 1
    lyriclen = 0
    for lyric_char in lyric:
        if lyric_char not in SLIM_CHARS:
            lyriclen += 2
        else:
            lyriclen += 1
    if chord_length > lyriclen:
        return chord_length - lyriclen
    else:
        return 0


def find_formatting_tags(text, active_formatting_tags):
    """
    Look for formatting tags in lyrics and adds/removes them to/from the given list. Returns the update list.

    :param text:
    :param active_formatting_tags:
    :return:
    """
    if not re.search(r'\{.*?\}', text):
        return active_formatting_tags
    word_iterator = iter(text)
    # Loop through lyrics to find any formatting tags
    for char in word_iterator:
        if char == '{':
            tag = ''
            char = next(word_iterator)
            start_tag = True
            if char == '/':
                start_tag = False
                char = next(word_iterator)
            while char != '}':
                tag += char
                char = next(word_iterator)
            # See if the found tag has an end tag
            for formatting_tag in FormattingTags.get_html_tags():
                if formatting_tag['start tag'] == '{' + tag + '}':
                    if formatting_tag['end html']:
                        if start_tag:
                            # prepend the new tag to the list of active formatting tags
                            active_formatting_tags[:0] = [tag]
                        else:
                            # remove the tag from the list
                            active_formatting_tags.remove(tag)
                    # Break out of the loop matching the found tag against the tag list.
                    break
    return active_formatting_tags


def render_chords_for_printing(text, line_split):
    """
    Render ChordPro tags for printing

    :param str text: The text containing the chords to be rendered.
    :param str line_split: The character(s) used to split lines
    :returns str: The rendered chords
    """
    if not re.search(r'\[.*?\]', text):
        return text
    text_lines = text.split(line_split)
    rendered_text_lines = []
    for line in text_lines:
        # If a ChordPro is detected in the line, build html tables.
        new_line = '<table class="line" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td>'
        active_formatting_tags = []
        if re.search(r'\[.*?\]', line):
            words = line.split(' ')
            in_chord = False
            for word in words:
                chords = []
                lyrics = []
                new_line += '<table class="segment" cellpadding="0" cellspacing="0" border="0" align="left">'
                # If the word contains a chord, we need to handle it.
                if re.search(r'\[.*?\]', word):
                    chord = ''
                    lyric = ''
                    # Loop over each character of the word
                    for char in word:
                        if char == '[':
                            in_chord = True
                            if lyric != '':
                                if chord == '':
                                    chord = '&nbsp;'
                                chords.append(chord)
                                lyrics.append(lyric)
                                chord = ''
                                lyric = ''
                        elif char == ']' and in_chord:
                            in_chord = False
                        elif in_chord:
                            chord += char
                        else:
                            lyric += char
                    if lyric != '' or chord != '':
                        if chord == '':
                            chord = '&nbsp;'
                        if lyric == '':
                            lyric = '&nbsp;'
                        chords.append(chord)
                        lyrics.append(lyric)
                    new_chord_line = '<tr class="chordrow">'
                    new_lyric_line = '</tr><tr>'
                    for i in range(len(lyrics)):
                        spacer = compare_chord_lyric_width(chords[i], lyrics[i])
                        # Handle formatting tags
                        start_formatting_tags = ''
                        if active_formatting_tags:
                            start_formatting_tags = '{' + '}{'.join(active_formatting_tags) + '}'
                        # Update list of active formatting tags
                        active_formatting_tags = find_formatting_tags(lyrics[i], active_formatting_tags)
                        end_formatting_tags = ''
                        if active_formatting_tags:
                            end_formatting_tags = '{/' + '}{/'.join(active_formatting_tags) + '}'
                        new_chord_line += '<td class="chord">%s</td>' % chords[i]
                        # Check if this is the last column, if so skip spacing calc and instead insert a single space
                        if i + 1 == len(lyrics):
                            new_lyric_line += '<td class="lyrics">{starttags}{lyrics}&nbsp;{endtags}</td>'.format(
                                starttags=start_formatting_tags, lyrics=lyrics[i], endtags=end_formatting_tags)
                        else:
                            spacing = ''
                            if spacer > 0:
                                space = '&nbsp;' * int(math.ceil(spacer / 2))
                                spacing = '<span class="chordspacing">%s-%s</span>' % (space, space)
                            new_lyric_line += '<td class="lyrics">{starttags}{lyrics}{spacing}{endtags}</td>'.format(
                                starttags=start_formatting_tags, lyrics=lyrics[i], spacing=spacing,
                                endtags=end_formatting_tags)
                    new_line += new_chord_line + new_lyric_line + '</tr>'
                else:
                    start_formatting_tags = ''
                    if active_formatting_tags:
                        start_formatting_tags = '{' + '}{'.join(active_formatting_tags) + '}'
                    active_formatting_tags = find_formatting_tags(word, active_formatting_tags)
                    end_formatting_tags = ''
                    if active_formatting_tags:
                        end_formatting_tags = '{/' + '}{/'.join(active_formatting_tags) + '}'
                    new_line += '<tr class="chordrow"><td class="chord">&nbsp;</td></tr><tr><td class="lyrics">' \
                                '{starttags}{lyrics}&nbsp;{endtags}</td></tr>'.format(
                                    starttags=start_formatting_tags, lyrics=word, endtags=end_formatting_tags)
                new_line += '</table>'
        else:
            new_line += line
        new_line += '</td></tr></table>'
        rendered_text_lines.append(new_line)
    # the {br} tag used to split lines is not inserted again since the style of the line-tables makes them redundant.
    return ''.join(rendered_text_lines)


def render_tags(text, can_render_chords=False, is_printing=False):
    """
    The :func:`~openlp.core.display.render.render_tags` function takes a stirng with OpenLP-style tags in it
    and replaces them with the HTML version.

    :param str text: The string with OpenLP-style tags to be rendered.
    :param bool can_render_chords: Should the chords be rendererd?
    :param bool is_printing: Are we going to print this?
    :returns str: The HTML version of the tags is returned as a string.
    """
    if can_render_chords:
        if is_printing:
            text = render_chords_for_printing(text, '{br}')
        else:
            text = render_chords(text)
    else:
        text = remove_chords(text)
    for tag in FormattingTags.get_html_tags():
        text = text.replace(tag['start tag'], tag['start html'])
        text = text.replace(tag['end tag'], tag['end html'])
    return text


def words_split(line):
    """
    Split the slide up by word so can wrap better

    :param line: Line to be split
    """
    # this parse we are to be wordy
    return re.split(r'\s+', line)


def get_start_tags(raw_text):
    """
    Tests the given text for not closed formatting tags and returns a tuple consisting of three unicode strings::

        ('{st}{r}Text text text{/r}{/st}', '{st}{r}', '<strong><span style="-webkit-text-fill-color:red">')

    The first unicode string is the text, with correct closing tags. The second unicode string are OpenLP's opening
    formatting tags and the third unicode string the html opening formatting tags.

    :param raw_text: The text to test. The text must **not** contain html tags, only OpenLP formatting tags
    are allowed::
            {st}{r}Text text text
    """
    raw_tags = []
    html_tags = []
    endless_tags = []
    for formatting_tag in FormattingTags.get_html_tags():
        if not formatting_tag['end html']:
            endless_tags.append(formatting_tag['start tag'])
    for tag in FormattingTags.get_html_tags():
        if tag['start tag'] in endless_tags:
            continue
        if raw_text.count(tag['start tag']) != raw_text.count(tag['end tag']):
            raw_tags.append((raw_text.find(tag['start tag']), tag['start tag'], tag['end tag']))
            html_tags.append((raw_text.find(tag['start tag']), tag['start html']))
    # Sort the lists, so that the tags which were opened first on the first slide (the text we are checking) will be
    # opened first on the next slide as well.
    raw_tags.sort(key=lambda tag: tag[0])
    html_tags.sort(key=lambda tag: tag[0])
    # Create a list with closing tags for the raw_text.
    end_tags = []
    start_tags = []
    for tag in raw_tags:
        start_tags.append(tag[1])
        end_tags.append(tag[2])
    end_tags.reverse()
    # Remove the indexes.
    html_tags = [tag[1] for tag in html_tags]
    return raw_text + ''.join(end_tags), ''.join(start_tags), ''.join(html_tags)


class ThemePreviewRenderer(DisplayWindow, LogMixin):
    """
    A virtual display used for rendering thumbnails and other offscreen tasks
    """
    def __init__(self, *args, **kwargs):
        """
        Constructor
        """
        super().__init__(*args, **kwargs)
        self.force_page = False

    def calculate_line_count(self):
        """
        Calculate the number of lines that fits on one slide
        """
        return self.run_in_display('calculateLineCount', is_sync=True)

    def clear_slides(self):
        """
        Clear slides
        """
        return self.run_in_display('clearSlides')

    def generate_footer(self):
        """
        """
        footer_template = self.settings.value('songs/footer template')
        # Keep this in sync with the list in songstab.py
        vars = {
            'title': TITLE,
            'authors_none_label': translate('OpenLP.Ui', 'Written by'),
            'authors_words_label': translate('SongsPlugin.AuthorType', 'Words',
                                             'Author who wrote the lyrics of a song'),
            'authors_words': [AUTHOR],
            'copyright': FOOTER_COPYRIGHT,
            'ccli_license': self.settings.value('core/ccli number'),
            'ccli_license_label': translate('SongsPlugin.MediaItem', 'CCLI License'),
            'ccli_number': CCLI_NO,
        }
        try:
            footer_html = mako.template.Template(footer_template).render_unicode(**vars).replace('\n', '')
        except mako.exceptions.SyntaxException:
            log.error('Failed to render Song footer html:\n' + mako.exceptions.text_error_template().render())
            footer_html = 'Dummy footer text'
        return footer_html

    def generate_preview(self, theme_data, force_page=False, generate_screenshot=True):
        """
        Generate a preview of a theme.

        :param theme_data:  The theme to generated a preview for.
        :param force_page: Flag to tell message lines per page need to be generated.
        :param generate_screenshot: Do I need to generate a screen shot?
        :rtype: QtGui.QPixmap
        """
        # save value for use in format_slide
        self.force_page = force_page
        if not self.force_page:
            self.set_theme(theme_data, is_sync=True, service_item_type=ServiceItemType.Text)
            slides = self.format_slide(VERSE, None)
            verses = dict()
            verses['title'] = TITLE
            verses['text'] = render_tags(slides[0])
            verses['verse'] = 'V1'
            verses['footer'] = self.generate_footer()
            self.load_verses([verses], is_sync=True)
            # Wait for a second
            wait_for(lambda: False, timeout=1)
            self.force_page = False
            if generate_screenshot:
                return self.grab()
        self.force_page = False
        return None

    def format_slide(self, text, item):
        """
        Calculate how much text can fit on a slide.

        :param text:  The words to go on the slides.
        :param item: The :class:`~openlp.core.lib.serviceitem.ServiceItem` item object.

        """
        wait_for(lambda: self._is_initialised)
        self.log_debug('format slide')
        if item:
            # Set theme for preview
            self.set_theme(item.get_theme_data(self.theme_level))
        # Add line endings after each line of text used for bibles.
        line_end = '<br>'
        if item and item.is_capable(ItemCapabilities.NoLineBreaks):
            line_end = ' '
        # Bibles
        if item and item.name == 'bibles':
            if item.is_capable(ItemCapabilities.CanWordSplit):
                pages = self._paginate_slide_words(text.split('\n'), line_end)
            else:
                if item.is_capable(ItemCapabilities.NoLineBreaks):
                    pages = self._paginate_slide(text.split('\n'), "")
                else:
                    pages = self._paginate_slide(text.split('\n'), line_end)
        # Songs and Custom
        elif item is None or (item and item.is_capable(ItemCapabilities.CanSoftBreak)):
            pages = []
            if '[---]' in text:
                # Remove Overflow split if at start of the text
                if text.startswith('[---]'):
                    text = text[5:]
                # Remove two or more option slide breaks next to each other (causing infinite loop).
                while '\n[---]\n[---]\n' in text:
                    text = text.replace('\n[---]\n[---]\n', '\n[---]\n')
                while ' [---]' in text:
                    text = text.replace(' [---]', '[---]')
                while '[---] ' in text:
                    text = text.replace('[---] ', '[---]')
                # Grab the number of lines in the text to use as a max number of loops
                count = text.count('\n') + 1
                for _ in range(count):
                    slides = text.split('\n[---]\n', 2)
                    # If there are (at least) two occurrences of [---] we use the first two slides (and neglect the last
                    # for now).
                    if len(slides) == 3:
                        html_text = render_tags('\n'.join(slides[:2]))
                    # We check both slides to determine if the optional split is needed (there is only one optional
                    # split).
                    else:
                        html_text = render_tags('\n'.join(slides))
                    html_text = html_text.replace('\n', '<br>')
                    if self._text_fits_on_slide(html_text):
                        # The first two optional slides fit (as a whole) on one slide. Replace the first occurrence
                        # of [---].
                        text = text.replace('\n[---]', '', 1)
                    else:
                        # The first optional slide fits, which means we have to render the first optional slide.
                        text_contains_split = '[---]' in text
                        if text_contains_split:
                            try:
                                text_to_render, text = text.split('\n[---]\n', 1)
                            except ValueError:
                                text_to_render = text.split('\n[---]\n')[0]
                                text = ''
                            text_to_render, raw_tags, html_tags = get_start_tags(text_to_render)
                            if text:
                                text = raw_tags + text
                        else:
                            text_to_render = text
                            text = ''
                        lines = text_to_render.strip('\n').split('\n')
                        slides = self._paginate_slide(lines, line_end)
                        if len(slides) > 1 and text:
                            # Add all slides apart from the last one the list.
                            pages.extend(slides[:-1])
                            if text_contains_split:
                                text = slides[-1] + '\n[---]\n' + text
                            else:
                                text = slides[-1] + '\n' + text
                            text = text.replace('<br>', '\n')
                        else:
                            pages.extend(slides)
                    if '[---]' not in text:
                        lines = text.strip('\n').split('\n')
                        pages.extend(self._paginate_slide(lines, line_end))
                        break
            else:
                # Clean up line endings.
                pages = self._paginate_slide(text.split('\n'), line_end)
        # Other text items whose words may be split across slides (e.g. EGW Library
        # paragraphs, which are single long lines that _paginate_slide cannot break)
        elif item.is_capable(ItemCapabilities.CanWordSplit):
            pages = self._paginate_slide_words(text.split('\n'), line_end)
        else:
            pages = self._paginate_slide(text.split('\n'), line_end)
        new_pages = []
        for page in pages:
            while page.endswith('<br>'):
                page = page[:-4]
            new_pages.append(page)
        return new_pages

    def _paginate_slide(self, lines, line_end):
        """
        Figure out how much text can appear on a slide, using the current theme settings.

        **Note:** The smallest possible "unit" of text for a slide is one line. If a single line is too big for the
        main area on its own, it is split further word by word over as many slides as needed.

        :param lines: The text to be fitted on the slide split into lines.
        :param line_end: The text added after each line. Either ``' '`` or ``'<br>``.
        """
        formatted = []
        previous_html = ''
        previous_raw = ''
        # separator = '<br>'
        separator = line_end
        html_lines = list(map(render_tags, lines))
        # Text too long so go to next page.
        if not self._text_fits_on_slide(separator.join(html_lines)):
            previous_html, previous_raw = self._binary_chop(
                formatted, previous_html, previous_raw, html_lines, lines, separator, '')
            if previous_html:
                formatted.append(previous_raw)
            # The binary chop cannot split below one line, so a page holding a single line which is too big for the
            # main area can still overflow. Split any such page further, word by word.
            pages = []
            for page in formatted:
                if self._text_fits_on_slide(render_tags(page)):
                    pages.append(page)
                else:
                    pages.extend(self._paginate_slide_words(page.split('<br>'), line_end))
            return pages
        formatted.append(separator.join(lines))
        return formatted

    def _paginate_slide_words(self, lines, line_end):
        """
        Figure out how much text can appear on a slide, using the current theme settings.

        **Note:** The smallest possible "unit" of text for a slide is one word. If one line is too long it will be
        processed word by word. This is sometimes need for **bible** verses.

        :param lines: The text to be fitted on the slide split into lines.
        :param line_end: The text added after each line. Either ``' '`` or ``'<br>``. This is needed for **bibles**.
        """
        formatted = []
        previous_html = ''
        previous_raw = ''
        for line in lines:
            line = line.strip()
            html_line = render_tags(line)
            # Text too long so go to next page.
            if not self._text_fits_on_slide(previous_html + html_line):
                # Check if there was a verse before the current one and append it, when it fits on the page.
                if previous_html:
                    if self._text_fits_on_slide(previous_html):
                        formatted.append(previous_raw)
                        previous_html = ''
                        previous_raw = ''
                        # Now check if the current verse will fit, if it does not we have to start to process the verse
                        # word by word.
                        if self._text_fits_on_slide(html_line):
                            previous_html = html_line + line_end
                            previous_raw = line + line_end
                            continue
                # Figure out how many words of the line will fit on screen as the line will not fit as a whole.
                raw_words = words_split(line)
                html_words = list(map(render_tags, raw_words))
                previous_html, previous_raw = \
                    self._binary_chop(formatted, previous_html, previous_raw, html_words, raw_words, ' ', line_end)
            else:
                previous_html += html_line + line_end
                previous_raw += line + line_end
        if previous_html:
            formatted.append(previous_raw)
        return formatted

    def _binary_chop(self, formatted, previous_html, previous_raw, html_list, raw_list, separator, line_end):
        """
        This implements the binary chop algorithm for faster rendering. This algorithm works line based (line by line)
        and word based (word by word). It is assumed that this method is **only** called, when the lines/words to be
        rendered do **not** fit as a whole.

        :param formatted: The list to append any slides.
        :param previous_html: The html text which is know to fit on a slide, but is not yet added to the list of
        slides. (unicode string)
        :param previous_raw: The raw text (with formatting tags) which is known to fit on a slide, but is not yet added
        to the list of slides. (unicode string)
        :param html_list: The elements which do not fit on a slide and needs to be processed using the binary chop.
        The text contains html.
        :param raw_list: The elements which do not fit on a slide and needs to be processed using the binary chop.
        The elements can contain formatting tags.
        :param separator: The separator for the elements. For lines this is ``'<br>'`` and for words this is ``' '``.
        :param line_end: The text added after each "element line". Either ``' '`` or ``'<br>``. This is needed for
         bibles.
        """
        smallest_index = 0
        highest_index = len(html_list) - 1
        index = highest_index // 2
        while True:
            if not self._text_fits_on_slide(previous_html + separator.join(html_list[:index + 1]).strip()):
                # We know that it does not fit, so change/calculate the new index and highest_index accordingly.
                highest_index = index
                index = index - (index - smallest_index) // 2
            else:
                smallest_index = index
                index = index + (highest_index - index) // 2
            # We found the number of elements which will fit.
            if smallest_index == index or highest_index == index:
                index = smallest_index
                text = previous_raw.rstrip('<br>') + separator.join(raw_list[:index + 1])
                text, raw_tags, html_tags = get_start_tags(text)
                formatted.append(text)
                previous_html = ''
                previous_raw = ''
                # Stop here as the theme line count was requested.
                if self.force_page:
                    Registry().execute('theme_line_count', index + 1)
                    break
            else:
                continue
            # Check if the remaining elements fit on the slide.
            check_string = separator.join(html_list[index + 1:]).strip()
            if self._text_fits_on_slide(html_tags + check_string):
                previous_html = html_tags + check_string + line_end
                check_string_raw = separator.join(raw_list[index + 1:]).strip()
                previous_raw = raw_tags + check_string_raw + line_end
                break
            else:
                # The remaining elements do not fit, thus reset the indexes, create a new list and continue.
                raw_list = raw_list[index + 1:]
                log.debug(raw_list)
                raw_list[0] = raw_tags + raw_list[0]
                html_list = html_list[index + 1:]
                html_list[0] = html_tags + html_list[0]
                smallest_index = 0
                highest_index = len(html_list) - 1
                index = highest_index // 2
        return previous_html, previous_raw

    def _text_fits_on_slide(self, text):
        """
        Checks if the given ``text`` fits on a slide. If it does ``True`` is returned, otherwise ``False``.
        Text should always "fit" for empty strings

        :param text:  The text to check. It may contain HTML tags.
        """
        if text == '':
            return True
        self.clear_slides()
        self.log_debug('_text_fits_on_slide: 1\n{text}'.format(text=text))
        # run_in_display JSON-encodes the parameters, so the text must not be escaped here,
        # otherwise stray backslashes end up in the measured text and skew the result.
        self.run_in_display('setTextSlide', text, is_sync=True)
        self.log_debug('_text_fits_on_slide: 2')
        does_text_fit = self.run_in_display('doesContentFit', is_sync=True)
        return does_text_fit

    def save_screenshot(self, fname=None):
        """
        Save a screenshot, either returning it or saving it to file. Do some extra work to actually get a picture.
        """
        self.setVisible(True)
        QtWidgets.QApplication.instance().processEvents()
        wait_for(lambda: False, timeout=1)
        pixmap = self.grab()
        self.setVisible(False)
        pixmap = QtGui.QPixmap(self.webview.size())
        self.webview.render(pixmap)
        if fname:
            ext = os.path.splitext(fname)[-1][1:]
            pixmap.save(fname, ext)
        else:
            return pixmap


class Renderer(RegistryBase, ThemePreviewRenderer):
    """
    A virtual display used for rendering thumbnails and other offscreen tasks
    """
    def __init__(self, *args, **kwargs):
        """
        Constructor
        """
        super().__init__(*args, **kwargs)
        self.force_page = False
        screen_list = ScreenList()
        for screen in screen_list:
            if screen.is_display:
                self.setGeometry(screen.display_geometry.x(), screen.display_geometry.y(),
                                 screen.display_geometry.width(), screen.display_geometry.height())
                break
        else:
            # If there is no display screen, use the first screen as a fallback
            screen = screen_list[0]
            self.setGeometry(screen.display_geometry.x(), screen.display_geometry.y(),
                             screen.display_geometry.width(), screen.display_geometry.height())
        # If the display is not show'ed and hidden like this webegine will not render
        self.show()
        self.hide()
        self.theme_level = ThemeLevel.Global

    def set_theme_level(self, theme_level):
        """
        Sets the theme level.

        :param theme_level: The theme level to be used.
        """
        self.theme_level = theme_level
