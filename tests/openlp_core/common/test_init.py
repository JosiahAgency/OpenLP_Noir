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
Functional tests to test the :mod:`~openlp.core.common` module
"""
import os
import pytest
import sys

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, call, patch

from openlp.core.common import Singleton, add_actions, clean_filename, clean_button_text, de_hump, delete_file, \
    extension_loader, get_file_encoding, get_filesystem_encoding, get_uno_command, get_uno_instance, md5_hash, \
    normalize_str, path_to_module, qmd5_hash, sha256_file_hash, trace_error_handler, verify_ip_address
from openlp.core.common.platform import is_win

from tests.resources.projector.data import TEST_HASH, TEST_PIN, TEST_SALT
from tests.utils.constants import TEST_RESOURCES_PATH

test_non_ascii_string = '이것은 한국어 시험 문자열'
test_non_ascii_hash = 'fc00c7912976f6e9c19099b514ced201'

ip4_loopback = '127.0.0.1'
ip4_local = '192.168.1.1'
ip4_broadcast = '255.255.255.255'
ip4_bad = '192.168.1.256'

ip6_loopback = '::1'
ip6_link_local = 'fe80::223:14ff:fe99:d315'
ip6_bad = 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff'


if is_win():
    p_prefix = 'C:\\'
else:
    p_prefix = '/'


def test_extension_loader_no_files_found():
    """
    Test the `extension_loader` function when no files are found
    """
    # GIVEN: A mocked `Path.glob` method which does not match any files
    with patch.object(Path, 'glob', return_value=[]), \
         patch('openlp.core.common.importlib.import_module') as mocked_import_module:

        # WHEN: Calling `extension_loader`
        extension_loader(Path('/', 'app', 'dir', 'openlp'), 'glob', ['file2.py', 'file3.py'])

        # THEN: `extension_loader` should not try to import any files
        assert mocked_import_module.called is False


def test_extension_loader_files_found():
    """
    Test the `extension_loader` function when it successfully finds and loads some files
    """
    # GIVEN: A mocked `Path.glob` method which returns a list of files
    with patch.object(Path, 'glob', return_value=[
            Path('/', 'app', 'dir', 'openlp', 'import_dir', 'file1.py'),
            Path('/', 'app', 'dir', 'openlp', 'import_dir', 'file2.py'),
            Path('/', 'app', 'dir', 'openlp', 'import_dir', 'file3.py'),
            Path('/', 'app', 'dir', 'openlp', 'import_dir', 'file4.py')]), \
            patch('openlp.core.common.import_openlp_module') as mocked_import_module:

        # WHEN: Calling `extension_loader` with a list of files to exclude
        extension_loader(Path('/', 'app', 'dir', 'openlp'),'glob', ['file2.py', 'file3.py'])

        # THEN: `extension_loader` should only try to import the files that are matched by the blob, excluding the
        #       files listed in the `excluded_files` argument
        mocked_import_module.assert_has_calls([call('openlp.import_dir.file1'),
                                               call('openlp.import_dir.file4')])
        assert "/app/dir/community" not in sys.path, "Community path has been added to the application sys.path"


def test_extension_loader_files_found_community():
    """
    Test the `extension_loader` function when it successfully finds and loads some files
    """
    # GIVEN: A mocked `Path.glob` method which returns a list of files
    with patch.object(Path, 'glob', return_value=[
            Path(p_prefix, 'app', 'dir', 'contrib', 'import_dir', 'file1.py'),
            Path(p_prefix, 'app', 'dir', 'contrib', 'import_dir', 'file2.py'),
            Path(p_prefix, 'app', 'dir', 'contrib', 'import_dir', 'file3.py'),
            Path(p_prefix, 'app', 'dir', 'contrib', 'import_dir', 'file4.py')]), \
            patch('openlp.core.common.import_openlp_module') as mocked_import_module:

        # WHEN: Calling `extension_loader` with a list of files to exclude
        extension_loader(Path(p_prefix, 'app', 'dir'), 'glob', ['file2.py', 'file3.py'], True)

        # THEN: `extension_loader` should only try to import the files that are matched by the blob, excluding the
        #       files listed in the `excluded_files` argument
        mocked_import_module.assert_has_calls([call('contrib.import_dir.file1'),
                                               call('contrib.import_dir.file4')])
        expected_path = p_prefix + 'app' + os.path.sep + 'dir'
        assert expected_path in sys.path, expected_path + ' path has not been added to the application sys.path'


def test_extension_loader_import_error():
    """
    Test the `extension_loader` function when `SourceFileLoader` raises a `ImportError`
    """
    # GIVEN: A mocked `import_module` which raises an `ImportError`
    with patch.object(Path, 'glob', return_value=[
            Path(p_prefix, 'app', 'dir', 'openlp', 'import_dir', 'file1.py')]), \
            patch('openlp.core.common.import_openlp_module', side_effect=ImportError()), \
            patch('openlp.core.common.log') as mocked_logger:

        # WHEN: Calling `extension_loader`
        extension_loader(Path(p_prefix, 'app', 'dir', 'openlp'),'glob')

        # THEN: The `ImportError` should be caught and logged
        assert mocked_logger.exception.called


def test_extension_loader_os_error():
    """
    Test the `extension_loader` function when `import_module` raises a `ImportError`
    """
    # GIVEN: A mocked `SourceFileLoader` which raises an `OSError`
    with patch.object(Path, 'glob', return_value=[
            Path('/', 'app', 'dir', 'openlp', 'import_dir', 'file1.py')]), \
            patch('openlp.core.common.import_openlp_module', side_effect=OSError()), \
            patch('openlp.core.common.log') as mocked_logger:

        # WHEN: Calling `extension_loader`
        extension_loader(Path('/', 'app', 'dir', 'openlp'), 'glob')

        # THEN: The `OSError` should be caught and logged
        assert mocked_logger.exception.called


def test_de_hump_conversion():
    """
    Test the de_hump function with a class name
    """
    # GIVEN: a Class name in Camel Case
    string = "MyClass"

    # WHEN: we call de_hump
    new_string = de_hump(string)

    # THEN: the new string should be converted to python format
    assert new_string == "my_class", 'The class name should have been converted'


def test_de_hump_static():
    """
    Test the de_hump function with a python string
    """
    # GIVEN: a Class name in Camel Case
    string = "my_class"

    # WHEN: we call de_hump
    new_string = de_hump(string)

    # THEN: the new string should be converted to python format
    assert new_string == "my_class", 'The class name should have been preserved'


def test_path_to_module():
    """
    Test `path_to_module` when supplied with a `Path` object
    """
    # GIVEN: A `Path` object
    path = Path('core', 'ui', 'media', 'vlcplayer.py')

    # WHEN: Calling path_to_module with the `Path` object
    result = path_to_module(path)

    # THEN: path_to_module should return the module name
    assert result == 'openlp.core.ui.media.vlcplayer'


def test_path_to_module_community():
    """
    Test `path_to_module` when supplied with a `Path` object
    """
    # GIVEN: A `Path` object
    path = Path('core', 'ui', 'media', 'vlcplayer.py')

    # WHEN: Calling path_to_module with the `Path` object
    result = path_to_module(path, True)

    # THEN: path_to_module should return the module name
    assert result == 'contrib.core.ui.media.vlcplayer'


def test_trace_error_handler():
    """
    Test the trace_error_handler() method
    """
    # GIVEN: Mocked out objects
    with patch('openlp.core.common.traceback') as mocked_traceback:
        mocked_traceback.extract_stack.return_value = [('openlp.fake', 56, None, 'trace_error_handler_test')]
        mocked_logger = MagicMock()

        # WHEN: trace_error_handler() is called
        trace_error_handler(mocked_logger)

        # THEN: The mocked_logger.error() method should have been called with the correct parameters
        mocked_logger.error.assert_called_with(
            'OpenLP Error trace\n   File openlp.fake at line 56 \n\t called trace_error_handler_test')


def test_singleton_metaclass_multiple_init():
    """
    Test that a class using the Singleton Metaclass is only initialised once despite being called several times and
    that the same instance is returned each time..
    """
    # GIVEN: The Singleton Metaclass and a test class using it
    class SingletonClass(metaclass=Singleton):
        def __init__(self):
            pass

    with patch.object(SingletonClass, '__init__', return_value=None) as patched_init:

        # WHEN: Initialising the class multiple times
        inst_1 = SingletonClass()
        inst_2 = SingletonClass()

    # THEN: The __init__ method of the SingletonClass should have only been called once, and both returned values
    #       should be the same instance.
    assert inst_1 is inst_2
    assert patched_init.call_count == 1


def test_singleton_metaclass_multiple_classes():
    """
    Test that multiple classes using the Singleton Metaclass return the different an appropriate instances.
    """
    # GIVEN: Two different classes using the Singleton Metaclass
    class SingletonClass1(metaclass=Singleton):
        def __init__(self):
            pass

    class SingletonClass2(metaclass=Singleton):
        def __init__(self):
            pass

    # WHEN: Initialising both classes
    s_c1 = SingletonClass1()
    s_c2 = SingletonClass2()

    # THEN: The instances  should be an instance of the appropriate class
    assert isinstance(s_c1, SingletonClass1)
    assert isinstance(s_c2, SingletonClass2)


def test_normalize_str_leaves_newlines():
    # GIVEN: a string containing newlines
    string = 'something\nelse'
    # WHEN: normalize is called
    normalized_string = normalize_str(string)
    # THEN: string is unchanged
    assert normalized_string == string


def test_normalize_str_removes_null_byte():
    # GIVEN: a string containing a null byte
    string = 'somet\x00hing'
    # WHEN: normalize is called
    normalized_string = normalize_str(string)
    # THEN: nullbyte is removed
    assert normalized_string == 'something'


def test_normalize_str_replaces_crlf_with_lf():
    # GIVEN: a string containing crlf
    string = 'something\r\nelse'
    # WHEN: normalize is called
    normalized_string = normalize_str(string)
    # THEN: crlf is replaced with lf
    assert normalized_string == 'something\nelse'


def test_clean_button_text():
    """
    Test the clean_button_text() function.
    """
    # GIVEN: Button text
    input_text = '&Next >'
    expected_text = 'Next'

    # WHEN: The button caption is sent through the clean_button_text function
    actual_text = clean_button_text(input_text)

    # THEN: The text should have been cleaned
    assert expected_text == actual_text, 'The text should be clean'


def test_ip4_loopback_valid():
    """
    Test IPv4 loopbackvalid
    """
    # WHEN: Test with a local loopback test
    valid = verify_ip_address(addr=ip4_loopback)

    # THEN: Verify we received True
    assert valid, 'IPv4 loopback address should have been valid'


def test_ip4_local_valid():
    """
    Test IPv4 local valid
    """
    # WHEN: Test with a local loopback test
    valid = verify_ip_address(addr=ip4_local)

    # THEN: Verify we received True
    assert valid is True, 'IPv4 local address should have been valid'


def test_ip4_broadcast_valid():
    """
    Test IPv4 broadcast valid
    """
    # WHEN: Test with a local loopback test
    valid = verify_ip_address(addr=ip4_broadcast)

    # THEN: Verify we received True
    assert valid is True, 'IPv4 broadcast address should have been valid'


def test_ip4_address_invalid():
    """
    Test IPv4 address invalid
    """
    # WHEN: Test with a local loopback test
    valid = verify_ip_address(addr=ip4_bad)

    # THEN: Verify we received True
    assert valid is False, 'Bad IPv4 address should not have been valid'


def test_ip6_loopback_valid():
    """
    Test IPv6 loopback valid
    """
    # WHEN: Test IPv6 loopback address
    valid = verify_ip_address(addr=ip6_loopback)

    # THEN: Validate return
    assert valid is True, 'IPv6 loopback address should have been valid'


def test_ip6_local_valid():
    """
    Test IPv6 link-local valid
    """
    # WHEN: Test IPv6 link-local address
    valid = verify_ip_address(addr=ip6_link_local)

    # THEN: Validate return
    assert valid is True, 'IPv6 link-local address should have been valid'


def test_ip6_address_invalid():
    """
    Test NetworkUtils IPv6 address invalid
    """
    # WHEN: Given an invalid IPv6 address
    valid = verify_ip_address(addr=ip6_bad)

    # THEN: Validate bad return
    assert valid is False, 'IPv6 bad address should have been invalid'


def test_sha256_file_hash():
    """
    Test SHA256 file hash
    """
    # GIVEN: A mocked Path object
    ppt_path = os.path.join(TEST_RESOURCES_PATH, 'presentations', 'test.ppt')
    filename = Path(ppt_path)

    # WHEN: Generating a hash for the file
    result = sha256_file_hash(filename)

    # THEN: Validate that the hash is correct
    assert result == 'be6d7bdca25d1662d7faa1f856bfc224646dbad3b65ebff800d9ae70537968f9'


def test_sha256_file_hash_no_exist():
    """
    Test SHA256 file hash when the file doesn't exist
    """
    # GIVEN: A mocked Path object
    mocked_path = MagicMock()
    mocked_path.exists.return_value = False

    # WHEN: A hash is generated on a non-existent file
    result = sha256_file_hash(mocked_path)

    # THEN: the result should be None
    assert result is None


def test_sha256_file_hash_permission_error():
    """
    Test that SHA256 file hash re-raises a permission error
    """
    # GIVEN: A mocked Path object
    mocked_path = MagicMock()
    mocked_path.open.side_effect = PermissionError

    # WHEN: Generating a hash for the file
    # THEN: The PermissionError should be bubbled up
    with pytest.raises(PermissionError):
        sha256_file_hash(mocked_path)


def test_sha256_file_hash_other_error():
    """
    Test SHA256 file hash when there is an error other than permission error
    """
    # GIVEN: A mocked Path object
    mocked_path = MagicMock()
    mocked_path.open.side_effect = NotADirectoryError

    # WHEN: Generating a hash for the file
    result = sha256_file_hash(mocked_path)

    # THEN: The result should be None
    assert result is None


def test_md5_hash():
    """
    Test MD5 hash from salt+data pass (python)
    """
    # WHEN: Given a known salt+data
    hash_ = md5_hash(salt=TEST_SALT.encode('utf-8'), data=TEST_PIN.encode('utf-8'))

    # THEN: Validate return has is same
    assert hash_ == TEST_HASH, 'MD5 should have returned a good hash'


def test_md5_hash_no_salt_data():
    """
    Test MD5 hash with no salt or data (Python)
    """
    # WHEN: Given a known salt+data
    hash_ = md5_hash(None, None)

    # THEN: Validate return has is same
    assert hash_ is None, 'MD5 should have returned None'


def test_md5_hash_bad():
    """
    Test MD5 hash from salt+data fail (python)
    """
    # WHEN: Given a different salt+hash
    hash_ = md5_hash(salt=TEST_PIN.encode('utf-8'), data=TEST_SALT.encode('utf-8'))

    # THEN: return data is different
    assert hash_ is not TEST_HASH, 'MD5 should have returned a bad hash'


def test_qmd5_hash():
    """
    Test MD5 hash from salt+data pass (Qt)
    """
    # WHEN: Given a known salt+data
    hash_ = qmd5_hash(salt=TEST_SALT.encode('utf-8'), data=TEST_PIN.encode('utf-8'))

    # THEN: Validate return has is same
    assert hash_ == TEST_HASH, 'Qt-MD5 should have returned a good hash'


def test_qmd5_hash_no_salt_data():
    """
    Test MD5 hash with no salt or data (Qt)
    """
    # WHEN: Given a known salt+data
    hash_ = qmd5_hash(None, None)

    # THEN: Validate return has is same
    assert hash_ is None, 'Qt-MD5 should have returned None'


def test_qmd5_hash_bad():
    """
    Test MD5 hash from salt+hash fail (Qt)
    """
    # WHEN: Given a different salt+hash
    hash_ = qmd5_hash(salt=TEST_PIN.encode('utf-8'), data=TEST_SALT.encode('utf-8'))

    # THEN: return data is different
    assert hash_ is not TEST_HASH, 'Qt-MD5 should have returned a bad hash'


def test_md5_non_ascii_string():
    """
    Test MD5 hash with non-ascii string - bug 1417809
    """
    # WHEN: Non-ascii string is hashed
    hash_ = md5_hash(salt=test_non_ascii_string.encode('utf-8'), data=None)

    # THEN: Valid MD5 hash should be returned
    assert hash_ == test_non_ascii_hash, 'MD5 should have returned a valid hash'


def test_qmd5_non_ascii_string():
    """
    Test MD5 hash with non-ascii string - bug 1417809
    """
    # WHEN: Non-ascii string is hashed
    hash_ = md5_hash(data=test_non_ascii_string.encode('utf-8'))

    # THEN: Valid MD5 hash should be returned
    assert hash_ == test_non_ascii_hash, 'Qt-MD5 should have returned a valid hash'


def test_add_actions_empty_list():
    """
    Test that no actions are added when the list is empty
    """
    # GIVEN: a mocked action list, and an empty list
    mocked_target = MagicMock()
    empty_list = []

    # WHEN: The empty list is added to the mocked target
    add_actions(mocked_target, empty_list)

    # THEN: The add method on the mocked target is never called
    assert mocked_target.addSeparator.call_count == 0, 'addSeparator method should not have been called'
    assert mocked_target.addAction.call_count == 0, 'addAction method should not have been called'


def test_add_actions_none_action():
    """
    Test that a separator is added when a None action is in the list
    """
    # GIVEN: a mocked action list, and a list with None in it
    mocked_target = MagicMock()
    separator_list = [None]

    # WHEN: The list is added to the mocked target
    add_actions(mocked_target, separator_list)

    # THEN: The addSeparator method is called, but the addAction method is never called
    mocked_target.addSeparator.assert_called_with()
    assert mocked_target.addAction.call_count == 0, 'addAction method should not have been called'


def test_add_actions_add_action():
    """
    Test that an action is added when a valid action is in the list
    """
    # GIVEN: a mocked action list, and a list with an action in it
    mocked_target = MagicMock()
    action_list = ['action']

    # WHEN: The list is added to the mocked target
    add_actions(mocked_target, action_list)

    # THEN: The addSeparator method is not called, and the addAction method is called
    assert mocked_target.addSeparator.call_count == 0, 'addSeparator method should not have been called'
    mocked_target.addAction.assert_called_with('action')


def test_add_actions_action_and_none():
    """
    Test that an action and a separator are added when a valid action and None are in the list
    """
    # GIVEN: a mocked action list, and a list with an action and None in it
    mocked_target = MagicMock()
    action_list = ['action', None]

    # WHEN: The list is added to the mocked target
    add_actions(mocked_target, action_list)

    # THEN: The addSeparator method is called, and the addAction method is called
    mocked_target.addSeparator.assert_called_with()
    mocked_target.addAction.assert_called_with('action')


def test_get_uno_instance_pipe():
    """
    Test that when the UNO connection type is "pipe" the resolver is given the "pipe" URI
    """
    # GIVEN: A mock resolver object and UNO_CONNECTION_TYPE is "pipe"
    mock_resolver = MagicMock()

    # WHEN: get_uno_instance() is called
    get_uno_instance(mock_resolver)

    # THEN: the resolve method is called with the correct argument
    mock_resolver.resolve.assert_called_with('uno:pipe,name=openlp_pipe;urp;StarOffice.ComponentContext')


def test_get_uno_instance_socket():
    """
    Test that when the UNO connection type is other than "pipe" the resolver is given the "socket" URI
    """
    # GIVEN: A mock resolver object and UNO_CONNECTION_TYPE is "socket"
    mock_resolver = MagicMock()

    # WHEN: get_uno_instance() is called
    get_uno_instance(mock_resolver, 'socket')

    # THEN: the resolve method is called with the correct argument
    mock_resolver.resolve.assert_called_with('uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext')


def test_get_uno_command_libreoffice_command_exists():
    """
    Test the ``get_uno_command`` function uses the libreoffice command when available.
    :return:
    """

    # GIVEN: A patched 'which' method which returns a path when called with 'libreoffice'
    with patch('openlp.core.common.which',
               **{'side_effect': lambda command: {'libreoffice': '/usr/bin/libreoffice'}[command]}):
        # WHEN: Calling get_uno_command
        result = get_uno_command()

        # THEN: The command 'libreoffice' should be called with the appropriate parameters
        assert result == 'libreoffice --nologo --norestore --minimized --nodefault --nofirststartwizard' \
                         ' "--accept=pipe,name=openlp_pipe;urp;"'


def test_get_uno_command_only_soffice_command_exists():
    """
    Test the ``get_uno_command`` function uses the soffice command when the libreoffice command is not available.
    :return:
    """

    # GIVEN: A patched 'which' method which returns None when called with 'libreoffice' and a path when called with
    #        'soffice'
    with patch('openlp.core.common.which',
               **{'side_effect': lambda command: {'libreoffice': None, 'soffice': '/usr/bin/soffice'}[
                   command]}):
        # WHEN: Calling get_uno_command
        result = get_uno_command()

        # THEN: The command 'soffice' should be called with the appropriate parameters
        assert result == 'soffice --nologo --norestore --minimized --nodefault --nofirststartwizard' \
                         ' "--accept=pipe,name=openlp_pipe;urp;"'


def test_get_uno_command_when_no_command_exists():
    """
    Test the ``get_uno_command`` function raises an FileNotFoundError when neither the libreoffice or soffice
    commands are available.
    :return:
    """

    # GIVEN: A patched 'which' method which returns None
    with pytest.raises(FileNotFoundError), \
            patch('openlp.core.common.which', **{'return_value': None}):
        # WHEN: Calling get_uno_command
        # THEN: a FileNotFoundError exception should be raised
        get_uno_command()


def test_get_uno_command_connection_type():
    """
    Test the ``get_uno_command`` function when the connection type is anything other than pipe.
    :return:
    """

    # GIVEN: A patched 'which' method which returns 'libreoffice'
    with patch('openlp.core.common.which', **{'return_value': 'libreoffice'}):
        # WHEN: Calling get_uno_command with a connection type other than pipe
        result = get_uno_command('socket')

        # THEN: The connection parameters should be set for socket
        assert result == 'libreoffice --nologo --norestore --minimized --nodefault --nofirststartwizard' \
                         ' "--accept=socket,host=localhost,port=2002;urp;"'


def test_get_filesystem_encoding_sys_function_not_called():
    """
    Test the get_filesystem_encoding() function does not call the sys.getdefaultencoding() function
    """
    # GIVEN: sys.getfilesystemencoding returns "cp1252"
    with patch('openlp.core.common.sys.getfilesystemencoding') as mocked_getfilesystemencoding, \
            patch('openlp.core.common.sys.getdefaultencoding') as mocked_getdefaultencoding:
        mocked_getfilesystemencoding.return_value = 'cp1252'

        # WHEN: get_filesystem_encoding() is called
        result = get_filesystem_encoding()

        # THEN: getdefaultencoding should have been called
        mocked_getfilesystemencoding.assert_called_with()
        assert mocked_getdefaultencoding.called == 0, 'getdefaultencoding should not have been called'
        assert 'cp1252' == result, 'The result should be "cp1252"'


def test_get_filesystem_encoding_sys_function_is_called():
    """
    Test the get_filesystem_encoding() function calls the sys.getdefaultencoding() function
    """
    # GIVEN: sys.getfilesystemencoding returns None and sys.getdefaultencoding returns "utf-8"
    with patch('openlp.core.common.sys.getfilesystemencoding') as mocked_getfilesystemencoding, \
            patch('openlp.core.common.sys.getdefaultencoding') as mocked_getdefaultencoding:
        mocked_getfilesystemencoding.return_value = None
        mocked_getdefaultencoding.return_value = 'utf-8'

        # WHEN: get_filesystem_encoding() is called
        result = get_filesystem_encoding()

        # THEN: getdefaultencoding should have been called
        mocked_getfilesystemencoding.assert_called_with()
        mocked_getdefaultencoding.assert_called_with()
        assert 'utf-8' == result, 'The result should be "utf-8"'


def test_clean_filename():
    """
    Test the clean_filename() function
    """
    # GIVEN: A invalid file name and the valid file name.
    invalid_name = 'A_file_with_invalid_characters_[\\/:*?"<>|+[]%].py'
    wanted_name = 'A_file_with_invalid_characters________________.py'

    # WHEN: Clean the name.
    result = clean_filename(invalid_name)

    # THEN: The file name should be cleaned.
    assert wanted_name == result, 'The file name should not contain any special characters.'


def test_delete_file_no_path():
    """
    Test the delete_file function when called with out a valid path
    """
    # GIVEN: A blank path
    # WEHN: Calling delete_file
    result = delete_file(None)

    # THEN: delete_file should return False
    assert result is False, "delete_file should return False when called with None"


def test_delete_file_path_success():
    """
    Test the delete_file function when it successfully deletes a file
    """
    # GIVEN: A patched 'exists' method which returns True when called
    with patch.object(Path, 'exists', return_value=True), \
            patch.object(Path, 'unlink') as mocked_unlink:

        # WHEN: Calling delete_file with a file path
        result = delete_file(Path('path', 'file.ext'))

        # THEN: delete_file should return True
        assert mocked_unlink.called is True
        assert result is True, 'delete_file should return True when it successfully deletes a file'


def test_delete_file_path_no_file_exists():
    """
    Test the `delete_file` function when the file to remove does not exist
    """
    # GIVEN: A patched `exists` methods on the Path object, which returns False
    with patch.object(Path, 'exists', return_value=False), \
            patch.object(Path, 'unlink') as mocked_unlink:

        # WHEN: Calling `delete_file with` a file path
        result = delete_file(Path('path', 'file.ext'))

        # THEN: The function should not attempt to delete the file and it should return True
        assert mocked_unlink.called is False
        assert result is True, 'delete_file should return True when the file doesnt exist'


def test_delete_file_path_exception():
    """
    Test the delete_file function when an exception is raised
    """
    # GIVEN: A test `Path` object with a patched exists method which raises an OSError
    #       called.
    with patch.object(Path, 'exists') as mocked_exists, \
            patch('openlp.core.common.log') as mocked_log:
        mocked_exists.side_effect = OSError

        # WHEN: Calling delete_file with a the test Path object
        result = delete_file(Path('path', 'file.ext'))

        # THEN: The exception should be logged and `delete_file` should return False
        assert mocked_log.exception.called
        assert result is False, 'delete_file should return False when an OSError is raised'


def test_get_file_encoding_done():
    """
    Test get_file_encoding when the detector sets done to True
    """
    # GIVEN: A mocked UniversalDetector instance with done attribute set to True after first iteration
    with patch('openlp.core.common.UniversalDetector') as mocked_universal_detector, \
            patch.object(Path, 'open', return_value=BytesIO(b'data' * 260)) as mocked_open:
        encoding_result = {'encoding': 'UTF-8', 'confidence': 0.99}
        mocked_universal_detector_inst = MagicMock(**{'close.return_value': encoding_result})
        type(mocked_universal_detector_inst).done = PropertyMock(side_effect=[False, True])
        mocked_universal_detector.return_value = mocked_universal_detector_inst

        # WHEN: Calling get_file_encoding
        result = get_file_encoding(Path('file name'))

        # THEN: The feed method of UniversalDetector should only br called once before returning a result
        mocked_open.assert_called_once_with('rb')
        assert mocked_universal_detector_inst.feed.mock_calls == [call(b'data' * 256)]
        mocked_universal_detector_inst.close.assert_called_once_with()
        assert result == 'UTF-8'


def test_get_file_encoding_eof():
    """
    Test get_file_encoding when the end of the file is reached
    """
    # GIVEN: A mocked UniversalDetector instance which isn't set to done and a mocked open, with 1040 bytes of test
    #       data (enough to run the iterator twice)
    with patch('openlp.core.common.UniversalDetector') as mocked_universal_detector, \
            patch.object(Path, 'open', return_value=BytesIO(b'data' * 260)) as mocked_open:
        encoding_result = {'encoding': 'UTF-8', 'confidence': 0.99}
        mocked_universal_detector_inst = MagicMock(mock=mocked_universal_detector,
                                                   **{'done': False, 'close.return_value': encoding_result})
        mocked_universal_detector.return_value = mocked_universal_detector_inst

        # WHEN: Calling get_file_encoding
        result = get_file_encoding(Path('file name'))

        # THEN: The feed method of UniversalDetector should have been called twice before returning a result
        mocked_open.assert_called_once_with('rb')
        assert mocked_universal_detector_inst.feed.mock_calls == [call(b'data' * 256), call(b'data' * 4)]
        mocked_universal_detector_inst.close.assert_called_once_with()
        assert result == 'UTF-8'


def test_get_file_encoding_oserror():
    """
    Test get_file_encoding when the end of the file is reached
    """
    # GIVEN: A mocked UniversalDetector instance which isn't set to done and a mocked open, with 1040 bytes of test
    #       data (enough to run the iterator twice)
    with patch('openlp.core.common.UniversalDetector') as mocked_universal_detector, \
            patch('builtins.open', side_effect=OSError), \
            patch('openlp.core.common.log') as mocked_log:
        encoding_result = {'encoding': 'UTF-8', 'confidence': 0.99}
        mocked_universal_detector_inst = MagicMock(mock=mocked_universal_detector,
                                                   **{'done': False, 'close.return_value': encoding_result})
        mocked_universal_detector.return_value = mocked_universal_detector_inst

        # WHEN: Calling get_file_encoding
        result = get_file_encoding(Path('file name'))

        # THEN: log.exception should be called and get_file_encoding should return None
        mocked_log.exception.assert_called_once_with('Error detecting file encoding')
        mocked_universal_detector_inst.feed.assert_not_called()
        mocked_universal_detector_inst.close.assert_called_once_with()
        assert result == 'UTF-8'
