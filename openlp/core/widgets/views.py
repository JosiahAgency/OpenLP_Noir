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
The :mod:`listpreviewwidget` is a widget that lists the slides in the slide controller.
It is based on a QTableWidget but represents its contents in list form.
"""
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common.i18n import UiStrings
from openlp.core.common.mixins import RegistryProperties
from openlp.core.common.platform import is_win
from openlp.core.common.registry import Registry
from openlp.core.lib.serviceitem import ItemCapabilities, ServiceItem
from openlp.core.ui.style import NOIR_CUE, NOIR_INK_2, NOIR_INK_3, NOIR_INK_4, NOIR_ON_AIR, \
    NOIR_TEXT_BODY, NOIR_TEXT_HI, NOIR_TEXT_MID, UiThemes, is_ui_theme
from openlp.core.widgets.layouts import AspectRatioLayout


SCROLL_HINT = {
    0: QtWidgets.QAbstractItemView.ScrollHint.EnsureVisible,
    1: QtWidgets.QAbstractItemView.ScrollHint.PositionAtTop,
    2: QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter,
    3: QtWidgets.QAbstractItemView.ScrollHint.PositionAtBottom
}

# Data role holding the verse tag ('V1', 'C', ...) of a slide, painted as a chip
# by NoirSlideDelegate
VERSE_TAG_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1


class NoirSlideDelegate(QtWidgets.QStyledItemDelegate):
    """
    Paints the text slides of the Preview/Live slide lists as rounded cards
    instead of plain table rows: a small verse chip on top, the slide text
    below it, with distinct hover, selected and on-air states. Only installed
    when the Noir UI theme is active. Non-text slides (thumbnails) keep the
    default painting, as they are rendered by cell widgets.
    """
    CARD_MARGIN_X = 8
    CARD_MARGIN_Y = 3
    CARD_PADDING = 10
    CARD_RADIUS = 8
    CHIP_HEIGHT = 18
    CHIP_SPACING = 6

    def __init__(self, view, is_live=False):
        super().__init__(view)
        self.view = view
        self.is_live = is_live

    def _chip_font(self, base_font):
        font = QtGui.QFont(base_font)
        font.setPointSizeF(max(base_font.pointSizeF() - 2.5, 6.5))
        font.setBold(True)
        return font

    def _chip_label(self, index):
        verse_tag = index.data(VERSE_TAG_ROLE)
        return str(verse_tag) if verse_tag else str(index.row() + 1)

    def _accent_color(self):
        """
        The accent of the selected card: on-air red for the live controller
        while output is showing, the cue blue otherwise.
        """
        controller = self.view.parent()
        if self.is_live and getattr(controller, 'current_hide_mode', False) is None:
            return QtGui.QColor(NOIR_ON_AIR)
        return QtGui.QColor(NOIR_CUE)

    def paint(self, painter, option, index):
        text = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        selected = bool(option.state & QtWidgets.QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QtWidgets.QStyle.StateFlag.State_MouseOver)
        accent = self._accent_color()
        if not text:
            # Thumbnail slides are rendered by cell widgets on top of the cell,
            # so only the selection surface is painted here, behind them.
            if selected or hovered:
                painter.save()
                painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
                card = QtCore.QRectF(option.rect).adjusted(2, 1, -2, -1)
                if selected:
                    fill = QtGui.QColor(accent)
                    fill.setAlpha(34)
                    border = QtGui.QColor(accent)
                    border.setAlpha(150)
                else:
                    fill = QtGui.QColor(NOIR_INK_2)
                    border = QtGui.QColor(NOIR_INK_3)
                painter.setPen(QtGui.QPen(border, 1.5 if selected else 1))
                painter.setBrush(fill)
                painter.drawRoundedRect(card, self.CARD_RADIUS, self.CARD_RADIUS)
                painter.restore()
            return
        card = QtCore.QRectF(option.rect).adjusted(self.CARD_MARGIN_X, self.CARD_MARGIN_Y,
                                                   -self.CARD_MARGIN_X, -self.CARD_MARGIN_Y)
        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        # Card surface
        if selected:
            fill = QtGui.QColor(accent)
            fill.setAlpha(34)
            border = QtGui.QColor(accent)
            border.setAlpha(120)
        elif hovered:
            fill = QtGui.QColor(NOIR_INK_3)
            border = QtGui.QColor(NOIR_INK_4)
        else:
            fill = QtGui.QColor(NOIR_INK_2)
            border = QtGui.QColor(NOIR_INK_3)
        painter.setPen(QtGui.QPen(border, 1))
        painter.setBrush(fill)
        painter.drawRoundedRect(card, self.CARD_RADIUS, self.CARD_RADIUS)
        if selected:
            # Accent bar down the left edge of the selected card
            bar = QtCore.QRectF(card.left() + 4, card.top() + 6, 3, card.height() - 12)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(accent)
            painter.drawRoundedRect(bar, 1.5, 1.5)
        content = card.adjusted(self.CARD_PADDING + 4, self.CARD_PADDING, -self.CARD_PADDING,
                                -self.CARD_PADDING)
        # The view font is used for measuring and painting; option.font can
        # disagree with it while rows are being sized, which clips the text.
        body_font = self.view.font()
        # Verse chip
        chip_font = self._chip_font(body_font)
        chip_label = self._chip_label(index)
        chip_metrics = QtGui.QFontMetricsF(chip_font)
        chip_width = chip_metrics.horizontalAdvance(chip_label) + 14
        chip = QtCore.QRectF(content.left(), content.top(), chip_width, self.CHIP_HEIGHT)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        if selected:
            chip_fill = QtGui.QColor(accent)
            chip_text = QtGui.QColor('#FFFFFF') if self.is_live else QtGui.QColor('#0E1014')
        else:
            chip_fill = QtGui.QColor(NOIR_INK_4)
            chip_text = QtGui.QColor(NOIR_TEXT_MID)
        painter.setBrush(chip_fill)
        painter.drawRoundedRect(chip, 4, 4)
        painter.setFont(chip_font)
        painter.setPen(chip_text)
        painter.drawText(chip, QtCore.Qt.AlignmentFlag.AlignCenter, chip_label)
        # Slide text
        text_rect = QtCore.QRectF(content.left(), chip.bottom() + self.CHIP_SPACING,
                                  content.width(), content.bottom() - chip.bottom() - self.CHIP_SPACING)
        painter.setFont(body_font)
        painter.setPen(QtGui.QColor(NOIR_TEXT_HI if selected else NOIR_TEXT_BODY))
        painter.drawText(text_rect, QtCore.Qt.TextFlag.TextWordWrap, text)
        painter.restore()

    def sizeHint(self, option, index):
        text = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        if not text:
            return super().sizeHint(option, index)
        width = self.view.viewport().width() - 2 * self.CARD_MARGIN_X - 2 * self.CARD_PADDING - 4
        if width <= 0:
            width = 200
        metrics = QtGui.QFontMetrics(self.view.font())
        text_rect = metrics.boundingRect(QtCore.QRect(0, 0, int(width), 0),
                                         QtCore.Qt.TextFlag.TextWordWrap, text)
        height = (2 * self.CARD_MARGIN_Y + 2 * self.CARD_PADDING + self.CHIP_HEIGHT +
                  self.CHIP_SPACING + text_rect.height() + metrics.descent())
        return QtCore.QSize(option.rect.width(), int(height))


def handle_mime_data_urls(mime_data):
    """
    Process the data from a drag and drop operation.

    :param QtCore.QMimeData mime_data: The mime data from the drag and drop opperation.
    :return: A list of file paths that were dropped
    :rtype: list[Path]
    """
    file_paths = []
    for url in mime_data.urls():
        local_path = Path(url.toLocalFile())
        if local_path.is_file():
            file_paths.append(local_path)
        elif local_path.is_dir():
            for path in local_path.iterdir():
                file_paths.append(path)
    return file_paths


def remove_url_prefix(filename):
    """
    Remove the "file://" URL prefix

    :param str filename: The filename that may have a file URL prefix
    :returns str: The file name without the file URL prefix
    """
    return filename.replace('file://', '')


class ListPreviewWidget(QtWidgets.QTableWidget, RegistryProperties):
    """
    A special type of QTableWidget which lists the slides in the slide controller

    :param parent:
    :param screen_ratio:
    """
    resize_event = QtCore.Signal()

    def __init__(self, parent, screen_ratio):
        """
        Initializes the widget to default state.

        An empty ``ServiceItem`` is used by default. replace_service_manager_item() needs to be called to make this
        widget display something.
        """
        super().__init__(parent)
        self._setup(screen_ratio)

    def _setup(self, screen_ratio):
        """
        Set up the widget
        """
        self.setColumnCount(1)
        self.horizontalHeader().setVisible(False)
        self.setColumnWidth(0, self.parent().width())
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAlternatingRowColors(True)
        self.is_noir = is_ui_theme(UiThemes.Noir)
        if self.is_noir:
            # The Noir theme paints text slides as rounded cards with their own
            # hover/selected states, so the table chrome has to go.
            self.setAlternatingRowColors(False)
            self.setShowGrid(False)
            self.setMouseTracking(True)
            self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
            self.setItemDelegate(NoirSlideDelegate(self, is_live=bool(getattr(self.parent(), 'is_live', False))))
            # The delegate paints all selection states itself; a transparent
            # highlight stops the view painting its own row underlay behind
            # the cards.
            palette = self.palette()
            palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtCore.Qt.GlobalColor.transparent)
            palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor(NOIR_TEXT_HI))
            self.setPalette(palette)
        # Initialize variables.
        self.service_item = ServiceItem()
        self.screen_ratio = screen_ratio
        self.auto_row_height = 100
        # Connect signals
        self.verticalHeader().sectionResized.connect(self.row_resized)

    def resizeEvent(self, event):
        """
        Overloaded method from QTableWidget. Will recalculate the layout.
        """
        super().resizeEvent(event)
        self.__recalculate_layout()
        self.resize_event.emit()

    def __recalculate_layout(self):
        """
        Recalculates the layout of the table widget. It will set height and width
        of the table cells. QTableWidget does not adapt the cells to the widget size on its own.
        """
        self.setColumnWidth(0, self.viewport().width())
        if self.service_item:
            # Sort out songs, bibles, etc.
            if self.service_item.is_text():
                self.resizeRowsToContents()
            # Sort out image heights.
            else:
                height = self.viewport().width() // self.screen_ratio
                max_img_row_height = self.settings.value('advanced/slide max height')
                # Adjust for row height cap if in use.
                if isinstance(max_img_row_height, int):
                    if 0 < max_img_row_height < height:
                        height = max_img_row_height
                    elif max_img_row_height < 0:
                        # If auto setting, show that number of slides, or if the resulting slides too small, 100px.
                        # E.g. If setting is -4, 4 slides will be visible, unless those slides are < 100px high.
                        self.auto_row_height = max(self.viewport().height() / (-1 * max_img_row_height), 100)
                        height = min(height, self.auto_row_height)
                # Apply new height to slides
                for slide_index in range(len(self.service_item.slides)):
                    self.setRowHeight(slide_index, int(height))

    def row_resized(self, row, old_height, new_height):
        """
        Will scale non-image slides.
        """
        # Only for non-text slides when row height cap in use
        max_img_row_height = self.settings.value('advanced/slide max height')
        if self.service_item.is_text() or not isinstance(max_img_row_height, int) or max_img_row_height == 0:
            return
        # Get and validate label widget containing slide & adjust max width
        try:
            self.cellWidget(row, 0).children()[1].setMaximumWidth(new_height * self.screen_ratio)
        except Exception:
            return

    def screen_size_changed(self, screen_ratio):
        """
        This method is called whenever the live screen size changes, which then makes a layout recalculation necessary

        :param screen_ratio: The new screen ratio
        """
        self.screen_ratio = screen_ratio
        self.__recalculate_layout()

    def clear_list(self):
        """
        Clear the preview list
        :return:
        """
        self.setRowCount(0)
        self.clear()

    def replace_service_item(self, service_item, width, slide_number):
        """
        Replace the current preview items with the ones in service_item and display the given slide

        :param service_item: The service item to insert
        :param width: The width of the column
        :param slide_number: The slide number to pre-select
        """
        self.service_item = service_item
        self.setRowCount(0)
        self.clear_list()
        row = 0
        text = []
        slides = self.service_item.display_slides if self.service_item.is_text() else self.service_item.slides
        for slide_index, slide in enumerate(slides):
            self.setRowCount(self.slide_count() + 1)
            item = QtWidgets.QTableWidgetItem()
            slide_height = 0
            if self.service_item.is_text():
                if slide['verse']:
                    # These tags are already translated.
                    verse_def = slide['verse']
                    verse_def = '%s%s' % (verse_def[0], verse_def[1:])
                    two_line_def = '%s\n%s' % (verse_def[0], verse_def[1:])
                    row = two_line_def
                    item.setData(VERSE_TAG_ROLE, verse_def)
                else:
                    row += 1
                item.setText(slide['text'])
            else:
                label = QtWidgets.QLabel()
                label.setContentsMargins(4, 4, 4, 4)
                label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                if not self.service_item.is_media():
                    label.setScaledContents(True)
                if self.service_item.is_command():
                    if self.service_item.is_capable(ItemCapabilities.HasThumbnails):
                        pixmap = QtGui.QPixmap(str(slide['thumbnail']))
                    else:
                        if isinstance(slide['image'], QtGui.QIcon):
                            pixmap = slide['image'].pixmap(QtCore.QSize(32, 32))
                        else:
                            pixmap = QtGui.QPixmap(str(slide['image']))
                else:
                    pixmap = QtGui.QPixmap(str(slide['path']))
                if pixmap.height() > 0:
                    pixmap_ratio = pixmap.width() / pixmap.height()
                else:
                    pixmap_ratio = 1
                label.setPixmap(pixmap)
                container = QtWidgets.QWidget()
                layout = AspectRatioLayout(container, pixmap_ratio)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.addWidget(label)
                container.setLayout(layout)
                slide_height = width // self.screen_ratio
                max_img_row_height = self.settings.value('advanced/slide max height')
                if isinstance(max_img_row_height, int):
                    if 0 < max_img_row_height < slide_height:
                        slide_height = max_img_row_height
                    elif max_img_row_height < 0:
                        # If auto setting, show that number of slides, or if the resulting slides too small, 100px.
                        # E.g. If setting is -4, 4 slides will be visible, unless those slides are < 100px high.
                        self.auto_row_height = max(self.viewport().height() / (-1 * max_img_row_height), 100)
                        slide_height = min(slide_height, self.auto_row_height)
                self.setCellWidget(slide_index, 0, container)
                row += 1
            text.append(str(row))
            self.setItem(slide_index, 0, item)
            if slide_height:
                # First set the height to 1 and then to the right height. This makes the item display correctly.
                # If this is not done, sometimes the image item is displayed as blank.
                self.setRowHeight(slide_index, 1)
                self.setRowHeight(slide_index, int(slide_height))
        self.setVerticalHeaderLabels(text)
        if self.is_noir:
            # The verse tag is painted on the card itself, so the row header is
            # only needed for thumbnail slides
            self.verticalHeader().setVisible(not self.service_item.is_text())
        if self.service_item.is_text():
            self.resizeRowsToContents()
        self.setColumnWidth(0, self.viewport().width())
        self.change_slide(slide_number)

    def change_slide(self, slide):
        """
        Switches to the given row.
        """
        # Retrieve setting
        auto_scrolling = self.settings.value('advanced/autoscrolling')
        # Check if auto-scroll disabled (None) and validate value as dict containing 'dist' and 'pos'
        # 'dist' represents the slide to scroll to relative to the new slide (-1 = previous, 0 = current, 1 = next)
        # 'pos' represents the vert position of of the slide (0 = in view, 1 = top, 2 = middle, 3 = bottom)
        if not (isinstance(auto_scrolling, dict) and 'dist' in auto_scrolling and 'pos' in auto_scrolling and
                isinstance(auto_scrolling['dist'], int) and isinstance(auto_scrolling['pos'], int)):
            return
        # prevent scrolling past list bounds
        scroll_to_slide = slide + auto_scrolling['dist']
        if scroll_to_slide < 0:
            scroll_to_slide = 0
        if scroll_to_slide >= self.slide_count():
            scroll_to_slide = self.slide_count() - 1
        # Scroll to item if possible.
        self.scrollToItem(self.item(scroll_to_slide, 0), SCROLL_HINT[auto_scrolling['pos']])
        self.selectRow(slide)

    def current_slide_number(self):
        """
        Returns the position of the currently active item. Will return -1 if the widget is empty.
        """
        return super(ListPreviewWidget, self).currentRow()

    def slide_count(self):
        """
        Returns the number of slides this widget holds.
        """
        return super(ListPreviewWidget, self).rowCount()


class ListWidgetWithDnD(QtWidgets.QListWidget):
    """
    Provide a list widget to store objects and handle drag and drop events
    """
    def __init__(self, parent=None, name=''):
        """
        Initialise the list widget
        """
        super().__init__(parent)
        self.mime_data_text = name
        self.no_results_text = UiStrings().NoResults
        self.setSpacing(1)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)

    def activateDnD(self):
        """
        Activate DnD of widget
        """
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        Registry().register_function(('%s_dnd' % self.mime_data_text), self.parent().handle_mime_data)

    def clear(self, search_while_typing=False):
        """
        Re-implement clear, so that we can customise feedback when using 'Search as you type'

        :param search_while_typing: True if we want to display the customised message
        :return: None
        """
        if search_while_typing:
            self.no_results_text = UiStrings().ShortResults
        else:
            self.no_results_text = UiStrings().NoResults
        super().clear()

    def mouseMoveEvent(self, event):
        """
        Drag and drop event does not care what data is selected as the recipient will use events to request the data
        move just tell it what plugin to call
        """
        if event.buttons() != QtCore.Qt.MouseButton.LeftButton:
            event.ignore()
            return
        if not self.selectedItems():
            event.ignore()
            return
        drag = QtGui.QDrag(self)
        mime_data = QtCore.QMimeData()
        drag.setMimeData(mime_data)
        mime_data.setText(self.mime_data_text)
        drag.exec(QtCore.Qt.DropAction.CopyAction)

    def dragEnterEvent(self, event):
        """
        When something is dragged into this object, check if you should be able to drop it in here.
        """
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """
        Make an object droppable, and set it to copy the contents of the object, not move it.
        """
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """
        Receive drop event check if it is a file and process it if it is.

        :param event:  Handle of the event pint passed
        """
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.accept()
            file_paths = handle_mime_data_urls(event.mimeData())
            Registry().execute('{mime_data}_dnd'.format(mime_data=self.mime_data_text),
                               {'file_paths': file_paths})
        else:
            event.ignore()

    def allItems(self):
        """
        An generator to list all the items in the widget

        :return: a generator
        """
        for row in range(self.count()):
            yield self.item(row)

    def paintEvent(self, event):
        """
        Re-implement paintEvent so that we can add 'No Results' text when the listWidget is empty.

        :param event: A QPaintEvent
        :return: None
        """
        super().paintEvent(event)
        if not self.count():
            viewport = self.viewport()
            painter = QtGui.QPainter(viewport)
            font = QtGui.QFont()
            font.setItalic(True)
            painter.setFont(font)
            painter.drawText(QtCore.QRect(0, 0, viewport.width(), viewport.height()),
                             (QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.TextFlag.TextWordWrap),
                             self.no_results_text)


class TreeWidgetWithDnD(QtWidgets.QTreeWidget):
    """
    Provide a tree widget to store objects and handle drag and drop events
    """
    def __init__(self, parent=None, name=''):
        """
        Initialise the tree widget
        """
        super(TreeWidgetWithDnD, self).__init__(parent)
        self.mime_data_text = name
        self.allow_internal_dnd = False
        self.header().close()
        self.default_indentation = self.indentation()
        self.setIndentation(0)
        self.setAnimated(True)

    def activateDnD(self):
        """
        Activate DnD of widget
        """
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        Registry().register_function(('%s_dnd' % self.mime_data_text), self.parent().handle_mime_data)
        Registry().register_function(('%s_dnd_internal' % self.mime_data_text), self.parent().dnd_move_internal)

    def mouseMoveEvent(self, event):
        """
        Drag and drop event does not care what data is selected as the recipient will use events to request the data
        move just tell it what plugin to call

        :param event: The event that occurred
        """
        if event.buttons() != QtCore.Qt.MouseButton.LeftButton:
            event.ignore()
            return
        if not self.selectedItems():
            event.ignore()
            return
        drag = QtGui.QDrag(self)
        mime_data = QtCore.QMimeData()
        drag.setMimeData(mime_data)
        mime_data.setText(self.mime_data_text)
        drag.exec(QtCore.Qt.DropAction.CopyAction)

    def dragEnterEvent(self, event):
        """
        Receive drag enter event, check if it is a file or internal object and allow it if it is.

        :param event:  The event that occurred
        """
        if event.mimeData().hasUrls():
            event.accept()
        elif self.allow_internal_dnd:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """
        Receive drag move event, check if it is a file or internal object and allow it if it is.

        :param event: The event that occurred
        """
        QtWidgets.QTreeWidget.dragMoveEvent(self, event)
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.accept()
        elif self.allow_internal_dnd:
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """
        Receive drop event, check if it is a file or internal object and process it if it is.

        :param event: Handle of the event pint passed
        """
        # If we are on Windows, OpenLP window will not be set on top. For example, user can drag images to Library and
        # the folder stays on top of the group creation box. This piece of code fixes this issue.
        if is_win():
            self.setWindowState(self.windowState() & ~QtCore.Qt.WindowState.WindowMinimized |
                                QtCore.Qt.WindowState.WindowActive)
            self.setWindowState(QtCore.Qt.WindowState.WindowNoState)
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.accept()
            file_paths = handle_mime_data_urls(event.mimeData())
            Registry().execute('%s_dnd' % self.mime_data_text,
                               {'file_paths': file_paths, 'target': self.itemAt(event.pos())})
        elif self.allow_internal_dnd:
            event.setDropAction(QtCore.Qt.DropAction.CopyAction)
            event.accept()
            Registry().execute('%s_dnd_internal' % self.mime_data_text, self.itemAt(event.pos()))
        else:
            event.ignore()

    # Convenience methods for emulating a QListWidget. This helps keeping MediaManagerItem simple.
    def addItem(self, item):
        self.addTopLevelItem(item)

    def count(self):
        return self.topLevelItemCount()

    def item(self, index):
        return self.topLevelItem(index)
