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
Tests for the reference placement (footer vs. inline) behaviour of the EGW Library plugin's
generate_slide_data.
"""
from unittest.mock import MagicMock

from PySide6 import QtCore, QtWidgets

from openlp.core.common.enum import ReferencePlacement
from openlp.plugins.egwlibrary.lib.mediaitem import EGWLibraryMediaItem


def _mocked_paragraph_item():
    item = QtWidgets.QListWidgetItem()
    item.setData(QtCore.Qt.ItemDataRole.UserRole, {
        'type': 'paragraph', 'abbreviation': 'DA', 'reference': 'DA 83.2',
        'text': 'Sample text', 'book_title': 'The Desire of Ages', 'copyright': ''
    })
    return item


def _media_item():
    media_item = EGWLibraryMediaItem.__new__(EGWLibraryMediaItem)
    media_item.plugin = MagicMock()
    media_item.plugin.settings_tab.egw_theme = ''
    media_item.manager = MagicMock()
    media_item.list_view = MagicMock()
    return media_item


def test_generate_slide_data_reference_footer_default(settings):
    """
    Test that, by default (reference placement left at Footer), the marker stays stripped of the book
    abbreviation and the footer still gets the full reference -- unchanged from before this feature existed.
    """
    # GIVEN: A media item and default settings (reference placement not explicitly set)
    media_item = _media_item()
    service_item = MagicMock()
    service_item.raw_footer = []
    settings.setValue('egwlibrary/footer show reference', True)

    # WHEN: The slide data is generated
    result = media_item.generate_slide_data(service_item, item=[_mocked_paragraph_item()])

    # THEN: The slide marker should be stripped of the abbreviation, and the footer should carry the
    #       full reference
    assert result is True
    slide_text = service_item.add_from_text.call_args_list[0].args[0]
    assert 'DA' not in slide_text
    assert '83.2' in slide_text
    assert service_item.raw_footer == ['The Desire of Ages: DA 83.2']


def test_generate_slide_data_reference_inline(settings):
    """
    Test that, with reference placement set to Inline, the marker keeps the book abbreviation and the
    footer reference line is suppressed -- even though "show reference in footer" is still enabled
    (placement and the checkbox are independent axes).
    """
    # GIVEN: A media item with reference placement set to Inline
    media_item = _media_item()
    service_item = MagicMock()
    service_item.raw_footer = []
    settings.setValue('egwlibrary/footer show reference', True)
    settings.setValue('egwlibrary/reference placement', ReferencePlacement.Inline)

    # WHEN: The slide data is generated
    result = media_item.generate_slide_data(service_item, item=[_mocked_paragraph_item()])

    # THEN: The slide marker should keep the full reference, and the footer should stay empty
    assert result is True
    slide_text = service_item.add_from_text.call_args_list[0].args[0]
    assert 'DA 83.2' in slide_text
    assert service_item.raw_footer == []


def test_generate_slide_data_reference_footer_explicit(settings):
    """
    Test that explicitly selecting Footer placement behaves the same as the default.
    """
    # GIVEN: A media item with reference placement explicitly set to Footer
    media_item = _media_item()
    service_item = MagicMock()
    service_item.raw_footer = []
    settings.setValue('egwlibrary/footer show reference', True)
    settings.setValue('egwlibrary/reference placement', ReferencePlacement.Footer)

    # WHEN: The slide data is generated
    media_item.generate_slide_data(service_item, item=[_mocked_paragraph_item()])

    # THEN: The slide marker should be stripped, and the footer should carry the full reference
    slide_text = service_item.add_from_text.call_args_list[0].args[0]
    assert 'DA' not in slide_text
    assert service_item.raw_footer == ['The Desire of Ages: DA 83.2']
