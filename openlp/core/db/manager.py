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
The :mod:`~openlp.core.db.manager` module provides the database manager for the plugins
"""
import logging
from pathlib import Path
from types import FunctionType, ModuleType
from typing import List, Optional, Type, Union

from sqlalchemy import create_engine, func, text
from sqlalchemy.exc import DBAPIError, InvalidRequestError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.sql.expression import select, delete

from openlp.core.common.i18n import translate
from openlp.core.db.helpers import handle_db_error, init_url
from openlp.core.db.upgrades import upgrade_db
from openlp.core.lib.ui import critical_error_message_box


log = logging.getLogger(__name__)


class DBManager(object):
    """
    Provide generic object persistence management
    """
    def __init__(self, plugin_name: str, init_schema: FunctionType,
                 db_file_path: Union[Path, str, None] = None,
                 upgrade_mod: Optional[ModuleType] = None, session: Optional[Session] = None):
        """
        Runs the initialisation process that includes creating the connection to the database and the tables if they do
        not exist.

        :param plugin_name: The name to setup paths and settings section names
        :param init_schema: The init_schema function for this database
        :param pathlib.Path | None db_file_path: The file name to use for this database. Defaults to None resulting in
            the plugin_name being used.
        :param upgrade_mod: The upgrade_schema function for this database
        """
        super().__init__()
        self.is_dirty = False
        self.session = None
        self.db_url = None
        log.debug('Manager: Creating new DB url')
        self.db_url = init_url(plugin_name, db_file_path)
        if not session:
            try:
                self.session = init_schema(self.db_url)
            except (SQLAlchemyError, DBAPIError):
                handle_db_error(plugin_name, db_file_path)
        else:
            self.session = session
        if upgrade_mod:
            try:
                db_ver, up_ver = upgrade_db(self.db_url, upgrade_mod)
            except (SQLAlchemyError, DBAPIError):
                handle_db_error(plugin_name, db_file_path)
                return
            if db_ver > up_ver:
                critical_error_message_box(
                    translate('OpenLP.Manager', 'Database Error'),
                    translate('OpenLP.Manager', 'The database being loaded was created in a more recent version of '
                              'OpenLP. The database is version {db_ver}, while OpenLP expects version {db_up}. '
                              'The database will not be loaded.\n\nDatabase: {db_name}').format(db_ver=db_ver,
                                                                                                db_up=up_ver,
                                                                                                db_name=self.db_url))

                return

    def save_object(self, object_instance: DeclarativeMeta, commit: bool = True):
        """
        Save an object to the database

        :param object_instance: The object to save
        :param commit: Commit the session with this object
        """
        for try_count in range(3):
            try:
                self.session.add(object_instance)
                if commit:
                    self.session.commit()
                self.is_dirty = True
                return True
            except OperationalError:
                # This exception clause is for users running MySQL which likes to terminate connections on its own
                # without telling anyone. See bug #927473. However, other dbms can raise it, usually in a
                # non-recoverable way. So we only retry 3 times.
                log.exception('Probably a MySQL issue - "MySQL has gone away"')
                self.session.rollback()
                if try_count >= 2:
                    raise
            except InvalidRequestError:
                self.session.rollback()
                log.exception('Object list save failed')
                return False
            except Exception:
                self.session.rollback()
                raise

    def save_objects(self, object_list: List[DeclarativeMeta], commit: bool = True):
        """
        Save a list of objects to the database

        :param object_list: The list of objects to save
        :param commit: Commit the session with this object
        """
        for try_count in range(3):
            try:
                self.session.add_all(object_list)
                if commit:
                    self.session.commit()
                self.is_dirty = True
                return True
            except OperationalError:
                # This exception clause is for users running MySQL which likes to terminate connections on its own
                # without telling anyone. See bug #927473. However, other dbms can raise it, usually in a
                # non-recoverable way. So we only retry 3 times.
                log.exception('Probably a MySQL issue, "MySQL has gone away"')
                self.session.rollback()
                if try_count >= 2:
                    raise
            except InvalidRequestError:
                self.session.rollback()
                log.exception('Object list save failed')
                return False
            except Exception:
                self.session.rollback()
                raise

    def get_object(self, object_class: Type[DeclarativeMeta], key: Union[str, int] = None) -> DeclarativeMeta:
        """
        Return the details of an object

        :param object_class:  The type of object to return
        :param key: The unique reference or primary key for the instance to return
        """
        if not key:
            return object_class()
        else:
            for try_count in range(3):
                try:
                    return self.session.get(object_class, key)
                except OperationalError:
                    # This exception clause is for users running MySQL which likes to terminate connections on its own
                    # without telling anyone. See bug #927473. However, other dbms can raise it, usually in a
                    # non-recoverable way. So we only retry 3 times.
                    log.exception('Probably a MySQL issue, "MySQL has gone away"')
                    if try_count >= 2:
                        raise

    def get_object_filtered(self, object_class: Type[DeclarativeMeta], *filter_clauses) -> DeclarativeMeta:
        """
        Returns an object matching specified criteria

        :param object_class: The type of object to return
        :param filter_clause: The criteria to select the object by
        """
        query = select(object_class)
        for filter_clause in filter_clauses:
            query = query.where(filter_clause)
        for try_count in range(3):
            try:
                return self.session.execute(query).scalar()
            except OperationalError as oe:
                # This exception clause is for users running MySQL which likes to terminate connections on its own
                # without telling anyone. See bug #927473. However, other dbms can raise it, usually in a
                # non-recoverable way. So we only retry 3 times.
                if try_count >= 2 or 'MySQL has gone away' in str(oe):
                    raise
                log.exception('Probably a MySQL issue, "MySQL has gone away"')

    def get_all_objects(self, object_class: Type[DeclarativeMeta], filter_clause=None, order_by_ref=None):
        """
        Returns all the objects from the database

        :param object_class: The type of objects to return
        :param filter_clause: The filter governing selection of objects to return. Defaults to None.
        :param order_by_ref: Any parameters to order the returned objects by. Defaults to None.
        """
        query = select(object_class)
        # Check filter_clause
        if filter_clause is not None:
            if isinstance(filter_clause, list):
                for dbfilter in filter_clause:
                    query = query.where(dbfilter)
            else:
                query = query.where(filter_clause)
        # Check order_by_ref
        if order_by_ref is not None:
            if isinstance(order_by_ref, list):
                query = query.order_by(*order_by_ref)
            else:
                query = query.order_by(order_by_ref)

        for try_count in range(3):
            try:
                return self.session.execute(query).scalars().all()
            except OperationalError:
                # This exception clause is for users running MySQL which likes to terminate connections on its own
                # without telling anyone. See bug #927473. However, other dbms can raise it, usually in a
                # non-recoverable way. So we only retry 3 times.
                log.exception('Probably a MySQL issue, "MySQL has gone away"')
                if try_count >= 2:
                    raise

    def get_object_count(self, object_class: Type[DeclarativeMeta], filter_clause=None):
        """
        Returns a count of the number of objects in the database.

        :param object_class: The type of objects to return.
        :param filter_clause: The filter governing selection of objects to return. Defaults to None.
        """
        query = select(func.count()).select_from(object_class)
        if filter_clause is not None:
            query = query.where(filter_clause)
        for try_count in range(3):
            try:
                return self.session.execute(query).scalar()
            except OperationalError:
                # This exception clause is for users running MySQL which likes to terminate connections on its own
                # without telling anyone. See bug #927473. However, other dbms can raise it, usually in a
                # non-recoverable way. So we only retry 3 times.
                log.exception('Probably a MySQL issue, "MySQL has gone away"')
                if try_count >= 2:
                    raise

    def delete_object(self, object_class: Type[DeclarativeMeta], key: Union[int, str]):
        """
        Delete an object from the database

        :param object_class: The type of object to delete
        :param key: The unique reference or primary key for the instance to be deleted
        """
        if key != 0:
            object_instance = self.get_object(object_class, key)
            for try_count in range(3):
                try:
                    self.session.delete(object_instance)
                    self.session.commit()
                    self.is_dirty = True
                    return True
                except OperationalError:
                    # This exception clause is for users running MySQL which likes to terminate connections on its own
                    # without telling anyone. See bug #927473. However, other dbms can raise it, usually in a
                    # non-recoverable way. So we only retry 3 times.
                    log.exception('Probably a MySQL issue, "MySQL has gone away"')
                    self.session.rollback()
                    if try_count >= 2:
                        raise
                except InvalidRequestError:
                    self.session.rollback()
                    log.exception('Failed to delete object')
                    return False
                except Exception:
                    self.session.rollback()
                    raise
        else:
            return True

    def delete_all_objects(self, object_class, filter_clause=None):
        """
        Delete all object records. This method should only be used for simple tables and **not** ones with
        relationships. The relationships are not deleted from the database and this will lead to database corruptions.

        :param object_class:  The type of object to delete
        :param filter_clause: The filter governing selection of objects to return. Defaults to None.
        """
        for try_count in range(3):
            try:
                query = delete(object_class)
                if filter_clause is not None:
                    query = query.where(filter_clause)
                self.session.execute(query.execution_options(synchronize_session=False))
                self.session.commit()
                self.is_dirty = True
                return True
            except OperationalError:
                # This exception clause is for users running MySQL which likes to terminate connections on its own
                # without telling anyone. See bug #927473. However, other dbms can raise it, usually in a
                # non-recoverable way. So we only retry 3 times.
                log.exception('Probably a MySQL issue, "MySQL has gone away"')
                self.session.rollback()
                if try_count >= 2:
                    raise
            except InvalidRequestError:
                self.session.rollback()
                log.exception('Failed to delete {name} records'.format(name=object_class.__name__))
                return False
            except Exception:
                self.session.rollback()
                raise

    def finalise(self):
        """
        VACUUM the database on exit.
        """
        if self.is_dirty and self.db_url.startswith('sqlite'):
            try:
                engine = create_engine(self.db_url)
                engine.connect().execute(text('vacuum'))
            except OperationalError:
                # Just ignore the operational error
                pass

    def close(self):
        """
        Close the session and release the underlying database connection(s).

        This is needed (rather than just discarding the session/manager and relying on the
        garbage collector) because SQLite databases opened via ``init_db()`` use a
        ``StaticPool``, which keeps a single DB-API connection open for the lifetime of the
        engine. Simply closing the session returns that connection to the pool, it does not
        close the underlying file handle, so on some platforms (e.g. Windows) the database
        file cannot be deleted or renamed until the connection is actually closed. Disposing
        of the engine here closes it deterministically, without depending on when (or if) the
        garbage collector runs.
        """
        if self.session:
            engine = self.session.get_bind()
            self.session.close()
            engine.dispose()
            self.session = None
