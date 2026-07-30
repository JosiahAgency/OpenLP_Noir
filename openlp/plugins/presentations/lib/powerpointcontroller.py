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
This module is for controlling powerpoint. PPT API documentation:
`http://msdn.microsoft.com/en-us/library/aa269321(office.10).aspx`_
2010: https://msdn.microsoft.com/en-us/library/office/ff743835%28v=office.14%29.aspx
2013: https://msdn.microsoft.com/en-us/library/office/ff743835.aspx
"""
import logging

import json
from PySide6 import QtCore

from openlp.core.common import trace_error_handler
from openlp.core.common.i18n import UiStrings
from openlp.core.common.platform import is_win
from openlp.core.common.registry import Registry
from openlp.core.display.screens import ScreenList
from openlp.core.lib.ui import critical_error_message_box, translate
from openlp.plugins.presentations.lib.presentationcontroller import PresentationController, PresentationDocument


if is_win():
    from win32com.client import Dispatch
    import win32con
    import win32gui
    import win32api
    import pywintypes
    import winreg
    import ctypes

log = logging.getLogger(__name__)


class PowerpointController(PresentationController):
    """
    Class to control interactions with PowerPoint Presentations. It creates the runtime Environment , Loads the and
    Closes the Presentation. As well as triggering the correct activities based on the users input.
    """
    log.info('PowerpointController loaded')

    def __init__(self, plugin):
        """
        Initialise the class
        """
        log.debug('Initialising')
        super(PowerpointController, self).__init__(plugin, 'Powerpoint', PowerpointDocument)
        self.supports = ['ppt', 'pps', 'pptx', 'ppsx', 'pptm']
        # MS Office has since version 12 (2007) or above supported odp
        self.also_supports = ['odp']
        self.process = None
        self.com_obj_name = None

    def check_available(self):
        """
        PowerPoint is able to run on this machine.

        This is a registry-only check: it never launches (or attaches to and Quit()s) a real PowerPoint
        COM object. An earlier version actually called Dispatch()/Quit() here to verify PowerPoint could be
        automated, but that is fundamentally unsafe to do just to answer "is it available" -- releasing a
        COM proxy for an Application we just told to Quit() races the out-of-process server's own teardown,
        and was observed to bring down the whole process with an unrecoverable RPC/SEH fault (not a normal,
        catchable Python exception) rather than a clean failure. Checking that a ProgID resolves in the
        registry is enough to know PowerPoint is installed; whether it can actually be automated is left to
        discover at real use time in start_process(), whose failures are already handled there.
        """
        log.debug('check_available')
        if not is_win():
            return False
        # Entry postfixes are for versions 16=2016-2021, 15=2013, 14=2010, 12=2007, 17=future?
        for entry in ['', '.16', '.17', '.15', '.14', '.12']:
            try:
                winreg.QueryValue(winreg.HKEY_CLASSES_ROOT, 'PowerPoint.Application' + entry)
            except OSError:
                continue
            self.com_obj_name = 'PowerPoint.Application' + entry
            return True
        return False

    if is_win():
        def start_process(self):
            """
            Loads PowerPoint process.
            """
            log.debug('start_process')
            if not self.process and self.com_obj_name:
                self.process = Dispatch(self.com_obj_name)

        def kill(self):
            """
            Called at system exit to clean up any running presentations.
            """
            log.debug('Kill powerpoint')
            while self.docs:
                self.docs[0].close_presentation()
            if self.process is None:
                return
            try:
                if self.process.Presentations.Count > 0:
                    return
                self.process.Quit()
            except (AttributeError, pywintypes.com_error):
                log.exception('Exception caught while killing powerpoint process')
                trace_error_handler(log)
            self.process = None


class PowerpointDocument(PresentationDocument):
    """
    Class which holds information and controls a single presentation.
    """

    @property
    def is_in_cloud(self):
        """Determine if the document is a cloud document."""
        return str(self.presentation.FullName).startswith('https://') \
            if self.presentation else False

    @property
    def presentation_file(self):
        """The file name of the presentation, normalised in case of a cloud document."""
        return str(self.presentation.Name) if self.is_in_cloud else str(self.presentation.FullName)

    @property
    def presentation_controller_file(self):
        """The file name of the presentation in the Slide Controller, normalised in case of
            a cloud document."""
        return str(self.file_path.name) if self.is_in_cloud else str(self.file_path)

    def __init__(self, controller, document_path):
        """
        Constructor, store information about the file and initialise.

        :param controller:
        :param pathlib.Path document_path: Path to the document to load
        :rtype: None
        """
        log.debug('Init Presentation Powerpoint')
        super().__init__(controller, document_path)
        self.presentation = None
        self.index_map = {}
        self.slide_count = 0
        self.blank_slide = 1
        self.blank_click = None
        self.presentation_hwnd = None

    def load_presentation(self):
        """
        Called when a presentation is added to the SlideController. Opens the PowerPoint file using the process created
        earlier.
        """
        log.debug('load_presentation')
        try:
            if not self.controller.process:
                self.controller.start_process()
            self.presentation = self.controller.process.Presentations.Open(str(self.file_path), False, False, False)
            log.debug('Loaded presentation %s', self.presentation.FullName)
            self.export_presentation_data()
            # Make sure powerpoint doesn't steal focus, unless we're on a single screen setup
            if len(ScreenList()) > 1:
                Registry().get('main_window').activateWindow()
            return True
        except (AttributeError, pywintypes.com_error):
            log.exception('Exception caught while loading Powerpoint presentation')
            trace_error_handler(log)
            return False

    def export_presentation_data(self):
        """
        Creates the following data for each slide:
        slide[x].png      - Thumbnail images of the slides
        slideNotes[x].txt - Notes for each slide
        titles.txt        - Titles of all slides
        index_map.txt     - Index map of slides and animations
        """
        if self.check_exported_presentation_data_exists():
            return
        try:
            key = 1
            titles = []
            notes = []
            thumbnail_folder = super().get_thumbnail_folder()
            image_width = round(self.presentation.PageSetup.SlideWidth / self.presentation.PageSetup.SlideHeight * 360)
            for num in range(self.presentation.Slides.Count):
                slide = self.presentation.Slides(num + 1)
                if not slide.SlideShowTransition.Hidden:
                    self.index_map[key] = num + 1
                    slide.Export(str(thumbnail_folder / f'slide{key:d}.png'),
                                 'png', image_width, 360)
                    try:
                        text = slide.Shapes.Title.TextFrame.TextRange.Text
                    except Exception:
                        log.exception('Exception raised when getting title text')
                        text = ''
                    slide_title = text.replace('\r\n', ' ').replace('\n', ' ').replace('\x0b', ' ').strip()
                    titles.append(slide_title)
                    note = _get_text_from_shapes(slide.NotesPage.Shapes)
                    if len(note) == 0:
                        note = ' '
                    notes.append(note)
                    key += 1
            self.slide_count = key - 1
            self.save_titles_and_notes(titles, notes)
            with open(thumbnail_folder / 'index_map.txt', 'w', encoding='utf-8') as file:
                json.dump(self.index_map, file)
        except Exception:
            log.exception('Caught exception while creating thumbnails')
            trace_error_handler(log)

    def check_exported_presentation_data_exists(self):
        """
        Checks if there is already exported data that can be used.
        This is the case when:
        1. self.index_map is not empty, since it is only created here or in export_presentation_data.
        2. if index_map.txt exists and is not empty.

        We don't need to check if the content of the PowerPoint file has changed, since get_thumbnail_folder() is
        hash-dependent and would change if the PowerPoint content changes.
        """
        if self.index_map and self.slide_count != 0:
            return True
        thumbnail_folder = super().get_thumbnail_folder()
        index_map_path = thumbnail_folder / 'index_map.txt'
        if not index_map_path.is_file():
            return False
        try:
            with open(index_map_path, 'r', encoding='utf-8') as file:
                self.index_map = json.load(file)
            if not isinstance(self.index_map, dict):
                log.error('Invalid index_map format: Expected a dictionary, got %s', type(self.index_map))
                self.index_map = {}
                self.slide_count = 0
                return False
            self.slide_count = len(self.index_map)
            return True
        except Exception:
            log.exception('Caught exception while trying to import index_map')
            trace_error_handler(log)
            return False

    def close_presentation(self):
        """
        Close presentation and clean up objects. This is triggered by a new object being added to SlideController or
        OpenLP being shut down.
        """
        log.debug('close_presentation')
        if self.presentation:
            try:
                check_for_ghost_window = self.presentation.SlideShowSettings.ShowType == 2
                if check_for_ghost_window:
                    current_window_position = self._get_QRect_from_current_powerpoint_window_position()
                self.presentation.Close()
                if check_for_ghost_window and isinstance(current_window_position, QtCore.QRect):
                    self.close_powerpoint_ghost_window(current_window_position)
            except (AttributeError, pywintypes.com_error):
                log.exception('Caught exception while closing powerpoint presentation')
                trace_error_handler(log)
        self.presentation = None
        self.controller.remove_doc(self)
        # Make sure powerpoint doesn't steal focus, unless we're on a single screen setup
        if len(ScreenList()) > 1:
            Registry().get('main_window').activateWindow()

    def is_loaded(self):
        """
        Returns ``True`` if a presentation is loaded.
        """
        log.debug('is_loaded')
        try:
            if self.presentation is None:
                return False
            return self.presentation_file == self.presentation_controller_file
        except (AttributeError, pywintypes.com_error):
            log.exception('Caught exception while in is_loaded')
            trace_error_handler(log)
            return False

    def is_active(self):
        """
        Returns ``True`` if a presentation is currently active.
        """
        log.debug('is_active')
        if not self.is_loaded():
            return False
        try:
            if self.presentation.SlideShowWindow is None:
                return False
            if self.presentation.SlideShowWindow.View is None:
                return False
            # If a fullscreen PowerPoint window had focus and then lost it,
            # all animations and slide advancements are paused.
            # is_active() is indirectly triggered by poll() in messagelistener.py every 0.5 seconds.
            # If the PowerPoint presentation was paused, it is resumed here.
            if self.presentation.SlideShowWindow.View.State == 2:
                self.presentation.SlideShowWindow.Activate()
                if self.presentation_hwnd:
                    win32gui.FlashWindowEx(self.presentation_hwnd, win32con.FLASHW_STOP, 0, 0)
        except (AttributeError, pywintypes.com_error) as e:
            # PowerPoint COM error 2147188160: occurs in windowed mode with no SlideShowWindow. (e.g. ShowDesktop)
            error_code = getattr(e, 'excepinfo', [None] * 6)[5]
            if error_code != -2147188160:
                log.exception('Caught exception while in is_active')
                trace_error_handler(log)
            return False
        return True

    def unblank_screen(self):
        """
        Unblanks (restores) the presentation.
        """
        log.debug('unblank_screen')
        try:
            self.presentation.SlideShowWindow.Activate()
            self.presentation.SlideShowWindow.View.State = 1
            # Unblanking is broken in PowerPoint 2010 (14.0), need to redisplay
            if 15.0 > float(self.presentation.Application.Version) >= 14.0:
                self.presentation.SlideShowWindow.View.GotoSlide(self.index_map[self.blank_slide], False)
                if self.blank_click:
                    self.presentation.SlideShowWindow.View.GotoClick(self.blank_click)
        except (AttributeError, pywintypes.com_error):
            log.exception('Caught exception while in unblank_screen')
            trace_error_handler(log)
            self.show_error_msg()
        # Stop powerpoint from flashing in the taskbar
        if self.presentation_hwnd:
            win32gui.FlashWindowEx(self.presentation_hwnd, win32con.FLASHW_STOP, 0, 0)
        # Make sure powerpoint doesn't steal focus, unless we're on a single screen setup
        if len(ScreenList()) > 1:
            Registry().get('main_window').activateWindow()

    def blank_screen(self):
        """
        Blanks the screen.
        """
        log.debug('blank_screen')
        try:
            # Unblanking is broken in PowerPoint 2010 (14.0), need to save info for later
            if 15.0 > float(self.presentation.Application.Version) >= 14.0:
                self.blank_slide = self.get_slide_number()
                self.blank_click = self.presentation.SlideShowWindow.View.GetClickIndex()
            # ppSlideShowBlackScreen = 3
            self.presentation.SlideShowWindow.View.State = 3
        except (AttributeError, pywintypes.com_error):
            log.exception('Caught exception while in blank_screen')
            trace_error_handler(log)
            self.show_error_msg()

    def is_blank(self):
        """
        Returns ``True`` if screen is blank.
        """
        log.debug('is_blank')
        if self.is_active():
            try:
                # ppSlideShowBlackScreen = 3
                return self.presentation.SlideShowWindow.View.State == 3
            except (AttributeError, pywintypes.com_error):
                log.exception('Caught exception while in is_blank')
                trace_error_handler(log)
                self.show_error_msg()
        else:
            return False

    def stop_presentation(self):
        """
        Stops the current presentation and hides the output. Used when blanking to desktop.
        """
        log.debug('stop_presentation')
        try:
            check_for_ghost_window = (self.presentation.SlideShowSettings.ShowType == 2)
            if check_for_ghost_window:
                current_window_position = self._get_QRect_from_current_powerpoint_window_position()
            self.presentation.SlideShowSettings.ShowType = 4
            self.presentation.SlideShowWindow.View.Exit()
            if check_for_ghost_window and isinstance(current_window_position, QtCore.QRect):
                if self.close_powerpoint_ghost_window(current_window_position):
                    # The closure of the ghost window causes the presentation to be closed.
                    # It is therefore reloaded immediately.
                    self.load_presentation()
        except (AttributeError, pywintypes.com_error):
            log.exception('Caught exception while in stop_presentation')
            trace_error_handler(log)
            self.show_error_msg()

    if is_win():
        def start_presentation(self):
            """
            Starts a presentation from the beginning.
            """
            log.debug('start_presentation')
            ppt_window = None
            change_powerpoint_display_monitor = (Registry().get('settings')
                                                 .value('presentations/powerpoint control window')
                                                 == QtCore.Qt.CheckState.Unchecked)
            is_fullscreen = ScreenList().current.custom_geometry is None
            # Configure and run PowerPoint
            try:
                if change_powerpoint_display_monitor:
                    if is_fullscreen:
                        self.presentation.SlideShowSettings.ShowType = 1
                        win_displayname = self.get_win_display_name_by_geometry(ScreenList().current.display_geometry)
                        original_powerpoint_display_monitor = self.modify_powerpoint_display_monitor(win_displayname)
                    else:
                        self.presentation.SlideShowSettings.ShowType = 2
                        self.presentation.SlideShowSettings.ShowScrollbar = 0
                self.presentation.SlideShowSettings.ShowPresenterView = 0
                ppt_window = self.presentation.SlideShowSettings.Run()
                if change_powerpoint_display_monitor:
                    if is_fullscreen:
                        self.modify_powerpoint_display_monitor(original_powerpoint_display_monitor)
                    else:
                        self.adjust_powerpoint_window_position(ppt_window, hwnd_to_scale=None)
            except (AttributeError, pywintypes.com_error):
                log.exception('Caught exception while in start_presentation')
                trace_error_handler(log)
                self.show_error_msg()
            # Find the presentation window and save the handle for later
            self.presentation_hwnd = None
            if ppt_window:
                size = ScreenList().current.display_geometry
                log.debug('main display size:  y={y:d}, height={height:d}, '
                          'x={x:d}, width={width:d}'.format(y=int(size.y()), height=int(size.height()),
                                                            x=int(size.x()), width=int(size.width())))
                try:
                    win32gui.EnumWindows(lambda hwnd,
                                         _: self._window_enum_callback(hwnd, size, search_presentation_window=True),
                                         None)
                except pywintypes.error:
                    # When _window_enum_callback returns False to stop the enumeration (looping over open windows)
                    # it causes an exception that is ignored here
                    pass
                # Move PowerPoint window slightly so caption and border are outside the geometry used by OpenLP
                if not is_fullscreen:
                    self.adjust_powerpoint_window_position(ppt_window, self.presentation_hwnd)
                # It is a known bug that BringWindowToTop and SetForegroundWindow don't work properly in some cases.
                # A widely accepted workaround is pressing a key before calling the API,
                # but even that does not guarantee success. Here, BringWindowToTop is used without any workarounds,
                # just to increase the chances of it showing up on top, in case there are other programs running
                # on the monitor which ideally shouldn't be the case in a multi screen setup anyway.
                try:
                    win32gui.BringWindowToTop(self.presentation_hwnd)
                except Exception as e:
                    log.exception('Caught exception while running BringWindowToTop in start_presentation. %s', e)
            # Make sure powerpoint doesn't steal focus, unless we're on a single screen setup
            if len(ScreenList()) > 1:
                Registry().get('main_window').activateWindow()

        def close_powerpoint_ghost_window(self, size):
            """
            Closes a 'ghost' PowerPoint window that appears when PowerPoint is in windowed mode and
            SlideShowWindow.View.Exit() or presentation.Close() is called.
            Ideally this function shouldn't exist but it seems there is no way
            to prevent the creation of this new window.
            """
            log.debug('close_powerpoint_ghost_window')
            # Since the presentation window got closed, presentation_hwnd can be reused for this 'ghost window'
            self.presentation_hwnd = None
            try:
                win32gui.EnumWindows(lambda hwnd,
                                     _: self._window_enum_callback(hwnd, size, search_presentation_window=False),
                                     None)
            except pywintypes.error:
                # When _window_enum_callback returns False to stop the enumeration (looping over open windows),
                # it causes an exception that is ignored here
                pass
            if self.presentation_hwnd is not None:
                try:
                    WM_CLOSE = 0x0010
                    ctypes.windll.user32.PostMessageW(self.presentation_hwnd, WM_CLOSE, 0, 0)
                    return True
                except Exception:
                    log.warning('Caught exception while trying to close possible PowerPoint ghost window')
                    trace_error_handler(log)
                finally:
                    self.presentation_hwnd = None

        def get_win_display_name_by_geometry(self, qt_geometry):
            try:
                qt_tuple = (qt_geometry.x(),
                            qt_geometry.y(),
                            qt_geometry.x() + qt_geometry.width(),
                            qt_geometry.y() + qt_geometry.height())
                for hMonitor, hdcMonitor, win_rect in win32api.EnumDisplayMonitors():
                    if qt_tuple == win_rect:
                        info = win32api.GetMonitorInfo(hMonitor)
                        return info['Device']
            except Exception:
                log.warning('Caught exception while in get_win_display_name_by_geometry')
                trace_error_handler(log)
            return None

        def modify_powerpoint_display_monitor(self, new_value):
            """
            Changes the registry key used by PowerPoint to control which monitor is used when in fullscreen.
            The state of the registry key before the change is cached and rolled back immediately after
            the presentation is started.
            """
            if not isinstance(new_value, str):
                log.warning('modify_powerpoint_display_monitor called with a new value that is not a string.')
                return
            pp_version = 'Failed to find PowerPoint version'
            try:
                pp_version = self.presentation.Parent.Application.Version
                reg_path = rf'SOFTWARE\Microsoft\Office\{pp_version}\PowerPoint\Options'
                reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0,
                                         winreg.KEY_ALL_ACCESS | winreg.KEY_WOW64_32KEY)
                try:
                    original_value = winreg.QueryValueEx(reg_key, 'DisplayMonitor')[0]
                except FileNotFoundError:
                    original_value = None
                if original_value != new_value:
                    winreg.SetValueEx(reg_key, 'DisplayMonitor', 0, winreg.REG_SZ, new_value)
                winreg.CloseKey(reg_key)
                return original_value
            except OSError:
                log.warning(
                    'Unable to change PowerPoint setting for selecting the presentation monitor. '
                    'PowerPoint version used for registry access: %s', pp_version)

        def adjust_powerpoint_window_position(self, ppt_window, hwnd_to_scale=None):
            """
            Move PowerPoint window to geometry used by OpenLP or move PowerPoint window
            so that the part of the window used fot the presentation it the same as the geometry used by OpenLP.
            This function is only used when PowerPoint is run in windowed mode
            """
            # Calculate Border and Caption
            caption_hight = 0
            border_width = 0
            if hwnd_to_scale is not None:
                try:
                    window_rect = ctypes.wintypes.RECT()
                    usable_rect = ctypes.wintypes.RECT()
                    ctypes.windll.user32.GetWindowRect(self.presentation_hwnd, ctypes.byref(window_rect))
                    ctypes.windll.user32.GetClientRect(self.presentation_hwnd, ctypes.byref(usable_rect))
                    window_width = window_rect.right - window_rect.left
                    window_height = window_rect.bottom - window_rect.top
                    client_width = usable_rect.right - usable_rect.left
                    client_height = usable_rect.bottom - usable_rect.top
                    border_width = (window_width - client_width) // 2
                    caption_hight = window_height - client_height - border_width
                except Exception:
                    log.exception('Unable to calculate border and titlebar size.')
                    trace_error_handler(log)
            try:
                dpi = ScreenList().current.raw_screen.logicalDotsPerInch()
                size = ScreenList().current.display_geometry
                ppt_window.Top = (size.y() - caption_hight) * 72 / dpi
                ppt_window.Height = (size.height() + caption_hight + border_width) * 72 / dpi
                ppt_window.Left = (size.x() - border_width) * 72 / dpi
                ppt_window.Width = (size.width() + 2 * border_width) * 72 / dpi
            except AttributeError:
                log.exception('AttributeError while in adjust_powerpoint_window_position')
                trace_error_handler(log)

    def _window_enum_callback(self, hwnd, size, search_presentation_window=True):
        """
        Method for callback from win32gui.EnumWindows.
        Used to find the PowerPoint presentation window and stop it flashing in the taskbar.
        """
        # Get the size of the current window and if it greater than or equal to the size of our main display we assume
        # it is the PowerPoint presentation window.
        (left, top, right, bottom) = win32gui.GetWindowRect(hwnd)
        window_title = win32gui.GetWindowText(hwnd)
        powerpoint_height = bottom - top
        powerpoint_width = right - left
        log.debug('window size: left=%d, top=%d, right=%d, bottom=%d', left, top, right, bottom)
        log.debug('compare size: %d and %d, %d and %d, %d and %d, %d and %d',
                  size.y(), top, size.height(), powerpoint_height, size.x(), left, size.width(),
                  powerpoint_width)
        log.debug('window title: %s', window_title)
        handle_is_found = size.y() == top and \
            size.height() <= powerpoint_height and \
            size.x() == left and \
            size.width() <= powerpoint_width and \
            window_title.startswith('PowerPoint')
        if search_presentation_window:
            handle_is_found = handle_is_found and self.file_path.stem in window_title
        if handle_is_found:
            log.debug('Found a match and will save the handle')
            self.presentation_hwnd = hwnd
            if search_presentation_window:
                # Stop PowerPoint from flashing in the taskbar.
                win32gui.FlashWindowEx(self.presentation_hwnd, win32con.FLASHW_STOP, 0, 0)
        # Returning false stops the enumeration (looping over open windows).
        return not handle_is_found

    def _get_QRect_from_current_powerpoint_window_position(self):
        if not self.presentation:
            return False
        try:
            dpi = ScreenList().current.raw_screen.logicalDotsPerInch()
            return QtCore.QRect(self.presentation.SlideShowWindow.Left * dpi / 72,
                                self.presentation.SlideShowWindow.Top * dpi / 72,
                                self.presentation.SlideShowWindow.Width * dpi / 72,
                                self.presentation.SlideShowWindow.Height * dpi / 72)
        except Exception:
            log.exception('Caught exception while calculating powerpoint position')
            trace_error_handler(log)
            return False

    def get_slide_number(self):
        """
        Returns the current slide number.
        """
        log.debug('get_slide_number')
        ret = 0
        try:
            # We need 2 approaches to getting the current slide number, because
            # SlideShowWindow.View.Slide.SlideIndex wont work on the end-slide where Slide isn't available, and
            # SlideShowWindow.View.CurrentShowPosition returns 0 when called when a transition is executing (in 2013)
            # So we use SlideShowWindow.View.Slide.SlideIndex unless the state is done (ppSlideShowDone = 5)
            if self.presentation.SlideShowWindow.View.State != 5:
                ret = self.presentation.SlideShowWindow.View.Slide.SlideIndex
                # Do reverse lookup in the index_map to find the slide number to return
                ret = next((key for key, slidenum in self.index_map.items() if slidenum == ret), None)
            else:
                ret = self.presentation.SlideShowWindow.View.CurrentShowPosition
        except (AttributeError, pywintypes.com_error):
            log.exception('Caught exception while in get_slide_number')
            trace_error_handler(log)
            self.show_error_msg()
        return ret

    def get_slide_count(self):
        """
        Returns total number of slides that are not hidden.
        """
        log.debug('get_slide_count')
        if (self.slide_count == 0 or bool(self.index_map) is False) and self.is_loaded():
            # If this function gets run before export_presentation_data() we haven't calculated the slide_count yet
            self.export_presentation_data()
        return self.slide_count

    def goto_slide(self, slide_no: int) -> None:
        """
        Moves to a specific slide in the presentation.

        :param slide_no: The slide number to be moved to, starting at 1
        """
        log.debug('goto_slide')
        try:
            if Registry().get('settings').value('presentations/powerpoint slide click advance') \
                    and self.get_slide_number() == slide_no:
                click_index = self.presentation.SlideShowWindow.View.GetClickIndex()
                click_count = self.presentation.SlideShowWindow.View.GetClickCount()
                log.debug('We are already on this slide - go to next effect if any left, index: '
                          '%d, count: %d', click_index, click_count)
                if click_index < click_count:
                    self.next_step()
            else:
                slide_index = self.index_map.get(slide_no)
                if slide_index is None:
                    slide_index = self.index_map.get(str(slide_no))
                if slide_index is not None:
                    self.presentation.SlideShowWindow.View.GotoSlide(slide_index)
        except (AttributeError, pywintypes.com_error):
            log.exception('Caught exception while in goto_slide')
            trace_error_handler(log)
            self.show_error_msg()

    def next_step(self):
        """
        Triggers the next effect of slide on the running presentation.
        """
        log.debug('next_step')
        # if we are at the presentations end don't go further, just return True
        if self.presentation.SlideShowWindow.View.GetClickCount() == \
                self.presentation.SlideShowWindow.View.GetClickIndex() \
                and self.get_slide_number() == self.get_slide_count():
            return True
        past_end = False
        try:
            self.presentation.SlideShowWindow.Activate()
            self.presentation.SlideShowWindow.View.Next()
        except (AttributeError, pywintypes.com_error):
            log.exception('Caught exception while in next_step')
            trace_error_handler(log)
            self.show_error_msg()
            return past_end
        # If for some reason the presentation end was not detected above, this will catch it.
        if self.get_slide_number() > self.get_slide_count():
            log.debug('past end, stepping back to previous')
            self.previous_step()
            past_end = True
        # Stop powerpoint from flashing in the taskbar
        if self.presentation_hwnd:
            win32gui.FlashWindowEx(self.presentation_hwnd, win32con.FLASHW_STOP, 0, 0)
        # Make sure powerpoint doesn't steal focus, unless we're on a single screen setup
        if len(ScreenList()) > 1:
            Registry().get('main_window').activateWindow()
        return past_end

    def previous_step(self):
        """
        Triggers the previous slide on the running presentation.
        """
        log.debug('previous_step')
        # if we are at the presentations start we can't go further back, just return True
        if self.presentation.SlideShowWindow.View.GetClickIndex() == 0 and self.get_slide_number() == 1:
            return True
        try:
            self.presentation.SlideShowWindow.View.Previous()
        except (AttributeError, pywintypes.com_error):
            log.exception('Caught exception while in previous_step')
            trace_error_handler(log)
            self.show_error_msg()
        return False

    def get_slide_text(self, slide_no):
        """
        Returns the text on the slide.

        :param slide_no: The slide the text is required for, starting at 1
        """
        return _get_text_from_shapes(self.presentation.Slides(self.index_map[slide_no]).Shapes)

    def get_slide_notes(self, slide_no):
        """
        Returns the text on the slide.

        :param slide_no: The slide the text is required for, starting at 1
        """
        return _get_text_from_shapes(self.presentation.Slides(self.index_map[slide_no]).NotesPage.Shapes)

    def show_error_msg(self):
        """
        Stop presentation and display an error message.
        """
        try:
            self.presentation.SlideShowWindow.View.Exit()
        except (AttributeError, pywintypes.com_error):
            log.exception('Failed to exit Powerpoint presentation after error')
        critical_error_message_box(UiStrings().Error, translate('PresentationPlugin.PowerpointDocument',
                                                                'An error occurred in the PowerPoint integration '
                                                                'and the presentation will be stopped. '
                                                                'Restart the presentation if you wish to present it.'))


def _get_text_from_shapes(shapes):
    """
    Returns any text extracted from the shapes on a presentation slide.

    :param shapes: A set of shapes to search for text.
    """
    text = ''
    try:
        for shape in shapes:
            if shape.PlaceholderFormat.Type == 2:  # 2 from is enum PpPlaceholderType.ppPlaceholderBody
                if shape.HasTextFrame and shape.TextFrame.HasText:
                    text += shape.TextFrame.TextRange.Text + '\n'
    except pywintypes.com_error:
        log.exception('Failed to extract text from powerpoint slide')
    return text
