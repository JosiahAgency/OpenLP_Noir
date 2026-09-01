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
The actual print service dialog
"""
import datetime
import html

import lxml.html
from PySide6 import QtCore, QtGui, QtPrintSupport, QtWidgets

from openlp.core.common.applocation import AppLocation
from openlp.core.common.i18n import translate
from openlp.core.common.mixins import RegistryProperties
from openlp.core.common.registry import Registry
from openlp.core.lib import get_text_file_string
from openlp.core.ui.printservicedialog import Ui_PrintServiceDialog, ZoomSize


DEFAULT_CSS = """/*
Edit this file to customize the service order print. Note, that not all CSS
properties are supported. See:
https://doc.qt.io/qt-5/richtext-html-subset.html#css-properties
*/

.serviceTitle {
   font-weight: 600;
   font-size: x-large;
   color: black;
}

.item {
   color: black;
}

.itemTitle {
   font-weight: 600;
   font-size: large;
}

.itemText {
   margin-top: 10px;
}

.itemFooter {
   font-size: 8px;
}

.itemNotes {}

.itemNotesTitle {
   font-weight: bold;
   font-size: 12px;
}

.itemNotesText {
   font-size: 11px;
}

.media {}

.mediaTitle {
    font-weight: bold;
    font-size: 11px;
}

.mediaText {}

.imageList {}

.customNotes {
   margin-top: 10px;
}

.customNotesTitle {
   font-weight: bold;
   font-size: 11px;
}

.customNotesText {
   font-size: 11px;
}

.newPage {
    page-break-before: always;
}

table.line {}

table.segment {
  float: left;
}

td.chord {
    font-size: 80%;
}

