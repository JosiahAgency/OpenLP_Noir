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
This module contains tests for the upgrade submodule of the Alerts plugin,
in particular upgrade_2 which gives each alert its own name/style.
"""
import json

from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, Table, UnicodeText, create_engine, insert, select

from openlp.core.db.upgrades import upgrade_db
from openlp.plugins.alerts.lib import upgrade
from openlp.plugins.alerts.lib.presets import DEFAULT_PRESETS


def _make_v1_db(tmp_path):
    """A v1-shape alerts database (post upgrade_1, pre upgrade_2) with two rows."""
    db_url = 'sqlite:///' + str(tmp_path / 'alerts.sqlite')
    engine = create_engine(db_url)
    metadata = MetaData()
    alerts_table = Table(
        'alerts', metadata,
        Column('id', Integer, primary_key=True),
        Column('text', UnicodeText, nullable=False),
        Column('priority', Integer, nullable=False, server_default='0'),
        Column('scheduled', Boolean, nullable=False, server_default='0'),
        Column('enabled', Boolean, nullable=False, server_default='1'),
        Column('start_time', DateTime, nullable=True),
        Column('end_time', DateTime, nullable=True),
        Column('repeat_minutes', Integer, nullable=False, server_default='0'),
        Column('last_fired', DateTime, nullable=True),
    )
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(insert(alerts_table).values(
            text='Info alert', priority=0, scheduled=False, enabled=True, repeat_minutes=0))
        conn.execute(insert(alerts_table).values(
            text='Critical alert', priority=3, scheduled=False, enabled=True, repeat_minutes=0))
    engine.dispose()
    return db_url


def _read_alerts_by_text(db_url):
    engine = create_engine(db_url)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    alerts_table = metadata.tables['alerts']
    with engine.connect() as conn:
        rows = {row.text: row for row in conn.execute(select(alerts_table)).all()}
    engine.dispose()
    return rows


def test_upgrade_2_backfills_style_from_priority(tmp_path):
    """Existing rows get a style snapshot matching their priority's factory preset"""
    # GIVEN: A v1-shape alerts database with an Info and a Critical alert
    db_url = _make_v1_db(tmp_path)

    # WHEN: The database is upgraded
    version, target_version = upgrade_db(db_url, upgrade)

    # THEN: The database reaches the module's target version
    assert version == target_version == upgrade.__version__

    # AND: Each row's style matches its own priority's factory preset, and name is unset
    rows = _read_alerts_by_text(db_url)
    assert json.loads(rows['Info alert'].style) == DEFAULT_PRESETS['info']
    assert json.loads(rows['Critical alert'].style) == DEFAULT_PRESETS['critical']
    assert rows['Info alert'].name is None
    assert rows['Critical alert'].name is None


def test_upgrade_2_is_idempotent(tmp_path):
    """Running the upgrade path twice does not error or clobber the data"""
    # GIVEN: A v1-shape alerts database, already upgraded once
    db_url = _make_v1_db(tmp_path)
    upgrade_db(db_url, upgrade)
    rows_after_first = _read_alerts_by_text(db_url)

    # WHEN: The upgrade path runs again
    version, target_version = upgrade_db(db_url, upgrade)

    # THEN: It's a no-op — same version, same data
    assert version == target_version == upgrade.__version__
    rows_after_second = _read_alerts_by_text(db_url)
    assert rows_after_second['Info alert'].style == rows_after_first['Info alert'].style
    assert rows_after_second['Critical alert'].style == rows_after_first['Critical alert'].style
