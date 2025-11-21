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
"""
The :mod:`languages` module provides a list of icons.
"""
import logging

import qtawesome as qta
from PyQt5 import QtGui, QtWidgets

from openlp.core.common import Singleton
from openlp.core.common.applocation import AppLocation
from openlp.core.common.registry import Registry
from openlp.core.lib import build_icon
from openlp.core.ui.style import is_ui_theme_dark


log = logging.getLogger(__name__)


class UiIcons(metaclass=Singleton):
    """
    Provide standard icons for objects to use.
    """
    def __init__(self):
        """
        These are the font icons used in the code.
        """
        font_path = AppLocation.get_directory(AppLocation.AppDir) / 'core' / 'ui' / 'fonts'
        qta.load_font('op', 'OpenLP.ttf', 'openlp-charmap.json', directory=str(font_path))
        palette = QtWidgets.QApplication.palette()
        self._default_icon_colors = {
            "color": palette.color(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.WindowText),
            "color_disabled": palette.color(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.WindowText)
        }
        qta.set_defaults(**self._default_icon_colors)
        self._icon_list = {
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
            'download': {'icon': 'mdi.download'},
            'edit': {'icon': 'mdi.file-document-edit-outline'},
            'email': {'icon': 'mdi.email'},
            'error': {'icon': 'mdi.exclamation-thick', 'attr': 'red'},
            'exception': {'icon': 'mdi.close-circle'},
            'exit': {'icon': 'mdi.logout'},
            'folder': {'icon': 'mdi.folder'},
            'group': {'icon': 'mdi.group'},
            'inactive': {'icon': 'mdi.human-handsup', 'attr': 'lightGray'},
            'info': {'icon': 'mdi.information-variant'},
            'italic': {'icon': 'mdi.format-italic'},
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
            'optical': {'icon': 'mdi.disc'},
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
        self.load_icons(self._icon_list)
        self.main_icon = build_icon(':/icon/openlp-logo.svg')

    def load_icons(self, icon_list):
        """
        Load the list of icons to be processed
        """
        is_dark = is_ui_theme_dark()
        for key in icon_list:
            try:
                icon = icon_list[key]['icon']
                try:
                    attr = icon_list[key]['attr']
                    setattr(self, key, qta.icon(icon, color=attr))
                except KeyError:
                    if is_dark:
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
        is_dark = is_ui_theme_dark()
        if is_dark:
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

    @staticmethod
    def _print_icons():
        """
        Have ability to dump icons to see what is actually available.  Can only run within an application.
        Alternatively look at https://pictogrammers.github.io/@mdi/font/5.9.55/
        :return:
        """
        ico = qta._resource['iconic']
        mdi = ico.charmap['mdi']
        for ky in mdi.keys():
            print(ky, mdi[ky])
