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
This class contains the core default settings.
"""
import datetime
import json
import logging
import os
from enum import IntEnum
from pathlib import Path
from tempfile import gettempdir

from PyQt5 import QtCore, QtGui

from openlp.core.common import SlideLimits, ThemeLevel
from openlp.core.common.enum import AlertLocation, BibleSearch, CustomSearch, HiDPIMode, ImageThemeMode, LayoutStyle, \
    DisplayStyle, LanguageSelection, SongFirstSlideMode, SongSearch, PluginStatus
from openlp.core.common.json import OpenLPJSONDecoder, OpenLPJSONEncoder, is_serializable
from openlp.core.common.path import files_to_paths, str_to_path
from openlp.core.common.platform import is_linux, is_win
from openlp.core.ui.style import UiThemes


log = logging.getLogger(__name__)

__version__ = 3


class ProxyMode(IntEnum):
    NO_PROXY = 1
    SYSTEM_PROXY = 2
    MANUAL_PROXY = 3


TODAY = QtCore.QDate.currentDate()

# Fix for bug #1014422.
X11_BYPASS_DEFAULT = True
if is_linux():                                                                              # pragma: no cover
    # Default to False on Gnome.
    X11_BYPASS_DEFAULT = bool(not os.environ.get('GNOME_DESKTOP_SESSION_ID'))
    # Default to False on Xfce.
    if os.environ.get('DESKTOP_SESSION') == 'xfce':
        X11_BYPASS_DEFAULT = False


def media_players_conv(string):
    """
    If phonon is in the setting string replace it with system
    :param string: String to convert
    :return: Converted string
    """
    values = string.split(',')
    for index, value in enumerate(values):
        if value == 'phonon':
            values[index] = 'system'
    string = ','.join(values)
    return string


def upgrade_screens(number, x_position, y_position, height, width, can_override, is_display_screen):
    """
    Upgrade them monitor setting from a few single entries to a composite JSON entry

    :param int number: The old monitor number
    :param int x_position: The X position
    :param int y_position: The Y position
    :param bool can_override: Are the screen positions overridden
    :param bool is_display_screen: Is this a display screen
    :returns dict: Dictionary with the new value
    """
    geometry_key = 'geometry'
    if can_override:
        geometry_key = 'custom_geometry'
    return {
        number: {
            'number': number,
            geometry_key: {
                'x': int(x_position),
                'y': int(y_position),
                'height': int(height),
                'width': int(width)
            },
            'is_display': is_display_screen,
            'is_primary': can_override
        }
    }


def upgrade_dark_theme_to_ui_theme(value):
    """
    Upgrade the dark theme setting to use the new UiThemes setting.

    :param bool value: The old use_dark_style setting
    :returns UiThemes: New UiThemes value
    """
    return UiThemes.QDarkStyle if value else UiThemes.Automatic


def upgrade_add_first_songbook_slide_config(value):
    """
    Upgrade the "songs/add songbook slide" property to "songs/add first slide".

    :param bool value: the old "add_songbook_slide" value
    :returns SongFirstSlideMode: new SongFirstSlideMode value
    """
    return SongFirstSlideMode.Songbook if value is True else SongFirstSlideMode.Default


class Settings(QtCore.QSettings):
    """
    Class to wrap QSettings.

    * Exposes all the methods of QSettings.
    * Adds functionality for OpenLP Portable. If the ``defaultFormat`` is set to ``IniFormat``, and the path to the Ini
      file is set using ``set_filename``, then the Settings constructor (without any arguments) will create a Settings
      object for accessing settings stored in that Ini file.

    ``__default_settings__``
        This dict contains all core settings with their default values.

    ``__obsolete_settings__``
        Each entry is structured in the following way::

            ('general/enable slide loop', 'advanced/slide limits', [(SlideLimits.Wrap, True), (SlideLimits.End, False)])

        The first entry is the *old key*; if it is different from the *new key* it will be removed.

        The second entry is the *new key*; we will add it to the config. If this is just an empty string, we just remove
        the old key. The last entry is a list containing two-pair tuples. If the list is empty, no conversion is made.
        If the first value is callable i.e. a function, the function will be called with the old setting's value.
        Otherwise each pair describes how to convert the old setting's value::

            (SlideLimits.Wrap, True)

        This means, that if the value of ``general/enable slide loop`` is equal (``==``) ``True`` then we set
        ``advanced/slide limits`` to ``SlideLimits.Wrap``. **NOTE**, this means that the rules have to cover all cases!
        So, if the type of the old value is bool, then there must be two rules.
    """
    __default_settings__ = {
        'settings/version': 0,
        'advanced/add page break': False,
        'advanced/disable transparent display': True,
        'advanced/alternate rows': not is_win(),
        'advanced/autoscrolling': {'dist': 1, 'pos': 0},
        'advanced/current media plugin': -1,
        'advanced/data path': None,
        # 7 stands for now, 0 to 6 is Monday to Sunday.
        'advanced/default service day': 7,
        'advanced/default service enabled': True,
        'advanced/default service hour': 11,
        'advanced/default service minute': 0,
        'advanced/default service name': 'Service %Y-%m-%d %H-%M',
        'advanced/display size': 0,
        'advanced/double click live': False,
        'advanced/enable exit confirmation': True,
        'advanced/expand service item': False,
        'advanced/hide mouse': True,
        'advanced/ignore aspect ratio': False,
        'advanced/is portable': False,
        'advanced/max recent files': 20,
        'advanced/new service message': True,
        'advanced/print file meta data': False,
        'advanced/print notes': False,
        'advanced/print slide text': False,
        'advanced/protect data directory': False,
        'advanced/proxy mode': ProxyMode.SYSTEM_PROXY,
        'advanced/proxy http': '',
        'advanced/proxy https': '',
        'advanced/proxy username': '',
        'advanced/proxy password': '',
        'advanced/recent file count': 4,
        'advanced/save current plugin': False,
        'advanced/slide limits': SlideLimits.End,
        'advanced/slide max height': -4,
        'advanced/slide numbers in footer': False,
        'advanced/single click preview': False,
        'advanced/single click service preview': False,
        'advanced/x11 bypass wm': X11_BYPASS_DEFAULT,
        'advanced/prefer windowed screen capture': False,
        'advanced/search as type': True,
        'advanced/ui_theme_name': UiThemes.Automatic,
        'advanced/delete service item confirmation': False,
        'advanced/hidpi mode': HiDPIMode.Default,
        'alerts/font face': QtGui.QFont().family(),
        'alerts/font size': 40,
        'alerts/db type': 'sqlite',
        'alerts/db username': '',
        'alerts/db password': '',
        'alerts/db hostname': '',
        'alerts/db database': '',
        'alerts/location': AlertLocation.Bottom,
        'alerts/background color': '#660000',
        'alerts/font color': '#ffffff',
        'alerts/status': PluginStatus.Inactive,
        'alerts/timeout': 10,
        'alerts/repeat': 1,
        'alerts/scroll': True,
        'api/twelve hour': True,
        'api/port': 4316,
        'api/websocket port': 4317,
        'api/user id': 'openlp',
        'api/password': 'password',
        'api/authentication enabled': False,
        'api/ip address': '0.0.0.0',
        'api/thumbnails': True,
        'api/download version': None,
        'api/last version test': '',
        'api/update check': True,
        'bibles/db type': 'sqlite',
        'bibles/db username': '',
        'bibles/db password': '',
        'bibles/db hostname': '',
        'bibles/db database': '',
        'bibles/last used search type': BibleSearch.Combined,
        'bibles/reset to combined quick search': True,
        'bibles/verse layout style': LayoutStyle.VersePerSlide,
        'bibles/book name language': LanguageSelection.Bible,
        'bibles/display brackets': DisplayStyle.NoBrackets,
        'bibles/is verse number visible': True,
        'bibles/display new chapter': False,
        'bibles/second bibles': True,
        'bibles/status': PluginStatus.Inactive,
        'bibles/primary bible': '',
        'bibles/second bible': None,
        'bibles/bible theme': '',
        'bibles/verse separator': '',
        'bibles/range separator': '',
        'bibles/list separator': '',
        'bibles/end separator': '',
        'bibles/last directory import': None,
        'bibles/hide combined quick error': False,
        'bibles/is search while typing enabled': True,
        'crashreport/last directory': None,
        'custom/db type': 'sqlite',
        'custom/db username': '',
        'custom/db password': '',
        'custom/db hostname': '',
        'custom/db database': '',
        'custom/last used search type': CustomSearch.Titles,
        'custom/display footer': True,
        'custom/add custom from service': True,
        'custom/status': PluginStatus.Inactive,
        'formattingTags/html_tags': '',
        'core/auto open': False,
        'core/auto preview': False,
        'core/auto unblank': False,
        'core/click live slide to unblank': False,
        'core/blank warning': False,
        'core/ccli number': '',
        'core/has run wizard': False,
        'core/language': '[en]',
        'core/last version test': '',
        'core/live preview shows blank screen': False,
        'core/loop delay': 5,
        'core/recent files': [],
        'core/screens': '{}',
        'core/screen blank': False,
        'core/show splash': True,
        'core/logo background color': '#ffffff',
        'core/logo file': Path(':/graphics/openlp-splash-screen.png'),
        'core/logo hide on startup': False,
        'core/songselect password': '',
        'core/songselect username': '',
        'core/update check': True,
        'core/view mode': 'default',
        # The other display settings (display position and dimensions) are defined in the ScreenList class due to a
        # circular dependency.
        'core/display on monitor': False,
        'core/override position': False,
        'core/monitor': {},
        'core/application version': '0.0',
        'images/background mode': ImageThemeMode.Black,
        'images/theme': None,
        'images/db type': 'sqlite',
        'images/db username': '',
        'images/db password': '',
        'images/db hostname': '',
        'images/db database': '',
        'images/last directory': None,
        'images/status': PluginStatus.Inactive,
        'media/status': PluginStatus.Inactive,
        'media/media files': [],
        'media/last directory': None,
        'media/media auto start': QtCore.Qt.Unchecked,
        'media/vlc arguments': '',
        'media/live volume': 50,
        'media/preview volume': 0,
        'media/live loop': False,
        'media/preview loop': False,
        'media/db type': 'sqlite',
        'media/db username': '',
        'media/db password': '',
        'media/db hostname': '',
        'media/db database': '',
        'players/background color': '#000000',
        'obs_studio/status': PluginStatus.Inactive,
        'obs_studio/host': 'localhost',
        'obs_studio/port': 4455,
        'obs_studio/password': '',
        'planningcenter/status': PluginStatus.Inactive,
        'planningcenter/application_id': '',
        'planningcenter/secret': '',
        'presentations/status': PluginStatus.Inactive,
        'presentations/override app': QtCore.Qt.Unchecked,
        'presentations/maclo': QtCore.Qt.Checked,
        'presentations/Impress': QtCore.Qt.Checked,
        'presentations/Powerpoint': QtCore.Qt.Checked,
        'presentations/Pdf': QtCore.Qt.Checked,
        'presentations/Keynote': QtCore.Qt.Checked,
        'presentations/PowerPointMac': QtCore.Qt.Checked,
        'presentations/presentations files': [],
        'presentations/thumbnail_scheme': '',
        'presentations/powerpoint slide click advance': QtCore.Qt.Unchecked,
        'presentations/powerpoint control window': QtCore.Qt.Unchecked,
        'presentations/impress use display setting': QtCore.Qt.Unchecked,
        'presentations/last directory': None,
        'presentations/db type': 'sqlite',
        'presentations/db username': '',
        'presentations/db password': '',
        'presentations/db hostname': '',
        'presentations/db database': '',
        'servicemanager/last directory': None,
        'servicemanager/last file': None,
        'servicemanager/service theme': None,
        'SettingsImport/file_date_created': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        'SettingsImport/Make_Changes': 'At_Own_RISK',
        'SettingsImport/type': 'OpenLP_settings_export',
        'SettingsImport/version': '',
        'songs/status': PluginStatus.Inactive,
        'songs/db type': 'sqlite',
        'songs/db username': '',
        'songs/db password': '',
        'songs/db hostname': '',
        'songs/db database': '',
        'songs/last used search type': SongSearch.Entire,
        'songs/last import type': 0,
        'songs/update service on edit': False,
        'songs/add song from service': True,
        'songs/first slide mode': SongFirstSlideMode.Default,
        'songs/display songbar': True,
        'songs/last directory import': None,
        'songs/last directory export': None,
        'songs/songselect username': '',
        'songs/songselect password': '',
        'songs/songselect searches': '',
        'songs/enable chords': True,
        'songs/warn about missing song key': True,
        'songs/chord notation': 'english',  # Can be english, german or neo-latin
        'songs/disable chords import': False,
        'songs/auto play audio': False,
        'songs/uppercase songs': False,
        'songusage/status': PluginStatus.Inactive,
        'songusage/db type': 'sqlite',
        'songusage/db username': '',
        'songusage/db password': '',
        'songusage/db hostname': '',
        'songusage/db database': '',
        'songusage/active': False,
        'songusage/to date': TODAY,
        'songusage/from date': TODAY.addYears(-1),
        'songusage/last directory export': None,
        'themes/global theme': '',
        'themes/last directory': None,
        'themes/last directory export': None,
        'themes/last directory import': None,
        'themes/theme level': ThemeLevel.Global,
        'themes/item transitions': False,
        'themes/hot reload': False,
        'user interface/is preset layout': False,
        'user interface/live panel': True,
        'user interface/live splitter geometry': QtCore.QByteArray(),
        'user interface/lock panel': True,
        'user interface/main window geometry': QtCore.QByteArray(),
        'user interface/main window position': QtCore.QPoint(0, 0),
        'user interface/main window splitter geometry': QtCore.QByteArray(),
        'user interface/main window state': QtCore.QByteArray(),
        'user interface/preview panel': True,
        'user interface/preview splitter geometry': QtCore.QByteArray(),
        'user interface/theme manager view mode': 0,
        'user interface/show library': True,
        'user interface/show projectors': True,
        'user interface/show service': True,
        'user interface/show themes': True,
        'projector/show after wizard': False,
        'projector/db type': 'sqlite',
        'projector/db username': '',
        'projector/db password': '',
        'projector/db hostname': '',
        'projector/db database': '',
        'projector/enable': True,
        'projector/connect on start': False,
        'projector/connect when LKUP received': True,  # PJLink v2: Projector sends LKUP command after it powers up
        'projector/last directory import': None,
        'projector/last directory export': None,
        'projector/poll time': 20,  # PJLink  timeout is 30 seconds
        'projector/socket timeout': 5,  # 5 second socket timeout
        'projector/source dialog type': 0,  # Source select dialog box type
        'projector/udp broadcast listen': False  # Enable/disable listening for PJLink 2 UDP broadcast packets
    }
    __file_path__ = ''
    # Settings upgrades prior to 3.0
    __setting_upgrade_1__ = [
        ('songs/search as type', 'advanced/search as type', []),
        ('media/players', 'media/players_temp', [(media_players_conv, None)]),  # Convert phonon to system
        ('media/players_temp', 'media/players', []),  # Move temp setting from above to correct setting
    ]
    # Settings upgrades for 3.0 (aka 2.6)
    __setting_upgrade_2__ = [
        # The following changes are being made for the conversion to using Path objects made in 2.6 development
        ('advanced/data path', 'advanced/data path', [(lambda p: Path(p) if p is not None else None, None)]),
        ('advanced/default color', 'core/logo background color', []),  # Default image renamed + moved to general > 2.4.
        ('advanced/default image', 'core/logo file', []),  # Default image renamed + moved to general after 2.4.
        ('advanced/use_dark_style', 'advanced/ui_theme_name', [(upgrade_dark_theme_to_ui_theme, [False])]),
        ('bibles/advanced bible', '', []),  # Common bible search widgets combined in 2.6
        ('bibles/last directory import', 'bibles/last directory import', [(str_to_path, None)]),
        ('bibles/last search type', '', []),
        ('bibles/proxy address', '', []),
        ('bibles/proxy name', '', []),  # Just remove these bible proxy settings. They weren't used in 2.4!
        ('bibles/proxy password', '', []),
        ('bibles/proxy username', '', []),
        ('bibles/quick bible', 'bibles/primary bible', []),  # Common bible search widgets combined in 2.6
        ('core/audio repeat list', '', []),
        ('core/audio start paused', '', []),
        ('core/logo file', 'core/logo file', [(str_to_path, None)]),
        (['core/monitor', 'core/x position', 'core/y position', 'core/height', 'core/width', 'core/override position',
          'core/display on monitor'], 'core/screens', [(upgrade_screens, [1, 0, 0, None, None, False, False])]),
        ('core/recent files', 'core/recent files', [(files_to_paths, None)]),
        ('core/save prompt', '', []),
        ('crashreport/last directory', 'crashreport/last directory', [(str_to_path, None)]),
        ('custom/last search type', 'custom/last used search type', []),
        ('images/background color', '', []),
        ('images/last directory', 'images/last directory', [(str_to_path, None)]),
        ('media/last directory', 'media/last directory', [(str_to_path, None)]),
        ('media/media files', 'media/media files', [(files_to_paths, None)]),
        ('media/override player', '', []),
        ('media/players', '', []),
        ('presentations / Powerpoint Viewer', '', []),
        ('presentations/enable_pdf_program', '', []),
        ('presentations/last directory', 'presentations/last directory', [(str_to_path, None)]),
        ('presentations/pdf_program', '', []),
        ('presentations/presentations files', 'presentations/presentations files', [(files_to_paths, None)]),
        ('projector/last directory export', 'projector/last directory export', [(str_to_path, None)]),
        ('projector/last directory import', 'projector/last directory import', [(str_to_path, None)]),
        ('remotes/authentication enabled', 'api/authentication enabled', []),
        ('remotes/https enabled', '', []),
        ('remotes/https port', '', []),
        ('remotes/ip address', 'api/ip address', []),
        ('remotes/password', 'api/password', []),
        ('remotes/port', 'api/port', []),
        ('remotes/thumbnails', 'api/thumbnails', []),
        ('remotes/twelve hour', 'api/twelve hour', []),
        ('remotes/user id', 'api/user id', []),
        ('remotes/websocket port', 'api/websocket port', []),
        ('servicemanager/last directory', 'servicemanager/last directory', [(str_to_path, None)]),
        ('servicemanager/last file', 'servicemanager/last file', [(str_to_path, None)]),
        ('shortcuts/desktopScreenEnable', '', []),
        ('shortcuts/escapeItem', '', []),  # Escape item was removed in 2.6.
        ('shortcuts/offlineHelpItem', 'shortcuts/userManualItem', []),  # Online and Offline help were combined in 2.6.
        ('shortcuts/onlineHelpItem', 'shortcuts/userManualItem', []),  # Online and Offline help were combined in 2.6.
        ('songs/auto play audio', 'songs/auto play audio', [(bool, None)]),
        ('songs/last directory export', 'songs/last directory export', [(str_to_path, None)]),
        ('songs/last directory import', 'songs/last directory import', [(str_to_path, None)]),
        # Last search type was renamed to last used search type in 2.6 since Bible search value type changed in 2.6.
        ('songs/last search type', 'songs/last used search type', []),
        ('songuasge/db database', 'songusage/db database', []),
        ('songuasge/db hostname', 'songusage/db hostname', []),
        ('songuasge/db password', 'songusage/db password', []),
        ('songusage/last directory export', 'songusage/last directory export', [(str_to_path, None)]),
        ('themes/last directory export', 'themes/last directory export', [(str_to_path, None)]),
        ('themes/last directory import', 'themes/last directory import', [(str_to_path, None)]),
        ('themes/last directory', 'themes/last directory', [(str_to_path, None)]),
        ('themes/wrap footer', '', []),
    ]
    # Settings upgrades for 3.1
    __setting_upgrade_3__ = [
        ('songs/add songbook slide', 'songs/first slide mode', [(upgrade_add_first_songbook_slide_config, False)])
    ]

    @staticmethod
    def extend_default_settings(default_values):
        """
        Static method to merge the given ``default_values`` with the ``Settings.__default_settings__``.

        :param default_values: A dict with setting keys and their default values.
        """
        Settings.__default_settings__.update(default_values)

    @staticmethod
    def set_filename(ini_path):
        """
        Sets the complete path to an Ini file to be used by Settings objects.

        Does not affect existing Settings objects.

        :param Path ini_path: ini file path
        :rtype: None
        """
        Settings.__file_path__ = str(ini_path)

    @staticmethod
    def set_up_default_values():
        """
        This static method is called on start up. It is used to perform any operation on the __default_settings__ dict.
        """
        # Make sure the string is translated (when building the dict the string is not translated because the translate
        # function was not set up as this stage).
        from openlp.core.common.i18n import UiStrings
        Settings.__default_settings__['advanced/default service name'] = UiStrings().DefaultServiceName

    def __init__(self, *args):
        """
        Constructor which checks if this should be a native settings object, or an INI file.
        """
        if not args and Settings.__file_path__ and Settings.defaultFormat() == Settings.IniFormat:
            QtCore.QSettings.__init__(self, Settings.__file_path__, Settings.IniFormat)
        else:
            QtCore.QSettings.__init__(self, *args)

    def init_default_shortcuts(self):
        # Add shortcuts here so QKeySequence has a QApplication instance to use.
        Settings.__default_settings__.update({
            'shortcuts/aboutItem': [QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_F1)],
            'shortcuts/addToService': [],
            'shortcuts/audioPauseItem': [],
            'shortcuts/displayTagItem': [],
            'shortcuts/blankScreen': [QtGui.QKeySequence(QtCore.Qt.Key_Period)],
            'shortcuts/collapse': [QtGui.QKeySequence(QtCore.Qt.Key_Minus)],
            'shortcuts/desktopScreen': [QtGui.QKeySequence(QtCore.Qt.Key_D), QtGui.QKeySequence(QtCore.Qt.Key_Escape)],
            'shortcuts/delete': [QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Delete)],
            'shortcuts/down': [QtGui.QKeySequence(QtCore.Qt.Key_Down)],
            'shortcuts/editSong': [],
            'shortcuts/expand': [QtGui.QKeySequence(QtCore.Qt.Key_Plus)],
            'shortcuts/exportThemeItem': [],
            'shortcuts/fileNewItem': [QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.New)],
            'shortcuts/fileSaveAsItem': [QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.SaveAs)],
            'shortcuts/fileExitItem': [QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Quit)],
            'shortcuts/fileSaveItem': [QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Save)],
            'shortcuts/fileOpenItem': [QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Open)],
            'shortcuts/goLive': [],
            'shortcuts/userManualItem': [QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.HelpContents)],
            'shortcuts/importThemeItem': [],
            'shortcuts/importBibleItem': [],
            'shortcuts/listViewBiblesDeleteItem': [QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Delete)],
            'shortcuts/listViewBiblesPreviewItem': [QtGui.QKeySequence(QtCore.Qt.Key_Return),
                                                    QtGui.QKeySequence(QtCore.Qt.Key_Enter)],
            'shortcuts/listViewBiblesLiveItem': [QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Return),
                                                 QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Enter)],
            'shortcuts/listViewBiblesServiceItem': [QtGui.QKeySequence(QtCore.Qt.Key_Plus),
                                                    QtGui.QKeySequence(QtCore.Qt.Key_Equal)],
            'shortcuts/listViewCustomDeleteItem': [QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Delete)],
            'shortcuts/listViewCustomPreviewItem': [QtGui.QKeySequence(QtCore.Qt.Key_Return),
                                                    QtGui.QKeySequence(QtCore.Qt.Key_Enter)],
            'shortcuts/listViewCustomLiveItem': [QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Return),
                                                 QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Enter)],
            'shortcuts/listViewCustomServiceItem': [QtGui.QKeySequence(QtCore.Qt.Key_Plus),
                                                    QtGui.QKeySequence(QtCore.Qt.Key_Equal)],
            'shortcuts/listViewImagesDeleteItem': [QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Delete)],
            'shortcuts/listViewImagesPreviewItem': [QtGui.QKeySequence(QtCore.Qt.Key_Return),
                                                    QtGui.QKeySequence(QtCore.Qt.Key_Enter)],
            'shortcuts/listViewImagesLiveItem': [QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Return),
                                                 QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Enter)],
            'shortcuts/listViewImagesServiceItem': [QtGui.QKeySequence(QtCore.Qt.Key_Plus),
                                                    QtGui.QKeySequence(QtCore.Qt.Key_Equal)],
            'shortcuts/listViewMediaDeleteItem': [QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Delete)],
            'shortcuts/listViewMediaPreviewItem': [QtGui.QKeySequence(QtCore.Qt.Key_Return),
                                                   QtGui.QKeySequence(QtCore.Qt.Key_Enter)],
            'shortcuts/listViewMediaLiveItem': [QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Return),
                                                QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Enter)],
            'shortcuts/listViewMediaServiceItem': [QtGui.QKeySequence(QtCore.Qt.Key_Plus),
                                                   QtGui.QKeySequence(QtCore.Qt.Key_Equal)],
            'shortcuts/listViewPresentationsDeleteItem': [QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Delete)],
            'shortcuts/listViewPresentationsPreviewItem': [QtGui.QKeySequence(QtCore.Qt.Key_Return),
                                                           QtGui.QKeySequence(QtCore.Qt.Key_Enter)],
            'shortcuts/listViewPresentationsLiveItem': [QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Return),
                                                        QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Enter)],
            'shortcuts/listViewPresentationsServiceItem': [QtGui.QKeySequence(QtCore.Qt.Key_Plus),
                                                           QtGui.QKeySequence(QtCore.Qt.Key_Equal)],
            'shortcuts/listViewSongsDeleteItem': [QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Delete)],
            'shortcuts/listViewSongsPreviewItem': [QtGui.QKeySequence(QtCore.Qt.Key_Return),
                                                   QtGui.QKeySequence(QtCore.Qt.Key_Enter)],
            'shortcuts/listViewSongsLiveItem': [QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Return),
                                                QtGui.QKeySequence(QtCore.Qt.SHIFT + QtCore.Qt.Key_Enter)],
            'shortcuts/listViewSongsServiceItem': [QtGui.QKeySequence(QtCore.Qt.Key_Plus),
                                                   QtGui.QKeySequence(QtCore.Qt.Key_Equal)],
            'shortcuts/lockPanel': [],
            'shortcuts/modeDefaultItem': [],
            'shortcuts/modeLiveItem': [],
            'shortcuts/make_live': [QtGui.QKeySequence(QtCore.Qt.Key_Return), QtGui.QKeySequence(QtCore.Qt.Key_Enter)],
            'shortcuts/moveUp': [QtGui.QKeySequence(QtCore.Qt.Key_PageUp)],
            'shortcuts/moveTop': [QtGui.QKeySequence(QtCore.Qt.Key_Home)],
            'shortcuts/modeSetupItem': [],
            'shortcuts/moveBottom': [QtGui.QKeySequence(QtCore.Qt.Key_End)],
            'shortcuts/moveDown': [QtGui.QKeySequence(QtCore.Qt.Key_PageDown)],
            'shortcuts/nextTrackItem': [],
            'shortcuts/nextItem_live': [QtGui.QKeySequence(QtCore.Qt.Key_Down),
                                        QtGui.QKeySequence(QtCore.Qt.Key_PageDown)],
            'shortcuts/nextItem_preview': [QtGui.QKeySequence(QtCore.Qt.Key_Down),
                                           QtGui.QKeySequence(QtCore.Qt.Key_PageDown)],
            'shortcuts/nextService': [QtGui.QKeySequence(QtCore.Qt.Key_Right)],
            'shortcuts/newService': [],
            'shortcuts/openService': [],
            'shortcuts/saveService': [],
            'shortcuts/previousItem_live': [QtGui.QKeySequence(QtCore.Qt.Key_Up),
                                            QtGui.QKeySequence(QtCore.Qt.Key_PageUp)],
            'shortcuts/playbackPause': [],
            'shortcuts/playbackPlay': [],
            'shortcuts/playbackStop': [],
            'shortcuts/playSlidesLoop': [],
            'shortcuts/playSlidesOnce': [],
            'shortcuts/previousService': [QtGui.QKeySequence(QtCore.Qt.Key_Left)],
            'shortcuts/previousItem_preview': [QtGui.QKeySequence(QtCore.Qt.Key_Up),
                                               QtGui.QKeySequence(QtCore.Qt.Key_PageUp)],
            'shortcuts/printServiceItem': [QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Print)],
            'shortcuts/songExportItem': [],
            'shortcuts/songUsageStatus': [QtGui.QKeySequence(QtCore.Qt.Key_F4)],
            'shortcuts/searchShortcut': [QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Find)],
            'shortcuts/settingsShortcutsItem': [],
            'shortcuts/settingsImportItem': [],
            'shortcuts/settingsPluginListItem': [QtGui.QKeySequence(QtCore.Qt.ALT + QtCore.Qt.Key_F7)],
            'shortcuts/songUsageDelete': [],
            'shortcuts/settingsConfigureItem': [QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.Preferences)],
            'shortcuts/shortcutAction_B': [QtGui.QKeySequence(QtCore.Qt.Key_B)],
            'shortcuts/shortcutAction_C': [QtGui.QKeySequence(QtCore.Qt.Key_C)],
            'shortcuts/shortcutAction_E': [QtGui.QKeySequence(QtCore.Qt.Key_E)],
            'shortcuts/shortcutAction_I': [QtGui.QKeySequence(QtCore.Qt.Key_I)],
            'shortcuts/shortcutAction_O': [QtGui.QKeySequence(QtCore.Qt.Key_O)],
            'shortcuts/shortcutAction_P': [QtGui.QKeySequence(QtCore.Qt.Key_P)],
            'shortcuts/shortcutAction_V': [QtGui.QKeySequence(QtCore.Qt.Key_V)],
            'shortcuts/shortcutAction_0': [QtGui.QKeySequence(QtCore.Qt.Key_0)],
            'shortcuts/shortcutAction_1': [QtGui.QKeySequence(QtCore.Qt.Key_1)],
            'shortcuts/shortcutAction_2': [QtGui.QKeySequence(QtCore.Qt.Key_2)],
            'shortcuts/shortcutAction_3': [QtGui.QKeySequence(QtCore.Qt.Key_3)],
            'shortcuts/shortcutAction_4': [QtGui.QKeySequence(QtCore.Qt.Key_4)],
            'shortcuts/shortcutAction_5': [QtGui.QKeySequence(QtCore.Qt.Key_5)],
            'shortcuts/shortcutAction_6': [QtGui.QKeySequence(QtCore.Qt.Key_6)],
            'shortcuts/shortcutAction_7': [QtGui.QKeySequence(QtCore.Qt.Key_7)],
            'shortcuts/shortcutAction_8': [QtGui.QKeySequence(QtCore.Qt.Key_8)],
            'shortcuts/shortcutAction_9': [QtGui.QKeySequence(QtCore.Qt.Key_9)],
            'shortcuts/showScreen': [QtGui.QKeySequence(QtCore.Qt.Key_Space)],
            'shortcuts/settingsExportItem': [],
            'shortcuts/songUsageReport': [],
            'shortcuts/songImportItem': [],
            'shortcuts/themeScreen': [QtGui.QKeySequence(QtCore.Qt.Key_T)],
            'shortcuts/toolsReindexItem': [],
            'shortcuts/toolsFindDuplicates': [],
            'shortcuts/toolsSongListReport': [],
            'shortcuts/toolsAlertItem': [QtGui.QKeySequence(QtCore.Qt.Key_F7)],
            'shortcuts/toolsFirstTimeWizard': [],
            'shortcuts/toolsOpenDataFolder': [],
            'shortcuts/toolsAddToolItem': [],
            'shortcuts/updateThemeImages': [],
            'shortcuts/up': [QtGui.QKeySequence(QtCore.Qt.Key_Up)],
            'shortcuts/viewProjectorManagerItem': [QtGui.QKeySequence(QtCore.Qt.Key_F6)],
            'shortcuts/viewThemeManagerItem': [QtGui.QKeySequence(QtCore.Qt.Key_F10)],
            'shortcuts/viewMediaManagerItem': [QtGui.QKeySequence(QtCore.Qt.Key_F8)],
            'shortcuts/viewPreviewPanel': [QtGui.QKeySequence(QtCore.Qt.Key_F11)],
            'shortcuts/viewLivePanel': [QtGui.QKeySequence(QtCore.Qt.Key_F12)],
            'shortcuts/viewServiceManagerItem': [QtGui.QKeySequence(QtCore.Qt.Key_F9)],
            'shortcuts/webSiteItem': []
        })

    def get_default_value(self, key):
        """
        Get the default value of the given key
        """
        if self.group():
            key = self.group() + '/' + key
        return Settings.__default_settings__[key]

    def from_future(self):
        """
        Is the settings version higher then the version required by OpenLP

        :rtype: bool
        """
        return __version__ < self.value('settings/version')

    def version_mismatched(self):
        """
        Are the settings a different version as required by OpenLP

        :rtype: bool
        """
        return __version__ != self.value('settings/version')

    def upgrade_settings(self):
        """
        This method is only called to clean up the config. It removes old settings and it renames settings. See
        ``__obsolete_settings__`` for more details.
        """
        current_version = self.value('settings/version')
        for version in range(current_version, __version__):
            version += 1
            upgrade_list = getattr(self, '__setting_upgrade_{version}__'.format(version=version))
            for old_keys, new_key, rules in upgrade_list:
                # Once removed we don't have to do this again. - Can be removed once fully switched to the versioning
                # system.
                if not isinstance(old_keys, (tuple, list)):
                    old_keys = [old_keys]
                if any([not self.contains(old_key) for old_key in old_keys]):
                    log.warning('One of {} does not exist, skipping upgrade'.format(old_keys))
                    continue
                if new_key:
                    # Get the value of the old_key.
                    old_values = [super(Settings, self).value(old_key) for old_key in old_keys]
                    # When we want to convert the value, we have to figure out the default value (because we cannot get
                    # the default value from the central settings dict.
                    if rules:
                        default_values = rules[0][1]
                        if not isinstance(default_values, (list, tuple)):
                            default_values = [default_values]
                        old_values = [self._convert_value(old_value, default_value)
                                      for old_value, default_value in zip(old_values, default_values)]
                    # Iterate over our rules and check what the old_value should be "converted" to.
                    new_value = old_values[0]
                    for new_rule, old_rule in rules:
                        # If the value matches with the condition (rule), then use the provided value. This is used to
                        # convert values. E. g. an old value 1 results in True, and 0 in False.
                        if callable(new_rule):
                            new_value = new_rule(*old_values)
                        elif old_rule in old_values:
                            new_value = new_rule
                            break
                    self.setValue(new_key, new_value)
                [self.remove(old_key) for old_key in old_keys if old_key != new_key]
            self.setValue('settings/version', version)

    def value(self, key):
        """
        Returns the value for the given ``key``. The returned ``value`` is of the same type as the default value in the
        *Settings.__default_settings__* dict.

        :param str key: The key to return the value from.
        :return: The value stored by the setting.
        """
        # if group() is not empty the group has not been specified together with the key.
        if self.group():
            default_value = Settings.__default_settings__[self.group() + '/' + key]
        else:
            default_value = Settings.__default_settings__[key]
        try:
            setting = super().value(key, default_value)
        except TypeError:
            setting = default_value
        return self._convert_value(setting, default_value)

    def setValue(self, key, value):
        """
        Reimplement the setValue method to handle Path objects.

        :param str key: The key of the setting to save
        :param value: The value to save
        :rtype: None
        """
        if is_serializable(value) or isinstance(value, dict) or \
                (isinstance(value, list) and value and is_serializable(value[0])):
            value = json.dumps(value, cls=OpenLPJSONEncoder)
        super().setValue(key, value)

    def _convert_value(self, setting, default_value):
        """
        This converts the given ``setting`` to the type of the given ``default_value``.

        :param setting: The setting to convert. This could be ``true`` for example.Settings()
        :param default_value: Indication the type the setting should be converted to. For example ``True``
        (type is boolean), meaning that we convert the string ``true`` to a python boolean.

        **Note**, this method only converts a few types and might need to be extended if a certain type is missing!
        """
        # Handle 'None' type (empty value) properly.
        if setting is None:
            # An empty string saved to the settings results in a None type being returned.
            # Convert it to empty unicode string.
            if isinstance(default_value, str):
                return ''
            # An empty list saved to the settings results in a None type being returned.
            elif isinstance(default_value, list):
                return []
            # An empty dictionary saved to the settings results in a None type being returned.
            elif isinstance(default_value, dict):
                return {}
        elif isinstance(setting, (str, bytes)):
            if isinstance(setting, bytes):
                # convert to str
                setting = setting.decode('utf8')
            if 'json_meta' in setting or '__Path__' in setting or setting.startswith('{'):
                return json.loads(setting, cls=OpenLPJSONDecoder)
        # Convert the setting to the correct type.
        if isinstance(default_value, bool):
            if isinstance(setting, bool):
                return setting
            # Sometimes setting is string instead of a boolean.
            return setting == 'true'
        if isinstance(default_value, int):
            if setting is None:
                return 0
            return int(setting)
        return setting

    def export(self, dest_path):
        """
        Export the settings to file.

        :param Path dest_path: The file path to create the export file.
        :return: Success
        :rtype: bool
        """
        temp_path = Path(gettempdir(), 'openlp', 'exportConf.tmp')
        # Delete old files if found.
        if temp_path.exists():
            temp_path.unlink()
        if dest_path.exists():
            dest_path.unlink()
        self.remove('SettingsImport')
        # Get the settings.
        keys = self.allKeys()
        export_settings = QtCore.QSettings(str(temp_path), QtCore.QSettings.Format.IniFormat)
        # Add a header section.
        # This is to insure it's our conf file for import.
        now = datetime.datetime.now()
        # Write INI format using QSettings.
        # Write our header.
        export_settings.setValue('SettingsImport/Make_Changes', 'At_Own_RISK')
        export_settings.setValue('SettingsImport/type', 'OpenLP_settings_export')
        export_settings.setValue('SettingsImport/file_date_created', now.strftime("%Y-%m-%d %H:%M"))
        # Write all the sections and keys.
        for section_key in keys:
            try:
                key_value = super().value(section_key)
                if key_value is not None:
                    export_settings.setValue(section_key, key_value)
            except TypeError:
                log.exception(f'Key Value invalid and bypassed for {section_key}')
        export_settings.sync()
        # Temp CONF file has been written.  Blanks in keys are now '%20'.
        # Read the  temp file and output the user's CONF file with blanks to
        # make it more readable.
        try:
            with dest_path.open('w') as export_conf_file, temp_path.open('r') as temp_conf:
                for file_record in temp_conf:
                    # Get rid of any invalid entries.
                    if file_record.find('@Invalid()') == -1:
                        file_record = file_record.replace('%20', ' ')
                        export_conf_file.write(file_record)
        finally:
            temp_path.unlink()
