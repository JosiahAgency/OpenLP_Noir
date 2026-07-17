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
Tests for the EGW Library PDF import details dialog.
"""
from PySide6 import QtWidgets

from openlp.plugins.egwlibrary.lib.pdfimportdialog import PdfBookDetailsDialog


def test_pdf_book_details_dialog(qapp):
    """
    Test that the details dialog pre-fills the guessed metadata and applies edits.
    """
    # GIVEN: A dialog for a converted book with guessed metadata
    book_data = {'title': 'The Desire of Ages', 'abbreviation': 'DA', 'copyright': '', 'language': 'en',
                 'aliases': [], 'chapters': [{'number': 1, 'title': 'God With Us',
                                              'paragraphs': [{'page': 19, 'text': 'Text.'}]}]}
    dialog = PdfBookDetailsDialog(None, 'en_DA.pdf', book_data, ['page markers jump from 18 to 20'])

    # THEN: The fields are pre-filled and OK is available
    assert dialog.title_edit.text() == 'The Desire of Ages'
    assert dialog.abbreviation_edit.text() == 'DA'
    ok_button = dialog.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
    assert ok_button.isEnabled()

    # WHEN: The user clears the abbreviation
    dialog.abbreviation_edit.setText('  ')
    # THEN: OK is disabled until it is filled again
    assert not ok_button.isEnabled()

    # WHEN: The user corrects the metadata
    dialog.abbreviation_edit.setText('DA')
    dialog.copyright_edit.setText('Public domain.')
    dialog.aliases_edit.setText('Desire of Ages, desire , ')
    result = dialog.book_data()

    # THEN: The edits are applied to the book dict, with aliases split and stripped
    assert result['abbreviation'] == 'DA'
    assert result['copyright'] == 'Public domain.'
    assert result['aliases'] == ['Desire of Ages', 'desire']
    assert result['chapters'] is book_data['chapters']
