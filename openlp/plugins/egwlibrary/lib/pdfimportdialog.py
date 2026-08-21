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
The :mod:`~openlp.plugins.egwlibrary.lib.pdfimportdialog` module contains the dialog
which lets the user confirm or correct the book details guessed from an imported PDF
before the book is written to the library.
"""
from PySide6 import QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.lib.ui import create_button_box


class PdfBookDetailsDialog(QtWidgets.QDialog):
    """
    Confirm/edit the title, abbreviation, copyright and aliases of a book converted
    from a PDF. The conversion result (chapter/paragraph/page counts and any warnings)
    is shown so the user can sanity-check it before importing.
    """
    def __init__(self, parent, file_name, book_data, warnings):
        """
        :param parent: The parent widget.
        :param file_name: The name of the PDF, shown in the dialog title.
        :param book_data: The converted book dict with guessed metadata (see
            :func:`~openlp.plugins.egwlibrary.lib.pdfimport.convert_pdf_book`).
        :param warnings: Conversion warnings to surface to the user.
        """
        super().__init__(parent)
        self._book_data = book_data
        self.setObjectName('pdf_book_details_dialog')
        self.setWindowTitle(translate('EGWLibraryPlugin.PdfImportDialog',
                                      'Import "{name}"').format(name=file_name))
        self.setMinimumWidth(450)
        layout = QtWidgets.QVBoxLayout(self)
        chapters = book_data['chapters']
        paragraph_count = sum(len(chapter['paragraphs']) for chapter in chapters)
        pages = [paragraph['page'] for chapter in chapters for paragraph in chapter['paragraphs']]
        if pages:
            page_range = '{first}-{last}'.format(first=min(pages), last=max(pages))
        else:
            page_range = translate('EGWLibraryPlugin.PdfImportDialog', 'n/a')
        summary_label = QtWidgets.QLabel(
            translate('EGWLibraryPlugin.PdfImportDialog',
                      'Converted {chapters} chapter(s), {paragraphs} paragraph(s), pages {page_range}.\n'
                      'Check the book details below; the abbreviation is used in citations (e.g. "DA 83.2").'
                      ).format(chapters=len(chapters), paragraphs=paragraph_count, page_range=page_range), self)
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)
        if warnings:
            warnings_label = QtWidgets.QLabel(
                translate('EGWLibraryPlugin.PdfImportDialog', 'Conversion warnings:\n{warnings}').format(
                    warnings='\n'.join('• ' + warning for warning in warnings)), self)
            warnings_label.setWordWrap(True)
            layout.addWidget(warnings_label)
        form_layout = QtWidgets.QFormLayout()
        self.title_edit = QtWidgets.QLineEdit(book_data.get('title', ''), self)
        form_layout.addRow(translate('EGWLibraryPlugin.PdfImportDialog', 'Title:'), self.title_edit)
        self.abbreviation_edit = QtWidgets.QLineEdit(book_data.get('abbreviation', ''), self)
        form_layout.addRow(translate('EGWLibraryPlugin.PdfImportDialog', 'Abbreviation:'), self.abbreviation_edit)
        self.copyright_edit = QtWidgets.QLineEdit(book_data.get('copyright', ''), self)
        form_layout.addRow(translate('EGWLibraryPlugin.PdfImportDialog', 'Copyright:'), self.copyright_edit)
        self.aliases_edit = QtWidgets.QLineEdit(', '.join(book_data.get('aliases', [])), self)
        self.aliases_edit.setPlaceholderText(
            translate('EGWLibraryPlugin.PdfImportDialog', 'Extra search names, separated by commas'))
        form_layout.addRow(translate('EGWLibraryPlugin.PdfImportDialog', 'Aliases:'), self.aliases_edit)
        layout.addLayout(form_layout)
        self.button_box = create_button_box(self, 'button_box', ['cancel', 'ok'])
        layout.addWidget(self.button_box)
        self.title_edit.textChanged.connect(self._update_ok_button)
        self.abbreviation_edit.textChanged.connect(self._update_ok_button)
        self._update_ok_button()

    def _update_ok_button(self):
        """
        The book cannot be imported without a title and an abbreviation.
        """
        ok_button = self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        ok_button.setEnabled(bool(self.title_edit.text().strip()) and
                             bool(self.abbreviation_edit.text().strip()))

    def book_data(self):
        """
        The book dict with the user's (possibly edited) metadata applied.
        """
        self._book_data['title'] = self.title_edit.text().strip()
        self._book_data['abbreviation'] = self.abbreviation_edit.text().strip()
        self._book_data['copyright'] = self.copyright_edit.text().strip()
        self._book_data['aliases'] = [alias.strip() for alias in self.aliases_edit.text().split(',')
                                      if alias.strip()]
        return self._book_data
