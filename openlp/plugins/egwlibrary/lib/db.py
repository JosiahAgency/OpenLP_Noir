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
The :mod:`~openlp.plugins.egwlibrary.lib.db` module provides the database and schema
that is the backend for the EGW Library plugin.

The whole library lives in a single database. Every paragraph of every book is indexed
individually, and (on SQLite) mirrored into an FTS5 full text index which is kept in
sync by triggers, so text searches stay fast even for a library of many books.
"""
import logging
import re

from sqlalchemy import Column, ForeignKey, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, joinedload, relationship
from sqlalchemy.sql import and_, or_
from sqlalchemy.types import Integer, Unicode, UnicodeText

from openlp.core.common.i18n import get_natural_key
from openlp.core.db.helpers import init_db
from openlp.core.db.manager import DBManager
from openlp.plugins.egwlibrary.lib import normalize_alias

log = logging.getLogger(__name__)

Base = declarative_base()


class EGWMeta(Base):
    """
    Key/value metadata about the library database.
    """
    __tablename__ = 'metadata'

    key = Column(Unicode(255), primary_key=True, index=True)
    value = Column(Unicode(255))


class Book(Base):
    """
    A book in the library.
    """
    __tablename__ = 'book'

    id = Column(Integer, primary_key=True)
    title = Column(Unicode(255), nullable=False, index=True)
    abbreviation = Column(Unicode(50), nullable=False, index=True)
    copyright = Column(UnicodeText)
    language = Column(Unicode(10), default='en')

    chapters = relationship('Chapter', back_populates='book', order_by='Chapter.number')
    aliases = relationship('Alias', back_populates='book')

    def __lt__(self, other):
        return get_natural_key(self.title) < get_natural_key(other.title)

    def __eq__(self, other):
        return get_natural_key(self.title) == get_natural_key(other.title)

    def __hash__(self):
        return self.id


class Chapter(Base):
    """
    A chapter of a book. Books without chapters get a single implicit chapter with
    number 0 and an empty title, so that queries and display code only ever deal with
    one shape of data.
    """
    __tablename__ = 'chapter'

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey('book.id'), nullable=False, index=True)
    number = Column(Integer, nullable=False)
    title = Column(Unicode(255), default='')

    book = relationship('Book', back_populates='chapters')
    paragraphs = relationship('Paragraph', back_populates='chapter', order_by='Paragraph.paragraph_number')


class Paragraph(Base):
    """
    A single paragraph. ``paragraph_number`` is the sequential number within the
    chapter, while ``page`` and ``para_on_page`` carry the standard EGW citation
    (e.g. "DA 83.2" is page 83, ``para_on_page`` 2). ``book_id`` is denormalised so
    page lookups and searches do not need to join through the chapter table.
    """
    __tablename__ = 'paragraph'

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey('book.id'), nullable=False, index=True)
    chapter_id = Column(Integer, ForeignKey('chapter.id'), nullable=False, index=True)
    paragraph_number = Column(Integer, nullable=False)
    page = Column(Integer, default=0, index=True)
    para_on_page = Column(Integer, default=0)
    text = Column(UnicodeText, nullable=False)

    chapter = relationship('Chapter', back_populates='paragraphs')
    book = relationship('Book')


class Alias(Base):
    """
    A lookup key for a book. The ``key`` column holds the normalised form (lowercase,
    letters and digits only) so "D.A.", "da" and "DA" all resolve through one row;
    ``display`` keeps the human readable form for completers and the UI.
    """
    __tablename__ = 'alias'

    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey('book.id'), nullable=False, index=True)
    key = Column(Unicode(255), nullable=False, unique=True, index=True)
    display = Column(Unicode(255), nullable=False)

    book = relationship('Book', back_populates='aliases')


FTS_SCHEMA = [
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS paragraph_fts USING fts5(
        text, content='paragraph', content_rowid='id', tokenize='unicode61 remove_diacritics 2')
    """,
    """
    CREATE TRIGGER IF NOT EXISTS paragraph_fts_ai AFTER INSERT ON paragraph BEGIN
        INSERT INTO paragraph_fts(rowid, text) VALUES (new.id, new.text);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS paragraph_fts_ad AFTER DELETE ON paragraph BEGIN
        INSERT INTO paragraph_fts(paragraph_fts, rowid, text) VALUES ('delete', old.id, old.text);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS paragraph_fts_au AFTER UPDATE ON paragraph BEGIN
        INSERT INTO paragraph_fts(paragraph_fts, rowid, text) VALUES ('delete', old.id, old.text);
        INSERT INTO paragraph_fts(rowid, text) VALUES (new.id, new.text);
    END
    """
]


