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
The :mod:`~openlp.plugins.egwlibrary.lib.importer` module imports books into the EGW
library from JSON files.

A file contains either a single book (``{"book": {...}}``) or several
(``{"books": [{...}, ...]}``). A book looks like this::

    {
        "title": "The Desire of Ages",
        "abbreviation": "DA",
        "copyright": "Public domain.",
        "language": "en",
        "aliases": ["Desire of Ages", "desire", "d.a."],
        "chapters": [
            {
                "number": 1,
                "title": "God With Us",
                "paragraphs": [
                    {"page": 19, "text": "..."},
                    {"page": 19, "text": "..."},
                    {"page": 20, "para": 2, "text": "..."}
                ]
            }
        ]
    }

Books without chapters may put ``"paragraphs"`` directly on the book instead of
``"chapters"``; they are stored under a single implicit chapter with number 0.

``page`` is the page the paragraph starts on; when omitted it carries forward from the
previous paragraph. ``para`` (the paragraph's number on its page, the ".2" in
"DA 83.2") is normally computed automatically by counting the paragraphs on each page,
but can be given explicitly when the source numbering differs (for instance when a
paragraph carried over from the previous page counts as paragraph 1).

Importing a book whose abbreviation already exists in the library replaces that book.
"""
import json
import logging

from openlp.core.common.i18n import translate
from openlp.plugins.egwlibrary.lib import normalize_alias
from openlp.plugins.egwlibrary.lib.db import Alias, Book, Chapter, Paragraph

log = logging.getLogger(__name__)


class EGWImportError(Exception):
    """
    Raised when a JSON file cannot be imported. The exception message is user visible.
    """
    pass


def _error(message, **kwargs):
    return EGWImportError(message.format(**kwargs))


def _validate_book(data):
    """
    Check that a book dict has the required structure, raising EGWImportError if not.
    """
    if not isinstance(data, dict):
        raise _error(translate('EGWLibraryPlugin.Importer', 'A book must be a JSON object.'))
    for field in ['title', 'abbreviation']:
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise _error(translate('EGWLibraryPlugin.Importer', 'A book needs a non-empty "{field}" field.'),
                         field=field)
    if 'chapters' in data:
        if not isinstance(data['chapters'], list) or not data['chapters']:
            raise _error(translate('EGWLibraryPlugin.Importer',
                                   '"{title}": "chapters" must be a non-empty list.'), title=data['title'])
        for chapter in data['chapters']:
            if not isinstance(chapter, dict) or not isinstance(chapter.get('paragraphs'), list):
                raise _error(translate('EGWLibraryPlugin.Importer',
                                       '"{title}": every chapter needs a "paragraphs" list.'), title=data['title'])
    elif not isinstance(data.get('paragraphs'), list) or not data['paragraphs']:
        raise _error(translate('EGWLibraryPlugin.Importer',
                               '"{title}": a book needs either "chapters" or "paragraphs".'), title=data['title'])
    # Check for actual text now, before the import replaces an existing book.
    all_paragraphs = []
    for chapter in data.get('chapters', [{'paragraphs': data.get('paragraphs', [])}]):
        all_paragraphs.extend(chapter.get('paragraphs', []))
    if not any((paragraph if isinstance(paragraph, str) else str(paragraph.get('text', '') or '')).strip()
               for paragraph in all_paragraphs if isinstance(paragraph, (str, dict))):
        raise _error(translate('EGWLibraryPlugin.Importer',
                               '"{title}" does not contain any paragraphs.'), title=data['title'])


def import_book(manager, data):
    """
    Import one book dict into the library, replacing any existing book with the same
    abbreviation. The caller is responsible for showing errors to the user.

    :param manager: The EGWLibraryManager to import into.
    :param data: The book dict, as described in the module docstring.
    :return: A tuple of (Book, paragraph_count).
    """
    _validate_book(data)
    title = data['title'].strip()
    abbreviation = data['abbreviation'].strip()
    # Replace an existing book with the same abbreviation
    existing = manager.get_book_by_alias(abbreviation)
    if existing:
        log.info('Replacing existing book "{title}"'.format(title=existing.title))
        manager.delete_book(existing.id)
    book = Book(title=title, abbreviation=abbreviation,
                copyright=str(data.get('copyright', '') or ''),
                language=str(data.get('language', 'en') or 'en'))
    manager.session.add(book)
    manager.session.flush()
    # The title and the abbreviation are aliases too, plus whatever the file defines.
    alias_names = [title, abbreviation] + [alias for alias in data.get('aliases', []) if isinstance(alias, str)]
    seen_keys = set()
    for name in alias_names:
        key = normalize_alias(name)
        if not key or key in seen_keys:
            continue
        if manager.get_object_filtered(Alias, Alias.key == key):
            log.warning('Alias "{name}" already belongs to another book, skipping it'.format(name=name))
            continue
        manager.session.add(Alias(book_id=book.id, key=key, display=name.strip()))
        seen_keys.add(key)
    chapters = data.get('chapters')
    if chapters is None:
        # A book without chapters gets one implicit chapter with number 0
        chapters = [{'number': 0, 'title': '', 'paragraphs': data['paragraphs']}]
    paragraph_count = 0
    current_page = 0
    paras_on_page = {}
    for index, chapter_data in enumerate(chapters):
        chapter = Chapter(book_id=book.id,
                          number=int(chapter_data.get('number', index + 1)),
                          title=str(chapter_data.get('title', '') or ''))
        manager.session.add(chapter)
        manager.session.flush()
        paragraph_number = 0
        for paragraph_data in chapter_data['paragraphs']:
            if isinstance(paragraph_data, str):
                paragraph_data = {'text': paragraph_data}
            paragraph_text = str(paragraph_data.get('text', '') or '').strip()
            if not paragraph_text:
                continue
            paragraph_number += 1
            paragraph_count += 1
            current_page = int(paragraph_data.get('page', current_page) or 0)
            if 'para' in paragraph_data:
                para_on_page = int(paragraph_data['para'])
                paras_on_page[current_page] = para_on_page
            else:
                para_on_page = paras_on_page.get(current_page, 0) + 1
                paras_on_page[current_page] = para_on_page
            manager.session.add(Paragraph(book_id=book.id, chapter_id=chapter.id,
                                          paragraph_number=paragraph_number, page=current_page,
                                          para_on_page=para_on_page, text=paragraph_text))
    manager.session.commit()
    manager.is_dirty = True
    return book, paragraph_count


def import_json_file(manager, file_path):
    """
    Import all the books in a JSON file into the library.

    :param manager: The EGWLibraryManager to import into.
    :param file_path: A Path to the JSON file.
    :return: A list of (Book, paragraph_count) tuples for the imported books.
    """
    try:
        contents = json.loads(file_path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as error:
        raise _error(translate('EGWLibraryPlugin.Importer', 'Unable to read "{name}": {error}'),
                     name=file_path.name, error=error)
    if isinstance(contents, dict) and 'book' in contents:
        books = [contents['book']]
    elif isinstance(contents, dict) and 'books' in contents:
        books = contents['books']
        if not isinstance(books, list):
            raise _error(translate('EGWLibraryPlugin.Importer', '"books" in "{name}" must be a list.'),
                         name=file_path.name)
    elif isinstance(contents, dict):
        # Also accept a bare book object at the top level
        books = [contents]
    else:
        raise _error(translate('EGWLibraryPlugin.Importer', '"{name}" is not an EGW Library book file.'),
                     name=file_path.name)
    return [import_book(manager, book_data) for book_data in books]
