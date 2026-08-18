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
The UI widgets for the first time wizard.
"""
from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common import clean_button_text
from openlp.core.common.platform import is_macosx
from openlp.core.common.i18n import translate
from openlp.core.lib.ui import add_welcome_page
from openlp.core.ui.icons import UiIcons

from openlp.core.display.screens import ScreenList
from openlp.core.pages import GridLayoutPage
from openlp.core.widgets.widgets import ScreenSelectionWidget


class FirstTimePage(object):
    """
    An enumeration class with each of the pages of the wizard.
    """
    Welcome = 0
    Plugins = 1
    ScreenConfig = 2
    SampleOption = 3
    Download = 4
    NoInternet = 5
    Remote = 6
    Songs = 7
    Bibles = 8
    Themes = 9
    Progress = 10


class RemotePage(GridLayoutPage):
    """
    A page for the web remote
    """
    def setup_ui(self):
        """
        Set up the page
        """
        self.remote_label = QtWidgets.QLabel(self)
        self.remote_label.setWordWrap(True)
        self.remote_label.setObjectName('remote_label')
        self.layout.addWidget(self.remote_label, 0, 0, 1, 4)
        self.download_checkbox = QtWidgets.QCheckBox(self)
        self.setObjectName('download_checkbox')
        self.layout.addWidget(self.download_checkbox, 1, 1, 1, 3)

    def retranslate_ui(self):
        """
        Translate the interface
        """
        self.remote_label.setText(translate('OpenLP.FirstTimeWizard', 'OpenLP has a web remote, which enables you to '
                                            'control OpenLP from another computer, phone or tablet on the same network '
                                            'as the OpenLP computer. OpenLP can download this web remote for you now, '
                                            'or you can download it later via the remote settings.'))
        self.download_checkbox.setText(translate('OpenLP.FirstTimeWizard', 'Yes, download the remote now'))
        self.setTitle(translate('OpenLP.FirstTimeWizard', 'Web-based Remote Interface'))
        self.setSubTitle(translate('OpenLP.FirstTimeWizard', 'Please confirm if you want to download the web remote.'))

    @property
    def can_download_remote(self):
        """
        The get method of a property to determine if the user selected the "Download remote now" checkbox
        """
        return self.download_checkbox.isChecked()

    @can_download_remote.setter
    def can_download_remote(self, value):
        if not isinstance(value, bool):
            raise TypeError('Must be a bool')
        self.download_checkbox.setChecked(value)


class ThemeListWidget(QtWidgets.QListWidget):
    """
    Subclass a QListWidget so we can make it look better when it resizes.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setIconSize(QtCore.QSize(133, 100))
        self.setMovement(QtWidgets.QListView.Movement.Static)
        self.setFlow(QtWidgets.QListView.Flow.LeftToRight)
        self.setProperty("isWrapping", True)
        self.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        self.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        self.setUniformItemSizes(True)

    def resizeEvent(self, event):
        """
        Resize the grid so the list looks better when its resized/

        :param QtGui.QResizeEvent event: Not used
        :return: None
        """
        super().resizeEvent(event)
        nominal_width = 141  # Icon width of 133 + 4 each side
        max_items_per_row = self.viewport().width() // nominal_width or 1  # or 1 to avoid divide by 0 errors
        col_size = (self.viewport().width() - 1) // max_items_per_row
        self.setGridSize(QtCore.QSize(col_size, 140))


