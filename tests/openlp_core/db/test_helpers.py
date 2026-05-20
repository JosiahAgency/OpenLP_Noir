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
Package to test the :mod:`~openlp.core.db.helpers` package.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

from sqlalchemy import MetaData, __version__ as sqla_version
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm.scoping import ScopedSession
from sqlalchemy.pool import StaticPool

from openlp.core.db.helpers import init_db, delete_database


def test_init_db_calls_correct_functions():
    """
    Test that the init_db function makes the correct function calls
    """
    # GIVEN: Mocked out SQLAlchemy calls and return objects, and an in-memory SQLite database URL
    with patch('openlp.core.db.helpers.create_engine') as mocked_create_engine, \
            patch('openlp.core.db.helpers.MetaData') as MockedMetaData, \
            patch('openlp.core.db.helpers.sessionmaker') as mocked_sessionmaker, \
            patch('openlp.core.db.helpers.scoped_session') as mocked_scoped_session:
        mocked_engine = MagicMock()
        mocked_metadata = MagicMock()
        mocked_sessionmaker_object = MagicMock()
        mocked_scoped_session_object = MagicMock()
        mocked_create_engine.return_value = mocked_engine
        MockedMetaData.return_value = mocked_metadata
        mocked_sessionmaker.return_value = mocked_sessionmaker_object
        mocked_scoped_session.return_value = mocked_scoped_session_object
        db_url = 'sqlite://'

        # WHEN: We try to initialise the db
        session, metadata = init_db(db_url)

        # THEN: We should see the correct function calls
        mocked_create_engine.assert_called_with(db_url, poolclass=StaticPool)
        MockedMetaData.assert_called_with()
        if sqla_version.startswith('1.'):
            mocked_sessionmaker.assert_called_with(autoflush=True, autocommit=False, bind=mocked_engine)
        else:
            mocked_sessionmaker.assert_called_with(autoflush=True, autobegin=True, bind=mocked_engine)
        mocked_scoped_session.assert_called_with(mocked_sessionmaker_object)
        assert session is mocked_scoped_session_object, 'The ``session`` object should be the mock'
        assert metadata is mocked_metadata, 'The ``metadata`` object should be the mock'


def test_init_db_defaults():
    """
    Test that initialising an in-memory SQLite database via ``init_db`` uses the defaults
    """
    # GIVEN: An in-memory SQLite URL
    db_url = 'sqlite://'
    Base = declarative_base()

    # WHEN: The database is initialised through init_db
    session, metadata = init_db(db_url, base=Base)

    # THEN: Valid session and metadata objects should be returned
    assert isinstance(session, ScopedSession), 'The ``session`` object should be a ``ScopedSession`` instance'
    assert isinstance(metadata, MetaData), 'The ``metadata`` object should be a ``MetaData`` instance'


def test_delete_database_without_db_file_name(registry):
    """
    Test that the ``delete_database`` function removes a database file, without the file name parameter
    """
    # GIVEN: Mocked out AppLocation class and delete_file method, a test plugin name and a db location
    with patch('openlp.core.db.helpers.AppLocation') as MockedAppLocation, \
            patch('openlp.core.db.helpers.delete_file') as mocked_delete_file:
        MockedAppLocation.get_section_data_path.return_value = Path('test-dir')
        mocked_delete_file.return_value = True
        test_plugin = 'test'
        test_location = Path('test-dir', test_plugin)

        # WHEN: delete_database is run without a database file
        result = delete_database(test_plugin)

        # THEN: The AppLocation.get_section_data_path and delete_file methods should have been called
        MockedAppLocation.get_section_data_path.assert_called_with(test_plugin)
        mocked_delete_file.assert_called_with(test_location)
        assert result is True, 'The result of delete_file should be True (was rigged that way)'


def test_delete_database_with_db_file_name():
    """
    Test that the ``delete_database`` function removes a database file, with the file name supplied
    """
    # GIVEN: Mocked out AppLocation class and delete_file method, a test plugin name and a db location
    with patch('openlp.core.db.helpers.AppLocation') as MockedAppLocation, \
            patch('openlp.core.db.helpers.delete_file') as mocked_delete_file:
        MockedAppLocation.get_section_data_path.return_value = Path('test-dir')
        mocked_delete_file.return_value = False
        test_plugin = 'test'
        test_db_file = 'mydb.sqlite'
        test_location = Path('test-dir', test_db_file)

        # WHEN: delete_database is run without a database file
        result = delete_database(test_plugin, test_db_file)

        # THEN: The AppLocation.get_section_data_path and delete_file methods should have been called
        MockedAppLocation.get_section_data_path.assert_called_with(test_plugin)
        mocked_delete_file.assert_called_with(test_location)
        assert result is False, 'The result of delete_file should be False (was rigged that way)'
