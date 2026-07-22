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
The :mod:`lib` module contains most of the components and libraries that make
OpenLP work.
"""
import logging
import os
import base64
from enum import IntEnum
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common.i18n import UiStrings, translate

log = logging.getLogger(__name__ + '.__init__')


DEFAULT_THUMBNAIL_HEIGHT = 88


class DataType(IntEnum):
    U8 = 1
    U16 = 2
    U32 = 4


class ServiceItemContext(object):
    """
    The context in which a Service Item is being generated
    """
    Preview = 0
    Live = 1
    Service = 2


class ImageSource(object):
    """
    This enumeration class represents different image sources. An image sources states where an image is used. This
    enumeration class is need in the context of the :class:~openlp.core.lib.imagemanager`.

    ``ImagePlugin``
        This states that an image is being used by the image plugin.

    ``Theme``
        This says, that the image is used by a theme.

    ``CommandPlugins``
        This states that an image is being used by a command plugin.
    """
    ImagePlugin = 1
    Theme = 2
    CommandPlugins = 3


class ServiceItemAction(object):
    """
    Provides an enumeration for the required action moving between service items by left/right arrow keys
    """
    Previous = 1
    PreviousLastSlide = 2
    Next = 3


class ItemCapabilities(object):
    """
    Provides an enumeration of a service item's capabilities

    ``CanPreview``
            The capability to allow the ServiceManager to add to the preview tab when making the previous item live.

    ``CanEdit``
            The capability to allow the ServiceManager to allow the item to be edited

    ``CanMaintain``
            The capability to allow the ServiceManager to allow the item to be reordered.

    ``RequiresMedia``
            Determines is the service_item needs a Media Player

    ``CanLoop``
            The capability to allow the SlideController to allow the loop processing.

    ``CanAppend``
            The capability to allow the ServiceManager to add leaves to the
            item

    ``NoLineBreaks``
            The capability to remove lines breaks in the renderer

    ``OnLoadUpdate``
            The capability to update MediaManager when a service Item is loaded.

    ``AddIfNewItem``
            Not Used

    ``ProvidesOwnDisplay``
            The capability to tell the SlideController the service Item has a different display.

    ``HasDetailedTitleDisplay``
            Being Removed and decommissioned.

    ``HasVariableStartTime``
            The capability to tell the ServiceManager that a change to start time is possible.

    ``CanSoftBreak``
            The capability to tell the renderer that Soft Break is allowed

    ``CanWordSplit``
            The capability to tell the renderer that it can split words is
            allowed

    ``HasBackgroundAudio``
            That a audio file is present with the text.

    ``CanAutoStartForLive``
            The capability to ignore the do not play if display blank flag.

    ``CanEditTitle``
            The capability to edit the title of the item

    ``IsOptical``
            Determines is the service_item is based on an optical device

    ``HasDisplayTitle``
            The item contains 'displaytitle' on every frame which should be
            preferred over 'title' when displaying the item

    ``HasNotes``
            The item contains 'notes'

    ``HasThumbnails``
            The item has related thumbnails available

    ``HasMetaData``
            The item has Meta Data about item

    ``CanStream``
            The item requires to process a Media Player Stream

    ``HasBackgroundVideo``
            That a video file is present with the text

    ``HasBackgroundStream``
            That a video stream is present with the text

    ``ProvidesOwnTheme``
            The capability to tell the SlideController to force the use of the service item theme.
    """
    CanPreview = 1
    CanEdit = 2
    CanMaintain = 3
    RequiresMedia = 4
    CanLoop = 5
    CanAppend = 6
    NoLineBreaks = 7
    OnLoadUpdate = 8
    AddIfNewItem = 9
    ProvidesOwnDisplay = 10
    # HasDetailedTitleDisplay = 11
    HasVariableStartTime = 12
    CanSoftBreak = 13
    CanWordSplit = 14
    HasBackgroundAudio = 15
    CanAutoStartForLive = 16
    CanEditTitle = 17
    IsOptical = 18
    HasDisplayTitle = 19
    HasNotes = 20
    HasThumbnails = 21
    HasMetaData = 22
    CanStream = 23
    HasBackgroundVideo = 24
    HasBackgroundStream = 25
    ProvidesOwnTheme = 26


def get_text_file_string(text_file_path):
    """
    Open a file and return its content as a string. If the supplied file path is not a file then the function
    returns False. If there is an error loading the file or the content can't be decoded then the function will return
    None.

    :param Path text_file_path: The path to the file.
    :return: The contents of the file, False if the file does not exist, or None if there is an Error reading or
    decoding the file.
    :rtype: str | False | None
    """
    if not text_file_path.is_file():
        return False
    content = None
    try:
        with text_file_path.open('r', encoding='utf-8') as file_handle:
            if file_handle.read(3) != '\xEF\xBB\xBF':
                # no BOM was found
                file_handle.seek(0)
            content = file_handle.read()
    except (OSError, UnicodeError):
        log.exception('Failed to open text file {text}'.format(text=text_file_path))
    return content


def str_to_bool(string_value):
    """
    Convert a string version of a boolean into a real boolean.

    :param string_value: The string value to examine and convert to a boolean type.
    :return: The correct boolean value
    """
    if isinstance(string_value, bool):
        return string_value
    return str(string_value).strip().lower() in ('true', 'yes', 'y')


def build_icon(icon):
    """
    Build a QIcon instance from an existing QIcon, a resource location, or a physical file location. If the icon is a
    QIcon instance, that icon is simply returned. If not, it builds a QIcon instance from the resource or file name.

    :param QtGui.QIcon | Path | QtGui.QIcon | str icon:
        The icon to build. This can be a QIcon, a resource string in the form ``:/resource/file.png``, or a file path
        location like ``Path(/path/to/file.png)``. However, the **recommended** way is to specify a resource string.
    :return: The build icon.
    :rtype: QtGui.QIcon
    """
    if isinstance(icon, QtGui.QIcon):
        return icon
    pix_map = None
    button_icon = QtGui.QIcon()
    if isinstance(icon, str):
        pix_map = QtGui.QPixmap(icon)
    elif isinstance(icon, Path):
        pix_map = QtGui.QPixmap(str(icon))
    elif isinstance(icon, QtGui.QImage):            # pragma: no cover
        pix_map = QtGui.QPixmap.fromImage(icon)
    if pix_map:
        button_icon.addPixmap(pix_map, QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
    return button_icon


def image_to_byte(image: QtGui.QPixmap, base_64: bool = True) -> QtCore.QByteArray | str:
    """
    Resize an image to fit on the current screen for the web and returns it as a byte stream.

    :param image: The image to be converted.
    :param base_64: If True returns the image as Base64 bytes, otherwise the image is returned as a byte array.
        To preserve original intention, this defaults to True
    """
    log.debug('image_to_byte - start')
    byte_array = QtCore.QByteArray()
    # use buffer to store pixmap into byteArray
    buffer = QtCore.QBuffer(byte_array)
    buffer.open(QtCore.QIODevice.WriteOnly)
    image.save(buffer, "JPEG")
    log.debug('image_to_byte - end')
    if not base_64:
        return byte_array
    # convert to base64 encoding so does not get missed!
    return base64.b64encode(byte_array).decode('utf-8')


def image_to_data_uri(image_path):
    """
    Converts a image into a base64 data uri
    """
    extension = image_path.suffix.replace('.', '')
    with open(image_path, 'rb') as image_file:
        image_bytes = image_file.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    return 'data:image/{extension};base64,{data}'.format(extension=extension, data=image_base64)


def create_thumb(image_path, thumb_path, return_icon=True, size=None):
    """
    Create a thumbnail from the given image path and depending on ``return_icon`` it returns an icon from this thumb.

    :param Path image_path: The image file to create the icon from.
    :param Path thumb_path: The filename to save the thumbnail to.
    :param return_icon: States if an icon should be build and returned from the thumb. Defaults to ``True``.
    :param size: Allows to state a own size (QtCore.QSize) to use. Defaults to ``None``, which means it uses the value
                 from DEFAULT_THUMBNAIL_HEIGHT.
    :return: The final icon.
    """
    reader = QtGui.QImageReader(str(image_path))
    if size is None:
        # No size given; use default height of 88
        if reader.size().isEmpty():
            ratio = 1
        else:
            ratio = reader.size().width() / reader.size().height()
        reader.setScaledSize(QtCore.QSize(int(ratio * DEFAULT_THUMBNAIL_HEIGHT), DEFAULT_THUMBNAIL_HEIGHT))
    elif size.isValid():
        # Complete size given
        reader.setScaledSize(size)
    else:
        # Invalid size given
        if reader.size().isEmpty():
            ratio = 1
        else:
            ratio = reader.size().width() / reader.size().height()
        if size.width() >= 0:
            # Valid width; scale height
            reader.setScaledSize(QtCore.QSize(size.width(), int(size.width() / ratio)))
        elif size.height() >= 0:
            # Valid height; scale width
            reader.setScaledSize(QtCore.QSize(int(ratio * size.height()), size.height()))
        else:
            # Invalid; use default height of 88
            reader.setScaledSize(QtCore.QSize(int(ratio * DEFAULT_THUMBNAIL_HEIGHT), DEFAULT_THUMBNAIL_HEIGHT))
    thumb = reader.read()
    thumb.save(str(thumb_path), thumb_path.suffix[1:].lower())
    if not return_icon:
        return
    if thumb_path.exists():
        return build_icon(thumb_path)
    # Fallback for files with animation support.
    return build_icon(image_path)


def validate_thumb(file_path, thumb_path):
    """
    Validates whether an file's thumb still exists and if is up to date. **Note**, you must **not** call this function,
    before checking the existence of the file.

    :param Path file_path: The path to the file. The file **must** exist!
    :param Path thumb_path: The path to the thumb.
    :return: Has the image changed since the thumb was created?
    :rtype: bool
    """
    if not thumb_path.exists():
        return False
    image_date = file_path.stat().st_mtime
    thumb_date = thumb_path.stat().st_mtime
    return image_date <= thumb_date


def resize_image(image_path, width, height, background='#000000', ignore_aspect_ratio=False):
    """
    Resize an image to fit on the current screen.

    DO NOT REMOVE THE DEFAULT BACKGROUND VALUE!

    :param image_path: The path to the image to resize.
    :param width: The new image width.
    :param height: The new image height.
    :param background: The background colour. Defaults to black.
    """
    log.debug('resize_image - start')
    reader = QtGui.QImageReader(image_path)
    # The image's ratio.
    image_ratio = reader.size().width() / reader.size().height()
    resize_ratio = width / height
    # Figure out the size we want to resize the image to (keep aspect ratio).
    if image_ratio == resize_ratio or ignore_aspect_ratio:
        size = QtCore.QSize(width, height)
    elif image_ratio < resize_ratio:
        # Use the image's height as reference for the new size.
        size = QtCore.QSize(int(image_ratio * height), height)
    else:
        # Use the image's width as reference for the new size.
        size = QtCore.QSize(width, int(1 / (image_ratio / width)))
    reader.setScaledSize(size)
    preview = reader.read()
    if image_ratio == resize_ratio:
        # We neither need to centre the image nor add "bars" to the image.
        return preview
    real_width = preview.width()
    real_height = preview.height()
    # and move it to the centre of the preview space
    new_image = QtGui.QImage(width, height, QtGui.QImage.Format.Format_ARGB32_Premultiplied)
    painter = QtGui.QPainter(new_image)
    painter.fillRect(new_image.rect(), QtGui.QColor(background))
    painter.drawImage((width - real_width) // 2, (height - real_height) // 2, preview)
    painter.end()
    return new_image


def check_item_selected(list_widget, message):
    """
    Check if a list item is selected so an action may be performed on it

    :param list_widget: The list to check for selected items
    :param message: The message to give the user if no item is selected
    """
    if not list_widget.selectedIndexes():
        QtWidgets.QMessageBox.information(list_widget.parent(),
                                          translate('OpenLP.MediaManagerItem', 'No Items Selected'), message)
        return False
    return True


def create_separated_list(string_list):
    """
    Returns a string that represents a join of a list of strings with a localized separator.
    Localized separation will be done via the translate() function by the translators.

    :param string_list: List of unicode strings
    :return: Formatted string
    """
    list_length = len(string_list)
    if list_length == 1:
        list_to_string = string_list[0]
    elif list_length == 2:
        list_to_string = translate('OpenLP.core.lib', '{one} and {two}').format(one=string_list[0], two=string_list[1])
    elif list_length > 2:
        list_to_string = translate('OpenLP.core.lib', '{first} and {last}').format(first=', '.join(string_list[:-1]),
                                                                                   last=string_list[-1])
    else:
        list_to_string = ''
    return list_to_string


def read_or_fail(file_object, length):
    """
    Ensure that the data read is as the exact length requested. Otherwise raise an OSError.

    :param io.IOBase file_object: The file-lke object ot read from.
    :param int length: The length of the data to read.
    :return: The data read.
    """
    data = file_object.read(length)
    if len(data) != length:
        raise OSError(UiStrings().FileCorrupt)
    return data


def read_int(file_object, data_type, endian='big'):
    """
    Read the correct amount of data from a file-like object to decode it to the specified type.

    :param io.IOBase file_object: The file-like object to read from.
    :param DataType data_type: A member from the :enum:`DataType`
    :param endian: The endianess of the data to be read
    :return int: The decoded int
    """
    data = read_or_fail(file_object, data_type)
    return int.from_bytes(data, endian)


def seek_or_fail(file_object, offset, how=os.SEEK_SET):
    """
    See to a set position and return an error if the cursor has not moved to that position.

    :param io.IOBase file_object: The file-like object to attempt to seek.
    :param int offset: The offset / position to seek by / to.
    :param [os.SEEK_CUR | os.SEEK_SET how: Currently only supports os.SEEK_CUR (0) or os.SEEK_SET (1)
    :return int: The new position in the file.
    """
    if how not in (os.SEEK_CUR, os.SEEK_SET):
        raise NotImplementedError
    prev_pos = file_object.tell()
    new_pos = file_object.seek(offset, how)
    if how == os.SEEK_SET and new_pos != offset or how == os.SEEK_CUR and new_pos != prev_pos + offset:
        raise OSError(UiStrings().FileCorrupt)
    return new_pos
