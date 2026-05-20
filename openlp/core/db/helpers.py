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
The :mod:`~openlp.core.db.helpers` module provides database helper functions for OpenLP
"""
import logging
import os
from copy import copy
from pathlib import Path
from typing import Optional, Tuple, Union
from urllib.parse import quote_plus as urlquote

from sqlalchemy import MetaData, create_engine, __version__ as sqla_version
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.scoping import ScopedSession
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.pool import StaticPool

from openlp.core.common import delete_file
from openlp.core.common.applocation import AppLocation
from openlp.core.common.i18n import translate
from openlp.core.common.registry import Registry
from openlp.core.lib.ui import critical_error_message_box

log = logging.getLogger(__name__)


def _set_url_database(url, database: str) -> URL:
    new_url = URL.create(
        drivername=url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        database=database,
        query=url.query
    )
    assert new_url.database == database, new_url
    return new_url


def _get_scalar_result(engine: Engine, sql: str):
    with engine.connect() as conn:
        return conn.scalar(sql)


def _sqlite_file_exists(database: Union[Path, str]) -> bool:
    database = Path(database)
    if not database.is_file() or database.stat().st_size < 100:
        return False

    with database.open('rb') as f:
        header = f.read(100)

    return header[:16] == b'SQLite format 3\x00'


def get_db_path(plugin_name: str, db_file_name: Union[Path, str, None] = None) -> str:
    """
    Create a path to a database from the plugin name and database name

    :param plugin_name: Name of plugin
    :param pathlib.Path | str | None db_file_name: File name of database
    :return: The path to the database
    :rtype: str
    """
    if db_file_name is None:
        return 'sqlite:///{path}/{plugin}.sqlite'.format(path=AppLocation.get_section_data_path(plugin_name),
                                                         plugin=plugin_name)
    elif os.path.isabs(db_file_name):
        return 'sqlite:///{db_file_name}'.format(db_file_name=db_file_name)
    else:
        return 'sqlite:///{path}/{name}'.format(path=AppLocation.get_section_data_path(plugin_name), name=db_file_name)


def handle_db_error(plugin_name: str, db_file_path: Union[Path, str]):
    """
    Log and report to the user that a database cannot be loaded

    :param plugin_name: Name of plugin
    :param pathlib.Path db_file_path: File name of database
    :return: None
    """
    db_path = get_db_path(plugin_name, db_file_path)
    log.exception('Error loading database: {db}'.format(db=db_path))
    critical_error_message_box(translate('OpenLP.Manager', 'Database Error'),
                               translate('OpenLP.Manager',
                                         'OpenLP cannot load your database.\n\nDatabase: {db}').format(db=db_path))


def database_exists(url: str) -> bool:
    """Check if a database exists.
    :param url: A SQLAlchemy engine URL.
    Performs backend-specific testing to quickly determine if a database
    exists on the server. ::
        database_exists('postgresql://postgres@localhost/name')  #=> False
        create_database('postgresql://postgres@localhost/name')
        database_exists('postgresql://postgres@localhost/name')  #=> True
    Supports checking against a constructed URL as well. ::
        engine = create_engine('postgresql://postgres@localhost/name')
        database_exists(engine.url)  #=> False
        create_database(engine.url)
        database_exists(engine.url)  #=> True

    Borrowed from SQLAlchemy_Utils since we only need this one function.
    Copied from a fork/pull request since SQLAlchemy_Utils didn't supprt SQLAlchemy 1.4 when it was released:
 https://github.com/nsoranzo/sqlalchemy-utils/blob/4f52578/sqlalchemy_utils/functions/database.py
    """

    url = copy(make_url(url))
    database = url.database
    dialect_name = url.get_dialect().name

    if dialect_name == 'postgresql':
        text = "SELECT 1 FROM pg_database WHERE datname='%s'" % database
        for db in (database, 'postgres', 'template1', 'template0', None):
            url = _set_url_database(url, database=db)
            engine = create_engine(url, poolclass=StaticPool)
            try:
                return bool(_get_scalar_result(engine, text))
            except (ProgrammingError, OperationalError):
                pass
        return False

    elif dialect_name == 'mysql':
        url = _set_url_database(url, database=None)
        engine = create_engine(url, poolclass=StaticPool)
        text = ("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
                "WHERE SCHEMA_NAME = '%s'" % database)
        return bool(_get_scalar_result(engine, text))

    elif dialect_name == 'sqlite':
        url = _set_url_database(url, database=None)
        engine = create_engine(url, poolclass=StaticPool)
        if database:
            return database == ':memory:' or _sqlite_file_exists(database)
        else:
            # The default SQLAlchemy database is in memory,
            # and :memory is not required, thus we should support that use-case
            return True
    else:
        text = 'SELECT 1'
        try:
            engine = create_engine(url, poolclass=StaticPool)
            return bool(_get_scalar_result(engine, text))
        except (ProgrammingError, OperationalError):
            return False


def init_db(url: str, auto_flush: bool = True, auto_commit: bool = False,
            base: Optional[DeclarativeMeta] = None) -> Tuple[ScopedSession, MetaData]:
    """
    Initialise and return the session and metadata for a database

    :param url: The database to initialise connection with
    :param auto_flush: Sets the flushing behaviour of the session
    :param auto_commit: Sets the commit behaviour of the session
    :param base: If using declarative, the base class to bind with
    """
    engine = create_engine(url, poolclass=StaticPool)
    if sqla_version.startswith('1.'):
        session = scoped_session(sessionmaker(autoflush=auto_flush, autocommit=auto_commit, bind=engine))
    else:
        session = scoped_session(sessionmaker(autoflush=auto_flush, autobegin=True, bind=engine))

    if base is None:
        metadata = MetaData()
        metadata.bind = engine
    else:
        base.metadata.bind = engine
        metadata = base.metadata
    return session, metadata


def init_url(plugin_name: str, db_file_name: Union[Path, str, None] = None) -> str:
    """
    Construct the connection string for a database.

    :param plugin_name: The name of the plugin for the database creation.
    :param pathlib.Path | str | None db_file_name: The database file name. Defaults to None resulting in the plugin_name
                                                   being used.
    :return: The database URL
    :rtype: str
    """
    settings = Registry().get('settings')
    db_type = settings.value(f'{plugin_name}/db type')
    if db_type == 'sqlite':
        db_url = get_db_path(plugin_name, db_file_name)
    else:
        db_url = '{type}://{user}:{password}@{host}/{db}'.format(
            type=db_type,
            user=urlquote(settings.value(f'{plugin_name}/db username')),
            password=urlquote(settings.value(f'{plugin_name}/db password')),
            host=urlquote(settings.value(f'{plugin_name}/db hostname')),
            db=urlquote(settings.value(f'{plugin_name}/db database')))
    return db_url


def delete_database(plugin_name: str, db_file_name: Union[Path, str, None] = None) -> bool:
    """
    Remove a database file from the system.

    :param plugin_name: The name of the plugin to remove the database for
    :param db_file_name: The database file name. Defaults to None resulting in the plugin_name being used.
    """
    db_file_path = AppLocation.get_section_data_path(plugin_name)
    if db_file_name:
        db_file_path = db_file_path / db_file_name
    else:
        db_file_path = db_file_path / plugin_name
    return delete_file(db_file_path)
