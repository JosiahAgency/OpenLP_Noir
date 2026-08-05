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
The :mod:`~openlp.core.ui.dark` module looks for and loads a dark theme
"""
import logging
import tempfile
from enum import Enum
from pathlib import Path
from subprocess import Popen, PIPE

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common.platform import is_macosx, is_win
from openlp.core.common.registry import Registry

try:
    import qdarkstyle

    HAS_DARK_THEME = True
except ImportError:
    HAS_DARK_THEME = False

log = logging.getLogger(__name__)

WIN_REPAIR_STYLESHEET = """
QMainWindow::separator
{
  border: none;
}

QDockWidget::title
{
  border: 1px solid palette(dark);
  padding-left: 5px;
  padding-top: 2px;
  margin: 1px 0;
}

QToolBar
{
  border: none;
  margin: 0;
  padding: 0;
}
"""

MEDIA_MANAGER_STYLE = """
::tab#media_tool_box {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 palette(button), stop: 1.0 palette(mid));
    border: 0;
    border-radius: 2px;
    margin-top: 0;
    margin-bottom: 0;
    text-align: left;
}
/* This is here to make the tabs on KDE with the Breeze theme work */
::tab:selected {}
"""

PROGRESSBAR_STYLE = """
QProgressBar{
    height: 10px;
}
"""

# Noir theme tokens. A five-value cool-biased ink ramp with a single "cue" accent
# reserved for selection, focus and live state, plus an on-air red used only for
# live output that is actually showing. Success/warning are muted so the cue and
# on-air colors stay the loudest things on screen.
NOIR_INK_0 = '#0E1014'
NOIR_INK_1 = '#14171C'
NOIR_INK_2 = '#1B1F26'
NOIR_INK_3 = '#242933'
NOIR_INK_4 = '#303743'
NOIR_LINE = '#262C36'
NOIR_LINE_SOFT = '#2E3542'
NOIR_TEXT_HI = '#E8EBF0'
NOIR_TEXT_BODY = '#C7CDD8'
NOIR_TEXT_MID = '#9AA3B2'
NOIR_TEXT_LOW = '#5C6675'
NOIR_CUE = '#4D9FFF'
NOIR_CUE_HOVER = '#71B4FF'
NOIR_CUE_DIM = 'rgba(77, 159, 255, 0.14)'
NOIR_CUE_LINE = 'rgba(77, 159, 255, 0.45)'
NOIR_ON_AIR = '#C13A30'
NOIR_ON_AIR_DIM = 'rgba(193, 58, 48, 0.14)'
NOIR_ON_AIR_LINE = 'rgba(193, 58, 48, 0.55)'
NOIR_SUCCESS = '#4CB782'
NOIR_WARNING = '#D9A23C'
# Interaction accents that fall outside the ink ramp: the scrollbar/splitter
# grip hover, and the text color painted on top of the on-air red.
NOIR_LINE_HOVER = '#3A4250'
NOIR_TEXT_ON_ACCENT = '#FFFFFF'
# Per-plugin identity accents, used for icon tint and service-list chip tint.
# Muted (lower saturation) vs NOIR_CUE/NOIR_ON_AIR so plugin colour never
# competes with selection/live-state signalling.
NOIR_PLUGIN_SONGS = '#7E79C8'
NOIR_PLUGIN_BIBLES = '#5BB5B9'
NOIR_PLUGIN_PRESENTATIONS = '#9E7EC8'
NOIR_PLUGIN_MEDIA = '#B77BC6'
NOIR_PLUGIN_IMAGES = '#C775B9'
NOIR_PLUGIN_CUSTOM = '#C46E96'
NOIR_PLUGIN_ALERTS = '#91B356'
NOIR_PLUGIN_LIBRARY = '#62AF5A'
NOIR_PLUGIN_COLORS = {
    'songs': NOIR_PLUGIN_SONGS,
    'bibles': NOIR_PLUGIN_BIBLES,
    'presentations': NOIR_PLUGIN_PRESENTATIONS,
    'media': NOIR_PLUGIN_MEDIA,
    'images': NOIR_PLUGIN_IMAGES,
    'custom': NOIR_PLUGIN_CUSTOM,
    'alerts': NOIR_PLUGIN_ALERTS,
    'egwlibrary': NOIR_PLUGIN_LIBRARY,
}
# Verse-type tints for the idle rail pill in NoirSlideDelegate, keyed by the
# uppercase first letter of the (translated) verse tag.
NOIR_VERSE_VERSE = '#8477C5'
NOIR_VERSE_CHORUS = '#CA7DCA'
NOIR_VERSE_BRIDGE = '#A77BC6'
NOIR_VERSE_PRE_CHORUS = '#7CB262'
NOIR_VERSE_INTRO = '#5DB3B6'
NOIR_VERSE_ENDING = '#C67BA7'
NOIR_VERSE_TAG_COLORS = {
    'V': NOIR_VERSE_VERSE,
    'C': NOIR_VERSE_CHORUS,
    'B': NOIR_VERSE_BRIDGE,
    'P': NOIR_VERSE_PRE_CHORUS,
    'I': NOIR_VERSE_INTRO,
    'E': NOIR_VERSE_ENDING,
}
# Preferred UI font families, best first. Lato ships with OpenLP (see
# BUNDLED_FONT_DIR) so it is always available; the rest of the list is a
# fallback for the unlikely case the bundled files fail to register.
NOIR_FONT_FAMILIES = ['Lato', 'Segoe UI Variable Text', 'Segoe UI', 'Inter', 'Roboto', 'Noto Sans',
                      'Cantarell']
# Type scale. Body is the application font set in set_noir_palette(); the
# named steps below are interpolated into NOIR_STYLESHEET so every panel
# label, section header and title stays on the same four-step scale.
NOIR_TYPE_BODY_PT = 10.0
NOIR_TYPE_CAPTION = '8pt'
NOIR_TYPE_SECTION = '11pt'

NOIR_STYLESHEET = """
/* ------------------------------ Window chrome ------------------------------ */
QMainWindow::separator {{
    border: none;
    background: {ink1};
    width: 3px;
    height: 3px;
}}

