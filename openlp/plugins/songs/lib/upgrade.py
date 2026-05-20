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
The :mod:`upgrade` module provides a way for the database and schema that is the
backend for the Songs plugin
"""
import json
import logging
from pathlib import Path

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.schema import MetaData
from sqlalchemy.orm import Session
from sqlalchemy.types import Boolean, DateTime, Integer, Unicode
from sqlalchemy.sql.expression import false, func, null, text, select, update

from openlp.core.common import sha256_file_hash
from openlp.core.common.applocation import AppLocation
from openlp.core.common.json import OpenLPJSONEncoder, OpenLPJSONDecoder
from openlp.core.db.types import PathType
from openlp.core.db.upgrades import get_upgrade_op


log = logging.getLogger(__name__)
__version__ = 9


# TODO: When removing an upgrade path the ftw-data needs updating to the minimum supported version
def upgrade_1(session: Session, metadata: MetaData):
    """
    Version 1 upgrade.

    This upgrade removes the many-to-many relationship between songs and
    media_files and replaces it with a one-to-many, which is far more
    representative of the real relationship between the two entities.

    In order to facilitate this one-to-many relationship, a song_id column is
    added to the media_files table, and a weight column so that the media
    files can be ordered.

    :param session:
    :param metadata:
    """
    op = get_upgrade_op(session)
    metadata.reflect(bind=metadata.bind)
    if 'media_files_songs' in [t.name for t in metadata.tables.values()]:
        op.drop_table('media_files_songs')
        with op.batch_alter_table('media_files') as batch_op:
            batch_op.add_column(Column('song_id', Integer, server_default=null()))
            batch_op.add_column(Column('weight', Integer, server_default=text('0')))
            batch_op.create_foreign_key('fk_media_files_song_id', 'media_files', 'songs', ['song_id', 'id'])
    else:
        log.warning('Skipping upgrade_1 step of upgrading the song db')


def upgrade_2(session: Session, metadata: MetaData):
    """
    Version 2 upgrade.

    This upgrade adds a create_date and last_modified date to the songs table
    """
    op = get_upgrade_op(session)
    songs_table = Table('songs', metadata, autoload_with=metadata.bind)
    if 'create_date' not in [col.name for col in songs_table.c.values()]:
        op.add_column('songs', Column('create_date', DateTime, default=func.now()))
        op.add_column('songs', Column('last_modified', DateTime, default=func.now()))
    else:
        log.warning('Skipping upgrade_2 step of upgrading the song db')


def upgrade_3(session: Session, metadata: MetaData):
    """
    Version 3 upgrade.

    This upgrade adds a temporary song flag to the songs table
    """
    op = get_upgrade_op(session)
    songs_table = Table('songs', metadata, autoload_with=metadata.bind)
    if 'temporary' not in [col.name for col in songs_table.c.values()]:
        if metadata.bind.url.get_dialect().name == 'sqlite':
            op.add_column('songs', Column('temporary', Boolean(create_constraint=False), server_default=false()))
        else:
            op.add_column('songs', Column('temporary', Boolean, server_default=false()))
    else:
        log.warning('Skipping upgrade_3 step of upgrading the song db')


def upgrade_4(session: Session, metadata: MetaData):
    """
    Version 4 upgrade.

    This upgrade adds a column for author type to the authors_songs table
    """
    # This is now empty due to a bug in the upgrade
    pass


def upgrade_5(session: Session, metadata: MetaData):
    """
    Version 5 upgrade.

    This upgrade adds support for multiple songbooks
    """
    # This is now empty due to a bug in the upgrade
    pass


def upgrade_6(session, metadata):
    """
    Version 6 upgrade

    This version corrects the errors in upgrades 4 and 5
    """
    op = get_upgrade_op(session)
    metadata.reflect(bind=metadata.bind)
    # Move upgrade 4 to here and correct it (authors_songs table, not songs table)
    authors_songs = Table('authors_songs', metadata, autoload_with=metadata.bind)
    if 'author_type' not in [col.name for col in authors_songs.c.values()]:
        # Since SQLite doesn't support changing the primary key of a table, we need to recreate the table
        # and copy the old values
        op.create_table(
            'authors_songs_tmp',
            Column('author_id', Integer, ForeignKey('authors.id'), primary_key=True),
            Column('song_id', Integer, ForeignKey('songs.id'), primary_key=True),
            Column('author_type', Unicode(255), primary_key=True, nullable=False, server_default=text('""'))
        )
        op.execute('INSERT INTO authors_songs_tmp SELECT author_id, song_id, "" FROM authors_songs')
        op.drop_table('authors_songs')
        op.rename_table('authors_songs_tmp', 'authors_songs')
    # Move upgrade 5 here to correct it
    if 'songs_songbooks' not in [t.name for t in metadata.tables.values()]:
        # Create the mapping table (songs <-> songbooks)
        op.create_table(
            'songs_songbooks',
            Column('songbook_id', Integer, ForeignKey('song_books.id'), primary_key=True),
            Column('song_id', Integer, ForeignKey('songs.id'), primary_key=True),
            Column('entry', Unicode(255), primary_key=True, nullable=False)
        )

        # Migrate old data
        op.execute('INSERT INTO songs_songbooks SELECT song_book_id, id, song_number FROM songs\
                    WHERE song_book_id IS NOT NULL AND song_number IS NOT NULL AND song_book_id <> 0')

        # Drop old columns
        with op.batch_alter_table('songs') as batch_op:
            # batch_op.drop_constraint('song_book_id', 'foreignkey')
            batch_op.drop_column('song_book_id')
            batch_op.drop_column('song_number')
    # Finally, clean up our mess in people's databases
    op.execute('DELETE FROM songs_songbooks WHERE songbook_id = 0')


def upgrade_7(session, metadata):
    """
    Version 7 upgrade - Move file path from old db to JSON encoded path to new db. Upgrade added in 2.5 dev
    """
    log.debug('Starting upgrade_7 for file_path to JSON')
    metadata.clear()
    media_files = Table('media_files', metadata, autoload_with=metadata.bind)
    if 'file_path' not in [col.name for col in media_files.c.values()]:
        op = get_upgrade_op(session)
        conn = op.get_bind()
        results = conn.execute(select(media_files))
        data_path = AppLocation.get_data_path()
        # Add the column after doing the select, otherwise the records from the select are incomplete
        op.add_column('media_files', Column('file_path', PathType()))
        media_files.append_column(Column('file_path', PathType()))
        # Now update the table and set the new column
        for row in results.all():
            file_path_json = json.dumps(Path(row.file_name), cls=OpenLPJSONEncoder, base_path=data_path)
            conn.execute(update(media_files).where(media_files.c.id == row.id).values(file_path=file_path_json))
        # Drop old columns
        with op.batch_alter_table('media_files') as batch_op:
            if metadata.bind.url.get_dialect().name != 'sqlite':
                for fk in media_files.foreign_keys:
                    batch_op.drop_constraint(fk.name, 'foreignkey')
            batch_op.drop_column('file_name')


def upgrade_8(session, metadata):
    """
    Version 8 upgrade - add sha256 hash to media
    """
    log.debug('Starting upgrade_8 for adding sha256 hashes')
    metadata.clear()
    media_files = Table('media_files', metadata, autoload_with=metadata.bind)
    if 'file_hash' not in [col.name for col in media_files.c.values()]:
        op = get_upgrade_op(session)
        conn = op.get_bind()
        results = conn.execute(select(media_files))
        data_path = AppLocation.get_data_path()
        # Add the column after doing the select, otherwise the records from the select are incomplete
        op.add_column('media_files', Column('file_hash', Unicode(128)))
        media_files.append_column(Column('file_hash', Unicode(128)))
        # Now update the table and set the new column
        for row in results.all():
            file_path = json.loads(row.file_path, cls=OpenLPJSONDecoder)
            full_file_path = data_path / file_path
            if full_file_path.exists():
                hash_ = sha256_file_hash(full_file_path)
            else:
                log.warning('{audio} does not exists, so no sha256 hash added.'.format(audio=str(file_path)))
                # set a fake "hash" to allow for the upgrade to go through. The image will be marked as invalid
                hash_ = 'NONE'
            conn.execute(update(media_files).where(media_files.c.id == row.id).values(file_hash=hash_))


def upgrade_9(session: Session, metadata: MetaData):
    """
    Version 9 upgrade - add an "is_favourite" column to each song
    """
    log.debug('Starting upgrade_9 for adding is_favourite column')
    metadata.clear()
    songs_table = Table('songs', metadata, autoload_with=metadata.bind)
    if 'is_favourite' not in [col.name for col in songs_table.c.values()]:
        op = get_upgrade_op(session)
        op.add_column('songs', Column('is_favourite', Boolean, default=False))
        songs_table.append_column(Column('is_favourite', Boolean, default=False))
