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
The :mod:`serviceitem` provides the service item functionality including the
type and capability of an item.
"""
import datetime
import logging
import ntpath
import os
import time
import uuid
from copy import deepcopy
from pathlib import Path
from shutil import copytree, copy, move

from PySide6 import QtGui

from openlp.core.common import ThemeLevel, sha256_file_hash
from openlp.core.common.applocation import AppLocation
from openlp.core.common.enum import ServiceItemType
from openlp.core.common.i18n import translate
from openlp.core.common.mixins import RegistryProperties
from openlp.core.common.registry import Registry
from openlp.core.common.utils import wait_for
from openlp.core.display.render import remove_html_and_strip, remove_tags, render_tags, render_chords_for_printing
from openlp.core.lib import create_thumb, image_to_data_uri, ItemCapabilities
from openlp.core.lib.theme import BackgroundType, TransitionSpeed
from openlp.core.state import State
from openlp.core.ui.icons import UiIcons
from openlp.core.ui.media import parse_stream_path


log = logging.getLogger(__name__)


class ServiceItem(RegistryProperties):
    """
    The service item is a base class for the plugins to use to interact with
    the service manager, the slide controller, and the projection screen
    compositor.
    """
    log.info('Service Item created')

    def __init__(self, plugin=None):
        """
        Set up the service item.

        :param plugin: The plugin that this service item belongs to.
        """
        if plugin:
            self.name = plugin.name
        self._rendered_slides = None
        self._display_slides = None
        self._print_slides = None
        self._creating_slides = False
        self.title = ''
        self.slides = []
        self.processor = None
        self.audit = ''
        self.items = []
        self.icon = UiIcons().default
        self.raw_footer = []
        # Plugins can set footer_html themselves. If they don't, it will be generated from raw_footer.
        self.footer_html = ''
        self.theme = None
        self.service_item_type = None
        self.unique_identifier = 0
        self.notes = ''
        self.from_plugin = False
        self.capabilities = []
        self.is_valid = True
        self.icon = None
        self.main = None
        self.footer = None
        self.bg_image_bytes = None
        self.search_string = ''
        self.data_string = ''
        self.edit_id = None
        self.xml_version = None
        self.start_time = 0
        self.end_time = 0
        self.media_length = 0
        self.from_service = False
        self.background_audio = []
        self.theme_overwritten = False
        self.temporary_edit = False
        self.auto_play_slides_once = False
        self.auto_play_slides_loop = False
        self.timed_slide_interval = 0
        self.will_auto_start = False
        self.has_original_file_path = True
        self.sha256_file_hash = None
        self.stored_filename = None
        self._new_item()
        self.metadata = []

    def get_theme_data(self, theme_level=None):
        """
        Get the theme appropriate for this item

        :param theme_level: The theme_level to use,
                            the value in Settings is used when this value is missinig
        """
        if theme_level is None:
            theme_level = self.settings.value('themes/theme level')
        theme_manager = Registry().get('theme_manager')
        # Just assume we use the global theme.
        theme = theme_manager.global_theme
        if theme_level != ThemeLevel.Global:
            service_theme = self.settings.value('servicemanager/service theme')
            # Service or Song level, so assume service theme (if it exists and item in service)
            # but use song theme if level is song (and it exists)
            if service_theme and self.from_service:
                theme = service_theme
        if self.is_capable(ItemCapabilities.ProvidesOwnTheme) or theme_level == ThemeLevel.Song and self.theme:
            theme = self.theme
        theme = theme_manager.get_theme_data(theme)
        # Clean up capabilities and reload from the theme.
        if self.is_text():
            # Cleanup capabilities
            if self.is_capable(ItemCapabilities.CanStream):
                self.remove_capability(ItemCapabilities.CanStream)
            if self.is_capable(ItemCapabilities.HasBackgroundVideo):
                self.remove_capability(ItemCapabilities.HasBackgroundVideo)
            if self.is_capable(ItemCapabilities.HasBackgroundStream):
                self.remove_capability(ItemCapabilities.HasBackgroundStream)
            # Reload capabilities
            if theme.background_type == BackgroundType.to_string(BackgroundType.Stream):
                self.add_capability(ItemCapabilities.HasBackgroundStream)
                self.stream_mrl = theme.background_filename
            if theme.background_type == BackgroundType.to_string(BackgroundType.Video):
                self.video_file_name = theme.background_filename
                self.add_capability(ItemCapabilities.HasBackgroundVideo)
        return theme

    def _new_item(self):
        """
        Method to set the internal id of the item. This is used to compare service items to see if they are the same.
        """
        self.unique_identifier = str(uuid.uuid1())
        self.validate_item()

    def add_capability(self, capability):
        """
        Add an ItemCapability to a ServiceItem

        :param capability: The capability to add
        """
        self.capabilities.append(capability)

    def remove_capability(self, capability):
        """
        Remove an ItemCapability from a ServiceItem

        :param capability: The capability to remove
        """
        self.capabilities.remove(capability)

    def is_capable(self, capability):
        """
        Tell the caller if a ServiceItem has a capability

        :param capability: The capability to test for
        """
        return capability in self.capabilities

    def add_icon(self):
        """
        Add an icon to the service item. This is used when displaying the service item in the service manager.
        """
        if self.name == 'songs':
            self.icon = UiIcons().music
        elif self.name == 'bibles':
            self.icon = UiIcons().bible
        elif self.name == 'presentations':
            self.icon = UiIcons().presentation
        elif self.name == 'images':
            self.icon = UiIcons().picture
        elif self.name == 'media':
            self.icon = UiIcons().video
        else:
            self.icon = UiIcons().custom

    def _create_slides(self):
        """
        Create frames for rendering and display
        """
        wait_for(lambda: not self._creating_slides)
        self._creating_slides = True
        self._rendered_slides = []
        self._display_slides = []

        start_time = time.perf_counter()
        format_time = 0.0
        # Save rendered pages to this dict. In the case that a slide is used twice we can use the pages saved to
        # the dict instead of rendering them again.
        previous_pages = {}
        index = 0
        if not self.footer_html:
            self.footer_html = '<br>'.join([_f for _f in self.raw_footer if _f])
        for raw_slide in self.slides:
            verse_tag = raw_slide['verse']
            if verse_tag in previous_pages and previous_pages[verse_tag][0] == raw_slide:
                pages = previous_pages[verse_tag][1]
            else:
                format_start_time = time.perf_counter()
                pages = self.renderer.format_slide(raw_slide['text'], self)
                format_time += time.perf_counter() - format_start_time
                previous_pages[verse_tag] = (raw_slide, pages)
            for page in pages:
                footer_html = None
                has_footer_html = 'footer_html' in raw_slide
                if has_footer_html:
                    footer_html = raw_slide['footer_html']
                else:
                    footer_html = self.footer_html
                rendered_slide = {
                    'title': raw_slide['title'],
                    'text': render_tags(page),
                    'chords': remove_tags(page),
                    'verse': index,
                    'footer': footer_html
                }
                self._rendered_slides.append(rendered_slide)
                display_slide = {
                    'title': raw_slide['title'],
                    'text': remove_html_and_strip(remove_tags(page, can_remove_chords=True)),
                    'verse': verse_tag,
                }
                self._display_slides.append(display_slide)
                index += 1
        log.debug('_create_slides timing for "%s" (%s): total %.1f ms, %.1f ms in format_slide, '
                  '%d raw slide(s) -> %d rendered slide(s)',
                  self.title, getattr(self, 'name', 'unknown'), (time.perf_counter() - start_time) * 1000,
                  format_time * 1000,
                  len(self.slides), len(self._rendered_slides))
        self._creating_slides = False

    def _clear_slides_cache(self):
        """
        Clears the internal representation/cache of slides (display_slides and rendered_slides).
        """
        self._display_slides = None
        self._rendered_slides = None

    @property
    def rendered_slides(self):
        """
        Render the frames and return them
        """
        wait_for(lambda: not self._creating_slides)
        if not self._rendered_slides:
            self._create_slides()
        return self._rendered_slides

    @property
    def display_slides(self):
        """
        Render the frames and return them
        """
        wait_for(lambda: not self._creating_slides)
        if not self._display_slides:
            self._create_slides()
        return self._display_slides

    @property
    def print_slides(self):
        """
        Render the frames for printing and return them

        """
        if not self._print_slides:
            self._print_slides = []
            previous_pages = {}
            index = 0
            for raw_slide in self.slides:
                verse_tag = raw_slide['verse']
                if verse_tag in previous_pages and previous_pages[verse_tag][0] == raw_slide:
                    pages = previous_pages[verse_tag][1]
                else:
                    pages = self.renderer.format_slide(raw_slide['text'], self)
                    previous_pages[verse_tag] = (raw_slide, pages)
                for page in pages:
                    slide = {
                        'title': raw_slide['title'],
                        'text': render_chords_for_printing(remove_tags(page), '\n'),
                        'verse': index,
                        'footer': self.raw_footer,
                    }
                    self._print_slides.append(slide)
        return self._print_slides

    def add_from_image(self, path, title, thumbnail=None, file_hash=None):
        """
        Add an image slide to the service item.

        :param path: The directory in which the image file is located.
        :param title: A title for the slide in the service item.
        :param thumbnail: Optional alternative thumbnail, used for remote thumbnails.
        :param file_hash: Unique Reference to file .
        """
        self.service_item_type = ServiceItemType.Image
        if not file_hash:
            file_hash = sha256_file_hash(path)
        slide = {'title': title, 'path': path, 'file_hash': file_hash}
        if thumbnail:
            slide['thumbnail'] = thumbnail
        self.slides.append(slide)
        self._new_item()

    def add_from_text(self, text, verse_tag=None, footer_html=None, metadata=None):
        """
        Add a text slide to the service item.

        :param text: The raw text of the slide.
        :param verse_tag:
        :param footer_html: Custom HTML footer for current slide
        :param metadata: Additional metadata to add to service item
        """
        slide = self._create_slide_from_text(text, verse_tag, footer_html, metadata)
        self.slides.append(slide)
        self._new_item()

    def replace_slide_from_text(self, index, text, verse_tag=None, footer_html=None, metadata=None):
        """
        Replace a text slide on the service item.

        :param index: The index of slide to replace
        :param text: The raw text of the slide.
        :param verse_tag:
        :param footer_html: Custom HTML footer for current slide
        :param metadata: Additional metadata to add to service item
        """
        slide = self._create_slide_from_text(text, verse_tag, footer_html, metadata)
        self.slides[index] = slide
        self._clear_slides_cache()

    def _create_slide_from_text(self, text, verse_tag=None, footer_html=None, metadata=None):
        """
        Creates a text slide.

        :param text: The raw text of the slide.
        :param verse_tag:
        :param footer_html: Custom HTML footer for current slide
        :param metadata: Additional metadata to add to service item
        """
        if verse_tag:
            verse_tag = verse_tag.upper()
        else:
            # For items that don't have a verse tag, autoincrement the slide numbers
            verse_tag = str(len(self.slides) + 1)
        self.service_item_type = ServiceItemType.Text
        title = text[:30].split('\n')[0]
        slide = {'title': title, 'text': text, 'verse': verse_tag}
        if footer_html is not None:
            slide['footer_html'] = footer_html
        if isinstance(metadata, dict):
            slide['metadata'] = metadata
        return slide

    def add_from_command(self, path, file_name, image, display_title=None, notes=None, file_hash=None):
        """
        Add a slide from a command.

        :param path: The title of the slide in the service item.
        :param file_name: The title of the slide in the service item.
        :param image: The command of/for the slide.
        :param display_title: Title to show in gui/webinterface, optional.
        :param notes: Notes to show in the webinteface, optional.
        :param file_hash: Sha256 hash checksum of the file.
        """
        self.service_item_type = ServiceItemType.Command
        # If the item should have a display title but this frame doesn't have one, we make one up
        if self.is_capable(ItemCapabilities.HasDisplayTitle) and not display_title:
            display_title = translate('OpenLP.ServiceItem',
                                      '[slide {frame:d}]').format(frame=len(self.slides) + 1)
        if self.uses_file():
            if file_hash:
                self.sha256_file_hash = file_hash
            else:
                file_location = Path(path) / file_name
                self.sha256_file_hash = sha256_file_hash(file_location)
            self.stored_filename = '{hash}{ext}'.format(hash=self.sha256_file_hash, ext=os.path.splitext(file_name)[1])
        # Update image path to match servicemanager location if file was loaded from service
        if image and self.name == 'presentations':
            image = AppLocation.get_section_data_path(self.name) / 'thumbnails' / self.sha256_file_hash / \
                ntpath.basename(image)
        self.slides.append({'title': file_name, 'image': image, 'path': path, 'display_title': display_title,
                            'notes': notes, 'thumbnail': image})
        self._new_item()

    def get_service_repr(self, lite_save):
        """
        This method returns some text which can be saved into the service file to represent this item.
        """
        if self.sha256_file_hash:
            stored_filename = '{hash}{ext}'.format(hash=self.sha256_file_hash, ext=os.path.splitext(self.title)[1])
        else:
            stored_filename = None
        service_header = {
            'name': self.name,
            'plugin': self.name,
            'theme': self.theme,
            'title': self.title,
            'footer': self.raw_footer,
            'type': self.service_item_type,
            'audit': self.audit,
            'notes': self.notes,
            'from_plugin': self.from_plugin,
            'capabilities': self.capabilities,
            'search': self.search_string,
            'data': self.data_string,
            'xml_version': self.xml_version,
            'auto_play_slides_once': self.auto_play_slides_once,
            'auto_play_slides_loop': self.auto_play_slides_loop,
            'timed_slide_interval': self.timed_slide_interval,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'media_length': self.media_length,
            'background_audio': [],
            'theme_overwritten': self.theme_overwritten,
            'will_auto_start': self.will_auto_start,
            'processor': self.processor,
            'metadata': self.metadata,
            'sha256_file_hash': self.sha256_file_hash,
            'stored_filename': stored_filename
        }
        for file_path, file_hash in self.background_audio:
            if lite_save:
                path_str = str(file_path)
            else:
                # a side-effect of this is that if the song is imported from the service created from this, the
                # background audio filename shown in the ui will be the file_hash + the suffix.
                path_str = '{hash}{suffix}'.format(hash=file_hash, suffix=file_path.suffix)
            service_header['background_audio'].append(path_str)
        service_data = []
        if self.service_item_type == ServiceItemType.Text:
            for slide in self.slides:
                data_slide = deepcopy(slide)
                data_slide['raw_slide'] = data_slide.pop('text')
                data_slide['verseTag'] = data_slide.pop('verse')
                service_data.append(data_slide)
        elif self.service_item_type == ServiceItemType.Image:
            if lite_save:
                for slide in self.slides:
                    # When saving a service that originated from openlp 2.4 thumbnail might not be available
                    if 'thumbnail' in slide:
                        image_path = slide['thumbnail']
                    else:
                        # Check if (by chance) the thumbnails for this image is available on this machine
                        test_thumb = AppLocation.get_section_data_path(self.name) / 'thumbnails' / stored_filename
                        if test_thumb.exists():
                            image_path = test_thumb
                        else:
                            image_path = None
                    service_data.append({'title': slide['title'], 'image': image_path, 'path': slide['path'],
                                         'file_hash': slide['file_hash']})
            else:
                for slide in self.slides:
                    # When saving a service that originated from openlp 2.4 thumbnail might not be available
                    # Also, sometimes this is not a Path object, but a string.
                    if 'thumbnail' in slide:
                        image_path = Path(slide['thumbnail']).relative_to(AppLocation().get_data_path())
                    else:
                        # Check if (by chance) the thumbnails for this image is available on this machine
                        test_thumb = AppLocation.get_section_data_path(self.name) / 'thumbnails' / stored_filename
                        if test_thumb.exists():
                            image_path = test_thumb
                        else:
                            image_path = None
                    service_data.append({'title': slide['title'], 'image': image_path, 'file_hash': slide['file_hash']})
        elif self.service_item_type == ServiceItemType.Command:
            for slide in self.slides:
                if isinstance(slide['image'], QtGui.QIcon):
                    image = 'clapperboard'
                elif lite_save:
                    image = slide['image']
                else:
                    # Sometimss this is not a Path object, so typecast it
                    image = Path(slide['image']).relative_to(AppLocation().get_data_path())
                service_data.append({'title': slide['title'], 'image': image, 'path': slide['path'],
                                     'display_title': slide['display_title'], 'notes': slide['notes']})
        return {'header': service_header, 'data': service_data}

    def render_text_items(self):
        """
        This method forces the display to be regenerated
        """
        self._display_slides = []
        self._rendered_slides = []

    def set_from_service(self, service_item, path=None, version=2):
        """
        This method takes a service item from a saved service file (passed from the ServiceManager) and extracts the
        data actually required.

        :param service_item: The item to extract data from.
        :param path: Defaults to *None*. This is the service manager path for things which have their files saved
            with them or None when the saved service is lite and the original file paths need to be preserved.
        :param version: Format version of the data.
        """
        log.debug('set_from_service called with path {path}'.format(path=path))
        header = service_item['serviceitem']['header']
        self.title = header['title']
        self.name = header['name']
        self.service_item_type = ServiceItemType.parse(header['type'])
        self.theme = header['theme']
        self.add_icon()
        self.raw_footer = header['footer']
        self.audit = header['audit']
        self.notes = header['notes']
        self.from_plugin = header['from_plugin']
        self.capabilities = header['capabilities']
        # Added later so may not be present in older services.
        self.search_string = header.get('search', '')
        self.data_string = header.get('data', '')
        self.xml_version = header.get('xml_version')
        self.start_time = header.get('start_time', 0)
        self.end_time = header.get('end_time', 0)
        self.media_length = header.get('media_length', 0)
        self.auto_play_slides_once = header.get('auto_play_slides_once', False)
        self.auto_play_slides_loop = header.get('auto_play_slides_loop', False)
        self.timed_slide_interval = header.get('timed_slide_interval', 0)
        self.will_auto_start = header.get('will_auto_start', False)
        self.processor = header.get('processor', None)
        self.has_original_file_path = True
        self.metadata = header.get('item_meta_data', [])
        self.sha256_file_hash = header.get('sha256_file_hash', None)
        self.stored_filename = header.get('stored_filename', None)
        if 'background_audio' in header and State().check_preconditions('media'):
            self.background_audio = []
            for file_str in header['background_audio']:
                file_path = Path(file_str)
                file_hash = None
                # In OpenLP 3.0 we switched to storing Path objects in JSON files
                if version >= 3:
                    if path:
                        file_path = path / file_path
                else:
                    # Handle service files prior to OpenLP 3.0
                    # Windows can handle both forward and backward slashes, so we use ntpath to get the basename
                    file_path = path / ntpath.basename(file_path)
                if not file_hash:
                    file_hash = sha256_file_hash(file_path)
                self.background_audio.append((file_path, file_hash))
        self.theme_overwritten = header.get('theme_overwritten', False)
        if self.service_item_type == ServiceItemType.Text:
            for slide in service_item['serviceitem']['data']:
                footer_html = slide['footer_html'] if 'footer_html' in slide else None
                metadata = slide['metadata'] if 'metadata' in slide and isinstance(slide['metadata'], dict) else None
                self.add_from_text(slide['raw_slide'], slide['verseTag'], footer_html, metadata)
            self._create_slides()
        elif self.service_item_type == ServiceItemType.Image:
            if path:
                self.has_original_file_path = False
                for text_image in service_item['serviceitem']['data']:
                    text = None
                    file_hash = None
                    thumbnail = None
                    if version >= 3:
                        text = text_image['title']
                        file_hash = text_image['file_hash']
                        file_path = path / '{base}{ext}'.format(base=file_hash, ext=os.path.splitext(text)[1])
                        if text_image['image']:
                            thumbnail = AppLocation.get_data_path() / text_image['image']
                            # copy thumbnail from servicemanager path
                            if thumbnail.exists():
                                copy(path / 'thumbnails' / os.path.basename(text_image['image']),
                                     AppLocation.get_section_data_path(self.name) / 'thumbnails')
                    else:
                        text = text_image
                        org_file_path = path / text
                        # rename the extracted file so that it follows the sha256 based approach of openlp 3
                        self.sha256_file_hash = sha256_file_hash(org_file_path)
                        new_file = '{hash}{ext}'.format(hash=self.sha256_file_hash, ext=os.path.splitext(text)[1])
                        file_path = path / new_file
                        move(org_file_path, file_path)
                        # Check if (by chance) the thumbnails for this image is available on this machine
                        test_thumb = AppLocation.get_section_data_path(self.name) / 'thumbnails' / new_file
                        if test_thumb.exists():
                            thumbnail = test_thumb
                    self.add_from_image(file_path, text, thumbnail=thumbnail, file_hash=file_hash)
            else:
                for text_image in service_item['serviceitem']['data']:
                    file_hash = None
                    text = text_image['title']
                    thumbnail = None
                    if version >= 3:
                        file_path = text_image['path']
                        file_hash = text_image['file_hash']
                        if text_image['image']:
                            thumbnail = AppLocation.get_data_path() / text_image['image']
                    else:
                        file_path = Path(text_image['path'])
                        # Check if (by chance) the thumbnails for this image is available on this machine
                        file_hash = sha256_file_hash(file_path)
                        new_file = '{hash}{ext}'.format(hash=file_hash, ext=os.path.splitext(file_path)[1])
                        test_thumb = AppLocation.get_section_data_path(self.name) / 'thumbnails' / new_file
                        if test_thumb.exists():
                            thumbnail = test_thumb
                    self.add_from_image(file_path, text, thumbnail=thumbnail, file_hash=file_hash)
        elif self.service_item_type == ServiceItemType.Command:
            if version < 3:
                # If this is an old servicefile with files included, we need to rename the bundled files to match
                # the new sha256 based scheme
                if path:
                    file_path = Path(path) / self.title
                    self.sha256_file_hash = sha256_file_hash(file_path)
                    new_file = path / '{hash}{ext}'.format(hash=self.sha256_file_hash,
                                                           ext=os.path.splitext(self.title)[1])
                    # while copying instead of moving can lead to longer load times for older files, if we move we
                    # cannot load service files with duplicated files.
                    copy(file_path, new_file)
                else:
                    file_path = Path(service_item['serviceitem']['data'][0]['path']) / self.title
                    self.sha256_file_hash = sha256_file_hash(file_path)
            # Loop over the slides
            for text_image in service_item['serviceitem']['data']:
                if not self.title:
                    self.title = text_image['title']
                if self.is_capable(ItemCapabilities.IsOptical) or self.is_capable(ItemCapabilities.CanStream):
                    self.has_original_file_path = False
                    self.add_from_command(text_image['path'], text_image['title'], text_image['image'])
                elif path:
                    self.has_original_file_path = False
                    # Copy any bundled thumbnails into the plugin thumbnail folder
                    if version >= 3 and os.path.exists(path / self.sha256_file_hash) and \
                            os.path.isdir(path / self.sha256_file_hash):
                        try:
                            copytree(path / self.sha256_file_hash,
                                     AppLocation.get_section_data_path(self.name) / 'thumbnails' /
                                     self.sha256_file_hash)
                        except FileExistsError:
                            # Files already exists, just skip
                            pass
                    if text_image['image'] in ['clapperboard', ':/media/slidecontroller_multimedia.png']:
                        image_path = UiIcons().clapperboard
                    elif version < 3:
                        # convert the thumbnail path to new sha256 based
                        new_file = '{hash}{ext}'.format(hash=self.sha256_file_hash,
                                                        ext=os.path.splitext(text_image['image'])[1])
                        image_path = AppLocation.get_section_data_path(self.name) / 'thumbnails' / \
                            self.sha256_file_hash / os.path.split(text_image['image'])[1]
                    else:
                        image_path = text_image['image']
                    self.add_from_command(path, text_image['title'], image_path, text_image.get('display_title', ''),
                                          text_image.get('notes', ''), file_hash=self.sha256_file_hash)
                else:
                    if text_image['image'] in ['clapperboard', ':/media/slidecontroller_multimedia.png']:
                        image_path = UiIcons().clapperboard
                    elif version < 3:
                        # convert the thumbnail path to new sha256 based
                        image_path = AppLocation.get_section_data_path(self.name) / 'thumbnails' / \
                            self.sha256_file_hash / os.path.split(text_image['image'])[1]
                    else:
                        image_path = text_image['image']
                    self.add_from_command(Path(text_image['path']), str(text_image['title']), image_path)
        self._new_item()

    def get_display_title(self):
        """
        Returns the title of the service item.
        """
        if self.is_text() or self.is_capable(ItemCapabilities.IsOptical) \
                or self.is_capable(ItemCapabilities.CanEditTitle):
            return self.title
        else:
            if len(self.slides) > 1:
                return self.title
            else:
                return self.slides[0]['title']

    def get_transition_delay(self):
        """
        Returns a approximate time in seconds for how long it will take to switch slides
        """
        delay = 1
        if self.is_capable(ItemCapabilities.ProvidesOwnDisplay):
            delay = 0.5
        else:
            theme = self.get_theme_data()
            transition_speed = theme.display_slide_transition_speed
            if theme.display_slide_transition is False or transition_speed == TransitionSpeed.Fast:
                delay = 0.5
            elif transition_speed == TransitionSpeed.Normal:
                delay = 1
            elif transition_speed == TransitionSpeed.Slow:
                delay = 2
        return delay

    def merge(self, other):
        """
        Updates the unique_identifier with the value from the original one
        The unique_identifier is unique for a given service item but this allows one to replace an original version.

        :param other: The service item to be merged with
        """
        self.unique_identifier = other.unique_identifier
        self.notes = other.notes
        self.temporary_edit = other.temporary_edit
        # Copy theme over if present.
        if other.theme is not None:
            self.theme = other.theme
            self._new_item()
        if self.is_capable(ItemCapabilities.HasBackgroundAudio):
            log.debug(self.background_audio)

    def __eq__(self, other):
        """
        Confirms the service items are for the same instance
        """
        if not other:
            return False
        return self.unique_identifier == other.unique_identifier

    def __ne__(self, other):
        """
        Confirms the service items are not for the same instance
        """
        return self.unique_identifier != other.unique_identifier

    def __hash__(self):
        """
        Return the hash for the service item.
        """
        return self.unique_identifier

    def is_media(self):
        """
        Confirms if the ServiceItem is media
        """
        return ItemCapabilities.RequiresMedia in self.capabilities

    def is_command(self):
        """
        Confirms if the ServiceItem is a command
        """
        return self.service_item_type == ServiceItemType.Command

    def is_image(self):
        """
        Confirms if the ServiceItem is an image
        """
        return self.service_item_type == ServiceItemType.Image

    def uses_file(self):
        """
        Confirms if the ServiceItem uses a file
        """
        return self.service_item_type == ServiceItemType.Image or \
            (self.service_item_type == ServiceItemType.Command and not self.is_capable(ItemCapabilities.IsOptical)
             and not self.is_capable(ItemCapabilities.CanStream))

    def is_text(self):
        """
        Confirms if the ServiceItem is text
        """
        return self.service_item_type == ServiceItemType.Text

    def set_media_length(self, length):
        """
        Stores the media length of the item

        :param length: The length of the media item
        """
        self.media_length = length
        if length > 0:
            self.add_capability(ItemCapabilities.HasVariableStartTime)

    def get_frames(self):
        """
        Returns the frames for the ServiceItem
        """
        if self.service_item_type == ServiceItemType.Text:
            return self.display_slides
        else:
            return self.slides

    def get_rendered_frame(self, row, clean=False):
        """
        Returns the correct frame for a given list and renders it if required.

        :param row: The service item slide to be returned
        :param clean: do I want HTML tags or not
        """
        if self.service_item_type == ServiceItemType.Text:
            if clean:
                return self.display_slides[row]['text']
            else:
                return self.rendered_slides[row]['text']
        elif self.service_item_type == ServiceItemType.Image:
            return self.slides[row]['path']
        else:
            return self.slides[row]['image']

    def get_frame_title(self, row=0):
        """
        Returns the title of the raw frame
        """
        try:
            return self.get_frames()[row]['title']
        except IndexError:
            return ''

    def get_frame_path(self, row=0, frame=None):
        """
        Returns the path of the raw frame
        """
        if not frame:
            try:
                frame = self.slides[row]
            except IndexError:
                return ''
        if self.is_image() or self.is_capable(ItemCapabilities.IsOptical):
            frame_path = Path(frame['path'])
        elif self.is_command() and not self.has_original_file_path and self.sha256_file_hash:
            frame_path = Path(frame['path']) / self.stored_filename
        else:
            frame_path = Path(frame['path']) / frame['title']
        return frame_path

    def remove_frame(self, frame):
        """
        Remove the specified frame from the item
        """
        if frame in self.slides:
            self.slides.remove(frame)

    def get_media_time(self):
        """
        Returns the start and finish time for a media item
        """
        start = None
        end = None
        if self.start_time != 0:
            time = str(datetime.timedelta(seconds=self.start_time))
            start = translate('OpenLP.ServiceItem',
                              '<strong>Start</strong>: {start}').format(start=time)
        if self.media_length != 0:
            length = str(datetime.timedelta(seconds=self.media_length // 1000))
            end = translate('OpenLP.ServiceItem', '<strong>Length</strong>: {length}').format(length=length)

        if not start and not end:
            return ''
        elif start and not end:
            return start
        elif not start and end:
            return end
        else:
            return '{start} <br>{end}'.format(start=start, end=end)

    def update_theme(self, theme):
        """
        updates the theme in the service item

        :param theme: The new theme to be replaced in the service item
        """
        self.theme_overwritten = (theme is None)
        self.theme = theme
        if self.is_text():
            self._clear_slides_cache()
        self._new_item()

    def remove_invalid_frames(self, invalid_paths=None):
        """
        Remove invalid frames, such as ones where the file no longer exists.
        """
        if self.uses_file():
            for frame in self.get_frames():
                if self.get_frame_path(frame=frame) in invalid_paths:
                    self.remove_frame(frame)

    def requires_media(self):
        return self.is_capable(ItemCapabilities.HasBackgroundAudio) or \
            self.is_capable(ItemCapabilities.HasBackgroundVideo) or \
            self.is_capable(ItemCapabilities.HasBackgroundStream)

    def missing_frames(self):
        """
        Returns if there are any frames in the service item
        """
        return not bool(self.slides)

    def validate_item(self, suffixes=None):
        """
        Validates a service item to make sure it is valid

        """
        self.is_valid = True
        for slide in self.slides:
            if self.is_image() and not os.path.exists(slide['path']):
                self.is_valid = False
                break
            elif self.is_command():
                # Needs Media but no media processing available.
                if self.is_capable(ItemCapabilities.RequiresMedia) and not State().check_preconditions('media'):
                    self.is_valid = False
                    break
                elif self.is_capable(ItemCapabilities.HasBackgroundAudio) and not State().check_preconditions('media'):
                    self.is_valid = False
                    break
                # is not sup[ported but can arrive in old service file
                # TODO remove in 4.1
                elif self.is_capable(ItemCapabilities.IsOptical):
                    self.is_valid = False
                    break
                elif self.is_capable(ItemCapabilities.CanStream):
                    (_, name, mrl, options) = parse_stream_path(slide['path'])
                    if not name or not mrl or not options:
                        self.is_valid = False
                        break
                else:
                    if self.has_original_file_path:
                        file_name = Path(slide['path']) / slide['title']
                    else:
                        file_name = Path(slide['path']) / self.stored_filename
                    if not file_name.exists():
                        self.is_valid = False
                        break
                    if suffixes and not self.is_text():
                        file_suffix = "{suffx}".format(suffx=slide['title'].split('.')[-1])
                        if file_suffix.lower() not in suffixes:
                            self.is_valid = False
                            break

    def get_thumbnail_path(self):
        """
        Returns the thumbnail folder. Should only be used for items that support thumbnails.
        """
        if self.is_capable(ItemCapabilities.HasThumbnails):
            if self.is_command() and self.slides:
                return os.path.dirname(self.slides[0]['image'])
            elif self.is_image() and self.slides and 'thumbnail' in self.slides[0]:
                return os.path.dirname(self.slides[0]['thumbnail'])
        return None

    def to_dict(self, active=False, item_no=0):
        """
        Convert the service item into a dictionary
        Images and thumbnails are put in dict as data uri strings.

        :param boolean active: Do I filter list for only the active item
        :param int item_no: the index of the active item
        """
        data_dict = {
            'title': self.title,
            'name': self.name,
            'type': self.service_item_type,
            'theme': self.theme,
            'footer': self.raw_footer,
            'audit': self.audit,
            'notes': self.notes,
            'data': self.data_string or {},
            'fromPlugin': self.from_plugin,
            'capabilities': self.capabilities,
            'backgroundAudio': self.background_audio,
            'isThemeOverwritten': self.theme_overwritten,
            'slides': []
        }
        for index, frame in enumerate(self.get_frames()):
            if active and index is not item_no:
                continue
            else:
                item = {
                    'tag': index + 1,
                    'title': self.title,
                    'selected': False
                }
                if self.is_text():
                    if frame['verse']:
                        item['tag'] = str(frame['verse'])
                    item['text'] = frame['text']
                    item['html'] = self.rendered_slides[index]['text']
                    item['chords'] = self.rendered_slides[index]['chords']
                    item['footer'] = self.rendered_slides[index]['footer']
                elif self.is_image() and not frame.get('image', '') and \
                        Registry().get('settings_thread').value('api/thumbnails') and \
                        self.is_capable(ItemCapabilities.HasThumbnails):
                    thumbnail_path = frame['thumbnail']
                    if not thumbnail_path.exists():
                        create_thumb(Path(self.get_frame_path(index)), thumbnail_path, False)
                    item['img'] = image_to_data_uri(thumbnail_path)
                    item['text'] = str(frame['title'])
                    item['html'] = str(frame['title'])
                else:
                    # presentations and other things
                    if self.is_capable(ItemCapabilities.HasDisplayTitle):
                        item['title'] = str(frame['display_title'])
                    if self.is_capable(ItemCapabilities.HasNotes):
                        item['slide_notes'] = str(frame['notes'])
                    if self.is_capable(ItemCapabilities.HasThumbnails) and \
                            Registry().get('settings_thread').value('api/thumbnails'):
                        # If the file is under our app directory tree send the portion after the match
                        data_path = str(AppLocation.get_data_path())
                        try:
                            relative_file = frame['image'].relative_to(data_path)
                        except ValueError:
                            log.warning('Service item "{title}" is missing a thumbnail or has an invalid thumbnail path'
                                        .format(title=self.title))
                        else:
                            item['img'] = image_to_data_uri(AppLocation.get_data_path() / relative_file)
                    item['text'] = str(frame['title'])
                    item['html'] = str(frame['title'])
                data_dict['slides'].append(item)
        return data_dict