QDockWidget::title {{
    background: {ink1};
    border: none;
    border-bottom: 1px solid {line};
    padding: 6px 12px 5px 12px;
    color: {text_mid};
    font-size: {type_caption};
    font-weight: 600;
}}

QMenuBar {{
    background: {ink1};
    border-bottom: 1px solid {line};
    padding: 1px 4px;
}}

QMenuBar::item {{
    background: transparent;
    color: {text_mid};
    padding: 5px 10px;
    border-radius: 6px;
}}

QMenuBar::item:selected {{
    background: {ink3};
    color: {text_hi};
}}

QMenuBar::item:pressed {{
    background: {ink4};
    color: {text_hi};
}}

QMenu {{
    background: {ink2};
    border: 1px solid {line_soft};
    border-radius: 8px;
    padding: 5px;
}}

QMenu::item {{
    background: transparent;
    color: {text_body};
    padding: 6px 26px 6px 10px;
    border-radius: 5px;
}}

QMenu::item:selected {{
    background: {ink4};
    color: {text_hi};
}}

QMenu::item:disabled {{
    color: {text_low};
}}

QMenu::separator {{
    height: 1px;
    background: {line};
    margin: 5px 8px;
}}

QToolTip {{
    background: {ink3};
    color: {text_hi};
    border: 1px solid {line_soft};
    border-radius: 6px;
    padding: 5px 8px;
}}

QStatusBar {{
    background: {ink1};
    border-top: 1px solid {line};
    color: {text_mid};
}}

QStatusBar::item {{
    border: none;
}}

QSplitter::handle {{
    background: transparent;
}}

QSplitter::handle:hover, QMainWindow::separator:hover {{
    background: {ink4};
}}

/* -------------------------------- Toolbars -------------------------------- */
QToolBar {{
    border: none;
    background: transparent;
    margin: 0;
    padding: 2px;
    spacing: 2px;
}}

QToolBar::separator {{
    background: {line};
    width: 1px;
    height: 1px;
    margin: 5px 6px;
}}

QToolBar QToolButton {{
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 3px;
    background: transparent;
    color: {text_body};
}}

QToolBar QToolButton:hover {{
    background: {ink4};
    color: {text_hi};
}}

QToolBar QToolButton:focus {{
    border-color: {cue_line};
}}

QToolBar QToolButton:pressed {{
    background: {ink2};
}}

QToolBar QToolButton:checked {{
    background: {cue_dim};
    border: 1px solid {cue_line};
}}

/* --------------------------------- Buttons --------------------------------- */
QPushButton {{
    background: {ink3};
    color: {text_hi};
    border: 1px solid {line_soft};
    border-radius: 6px;
    padding: 5px 14px;
}}

QPushButton:hover {{
    background: {ink4};
}}

QPushButton:pressed {{
    background: {ink2};
}}

QPushButton:checked {{
    background: {cue_dim};
    border-color: {cue_line};
}}

QPushButton:focus {{
    border-color: {cue_line};
}}

QPushButton:disabled {{
    background: {ink2};
    color: {text_low};
    border-color: {line};
}}

