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
The :mod:`upgrade` module provides the database upgrade path for the Alerts
plugin.
"""
import logging

from sqlalchemy import Column
from sqlalchemy.orm import Session
from sqlalchemy.schema import MetaData
from sqlalchemy.sql.expression import text
from sqlalchemy.types import Boolean, DateTime, Integer

from openlp.core.db.upgrades import get_upgrade_op


log = logging.getLogger(__name__)
__version__ = 1


def upgrade_1(session: Session, metadata: MetaData):
    """
    Version 1 upgrade: add the priority and scheduling columns to the alerts
    table. Skipped when the columns already exist (fresh databases are created
    with the full schema).
    """
    op = get_upgrade_op(session)
    metadata.reflect(bind=metadata.bind)
    alerts_table = metadata.tables.get('alerts')
    if alerts_table is None or 'priority' in alerts_table.columns:
        log.debug('Skipping upgrade_1 of the alerts db: already up to date')
        return
    with op.batch_alter_table('alerts') as batch_op:
        batch_op.add_column(Column('priority', Integer, nullable=False, server_default=text('0')))
        batch_op.add_column(Column('scheduled', Boolean, nullable=False, server_default=text('0')))
        batch_op.add_column(Column('enabled', Boolean, nullable=False, server_default=text('1')))
        batch_op.add_column(Column('start_time', DateTime, nullable=True))
        batch_op.add_column(Column('end_time', DateTime, nullable=True))
        batch_op.add_column(Column('repeat_minutes', Integer, nullable=False, server_default=text('0')))
        batch_op.add_column(Column('last_fired', DateTime, nullable=True))
