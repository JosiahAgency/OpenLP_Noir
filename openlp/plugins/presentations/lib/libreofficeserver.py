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
This module runs a Pyro5 server using LibreOffice's version of Python

Please Note: This intentionally uses os.path over pathlib because we don't know which version of Python is shipped with
the version of LibreOffice on the user's computer.
"""
from subprocess import Popen
import sys
import os
import logging
import time


if sys.platform.startswith('darwin') and 'pytest' not in sys.argv[0]:
    # Only make the log file on OS X when running as a server
    logfile = os.path.join(str(os.getenv('HOME')), 'Library', 'Application Support', 'openlp', 'libreofficeserver.log')
    print('Setting up log file: {logfile}'.format(logfile=logfile))
    logging.basicConfig(filename=logfile, level=logging.INFO)


# Add the current directory to sys.path so that we can load the serializers
sys.path.append(os.path.join(os.path.dirname(__file__)))
# Add the vendor directory to sys.path so that we can load Pyro5
sys.path.append(os.path.join(os.path.dirname(__file__), 'vendor'))

from serializers import register_classes  # noqa: E402
from Pyro5.api import Daemon, expose  # noqa:E402

try:
    # Wrap these imports in a try so that we can run the tests on macOS
    import uno
    from com.sun.star.beans import PropertyValue
    from com.sun.star.task import ErrorCodeIOException
except ImportError:
    # But they need to be defined for mocking
    uno = None
    PropertyValue = None
    ErrorCodeIOException = Exception


log = logging.getLogger(__name__)
register_classes()


class TextType(object):
    """
    Type Enumeration for Types of Text to request
    """
    Title = 0
    SlideText = 1
    Notes = 2


@expose
class LibreOfficeServer(object):
    """
    A Pyro5 server which controls LibreOffice
    """
    def __init__(self):
        """
        Set up the server
        """
        self._desktop = None
        self._control = None
        self._document = None
        self._presentation = None
        self._process = None
        self._manager = None

    def _create_property(self, name, value):
        """
        Create an OOo style property object which are passed into some Uno methods.
        """
        log.debug('create property')
        property_object = PropertyValue()
        property_object.Name = name
        property_object.Value = value
        return property_object

    def _get_text_from_page(self, slide_no, text_type=TextType.SlideText):
        """
        Return any text extracted from the presentation page.

        :param slide_no: The slide the notes are required for, starting at 1
        :param notes: A boolean. If set the method searches the notes of the slide.
        :param text_type: A TextType. Enumeration of the types of supported text.
        """
        text = ''
        if TextType.Title <= text_type <= TextType.Notes:
            pages = self._document.getDrawPages()
            if 0 < slide_no <= pages.getCount():
                page = pages.getByIndex(slide_no - 1)
                if text_type == TextType.Notes:
                    page = page.getNotesPage()
                for index in range(page.getCount()):
                    shape = page.getByIndex(index)
                    shape_type = shape.getShapeType()
                    if shape.supportsService('com.sun.star.drawing.Text'):
                        # if they requested title, make sure it is the title
                        if text_type != TextType.Title or shape_type == 'com.sun.star.presentation.TitleTextShape':
                            text += shape.getString() + '\n'
        return text

    def start_process(self):
        """
        Initialise Impress
        """
        uno_command = [
            '/Applications/LibreOffice.app/Contents/MacOS/soffice',
            '--nologo',
            '--norestore',
            '--minimized',
            '--nodefault',
            '--nofirststartwizard',
            '--accept=pipe,name=openlp_maclo;urp;StarOffice.ServiceManager'
        ]
        self._process = Popen(uno_command)

    @property
    def desktop(self):
        """
        Set up an UNO desktop instance
        """
        if self._desktop is not None:
            return self._desktop
        uno_instance = None
        context = uno.getComponentContext()
        resolver = context.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver', context)
        loop = 0
        while uno_instance is None and loop < 3:
            try:
                uno_instance = resolver.resolve('uno:pipe,name=openlp_maclo;urp;StarOffice.ComponentContext')
            except Exception:
                log.exception('Unable to find running instance, retrying...')
                loop += 1
        try:
            self._manager = uno_instance.ServiceManager
            log.debug('get UNO Desktop Openoffice - createInstanceWithContext - Desktop')
            desktop = self._manager.createInstanceWithContext('com.sun.star.frame.Desktop', uno_instance)
            if not desktop:
                raise Exception('Failed to get UNO desktop')
            self._desktop = desktop
            return desktop
        except Exception:
            log.exception('Failed to get UNO desktop')
        return None

    def shutdown(self):
        """
        Shut down the server
        """
        can_kill = True
        if hasattr(self, '_docs'):
            while self._docs:
                self._docs[0].close_presentation()
        if self.desktop:
            docs = self.desktop.getComponents()
            count = 0
            if docs.hasElements():
                list_elements = docs.createEnumeration()
                while list_elements.hasMoreElements():
                    doc = list_elements.nextElement()
                    if doc.getImplementationName() != 'com.sun.star.comp.framework.BackingComp':
                        count += 1
            if count > 0:
                log.debug('LibreOffice not terminated as docs are still open')
                can_kill = False
            else:
                try:
                    self.desktop.terminate()
                    log.debug('LibreOffice killed')
                except Exception:
                    log.exception('Failed to terminate LibreOffice')
        if getattr(self, '_process') and can_kill:
            self._process.kill()

    def load_presentation(self, file_path, screen_number):
        """
        Load a presentation
        """
        self._file_path = file_path
        url = uno.systemPathToFileUrl(file_path)
        properties = (self._create_property('Hidden', True),)
        self._document = None
        loop_count = 0
        while loop_count < 3:
            try:
                self._document = self.desktop.loadComponentFromURL(url, '_blank', 0, properties)
            except Exception:
                log.exception('Failed to load presentation {url}'.format(url=url))
            if self._document:
                break
            time.sleep(0.5)
            loop_count += 1
        if loop_count == 3:
            log.error('Looped too many times')
            return False
        self._presentation = self._document.getPresentation()
        self._presentation.Display = screen_number
        self._control = None
        return True

    def extract_thumbnails(self, temp_folder):
        """
        Create thumbnails for the presentation
        """
        thumbnails = []
        thumb_dir_url = uno.systemPathToFileUrl(temp_folder)
        properties = (self._create_property('FilterName', 'impress_png_Export'),)
        pages = self._document.getDrawPages()
        if not pages:
            return []
        if not os.path.isdir(temp_folder):
            os.makedirs(temp_folder)
        for index in range(pages.getCount()):
            page = pages.getByIndex(index)
            self._document.getCurrentController().setCurrentPage(page)
            url_path = '{path}/{name}.png'.format(path=thumb_dir_url, name=str(index + 1))
            path = os.path.join(temp_folder, str(index + 1) + '.png')
            try:
                self._document.storeToURL(url_path, properties)
                thumbnails.append(path)
            except ErrorCodeIOException as exception:
                log.exception('ERROR! ErrorCodeIOException {error:d}'.format(error=exception.ErrCode))
            except Exception:
                log.exception('{path} - Unable to store openoffice preview'.format(path=path))
        return thumbnails

    def get_titles_and_notes(self):
        """
        Extract the titles and the notes from the slides.
        """
        titles = []
        notes = []
        pages = self._document.getDrawPages()
        for slide_no in range(1, pages.getCount() + 1):
            titles.append(self._get_text_from_page(slide_no, TextType.Title).replace('\n', ' ') + '\n')
            note = self._get_text_from_page(slide_no, TextType.Notes)
            if len(note) == 0:
                note = ' '
            notes.append(note)
        return titles, notes

    def close_presentation(self):
        """
        Close presentation and clean up objects.
        """
        log.debug('close Presentation LibreOffice')
        if self._document:
            if self._presentation:
                try:
                    self._presentation.end()
                    self._presentation = None
                    self._document.dispose()
                except Exception:
                    log.exception("Closing presentation failed")
            self._document = None

    def is_loaded(self):
        """
        Returns true if a presentation is loaded.
        """
        log.debug('is loaded LibreOffice')
        if self._presentation is None or self._document is None:
            log.debug("is_loaded: no presentation or document")
            return False
        try:
            if self._document.getPresentation() is None:
                log.debug("getPresentation failed to find a presentation")
                return False
        except Exception:
            log.exception("getPresentation failed to find a presentation")
            return False
        return True

    def is_active(self):
        """
        Returns true if a presentation is active and running.
        """
        log.debug('is active LibreOffice')
        if not self.is_loaded():
            return False
        return self._control.isRunning() if self._control else False

    def unblank_screen(self):
        """
        Unblanks the screen.
        """
        log.debug('unblank screen LibreOffice')
        return self._control.resume()

    def blank_screen(self):
        """
        Blanks the screen.
        """
        log.debug('blank screen LibreOffice')
        self._control.blankScreen(0)

    def is_blank(self):
        """
        Returns true if screen is blank.
        """
        log.debug('is blank LibreOffice')
        if self._control and self._control.isRunning():
            return self._control.isPaused()
        else:
            return False

    def stop_presentation(self):
        """
        Stop the presentation, remove from screen.
        """
        log.debug('stop presentation LibreOffice')
        self._presentation.end()
        self._control = None

    def start_presentation(self):
        """
        Start the presentation from the beginning.
        """
        log.debug('start presentation LibreOffice')
        if self._control is None or not self._control.isRunning():
            window = self._document.getCurrentController().getFrame().getContainerWindow()
            window.setVisible(True)
            self._presentation.start()
            self._control = self._presentation.getController()
            # start() returns before the Component is ready. Try for 15 seconds.
            sleep_count = 1
            while not self._control and sleep_count < 150:
                time.sleep(0.1)
                sleep_count += 1
                self._control = self._presentation.getController()
            window.setVisible(False)
        else:
            self._control.activate()
            self.goto_slide(1)

    def get_slide_number(self):
        """
        Return the current slide number on the screen, from 1.
        """
        return self._control.getCurrentSlideIndex() + 1

    def get_slide_count(self):
        """
        Return the total number of slides.
        """
        return self._document.getDrawPages().getCount()

    def goto_slide(self, slide_no):
        """
        Go to a specific slide (from 1).

        :param slide_no: The slide the text is required for, starting at 1
        """
        self._control.gotoSlideIndex(slide_no - 1)

    def next_step(self):
        """
        Triggers the next effect of slide on the running presentation.
        """
        is_paused = self._control.isPaused()
        self._control.gotoNextEffect()
        time.sleep(0.1)
        if not is_paused and self._control.isPaused():
            self._control.gotoPreviousEffect()

    def previous_step(self):
        """
        Triggers the previous slide on the running presentation.
        """
        self._control.gotoPreviousEffect()

    def get_slide_text(self, slide_no):
        """
        Returns the text on the slide.

        :param slide_no: The slide the text is required for, starting at 1
        """
        return self._get_text_from_page(slide_no)

    def get_slide_notes(self, slide_no):
        """
        Returns the text in the slide notes.

        :param slide_no: The slide the notes are required for, starting at 1
        """
        return self._get_text_from_page(slide_no, TextType.Notes)


def main():
    """
    The main function which runs the server
    """
    daemon = Daemon(host='localhost', port=4310)
    daemon.register(LibreOfficeServer, 'openlp.libreofficeserver')
    try:
        daemon.requestLoop()
    finally:
        daemon.close()


if __name__ == '__main__':
    main()