QPushButton:default {{
    background: {cue};
    color: {ink0};
    border: 1px solid {cue};
}}

QPushButton:default:hover {{
    background: {cue_hover};
}}

QPushButton:flat {{
    background: transparent;
    border: none;
}}

QPushButton:flat:hover {{
    background: {ink3};
}}

/* ---------------------------------- Inputs --------------------------------- */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit,
QTimeEdit, QDateTimeEdit, QKeySequenceEdit, QFontComboBox, QComboBox {{
    background: {ink3};
    border: 1px solid {line_soft};
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: {cue};
    selection-color: {ink0};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus,
QKeySequenceEdit:focus, QComboBox:focus {{
    border: 1px solid {cue};
}}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QSpinBox:disabled,
QDoubleSpinBox:disabled, QComboBox:disabled {{
    background: {ink2};
    color: {text_low};
    border-color: {line};
}}

QComboBox {{
    padding-right: 26px;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 24px;
    border: none;
}}

QComboBox QAbstractItemView {{
    background: {ink2};
    border: 1px solid {line_soft};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {ink4};
    selection-color: {text_hi};
}}

QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button,
QDoubleSpinBox::down-button, QDateEdit::up-button, QDateEdit::down-button,
QTimeEdit::up-button, QTimeEdit::down-button, QDateTimeEdit::up-button,
QDateTimeEdit::down-button {{
    background: transparent;
    border: none;
    border-radius: 4px;
    width: 18px;
    margin: 1px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::up-button:hover,
QDoubleSpinBox::down-button:hover, QDateEdit::up-button:hover, QDateEdit::down-button:hover,
QTimeEdit::up-button:hover, QTimeEdit::down-button:hover, QDateTimeEdit::up-button:hover,
QDateTimeEdit::down-button:hover {{
    background: {ink4};
}}

/* ---------------------------- Checks and radios ---------------------------- */
QCheckBox, QRadioButton {{
    spacing: 8px;
}}

QCheckBox::indicator, QGroupBox::indicator, QListView::indicator, QListWidget::indicator,
QTreeView::indicator, QTreeWidget::indicator, QTableView::indicator, QTableWidget::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {ink4};
    background: {ink3};
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 1px solid {ink4};
    background: {ink3};
}}

QCheckBox::indicator:hover, QRadioButton::indicator:hover, QGroupBox::indicator:hover {{
    border-color: {cue_line};
}}

QCheckBox::indicator:checked, QGroupBox::indicator:checked, QListView::indicator:checked,
QListWidget::indicator:checked, QTreeView::indicator:checked, QTreeWidget::indicator:checked,
QTableView::indicator:checked, QTableWidget::indicator:checked {{
    background: {cue};
    border-color: {cue};
}}

QRadioButton::indicator:checked {{
    border-color: {cue};
}}

QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
    background: {ink2};
    border-color: {line};
}}

/* ----------------------------------- Tabs ---------------------------------- */
QTabWidget::pane {{
    border: 1px solid {line};
    border-radius: 8px;
    top: -1px;
}}

QTabBar::tab {{
    background: transparent;
    color: {text_mid};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 7px 16px;
    margin-right: 2px;
}}

QTabBar::tab:hover {{
    color: {text_hi};
}}

QTabBar::tab:selected {{
    color: {text_hi};
    border-bottom: 2px solid {cue};
}}

/* ------------------------------- Group boxes ------------------------------- */
QGroupBox {{
    background: {ink2};
    border: 1px solid {line};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {text_mid};
    font-weight: 600;
}}

/* -------------------------------- Item views ------------------------------- */
QHeaderView::section {{
    background: {ink1};
    color: {text_mid};
    border: none;
    border-bottom: 1px solid {line};
    padding: 5px 8px;
    font-weight: 600;
}}

QListView, QListWidget, QTreeView, QTreeWidget, QTableView, QTableWidget {{
    background: {ink0};
    alternate-background-color: {ink1};
    border: 1px solid {line};
    border-radius: 8px;
    padding: 2px;
}}

/* Keyboard focus is load-bearing during live operation: the panel that will
   receive the next keystroke gets a soft cue outline. */
QListView:focus, QListWidget:focus, QTreeView:focus, QTreeWidget:focus,
QTableView:focus, QTableWidget:focus {{
    border: 1px solid {cue_line};
}}

QListView::item, QListWidget::item, QTreeView::item, QTreeWidget::item {{
    padding: 6px 8px;
    border-radius: 6px;
    margin: 1px 3px;
    color: {text_body};
}}

