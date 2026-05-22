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
The :mod:`common` module contains most of the components and libraries that make
OpenLP work.
"""
import hashlib
import importlib
import logging
import re
import sys
import traceback

from ipaddress import IPv4Address, IPv6Address, AddressValueError
from pathlib import Path
from shutil import which

from PySide6 import QtGui
from PySide6.QtCore import QCryptographicHash as QHash
from PySide6.QtNetwork import QAbstractSocket, QHostAddress, QNetworkInterface
from chardet.universaldetector import UniversalDetector

log = logging.getLogger(__name__ + '.__init__')


FIRST_CAMEL_REGEX = re.compile('(.)([A-Z][a-z]+)')
SECOND_CAMEL_REGEX = re.compile('([a-z0-9])([A-Z])')
CONTROL_CHARS = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]')
INVALID_FILE_CHARS = re.compile(r'[\\/:*?"<>|+\[\]%]')
IMAGES_FILTER = None
REPLACMENT_CHARS_MAP = str.maketrans({'\u2018': '\'', '\u2019': '\'', '\u201c': '"', '\u201d': '"', '\u2026': '...',
                                      '\u2013': '-', '\u2014': '-', '\v': '\n\n', '\f': '\n\n'})
NEW_LINE_REGEX = re.compile(r' ?(\r\n?|\n) ?')
WHITESPACE_REGEX = re.compile(r'[ \t]+')
INTERFACE_FILTER = re.compile('^lo|loopback|docker|tun', re.IGNORECASE)


def get_network_interfaces():
    """
    Creates a dictionary of local IPv4 interfaces on local machine.
    If no active interfaces available, returns a dict of localhost IPv4 information

    :returns: Dict of interfaces
    """
    log.debug('Getting local IPv4 interface(es) information')
    interfaces = {}
    for interface in QNetworkInterface.allInterfaces():
        interface_name = interface.name()
        if INTERFACE_FILTER.search(interface_name):
            log.debug('Filtering out interfaces we don\'t care about: {name}'.format(name=interface_name))
            continue
        log.debug('Checking for isValid and flags == IsUP | IsRunning')
        if not interface.isValid() or not (interface.flags() & (QNetworkInterface.InterfaceFlag.IsUp |
                                                                QNetworkInterface.InterfaceFlag.IsRunning)):
            continue
        log.debug('Checking address(es) protocol')
        for address in interface.addressEntries():
            ip = address.ip()
            log.debug('Checking for protocol == IPv4Protocol')
            if ip.protocol() == QAbstractSocket.NetworkLayerProtocol.IPv4Protocol:
                log.debug('Getting interface information')
                interfaces[interface_name] = {
                    'ip': ip.toString(),
                    'broadcast': address.broadcast().toString(),
                    'netmask': address.netmask().toString(),
                    'prefix': address.prefixLength(),
                    'localnet': QHostAddress(address.netmask().toIPv4Address() & ip.toIPv4Address()).toString()
                }
                log.debug('Adding {interface} to active list'.format(interface=interface.name()))
    if len(interfaces) == 0:
        log.warning('No active IPv4 network interfaces detected')
    return interfaces


def trace_error_handler(logger):
    """
    Log the calling path of an exception

    :param logger: logger to use so traceback is logged to correct class
    """
    log_string = "OpenLP Error trace"
    for tb in traceback.extract_stack():
        log_string += '\n   File {file} at line {line} \n\t called {data}'.format(file=tb[0], line=tb[1], data=tb[3])
    logger.error(log_string)


def path_to_module(path: Path, community: bool = None) -> str:
    """
    Convert a path to a module name (i.e openlp.core.common)

    :param pathlib.Path path: The path to convert to a module name.
    :param bool False community: Are we in Community Mode?
    :return: The module name.
    :rtype: str
    """
    module_path = path.with_suffix('')
    prefix = 'contrib.' if community else 'openlp.'
    return prefix + '.'.join(module_path.parts)


def import_openlp_module(module_name):
    """
    Refactor module import out for testability. In Python 3.11, mock.patch and import_module do not play along nicely.
    """
    importlib.import_module(module_name)


def extension_loader(base_dir: Path, glob_pattern: str, excluded_files: list = None, community: bool = False) -> None:
    """
    A utility function to find and load OpenLP extensions, such as plugins, presentation and media controllers and
    importers.

    :param Path base_dir: The base directory to search in; usually the application directory itself, but when loading
        community extensions, it is the 'contrib' subdirectory.
    :param str glob_pattern: A glob pattern used to find the extension(s) to be imported. Should be relative to the
        application directory. i.e. plugins/*/*plugin.py
    :param list[str] | None excluded_files: A list of file names to exclude that the glob pattern may find.
    :param bool | False community: are we using the community directory path
    :rtype: None
    """
    if community:
        sys.path.insert(0, str(base_dir))
        base_dir = base_dir / 'contrib'
    for extension_path in base_dir.glob(glob_pattern):
        extension_path = extension_path.relative_to(base_dir)
        if extension_path.name in (excluded_files or []):
            continue
        log.debug('Attempting to import %s', extension_path)
        module_name = path_to_module(extension_path, community)
        try:
            import_openlp_module(module_name)
        except (ImportError, OSError):
            # On some platforms importing a module might cause OSError exceptions. (e.g. Mac OS X)
            log.exception('Failed to import %s on path %s', module_name, extension_path)


def get_frozen_path(frozen_option, non_frozen_option):
    """
    Return a path based on the system status.

    :param frozen_option:
    :param non_frozen_option:
    """
    if getattr(sys, 'frozen', False) == 1:
        return frozen_option
    return non_frozen_option


class ThemeLevel(object):
    """
    Provides an enumeration for the level a theme applies to
    """
    Global = 1
    Service = 2
    Song = 3


class SlideLimits(object):
    """
    Provides an enumeration for behaviour of OpenLP at the end limits of each service item when pressing the up/down
    arrow keys
    """
    End = 1
    Wrap = 2
    Next = 3


class Singleton(type):
    """
    Provide a `Singleton` metaclass https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Create a new instance if one does not already exist.
        """
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


def de_hump(name):
    """
    Change any Camel Case string to python string
    """
    sub_name = FIRST_CAMEL_REGEX.sub(r'\1_\2', name)
    return SECOND_CAMEL_REGEX.sub(r'\1_\2', sub_name).lower()


def verify_ipv4(addr):
    """
    Validate an IPv4 address

    :param addr: Address to validate
    :returns: bool
    """
    try:
        IPv4Address(addr)
        return True
    except AddressValueError:
        return False


def verify_ipv6(addr):
    """
    Validate an IPv6 address

    :param addr: Address to validate
    :returns: bool
    """
    try:
        IPv6Address(addr)
        return True
    except AddressValueError:
        return False


def verify_ip_address(addr):
    """
    Validate an IP address as either IPv4 or IPv6

    :param addr: Address to validate
    :returns: bool
    """
    return True if verify_ipv4(addr) else verify_ipv6(addr)


def md5_hash(salt=None, data=None):
    """
    Returns the hashed output of md5sum on salt,data
    using Python3 hashlib

    :param salt: Initial salt
    :param data: OPTIONAL Data to hash
    :returns: str
    """
    log.debug('md5_hash(salt="{text}")'.format(text=salt))
    if not salt and not data:
        return None
    hash_obj = hashlib.new('md5')
    if salt:
        hash_obj.update(salt)
    if data:
        hash_obj.update(data)
    hash_value = hash_obj.hexdigest()
    log.debug('md5_hash() returning "{text}"'.format(text=hash_value))
    return hash_value


def sha256_file_hash(filename):
    """
    Returns the hashed output of sha256 on the file content using Python3 hashlib

    This method allows PermissionError to bubble up, while supressing other exceptions

    :param filename: Name of the file to hash
    :returns: str
    """
    log.debug('sha256_file_hash(filename="{filename}")'.format(filename=filename))
    hash_obj = hashlib.sha256()
    if not filename.exists():
        return None
    try:
        with filename.open('rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except PermissionError:
        raise
    except Exception:
        return None


def qmd5_hash(salt=None, data=None):
    """
    Returns the hashed output of MD5Sum on salt, data
    using PySide6.QCryptographicHash. Function returns a
    QByteArray instead of a text string.
    If you need a string instead, call with

        result = str(qmd5_hash(salt=..., data=...), encoding='ascii')

    :param salt: Initial salt
    :param data: OPTIONAL Data to hash
    :returns: QByteArray
    """
    log.debug('qmd5_hash(salt="{text}"'.format(text=salt))
    if salt is None and data is None:
        return None
    hash_obj = QHash(QHash.Md5)
    if salt:
        hash_obj.addData(salt)
    if data:
        hash_obj.addData(data)
    hash_value = hash_obj.result().toHex()
    log.debug('qmd5_hash() returning "{hash}"'.format(hash=hash_value))
    return hash_value


def clean_button_text(button_text):
    """
    Clean the & and other characters out of button text

    :param button_text: The text to clean
    """
    return button_text.replace('&', '').replace('< ', '').replace(' >', '')


def add_actions(target, actions):
    """
    Adds multiple actions to a menu or toolbar in one command.

    :param target: The menu or toolbar to add actions to
    :param actions: The actions to be added. An action consisting of the keyword ``None``
        will result in a separator being inserted into the target.
    """
    for action in actions:
        if action is None:
            target.addSeparator()
        else:
            target.addAction(action)


def get_uno_command(connection_type='pipe'):
    """
    Returns the UNO command to launch an libreoffice.org instance.
    """
    for command in ['libreoffice', 'soffice']:
        if which(command):
            break
    else:
        raise FileNotFoundError('Command not found')

    OPTIONS = '--nologo --norestore --minimized --nodefault --nofirststartwizard'
    if connection_type == 'pipe':
        CONNECTION = '"--accept=pipe,name=openlp_pipe;urp;"'
    else:
        CONNECTION = '"--accept=socket,host=localhost,port=2002;urp;"'
    return '{cmd} {opt} {conn}'.format(cmd=command, opt=OPTIONS, conn=CONNECTION)


def get_uno_instance(resolver, connection_type='pipe'):
    """
    Returns a running libreoffice.org instance.

    :param resolver: The UNO resolver to use to find a running instance.
    """
    log.debug('get UNO Desktop Openoffice - resolve')
    if connection_type == 'pipe':
        return resolver.resolve('uno:pipe,name=openlp_pipe;urp;StarOffice.ComponentContext')
    else:
        return resolver.resolve('uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext')


def get_filesystem_encoding():
    """
    Returns the name of the encoding used to convert Unicode filenames into system file names.
    """
    encoding = sys.getfilesystemencoding()
    if encoding is None:
        encoding = sys.getdefaultencoding()
    return encoding


def delete_file(file_path):
    """
    Deletes a file from the system.

    :param pathlib.Path file_path: The file, including path, to delete.
    :return: True if the deletion was successful, or the file never existed. False otherwise.
    :rtype: bool
    """
    if not file_path:
        return False
    try:
        if file_path.exists():
            file_path.unlink()
        return True
    except OSError:
        log.exception('Unable to delete file {file_path}'.format(file_path=file_path))
        return False


def case_insensitive_glob(extension):
    """
    Build a case-insensitive glob pattern for an extension.

    For example, ``png`` becomes ``*.[pP][nN][gG]``.

    :param str extension: The file extension without a leading dot.
    :return: A glob pattern matching all case permutations for that extension.
    :rtype: str
    """
    pattern = '*.'
    for char in extension:
        if char.isalpha():
            pattern += '[{lower}{upper}]'.format(lower=char.lower(), upper=char.upper())
        else:
            pattern += char
    return pattern


def get_images_filter():
    """
    Returns a filter string for a file dialog containing all the supported image formats.
    """
    from openlp.core.common.i18n import translate
    global IMAGES_FILTER
    if not IMAGES_FILTER:
        log.debug('Generating images filter.')
        formats = list(map(bytes.decode, map(bytes, QtGui.QImageReader.supportedImageFormats())))
        actual_formats = f"({' '.join(case_insensitive_glob(fmt) for fmt in formats)})"
        IMAGES_FILTER = f"{translate('OpenLP', 'Image Files')}{actual_formats}"
    return IMAGES_FILTER


def is_not_image_file(file_path):
    """
    Validate that the file is not an image file.

    :param pathlib.Path file_path: The file to be checked.
    :return: If the file is not an image
    :rtype: bool
    """
    if not (file_path and file_path.exists()):
        return True
    else:
        formats = [bytes(fmt).decode().lower() for fmt in QtGui.QImageReader.supportedImageFormats()]
        if file_path.suffix[1:].lower() in formats:
            return False
        return True


def clean_filename(filename):
    """
    Removes invalid characters from the given ``filename``.

    :param str filename:  The "dirty" file name to clean.
    :return: The cleaned string
    :rtype: str
    """
    return INVALID_FILE_CHARS.sub('_', CONTROL_CHARS.sub('', filename))


def get_file_encoding(file_path):
    """
    Utility function to incrementally detect the file encoding.

    :param pathlib.Path file_path: Filename for the file to determine the encoding for.
    :return: The name of the encoding detected
    :rtype: str
    """
    detector = UniversalDetector()
    try:
        with file_path.open('rb') as detect_file:
            while not detector.done:
                chunk = detect_file.read(1024)
                if not chunk:
                    break
                detector.feed(chunk)
    except OSError:
        log.exception('Error detecting file encoding')
    return detector.close()['encoding']


def normalize_str(irregular_string):
    """
    Normalize the supplied string. Remove unicode control chars and tidy up white space.

    :param str irregular_string: The string to normalize.
    :return: The normalized string
    :rtype: str
    """
    irregular_string = irregular_string.translate(REPLACMENT_CHARS_MAP)
    irregular_string = CONTROL_CHARS.sub('', irregular_string)
    irregular_string = NEW_LINE_REGEX.sub('\n', irregular_string)
    return WHITESPACE_REGEX.sub(' ', irregular_string)