class UiFirstTimeWizard(object):
    """
    The UI widgets for the first time wizard.
    """
    def setup_ui(self, first_time_wizard):
        """
        Set up the UI.

        :param first_time_wizard: The wizard form
        """
        first_time_wizard.setObjectName('first_time_wizard')
        first_time_wizard.setWindowIcon(UiIcons().main_icon)
        first_time_wizard.resize(640, 400)
        first_time_wizard.setModal(True)
        first_time_wizard.setOptions(QtWidgets.QWizard.WizardOption.IndependentPages |
                                     QtWidgets.QWizard.WizardOption.NoBackButtonOnStartPage |
                                     QtWidgets.QWizard.WizardOption.NoBackButtonOnLastPage |
                                     QtWidgets.QWizard.WizardOption.HaveCustomButton1)
        if is_macosx():                                                                             # pragma: nocover
            first_time_wizard.setPixmap(QtWidgets.QWizard.WizardPixmap.BackgroundPixmap,
                                        QtGui.QPixmap(':/wizards/openlp-osx-wizard.png'))
            first_time_wizard.resize(634, 386)
        else:
            first_time_wizard.setWizardStyle(QtWidgets.QWizard.WizardStyle.ModernStyle)
        add_welcome_page(first_time_wizard, ':/wizards/wizard_firsttime.bmp')
        # The screen config page
        self.screen_page = QtWidgets.QWizardPage()
        self.screen_page.setObjectName('defaults_page')
        self.screen_page_layout = QtWidgets.QFormLayout(self.screen_page)
        self.screen_selection_widget = ScreenSelectionWidget(self, ScreenList())
        self.screen_selection_widget.use_simple_view()
        self.screen_selection_widget.load()
        self.screen_page_layout.addRow(self.screen_selection_widget)
        first_time_wizard.setPage(FirstTimePage.ScreenConfig, self.screen_page)
        # Download Samples page
        self.resource_page = QtWidgets.QWizardPage()
        self.resource_page.setObjectName('resource_page')
        self.resource_page.setFinalPage(True)
        self.resource_layout = QtWidgets.QVBoxLayout(self.resource_page)
        self.resource_layout.setContentsMargins(50, 20, 50, 20)
        self.resource_layout.setObjectName('resource_layout')
        self.resource_label = QtWidgets.QLabel(self.resource_page)
        self.resource_label.setObjectName('resource_label')
        self.resource_label.setWordWrap(True)
        self.resource_layout.addWidget(self.resource_label)
        first_time_wizard.setPage(FirstTimePage.SampleOption, self.resource_page)
        # The download page
        self.download_page = QtWidgets.QWizardPage()
        self.download_page.setObjectName('download_page')
        self.download_layout = QtWidgets.QVBoxLayout(self.download_page)
        self.download_layout.setContentsMargins(48, 48, 48, 48)
        self.download_layout.setObjectName('download_layout')
        self.download_label = QtWidgets.QLabel(self.download_page)
        self.download_label.setObjectName('download_label')
        self.download_layout.addWidget(self.download_label)
        first_time_wizard.setPage(FirstTimePage.Download, self.download_page)
        # The "you don't have an internet connection" page.
        self.no_internet_page = QtWidgets.QWizardPage()
        self.no_internet_page.setObjectName('no_internet_page')
        self.no_internet_page.setFinalPage(True)
        self.no_internet_layout = QtWidgets.QVBoxLayout(self.no_internet_page)
        self.no_internet_layout.setContentsMargins(50, 30, 50, 40)
        self.no_internet_layout.setObjectName('no_internet_layout')
        self.no_internet_label = QtWidgets.QLabel(self.no_internet_page)
        self.no_internet_label.setWordWrap(True)
        self.no_internet_label.setObjectName('no_internet_label')
        self.no_internet_layout.addWidget(self.no_internet_label)
        first_time_wizard.setPage(FirstTimePage.NoInternet, self.no_internet_page)
        # The plugins page
        self.plugin_page = QtWidgets.QWizardPage()
        self.plugin_page.setObjectName('plugin_page')
        self.plugin_layout = QtWidgets.QVBoxLayout(self.plugin_page)
        self.plugin_layout.setContentsMargins(40, 15, 40, 0)
        self.plugin_layout.setObjectName('plugin_layout')
        self.songs_check_box = QtWidgets.QCheckBox(self.plugin_page)
        self.songs_check_box.setChecked(True)
        self.songs_check_box.setObjectName('songs_check_box')
        self.plugin_layout.addWidget(self.songs_check_box)
        self.custom_check_box = QtWidgets.QCheckBox(self.plugin_page)
        self.custom_check_box.setChecked(True)
        self.custom_check_box.setObjectName('custom_check_box')
        self.plugin_layout.addWidget(self.custom_check_box)
        self.bible_check_box = QtWidgets.QCheckBox(self.plugin_page)
        self.bible_check_box.setChecked(True)
        self.bible_check_box.setObjectName('bible_check_box')
        self.plugin_layout.addWidget(self.bible_check_box)
        self.image_check_box = QtWidgets.QCheckBox(self.plugin_page)
        self.image_check_box.setChecked(True)
        self.image_check_box.setObjectName('image_check_box')
        self.plugin_layout.addWidget(self.image_check_box)
        self.presentation_check_box = QtWidgets.QCheckBox(self.plugin_page)
        self.presentation_check_box.setChecked(True)
        self.presentation_check_box.setObjectName('presentation_check_box')
        self.plugin_layout.addWidget(self.presentation_check_box)
        self.media_check_box = QtWidgets.QCheckBox(self.plugin_page)
        self.media_check_box.setChecked(True)
        self.media_check_box.setObjectName('media_check_box')
        self.plugin_layout.addWidget(self.media_check_box)
        self.song_usage_check_box = QtWidgets.QCheckBox(self.plugin_page)
        self.song_usage_check_box.setChecked(True)
        self.song_usage_check_box.setObjectName('song_usage_check_box')
        self.plugin_layout.addWidget(self.song_usage_check_box)
        self.alert_check_box = QtWidgets.QCheckBox(self.plugin_page)
        self.alert_check_box.setChecked(True)
        self.alert_check_box.setObjectName('alert_check_box')
        self.plugin_layout.addWidget(self.alert_check_box)
        self.egw_library_check_box = QtWidgets.QCheckBox(self.plugin_page)
        self.egw_library_check_box.setChecked(True)
        self.egw_library_check_box.setObjectName('egw_library_check_box')
        self.plugin_layout.addWidget(self.egw_library_check_box)
        self.timer_check_box = QtWidgets.QCheckBox(self.plugin_page)
        self.timer_check_box.setChecked(True)
        self.timer_check_box.setObjectName('timer_check_box')
        self.plugin_layout.addWidget(self.timer_check_box)
        self.obs_studio_check_box = QtWidgets.QCheckBox(self.plugin_page)
        self.obs_studio_check_box.setChecked(False)
        self.obs_studio_check_box.setObjectName('obs_studio_check_box')
        self.plugin_layout.addWidget(self.obs_studio_check_box)
        first_time_wizard.setPage(FirstTimePage.Plugins, self.plugin_page)
        # Web Remote page
        self.remote_page = RemotePage(self)
        first_time_wizard.setPage(FirstTimePage.Remote, self.remote_page)
        # The song samples page
        self.songs_page = QtWidgets.QWizardPage()
        self.songs_page.setObjectName('songs_page')
        self.songs_layout = QtWidgets.QVBoxLayout(self.songs_page)
        self.songs_layout.setContentsMargins(50, 20, 50, 20)
        self.songs_layout.setObjectName('songs_layout')
        self.songs_list_widget = QtWidgets.QListWidget(self.songs_page)
        self.songs_list_widget.setAlternatingRowColors(True)
        self.songs_list_widget.setObjectName('songs_list_widget')
        self.songs_layout.addWidget(self.songs_list_widget)
        first_time_wizard.setPage(FirstTimePage.Songs, self.songs_page)
        # The Bible samples page
        self.bibles_page = QtWidgets.QWizardPage()
        self.bibles_page.setObjectName('bibles_page')
        self.bibles_layout = QtWidgets.QVBoxLayout(self.bibles_page)
        self.bibles_layout.setContentsMargins(50, 20, 50, 20)
        self.bibles_layout.setObjectName('bibles_layout')
        self.bibles_tree_widget = QtWidgets.QTreeWidget(self.bibles_page)
        self.bibles_tree_widget.setAlternatingRowColors(True)
        self.bibles_tree_widget.header().setVisible(False)
        self.bibles_tree_widget.setObjectName('bibles_tree_widget')
        self.bibles_layout.addWidget(self.bibles_tree_widget)
        first_time_wizard.setPage(FirstTimePage.Bibles, self.bibles_page)
        # The theme samples page
        self.themes_page = QtWidgets.QWizardPage()
        self.themes_page.setObjectName('themes_page')
        self.themes_layout = QtWidgets.QVBoxLayout(self.themes_page)
        self.themes_layout.setObjectName('themes_layout')
        self.themes_list_widget = ThemeListWidget(self.themes_page)
        self.themes_layout.addWidget(self.themes_list_widget)
        self.theme_options_layout = QtWidgets.QHBoxLayout()
        self.default_theme_layout = QtWidgets.QHBoxLayout()
        self.theme_label = QtWidgets.QLabel(self.themes_page)
        self.default_theme_layout.addWidget(self.theme_label)
        self.theme_combo_box = QtWidgets.QComboBox(self.themes_page)
        self.theme_combo_box.setEditable(False)
        self.default_theme_layout.addWidget(self.theme_combo_box, stretch=1)
        self.theme_options_layout.addLayout(self.default_theme_layout, stretch=1)
        self.select_buttons_layout = QtWidgets.QHBoxLayout()
        self.themes_select_all_button = QtWidgets.QToolButton(self.themes_page)
        self.themes_select_all_button.setIcon(UiIcons().select_all)
        self.select_buttons_layout.addWidget(self.themes_select_all_button, stretch=1,
                                             alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.themes_deselect_all_button = QtWidgets.QToolButton(self.themes_page)
        self.themes_deselect_all_button.setIcon(UiIcons().select_none)
        self.select_buttons_layout.addWidget(self.themes_deselect_all_button)
        self.theme_options_layout.addLayout(self.select_buttons_layout, stretch=1)
        self.themes_layout.addLayout(self.theme_options_layout)
        first_time_wizard.setPage(FirstTimePage.Themes, self.themes_page)
        # Progress page
        self.progress_page = QtWidgets.QWizardPage()
        self.progress_page.setObjectName('progress_page')
        self.progress_layout = QtWidgets.QVBoxLayout(self.progress_page)
        self.progress_layout.setContentsMargins(48, 48, 48, 48)
        self.progress_layout.setObjectName('progress_layout')
        self.progress_label = QtWidgets.QLabel(self.progress_page)
        self.progress_label.setObjectName('progress_label')
        self.progress_layout.addWidget(self.progress_label)
        self.progress_bar = QtWidgets.QProgressBar(self.progress_page)
        self.progress_bar.setObjectName('progress_bar')
        self.progress_layout.addWidget(self.progress_bar)
        first_time_wizard.setPage(FirstTimePage.Progress, self.progress_page)
        self.retranslate_ui()

    def retranslate_ui(self):
        """
        Translate the UI on the fly

        :param first_time_wizard: The wizard form
        """
        self.finish_button_text = clean_button_text(self.buttonText(QtWidgets.QWizard.WizardButton.FinishButton))
        back_button_text = clean_button_text(self.buttonText(QtWidgets.QWizard.WizardButton.BackButton))
        next_button_text = clean_button_text(self.buttonText(QtWidgets.QWizard.WizardButton.NextButton))

        self.setWindowTitle(translate('OpenLP.FirstTimeWizard', 'First Time Wizard'))
        text = translate('OpenLP.FirstTimeWizard', 'Welcome to the First Time Wizard')
        self.title_label.setText('<span style="font-size:14pt; font-weight:600;">{text}</span>'.format(text=text))
        self.information_label.setText(
            translate('OpenLP.FirstTimeWizard', 'This wizard will help you to configure OpenLP for initial use. '
                                                'Click the \'{next_button}\' button below to start.'
                      ).format(next_button=next_button_text))
        self.setButtonText(
            QtWidgets.QWizard.WizardButton.CustomButton1, translate('OpenLP.FirstTimeWizard', 'Internet Settings'))
        self.download_page.setTitle(translate('OpenLP.FirstTimeWizard', 'Downloading Resource Index'))
        self.download_page.setSubTitle(translate('OpenLP.FirstTimeWizard',
                                                 'Please wait while the resource index is downloaded.'))
        self.download_label.setText(translate('OpenLP.FirstTimeWizard',
                                              'Please wait while OpenLP downloads the resource index file...'))
        self.plugin_page.setTitle(translate('OpenLP.FirstTimeWizard', 'Select parts of the program you wish to use'))
        self.plugin_page.setSubTitle(translate('OpenLP.FirstTimeWizard',
                                               'You can also change these settings after the Wizard.'))
        self.screen_page.setTitle(translate('OpenLP.FirstTimeWizard', 'Displays'))
        self.screen_page.setSubTitle(translate('OpenLP.FirstTimeWizard',
                                               'Choose the main display screen for OpenLP.'))
        self.songs_check_box.setText(translate('OpenLP.FirstTimeWizard', 'Songs'))
        self.custom_check_box.setText(
            translate('OpenLP.FirstTimeWizard',
                      'Custom Slides – Easier to manage than songs and they have their own list of slides'))
        self.bible_check_box.setText(translate('OpenLP.FirstTimeWizard', 'Bibles – Import and show Bibles'))
        self.image_check_box.setText(translate('OpenLP.FirstTimeWizard',
                                               'Images – Show images or replace background with them'))
        self.presentation_check_box.setText(translate('OpenLP.FirstTimeWizard',
                                                      'Presentations – Show .ppt, .odp and .pdf files'))
        self.media_check_box.setText(translate('OpenLP.FirstTimeWizard', 'Media – Playback of Audio and Video files'))
        self.song_usage_check_box.setText(translate('OpenLP.FirstTimeWizard', 'Song Usage Monitor'))
        self.alert_check_box.setText(translate('OpenLP.FirstTimeWizard',
                                               'Alerts – Display informative messages while showing other slides'))
        self.egw_library_check_box.setText(
            translate('OpenLP.FirstTimeWizard', 'EGW Library - Search and display EGW writings')
        )
        self.timer_check_box.setText(
            translate('OpenLP.FirstTimeWizard', 'Clock (Timer) - Countdown and count-up timer overlays')
        )
        self.obs_studio_check_box.setText(
            translate('OpenLP.FirstTimeWizard', 'OBS Studio - Control scenes directly from OpenLP')
        )
        self.resource_page.setTitle(translate('OpenLP.FirstTimeWizard', 'Resource Data'))
        self.resource_page.setSubTitle(translate('OpenLP.FirstTimeWizard', 'Can OpenLP download some resource data?'))
        self.resource_label.setText(
            translate('OpenLP.FirstTimeWizard',
                      'OpenLP has collected some resources that we have permission to distribute.\n\n'
                      'If you would like to download some of these resources click the \'{next_button}\' button, '
                      'otherwise click the \'{finish_button}\' button.'
                      ).format(next_button=next_button_text, finish_button=self.finish_button_text))
        self.no_internet_page.setTitle(translate('OpenLP.FirstTimeWizard', 'No Internet Connection'))
        self.no_internet_page.setSubTitle(translate('OpenLP.FirstTimeWizard', 'Cannot connect to the internet.'))
        self.no_internet_label.setText(
            translate('OpenLP.FirstTimeWizard',
                      'OpenLP could not connect to the internet to get information about the sample data available.\n\n'
                      'Please check your internet connection. If your church uses a proxy server click the '
                      '\'Internet Settings\' button below and enter the server details there.\n\nClick the '
                      '\'{back_button}\' button to try again.\n\nIf you click the \'{finish_button}\' '
                      'button you can download the data at a later time by selecting \'Re-run First Time Wizard\' '
                      'from the \'Tools\' menu in OpenLP.'
                      ).format(back_button=back_button_text, finish_button=self.finish_button_text))
        self.songs_page.setTitle(translate('OpenLP.FirstTimeWizard', 'Sample Songs'))
        self.songs_page.setSubTitle(translate('OpenLP.FirstTimeWizard', 'Select and download public domain songs.'))
        self.bibles_page.setTitle(translate('OpenLP.FirstTimeWizard', 'Sample Bibles'))
        self.bibles_page.setSubTitle(translate('OpenLP.FirstTimeWizard', 'Select and download free Bibles.'))
        # Themes Page
        self.themes_page.setTitle(translate('OpenLP.FirstTimeWizard', 'Sample Themes'))
        self.themes_page.setSubTitle(translate('OpenLP.FirstTimeWizard', 'Select and download sample themes.'))
        self.theme_label.setText(translate('OpenLP.FirstTimeWizard', 'Default theme:'))
        self.themes_select_all_button.setToolTip(translate('OpenLP.FirstTimeWizard', 'Select all'))
        self.themes_deselect_all_button.setToolTip(translate('OpenLP.FirstTimeWizard', 'Deselect all'))
        self.progress_page.setTitle(translate('OpenLP.FirstTimeWizard', 'Downloading and Configuring'))
        self.progress_page.setSubTitle(
            translate('OpenLP.FirstTimeWizard', 'Please wait while resources are downloaded and OpenLP is configured.'))