QListView::item:hover, QListWidget::item:hover, QTreeView::item:hover, QTreeWidget::item:hover {{
    background: {ink2};
    color: {text_hi};
}}

QListView::item:selected, QListWidget::item:selected, QTreeView::item:selected,
QTreeWidget::item:selected {{
    background: {cue_dim};
    border-left: 2px solid {cue};
    padding: 6px 8px 6px 6px;
    color: {text_hi};
}}

QListView::item:selected:!active, QListWidget::item:selected:!active,
QTreeView::item:selected:!active, QTreeWidget::item:selected:!active {{
    background: {ink3};
    border-left: 2px solid {line_soft};
    padding: 6px 8px 6px 6px;
}}

QListView::item:pressed, QListWidget::item:pressed, QTreeView::item:pressed, QTreeWidget::item:pressed,
QTableView::item:pressed, QTableWidget::item:pressed {{
    background: {ink4};
}}

QTableView::item, QTableWidget::item {{
    padding: 4px 6px;
    border-radius: 6px;
    margin: 1px 2px;
}}

QTableView::item:hover, QTableWidget::item:hover {{
    background: {ink2};
}}

QTableView::item:selected, QTableWidget::item:selected {{
    background: {cue_dim};
    border-left: 2px solid {cue};
    padding: 4px 6px 4px 4px;
}}

QTableView::item:selected:!active, QTableWidget::item:selected:!active {{
    background: {ink3};
    border-left: 2px solid {line_soft};
    padding: 4px 6px 4px 4px;
}}

QTreeView::branch {{
    background: transparent;
}}

QTreeView::branch:selected, QTreeView::branch:hover {{
    background: transparent;
}}

/* The service list is painted entirely by NoirServiceDelegate: the generic
   item-view backgrounds above would show as square underlays behind the
   rounded cards, so they are switched off here. */
QTreeWidget#service_manager_list::item,
QTreeWidget#service_manager_list::item:hover,
QTreeWidget#service_manager_list::item:selected,
QTreeWidget#service_manager_list::item:selected:!active {{
    background: transparent;
    padding: 0;
    margin: 0;
}}

/* -------------------------------- Scrollbars ------------------------------- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {ink4};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:horizontal {{
    background: {ink4};
    border-radius: 5px;
    min-width: 24px;
}}

QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
    background: {line_hover};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
    width: 0;
}}

QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}

/* --------------------------- Sliders and progress -------------------------- */
QSlider::groove:horizontal {{
    height: 4px;
    background: {ink3};
    border-radius: 2px;
}}

QSlider::sub-page:horizontal {{
    background: {cue};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    background: {text_hi};
}}

QSlider::handle:horizontal:hover {{
    background: {cue_hover};
}}

QProgressBar {{
    background: {ink3};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: {text_mid};
}}

QProgressBar::chunk {{
    background: {cue};
    border-radius: 4px;
}}

/* Library sidebar: a slim icon rail with one button per plugin, and a header
   naming the active section. Replaces the stacked QToolBox tabs. */
QWidget#library_rail {{
    background: {ink1};
    border-right: 1px solid {line};
}}

QToolButton#library_rail_button {{
    border: 1px solid transparent;
    border-radius: 8px;
    background: transparent;
    padding: 0;
}}

QToolButton#library_rail_button:hover {{
    background: {ink3};
}}

QToolButton#library_rail_button:focus {{
    border-color: {cue_line};
}}

QToolButton#library_rail_button:pressed {{
    background: {ink2};
}}

QToolButton#library_rail_button:checked {{
    background: {cue_dim};
    border: 1px solid {cue_line};
}}

QLabel#library_header {{
    color: {text_hi};
    font-size: {type_section};
    font-weight: 600;
    padding: 8px 10px 6px 10px;
}}

/* Slide controller panels. Each controller announces its identity: a neutral
   accent line and chip for Preview, red for Live. The Live chip uses the cue
   accent on standby and turns on-air red while the output is actually
   showing (Show Presentation active). */
QWidget#slide_controller_panel {{
    border-top: 2px solid {ink4};
}}

QWidget#slide_controller_panel[isLive="true"] {{
    border-top: 2px solid {on_air};
}}

QLabel#slide_controller_type_label {{
    font-weight: bold;
    padding: 3px 10px;
    border-radius: 4px;
    margin: 2px;
    background-color: {ink3};
    color: {text_mid};
}}

QLabel#slide_controller_type_label[isLive="true"] {{
    background-color: {cue};
    color: {ink0};
}}

QLabel#slide_controller_type_label[isLive="true"][onAir="true"] {{
    background-color: {on_air};
    color: {text_on_accent};
}}

