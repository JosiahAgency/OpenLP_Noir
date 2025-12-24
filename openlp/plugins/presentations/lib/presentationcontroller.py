# -*- coding: utf-8 -*-

##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2008-2024 OpenLP Developers                              #
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
import logging
import shutil
from pathlib import Path

from PyQt5 import QtCore

from openlp.core.common import Singleton, md5_hash, sha256_file_hash
from openlp.core.common.applocation import AppLocation
from openlp.core.common.path import create_paths
from openlp.core.common.registry import Registry
from openlp.core.lib import create_thumb


log = logging.getLogger(__name__)


class PresentationDocument(object):
    """
    Base class for presentation documents to inherit from. Loads and closes the presentation as well as triggering the
    correct activities based on the users input

    **Hook Functions**

    ``load_presentation()``
        Load a presentation file

    ``close_presentation()``
        Close presentation and clean up objects

    ``presentation_loaded()``
        Returns True if presentation is currently loaded

    ``is_active()``
        Returns True if a presentation is currently running

    ``blank_screen()``
        Blanks the screen, making it black.

    ``unblank_screen()``
        Unblanks the screen, restoring the output

    ``is_blank``
        Returns true if screen is blank

    ``stop_presentation()``
        Stops the presentation, removing it from the output display

    ``start_presentation()``
        Starts the presentation from the beginning

    ``get_slide_number()``
        Returns the current slide number, from 1

    ``get_slide_count()``
        Returns total number of slides

    ``goto_slide(slide_no)``
        Jumps directly to the requested slide.

    ``next_step()``
       Triggers the next effect of slide on the running presentation

    ``previous_step()``
        Triggers the previous slide on the running presentation

    ``get_thumbnail_path(slide_no, check_exists)``
        Returns a path to an image containing a preview for the requested slide

    ``attempt_screenshot()``
        Attemps to take a screenshot from the presentation window. Returns a tuple with whether it succedded and
        the result image.

    """
    def __init__(self, controller, document_path):
        """
        Constructor for the PresentationController class

        :param controller:
        :param Path document_path: Path to the document to load.
        :rtype: None
        """
        self.controller = controller
        self._sha256_file_hash = None
        self.settings = Registry().get('settings')
        self._setup(document_path)

    def _setup(self, document_path):
        """
        Run some initial setup. This method is separate from __init__ in order to mock it out in tests.

        :param Path document_path: Path to the document to load.
        :rtype: None
        """
        self.slide_number = 0
        self.ui_slidenumber = 0
        self.file_path = document_path
        create_paths(self.get_thumbnail_folder())

    def load_presentation(self):
        """
        Called when a presentation is added to the SlideController. Loads the
        presentation and starts it.

        Returns False if the file could not be opened
        """
        return False

    def presentation_deleted(self):
        """
        Cleans up/deletes any controller specific files created for
        a file, e.g. thumbnails
        """
        try:
            thumbnail_folder_path = self.get_thumbnail_folder()
            temp_folder_path = self.get_temp_folder()
            if thumbnail_folder_path.exists():
                shutil.rmtree(thumbnail_folder_path)
            if temp_folder_path.exists():
                shutil.rmtree(temp_folder_path)
        except OSError:
            log.exception('Failed to delete presentation controller files')

    def get_thumbnail_folder(self):
        """
        The location where thumbnail images will be stored

        :return: The path to the thumbnail
        :rtype: Path
        """
        # TODO: Can be removed when the upgrade path to OpenLP 3.0 is no longer needed, also ensure code in
        #       get_temp_folder and PresentationPluginapp_startup is removed
        if self.settings.value('presentations/thumbnail_scheme') == 'md5':
            folder = md5_hash(bytes(self.file_path))
        elif self.settings.value('presentations/thumbnail_scheme') == 'sha256file':
            if self._sha256_file_hash:
                folder = self._sha256_file_hash
            else:
                self._sha256_file_hash = sha256_file_hash(self.file_path)
                # If the sha256_file_hash() function encounters an error, it will return None, so use the
                # filename as the thumbnail folder if the result is None (or falsey).
                folder = self._sha256_file_hash or self.file_path.name
        else:
            folder = self.file_path.name
        return Path(self.controller.thumbnail_folder, folder)

    def get_temp_folder(self):
        """
        The location where thumbnail images will be stored

        :return: The path to the temporary file folder
        :rtype: Path
        """
        # TODO: Can be removed when the upgrade path to OpenLP 3.0 is no longer needed, also ensure code in
        #       get_thumbnail_folder and PresentationPluginapp_startup is removed
        if self.settings.value('presentations/thumbnail_scheme') == 'md5':
            folder = md5_hash(bytes(self.file_path))
        elif self.settings.value('presentations/thumbnail_scheme') == 'sha256file':
            if self._sha256_file_hash:
                folder = self._sha256_file_hash
            else:
                self._sha256_file_hash = sha256_file_hash(self.file_path)
                # If the sha256_file_hash() function encounters an error, it will return None, so use the
                # filename as the temp folder if the result is None (or falsey).
                folder = self._sha256_file_hash or self.file_path.name
        else:
            folder = self.file_path.name
        return Path(self.controller.temp_folder, folder)

    def check_thumbnails(self):
        """
        Check that the last thumbnail image exists and is valid. It is not checked if presentation file is newer than
        thumbnail since the path is based on the file hash, so if it exists it is by definition up to date.

        :return: If the thumbnail is valid
        :rtype: bool
        """
        last_image_path = self.get_thumbnail_path(self.get_slide_count(), True)
        if not (last_image_path and last_image_path.is_file()):
            return False
        return True

    def close_presentation(self):
        """
        Close presentation and clean up objects. Triggered by new object being added to SlideController
        """
        self.controller.close_presentation()

    def is_active(self):
        """
        Returns True if a presentation is currently running
        """
        return False

    def is_loaded(self):
        """
        Returns true if a presentation is loaded
        """
        return False

    def blank_screen(self):
        """
        Blanks the screen, making it black.
        """
        pass

    def unblank_screen(self):
        """
        Unblanks (restores) the presentation
        """
        pass

    def is_blank(self):
        """
        Returns true if screen is blank
        """
        return False

    def stop_presentation(self):
        """
        Stops the presentation, removing it from the output display
        """
        pass

    def start_presentation(self):
        """
        Starts the presentation from the beginning
        """
        pass

    def get_slide_number(self):
        """
        Returns the current slide number, from 1
        """
        return 0

    def get_slide_count(self):
        """
        Returns total number of slides
        """
        return 0

    def goto_slide(self, slide_no):
        """
        Jumps directly to the requested slide.

        :param slide_no: The slide to jump to, starting at 1
        """
        pass

    def next_step(self):
        """
        Triggers the next effect of slide on the running presentation. This might be the next animation on the current
        slide, or the next slide.
        :rtype bool: True if we stepped beyond the slides of the presentation
        """
        return False

    def previous_step(self):
        """
        Triggers the previous slide on the running presentation
        :rtype bool: True if we stepped beyond the slides of the presentation
        """
        return False

    def convert_thumbnail(self, image_path, index):
        """
        Convert the slide image the application made to a scaled 360px height .png image.

        :param Path image_path: Path to the image to create a thumbnail of
        :param int index: The index of the slide to create the thumbnail for.
        :rtype: None
        """
        if self.check_thumbnails():
            return
        if image_path.is_file():
            thumb_path = self.get_thumbnail_path(index, False)
            create_thumb(image_path, thumb_path, False, QtCore.QSize(-1, 360))

    def get_thumbnail_path(self, slide_no, check_exists=False):
        """
        Returns an image path containing a preview for the requested slide

        :param int slide_no: The slide an image is required for, starting at 1
        :param bool check_exists: Check if the generated path exists
        :return: The path, or None if the :param:`check_exists` is True and the file does not exist
        :rtype: Path | None
        """
        path = self.get_thumbnail_folder() / (self.controller.thumbnail_prefix + str(slide_no) + '.png')
        if path.is_file() or not check_exists:
            return path
        else:
            return None

    def poll_slidenumber(self, is_live, hide_mode):
        """
        Check the current slide number
        """
        if not self.is_active():
            return
        if not hide_mode:
            current = self.get_slide_number()
            if current == self.slide_number:
                # if the latest reported slide number is the same as the current, return here and skip sending an update
                return
            self.slide_number = current
        else:
            # when in blank mode the slide selected in the live slidecontroller overrules the slide
            # currently selected in the blanked presentation.
            if self.slide_number == self.ui_slidenumber:
                # if the latest reported slide number is the same as the current, return here and skip sending an update
                return
            self.slide_number = self.ui_slidenumber
        if is_live:
            prefix = 'live'
        else:
            prefix = 'preview'
        Registry().execute(f'slidecontroller_{prefix}_change', int(self.slide_number) - 1)

    def get_slide_text(self, slide_no):
        """
        Returns the text on the slide

        :param slide_no: The slide the text is required for, starting at 1
        """
        return ''

    def get_slide_notes(self, slide_no):
        """
        Returns the text on the slide

        :param slide_no: The slide the text is required for, starting at 1
        """
        return ''

    def get_titles_and_notes(self):
        """
        Reads the titles from the titles file and
        the notes files and returns the content in two lists
        """
        notes = []
        titles_path = self.get_thumbnail_folder() / 'titles.txt'
        try:
            titles = titles_path.read_text().splitlines()
        except Exception:
            log.exception('Failed to open/read existing titles file')
            titles = []
        for slide_no, title in enumerate(titles, 1):
            notes_path = self.get_thumbnail_folder() / 'slideNotes{number:d}.txt'.format(number=slide_no)
            try:
                note = notes_path.read_text()
            except Exception:
                log.exception('Failed to open/read notes file')
                note = ''
            notes.append(note)
        return titles, notes

    def save_titles_and_notes(self, titles, notes):
        """
        Performs the actual persisting of titles to the titles.txt and notes to the slideNote%.txt

        :param list[str] titles: The titles to save
        :param list[str] notes: The notes to save
        :rtype: None
        """
        if titles:
            titles_path = self.get_thumbnail_folder() / 'titles.txt'
            titles_path.write_text('\n'.join(titles), encoding='utf-8')
        if notes:
            for slide_no, note in enumerate(notes, 1):
                notes_path = self.get_thumbnail_folder() / 'slideNotes{number:d}.txt'.format(number=slide_no)
                notes_path.write_text(note, encoding='utf-8')

    def get_sha256_file_hash(self):
        """
        Returns the sha256 file hash for the file.

        :return: The sha256 file hash
        :rtype: str
        """
        if not self._sha256_file_hash:
            self._sha256_file_hash = sha256_file_hash(self.file_path)
        return self._sha256_file_hash

    def attempt_screenshot(self, index):
        return (False, None)


