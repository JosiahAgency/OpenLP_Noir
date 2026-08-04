# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from PySide6 import QtGui

from openlp.plugins.songs.forms.duplicatesongremovalform import (
    _blend_colors,
    build_preview_pane_style,
    build_duplicate_song_groups,
    generate_candidate_index_pairs,
    select_keeper_song
)


class SongStub:
    def __init__(self, song_id, title, alternate_title='', search_lyrics='', last_modified=None):
        self.id = song_id
        self.title = title
        self.alternate_title = alternate_title
        self.search_title = f'{title}@{alternate_title}'
        self.search_lyrics = search_lyrics
        self.last_modified = last_modified
        self.authors = []


def test_generate_candidate_index_pairs_uses_blocking_keys():
    songs = [
        SongStub(1, 'Amazing Grace', search_lyrics='line one line two line three line four line five'),
        SongStub(2, 'Amazing Grace', search_lyrics='line one line two line three line four line five'),
        SongStub(3, 'Blessed Assurance', search_lyrics='another lyric set with enough characters 1234567890'),
    ]

    pairs = generate_candidate_index_pairs(songs)

    assert (0, 1) in pairs
    assert (0, 2) not in pairs
    assert (1, 2) not in pairs


def test_build_duplicate_song_groups_merges_connected_matches():
    base_time = datetime.now()
    songs = [
        SongStub(1, 'Song A', last_modified=base_time - timedelta(days=3)),
        SongStub(2, 'Song B', last_modified=base_time - timedelta(days=2)),
        SongStub(3, 'Song C', last_modified=base_time - timedelta(days=1)),
    ]

    groups = build_duplicate_song_groups(songs, [(0, 1), (1, 2)])

    assert len(groups) == 1
    assert {song.id for song in groups[0]} == {1, 2, 3}
    assert groups[0][0].id == 3


def test_select_keeper_song_picks_latest_last_modified():
    base_time = datetime.now()
    group = [
        SongStub(1, 'Old', last_modified=base_time - timedelta(days=2)),
        SongStub(2, 'New', last_modified=base_time),
        SongStub(3, 'Mid', last_modified=base_time - timedelta(days=1)),
    ]

    keeper = select_keeper_song(group)

    assert keeper.id == 2


def test_blend_colors_returns_expected_intermediate_rgb():
    blended = _blend_colors(QtGui.QColor(0, 0, 0), QtGui.QColor(200, 100, 50), 0.5)
    assert blended.red() == 100
    assert blended.green() == 50
    assert blended.blue() == 25


def test_build_preview_pane_style_has_distinct_bg_and_text():
    palette = QtGui.QPalette()
    style = build_preview_pane_style(True, palette)

    assert 'background-color:' in style
    assert 'color:' in style