/* Blanked output is an explicit state, not just the absence of red: the chip
   turns warning amber while a hide mode is active. */
QLabel#slide_controller_type_label[isLive="true"][onAir="false"] {{
    background-color: {warning};
    color: {ink0};
}}

QLabel#slide_controller_info_label {{
    color: {text_hi};
    font-weight: 600;
    padding-left: 4px;
}}

/* The output preview surface joins the card language: a framed ink0 stage
   that letterboxes the rendered display. */
QFrame#preview_frame {{
    background: {ink0};
    border: 1px solid {line};
    border-radius: 8px;
}}

/* Settings dialog: the tab list reads as a navigation sidebar, not a plain
   list — chrome background and roomier rows. */
QListWidget#setting_list_widget {{
    background: {ink1};
    padding: 6px 2px;
}}

QListWidget#setting_list_widget::item {{
    padding: 8px 10px;
    margin: 1px 4px;
}}

/* Theme manager: in grid view the thumbnails read as cards with the name
   centered beneath the preview. */
QListWidget#theme_list_widget::item {{
    padding: 8px;
    margin: 3px;
}}

QLabel#slide_controller_count_label {{
    color: {text_mid};
    font-weight: 600;
    padding: 3px 6px;
}}

/* Output state segment in the status bar: answers "what is the projector
   showing right now" from anywhere in the app. */
QLabel#output_state_label {{
    font-size: {type_caption};
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 4px;
    margin: 1px 2px;
    background: {ink3};
    color: {text_mid};
}}

QLabel#output_state_label[outputState="onair"] {{
    background: {on_air};
    color: {text_on_accent};
}}

QLabel#output_state_label[outputState="hidden"] {{
    background: {warning};
    color: {ink0};
}}
""".format(ink0=NOIR_INK_0, ink1=NOIR_INK_1, ink2=NOIR_INK_2, ink3=NOIR_INK_3, ink4=NOIR_INK_4,
           line=NOIR_LINE, line_soft=NOIR_LINE_SOFT, line_hover=NOIR_LINE_HOVER,
           text_hi=NOIR_TEXT_HI, text_body=NOIR_TEXT_BODY, text_mid=NOIR_TEXT_MID, text_low=NOIR_TEXT_LOW,
           cue=NOIR_CUE, cue_hover=NOIR_CUE_HOVER, cue_dim=NOIR_CUE_DIM, cue_line=NOIR_CUE_LINE,
           on_air=NOIR_ON_AIR, warning=NOIR_WARNING, text_on_accent=NOIR_TEXT_ON_ACCENT,
           type_caption=NOIR_TYPE_CAPTION, type_section=NOIR_TYPE_SECTION)

# The vertical metrics compensate for Qt drawing the tab icon top-aligned to
# the raw widget rect: the pill's bottom margin lifts its visual center up
# toward the fixed icon box, and get_noir_toolbox_icon() drops the glyph the
# rest of the way. Change these together.
NOIR_MEDIA_MANAGER_STYLE = """
::tab#media_tool_box {{
    background: {ink2};
    border: none;
    border-radius: 6px;
    margin: 2px 6px 5px 6px;
    padding: 0px 10px;
    min-height: 26px;
    text-align: left;
    color: {text_mid};
    font-weight: 600;
}}

::tab:hover#media_tool_box {{
    background: {ink3};
    color: {text_hi};
}}

