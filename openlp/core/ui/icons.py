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
The :mod:`languages` module provides a list of icons.
"""
import logging
import sys

import qtawesome as qta
from PySide6 import QtGui, QtWidgets

from openlp.core.common import Singleton
from openlp.core.common.applocation import AppLocation
from openlp.core.common.registry import Registry
from openlp.core.lib import build_icon
from openlp.core.ui.style import NOIR_CUE, NOIR_ON_AIR, NOIR_PLUGIN_ALERTS, NOIR_PLUGIN_BIBLES, \
    NOIR_PLUGIN_CUSTOM, NOIR_PLUGIN_IMAGES, NOIR_PLUGIN_LIBRARY, NOIR_PLUGIN_MEDIA, \
    NOIR_PLUGIN_PRESENTATIONS, NOIR_PLUGIN_SONGS, NOIR_SUCCESS, NOIR_TEXT_LOW, \
    NOIR_WARNING, get_noir_theme_tokens, is_ui_theme_dark, is_ui_theme_noir_family


log = logging.getLogger(__name__)

# The Noir icon set. Phosphor icons share a single stroke weight and geometric
# grid, so every icon in the application reads as part of one family. Colors
# come from the Noir palette tokens rather than raw named colors.
NOIR_ICON_LIST = {
    'active': {'icon': 'ph.hands-clapping'},
    'add': {'icon': 'ph.plus-circle'},
    'alert': {'icon': 'ph.megaphone', 'attr': NOIR_PLUGIN_ALERTS},
    'arrow_down': {'icon': 'ph.arrow-down'},
    'arrow_left': {'icon': 'ph.arrow-left'},
    'arrow_right': {'icon': 'ph.arrow-right'},
    'arrow_up': {'icon': 'ph.arrow-up'},
    'audio': {'icon': 'ph.music-note'},
    'authentication': {'icon': 'ph.shield-warning', 'attr': NOIR_WARNING},
    'address': {'icon': 'ph.book-open'},
    'back': {'icon': 'ph.skip-back'},
    'backspace': {'icon': 'ph.x'},
    'bible': {'icon': 'ph.book-open', 'attr': NOIR_PLUGIN_BIBLES},
    'blank': {'icon': 'ph.eye-slash'},
    'blank_theme': {'icon': 'ph.image-square'},
    'bold': {'icon': 'ph.text-bolder'},
    'book': {'icon': 'ph.book-open'},
    'bottom': {'icon': 'ph.caret-double-down'},
    'box': {'icon': 'ph.package'},
    'clapperboard': {'icon': 'ph.film-strip'},
    'clock': {'icon': 'ph.clock'},
    'clone': {'icon': 'ph.copy'},
    'close': {'icon': 'ph.x-circle'},
    'copy': {'icon': 'ph.copy-simple'},
    'copyright': {'icon': 'ph.copyright'},
    'custom': {'icon': 'ph.note-pencil', 'attr': NOIR_PLUGIN_CUSTOM},
    'database': {'icon': 'ph.database'},
    'default': {'icon': 'ph.info'},
    'desktop': {'icon': 'ph.monitor'},
    'delete': {'icon': 'ph.trash'},
    'device_stream': {'icon': 'ph.video-camera'},
    'donate': {'icon': 'ph.heart'},
    'download': {'icon': 'ph.download-simple'},
    'edit': {'icon': 'ph.pencil-simple'},
    'email': {'icon': 'ph.envelope-simple'},
    'error': {'icon': 'ph.warning-circle', 'attr': NOIR_ON_AIR},
    'exception': {'icon': 'ph.bug'},
    'exit': {'icon': 'ph.sign-out'},
    'favourite': {'icon': 'ph.star'},
    'folder': {'icon': 'ph.folder-simple'},
    'group': {'icon': 'ph.folders'},
    'inactive': {'icon': 'ph.hands-clapping', 'attr': NOIR_TEXT_LOW},
    'info': {'icon': 'ph.info'},
    'italic': {'icon': 'ph.text-italic'},
    'library': {'icon': 'ph.books', 'attr': NOIR_PLUGIN_LIBRARY},
    'light_bulb': {'icon': 'ph.lightbulb'},
    'live': {'icon': 'ph.broadcast'},
    'live_presentation': {'icon': 'ph.presentation-chart'},
    'live_theme': {'icon': 'ph.paint-brush-broad'},
    'live_black': {'icon': 'ph.rectangle'},
    'live_desktop': {'icon': 'ph.monitor-play'},
    'loop': {'icon': 'ph.repeat'},
    'manual': {'icon': 'ph.book-bookmark'},
    'media': {'icon': 'ph.play-circle'},
    'minus': {'icon': 'ph.minus'},
    'move_start': {'icon': 'ph.arrow-line-up'},
    'move_up': {'icon': 'ph.arrow-up'},
    'move_down': {'icon': 'ph.arrow-down'},
    'move_end': {'icon': 'ph.arrow-line-down'},
    'music': {'icon': 'ph.music-notes', 'attr': NOIR_PLUGIN_SONGS},
    'network_stream': {'icon': 'ph.link-simple'},
    'new': {'icon': 'ph.file-plus'},
    'new_group': {'icon': 'ph.folder-simple-plus'},
    'notes': {'icon': 'ph.note'},
    'obs_studio': {'icon': 'ph.record'},
    'open': {'icon': 'ph.folder-open'},
    'pause': {'icon': 'ph.pause'},
    'planning_center': {'icon': 'ph.cloud-arrow-down'},
    'play': {'icon': 'ph.play'},
    'player': {'icon': 'ph.device-tablet'},
    'play_slides': {'icon': 'ph.play-circle'},
    'plugin_list': {'icon': 'ph.puzzle-piece'},
    'plus': {'icon': 'ph.plus'},
    'presentation': {'icon': 'ph.presentation', 'attr': NOIR_PLUGIN_PRESENTATIONS},
    'preview': {'icon': 'ph.eye'},
    'projector': {'icon': 'ph.projector-screen'},
    'projector_connect': {'icon': 'ph.link'},
    'projector_cooldown': {'icon': 'ph.projector-screen', 'attr': NOIR_CUE},
    'projector_disconnect': {'icon': 'ph.link-break', 'attr': NOIR_TEXT_LOW},
    'projector_error': {'icon': 'ph.projector-screen', 'attr': NOIR_ON_AIR},
    'projector_hdmi': {'icon': 'ph.screencast'},
    'projector_power_off': {'icon': 'ph.power', 'attr': NOIR_ON_AIR},
    'projector_power_on': {'icon': 'ph.power', 'attr': NOIR_SUCCESS},
    'projector_off': {'icon': 'ph.projector-screen', 'attr': NOIR_TEXT_LOW},
    'projector_on': {'icon': 'ph.projector-screen', 'attr': NOIR_SUCCESS},
    'projector_select_connect': {'icon': 'ph.link', 'attr': NOIR_SUCCESS},
    'projector_select_disconnect': {'icon': 'ph.link-break', 'attr': NOIR_ON_AIR},
    'projector_warmup': {'icon': 'ph.projector-screen', 'attr': NOIR_WARNING},
    'picture': {'icon': 'ph.image', 'attr': NOIR_PLUGIN_IMAGES},
    'print': {'icon': 'ph.printer'},
    'remote': {'icon': 'ph.wifi-high'},
    'repeat': {'icon': 'ph.repeat'},
    'save': {'icon': 'ph.floppy-disk'},
    'search': {'icon': 'ph.magnifying-glass'},
    'search_ccli': {'icon': 'ph.hash'},
    'search_comb': {'icon': 'ph.columns'},
    'search_lyrics': {'icon': 'ph.text-align-left'},
    'search_minus': {'icon': 'ph.magnifying-glass-minus'},
    'search_plus': {'icon': 'ph.magnifying-glass-plus'},
    'search_ref': {'icon': 'ph.bookmark-simple'},
    'search_text': {'icon': 'ph.text-aa'},
    'select_all': {'icon': 'ph.check-square'},
    'select_none': {'icon': 'ph.square'},
    'settings': {'icon': 'ph.gear-six'},
    'shortcuts': {'icon': 'ph.keyboard'},
    'song_usage': {'icon': 'ph.chart-line'},
    'song_usage_active': {'icon': 'ph.minus-circle'},
    'song_usage_inactive': {'icon': 'ph.plus-circle'},
    'sort': {'icon': 'ph.sort-ascending'},
    'stop': {'icon': 'ph.stop'},
    'square': {'icon': 'ph.square'},
    'text': {'icon': 'ph.file-text'},
    'time': {'icon': 'ph.clock-counter-clockwise'},
    'theme': {'icon': 'ph.paint-brush-broad'},
    'top': {'icon': 'ph.caret-double-up'},
    'undo': {'icon': 'ph.arrow-counter-clockwise'},
    'upload': {'icon': 'ph.upload-simple'},
    'user': {'icon': 'ph.user'},
    'usermo': {'icon': 'ph.user-plus'},
    'users': {'icon': 'ph.users'},
    'video': {'icon': 'ph.film-strip', 'attr': NOIR_PLUGIN_MEDIA},
    'view_list': {'icon': 'ph.list-dashes'},
    'view_grid': {'icon': 'ph.squares-four'},
    'volunteer': {'icon': 'ph.users-three'}
}


class UiIcons(metaclass=Singleton):
    """
    Provide standard icons for objects to use.
    """
    def __init__(self):
        """
        These are the font icons used in the code.
        """
        app_dir = AppLocation.get_directory(AppLocation.AppDir)
        font_path_candidates = [app_dir / 'core' / 'ui' / 'fonts']
        if getattr(sys, 'frozen', False):
            font_path_candidates.append(app_dir.parent / 'Resources' / 'openlp' / 'core' / 'ui' / 'fonts')
        font_path = next((path for path in font_path_candidates if path.is_dir()), font_path_candidates[0])
        qta.load_font('op', 'OpenLP.ttf', 'openlp-charmap.json', directory=str(font_path))
        palette = QtWidgets.QApplication.palette()
        self._default_icon_colors = {
            "color": palette.color(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.WindowText),
            "color_disabled": palette.color(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.WindowText)
        }
        qta.set_defaults(**self._default_icon_colors)
        legacy_icon_list = {
            'active': {'icon': 'mdi.human-handsup'},
            'add': {'icon': 'mdi.plus-circle'},
            'alert': {'icon': 'mdi.alert'},
            'arrow_down': {'icon': 'mdi.arrow-down'},
            'arrow_left': {'icon': 'mdi.arrow-left'},
            'arrow_right': {'icon': 'mdi.arrow-right'},
            'arrow_up': {'icon': 'mdi.arrow-up'},
            'audio': {'icon': 'mdi.file-music-outline'},
            'authentication': {'icon': 'mdi.alert', 'attr': 'red'},
            'address': {'icon': 'mdi.book-open-variant'},
            'back': {'icon': 'mdi.skip-previous'},
            'backspace': {'icon': 'mdi.close'},
            # 'backspace': {'icon': 'mdi.chevron-left-box-outline'},
            'bible': {'icon': 'mdi.book-open-variant'},
            'blank': {'icon': 'mdi.close-circle'},
            'blank_theme': {'icon': 'mdi.file-image-outline'},
            'bold': {'icon': 'mdi.format-bold'},
            'book': {'icon': 'mdi.book-open-variant'},
            'bottom': {'icon': 'mdi.chevron-double-down'},
            'box': {'icon': 'mdi.briefcase'},
            'clapperboard': {'icon': 'mdi.filmstrip'},
            'clock': {'icon': 'mdi.clock-outline'},
            'clone': {'icon': 'mdi.content-duplicate'},
            'close': {'icon': 'mdi.close-circle-outline'},
            'copy': {'icon': 'mdi.content-copy'},
            'copyright': {'icon': 'mdi.copyright'},
            'custom': {'icon': 'mdi.text-box-outline'},
            'database': {'icon': 'mdi.database'},
            'default': {'icon': 'mdi.information'},
            'desktop': {'icon': 'mdi.desktop-mac'},
            'delete': {'icon': 'mdi.delete'},
            'device_stream': {'icon': 'mdi.video'},
            'donate': {'icon': 'mdi.cash-multiple'},
            'download': {'icon': 'mdi.download'},
            'edit': {'icon': 'mdi.file-document-edit-outline'},
            'email': {'icon': 'mdi.email'},
            'error': {'icon': 'mdi.exclamation-thick', 'attr': 'red'},
            'exception': {'icon': 'mdi.close-circle'},
            'exit': {'icon': 'mdi.logout'},
            'favourite': {'icon': 'mdi.star'},
            'folder': {'icon': 'mdi.folder'},
            'group': {'icon': 'mdi.group'},
            'inactive': {'icon': 'mdi.human-handsup', 'attr': 'lightGray'},
            'info': {'icon': 'mdi.information-variant'},
            'italic': {'icon': 'mdi.format-italic'},
            'library': {'icon': 'mdi.bookshelf'},
            'light_bulb': {'icon': 'mdi.lightbulb-outline'},
            'live': {'icon': 'op.live'},
            'live_presentation': {'icon': 'op.live-presentation'},
            'live_theme': {'icon': 'op.live-theme'},
            'live_black': {'icon': 'op.live-black'},
            'live_desktop': {'icon': 'op.live-desktop'},
            'loop': {'icon': 'mdi.replay'},
            'manual': {'icon': 'mdi.school'},
            'media': {'icon': 'mdi.fax'},
            'minus': {'icon': 'mdi.minus'},
            'move_start': {'icon': 'mdi.arrow-collapse-up'},
            'move_up': {'icon': 'mdi.arrow-up'},
            'move_down': {'icon': 'mdi.arrow-down'},
            'move_end': {'icon': 'mdi.arrow-collapse-down'},
            'music': {'icon': 'mdi.music'},
            'network_stream': {'icon': 'mdi.link-variant'},
            'new': {'icon': 'mdi.file-plus-outline'},
            'new_group': {'icon': 'mdi.folder'},
            'notes': {'icon': 'mdi.note'},
            'obs_studio': {'icon': 'mdi.spotlight'},
            'open': {'icon': 'mdi.folder-open'},
            'pause': {'icon': 'mdi.pause'},
            'planning_center': {'icon': 'mdi.cloud-download'},
            'play': {'icon': 'mdi.play'},
            'player': {'icon': 'mdi.tablet'},
            'play_slides': {'icon': 'mdi.play-circle-outline'},
            'plugin_list': {'icon': 'mdi.puzzle'},
            'plus': {'icon': 'mdi.plus'},
            'presentation': {'icon': 'mdi.chart-bar'},
            'preview': {'icon': 'mdi.laptop'},
            'projector': {'icon': 'mdi.projector'},
            'projector_connect': {'icon': 'mdi.power-plug'},
            'projector_cooldown': {'icon': 'mdi.projector', 'attr': 'blue'},
            'projector_disconnect': {'icon': 'mdi.power-plug', 'attr': 'lightGray'},  # Projector disconnect
            'projector_error': {'icon': 'mdi.projector', 'attr': 'red'},
            'projector_hdmi': {'icon': 'mdi.video-input-hdmi'},
            'projector_power_off': {'icon': 'mdi.projector', 'attr': 'red'},  # Toolbar power off
            'projector_power_on': {'icon': 'mdi.projector', 'attr': 'green'},  # Toolbar power on
            'projector_off': {'icon': 'mdi.projector', 'attr': 'black'},  # Projector off
            'projector_on': {'icon': 'mdi.projector', 'attr': 'green'},  # Projector on
            'projector_select_connect': {'icon': 'mdi.power-plug', 'attr': 'green'},  # Toolbar connect
            'projector_select_disconnect': {'icon': 'mdi.power-plug', 'attr': 'red'},  # Toolbar disconnect
            'projector_warmup': {'icon': 'mdi.projector', 'attr': 'yellow'},
            'picture': {'icon': 'mdi.image-outline'},
            'print': {'icon': 'mdi.printer'},
            'remote': {'icon': 'mdi.rss'},
            'repeat': {'icon': 'mdi.repeat'},
            'save': {'icon': 'mdi.content-save-outline'},
            'search': {'icon': 'mdi.magnify'},
            'search_ccli': {'icon': 'op.search-CCLI'},
            'search_comb': {'icon': 'mdi.view-column-outline'},
            'search_lyrics': {'icon': 'op.search-lyrics'},
            'search_minus': {'icon': 'mdi.magnify-minus-outline'},
            'search_plus': {'icon': 'mdi.magnify-plus-outline'},
            'search_ref': {'icon': 'mdi.bank'},
            'search_text': {'icon': 'op.search-text'},
            'select_all': {'icon': 'mdi.checkbox-marked-outline'},
            'select_none': {'icon': 'mdi.checkbox-blank-outline'},
            'settings': {'icon': 'mdi.cogs'},
            'shortcuts': {'icon': 'mdi.wrench'},
            'song_usage': {'icon': 'mdi.chart-line'},
            'song_usage_active': {'icon': 'mdi.minus-circle'},
            'song_usage_inactive': {'icon': 'mdi.plus-circle'},
            'sort': {'icon': 'mdi.sort'},
            'stop': {'icon': 'mdi.stop'},
            'square': {'icon': 'mdi.checkbox-blank'},
            'text': {'icon': 'mdi.file-document-outline'},
            'time': {'icon': 'mdi.history'},
            'theme': {'icon': 'mdi.brush'},
            'top': {'icon': 'mdi.chevron-double-up'},
            'undo': {'icon': 'mdi.undo'},
            'upload': {'icon': 'mdi.upload'},
            'user': {'icon': 'mdi.account'},
            'usermo': {'icon': 'mdi.account-plus'},
            'users': {'icon': 'mdi.account-group'},
            'video': {'icon': 'mdi.file-video-outline'},
            'view_list': {'icon': 'mdi.view-list'},
            'view_grid': {'icon': 'mdi.view-grid'},
            'volunteer': {'icon': 'mdi.account-group'}
        }
        self._icon_list = NOIR_ICON_LIST if is_ui_theme_noir_family() else legacy_icon_list
        self.load_icons(self._icon_list)
        self.main_icon = build_icon(':/icon/openlp-logo.svg')

    def load_icons(self, icon_list):
        """
        Load the list of icons to be processed
        """
        is_dark = is_ui_theme_dark()
        is_noir = is_ui_theme_noir_family()
        noir_text_hi = get_noir_theme_tokens()['text_hi']
        for key in icon_list:
            try:
                icon = icon_list[key]['icon']
                try:
                    attr = icon_list[key]['attr']
                    setattr(self, key, qta.icon(icon, color=attr))
                except KeyError:
                    if is_noir:
                        # Softer than pure white, matching the Noir text ramp
                        setattr(self, key, qta.icon(icon, color=noir_text_hi))
                    elif is_dark:
                        setattr(self, key, qta.icon(icon, color='white'))
                    else:
                        setattr(self, key, qta.icon(icon))
                except Exception:
                    log.exception(f'Unexpected error for icon: {icon}')
                    setattr(self, key, qta.icon('mdi.alert-circle', color='red'))
            except Exception:
                log.exception(f'Unexpected error for icon with key: {key}')
                setattr(self, key, qta.icon('mdi.alert-circle', color='red'))

    def get_icon_variant(self, icon_name, **kwargs):
        """
        See qta.icon() documentation for more information.

        :param icon_name: UiIcons' icon name
        """
        if icon_name not in self._icon_list:
            raise KeyError("Icon '{icon}' is not defined.".format(icon=icon_name))
        icon = self._icon_list[icon_name]['icon']
        if is_ui_theme_noir_family():
            args = {"color": get_noir_theme_tokens()['text_hi'], **kwargs}
        elif is_ui_theme_dark():
            args = {"color": "white", **kwargs}
        else:
            args = kwargs
        return qta.icon(icon, **args)

    def get_icon_variant_selected(self, icon_name):
        """
        Returns an icon that honors the Qt's Pallete HighlightText color when host button is selected.
        """
        qtApp = Registry().get('application-qt')
        color = qtApp.palette().highlightedText().color()
        icon = self.get_icon_variant(icon_name, color_on=color, color_off_active=self._default_icon_colors['color'])
        return icon

