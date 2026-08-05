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
The :mod:`slidecontroller` module contains the most important part of OpenLP - the slide controller
"""
import copy
import datetime
from collections import deque
from pathlib import Path, PurePath
from threading import Lock

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common import SlideLimits
from openlp.core.common.actions import ActionList, CategoryOrder
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.mixins import LogMixin, RegistryProperties
from openlp.core.common.platform import is_wayland_compositor
from openlp.core.common.registry import Registry, RegistryBase
from openlp.core.common.utils import wait_for
from openlp.core.display.screens import ScreenList
from openlp.core.display.window import DisplayWindow
from openlp.core.lib import ServiceItemAction, image_to_byte
from openlp.core.lib.serviceitem import ItemCapabilities
from openlp.core.lib.theme import BackgroundType
from openlp.core.lib.ui import create_action
from openlp.core.state import State
from openlp.core.ui import DisplayControllerType, HideMode
from openlp.core.ui.icons import UiIcons
from openlp.core.ui.media import MediaPlayItem, media_empty_song
from openlp.core.ui.style import UiThemes, is_ui_theme
from openlp.core.widgets.layouts import AspectRatioLayout
from openlp.core.widgets.toolbar import MediaToolbar, OpenLPToolbar
from openlp.core.widgets.views import ListPreviewWidget

# Threshold which has to be trespassed to toggle.
HIDE_MENU_THRESHOLD = 80

NARROW_MENU = [
    'hide_menu'
]
LOOP_LIST = [
    'play_slides_menu',
    'loop_separator',
    'delay_spin_box'
]
WIDE_MENU = [
    'show_screen_button',
    'blank_screen_button',
    'theme_screen_button',
    'desktop_screen_button'
]

NON_TEXT_MENU = [
    'show_screen_button',
    'blank_screen_button',
    'desktop_screen_button'
]


class InfoLabel(QtWidgets.QLabel):
    """
    InfoLabel is a subclassed QLabel. Created to provide the ability to add a ellipsis if the text is cut off. Original
    source: https://stackoverflow.com/questions/11446478/pyside-pyqt-truncate-text-in-qlabel-based-on-minimumsize
    """

    def paintEvent(self, event):
        """
        Reimplemented to allow the drawing of elided text if the text is longer than the width of the label
        """
        painter = QtGui.QPainter(self)
        try:
            metrics = QtGui.QFontMetrics(self.font())
            elided = metrics.elidedText(self.text(), QtCore.Qt.TextElideMode.ElideRight, self.width())
            painter.drawText(self.rect(),
                             QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter, elided)
        finally:
            painter.end()

    def setText(self, text):
        """
        Reimplemented to set the tool tip text.
        """
        self.setToolTip(text)
        super().setText(text)


class SlideController(QtWidgets.QWidget, LogMixin, RegistryProperties):
    """
    SlideController is the slide controller widget. This widget is what the
    user uses to control the displaying of verses/slides/etc on the screen.
    """

    slidecontroller_changed = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        """
        Set up the Slide Controller.
        """
        super().__init__(*args, **kwargs)
        self.is_live = False
        self.controller_type = None
        self.displays = []
        self.screens = ScreenList()
        self.media_player = None
        self.audio_player = None
        self.media_play_item = MediaPlayItem()
        Registry().set_flag('has doubleclick added item to service', True)
        Registry().set_flag('replace service manager item', False)

    def initialise(self):
        """
        Call by bootstrap functions
        """
        self.setup_ui()
        self.setup_displays()
        self.screen_size_changed()

    def post_set_up(self):
        # Update the theme whenever the theme is changed (hot reload)
        Registry().register_function('theme_update_list', self.on_theme_changed)
        Registry().register_function('theme_level_changed', self.on_theme_changed)
        Registry().register_function('theme_change_global', self.on_theme_changed)
        Registry().register_function('theme_change_service', self.on_theme_changed)

    def setup_displays(self):
        """
        Set up the display
        """
        if not self.is_live:
            return
        # Delete any existing displays
        self.close_displays()
        for screen in self.screens:
            if screen.is_display:
                will_start_hidden = self._current_hide_mode == HideMode.Screen
                display = DisplayWindow(self, screen, start_hidden=will_start_hidden,
                                        after_loaded_callback=self._display_after_loaded_callback,
                                        window_title='Live Screen' if self.is_live else 'Preview Screen')
                self.displays.append(display)
                self._reset_blank(False)
        if self.display:
            self.__add_actions_to_widget(self.display)

    def _display_after_loaded_callback(self):
        # As the display was reloaded, we'll need to process current item again
        if self.service_item:
            self._process_item(self.service_item, self.selected_row, is_reloading=True)
        # Restoring last hide mode
        if self._current_hide_mode:
            self.display.hide_display(self._current_hide_mode)

    def close_displays(self):
        """
        Close all open displays
        """
        for display in self.displays:
            display.deregister_display()
            display.setParent(None)
            display.close()
            del display
        self.displays = []

    @property
    def display(self):
        return self.displays[0] if self.displays else None

    @property
    def current_hide_mode(self):
        return self._current_hide_mode

    def setup_ui(self):
        """
        Initialise the UI elements of the controller
        """
        try:
            self.ratio = self.screens.current.display_geometry.width() / self.screens.current.display_geometry.height()
        except ZeroDivisionError:
            self.ratio = 1
        self.process_queue_lock = Lock()
        self.slide_selected_lock = Lock()
        self.timer_id = 0
        self.song_edit = False
        self.selected_row = 0
        self.service_item = None
        self.slide_limits = None
        self.update_slide_limits()
        self.panel = QtWidgets.QWidget(self.main_window.control_splitter)
        self.slide_list = {}
        self.slide_count = 0
        self.ignore_toolbar_resize_events = False
        # Layout for holding panel
        self.panel_layout = QtWidgets.QVBoxLayout(self.panel)
        self.panel_layout.setSpacing(0)
        self.panel_layout.setContentsMargins(0, 0, 0, 0)
        # Type label at the top of the slide controller with icon
        self.top_label_horizontal = QtWidgets.QHBoxLayout()
        self.panel_layout.addLayout(self.top_label_horizontal)
        if self.is_live:
            icon = UiIcons().live
        else:
            icon = UiIcons().preview
        pixmap = icon.pixmap(QtCore.QSize(28, 28))
        self.top_icon = QtWidgets.QLabel()
        self.top_icon.setPixmap(pixmap)
        self.top_icon.setStyleSheet("padding: 0px 0px 0px 25px;")
        self.top_icon.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.type_label = QtWidgets.QLabel(self.panel)
        self.type_label.setObjectName('slide_controller_type_label')
        self.type_label.setProperty('isLive', 'true' if self.is_live else 'false')
        self.type_label.setProperty('onAir', 'true' if self.is_live else 'false')
        if not is_ui_theme(UiThemes.Noir):
            # The Noir theme styles this label from the application stylesheet, which an
            # inline widget stylesheet would override.
            self.type_label.setStyleSheet('padding: 0px 20px 0px 2px; font-weight: bold;')
        if self.is_live:
            self.type_label.setText(UiStrings().Live)
        else:
            self.type_label.setText(UiStrings().Preview)
        # Info label for the title of the current item, at the top of the slide controller
        self.info_label = InfoLabel(self.panel)
        self.info_label.setObjectName('slide_controller_info_label')
        if not is_ui_theme(UiThemes.Noir):
            self.info_label.setStyleSheet('font-style: italic;')
        self.info_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
        # Slide position indicator ("3 / 12"), only shown by the Noir theme
        self.slide_count_label = QtWidgets.QLabel(self.panel)
        self.slide_count_label.setObjectName('slide_controller_count_label')
        if is_ui_theme(UiThemes.Noir):
            # Tabular figures stop the counter jittering as the numbers change
            try:
                count_font = self.slide_count_label.font()
                count_font.setFeature(QtGui.QFont.Tag('tnum'), 1)
                self.slide_count_label.setFont(count_font)
            except AttributeError:
                # QFont.setFeature needs Qt >= 6.7; older builds keep default figures
                pass
        self.top_label_horizontal.addWidget(self.top_icon)
        self.top_label_horizontal.addWidget(self.type_label)
        self.top_label_horizontal.addWidget(self.info_label, stretch=1)
        self.top_label_horizontal.addWidget(self.slide_count_label)
        if is_ui_theme(UiThemes.Noir):
            # The Live/Preview chip carries the identity, so the duplicate icon goes;
            # the panel itself gets an accent line to tell the two controllers apart.
            self.top_icon.hide()
            self.top_label_horizontal.setContentsMargins(8, 6, 8, 4)
            self.top_label_horizontal.setSpacing(6)
            self.panel.setObjectName('slide_controller_panel')
            self.panel.setProperty('isLive', 'true' if self.is_live else 'false')
            # Plain QWidgets only honor stylesheet borders/backgrounds with this set
            self.panel.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        # Splitter
        self.splitter = QtWidgets.QSplitter(self.panel)
        self.splitter.setOrientation(QtCore.Qt.Orientation.Vertical)
        self.panel_layout.addWidget(self.splitter)
        # Actual controller section
        self.controller = QtWidgets.QWidget(self.splitter)
        self.controller.setGeometry(QtCore.QRect(0, 0, 100, 536))
        self.controller.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                                            QtWidgets.QSizePolicy.Policy.Expanding))
        self.controller_layout = QtWidgets.QVBoxLayout(self.controller)
        self.controller_layout.setSpacing(0)
        self.controller_layout.setContentsMargins(0, 0, 0, 0)
        # Controller list view
        self.preview_widget = ListPreviewWidget(self, self.ratio)
        self.controller_layout.addWidget(self.preview_widget)
        # Build the full toolbar
        self.toolbar = OpenLPToolbar(self)
        self.toolbar.setObjectName('slide_controller_toolbar')
        size_toolbar_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed,
                                                    QtWidgets.QSizePolicy.Policy.Fixed)
        size_toolbar_policy.setHorizontalStretch(0)
        size_toolbar_policy.setVerticalStretch(0)
        size_toolbar_policy.setHeightForWidth(self.toolbar.sizePolicy().hasHeightForWidth())
        self.toolbar.setSizePolicy(size_toolbar_policy)
        self.previous_item = create_action(self, 'previousItem_' + self.type_prefix,
                                           text=translate('OpenLP.SlideController', 'Previous Slide'),
                                           icon=UiIcons().arrow_up,
                                           tooltip=translate('OpenLP.SlideController', 'Move to previous.'),
                                           can_shortcuts=True,
                                           context=QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut,
                                           category=self.category, triggers=self.on_slide_selected_previous)
        self.toolbar.addAction(self.previous_item)
        self.next_item = create_action(self, 'nextItem_' + self.type_prefix,
                                       text=translate('OpenLP.SlideController', 'Next Slide'),
                                       icon=UiIcons().arrow_down,
                                       tooltip=translate('OpenLP.SlideController', 'Move to next.'),
                                       can_shortcuts=True, context=QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut,
                                       category=self.category, triggers=self.on_slide_selected_next_action)
        self.toolbar.addAction(self.next_item)
        self.toolbar.addSeparator()
        self.controller_type = DisplayControllerType.Preview
        self._current_hide_mode = None
        if self.is_live:
            self.controller_type = DisplayControllerType.Live
            self.slide_changed_time = datetime.datetime.now()
            self.fetching_screenshot = False
            self.screen_capture = None
            # Hide Menu
            self.hide_menu = QtWidgets.QToolButton(self.toolbar)
            self.hide_menu.setObjectName('hide_menu')
            self.hide_menu.setText(translate('OpenLP.SlideController', 'Hide'))
            self.hide_menu.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)
            self.hide_menu.setMenu(QtWidgets.QMenu(translate('OpenLP.SlideController', 'Hide'), self.toolbar))
            self.toolbar.add_toolbar_widget(self.hide_menu)
            # The order of the blank to modes in Shortcuts list comes from here.
            self.show_screen = create_action(self, 'showScreen',
                                             text=translate('OpenLP.SlideController', 'Show Presentation'),
                                             icon=UiIcons().get_icon_variant_selected('live_presentation'),
                                             checked=False, can_shortcuts=True, category=self.category,
                                             triggers=self.on_show_display)
            self.theme_screen = create_action(self, 'themeScreen',
                                              text=translate('OpenLP.SlideController', 'Show Theme'),
                                              icon=UiIcons().get_icon_variant_selected('live_theme'),
                                              checked=False, can_shortcuts=True, category=self.category,
                                              triggers=self.on_toggle_theme)
            self.blank_screen = create_action(self, 'blankScreen',
                                              text=translate('OpenLP.SlideController', 'Show Black'),
                                              icon=UiIcons().get_icon_variant_selected('live_black'),
                                              checked=False, can_shortcuts=True, category=self.category,
                                              triggers=self.on_toggle_blank)
            self.desktop_screen = create_action(self, 'desktopScreen',
                                                text=translate('OpenLP.SlideController', 'Show Desktop'),
                                                icon=UiIcons().get_icon_variant_selected('live_desktop'),
                                                checked=False, can_shortcuts=True, category=self.category,
                                                triggers=self.on_toggle_desktop)
            self.hide_menu.setDefaultAction(self.show_screen)
            self.hide_menu.menu().addAction(self.show_screen)
            self.hide_menu.menu().addAction(self.theme_screen)
            self.hide_menu.menu().addAction(self.blank_screen)
            self.hide_menu.menu().addAction(self.desktop_screen)
            # Wide menu of display control buttons.
            self.show_screen_button = QtWidgets.QToolButton(self.toolbar)
            self.show_screen_button.setObjectName('show_screen_button')
            self.toolbar.add_toolbar_widget(self.show_screen_button)
            self.show_screen_button.setDefaultAction(self.show_screen)
            self.theme_screen_button = QtWidgets.QToolButton(self.toolbar)
            self.theme_screen_button.setObjectName('theme_screen_button')
            self.toolbar.add_toolbar_widget(self.theme_screen_button)
            self.theme_screen_button.setDefaultAction(self.theme_screen)
            self.blank_screen_button = QtWidgets.QToolButton(self.toolbar)
            self.blank_screen_button.setObjectName('blank_screen_button')
            self.toolbar.add_toolbar_widget(self.blank_screen_button)
            self.blank_screen_button.setDefaultAction(self.blank_screen)
            self.desktop_screen_button = QtWidgets.QToolButton(self.toolbar)
            self.desktop_screen_button.setObjectName('desktop_screen_button')
            self.toolbar.add_toolbar_widget(self.desktop_screen_button)
            self.desktop_screen_button.setDefaultAction(self.desktop_screen)
            self.toolbar.add_toolbar_action('loop_separator', separator=True)
            # Play Slides Menu
            self.play_slides_menu = QtWidgets.QToolButton(self.toolbar)
            self.play_slides_menu.setObjectName('play_slides_menu')
            self.play_slides_menu.setText(translate('OpenLP.SlideController', 'Play Slides'))
            self.play_slides_menu.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)
            self.play_slides_menu.setMenu(QtWidgets.QMenu(translate('OpenLP.SlideController', 'Play Slides'),
                                                          self.toolbar))
            self.toolbar.add_toolbar_widget(self.play_slides_menu)
            self.play_slides_loop = create_action(self, 'playSlidesLoop', text=UiStrings().PlaySlidesInLoop,
                                                  icon=UiIcons().get_icon_variant_selected('loop'), checked=False,
                                                  can_shortcuts=True, category=self.category,
                                                  triggers=self.on_play_slides_loop)
            self.play_slides_once = create_action(self, 'playSlidesOnce', text=UiStrings().PlaySlidesToEnd,
                                                  icon=UiIcons().get_icon_variant_selected('play_slides'),
                                                  checked=False, can_shortcuts=True, category=self.category,
                                                  triggers=self.on_play_slides_once)
            if self.settings.value('advanced/slide limits') == SlideLimits.Wrap:
                self.play_slides_menu.setDefaultAction(self.play_slides_loop)
            else:
                self.play_slides_menu.setDefaultAction(self.play_slides_once)
            self.play_slides_menu.menu().addAction(self.play_slides_loop)
            self.play_slides_menu.menu().addAction(self.play_slides_once)
            # Loop Delay Spinbox
            self.delay_spin_box = QtWidgets.QSpinBox()
            self.delay_spin_box.setObjectName('delay_spin_box')
            self.delay_spin_box.setRange(1, 180)
            self.delay_spin_box.setSuffix(' {unit}'.format(unit=UiStrings().Seconds))
            self.delay_spin_box.setToolTip(translate('OpenLP.SlideController', 'Delay between slides in seconds.'))
            self.receive_spin_delay()
            self.toolbar.add_toolbar_widget(self.delay_spin_box)
        else:
            self.toolbar.add_toolbar_action('goLive', icon=UiIcons().live,
                                            tooltip=translate('OpenLP.SlideController', 'Move to live.'),
                                            triggers=self.on_go_live)
            self.toolbar.add_toolbar_action('addToService', icon=UiIcons().add,
                                            tooltip=translate('OpenLP.SlideController', 'Add to Service.'),
                                            triggers=self.on_preview_add_to_service)
            self.toolbar.addSeparator()
            self.toolbar.add_toolbar_action('editSong', icon=UiIcons().edit,
                                            tooltip=translate('OpenLP.SlideController',
                                                              'Edit and reload song preview.'),
                                            triggers=self.on_edit_song)
            self.toolbar.add_toolbar_action('clear', icon=UiIcons().delete,
                                            tooltip=translate('OpenLP.SlideController',
                                                              'Clear'),
                                            triggers=self.on_clear)
        self.controller_layout.addWidget(self.toolbar)
        # Build a Media ToolBar
        self.mediabar = MediaToolbar(self)
        self.mediabar.identification_label.setText(translate('OpenLP.SlideController', 'Media'))
        self.mediabar.on_action = lambda *args: self.send_to_plugins(*args)
        self.controller_layout.addWidget(self.mediabar)
        self.mediabar.setVisible(False)
        if self.is_live:
            self.new_song_menu()
            self.toolbar.add_toolbar_widget(self.song_menu)
            self.toolbar.set_widget_visible('song_menu', False)
        # Screen preview area
        self.preview_frame = QtWidgets.QFrame(self.splitter)
        self.preview_frame.setGeometry(QtCore.QRect(0, 0, 300, int(300 * self.ratio)))
        self.preview_frame.setMinimumHeight(100)
        self.preview_frame.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,
                                                               QtWidgets.QSizePolicy.Policy.Ignored,
                                                               QtWidgets.QSizePolicy.ControlType.Label))
        self.preview_frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.preview_frame.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.preview_frame.setObjectName('preview_frame')
        self.slide_layout = AspectRatioLayout(self.preview_frame, self.ratio)
        self.slide_layout.margin = 8
        self.slide_layout.setSpacing(0)
        self.slide_layout.setObjectName('SlideLayout')
        # Set up the preview display
        self.preview_display = DisplayWindow(self, window_title='Live' if self.is_live else 'Preview')
        self.slide_layout.addWidget(self.preview_display)
        self.slide_layout.resize.connect(self.on_preview_resize)
        # Actual preview screen
        if self.is_live:
            self.current_shortcut = ''
            self.shortcut_timer = QtCore.QTimer()
            self.shortcut_timer.setObjectName('shortcut_timer')
            self.shortcut_timer.setSingleShot(True)
            shortcuts = [
                {'key': 'V', 'configurable': True, 'text': translate('OpenLP.SlideController', 'Go to "Verse"')},
                {'key': 'C', 'configurable': True, 'text': translate('OpenLP.SlideController', 'Go to "Chorus"')},
                {'key': 'B', 'configurable': True, 'text': translate('OpenLP.SlideController', 'Go to "Bridge"')},
                {'key': 'P', 'configurable': True,
                 'text': translate('OpenLP.SlideController', 'Go to "Pre-Chorus"')},
                {'key': 'I', 'configurable': True, 'text': translate('OpenLP.SlideController', 'Go to "Intro"')},
                {'key': 'E', 'configurable': True, 'text': translate('OpenLP.SlideController', 'Go to "Ending"')},
                {'key': 'O', 'configurable': True, 'text': translate('OpenLP.SlideController', 'Go to "Other"')}
            ]
            shortcuts.extend([{'key': str(number)} for number in range(10)])
            self.controller.addActions([create_action(self, 'shortcutAction_{key}'.format(key=s['key']),
                                                      text=s.get('text'),
                                                      can_shortcuts=True,
                                                      context=QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut,
                                                      category=self.category if s.get('configurable') else None,
                                                      triggers=self._slide_shortcut_activated) for s in shortcuts])
            self.shortcut_timer.timeout.connect(self._slide_shortcut_activated)
        # Signals
        self.preview_widget.clicked.connect(self.on_slide_selected)
        self.preview_widget.verticalHeader().sectionClicked.connect(self.on_slide_selected)
        if self.is_live:
            self.preview_widget.resize_event.connect(self.on_controller_size_changed)
            # Need to use event as called across threads and UI is updated
            self.slidecontroller_toggle_display.connect(self.toggle_display)
            Registry().register_function('slidecontroller_live_spin_delay', self.receive_spin_delay)
            self.toolbar.set_widget_visible(LOOP_LIST, False)
            self.toolbar.set_widget_visible(WIDE_MENU, False)
            self.set_live_hot_keys(self)
            self.__add_actions_to_widget(self.controller)
        else:
            self.preview_widget.doubleClicked.connect(self.on_preview_double_click)
            self.toolbar.set_widget_visible('editSong', False)
            self.toolbar.set_widget_visible('clear', False)
            self.controller.addActions([self.next_item, self.previous_item])
        Registry().register_function('slidecontroller_{text}_stop_loop'.format(text=self.type_prefix),
                                     self.on_stop_loop)
        Registry().register_function('slidecontroller_{text}_change'.format(text=self.type_prefix),
                                     self.on_slide_change)
        Registry().register_function('slidecontroller_{text}_blank'.format(text=self.type_prefix),
                                     self.on_blank_display)
        Registry().register_function('slidecontroller_{text}_unblank'.format(text=self.type_prefix),
                                     self.on_slide_unblank)
        Registry().register_function('slidecontroller_update_slide_limits', self.update_slide_limits)
        Registry().register_function('slidecontroller_preview_display_show_display', self.preview_display.show_display)
        getattr(self, 'slidecontroller_{text}_set'.format(text=self.type_prefix)).connect(self.on_slide_selected_index)
        getattr(self, 'slidecontroller_{text}_next'.format(text=self.type_prefix)).connect(self.on_slide_selected_next)
        # NOTE: {} used to keep line length < maxline
        getattr(self,
                'slidecontroller_{}_previous'.format(self.type_prefix)).connect(self.on_slide_selected_previous)
        if self.is_live:
            getattr(self, 'slidecontroller_live_clear').connect(self.on_clear)
            self.mediacontroller_live_play.connect(self.media_controller.on_media_play)
            self.mediacontroller_live_pause.connect(self.media_controller.on_media_pause)
            self.mediacontroller_live_stop.connect(self.media_controller.on_media_stop)
        else:
            getattr(self, 'slidecontroller_preview_clear').connect(self.on_clear)

    def new_song_menu(self):
        """
        Rebuild the song menu object from scratch.
        """
        # Build the Song Toolbar
        self.song_menu = QtWidgets.QToolButton(self.toolbar)
        self.song_menu.setObjectName('song_menu')
        self.song_menu.setText(translate('OpenLP.SlideController', 'Go To'))
        self.song_menu.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.song_menu.setMenu(QtWidgets.QMenu(translate('OpenLP.SlideController', 'Go To'), self.toolbar))

    def _raise_displays(self):
        for display in self.displays:
            display.raise_()

    def _slide_shortcut_activated(self):
        """
        Called, when a shortcut has been activated to jump to a chorus, verse, etc.

        **Note**: This implementation is based on shortcuts. But it rather works like "key sequences". You have to
        press one key after the other and **not** at the same time.
        For example to jump to "V3" you have to press "V" and afterwards but within a time frame of 350ms
        you have to press "3".
        """
        try:
            from openlp.plugins.songs.lib import VerseType
            is_songs_plugin_available = True
        except ImportError:
            class VerseType(object):
                """
                This empty class is mostly just to satisfy Python, PEP8 and PyCharm
                """
                pass

            is_songs_plugin_available = False
        sender_name = self.sender().objectName()
        verse_type = sender_name[15:] if sender_name[:15] == 'shortcutAction_' else ''
        if is_songs_plugin_available:
            if verse_type == 'V':
                self.current_shortcut = VerseType.translated_tags[VerseType.Verse]
            elif verse_type == 'C':
                self.current_shortcut = VerseType.translated_tags[VerseType.Chorus]
            elif verse_type == 'B':
                self.current_shortcut = VerseType.translated_tags[VerseType.Bridge]
            elif verse_type == 'P':
                self.current_shortcut = VerseType.translated_tags[VerseType.PreChorus]
            elif verse_type == 'I':
                self.current_shortcut = VerseType.translated_tags[VerseType.Intro]
            elif verse_type == 'E':
                self.current_shortcut = VerseType.translated_tags[VerseType.Ending]
            elif verse_type == 'O':
                self.current_shortcut = VerseType.translated_tags[VerseType.Other]
            elif verse_type.isnumeric():
                self.current_shortcut += verse_type
            self.current_shortcut = self.current_shortcut.upper()
        elif verse_type.isnumeric():
            self.current_shortcut += verse_type
        elif verse_type:
            self.current_shortcut = verse_type
        keys = list(self.slide_list.keys())
        matches = [match for match in keys if match.startswith(self.current_shortcut)]
        if len(matches) == 1:
            self.shortcut_timer.stop()
            self.current_shortcut = ''
            self.preview_widget.change_slide(self.slide_list[matches[0]])
            self.slide_selected()
        elif sender_name != 'shortcut_timer':
            # Start the time as we did not have any match.
            self.shortcut_timer.start(350)
        else:
            # The timer timed out.
            if self.current_shortcut in keys:
                # We had more than one match for example "V1" and "V10", but
                # "V1" was the slide we wanted to go.
                self.preview_widget.change_slide(self.slide_list[self.current_shortcut])
                self.slide_selected()
            # Reset the shortcut.
            self.current_shortcut = ''

    def send_to_plugins(self, *args):
        """
        This is the generic function to send signal for control widgets, created from within other plugins
        This function is needed to catch the current controller

        :param args: Arguments to send to the plugins
        """
        sender = self.sender().objectName() if self.sender().objectName() else self.sender().text()
        controller = self
        Registry().execute('{text}'.format(text=sender), [controller, args])

    def set_live_hot_keys(self, parent=None):
        """
        Set the live hotkeys

        :param parent: The parent UI object for actions to be added to.
        """
        self.previous_service = create_action(parent, 'previousService',
                                              text=translate('OpenLP.SlideController', 'Previous Service'),
                                              can_shortcuts=True,
                                              context=QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut,
                                              category=self.category,
                                              triggers=self.service_previous)
        self.next_service = create_action(parent, 'nextService',
                                          text=translate('OpenLP.SlideController', 'Next Service'),
                                          can_shortcuts=True,
                                          context=QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut,
                                          category=self.category,
                                          triggers=self.service_next)

    def toggle_display(self, action):
        """
        Toggle the display settings triggered from remote messages.

        :param action: The blank action to be processed.
        """
        if action == 'blank' or action == 'hide':
            self.set_hide_mode(HideMode.Blank)
        elif action == 'theme':
            self.set_hide_mode(HideMode.Theme)
        elif action == 'desktop':
            self.set_hide_mode(HideMode.Screen)
        elif action == 'show':
            self.set_hide_mode(None)

    def service_previous(self):
        """
        Live event to select the previous service item from the service manager.
        """
        self.keypress_queue.append(ServiceItemAction.Previous)
        self._process_queue()

    def service_next(self):
        """
        Live event to select the next service item from the service manager.
        """
        self.keypress_queue.append(ServiceItemAction.Next)
        self._process_queue()

    def _process_queue(self):
        """
        Process the service item request queue.  The key presses can arrive
        faster than the processing so implement a FIFO queue.
        """
        # Make sure only one thread get in here. Just return if already locked.
        if self.keypress_queue and self.process_queue_lock.acquire(False):
            while len(self.keypress_queue):
                keypress_command = self.keypress_queue.popleft()
                if keypress_command == ServiceItemAction.Previous:
                    self.service_manager.previous_item()
                elif keypress_command == ServiceItemAction.PreviousLastSlide:
                    # Go to the last slide of the previous item
                    self.service_manager.previous_item(last_slide=True)
                else:
                    self.service_manager.next_item()
            self.process_queue_lock.release()

    def screen_size_changed(self):
        """
        Settings dialog has changed the screen size of adjust output and screen previews.
        """
        size = self.screens.current.display_geometry.size()
        if self.is_live and self.displays:
            for display in self.displays:
                display.resize(size)
        old_preview_width = self.preview_display.size().width()
        scale = old_preview_width / size.width()
        new_preview_size = size * scale
        self.ratio = self.screens.current.display_geometry.width() / self.screens.current.display_geometry.height()
        self.preview_display.resize(new_preview_size)
        self.slide_layout.set_aspect_ratio(self.ratio)
        self.on_controller_size_changed()

    def __add_actions_to_widget(self, widget):
        """
        Add actions to the widget specified by `widget`
        This defines the controls available when Live display has stolen focus.
        Examples of this happening: Clicking anything in the live window or certain single screen mode scenarios.
        Needles to say, blank to modes should not be removed from here.
        For some reason this required a test. It may be found in test_slidecontroller.py as
        "live_stolen_focus_shortcuts_test. If you want to modify things here, you must also modify them there. (Duh)

        :param widget: The UI widget for the actions
        """
        widget.addActions([
            self.previous_item, self.next_item,
            self.previous_service, self.next_service,
            self.show_screen,
            self.desktop_screen,
            self.theme_screen,
            self.blank_screen])

    def on_controller_size_changed(self, event=None):
        """
        Change layout of display control buttons when the controller size changes
        """
        self.log_debug('on_controller_size_changed is_event:{}'.format(event is not None))
        if self.is_live and self.ignore_toolbar_resize_events is False:
            spare_space = self.controller.width() - self.toolbar.size().width()
            if spare_space <= 0 and not self.hide_menu.isVisible():
                self.set_hide_mode_menu(narrow=True)
            # Add threshold to prevent flickering.
            elif spare_space > HIDE_MENU_THRESHOLD and self.hide_menu.isVisible() \
                    or spare_space > 0 and not self.hide_menu.isVisible():
                self.set_hide_mode_menu(narrow=False)

    def set_hide_mode_menu(self, narrow):
        """
        Set the wide or narrow hide mode menu

        :param compact: Use the narrow menu?
        """
        self.toolbar.set_widget_visible(NARROW_MENU, narrow)
        self.toolbar.set_widget_visible(WIDE_MENU, False)
        if self.service_item and self.service_item.is_text():
            self.toolbar.set_widget_visible(WIDE_MENU, not narrow)
        else:
            self.toolbar.set_widget_visible(NON_TEXT_MENU, not narrow)

    def receive_spin_delay(self):
        """
        Adjusts the value of the ``delay_spin_box`` to the given one.
        """
        self.delay_spin_box.setValue(self.settings.value('core/loop delay'))

    def update_slide_limits(self):
        """
        Updates the Slide Limits variable from the settings.
        """
        self.slide_limits = self.settings.value('advanced/slide limits')

    def enable_tool_bar(self, item):
        """
        Allows the toolbars to be reconfigured based on Controller Type and ServiceItem Type

        :param item: current service item being processed
        """
        if self.is_live:
            self.enable_live_tool_bar(item)
        else:
            self.enable_preview_tool_bar(item)

    def enable_live_tool_bar(self, item):
        """
        Allows the live toolbar to be customised

        :param item: The current service item
        """
        # Work-around for OS X, hide and then show the toolbar
        # See bug #791050
        self.toolbar.hide()
        self.mediabar.hide()
        self.song_menu.hide()
        self.toolbar.set_widget_visible(LOOP_LIST, False)
        self.toolbar.set_widget_visible('song_menu', False)
        # Set to narrow menu so we don't push the panel wider than it needs to be when adding new buttons
        self.set_hide_mode_menu(narrow=True)
        # Reset the button
        self.play_slides_once.setChecked(False)
        self.play_slides_once.setIcon(UiIcons().play_slides)
        self.play_slides_once.setText(UiStrings().PlaySlidesToEnd)
        self.play_slides_loop.setChecked(False)
        self.play_slides_loop.setIcon(UiIcons().loop)
        self.play_slides_loop.setText(UiStrings().PlaySlidesInLoop)
        if item.is_text():
            if self.settings.value('songs/display songbar') and not self.song_menu.menu().isEmpty():
                self.toolbar.set_widget_visible('song_menu', True)
        if item.is_capable(ItemCapabilities.CanLoop) and len(item.slides) > 1:
            self.toolbar.set_widget_visible(LOOP_LIST)
        if item.is_media() or item.is_capable(ItemCapabilities.HasBackgroundAudio):
            self.mediabar.show()
        self.previous_item.setVisible(not item.is_media())
        self.next_item.setVisible(not item.is_media())
        # Work-around for OS X, hide and then show the toolbar
        # See bug #791050
        self.toolbar.show()

    def enable_preview_tool_bar(self, item):
        """
        Allows the Preview toolbar to be customised

        :param item: The current service item
        """
        # Work-around for OS X, hide and then show the toolbar
        # See bug #791050
        self.toolbar.hide()
        self.mediabar.hide()
        self.toolbar.set_widget_visible('editSong', False)
        self.toolbar.set_widget_visible('clear', True)
        if item.is_capable(ItemCapabilities.CanEdit) and item.from_plugin:
            self.toolbar.set_widget_visible('editSong')
        elif item.is_media():
            self.mediabar.show()
        self.previous_item.setVisible(not item.is_media())
        self.next_item.setVisible(not item.is_media())
        # Work-around for OS X, hide and then show the toolbar
        # See bug #791050
        self.toolbar.show()

    def refresh_service_item(self, service_item=None):
        """
        Method to update the current service item
        """
        selected_row = self.selected_row
        if not service_item:
            service_item = self.service_item
        self._process_item(service_item, selected_row, True)
        self.slide_selected()

    def add_service_item(self, item):
        """
        Method to install the service item into the controller
        Called by plugins

        :param item: The current service item
        """
        slide_no = 0
        if self.song_edit:
            slide_no = self.selected_row
        self.song_edit = False
        self._process_item(item, slide_no)

    def replace_service_manager_item(self, item):
        """
        Replacement item following a remote edit.
        This action  also takes place when a song that is sent to live from Service Manager is edited.

        :param item: The current service item
        """
        if item == self.service_item:
            Registry().set_flag('replace service manager item', True)
            self._process_item(item, self.preview_widget.current_slide_number())
            Registry().set_flag('replace service manager item', False)

    def add_service_manager_item(self, item, slide_no):
        """
        Method to install the service item into the controller and request the correct toolbar for the plugin. Called by
        :class:`~openlp.core.ui.servicemanager.ServiceManager`

        :param item: The current service item
        :param slide_no: The slide number to select
        """
        # If no valid slide number is specified we take the first one, but we remember the initial value to see if we
        # should reload the song or not
        slide_num = slide_no
        if slide_no == -1:
            slide_num = 0
        # If service item is the same as the current one, only change slide
        if slide_no >= 0 and item == self.service_item:
            self.preview_widget.change_slide(slide_num)
            self.slide_selected()
        else:
            self._process_item(item, slide_num)
            if self.is_live and item.auto_play_slides_loop and item.timed_slide_interval > 0:
                self.play_slides_loop.setChecked(item.auto_play_slides_loop)
                self.delay_spin_box.setValue(int(item.timed_slide_interval))
                self.on_play_slides_loop()
            elif self.is_live and item.auto_play_slides_once and item.timed_slide_interval > 0:
                self.play_slides_once.setChecked(item.auto_play_slides_once)
                self.delay_spin_box.setValue(int(item.timed_slide_interval))
                self.on_play_slides_once()

    def set_background_image(self, image_path):
        """
        Reload the theme on displays.
        """
        # Set theme for preview
        self.preview_display.set_background_image(image_path)
        # Set theme for displays
        for display in self.displays:
            display.set_background_image(image_path)

    def on_theme_changed(self, var=None):
        """
        Reloads the service item

        :param var: Unused but needed to catch the theme_update_list event
        """
        if self.service_item and self.settings.value('themes/hot reload'):
            slide_num = self.preview_widget.current_slide_number()
            self._process_item(self.service_item, slide_num)

    def reload_theme(self):
        """
        Reload the theme on displays.
        """
        # Set theme for preview
        self.preview_display.reload_theme()
        # Set theme for displays
        for display in self.displays:
            display.reload_theme()

    def _set_theme(self, service_item):
        """
        Set up the theme from the service item.

        :param service_item: The current service item
        """
        # Get theme
        theme_data = service_item.get_theme_data()
        # Set theme for preview
        self.preview_display.set_theme(theme_data, service_item_type=service_item.service_item_type)
        # Set theme for displays
        for display in self.displays:
            display.set_theme(theme_data, service_item_type=service_item.service_item_type)

    def _process_item(self, service_item, slide_no, is_reloading=False):
        """
        Loads a ServiceItem into the system from ServiceManager. Display the slide number passed.

        :param service_item: The current service item
        :param slide_no: The slide number to select
        :param is_reloading: If the controller is reloading the current item, due to a display update (for example).
        """
        self.log_debug('_process_item start')
        self.on_stop_loop()
        self.ignore_toolbar_resize_events = True
        old_item = self.service_item
        # rest to allow the remote pick up verse 1 if large imaged
        self.selected_row = 0
        # take a copy not a link to the servicemanager copy.
        self.service_item = copy.copy(service_item)
        if self.is_live:
            # Reset screen capture before any api call can arrive
            self.screen_capture = None
            # If item transitions are on, make sure the delay is longer than the animation
            self.slide_changed_time = datetime.datetime.now()
            if self.settings.value('themes/item transitions') and self.service_item.get_transition_delay() < 1:
                self.slide_changed_time += datetime.timedelta(seconds=0.5)
        if self.service_item.is_command() and not self.service_item.is_media():
            # Prevent that the same presentation is started multiple times.
            if (old_item is None or old_item.sha256_file_hash != self.service_item.sha256_file_hash):
                Registry().execute(
                    '{text}_start'.format(text=self.service_item.name.lower()),
                    [self.service_item, self.is_live, self._current_hide_mode, slide_no])
            if self.service_item.is_capable(ItemCapabilities.ProvidesOwnTheme):
                self._set_theme(self.service_item)
        else:
            self._set_theme(self.service_item)
        self.info_label.setText("–  " + self.service_item.title)
        self.slide_list = {}
        # if the old item was text or images (ie doesn't provide its own display) and the new item provides its own
        # display then clear out the old item so that it doesn't flash momentarily when next showing text/image
        # An item provides its own display if the capability ProvidesOwnDisplay is set or if it's a media item
        old_item_provides_own_display = old_item and (old_item.is_capable(ItemCapabilities.ProvidesOwnDisplay) or
                                                      old_item.is_media())
        new_item_provides_own_display = (self.service_item.is_capable(ItemCapabilities.ProvidesOwnDisplay) or
                                         self.service_item.is_media())
        if self.is_live and not old_item_provides_own_display and new_item_provides_own_display:
            for display in self.displays:
                display.finish_with_current_item()
        # Prepare the new slides for text / image items
        row = 0
        width = self.main_window.control_splitter.sizes()[self.split]
        if self.service_item.is_text():
            self.preview_display.load_verses(self.service_item.rendered_slides)
            self.preview_display.show()
            for display in self.displays:
                display.load_verses(self.service_item.rendered_slides)
            # Replace the song menu so the verses match the song and are not cumulative
            if self.is_live:
                self.toolbar.remove_widget('song_menu')
                self.new_song_menu()
                self.toolbar.add_toolbar_widget(self.song_menu)
            for slide_index, slide in enumerate(self.service_item.display_slides):
                if not slide['verse'].isdigit():
                    # These tags are already translated.
                    verse_def = slide['verse']
                    verse_def = '{def1}{def2}'.format(def1=verse_def[0], def2=verse_def[1:])
                    two_line_def = '{def1}\n{def2}'.format(def1=verse_def[0], def2=verse_def[1:])
                    row = two_line_def
                    if verse_def not in self.slide_list:
                        self.slide_list[verse_def] = slide_index
                        if self.is_live:
                            self.song_menu.menu().addAction(verse_def, self.on_song_bar_handler)
                else:
                    row += 1
                    self.slide_list[str(row)] = row - 1
        else:
            if self.service_item.is_image():
                self.preview_display.load_images(self.service_item.slides)
                for display in self.displays:
                    display.load_images(self.service_item.slides)
            for _, _ in enumerate(self.service_item.slides):
                row += 1
                self.slide_list[str(row)] = row - 1
        self.preview_widget.replace_service_item(self.service_item, width, slide_no)
        # Tidy up aspects associated with the old item
        if old_item:
            new_item_has_background_video = self.service_item.is_capable(ItemCapabilities.HasBackgroundVideo) or \
                                            self.service_item.is_capable(ItemCapabilities.HasBackgroundStream)
            # Media Manager cannot play background videos on preview pane yet
            is_unsupported_preview_background = not self.is_live and new_item_has_background_video
            # Close the old item if it's not to be used by the new service item
            if not self.service_item.is_media() and (not self.service_item.requires_media() or
                                                     is_unsupported_preview_background):
                self.on_media_close()
            if old_item.is_command() and not old_item.is_media():
                Registry().execute('{name}_stop'.format(name=old_item.name.lower()), [old_item, self.is_live])
            # if the old item was media which hid the main display then need to reset it if new service item uses it
            if self.is_live and self._current_hide_mode is None and old_item.is_media() and not \
                    old_item.requires_media() and not self.service_item.is_capable(ItemCapabilities.ProvidesOwnDisplay):
                for display in self.displays:
                    display.show_display()
        self.enable_tool_bar(self.service_item)
        # Reset blanking if needed
        if old_item and self.is_live and (old_item.is_capable(ItemCapabilities.ProvidesOwnDisplay) or
                                          self.service_item.is_capable(ItemCapabilities.ProvidesOwnDisplay)):
            self._reset_blank(self.service_item.is_capable(ItemCapabilities.ProvidesOwnDisplay))
        if self.service_item.is_media() or self.service_item.requires_media():
            self._set_theme(self.service_item)
            if self.service_item.is_command():
                self.preview_display.load_verses(media_empty_song, True)
            self.on_media_start(self.service_item)
            # Try to get display back on top of media window asap. If the media window
            # is not loaded by the time _raise_displays is run, lyrics (web display)
            # will be under the media window (not good).
            self._raise_displays()
            QtCore.QTimer.singleShot(100, self._raise_displays)
            QtCore.QTimer.singleShot(500, self._raise_displays)
            QtCore.QTimer.singleShot(1000, self._raise_displays)
        self.slide_selected(True)
        if self.service_item.from_service:
            self.preview_widget.setFocus()
        if self.is_live:
            Registry().execute('slidecontroller_{item}_started'.format(item=self.type_prefix), [self.service_item])
            # Need to process events four times to get correct controller width
            for _ in range(4):
                self.application.process_events()
            self.ignore_toolbar_resize_events = False
            self.on_controller_size_changed()
            if not is_reloading and self.settings.value('core/auto unblank'):
                self.set_hide_mode(None)
        self.log_debug('_process_item end')

    def on_slide_selected_index(self, message):
        """
        Go to the requested slide

        :param message: remote message to be processed.
        """
        index = int(message[0])
        if not self.service_item:
            return
        if self.service_item.is_command():
            Registry().execute('{name}_slide'.format(name=self.service_item.name.lower()),
                               [self.service_item, self.is_live, index])
            self.update_preview()
            self.selected_row = index
        else:
            self.preview_widget.change_slide(index)
            self.slide_selected()

    def on_song_bar_handler(self):
        """
        Some song handler
        """
        request = self.sender().text()
        slide_no = self.slide_list[request]
        width = self.main_window.control_splitter.sizes()[self.split]
        self.preview_widget.replace_service_item(self.service_item, width, slide_no)
        self.slide_selected()

    def on_preview_resize(self, size):
        """
        Set the preview display's zoom factor based on the size relative to the display size
        """
        if size.width() <= 0:
            # A transient layout pass (e.g. a media manager dock/tab switch briefly
            # collapsing this panel) can report a width of 0 before settling. Skip it
            # rather than computing a zero scale; set_scale() would reject it anyway,
            # and a follow-up resize with the real size will correct things shortly.
            return
        display_with = 0
        for screen in self.screens:
            if screen.is_display:
                display_with = screen.display_geometry.width()
        if display_with == 0:
            ratio = 0.25
        else:
            ratio = float(size.width()) / display_with
        self.preview_display.set_scale(ratio)

    def on_slide_unblank(self):
        """
        Handle the slidecontroller unblank event.
        """
        if not Registry().get_flag('replace service manager item') is True:
            self.set_hide_mode(None)

    def on_show_display(self, checked=None):
        """
        Handle the blank screen button actions

        :param checked: the new state of the widget
        """
        self.set_hide_mode(None)

    def on_toggle_blank(self, checked=None):
        """
        Toggle the blank screen
        """
        if self._current_hide_mode == HideMode.Blank:
            self.set_hide_mode(None)
        else:
            self.set_hide_mode(HideMode.Blank)

    def on_blank_display(self, checked=None):
        """
        Handle the blank screen button actions

        :param checked: the new state of the of the widget
        """
        self.set_hide_mode(HideMode.Blank)

    def on_toggle_theme(self, checked=None):
        """
        Toggle the Theme screen
        """
        if self._current_hide_mode == HideMode.Theme:
            self.set_hide_mode(None)
        else:
            self.set_hide_mode(HideMode.Theme)

    def on_theme_display(self, checked=None):
        """
        Handle the Theme screen button

        :param checked: the new state of the of the widget
        """
        self.set_hide_mode(HideMode.Theme)

    def on_toggle_desktop(self, checked=None):
        """
        Toggle the desktop
        """
        if self._current_hide_mode == HideMode.Screen:
            self.set_hide_mode(None)
        else:
            self.set_hide_mode(HideMode.Screen)

    def on_hide_display(self, checked=None):
        """
        Handle the Hide screen button
        This enables the desktop screen.

        :param checked: the new state of the of the widget
        """
        self.set_hide_mode(HideMode.Screen)

    def set_hide_mode(self, hide_mode):
        """
        Blank/Hide the display screen (within a plugin if required).
        """
        self.log_debug('set_hide_mode: {old} -> {new} (live={live}, item={item})'.format(
            old=self._current_hide_mode, new=hide_mode, live=self.is_live,
            item=getattr(self.service_item, 'name', None) if self.service_item else None))
        self._current_hide_mode = hide_mode
        # Reflect the on-air state in the live indicator (red while the output is showing)
        if self.is_live:
            self.type_label.setProperty('onAir', 'false' if hide_mode else 'true')
            if is_ui_theme(UiThemes.Noir):
                # Blanked output is an explicit chip state, not just the absence of red
                if hide_mode == HideMode.Blank:
                    self.type_label.setText(translate('OpenLP.SlideController', 'Blanked'))
                elif hide_mode == HideMode.Theme:
                    self.type_label.setText(translate('OpenLP.SlideController', 'Theme'))
                elif hide_mode == HideMode.Screen:
                    self.type_label.setText(translate('OpenLP.SlideController', 'Hidden'))
                else:
                    self.type_label.setText(UiStrings().Live)
            self.type_label.style().unpolish(self.type_label)
            self.type_label.style().polish(self.type_label)
            # The Noir slide cards also change their accent with the on-air state
            self.preview_widget.viewport().update()
            # Anything interested in the output state (e.g. the status bar segment)
            # hears about the change without holding a reference to the controller
            Registry().execute('live_output_state_changed', hide_mode)
        # Update ui buttons
        if hide_mode is None:
            self.hide_menu.setDefaultAction(self.blank_screen)
            self.settings.setValue('core/screen blank', False)
        else:
            self.hide_menu.setDefaultAction(self.show_screen)
            self.settings.setValue('core/screen blank', True)
        self.show_screen.setChecked(hide_mode is None)
        self.blank_screen.setChecked(hide_mode == HideMode.Blank)
        self.theme_screen.setChecked(hide_mode == HideMode.Theme)
        self.desktop_screen.setChecked(hide_mode == HideMode.Screen)
        # Update plugin display. The per-plugin blank/unblank hooks are optional: only
        # plugins whose items drive their own display (e.g. presentations) register them,
        # so they are only fired when registered rather than logging a "not registered"
        # error for every other plugin.
        if self.service_item is not None:
            if hide_mode:
                if not self.service_item.is_command():
                    Registry().execute('live_display_hide', hide_mode)
                blank_event = '{text}_blank'.format(text=self.service_item.name.lower())
                if Registry().has_function(blank_event):
                    Registry().execute(blank_event, [self.service_item, self.is_live, hide_mode])
            else:
                if not self.service_item.is_command():
                    Registry().execute('live_display_show')
                unblank_event = '{text}_unblank'.format(text=self.service_item.name.lower())
                if Registry().has_function(unblank_event):
                    Registry().execute(unblank_event, [self.service_item, self.is_live])
        else:
            if hide_mode:
                Registry().execute('live_display_hide', hide_mode)
            else:
                Registry().execute('live_display_show')
        self.update_preview()
        # Update loop state
        self.on_toggle_loop()

    def on_slide_selected(self):
        """
        Slide selected in controller
        Note for some reason a dummy field is required.  Nothing is passed!
        """
        self.slide_selected()

    def slide_selected(self, start=False):
        """
        Generate the preview when you click on a slide. If this is the Live Controller also display on the screen.

        :param start:
        """
        row = self.preview_widget.current_slide_number()
        Registry().execute('slidecontroller_slide_selected', [self.service_item, self.is_live, row])
        # Only one thread should be in here at the time. If already locked just skip, since the update will be
        # done by the thread holding the lock. If it is a "start" slide, we must wait for the lock, but only for 0.2
        # seconds, since we don't want to cause a deadlock
        timeout = 0.2 if start else -1
        if not self.slide_selected_lock.acquire(start, timeout):
            if start:
                self.log_debug(f'Could not get lock in slide_selected after waiting {timeout}, skip to avoid deadlock.')
            return
        # If "click live slide to unblank" is enabled, unblank the display. And start = Item is sent to Live.
        # Note: If this if statement is placed at the bottom of this function instead of top slide transitions are lost.
        if (not start and
                self.is_live and
                self._current_hide_mode and
                self.settings.value('core/click live slide to unblank')):
            Registry().execute('slidecontroller_live_unblank')
        self.selected_row = 0
        if -1 < row < self.preview_widget.slide_count():
            if self.service_item.is_command():
                if self.is_live and not start:
                    Registry().execute('{text}_slide'.format(text=self.service_item.name.lower()),
                                       [self.service_item, self.is_live, row])
            else:
                for display in self.displays:
                    display.go_to_slide(row)
                if not self.service_item.is_text():
                    # reset the store used to display first image
                    self.service_item.bg_image_bytes = None
            self.selected_row = row
            self.update_preview()
            self.preview_widget.change_slide(row)
        if self.is_live:
            self.preview_widget.setFocus()
        # Release lock
        self.slide_selected_lock.release()

    def on_slide_change(self, row):
        """
        The slide has been changed. Update the slidecontroller accordingly

        :param row: Row to be selected
        """
        self.preview_widget.change_slide(row)
        self.update_preview()
        self.selected_row = row

    def update_preview(self):
        """
        This updates the preview frame, for example after changing a slide or using *Blank to Theme*.
        """
        self.log_debug('update_preview {text}'.format(text=self.screens.current))
        if self.is_live:
            self.screen_capture = None
            self.slide_changed_time = max(self.slide_changed_time, datetime.datetime.now())
        if self.service_item:
            if (self.is_live and self.current_hide_mode and
                    self.settings.value('core/live preview shows blank screen')):
                # If live, hidden and setting 'live preview shows blank screen' is active
                # blank the live preview panel.
                self.preview_display.hide_display(self.current_hide_mode)
            if self.service_item.is_capable(ItemCapabilities.ProvidesOwnDisplay):
                if (self.is_live and not self.current_hide_mode):
                    # If live and not hidden grab screen-cap of main display in case the service item
                    # provides it's own display.
                    wait_for(self.is_slide_loaded)
                    self.display_maindisplay()
                elif not self.settings.value('core/live preview shows blank screen'):
                    # If not live and setting 'live preview shows blank screen' is not active,
                    # use the slide's thumbnail/icon instead in case the service item
                    # provides it's own display.
                    image_path = Path(self.service_item.get_rendered_frame(self.selected_row))
                    self.screen_capture = image_path
                    self.preview_display.set_single_image('#000', image_path)
            else:
                self.preview_display.go_to_slide(self.selected_row)
            if (not self.current_hide_mode and self.preview_display.hide_mode):
                self.preview_display.show_display()
        self.update_slide_count_label()
        # Used for updating the main view in Web Remote.
        self.output_has_changed()

    def update_slide_count_label(self):
        """
        Update the "current / total" slide position indicator in the panel header.
        Only the Noir theme shows this label.
        """
        if not is_ui_theme(UiThemes.Noir):
            return
        try:
            total = int(self.preview_widget.slide_count())
            current = int(self.preview_widget.current_slide_number()) + 1
        except (TypeError, ValueError):
            return
        if total > 0 and current > 0:
            self.slide_count_label.setText('{current} / {total}'.format(current=current, total=total))
        else:
            self.slide_count_label.setText('')

    def output_has_changed(self):
        """
        The output has changed so we need to poke to POLL Websocket.
        """
        self.slide_count += 1
        self.slidecontroller_changed.emit()

    def display_maindisplay(self):
        """
        Gets an image of the display screen and updates the preview frame.
        """
        display_image = self._capture_maindisplay()
        # display_image.setDevicePixelRatio(self.preview_display.devicePixelRatio())
        base64_image = image_to_byte(display_image)
        self.screen_capture = base64_image
        self.preview_display.set_single_image_data('#000', base64_image)

    def _capture_maindisplay(self):
        """
        Creates an image of the current screen.
        """
        self.log_debug('_capture_maindisplay {text}'.format(text=self.screens.current))
        # Wayland needs screenshot fallback even when OpenLP is running on X11/xcb mode.
        fallback_to_windowed = is_wayland_compositor() or \
                               self.settings.value('advanced/prefer windowed screen capture')
        if not fallback_to_windowed:
            # Check if display screen is outside real screen bounds
            # OpenLP can't take reliable screenshots when any of these conditions happens
            # See last warning in grabWindow at https://doc.qt.io/qt-6/qscreen.html#grabWindow
            display_rect = ScreenList().current.display_geometry
            screen_rect = ScreenList().current.geometry
            display_above_horizontal = display_rect.left() < screen_rect.left()
            display_above_vertical = display_rect.top() < screen_rect.top()
            display_beyond_horizontal = (display_rect.left() + display_rect.width() >
                                         screen_rect.left() + screen_rect.width())
            display_beyond_vertical = (display_rect.top() + display_rect.height() >
                                       screen_rect.top() + screen_rect.height())
            fallback_to_windowed = display_above_horizontal or display_above_vertical \
                                   or display_beyond_horizontal or display_beyond_vertical
        if fallback_to_windowed:
            if self.service_item and (self.service_item.is_capable(ItemCapabilities.ProvidesOwnDisplay) or
                                      self.service_item.is_media() or self.service_item.is_command()):
                if self.service_item.is_command():
                    # Attempting to get screenshot from command handler
                    service_item_name = self.service_item.name.lower()
                    event_name = '{text}_attempt_screenshot'.format(text=service_item_name)
                    if Registry().has_function(event_name):
                        results = Registry().execute(event_name, [self.service_item, self.selected_row])
                        if len(results):
                            succedded, binary_data = results[0]
                            if succedded and binary_data:
                                self.log_debug('_capture_maindisplay using window capture from {name}'
                                               .format(name=service_item_name))
                                return binary_data
                # Falling back to desktop capture, maybe it works
                self.log_debug('_capture_maindisplay cannot do window capture, trying to get screenshot from screen'
                               ' anyway')
                return self._capture_maindisplay_desktop()
            else:
                self.log_debug('_capture_maindisplay falling back to window capture')
                return self._capture_maindisplay_window()
        else:
            return self._capture_maindisplay_desktop()

    def _capture_maindisplay_desktop(self):
        current_screen = ScreenList().current
        display_rect = current_screen.display_geometry
        screen_rect = current_screen.geometry
        # As we capture using current screen object, we need relative coordinates.
        # (OpenLP is storing screen positions like a big one-screen, and we can't change this without
        # disrupting existing users)
        relative_x = display_rect.x() - screen_rect.x()
        relative_y = display_rect.y() - screen_rect.y()
        width = display_rect.width()
        height = display_rect.height()
        win_image = current_screen.try_grab_screen_part(relative_x, relative_y, width, height)
        return win_image

    def _capture_maindisplay_window(self):
        win_image = None
        for display in self.displays:
            if display.is_display:
                if display.hide_mode == HideMode.Screen or display.hide_mode == HideMode.Blank:
                    # Sending a black image to avoid artifacts
                    size = display.size()
                    win_image = QtGui.QPixmap(size)
                    win_image.fill(QtGui.QColorConstants.Black)
                else:
                    win_image = display.grab_screenshot_safe()
                    if win_image:
                        win_image.setDevicePixelRatio(self.preview_display.devicePixelRatio())
                break
        return win_image

    def is_slide_loaded(self):
        """
        Returns a boolean as to whether the slide should be fully visible.
        Takes transition time into consideration.
        """
        slide_delay_time = 0
        if self.service_item:
            slide_delay_time = self.service_item.get_transition_delay() if self.get_hide_mode() is None else 1
        slide_ready_time = self.slide_changed_time + datetime.timedelta(seconds=slide_delay_time)
        return datetime.datetime.now() > slide_ready_time

    @QtCore.Slot(result=str)
    def grab_maindisplay(self) -> str:
        """
        Gets the last taken screenshot
        """
        wait_for(lambda: not self.fetching_screenshot)
        if self.screen_capture is None or isinstance(self.screen_capture, PurePath):
            self.fetching_screenshot = True
            wait_for(self.is_slide_loaded)
            self.screen_capture = image_to_byte(self._capture_maindisplay())
            self.fetching_screenshot = False
        return self.screen_capture

    def on_slide_selected_next_action(self, checked):
        """
        Wrapper function from create_action so we can throw away the incorrect parameter

        :param checked: the new state of the of the widget
        """
        self.on_slide_selected_next()

    def on_slide_selected_next(self, wrap=None):
        """
        Go to the next slide.

        :param wrap: Are we wrapping round the service item
        """
        if not self.service_item:
            return
        if self.service_item.is_command():
            past_end = Registry().execute('{text}_next'.format(text=self.service_item.name.lower()),
                                          [self.service_item, self.is_live])
            # Check if we have gone past the end of the last slide
            if self.is_live and past_end and past_end[0]:
                if wrap is None:
                    if self.slide_limits == SlideLimits.Wrap:
                        self.on_slide_selected_index([0])
                    elif self.is_live and self.slide_limits == SlideLimits.Next:
                        self.service_next()
                elif wrap:
                    self.on_slide_selected_index([0])
            elif self.is_live:
                self.update_preview()
        else:
            row = self.preview_widget.current_slide_number() + 1
            if row == self.preview_widget.slide_count():
                if wrap is None:
                    if self.slide_limits == SlideLimits.Wrap:
                        row = 0
                    elif self.is_live and self.slide_limits == SlideLimits.Next:
                        self.service_next()
                        return
                    else:
                        row = self.preview_widget.slide_count() - 1
                elif wrap:
                    row = 0
                else:
                    row = self.preview_widget.slide_count() - 1
            self.preview_widget.change_slide(row)
            self.slide_selected()

    def on_slide_selected_previous(self):
        """
        Go to the previous slide.
        """
        if not self.service_item:
            return
        if self.service_item.is_command():
            before_start = Registry().execute('{text}_previous'.format(text=self.service_item.name.lower()),
                                              [self.service_item, self.is_live])
            # Check id we have tried to go before that start slide
            if self.is_live and before_start and before_start[0]:
                if self.slide_limits == SlideLimits.Wrap:
                    self.on_slide_selected_index([self.preview_widget.slide_count() - 1])
                elif self.is_live and self.slide_limits == SlideLimits.Next:
                    self.keypress_queue.append(ServiceItemAction.PreviousLastSlide)
                    self._process_queue()
            elif self.is_live:
                self.update_preview()
        else:
            row = self.preview_widget.current_slide_number() - 1
            if row == -1:
                if self.slide_limits == SlideLimits.Wrap:
                    row = self.preview_widget.slide_count() - 1
                elif self.is_live and self.slide_limits == SlideLimits.Next:
                    self.keypress_queue.append(ServiceItemAction.PreviousLastSlide)
                    self._process_queue()
                    return
                else:
                    row = 0
            self.preview_widget.change_slide(row)
            self.slide_selected()

    def on_toggle_loop(self):
        """
        Toggles the loop state.
        """
        if self._current_hide_mode is None and (self.play_slides_loop.isChecked() or self.play_slides_once.isChecked()):
            self.on_start_loop()
        else:
            self.on_stop_loop()

    def on_start_loop(self):
        """
        Start the timer loop running and store the timer id
        """
        if self.preview_widget.slide_count() > 1:
            self.timer_id = self.startTimer(int(self.delay_spin_box.value()) * 1000)

    def on_stop_loop(self):
        """
        Stop the timer loop running
        """
        if self.timer_id:
            self.killTimer(self.timer_id)
            self.timer_id = 0

    def on_play_slides_loop(self, checked=None):
        """
        Start or stop 'Play Slides in Loop'

        :param checked: is the check box checked.
        """
        if checked is None:
            checked = self.play_slides_loop.isChecked()
        else:
            self.play_slides_loop.setChecked(checked)
        self.log_debug('on_play_slides_loop {text}'.format(text=checked))
        if checked:
            self.play_slides_loop.setIcon(UiIcons().stop)
            self.play_slides_loop.setText(UiStrings().StopPlaySlidesInLoop)
            self.play_slides_once.setIcon(UiIcons().play_slides)
            self.play_slides_once.setText(UiStrings().PlaySlidesToEnd)
            self.play_slides_menu.setDefaultAction(self.play_slides_loop)
            self.play_slides_once.setChecked(False)
            if self.settings.value('core/click live slide to unblank'):
                Registry().execute('slidecontroller_live_unblank')
        else:
            self.play_slides_loop.setIcon(UiIcons().loop)
            self.play_slides_loop.setText(UiStrings().PlaySlidesInLoop)
        self.on_toggle_loop()

    def on_play_slides_once(self, checked=None):
        """
        Start or stop 'Play Slides to End'

        :param checked: is the check box checked.
        """
        if checked is None:
            checked = self.play_slides_once.isChecked()
        else:
            self.play_slides_once.setChecked(checked)
        self.log_debug('on_play_slides_once {text}'.format(text=checked))
        if checked:
            self.play_slides_once.setIcon(UiIcons().stop)
            self.play_slides_once.setText(UiStrings().StopPlaySlidesToEnd)
            self.play_slides_loop.setIcon(UiIcons().loop)
            self.play_slides_loop.setText(UiStrings().PlaySlidesInLoop)
            self.play_slides_menu.setDefaultAction(self.play_slides_once)
            self.play_slides_loop.setChecked(False)
            if self.settings.value('core/click live slide to unblank'):
                Registry().execute('slidecontroller_live_unblank')
        else:
            self.play_slides_once.setIcon(UiIcons().play_slides)
            self.play_slides_once.setText(UiStrings().PlaySlidesToEnd)
        self.on_toggle_loop()

    def timerEvent(self, event):
        """
        If the timer event is for this window select next slide

        :param event: The triggered event
        """
        if event.timerId() == self.timer_id:
            self.on_slide_selected_next(self.play_slides_loop.isChecked())

    def on_edit_song(self):
        """
        From the preview display requires the service Item to be editied
        """
        self.song_edit = True
        new_item = Registry().get(self.service_item.name).on_remote_edit(self.service_item.edit_id, True)
        if new_item:
            self.add_service_item(new_item)

    def on_clear(self):
        """
        Clear the preview bar and other bits.
        """
        self.preview_widget.clear_list()
        self.service_item = None
        if self.is_live:
            self.mediabar.setVisible(False)
        else:
            self.toolbar.set_widget_visible('editSong', False)
            self.toolbar.set_widget_visible('clear', False)

    def on_preview_add_to_service(self):
        """
        From the preview display request the Item to be added to service
        """
        if self.service_item:
            self.service_manager.add_service_item(self.service_item)

    def on_preview_double_click(self):
        """
        Triggered when a preview slide item is double clicked
        """
        if self.service_item:
            if self.settings.value('advanced/double click live'):
                # Live and Preview have issues if we have video or presentations
                # playing in both at the same time.
                if self.service_item.is_command():
                    Registry().execute('{text}_stop'.format(text=self.service_item.name.lower()),
                                       [self.service_item, self.is_live])
                if self.service_item.is_media():
                    self.on_media_close()
                self.on_go_live()
            # If ('advanced/double click live') is not enabled, double clicking preview adds the item to Service.
            # Prevent same item in preview from being sent to Service multiple times.
            # Changing the preview slide resets this flag to False.
            # Do note that this still allows to add item to Service multiple times if icon is clicked.
            elif not Registry().get_flag('has doubleclick added item to service') is True:
                self.on_preview_add_to_service()
                Registry().set_flag('has doubleclick added item to service', True)

    def on_go_live(self, field=None):
        """
        If preview copy slide item to live controller from Preview Controller
        """
        row = self.preview_widget.current_slide_number()
        if -1 < row < self.preview_widget.slide_count():
            if self.service_item.from_service:
                self.service_manager.preview_live(self.service_item.unique_identifier, row)
            else:
                self.live_controller.add_service_manager_item(self.service_item, row)
            self.live_controller.preview_widget.setFocus()

    def on_media_start(self, item):
        """
        Respond to the arrival of a media service item but only run if we have media

        :param item: The service item to be processed
        """
        if State().check_preconditions('media'):
            theme_data = item.get_theme_data()
            is_theme_background = BackgroundType.from_string(theme_data.background_type) in [BackgroundType.Stream,
                                                                                             BackgroundType.Video]
            if self.is_live and not item.is_media() and item.requires_media():
                self.media_controller.load_media(self.controller_type, item, self._current_hide_mode,
                                                 is_theme_background)
            elif self.is_live:
                if self._current_hide_mode == HideMode.Theme:
                    self.set_hide_mode(HideMode.Blank)
                self.media_controller.load_media(self.controller_type, item, self._current_hide_mode, False)
            elif item.is_media():
                self.media_controller.load_media(self.controller_type, item)
            if not self.is_live:
                self.preview_display.show()

    def on_media_close(self):
        """
        Respond to a request to close the Video if we have media
        """
        if State().check_preconditions('media'):
            self.media_controller.media_reset(self, delayed=True)

    def _reset_blank(self, no_theme):
        """
        Used by command items which provide their own displays to reset the screen hide attributes

        :param no_theme: Does the new item support theme-blanking.
        """
        if self._current_hide_mode == HideMode.Theme and no_theme:
            # The new item-type doesn't support theme-blanking, so 'switch' to normal blanking.
            self.set_hide_mode(HideMode.Blank)
        else:
            self.set_hide_mode(self._current_hide_mode)

    def get_hide_mode(self):
        """
        Determine what the hide mode should be according to the blank button
        """
        return self.current_hide_mode if self.is_live else None


class PreviewController(RegistryBase, SlideController):
    """
    Set up the Preview Controller.
    """
    slidecontroller_preview_set = QtCore.Signal(list)
    slidecontroller_preview_next = QtCore.Signal()
    slidecontroller_preview_previous = QtCore.Signal()
    slidecontroller_preview_clear = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        """
        Set up the base Controller as a preview.
        """
        self.__registry_name = 'preview_controller'
        super().__init__(*args, **kwargs)
        self.split = 0
        self.type_prefix = 'preview'
        self.category = 'Preview Toolbar'

    def bootstrap_initialise(self):
        """
        process the bootstrap initialise request
        """
        self.initialise()

    def bootstrap_post_set_up(self):
        """
        process the bootstrap post setup request
        """
        self.post_set_up()


class LiveController(RegistryBase, SlideController):
    """
    Set up the Live Controller.
    """
    slidecontroller_live_set = QtCore.Signal(list)
    slidecontroller_live_next = QtCore.Signal()
    slidecontroller_live_previous = QtCore.Signal()
    slidecontroller_toggle_display = QtCore.Signal(str)
    slidecontroller_live_clear = QtCore.Signal()
    mediacontroller_live_play = QtCore.Signal()
    mediacontroller_live_pause = QtCore.Signal()
    mediacontroller_live_stop = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        """
        Set up the base Controller as a live.
        """
        self.__registry_name = 'live_controller'
        super().__init__(*args, **kwargs)
        self.is_live = True
        self.split = 1
        self.type_prefix = 'live'
        self.keypress_queue = deque()
        self.category = UiStrings().LiveToolbar
        ActionList.get_instance().add_category(str(self.category), CategoryOrder.standard_toolbar)

    def bootstrap_initialise(self):
        """
        process the bootstrap initialise request
        """
        self.initialise()

    def bootstrap_post_set_up(self):
        """
        process the bootstrap post setup request
        """
        self.post_set_up()