::tab:selected#media_tool_box {{
    background: {cue_dim};
    color: {text_hi};
}}
""".format(ink2=NOIR_INK_2, ink3=NOIR_INK_3, text_hi=NOIR_TEXT_HI, text_mid=NOIR_TEXT_MID,
           cue_dim=NOIR_CUE_DIM)

# Tiny SVG glyphs for stylesheet subcontrols (combo box arrows, check marks and
# tree branch carets). Qt stylesheets can only load images from files, so these
# are written to a temp directory at runtime; see get_noir_asset_stylesheet().
NOIR_ASSET_SVGS = {
    'caret-down': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M4 6l4 4 4-4" '
                  'fill="none" stroke="{mid}" stroke-width="1.8" stroke-linecap="round" '
                  'stroke-linejoin="round"/></svg>'.format(mid=NOIR_TEXT_MID),
    'caret-up': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M4 10l4-4 4 4" '
                'fill="none" stroke="{mid}" stroke-width="1.8" stroke-linecap="round" '
                'stroke-linejoin="round"/></svg>'.format(mid=NOIR_TEXT_MID),
    'caret-right': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M6 4l4 4-4 4" '
                   'fill="none" stroke="{mid}" stroke-width="1.8" stroke-linecap="round" '
                   'stroke-linejoin="round"/></svg>'.format(mid=NOIR_TEXT_MID),
    'check': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M3.5 8.5l3 3 6-7" '
             'fill="none" stroke="{ink0}" stroke-width="2" stroke-linecap="round" '
             'stroke-linejoin="round"/></svg>'.format(ink0=NOIR_INK_0),
    'radio-dot': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
                 '<circle cx="8" cy="8" r="4" fill="{cue}"/></svg>'.format(cue=NOIR_CUE),
}

NOIR_ASSET_STYLESHEET = """
QComboBox::down-arrow {{
    image: url({assets}/caret-down.svg);
    width: 12px;
    height: 12px;
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QDateEdit::up-arrow, QTimeEdit::up-arrow,
QDateTimeEdit::up-arrow {{
    image: url({assets}/caret-up.svg);
    width: 10px;
    height: 10px;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QDateEdit::down-arrow, QTimeEdit::down-arrow,
QDateTimeEdit::down-arrow {{
    image: url({assets}/caret-down.svg);
    width: 10px;
    height: 10px;
}}

QCheckBox::indicator:checked, QGroupBox::indicator:checked, QListView::indicator:checked,
QListWidget::indicator:checked, QTreeView::indicator:checked, QTreeWidget::indicator:checked,
QTableView::indicator:checked, QTableWidget::indicator:checked {{
    image: url({assets}/check.svg);
}}

QRadioButton::indicator:checked {{
    image: url({assets}/radio-dot.svg);
}}

QTreeView::branch:has-children:!has-siblings:closed,
QTreeView::branch:closed:has-children:has-siblings {{
    image: url({assets}/caret-right.svg);
}}

QTreeView::branch:open:has-children:!has-siblings,
QTreeView::branch:open:has-children:has-siblings {{
    image: url({assets}/caret-down.svg);
}}
"""


def get_noir_asset_stylesheet():
    """
    Write the Noir SVG glyphs to a temp directory and return the stylesheet
    chunk that references them. Returns an empty string if the files cannot
    be written, in which case Qt falls back to its default subcontrol glyphs.

    :return str: The asset stylesheet chunk, or an empty string
    """
    try:
        asset_dir = Path(tempfile.gettempdir()) / 'openlp-noir-assets'
        asset_dir.mkdir(parents=True, exist_ok=True)
        for name, svg in NOIR_ASSET_SVGS.items():
            asset_path = asset_dir / '{name}.svg'.format(name=name)
            if not asset_path.exists() or asset_path.read_text(encoding='utf8') != svg:
                asset_path.write_text(svg, encoding='utf8')
        return NOIR_ASSET_STYLESHEET.format(assets=asset_dir.as_posix())
    except OSError:
        log.exception('Unable to write the Noir theme assets')
        return ''


def get_noir_toolbox_icon(icon):
    """
    Rebuild a media manager tab icon with transparent headroom. Qt paints a
    QToolBox tab icon top-aligned to the raw widget rect, so without this the
    glyph pokes out of the top of the rounded Noir tab; the inset drops it to
    the vertical center of the pill defined by NOIR_MEDIA_MANAGER_STYLE.

    :param QtGui.QIcon icon: The original tab icon
    :return QtGui.QIcon: The icon with the glyph shifted down
    """
    size = 40
    inset = 10
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pixmap)
    icon.paint(painter, QtCore.QRect(0, inset, size - inset, size - inset))
    painter.end()
    return QtGui.QIcon(pixmap)


class UiThemes(Enum):
    """
    An enumeration for themes.
    """
    Automatic = 'automatic'
    DefaultLight = 'light:default'
    DefaultDark = 'dark:default'
    QDarkStyle = 'dark:qdarkstyle'
    Noir = 'dark:noir'


def is_ui_theme_dark():
    ui_theme_name = Registry().get('settings').value('advanced/ui_theme_name')

    if ui_theme_name is None or ui_theme_name == UiThemes.Automatic:
        return is_system_darkmode()
    else:
        return ui_theme_name.value.startswith('dark:')


def is_ui_theme(ui_theme: UiThemes):
    ui_theme_name = Registry().get('settings').value('advanced/ui_theme_name')
    return ui_theme_name == ui_theme


def init_ui_theme_if_needed(ui_theme_name):
    return not isinstance(ui_theme_name, UiThemes)


def has_ui_theme(ui_theme: UiThemes):
    if ui_theme == UiThemes.QDarkStyle:
        return HAS_DARK_THEME
    return True


IS_SYSTEM_DARKMODE = None


def is_system_darkmode():
    global IS_SYSTEM_DARKMODE

    if IS_SYSTEM_DARKMODE is None:
        try:
            if is_win():
                IS_SYSTEM_DARKMODE = is_windows_darkmode()
            elif is_macosx():
                IS_SYSTEM_DARKMODE = is_macosx_darkmode()
            else:
                IS_SYSTEM_DARKMODE = False
        except Exception:
            IS_SYSTEM_DARKMODE = False

    return IS_SYSTEM_DARKMODE


def is_windows_darkmode():
    """
    Detects if Windows is using dark mode system theme.

    Source: https://github.com/olivierkes/manuskript/blob/731e017e9e0dd7e4062f1af419705c11b2825515/manuskript/main.py
    (GPL3)

    Changes:
        * Allowed palette to be set on any operating system;
        * Split Windows Dark Mode detection to another function.
    """
    theme_settings = QtCore.QSettings('HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes'
                                      '\\Personalize',
                                      QtCore.QSettings.Format.NativeFormat)
    return theme_settings.value('AppsUseLightTheme') == 0


def is_macosx_darkmode():
    """
    Detects if Mac OS X is using dark mode system theme.

    Source: https://stackoverflow.com/a/65357166 (CC BY-SA 4.0)

    Changes:
        * Using OpenLP formatting rules
        * Handling exceptions
    """
    try:
        command = 'defaults read -g AppleInterfaceStyle'
        process = Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
        stdin = process.communicate()[0]
        return bool(stdin)
    except Exception:
        return False


# Fonts shipped with OpenLP. They live under the display html directory so the
# same files are served to the display web view (via the openlp:// scheme) for
# @font-face use, and registered with Qt here for the widget UI.
BUNDLED_FONT_DIR = Path(__file__).parent.parent / 'display' / 'html' / 'fonts'
_bundled_fonts_registered = False


def register_bundled_fonts():
    """
    Register the font files shipped with OpenLP (currently Lato) with the
    Qt font database so they are available to the UI and font pickers even when
    not installed on the system.
    """
    global _bundled_fonts_registered
    if _bundled_fonts_registered:
        return
    _bundled_fonts_registered = True
    for font_file in sorted(BUNDLED_FONT_DIR.glob('*.ttf')):
        font_id = QtGui.QFontDatabase.addApplicationFont(str(font_file))
        if font_id == -1:
            log.warning('Failed to register bundled font %s', font_file)


def set_default_theme(app):
    """
    Setup theme
    """
    register_bundled_fonts()
    if is_ui_theme(UiThemes.Noir):
        set_noir_palette(app)
    elif is_ui_theme(UiThemes.DefaultDark) or (is_ui_theme(UiThemes.Automatic) and is_ui_theme_dark()):
        set_default_darkmode(app)
    elif is_ui_theme(UiThemes.DefaultLight):
        set_default_lightmode(app)


def set_default_lightmode(app):
    """
    Setup lightmode on the application if Default Lightt theme is enabled in the OpenLP Settings.
    """
    app.setStyle('Fusion')
    app.setPalette(app.style().standardPalette())


def set_default_darkmode(app):
    """
    Setup darkmode on the application if enabled in the OpenLP Settings or using a dark mode system theme.

    Source:
    https://github.com/olivierkes/manuskript/blob/731e017e9e0dd7e4062f1af419705c11b2825515/manuskript/main.py
    (GPL3)

    Changes:
        * Allowed palette to be set on any operating system;
        * Split Windows Dark Mode detection to another function.
    """
    app.setStyle('Fusion')
    dark_palette = QtGui.QPalette()
    dark_color = QtGui.QColor(45, 45, 45)
    disabled_color = QtGui.QColor(127, 127, 127)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Window, dark_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtCore.Qt.GlobalColor.white)
    dark_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.WindowText, disabled_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(18, 18, 18))
    dark_palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, dark_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtCore.Qt.GlobalColor.white)
    dark_palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtCore.Qt.GlobalColor.black)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Text, QtCore.Qt.GlobalColor.white)
    dark_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.Text, disabled_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Button, dark_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtCore.Qt.GlobalColor.white)
    dark_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.ButtonText, disabled_color)
    dark_palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtCore.Qt.GlobalColor.red)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtCore.Qt.GlobalColor.black)
    dark_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.HighlightedText, disabled_color)
    # Fixes ugly (not to mention hard to read) disabled menu items.
    # Source: https://bugreports.qt.io/browse/QTBUG-10322?focusedCommentId=371060#comment-371060
    dark_palette.setColor(QtGui.QPalette.ColorGroup.Disabled,
                          QtGui.QPalette.ColorRole.Light,
                          QtCore.Qt.GlobalColor.transparent)
    # Fixes ugly media manager headers.
    dark_palette.setColor(QtGui.QPalette.ColorRole.Mid, QtGui.QColor(64, 64, 64))
    app.setPalette(dark_palette)


def set_noir_palette(app):
    """
    Setup the Noir palette on the application if the Noir theme is enabled in the OpenLP Settings.
    """
    app.setStyle('Fusion')
    window = QtGui.QColor(NOIR_INK_1)
    base = QtGui.QColor(NOIR_INK_0)
    panel = QtGui.QColor(NOIR_INK_2)
    raised = QtGui.QColor(NOIR_INK_3)
    hover = QtGui.QColor(NOIR_INK_4)
    text_hi = QtGui.QColor(NOIR_TEXT_HI)
    disabled = QtGui.QColor(NOIR_TEXT_LOW)
    cue = QtGui.QColor(NOIR_CUE)
    noir_palette = QtGui.QPalette()
    noir_palette.setColor(QtGui.QPalette.ColorRole.Window, window)
    noir_palette.setColor(QtGui.QPalette.ColorRole.WindowText, text_hi)
    noir_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.WindowText, disabled)
    noir_palette.setColor(QtGui.QPalette.ColorRole.Base, base)
    noir_palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, panel)
    noir_palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, panel)
    noir_palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, text_hi)
    noir_palette.setColor(QtGui.QPalette.ColorRole.Text, text_hi)
    noir_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.Text, disabled)
    noir_palette.setColor(QtGui.QPalette.ColorRole.PlaceholderText, disabled)
    noir_palette.setColor(QtGui.QPalette.ColorRole.Button, raised)
    noir_palette.setColor(QtGui.QPalette.ColorRole.ButtonText, text_hi)
    noir_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.ButtonText, disabled)
    noir_palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor(NOIR_ON_AIR))
    noir_palette.setColor(QtGui.QPalette.ColorRole.Link, cue)
    noir_palette.setColor(QtGui.QPalette.ColorRole.Highlight, cue)
    noir_palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, base)
    noir_palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.HighlightedText, disabled)
    # Fixes ugly (not to mention hard to read) disabled menu items.
    # Source: https://bugreports.qt.io/browse/QTBUG-10322?focusedCommentId=371060#comment-371060
    noir_palette.setColor(QtGui.QPalette.ColorGroup.Disabled,
                          QtGui.QPalette.ColorRole.Light,
                          QtCore.Qt.GlobalColor.transparent)
    # Fixes ugly media manager headers.
    noir_palette.setColor(QtGui.QPalette.ColorRole.Mid, hover)
    app.setPalette(noir_palette)
    # Typography: prefer a modern variable-width UI font, falling back down the
    # stack on systems where it is not installed.
    font = QtGui.QFont()
    font.setFamilies(NOIR_FONT_FAMILIES)
    font.setPointSizeF(NOIR_TYPE_BODY_PT)
    app.setFont(font)


def get_alternate_rows_repair_stylesheet(base_color_name):
    return 'QTableWidget, QListWidget, QTreeWidget {alternate-background-color: ' + base_color_name + ';}\n'


def get_application_stylesheet():
    """
    Return the correct application stylesheet based on the current style and operating system

    :return str: The correct stylesheet as a string
    """
    stylesheet = ''
    if is_ui_theme(UiThemes.QDarkStyle):
        stylesheet = qdarkstyle.load_stylesheet_pyqt()
    else:
        if not Registry().get('settings').value('advanced/alternate rows'):
            base_color = QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorGroup.Active,
                                                                QtGui.QPalette.ColorRole.Base)
            alternate_rows_repair_stylesheet = get_alternate_rows_repair_stylesheet(base_color.name())
            stylesheet += alternate_rows_repair_stylesheet
        if is_win():
            stylesheet += WIN_REPAIR_STYLESHEET
        if is_ui_theme(UiThemes.Noir):
            stylesheet += NOIR_STYLESHEET
            stylesheet += get_noir_asset_stylesheet()
    stylesheet += 'QWidget#slide_controller_toolbar QToolButton::checked {' \
                  '  background-color: palette(highlight);' \
                  '  color: palette(highlighted-text);' \
                  '}'
    return stylesheet


def get_library_stylesheet():
    """
    Return the correct stylesheet for the main window

    :return str: The correct stylesheet as a string
    """
    if is_ui_theme(UiThemes.QDarkStyle):
        return ''
    elif is_ui_theme(UiThemes.Noir):
        return NOIR_MEDIA_MANAGER_STYLE
    else:
        return MEDIA_MANAGER_STYLE