td.lyrics {
}
"""


class PrintServiceForm(QtWidgets.QDialog, Ui_PrintServiceDialog, RegistryProperties):
    """
    The :class:`~openlp.core.ui.printserviceform.PrintServiceForm` class displays a dialog for printing the service.
    """
    def __init__(self):
        """
        Constructor
        """
        super(PrintServiceForm, self).__init__(Registry().get('main_window'),
                                               QtCore.Qt.WindowType.WindowSystemMenuHint |
                                               QtCore.Qt.WindowType.WindowTitleHint |
                                               QtCore.Qt.WindowType.WindowCloseButtonHint)
        self.printer = QtPrintSupport.QPrinter()
        self.print_dialog = QtPrintSupport.QPrintDialog(self.printer, self)
        self.document = QtGui.QTextDocument()
        self.zoom = 0
        self.setup_ui(self)
        # Load the settings for the dialog.
        self.settings.beginGroup('advanced')
        self.slide_text_check_box.setChecked(self.settings.value('print slide text'))
        self.page_break_after_text.setChecked(self.settings.value('add page break'))
        if not self.slide_text_check_box.isChecked():
            self.page_break_after_text.setDisabled(True)
        self.meta_data_check_box.setChecked(self.settings.value('print file meta data'))
        self.notes_check_box.setChecked(self.settings.value('print notes'))
        self.zoom_combo_box.setCurrentIndex(self.settings.value('display size'))
        self.settings.endGroup()
        # Signals
        self.print_button.triggered.connect(self.print_service_order)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_original_button.clicked.connect(self.zoom_original)
        self.preview_widget.paintRequested.connect(self.paint_requested)
        self.zoom_combo_box.currentIndexChanged.connect(self.display_size_changed)
        self.plain_copy.triggered.connect(self.copy_text)
        self.html_copy.triggered.connect(self.copy_html_text)
        self.slide_text_check_box.stateChanged.connect(self.on_slide_text_check_box_changed)
        self.update_preview_text()

    def toggle_options(self, checked):
        """
        Toggle various options
        """
        self.options_widget.setVisible(checked)
        if checked:
            left = self.options_button.pos().x()
            top = self.toolbar.height()
            self.options_widget.move(left, top)
            self.title_line_edit.setFocus()
        else:
            self.save_options()
        self.update_preview_text()

    def update_preview_text(self):
        """
        Creates the html text and updates the html of *self.document*.
        """
        html_data = self._add_element('html')
        self._add_element('head', parent=html_data)
        self._add_element('title', self.title_line_edit.text(), html_data.head)
        css_path = AppLocation.get_data_path() / 'serviceprint' / 'service_print.css'
        custom_css = get_text_file_string(css_path)
        if not custom_css:
            custom_css = DEFAULT_CSS
        self._add_element('style', custom_css, html_data.head, attribute=('type', 'text/css'))
        self._add_element('body', parent=html_data)
        self._add_element('h1', html.escape(self.title_line_edit.text()), html_data.body, class_id='serviceTitle')
        for index, item in enumerate(self.service_manager.service_items):
            self._add_preview_item(html_data.body, item['service_item'], index)
        if not self.show_chords_check_box.isChecked():
            # Remove chord row and spacing span elements when not printing chords
            for chord_row in html_data.find_class('chordrow'):
                chord_row.drop_tree()
            for spacing_span in html_data.find_class('chordspacing'):
                spacing_span.drop_tree()
        # Add the custom service notes:
        if self.footer_text_edit.toPlainText():
            div = self._add_element('div', parent=html_data.body, class_id='customNotes')
            self._add_element(
                'span', translate('OpenLP.ServiceManager', 'Service Notes: '), div, class_id='customNotesTitle')
            self._add_element('span', html.escape(self.footer_text_edit.toPlainText()), div, class_id='customNotesText')
        self.document.setHtml(lxml.html.tostring(html_data).decode())
        self.preview_widget.updatePreview()

    def _add_preview_item(self, body, item, index):
        """
        Add a preview item
        """
        div = self._add_element('div', class_id='item', parent=body)
        # Add the title of the service item.
        item_title = self._add_element('h2', parent=div, class_id='itemTitle')
        self._add_element('span', '&nbsp;' + html.escape(item.get_display_title()), item_title)
        if self.slide_text_check_box.isChecked():
            # Add the text of the service item.
            if item.is_text():
                verse_def = None
                verse_html = None
                for slide in item.print_slides:
                    slide_text = slide['text'].replace('\n', '<br>')
                    if not verse_def or verse_def != slide['verse'] or verse_html == slide_text:
                        text_div = self._add_element('div', parent=div, class_id='itemText')
                    elif 'chordspacing' not in slide_text:
                        self._add_element('br', parent=text_div)
                    self._add_element('span', slide_text, text_div)
                    verse_def = slide['verse']
                    verse_html = slide_text
                # Break the page before the div element.
                if index != 0 and self.page_break_after_text.isChecked():
                    div.set('class', 'item newPage')
            # Add the image names of the service item.
            elif item.is_image():
                ol = self._add_element('ol', parent=div, class_id='imageList')
                for slide in range(len(item.get_frames())):
                    self._add_element('li', item.get_frame_title(slide), ol)
            # add footer
            footer_html = item.footer_html
            footer_html = footer_html.partition('<br>')[2]
            if footer_html:
                footer_html = html.escape(footer_html.replace('<br>', '\n'))
                self._add_element('div', footer_html.replace('\n', '<br>'), parent=div, class_id='itemFooter')
        # Add service items' notes.
        if self.notes_check_box.isChecked():
            if item.notes:
                p = self._add_element('div', class_id='itemNotes', parent=div)
                self._add_element('span', translate('OpenLP.ServiceManager', 'Notes: '), p, class_id='itemNotesTitle')
                self._add_element('span', html.escape(item.notes).replace('\n', '<br>'), p, class_id='itemNotesText')
        # Add play length of media files.
        if item.is_media() and self.meta_data_check_box.isChecked():
            tme = item.media_length
            if item.end_time > 0:
                tme = item.end_time - item.start_time
            title = self._add_element('div', class_id='media', parent=div)
            self._add_element(
                'span', translate('OpenLP.ServiceManager', 'Playing time: '), title, class_id='mediaTitle')
            self._add_element('span', str(datetime.timedelta(seconds=tme)), title, class_id='mediaText')

    def _add_element(self, tag, text=None, parent=None, class_id=None, attribute=None):
        """
        Creates a html element. If ``text`` is given, the element's text will set and if a ``parent`` is given,
        the element is appended.

        :param tag: The html tag, e. g. ``'span'``. Defaults to ``None``.
        :param text: The text for the tag. Defaults to ``None``.
        :param parent: The parent element. Defaults to ``None``.
        :param class_id: Value for the class attribute
        :param attribute: Tuple name/value pair to add as an optional attribute
        """
        if text is not None:
            element = lxml.html.fragment_fromstring(str(text), create_parent=tag)
        else:
            element = lxml.html.Element(tag)
        if parent is not None:
            parent.append(element)
        if class_id is not None:
            element.set('class', class_id)
        if attribute is not None:
            element.set(attribute[0], attribute[1])
        return element

    def paint_requested(self, printer):
        """
        Paint the preview of the *self.document*.

        ``printer``
            A *QPrinter* object.
        """
        self.document.print_(printer)

    def display_size_changed(self, display):
        """
        The Zoom Combo box has changed so set up the size.
        """
        if display == ZoomSize.Page:
            self.preview_widget.fitInView()
        elif display == ZoomSize.Width:
            self.preview_widget.fitToWidth()
        elif display == ZoomSize.OneHundred:
            self.preview_widget.fitToWidth()
            self.preview_widget.zoomIn(1)
        elif display == ZoomSize.SeventyFive:
            self.preview_widget.fitToWidth()
            self.preview_widget.zoomIn(0.75)
        elif display == ZoomSize.Fifty:
            self.preview_widget.fitToWidth()
            self.preview_widget.zoomIn(0.5)
        elif display == ZoomSize.TwentyFive:
            self.preview_widget.fitToWidth()
            self.preview_widget.zoomIn(0.25)
        self.settings.beginGroup('advanced')
        self.settings.setValue('display size', display)
        self.settings.endGroup()

    def copy_text(self):
        """
        Copies the display text to the clipboard as plain text
        """
        self.update_song_usage()
        cursor = QtGui.QTextCursor(self.document)
        cursor.select(QtGui.QTextCursor.SelectionType.Document)
        clipboard_text = cursor.selectedText()
        # We now have the unprocessed unicode service text in the cursor
        # So we replace u2028 with \n and u2029 with \n\n and a few others
        clipboard_text = clipboard_text.replace('\u2028', '\n')
        clipboard_text = clipboard_text.replace('\u2029', '\n\n')
        clipboard_text = clipboard_text.replace('\u2018', '\'')
        clipboard_text = clipboard_text.replace('\u2019', '\'')
        clipboard_text = clipboard_text.replace('\u201c', '"')
        clipboard_text = clipboard_text.replace('\u201d', '"')
        clipboard_text = clipboard_text.replace('\u2026', '...')
        clipboard_text = clipboard_text.replace('\u2013', '-')
        clipboard_text = clipboard_text.replace('\u2014', '-')
        # remove the icon from the text
        clipboard_text = clipboard_text.replace('\ufffc\xa0', '')
        # and put it all on the clipboard
        self.main_window.clipboard.setText(clipboard_text)

    def copy_html_text(self):
        """
        Copies the display text to the clipboard as Html
        """
        self.update_song_usage()
        self.main_window.clipboard.setText(self.document.toHtml())

    def print_service_order(self):
        """
        Called, when the *print_button* is clicked. Opens the *print_dialog*.
        """
        if not self.print_dialog.exec():
            return
        self.update_song_usage()
        # Print the document.
        self.document.print_(self.printer)

    def zoom_in(self):
        """
        Called when *zoom_in_button* is clicked.
        """
        self.preview_widget.zoomIn()
        self.zoom -= 0.1

    def zoom_out(self):
        """
        Called when *zoom_out_button* is clicked.
        """
        self.preview_widget.zoomOut()
        self.zoom += 0.1

    def zoom_original(self):
        """
        Called when *zoom_out_button* is clicked.
        """
        self.preview_widget.zoomIn(1 + self.zoom)
        self.zoom = 0

    def on_slide_text_check_box_changed(self, state):
        """
        Disable or enable the ``page_break_after_text`` checkbox  as it should only
        be enabled, when the ``slide_text_check_box`` is enabled.
        """
        self.page_break_after_text.setDisabled(QtCore.Qt.CheckState(state) == QtCore.Qt.CheckState.Unchecked)

    def save_options(self):
        """
        Save the settings and close the dialog.
        """
        # Save the settings for this dialog.
        self.settings.beginGroup('advanced')
        self.settings.setValue('print slide text', self.slide_text_check_box.isChecked())
        self.settings.setValue('add page break', self.page_break_after_text.isChecked())
        self.settings.setValue('print file meta data', self.meta_data_check_box.isChecked())
        self.settings.setValue('print notes', self.notes_check_box.isChecked())
        self.settings.endGroup()

    def update_song_usage(self):
        """
        Update the song usage
        """
        # Only continue when we include the song's text.
        if not self.slide_text_check_box.isChecked():
            return
        for item in self.service_manager.service_items:
            # Trigger Audit requests
            Registry().register_function('print_service_started', [item['service_item']])