def init_schema(url):
    """
    Set up the EGW library database connection and initialise the database schema.

    :param url: The database to setup
    """
    session, metadata = init_db(url, base=Base)
    metadata.create_all(bind=metadata.bind, checkfirst=True)
    if url.startswith('sqlite'):
        try:
            for statement in FTS_SCHEMA:
                session.execute(text(statement))
            session.commit()
        except OperationalError:
            # SQLite without FTS5 support; searches fall back to LIKE queries.
            log.exception('Unable to create the FTS5 index, full text search will use LIKE queries')
            session.rollback()
    return session


class EGWLibraryManager(DBManager):
    """
    The database manager for the EGW library, providing all the queries the media item
    and the importer need.
    """
    def __init__(self, session=None):
        super().__init__('egwlibrary', init_schema, session=session)
        self._has_fts = None

    def has_fts(self):
        """
        Check (once) whether the FTS5 index is available in this database.
        """
        if self._has_fts is None:
            try:
                result = self.session.execute(
                    text("SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'paragraph_fts'"))
                self._has_fts = bool(result.scalar())
            except OperationalError:
                # Not SQLite (no sqlite_master table)
                self._has_fts = False
        return self._has_fts

    def get_books(self):
        """
        Return all books, ordered by title.
        """
        return self.get_all_objects(Book, order_by_ref=Book.title)

    def get_book_by_alias(self, name):
        """
        Look a book up by any of its aliases (this includes its title and abbreviation).

        :param name: The (non-normalised) book name, abbreviation or alias.
        :return: The Book, or None.
        """
        key = normalize_alias(name)
        if not key:
            return None
        alias = self.get_object_filtered(Alias, Alias.key == key)
        return alias.book if alias else None

    def get_book_by_title(self, title):
        """
        Return the book with the given exact title, or None.
        """
        return self.get_object_filtered(Book, Book.title == title)

    def get_chapters(self, book_id):
        """
        Return all chapters of a book, in order.
        """
        return self.get_all_objects(Chapter, Chapter.book_id == book_id, order_by_ref=Chapter.number)

    def get_chapter(self, book_id, number):
        """
        Return a single chapter of a book by its chapter number, or None.
        """
        return self.get_object_filtered(Chapter, and_(Chapter.book_id == book_id, Chapter.number == number))

    def get_paragraphs_for_chapter(self, chapter_id):
        """
        Return all paragraphs of a chapter, in order.
        """
        return self._fetch_paragraphs(
            filters=[Paragraph.chapter_id == chapter_id],
            order_by=[Paragraph.paragraph_number]
        )

    def get_paragraphs_for_pages(self, book_id, from_page, to_page=None):
        """
        Return all paragraphs of a book on the given page or page range, in order.
        """
        if to_page is None or to_page < from_page:
            to_page = from_page
        return self._fetch_paragraphs(
            filters=[Paragraph.book_id == book_id, Paragraph.page >= from_page, Paragraph.page <= to_page],
            order_by=[Paragraph.page, Paragraph.para_on_page]
        )

    def get_paragraphs_for_reference(self, book_id, from_page, from_para, to_page=None, to_para=None):
        """
        Return the paragraphs for a page.paragraph citation or citation range,
        e.g. 83.2 or 83.2-84.1, in order.
        """
        if to_page is None:
            to_page = from_page
        if to_para is None:
            to_para = from_para
        after_start = or_(Paragraph.page > from_page,
                          and_(Paragraph.page == from_page, Paragraph.para_on_page >= from_para))
        before_end = or_(Paragraph.page < to_page,
                         and_(Paragraph.page == to_page, Paragraph.para_on_page <= to_para))
        return self._fetch_paragraphs(
            filters=[Paragraph.book_id == book_id, after_start, before_end],
            order_by=[Paragraph.page, Paragraph.para_on_page]
        )

    def text_search(self, search_text, book_id=None, limit=100):
        """
        Perform a full text search over the paragraphs, using the FTS5 index when it is
        available and falling back to LIKE queries when it is not. All words must match.

        :param search_text: The words to search for.
        :param book_id: Restrict the search to this book. None searches all books.
        :param limit: The maximum number of paragraphs to return.
        :return: The list of matching paragraphs, best matches first (FTS) or in book
            order (LIKE fallback).
        """
        tokens = [token for token in re.split(r'\s+', search_text.strip()) if token]
        if not tokens:
            return []
        if self.has_fts():
            # Quote each token so user input cannot break the FTS5 query syntax.
            match_query = ' '.join('"{token}"'.format(token=token.replace('"', '""')) for token in tokens)
            sql = ('SELECT paragraph.id FROM paragraph '
                   'JOIN paragraph_fts ON paragraph_fts.rowid = paragraph.id '
                   'WHERE paragraph_fts MATCH :match')
            parameters = {'match': match_query, 'limit': limit}
            if book_id is not None:
                sql += ' AND paragraph.book_id = :book_id'
                parameters['book_id'] = book_id
            sql += ' ORDER BY rank LIMIT :limit'
            try:
                paragraph_ids = [row[0] for row in self.session.execute(text(sql), parameters)]
            except OperationalError:
                log.exception('FTS search failed, falling back to a LIKE search')
                self.session.rollback()
                return self._like_search(tokens, book_id, limit)
            if not paragraph_ids:
                return []
            paragraphs = {paragraph.id: paragraph
                          for paragraph in self._fetch_paragraphs(filters=[Paragraph.id.in_(paragraph_ids)])}
            return [paragraphs[paragraph_id] for paragraph_id in paragraph_ids if paragraph_id in paragraphs]
        return self._like_search(tokens, book_id, limit)

    def _like_search(self, tokens, book_id, limit):
        """
        The LIKE based fallback for :func:`text_search`.
        """
        filters = [Paragraph.text.like('%{token}%'.format(token=token)) for token in tokens]
        if book_id is not None:
            filters.append(Paragraph.book_id == book_id)
        return self.session.query(Paragraph) \
            .options(joinedload(Paragraph.book), joinedload(Paragraph.chapter)) \
            .filter(*filters) \
            .order_by(Paragraph.book_id, Paragraph.page, Paragraph.para_on_page,
                      Paragraph.chapter_id, Paragraph.paragraph_number) \
            .limit(limit) \
            .all()

    def _fetch_paragraphs(self, *, filters=None, order_by=None):
        """
        Return paragraphs with related book/chapter preloaded to avoid per-row lookups.
        """
        query = self.session.query(Paragraph).options(joinedload(Paragraph.book), joinedload(Paragraph.chapter))
        for db_filter in filters or []:
            query = query.filter(db_filter)
        if order_by:
            query = query.order_by(*order_by)
        return query.all()

    def delete_book(self, book_id):
        """
        Delete a book and everything that belongs to it from the library.
        """
        try:
            # Deletes run through SQL so the SQLite triggers keep the FTS index in sync.
            self.session.query(Paragraph).filter(Paragraph.book_id == book_id).delete(synchronize_session=False)
            self.session.query(Chapter).filter(Chapter.book_id == book_id).delete(synchronize_session=False)
            self.session.query(Alias).filter(Alias.book_id == book_id).delete(synchronize_session=False)
            self.session.query(Book).filter(Book.id == book_id).delete(synchronize_session=False)
            self.session.commit()
            # The bulk deletes bypass the session, so drop any stale cached objects
            self.session.expunge_all()
            self.is_dirty = True
            return True
        except OperationalError:
            log.exception('Failed to delete book {book_id}'.format(book_id=book_id))
            self.session.rollback()
            return False
