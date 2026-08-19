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
The bible import functions for OpenLP
"""
import logging
import urllib.error
from csv import Error as CSVError, reader
from pathlib import Path

from lxml import etree
from PySide6 import QtWidgets, QtGui, QtCore

try:
    from pysword import modules
    PYSWORD_AVAILABLE = True
except ImportError:
    PYSWORD_AVAILABLE = False

from openlp.core.common import trace_error_handler
from openlp.core.common.applocation import AppLocation
from openlp.core.common.i18n import UiStrings, get_locale_key, translate
from openlp.core.db.helpers import delete_database
from openlp.core.lib.exceptions import ValidationError
from openlp.core.lib.ui import critical_error_message_box
from openlp.core.widgets.enums import PathEditType
from openlp.core.widgets.edits import PathEdit
from openlp.core.widgets.wizard import OpenLPWizard, WizardStrings
from openlp.plugins.bibles.lib.db import clean_filename
from openlp.plugins.bibles.lib.importers.http import BGExtract, CWExtract, BSExtract
from openlp.plugins.bibles.lib.manager import BibleFormat


log = logging.getLogger(__name__)


class WebDownload(object):
    """
    Provides an enumeration for the web bible types available to OpenLP.
    """
    Unknown = -1
    Crosswalk = 0
    BibleGateway = 1
    BibleServer = 2

    Names = ['Crosswalk', 'BibleGateway', 'BibleServer']


class BibleImportForm(OpenLPWizard):
    """
    This is the Bible Import Wizard, which allows easy importing of Bibles into OpenLP from other formats like OSIS,
    CSV and OpenSong.
    """
    log.info('BibleImportForm loaded')

    def __init__(self, parent, manager, bible_plugin):
        """
        Instantiate the wizard, and run any extra setup we need to.

        :param parent: The QWidget-derived parent of the wizard.
        :param manager: The Bible manager.
        :param bible_plugin: The Bible plugin.
        """
        self.manager = manager
        self.web_bible_list = {}
        super(BibleImportForm, self).__init__(parent, bible_plugin,
                                              'bibleImportWizard', ':/wizards/wizard_importbible.bmp')

    def setup_ui(self, image):
        """
        Set up the UI for the bible wizard.
        """
        super(BibleImportForm, self).setup_ui(image)
        self.format_combo_box.currentIndexChanged.connect(self.on_current_index_changed)

    def on_current_index_changed(self, index):
        """
        Called when the format combo box's index changed. We have to check if
        the import is available and accordingly to disable or enable the next
        button.
        """
        self.select_stack.setCurrentIndex(index)

    def custom_init(self):
        """
        Perform any custom initialisation for bible importing.
        """
        self.manager.set_process_dialog(self)
        self.restart()
        self.select_stack.setCurrentIndex(0)
        if PYSWORD_AVAILABLE:
            self.pysword_folder_modules = modules.SwordModules()
            try:
                self.pysword_folder_modules_json = self.pysword_folder_modules.parse_modules()
            except FileNotFoundError:
                log.debug('No installed SWORD modules found in the default location')
                self.sword_bible_combo_box.clear()
                return
            bible_keys = self.pysword_folder_modules_json.keys()
            for key in bible_keys:
                self.sword_bible_combo_box.addItem(self.pysword_folder_modules_json[key]['description'], key)
        else:
            self.sword_tab_widget.setDisabled(True)

    def custom_signals(self):
        """
        Set up the signals used in the bible importer.
        """
        self.web_source_combo_box.currentIndexChanged.connect(self.on_web_source_combo_box_index_changed)
        self.web_update_button.clicked.connect(self.on_web_update_button_clicked)
        self.osis_path_edit.pathChanged.connect(
            lambda path: self.on_format_source_path_changed(path, BibleFormat.OSIS))
        self.open_song_path_edit.pathChanged.connect(
            lambda path: self.on_format_source_path_changed(path, BibleFormat.OpenSong))
        self.zefania_path_edit.pathChanged.connect(
            lambda path: self.on_format_source_path_changed(path, BibleFormat.Zefania))
        self.wordproject_path_edit.pathChanged.connect(
            lambda path: self.on_format_source_path_changed(path, BibleFormat.WordProject))
        self.sword_folder_path_edit.pathChanged.connect(self.on_sword_folder_path_edit_path_changed)
        self.sword_zipfile_path_edit.pathChanged.connect(self.on_sword_zipfile_path_edit_path_changed)

    def add_custom_pages(self):
        """
        Add the bible import specific wizard pages.
        """
        # Select Page
        self.select_page = QtWidgets.QWizardPage()
        self.select_page.setObjectName('SelectPage')
        self.select_page_layout = QtWidgets.QVBoxLayout(self.select_page)
        self.select_page_layout.setObjectName('SelectPageLayout')
        self.format_layout = QtWidgets.QFormLayout()
        self.format_layout.setObjectName('FormatLayout')
        self.format_label = QtWidgets.QLabel(self.select_page)
        self.format_label.setObjectName('FormatLabel')
        self.format_combo_box = QtWidgets.QComboBox(self.select_page)
        self.format_combo_box.addItems(['', '', '', '', '', '', ''])
        self.format_combo_box.setObjectName('FormatComboBox')
        self.format_layout.addRow(self.format_label, self.format_combo_box)
        self.format_hint_label = QtWidgets.QLabel(self.select_page)
        self.format_hint_label.setObjectName('FormatHintLabel')
        self.format_hint_label.setWordWrap(True)
        self.format_layout.addRow('', self.format_hint_label)
        self.supported_formats_label = QtWidgets.QLabel(self.select_page)
        self.supported_formats_label.setObjectName('SupportedFormatsLabel')
        self.supported_formats_label.setWordWrap(True)
        self.format_layout.addRow('', self.supported_formats_label)
        self.format_spacer = QtWidgets.QSpacerItem(10, 0, QtWidgets.QSizePolicy.Policy.Fixed,
                                                   QtWidgets.QSizePolicy.Policy.Minimum)
        self.format_layout.setItem(3, QtWidgets.QFormLayout.ItemRole.LabelRole, self.format_spacer)
        self.select_page_layout.addLayout(self.format_layout)
        self.select_stack = QtWidgets.QStackedLayout()
        self.select_stack.setObjectName('SelectStack')
        self.osis_widget = QtWidgets.QWidget(self.select_page)
        self.osis_widget.setObjectName('OsisWidget')
        self.osis_layout = QtWidgets.QFormLayout(self.osis_widget)
        self.osis_layout.setContentsMargins(0, 0, 0, 0)
        self.osis_layout.setObjectName('OsisLayout')
        self.osis_file_label = QtWidgets.QLabel(self.osis_widget)
        self.osis_file_label.setObjectName('OsisFileLabel')
        self.osis_path_edit = PathEdit(
            self.osis_widget,
            default_path=self.settings.value('bibles/last directory import'),
            dialog_caption=WizardStrings.OpenTypeFile.format(file_type=WizardStrings.OSIS),
            show_revert=False)
        self.osis_path_edit.filters = '{name} (*.xml *.osis *.xmm *.txt);;{all} (*)'.format(
            name=translate('BiblesPlugin.ImportWizardForm', 'OSIS XML Files'),
            all=UiStrings().AllFiles)
        self.osis_layout.addRow(self.osis_file_label, self.osis_path_edit)
        self.osis_spacer = QtWidgets.QSpacerItem(10, 0, QtWidgets.QSizePolicy.Policy.Fixed,
                                                 QtWidgets.QSizePolicy.Policy.Minimum)
        self.osis_layout.setItem(1, QtWidgets.QFormLayout.ItemRole.LabelRole, self.osis_spacer)
        self.select_stack.addWidget(self.osis_widget)
        self.csv_widget = QtWidgets.QWidget(self.select_page)
        self.csv_widget.setObjectName('CsvWidget')
        self.csv_layout = QtWidgets.QFormLayout(self.csv_widget)
        self.csv_layout.setContentsMargins(0, 0, 0, 0)
        self.csv_layout.setObjectName('CsvLayout')
        self.csv_books_label = QtWidgets.QLabel(self.csv_widget)
        self.csv_books_label.setObjectName('CsvBooksLabel')
        self.csv_books_path_edit = PathEdit(
            self.csv_widget,
            default_path=self.settings.value('bibles/last directory import'),
            dialog_caption=WizardStrings.OpenTypeFile.format(file_type=WizardStrings.CSV),
            show_revert=False,
        )
        self.csv_books_path_edit.filters = \
            '{name} (*.csv *.txt);;{all} (*)'.format(
                name=translate('BiblesPlugin.ImportWizardForm', 'CSV File'),
                all=UiStrings().AllFiles)
        self.csv_layout.addRow(self.csv_books_label, self.csv_books_path_edit)
        self.csv_verses_label = QtWidgets.QLabel(self.csv_widget)
        self.csv_verses_label.setObjectName('CsvVersesLabel')
        self.csv_verses_path_edit = PathEdit(
            self.csv_widget,
            default_path=self.settings.value('bibles/last directory import'),
            dialog_caption=WizardStrings.OpenTypeFile.format(file_type=WizardStrings.CSV),
            show_revert=False,
        )
        self.csv_verses_path_edit.filters = \
            '{name} (*.csv *.txt);;{all} (*)'.format(
                name=translate('BiblesPlugin.ImportWizardForm', 'CSV File'),
                all=UiStrings().AllFiles)
        self.csv_layout.addRow(self.csv_books_label, self.csv_books_path_edit)
        self.csv_layout.addRow(self.csv_verses_label, self.csv_verses_path_edit)
        self.csv_help_label = QtWidgets.QLabel(self.csv_widget)
        self.csv_help_label.setObjectName('CsvHelpLabel')
        self.csv_help_label.setWordWrap(True)
        self.csv_layout.addRow(self.csv_help_label)
        self.csv_spacer = QtWidgets.QSpacerItem(10, 0, QtWidgets.QSizePolicy.Policy.Fixed,
                                                QtWidgets.QSizePolicy.Policy.Minimum)
        self.csv_layout.setItem(4, QtWidgets.QFormLayout.ItemRole.LabelRole, self.csv_spacer)
        self.select_stack.addWidget(self.csv_widget)
        self.open_song_widget = QtWidgets.QWidget(self.select_page)
        self.open_song_widget.setObjectName('OpenSongWidget')
        self.open_song_layout = QtWidgets.QFormLayout(self.open_song_widget)
        self.open_song_layout.setContentsMargins(0, 0, 0, 0)
        self.open_song_layout.setObjectName('OpenSongLayout')
        self.open_song_file_label = QtWidgets.QLabel(self.open_song_widget)
        self.open_song_file_label.setObjectName('OpenSongFileLabel')
        self.open_song_path_edit = PathEdit(
            self.open_song_widget,
            default_path=self.settings.value('bibles/last directory import'),
            dialog_caption=WizardStrings.OpenTypeFile.format(file_type=WizardStrings.OS),
            show_revert=False,
        )
        self.open_song_path_edit.filters = '{name} (*.xml *.xmm *.txt);;{all} (*)'.format(
            name=translate('BiblesPlugin.ImportWizardForm', 'OpenSong XML Files'),
            all=UiStrings().AllFiles)
        self.open_song_layout.addRow(self.open_song_file_label, self.open_song_path_edit)
        self.opensong_spacer = QtWidgets.QSpacerItem(10, 0, QtWidgets.QSizePolicy.Policy.Fixed,
                                                     QtWidgets.QSizePolicy.Policy.Minimum)
        self.open_song_layout.setItem(1, QtWidgets.QFormLayout.ItemRole.LabelRole, self.opensong_spacer)
        self.select_stack.addWidget(self.open_song_widget)
        self.web_widget = QtWidgets.QWidget(self.select_page)
        self.web_widget.setObjectName('WebWidget')
        self.web_bible_tab = QtWidgets.QWidget()
        self.web_bible_tab.setObjectName('WebBibleTab')
        self.web_bible_layout = QtWidgets.QFormLayout(self.web_widget)
        self.web_bible_layout.setObjectName('WebBibleLayout')
        self.web_update_label = QtWidgets.QLabel(self.web_widget)
        self.web_update_label.setObjectName('WebUpdateLabel')
        self.web_bible_layout.setWidget(0, QtWidgets.QFormLayout.ItemRole.LabelRole, self.web_update_label)
        self.web_update_button = QtWidgets.QPushButton(self.web_widget)
        self.web_update_button.setObjectName('WebUpdateButton')
        self.web_bible_layout.setWidget(0, QtWidgets.QFormLayout.ItemRole.FieldRole, self.web_update_button)
        self.web_source_label = QtWidgets.QLabel(self.web_widget)
        self.web_source_label.setObjectName('WebSourceLabel')
        self.web_bible_layout.setWidget(1, QtWidgets.QFormLayout.ItemRole.LabelRole, self.web_source_label)
        self.web_source_combo_box = QtWidgets.QComboBox(self.web_widget)
        self.web_source_combo_box.setObjectName('WebSourceComboBox')
        self.web_source_combo_box.addItems(['', '', ''])
        self.web_source_combo_box.setEnabled(False)
        self.web_bible_layout.setWidget(1, QtWidgets.QFormLayout.ItemRole.FieldRole, self.web_source_combo_box)
        self.web_translation_label = QtWidgets.QLabel(self.web_bible_tab)
        self.web_translation_label.setObjectName('web_translation_label')
        self.web_bible_layout.setWidget(2, QtWidgets.QFormLayout.ItemRole.LabelRole, self.web_translation_label)
        self.web_translation_combo_box = QtWidgets.QComboBox(self.web_bible_tab)
        self.web_translation_combo_box.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.web_translation_combo_box.setObjectName('WebTranslationComboBox')
        self.web_translation_combo_box.setEnabled(False)
        self.web_bible_layout.setWidget(2, QtWidgets.QFormLayout.ItemRole.FieldRole, self.web_translation_combo_box)
        self.web_progress_bar = QtWidgets.QProgressBar(self)
        self.web_progress_bar.setRange(0, 3)
        self.web_progress_bar.setObjectName('WebTranslationProgressBar')
        self.web_progress_bar.setVisible(False)
        self.web_bible_layout.setWidget(3, QtWidgets.QFormLayout.ItemRole.SpanningRole, self.web_progress_bar)
        self.select_stack.addWidget(self.web_widget)
        self.zefania_widget = QtWidgets.QWidget(self.select_page)
        self.zefania_widget.setObjectName('ZefaniaWidget')
        self.zefania_layout = QtWidgets.QFormLayout(self.zefania_widget)
        self.zefania_layout.setContentsMargins(0, 0, 0, 0)
        self.zefania_layout.setObjectName('ZefaniaLayout')
        self.zefania_file_label = QtWidgets.QLabel(self.zefania_widget)
        self.zefania_file_label.setObjectName('ZefaniaFileLabel')
        self.zefania_path_edit = PathEdit(
            self.zefania_widget,
            default_path=self.settings.value('bibles/last directory import'),
            dialog_caption=WizardStrings.OpenTypeFile.format(file_type=WizardStrings.ZEF),
            show_revert=False,
        )
        self.zefania_path_edit.filters = '{name} (*.xml *.xmm *.txt);;{all} (*)'.format(
            name=translate('BiblesPlugin.ImportWizardForm', 'Zefania XML Files'),
            all=UiStrings().AllFiles)
        self.zefania_layout.addRow(self.zefania_file_label, self.zefania_path_edit)
        self.zefania_spacer = QtWidgets.QSpacerItem(10, 0, QtWidgets.QSizePolicy.Policy.Fixed,
                                                    QtWidgets.QSizePolicy.Policy.Minimum)
        self.zefania_layout.setItem(2, QtWidgets.QFormLayout.ItemRole.LabelRole, self.zefania_spacer)
        self.select_stack.addWidget(self.zefania_widget)
        self.sword_widget = QtWidgets.QWidget(self.select_page)
        self.sword_widget.setObjectName('SwordWidget')
        self.sword_layout = QtWidgets.QVBoxLayout(self.sword_widget)
        self.sword_layout.setContentsMargins(0, 0, 0, 0)
        self.sword_layout.setObjectName('SwordLayout')
        self.sword_tab_widget = QtWidgets.QTabWidget(self.sword_widget)
        self.sword_tab_widget.setObjectName('SwordTabWidget')
        self.sword_folder_tab = QtWidgets.QWidget(self.sword_tab_widget)
        self.sword_folder_tab.setObjectName('SwordFolderTab')
        self.sword_folder_tab_layout = QtWidgets.QFormLayout(self.sword_folder_tab)
        self.sword_folder_tab_layout.setObjectName('SwordTabFolderLayout')
        self.sword_folder_label = QtWidgets.QLabel(self.sword_folder_tab)
        self.sword_folder_label.setObjectName('SwordSourceLabel')
        self.sword_folder_label.setObjectName('SwordFolderLabel')
        self.sword_folder_path_edit = PathEdit(
            self.sword_folder_tab,
            path_type=PathEditType.Directories,
            default_path=self.settings.value('bibles/last directory import'),
            dialog_caption=WizardStrings.OpenTypeFile.format(file_type=WizardStrings.SWORD),
            show_revert=False,
        )
        self.sword_folder_tab_layout.addRow(self.sword_folder_label, self.sword_folder_path_edit)
        self.sword_bible_label = QtWidgets.QLabel(self.sword_folder_tab)
        self.sword_bible_label.setObjectName('SwordBibleLabel')
        self.sword_bible_combo_box = QtWidgets.QComboBox(self.sword_folder_tab)
        self.sword_bible_combo_box.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.sword_bible_combo_box.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.InsertAlphabetically)
        self.sword_bible_combo_box.setObjectName('SwordBibleComboBox')
        self.sword_folder_tab_layout.addRow(self.sword_bible_label, self.sword_bible_combo_box)
        self.sword_tab_widget.addTab(self.sword_folder_tab, '')
        self.sword_zip_tab = QtWidgets.QWidget(self.sword_tab_widget)
        self.sword_zip_tab.setObjectName('SwordZipTab')
        self.sword_zip_layout = QtWidgets.QFormLayout(self.sword_zip_tab)
        self.sword_zip_layout.setObjectName('SwordZipLayout')
        self.sword_zipfile_label = QtWidgets.QLabel(self.sword_zip_tab)
        self.sword_zipfile_label.setObjectName('SwordZipFileLabel')
        self.sword_zipfile_path_edit = PathEdit(
            self.sword_zip_tab,
            default_path=self.settings.value('bibles/last directory import'),
            dialog_caption=WizardStrings.OpenTypeFile.format(file_type=WizardStrings.SWORD),
            show_revert=False,
        )
        self.sword_zip_layout.addRow(self.sword_zipfile_label, self.sword_zipfile_path_edit)
        self.sword_zipbible_label = QtWidgets.QLabel(self.sword_folder_tab)
        self.sword_zipbible_label.setObjectName('SwordZipBibleLabel')
        self.sword_zipbible_combo_box = QtWidgets.QComboBox(self.sword_zip_tab)
        self.sword_zipbible_combo_box.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.sword_zipbible_combo_box.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.InsertAlphabetically)
        self.sword_zipbible_combo_box.setObjectName('SwordZipBibleComboBox')
        self.sword_zip_layout.addRow(self.sword_zipbible_label, self.sword_zipbible_combo_box)
        self.sword_tab_widget.addTab(self.sword_zip_tab, '')
        self.sword_layout.addWidget(self.sword_tab_widget)
        self.sword_disabled_label = QtWidgets.QLabel(self.sword_widget)
        self.sword_disabled_label.setObjectName('SwordDisabledLabel')
        self.sword_disabled_label.setWordWrap(True)
        self.sword_layout.addWidget(self.sword_disabled_label)
        self.select_stack.addWidget(self.sword_widget)
        self.wordproject_widget = QtWidgets.QWidget(self.select_page)
        self.wordproject_widget.setObjectName('WordProjectWidget')
        self.wordproject_layout = QtWidgets.QFormLayout(self.wordproject_widget)
        self.wordproject_layout.setContentsMargins(0, 0, 0, 0)
        self.wordproject_layout.setObjectName('WordProjectLayout')
        self.wordproject_file_label = QtWidgets.QLabel(self.wordproject_widget)
        self.wordproject_file_label.setObjectName('WordProjectFileLabel')
        self.wordproject_path_edit = PathEdit(
            self.wordproject_widget,
            default_path=self.settings.value('bibles/last directory import'),
            dialog_caption=WizardStrings.OpenTypeFile.format(file_type=WizardStrings.WordProject),
            show_revert=False)
        self.wordproject_path_edit.filters = '{name} (*.zip);;{all} (*)'.format(
            name=translate('BiblesPlugin.ImportWizardForm', 'WordProject ZIP Files'),
            all=UiStrings().AllFiles)
        self.wordproject_layout.addRow(self.wordproject_file_label, self.wordproject_path_edit)
        self.wordproject_spacer = QtWidgets.QSpacerItem(10, 0, QtWidgets.QSizePolicy.Policy.Fixed,
                                                        QtWidgets.QSizePolicy.Policy.Minimum)
        self.wordproject_layout.setItem(1, QtWidgets.QFormLayout.ItemRole.LabelRole, self.wordproject_spacer)
        self.select_stack.addWidget(self.wordproject_widget)
        self.select_page_layout.addLayout(self.select_stack)
        self.addPage(self.select_page)
        # License Page
        self.license_details_page = QtWidgets.QWizardPage()
        self.license_details_page.setObjectName('LicenseDetailsPage')
        self.license_details_layout = QtWidgets.QFormLayout(self.license_details_page)
        self.license_details_layout.setObjectName('LicenseDetailsLayout')
        self.version_name_label = QtWidgets.QLabel(self.license_details_page)
        self.version_name_label.setObjectName('VersionNameLabel')
        self.license_details_layout.setWidget(0, QtWidgets.QFormLayout.ItemRole.LabelRole, self.version_name_label)
        self.version_name_edit = QtWidgets.QLineEdit(self.license_details_page)
        self.version_name_edit.setObjectName('VersionNameEdit')
        self.license_details_layout.setWidget(0, QtWidgets.QFormLayout.ItemRole.FieldRole, self.version_name_edit)
        self.copyright_label = QtWidgets.QLabel(self.license_details_page)
        self.copyright_label.setObjectName('CopyrightLabel')
        self.license_details_layout.setWidget(1, QtWidgets.QFormLayout.ItemRole.LabelRole, self.copyright_label)
        self.copyright_edit = QtWidgets.QLineEdit(self.license_details_page)
        self.copyright_edit.setObjectName('CopyrightEdit')
        self.license_details_layout.setWidget(1, QtWidgets.QFormLayout.ItemRole.FieldRole, self.copyright_edit)
        self.permissions_label = QtWidgets.QLabel(self.license_details_page)
        self.permissions_label.setObjectName('PermissionsLabel')
        self.license_details_layout.setWidget(2, QtWidgets.QFormLayout.ItemRole.LabelRole, self.permissions_label)
        self.permissions_edit = QtWidgets.QLineEdit(self.license_details_page)
        self.permissions_edit.setObjectName('PermissionsEdit')
        self.license_details_layout.setWidget(2, QtWidgets.QFormLayout.ItemRole.FieldRole, self.permissions_edit)
        self.full_license_label = QtWidgets.QLabel(self.license_details_page)
        self.full_license_label.setObjectName('FullLicenseLabel')
        self.license_details_layout.setWidget(3, QtWidgets.QFormLayout.ItemRole.LabelRole, self.full_license_label)
        self.full_license_edit = QtWidgets.QPlainTextEdit(self.license_details_page)
        self.full_license_edit.setObjectName('FullLicenseEdit')
        self.license_details_layout.setWidget(3, QtWidgets.QFormLayout.ItemRole.FieldRole, self.full_license_edit)
        self.addPage(self.license_details_page)

    def retranslate_ui(self):
        """
        Allow for localisation of the bible import wizard.
        """
        self.setWindowTitle(translate('BiblesPlugin.ImportWizardForm', 'Bible Import Wizard'))
        self.title_label.setText(WizardStrings.HeaderStyle.format(text=translate('OpenLP.Ui',
                                                                                 'Welcome to the Bible Import Wizard')))
        self.information_label.setText(
            translate('BiblesPlugin.ImportWizardForm',
                      'This wizard will help you to import Bibles from a variety of '
                      'formats. Click the next button below to start the process by '
                      'selecting a format to import from.'))
        self.select_page.setTitle(WizardStrings.ImportSelect)
        self.select_page.setSubTitle(WizardStrings.ImportSelectLong)
        self.format_label.setText(WizardStrings.FormatLabel)
        self.format_hint_label.setText(
            translate('BiblesPlugin.ImportWizardForm',
                      'Tip: If you are unsure, select your file first. OpenLP will try to detect a matching format.'))
        self.supported_formats_label.setText(
            translate('BiblesPlugin.ImportWizardForm',
                      'Supported formats:\n'
                      '- OSIS: .osis, .xml\n'
                      '- CSV: .csv/.txt (requires 2 files: Books and Verses)\n'
                      '- OpenSong: .xml\n'
                      '- Zefania: .xml, .xmm\n'
                      '- WordProject: .zip\n'
                      '- SWORD: module folder or zip package'))
        self.format_combo_box.setItemText(BibleFormat.OSIS, WizardStrings.OSIS)
        self.format_combo_box.setItemText(BibleFormat.CSV, WizardStrings.CSV)
        self.format_combo_box.setItemText(BibleFormat.OpenSong, WizardStrings.OS)
        self.format_combo_box.setItemText(BibleFormat.WordProject, WizardStrings.WordProject)
        self.format_combo_box.setItemText(BibleFormat.WebDownload, translate('BiblesPlugin.ImportWizardForm',
                                                                             'Web Download'))
        self.format_combo_box.setItemText(BibleFormat.Zefania, WizardStrings.ZEF)
        self.format_combo_box.setItemText(BibleFormat.SWORD, WizardStrings.SWORD)
        self.osis_file_label.setText(translate('BiblesPlugin.ImportWizardForm', 'Bible file:'))
        self.csv_books_label.setText(translate('BiblesPlugin.ImportWizardForm', 'Books file:'))
        self.csv_verses_label.setText(translate('BiblesPlugin.ImportWizardForm', 'Verses file:'))
        self.csv_help_label.setText(translate('BiblesPlugin.ImportWizardForm',
                                              'CSV import requires two files:\n'
                                              '1) Books file (book names/order)\n'
                                              '2) Verses file (verse text)\n'
                                              'Accepted file types: .csv or .txt'))
        self.open_song_file_label.setText(translate('BiblesPlugin.ImportWizardForm', 'Bible file:'))
        self.web_source_label.setText(translate('BiblesPlugin.ImportWizardForm', 'Location:'))
        self.zefania_file_label.setText(translate('BiblesPlugin.ImportWizardForm', 'Bible file:'))
        self.wordproject_file_label.setText(translate('BiblesPlugin.ImportWizardForm', 'Bible file:'))
        self.web_update_label.setText(translate('BiblesPlugin.ImportWizardForm', 'Click to download bible list'))
        self.web_update_button.setText(translate('BiblesPlugin.ImportWizardForm', 'Download bible list'))
        self.web_source_combo_box.setItemText(WebDownload.Crosswalk, translate('BiblesPlugin.ImportWizardForm',
                                                                               'Crosswalk'))
        self.web_source_combo_box.setItemText(WebDownload.BibleGateway, translate('BiblesPlugin.ImportWizardForm',
                                                                                  'BibleGateway'))
        self.web_source_combo_box.setItemText(WebDownload.BibleServer, translate('BiblesPlugin.ImportWizardForm',
                                                                                 'Bibleserver'))
        self.web_translation_label.setText(translate('BiblesPlugin.ImportWizardForm', 'Bible:'))
        self.sword_bible_label.setText(translate('BiblesPlugin.ImportWizardForm', 'Bibles:'))
        self.sword_folder_label.setText(translate('BiblesPlugin.ImportWizardForm', 'SWORD data folder:'))
        self.sword_zipfile_label.setText(translate('BiblesPlugin.ImportWizardForm', 'SWORD zip-file:'))
        self.sword_zipbible_label.setText(translate('BiblesPlugin.ImportWizardForm', 'Bibles:'))
        self.sword_tab_widget.setTabText(self.sword_tab_widget.indexOf(self.sword_folder_tab),
                                         translate('BiblesPlugin.ImportWizardForm', 'Import from folder'))
        self.sword_tab_widget.setTabText(self.sword_tab_widget.indexOf(self.sword_zip_tab),
                                         translate('BiblesPlugin.ImportWizardForm', 'Import from Zip-file'))
        if PYSWORD_AVAILABLE:
            self.sword_disabled_label.setText('')
        else:
            self.sword_disabled_label.setText(translate('BiblesPlugin.ImportWizardForm',
                                                        'To import SWORD bibles the pysword python module must be '
                                                        'installed. Please read the manual for instructions.'))
        self.license_details_page.setTitle(
            translate('BiblesPlugin.ImportWizardForm', 'License Details'))
        self.license_details_page.setSubTitle(translate('BiblesPlugin.ImportWizardForm',
                                                        'Set up the Bible\'s license details.'))
        self.version_name_label.setText(translate('BiblesPlugin.ImportWizardForm', 'Version name:'))
        self.copyright_label.setText(translate('BiblesPlugin.ImportWizardForm', 'Copyright:'))
        self.permissions_label.setText(translate('BiblesPlugin.ImportWizardForm', 'Permissions:'))
        self.full_license_label.setText(translate('BiblesPlugin.ImportWizardForm', 'Full license:'))
        self.progress_page.setTitle(WizardStrings.Importing)
        self.progress_page.setSubTitle(translate('BiblesPlugin.ImportWizardForm',
                                                 'Please wait while your Bible is imported.'))
        self.progress_label.setText(WizardStrings.Ready)
        self.progress_bar.setFormat('%p%')
        # Align all QFormLayouts towards each other.
        label_width = max(self.format_label.minimumSizeHint().width(),
                          self.osis_file_label.minimumSizeHint().width(),
                          self.csv_books_label.minimumSizeHint().width(),
                          self.csv_verses_label.minimumSizeHint().width(),
                          self.open_song_file_label.minimumSizeHint().width(),
                          self.zefania_file_label.minimumSizeHint().width())
        for spacer in [self.format_spacer, self.osis_spacer, self.csv_spacer, self.opensong_spacer,
                       self.zefania_spacer, self.wordproject_spacer]:
            spacer.changeSize(label_width, 0,
                              QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)

    def detect_bible_format_from_path(self, file_path):
        """
        Try to infer the Bible format from the selected source file.

        :param file_path: The selected file path
        :return: tuple[int | None, str | None]
        """
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix == '.zip':
            return BibleFormat.WordProject, 'WordProject ZIP'
        if suffix == '.csv':
            return BibleFormat.CSV, 'CSV'
        if suffix == '.osis':
            return BibleFormat.OSIS, 'OSIS XML'
        detected_xml_format, detected_xml_name = self._detect_xml_root_format(path)
        if detected_xml_format is not None:
            return detected_xml_format, detected_xml_name
        if self._looks_like_csv_text(path):
            return BibleFormat.CSV, 'CSV text'
        return None, None

    def _detect_xml_root_format(self, path):
        """
        Detect XML-based Bible formats from root tag regardless of file extension.
        """
        try:
            root_tag = etree.iterparse(str(path), events=('start',), huge_tree=False)
            root_name = None
            for _, element in root_tag:
                root_name = element.tag.lower()
                break
            if root_name is None:
                return None, None
            if root_name.endswith('osis'):
                return BibleFormat.OSIS, 'OSIS XML'
            if root_name == 'bible':
                return BibleFormat.OpenSong, 'OpenSong XML'
            if root_name == 'xmlbible':
                return BibleFormat.Zefania, 'Zefania XML'
        except (OSError, etree.XMLSyntaxError, ValueError):
            log.debug('Could not detect XML root for %s', path)
        return None, None

    def _looks_like_csv_text(self, path):
        """
        Heuristic check for CSV-like content (including .txt sources).
        """
        try:
            lines = []
            with path.open('r', encoding='utf-8', errors='ignore') as file_handle:
                for line in file_handle:
                    if line.strip():
                        lines.append(line.strip())
                    if len(lines) >= 2:
                        break
            if not lines:
                return False
            sample_rows = list(reader(lines))
            if not sample_rows:
                return False
            row1 = sample_rows[0]
            row2 = sample_rows[1] if len(sample_rows) > 1 else []
            if len(row1) < 4:
                return False
            if not row2:
                return row1.count(',') >= 3
            if len(row2) < 4:
                return False
            if row1[0].isdigit() and row1[1].isdigit():
                return True
            if row1[1].isdigit() and row1[2].isdigit():
                return True
            if row2[0].isdigit() and row2[1].isdigit():
                return True
            if row2[1].isdigit() and row2[2].isdigit():
                return True
        except (OSError, UnicodeError, CSVError):
            return False
        return False

    def on_format_source_path_changed(self, new_path, expected_format):
        """
        Try to auto-detect and align source format selection based on selected file.
        """
        if not new_path:
            return
        detected_format, detected_name = self.detect_bible_format_from_path(new_path)
        if detected_format is None:
            self.format_hint_label.setText(
                translate('BiblesPlugin.ImportWizardForm',
                          'OpenLP could not detect this file automatically. '
                          'Check the Supported formats list and continue only if your file matches one of them.'))
            return
        if detected_format != expected_format:
            self.format_combo_box.setCurrentIndex(detected_format)
            self.format_hint_label.setText(
                translate('BiblesPlugin.ImportWizardForm',
                          'Detected {format}. OpenLP switched the import format automatically.').format(
                              format=detected_name))
        else:
            self.format_hint_label.setText(
                translate('BiblesPlugin.ImportWizardForm', 'Detected {format}.').format(format=detected_name))

    def validateCurrentPage(self):
        """
        Validate the current page before moving on to the next page.
        """
        log.debug(self.size())
        if self.currentPage() == self.welcome_page:
            return True
        elif self.currentPage() == self.select_page:
            self.version_name_edit.clear()
            self.permissions_edit.clear()
            self.full_license_edit.clear()
            self.copyright_edit.clear()
            if self.field('source_format') == BibleFormat.OSIS:
                if not self.field('osis_location'):
                    critical_error_message_box(UiStrings().NFSs, WizardStrings.YouSpecifyFile % WizardStrings.OSIS)
                    self.osis_path_edit.setFocus()
                    return False
            elif self.field('source_format') == BibleFormat.CSV:
                if not self.field('csv_booksfile'):
                    critical_error_message_box(
                        UiStrings().NFSs, translate('BiblesPlugin.ImportWizardForm',
                                                    'Please select the CSV/TXT Books file (required for CSV import).'))
                    self.csv_books_path_edit.setFocus()
                    return False
                elif not self.field('csv_versefile'):
                    critical_error_message_box(
                        UiStrings().NFSs,
                        translate('BiblesPlugin.ImportWizardForm',
                                  'Please select the CSV/TXT Verses file (required for CSV import).'))
                    self.csv_verses_path_edit.setFocus()
                    return False
            elif self.field('source_format') == BibleFormat.OpenSong:
                if not self.field('opensong_file'):
                    critical_error_message_box(UiStrings().NFSs, WizardStrings.YouSpecifyFile % WizardStrings.OS)
                    self.open_song_path_edit.setFocus()
                    return False
            elif self.field('source_format') == BibleFormat.Zefania:
                if not self.field('zefania_file'):
                    critical_error_message_box(UiStrings().NFSs, WizardStrings.YouSpecifyFile % WizardStrings.ZEF)
                    self.zefania_path_edit.setFocus()
                    return False
            elif self.field('source_format') == BibleFormat.WordProject:
                if not self.field('wordproject_file'):
                    critical_error_message_box(UiStrings().NFSs,
                                               WizardStrings.YouSpecifyFile % WizardStrings.WordProject)
                    self.wordproject_path_edit.setFocus()
                    return False
            elif self.field('source_format') == BibleFormat.WebDownload:
                # If count is 0 the bible list has not yet been downloaded
                if self.web_translation_combo_box.count() == 0:
                    return False
                else:
                    self.version_name_edit.setText(self.web_translation_combo_box.currentText())
            elif self.field('source_format') == BibleFormat.SWORD:
                # Test the SWORD tab that is currently active
                if self.sword_tab_widget.currentIndex() == self.sword_tab_widget.indexOf(self.sword_folder_tab):
                    if not self.field('sword_folder_path') and self.sword_bible_combo_box.count() == 0:
                        critical_error_message_box(UiStrings().NFSs,
                                                   WizardStrings.YouSpecifyFolder % WizardStrings.SWORD)
                        self.sword_folder_path_edit.setFocus()
                        return False
                    key = self.sword_bible_combo_box.itemData(self.sword_bible_combo_box.currentIndex())
                    if not key:
                        critical_error_message_box(UiStrings().NFSs,
                                                   WizardStrings.YouSpecifyFolder % WizardStrings.SWORD)
                        self.sword_folder_path_edit.setFocus()
                        return False
                    if 'description' in self.pysword_folder_modules_json[key]:
                        self.version_name_edit.setText(self.pysword_folder_modules_json[key]['description'])
                    if 'distributionlicense' in self.pysword_folder_modules_json[key]:
                        self.permissions_edit.setText(self.pysword_folder_modules_json[key]['distributionlicense'])
                    if 'copyright' in self.pysword_folder_modules_json[key]:
                        self.copyright_edit.setText(self.pysword_folder_modules_json[key]['copyright'])
                elif self.sword_tab_widget.currentIndex() == self.sword_tab_widget.indexOf(self.sword_zip_tab):
                    if not self.field('sword_zip_path'):
                        critical_error_message_box(UiStrings().NFSs, WizardStrings.YouSpecifyFile % WizardStrings.SWORD)
                        self.sword_zipfile_path_edit.setFocus()
                        return False
                    key = self.sword_zipbible_combo_box.itemData(self.sword_zipbible_combo_box.currentIndex())
                    if 'description' in self.pysword_zip_modules_json[key]:
                        self.version_name_edit.setText(self.pysword_zip_modules_json[key]['description'])
                    if 'distributionlicense' in self.pysword_zip_modules_json[key]:
                        self.permissions_edit.setText(self.pysword_zip_modules_json[key]['distributionlicense'])
            return True
        elif self.currentPage() == self.license_details_page:
            license_version = self.field('license_version')
            license_copyright = self.field('license_copyright')
            if not license_version:
                critical_error_message_box(
                    UiStrings().EmptyField,
                    translate('BiblesPlugin.ImportWizardForm', 'You need to specify a version name for your Bible.'))
                self.version_name_edit.setFocus()
                return False
            elif not license_copyright:
                critical_error_message_box(
                    UiStrings().EmptyField,
                    translate('BiblesPlugin.ImportWizardForm', 'You need to set a copyright for your Bible. '
                              'Bibles in the Public Domain need to be marked as such.'))
                self.copyright_edit.setFocus()
                return False
            elif self.manager.exists(license_version):
                critical_error_message_box(
                    translate('BiblesPlugin.ImportWizardForm', 'Bible Exists'),
                    translate('BiblesPlugin.ImportWizardForm',
                              'This Bible already exists. Please import a different Bible or first delete the '
                              'existing one.'))
                self.version_name_edit.setFocus()
                return False
            elif (AppLocation.get_section_data_path('bibles') / clean_filename(license_version)).exists():
                critical_error_message_box(
                    translate('BiblesPlugin.ImportWizardForm', 'Bible Exists'),
                    translate('BiblesPlugin.ImportWizardForm', 'This Bible already exists. Please import '
                              'a different Bible or first delete the existing one.'))
                self.version_name_edit.setFocus()
                return False
            return True
        if self.currentPage() == self.progress_page:
            return True

    def on_web_source_combo_box_index_changed(self, index):
        """
        Setup the list of Bibles when you select a different source on the web download page.

        :param index: The index of the combo box.
        """
        self.web_translation_combo_box.clear()
        if self.web_bible_list and index in self.web_bible_list:
            bibles = list(self.web_bible_list[index].keys())
            bibles.sort(key=get_locale_key)
            self.web_translation_combo_box.addItems(bibles)

    def on_web_update_button_clicked(self):
        """
        Download list of bibles from Crosswalk, BibleServer and BibleGateway.
        """
        # Download from Crosswalk, BiblesGateway, BibleServer
        self.web_bible_list = {}
        self.web_source_combo_box.setEnabled(False)
        self.web_translation_combo_box.setEnabled(False)
        self.web_update_button.setEnabled(False)
        self.web_progress_bar.setVisible(True)
        self.web_progress_bar.setValue(0)
        # TODO: Where does critical_error_message_box get %s string from?
        # NOTE: BibleServer support has been disabled since we can't currently parse it. Re-add if/when fixed.
        for (download_type, extractor) in ((WebDownload.Crosswalk, CWExtract()),
                                           (WebDownload.BibleGateway, BGExtract()),
                                           (WebDownload.BibleServer, BSExtract())):
            try:
                bibles = extractor.get_bibles_from_http()
            except (urllib.error.URLError, ConnectionError):
                critical_error_message_box(translate('BiblesPlugin.ImportWizardForm', 'Error during download'),
                                           translate('BiblesPlugin.ImportWizardForm',
                                                     'An error occurred while downloading the list of bibles from %s.'))
                bibles = None
            if bibles:
                self.web_bible_list[download_type] = {}
                for (bible_name, bible_key, language_code) in bibles:
                    self.web_bible_list[download_type][bible_name] = (bible_key, language_code)
            self.web_progress_bar.setValue(download_type + 1)
        # Update combo box if something got into the list
        if self.web_bible_list:
            self.on_web_source_combo_box_index_changed(0)
        self.web_source_combo_box.setEnabled(True)
        self.web_translation_combo_box.setEnabled(True)
        self.web_update_button.setEnabled(True)
        self.web_progress_bar.setVisible(False)

    def on_sword_folder_path_edit_path_changed(self, new_path):
        """
        Show the file open dialog for the SWORD folder.
        """
        if new_path:
            try:
                self.pysword_folder_modules = modules.SwordModules(str(new_path))
                self.pysword_folder_modules_json = self.pysword_folder_modules.parse_modules()
                bible_keys = self.pysword_folder_modules_json.keys()
                self.sword_bible_combo_box.clear()
                for key in bible_keys:
                    self.sword_bible_combo_box.addItem(self.pysword_folder_modules_json[key]['description'], key)
            except Exception:
                log.exception('Loading SWORD folder failed')
                critical_error_message_box(translate('BiblesPlugin.ImportWizardForm', 'Invalid SWORD folder'),
                                           translate('BiblesPlugin.ImportWizardForm',
                                                     'The folder selected does not contain a valid SWORD module.'))
                self.sword_bible_combo_box.clear()
                self.setField('sword_folder_path', None)

    def on_sword_zipfile_path_edit_path_changed(self, new_path):
        """
        Show the file open dialog for a SWORD zip-file.
        """
        if new_path:
            try:
                self.pysword_zip_modules = modules.SwordModules(str(new_path))
                self.pysword_zip_modules_json = self.pysword_zip_modules.parse_modules()
                bible_keys = self.pysword_zip_modules_json.keys()
                self.sword_zipbible_combo_box.clear()
                for key in bible_keys:
                    self.sword_zipbible_combo_box.addItem(self.pysword_zip_modules_json[key]['description'], key)
            except Exception:
                log.exception('Loading SWORD zip-file failed')
                critical_error_message_box(translate('BiblesPlugin.ImportWizardForm', 'Invalid SWORD zip-file'),
                                           translate('BiblesPlugin.ImportWizardForm',
                                                     'The file selected is not a valid SWORD zip-file.'))
                self.sword_zipbible_combo_box.clear()
                self.setField('sword_zip_path', None)

    def register_fields(self):
        """
        Register the bible import wizard fields.
        """
        self.select_page.registerField('source_format', self.format_combo_box)
        self.select_page.registerField('osis_location', self.osis_path_edit, 'path', self.osis_path_edit.pathChanged)
        self.select_page.registerField('csv_booksfile', self.csv_books_path_edit, 'path',
                                       self.csv_books_path_edit.pathChanged)
        self.select_page.registerField('csv_versefile', self.csv_verses_path_edit, 'path',
                                       self.csv_books_path_edit.pathChanged)
        self.select_page.registerField('opensong_file', self.open_song_path_edit, 'path',
                                       self.open_song_path_edit.pathChanged)
        self.select_page.registerField('zefania_file', self.zefania_path_edit, 'path',
                                       self.zefania_path_edit.pathChanged)
        self.select_page.registerField('wordproject_file', self.wordproject_path_edit, 'path',
                                       self.wordproject_path_edit.pathChanged)
        self.select_page.registerField('web_location', self.web_source_combo_box)
        self.select_page.registerField('web_biblename', self.web_translation_combo_box)
        self.select_page.registerField('sword_folder_path', self.sword_folder_path_edit, 'path',
                                       self.sword_folder_path_edit.pathChanged)
        self.select_page.registerField('sword_zip_path', self.sword_zipfile_path_edit, 'path',
                                       self.sword_zipfile_path_edit.pathChanged)
        self.license_details_page.registerField('license_version', self.version_name_edit)
        self.license_details_page.registerField('license_copyright', self.copyright_edit)
        self.license_details_page.registerField('license_permissions', self.permissions_edit)
        self.license_details_page.registerField("license_full_license", self.full_license_edit, 'plainText')

    def set_defaults(self):
        """
        Set default values for the wizard pages.
        """
        self.restart()
        self.finish_button.setVisible(False)
        self.cancel_button.setVisible(True)
        # The PathEdit fields are not initialised since that does not work well with the UI Internals
        self.setField('source_format', 0)
        self.setField('web_location', WebDownload.Crosswalk)
        self.setField('web_biblename', self.web_translation_combo_box.currentIndex())
        self.setField('license_version', self.version_name_edit.text())
        self.version_name_edit.setPlaceholderText(UiStrings().RequiredShowInFooter)
        self.setField('license_copyright', self.copyright_edit.text())
        self.copyright_edit.setPlaceholderText(UiStrings().RequiredShowInFooter)
        self.setField('license_permissions', self.permissions_edit.text())
        self.permissions_edit.setPlaceholderText(UiStrings().OptionalShowInFooter)
        self.setField('license_full_license', self.full_license_edit.toPlainText())
        self.full_license_edit.setPlaceholderText(UiStrings().OptionalHideInFooter)
        self.on_web_source_combo_box_index_changed(WebDownload.Crosswalk)

    def pre_wizard(self):
        """
        Prepare the UI for the import.
        """
        super(BibleImportForm, self).pre_wizard()
        bible_type = self.field('source_format')
        if bible_type == BibleFormat.WebDownload:
            self.progress_label.setText(translate('BiblesPlugin.ImportWizardForm', 'Registering Bible...'))
        else:
            self.progress_label.setText(WizardStrings.StartingImport)
        self.application.process_events()

    def perform_wizard(self):
        """
        Perform the actual import.
        """
        bible_type = self.field('source_format')
        license_version = self.field('license_version')
        license_copyright = self.field('license_copyright')
        license_permissions = self.field('license_permissions')
        license_full_license = self.field('license_full_license')
        importer = None
        if bible_type == BibleFormat.OSIS:
            # Import an OSIS bible.
            importer = self.manager.import_bible(BibleFormat.OSIS, name=license_version,
                                                 file_path=self.field('osis_location'))
        elif bible_type == BibleFormat.CSV:
            # Import a CSV bible.
            importer = self.manager.import_bible(BibleFormat.CSV, name=license_version,
                                                 books_path=self.field('csv_booksfile'),
                                                 verse_path=self.field('csv_versefile'))
        elif bible_type == BibleFormat.OpenSong:
            # Import an OpenSong bible.
            importer = self.manager.import_bible(BibleFormat.OpenSong, name=license_version,
                                                 file_path=self.field('opensong_file'))
        elif bible_type == BibleFormat.WebDownload:
            # Import a bible from the web.
            self.progress_bar.setMaximum(1)
            download_location = self.field('web_location')
            bible_version = self.web_translation_combo_box.currentText()
            (bible, language_id) = self.web_bible_list[download_location][bible_version]
            importer = self.manager.import_bible(
                BibleFormat.WebDownload, name=license_version,
                download_source=WebDownload.Names[download_location],
                download_name=bible,
                language_id=language_id
            )
        elif bible_type == BibleFormat.Zefania:
            # Import a Zefania bible.
            importer = self.manager.import_bible(BibleFormat.Zefania, name=license_version,
                                                 file_path=self.field('zefania_file'))
        elif bible_type == BibleFormat.WordProject:
            # Import a WordProject bible.
            importer = self.manager.import_bible(BibleFormat.WordProject, name=license_version,
                                                 file_path=self.field('wordproject_file'))
        elif bible_type == BibleFormat.SWORD:
            # Import a SWORD bible.
            if self.sword_tab_widget.currentIndex() == self.sword_tab_widget.indexOf(self.sword_folder_tab):
                importer = self.manager.import_bible(BibleFormat.SWORD, name=license_version,
                                                     sword_path=self.field('sword_folder_path'),
                                                     sword_key=self.sword_bible_combo_box.itemData(
                                                         self.sword_bible_combo_box.currentIndex()))
            else:
                importer = self.manager.import_bible(BibleFormat.SWORD, name=license_version,
                                                     sword_path=self.field('sword_zip_path'),
                                                     sword_key=self.sword_zipbible_combo_box.itemData(
                                                         self.sword_zipbible_combo_box.currentIndex()))
        import_failed = True
        exception = None
        try:
            if importer.do_import(license_version) and not importer.stop_import_flag:
                self.manager.save_meta_data(license_version, license_version,
                                            license_copyright, license_permissions, license_full_license)
                self.manager.reload_bibles()
                if bible_type == BibleFormat.WebDownload:
                    self.progress_label.setText(
                        translate('BiblesPlugin.ImportWizardForm', 'Registered Bible. Please note, that verses will be '
                                  'downloaded on demand and thus an internet connection is required.'))
                else:
                    self.progress_label.setText(WizardStrings.FinishedImport)
                return
        except (AttributeError, ValidationError, etree.XMLSyntaxError) as import_exception:
            log.exception('Importing bible failed')
            trace_error_handler(log)
            exception = import_exception
        if import_failed:
            failure = getattr(importer, 'import_failure', None)
            log.error('Bible import failed (type=%s, importer=%s, file=%s, failure_code=%s)',
                      bible_type, importer.__class__.__name__,
                      getattr(importer, 'file_path', None),
                      failure.code if failure else None)
            self.progress_label.setText(self.get_failure_feedback(importer, exception))
            self.cleanup_failed_import(importer)

    def get_failure_feedback(self, importer, exception):
        """
        Build a user-facing failure summary with direct next steps.
        """
        failure = getattr(importer, 'import_failure', None)
        default_title = translate('BiblesPlugin.ImportWizardForm', 'Your Bible import failed.')
        if importer.stop_import_flag:
            return translate('BiblesPlugin.ImportWizardForm', 'Bible import was cancelled.')
        if not failure:
            if exception:
                return default_title + '\n' + translate(
                    'BiblesPlugin.ImportWizardForm',
                    'OpenLP could not complete this import because of an unexpected error.'
                )
            return default_title
        lines = []
        if failure.is_user_cancelled:
            lines.append(translate('BiblesPlugin.ImportWizardForm', 'Bible import was cancelled.'))
        else:
            lines.append(default_title)
        lines.append(failure.summary)
        if failure.details:
            lines.append(failure.details)
        if failure.actions:
            action_lines = '\n'.join(['- {action}'.format(action=action) for action in failure.actions])
            lines.append(translate('BiblesPlugin.ImportWizardForm', 'Try this:') + '\n' + action_lines)
        if exception:
            lines.append(translate('BiblesPlugin.ImportWizardForm', 'Technical error: {error}').format(
                error=exception.__class__.__name__))
        return '\n'.join(lines)

    def cleanup_failed_import(self, importer):
        """
        Remove partially-created import state when an import fails.
        """
        if importer is None:
            return
        self.manager.db_cache.pop(importer.name, None)
        if hasattr(importer, 'session') and importer.session:
            importer.session.rollback()
            importer.session.close()
            importer.session = None
        if hasattr(importer, 'file_path') and importer.file_path:
            delete_database(self.plugin.name, importer.file_path)

    def provide_help(self):
        """
        Provide help within the wizard by opening the appropriate page of the openlp manual in the user's browser
        """
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://manual.openlp.org/bibles.html"))