class PresentationList(metaclass=Singleton):
    """
    This is a singleton class which maintains a list of instances for presentations
    which have been started.
    The document load_presentation() method is called several times - for example, when the
    presentation files are being loaded into the library - but a document is included in this
    PresentationList only when the presentation is actually displayed.
    In this case the loading is initiated by a Registry 'presentation_start' event, the message
    includes the service item, and the unique_identifier from the service item is used as the id
    to differentiate the presentation document instances within this PresentationList.
    The purpose of this is so that the 'presentation_stop' event, which also includes the service
    item and its unique identifier, can result in the correct presentation being stopped.
    This fixes issue #700
    """

    def __init__(self):
        self._presentations = {}

    def add(self, document, unique_id):
        self._presentations[unique_id] = document

    def remove(self, unique_id):
        del self._presentations[unique_id]

    def get_presentation_by_id(self, unique_id):
        if unique_id in self._presentations:
            return self._presentations[unique_id]
        else:
            return None


class PresentationController(object):
    """
    This class is used to control interactions with presentation applications by creating a runtime environment.
    This is a base class for presentation controllers to inherit from.

    To create a new controller, take a copy of this file and name it so it ends with ``controller.py``, i.e.
    ``foobarcontroller.py``. Make sure it inherits
    :class:`~openlp.plugins.presentations.lib.presentationcontroller.PresentationController`, and then fill in the
    blanks. If possible try to make sure it loads on all platforms, usually by using :mod:``os.name`` checks, although
    ``__init__``, ``check_available`` and ``presentation_deleted`` should always be implemented.

    See :class:`~openlp.plugins.presentations.lib.impresscontroller.ImpressController`,
    :class:`~openlp.plugins.presentations.lib.powerpointcontroller.PowerpointController` or
    :class:`~openlp.plugins.presentations.lib.pptviewcontroller.PptviewController`
    for examples.

    **Basic Attributes**

    ``name``
        The name that appears in the options and the media manager.

    ``enabled``
        The controller is enabled.

    ``available``
        The controller is available on this machine. Set by init via call to check_available.

    ``plugin``
        The presentationplugin object.

    ``supports``
        The primary native file types this application supports.

    ``also_supports``
        Other file types the application can import, although not necessarily the first choice due to potential
        incompatibilities.

    **Hook Functions**

    ``kill()``
        Called at system exit to clean up any running presentations.

    ``check_available()``
        Returns True if presentation application is installed/can run on this machine.

    ``presentation_deleted()``
        Deletes presentation specific files, e.g. thumbnails.

    """
    log.info('PresentationController loaded')

    def __init__(self, plugin=None, name='PresentationController', document_class=PresentationDocument,
                 display_name=None):
        """
        This is the constructor for the presentationcontroller object. This provides an easy way for descendent plugins

        to populate common data. This method *must* be overridden, like so::

            class MyPresentationController(PresentationController):
                def __init__(self, plugin):
                    PresentationController.__init(
                        self, plugin, 'My Presenter App')

        :param plugin:  Defaults to *None*. The presentationplugin object
        :param name: Name of the application, to appear in the application
        :param document_class:
        """
        self.supports = []
        self.also_supports = []
        self.docs = []
        self.plugin = plugin
        self.name = name
        self.display_name = display_name if display_name is not None else name
        self.document_class = document_class

        self.available = None
        self.temp_folder = AppLocation.get_section_data_path('presentations') / name
        self.thumbnail_folder = AppLocation.get_section_data_path('presentations') / 'thumbnails'
        self.thumbnail_prefix = 'slide'
        create_paths(self.thumbnail_folder, self.temp_folder)

    def enabled(self):
        """
        Return whether the controller is currently enabled
        """
        if Registry().get('settings').value('presentations/' + self.name) == QtCore.Qt.Checked:
            return self.is_available()
        else:
            return False

    def is_available(self):
        if self.available is None:
            self.available = self.check_available()
        return self.available

    def check_available(self):
        """
        Presentation app is able to run on this machine.
        """
        return False

    def start_process(self):
        """
        Loads a running version of the presentation application in the background.
        """
        pass

    def kill(self):
        """
        Called at system exit to clean up any running presentations and close the application.
        """
        log.debug('Kill')
        self.close_presentation()

    def add_document(self, document_path):
        """
        Called when a new presentation document is opened.

        :param Path document_path: Path to the document to load
        :return: The document
        :rtype: PresentationDocument
        """
        document = self.document_class(self, document_path)
        self.docs.append(document)
        return document

    def remove_doc(self, doc=None):
        """
        Called to remove an open document from the collection.
        """
        log.debug('remove_doc Presentation')
        if doc is None:
            return
        if doc in self.docs:
            self.docs.remove(doc)

    def close_presentation(self):
        pass


class TextType(object):
    """
    Type Enumeration for Types of Text to request
    """
    Title = 0
    SlideText = 1
    Notes = 2
