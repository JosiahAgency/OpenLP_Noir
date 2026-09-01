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
:mod: openlp.core.ui.projector.manager` module

Provides the functions for the display/control of Projectors.
"""
import logging
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.common.mixins import LogMixin, RegistryProperties
from openlp.core.common.registry import Registry, RegistryBase
from openlp.core.lib.ui import create_widget_action
from openlp.core.projectors import DialogSourceStyle
from openlp.core.projectors.constants import E_AUTHENTICATION, E_ERROR, E_NETWORK, E_NOT_CONNECTED, E_SOCKET_TIMEOUT, \
    E_UNKNOWN_SOCKET_ERROR, PJLINK_PORT, QSOCKET_STATE, S_CONNECTED, S_CONNECTING, S_COOLDOWN, S_INITIALIZE, \
    S_NOT_CONNECTED, S_OFF, S_ON, S_STANDBY, S_WARMUP, STATUS_CODE, STATUS_MSG

from openlp.core.projectors.db import ProjectorDB
from openlp.core.projectors.editform import ProjectorEditForm
from openlp.core.projectors.pjlink import PJLink, PJLinkUDP
from openlp.core.projectors.sourceselectform import SourceSelectSingle, SourceSelectTabs
from openlp.core.ui.icons import UiIcons
from openlp.core.widgets.toolbar import OpenLPToolbar

log = logging.getLogger(__name__)
log.debug('projectormanager loaded')


class UiProjectorManager(object):
    """
    UI part of the Projector Manager
    """
    def setup_ui(self, widget):
        """
        Define the UI

        :param widget: The screen object the dialog is to be attached to.
        """
        log.debug('setup_ui()')
        # Create ProjectorManager box
        self.layout = QtWidgets.QVBoxLayout(widget)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setObjectName('layout')
        # Add one selection toolbar
        self.one_toolbar = OpenLPToolbar(widget)
        self.one_toolbar.add_toolbar_action('new_projector',
                                            text=translate('OpenLP.ProjectorManager', 'Add Projector'),
                                            icon=UiIcons().new,
                                            tooltip=translate('OpenLP.ProjectorManager', 'Add a new projector.'),
                                            triggers=self.on_add_projector)
        # Show edit/delete when projector not connected
        self.one_toolbar.add_toolbar_action('edit_projector',
                                            text=translate('OpenLP.ProjectorManager', 'Edit Projector'),
                                            icon=UiIcons().edit,
                                            tooltip=translate('OpenLP.ProjectorManager', 'Edit selected projector.'),
                                            triggers=self.on_edit_projector)
        self.one_toolbar.add_toolbar_action('delete_projector',
                                            text=translate('OpenLP.ProjectorManager', 'Delete Projector'),
                                            icon=UiIcons().delete,
                                            tooltip=translate('OpenLP.ProjectorManager', 'Delete selected projector.'),
                                            triggers=self.on_delete_projector)
        # Show source/view when projector connected
        self.one_toolbar.add_toolbar_action('source_view_projector',
                                            text=translate('OpenLP.ProjectorManager', 'Select Input Source'),
                                            icon=UiIcons().projector_hdmi,
                                            tooltip=translate('OpenLP.ProjectorManager',
                                                              'Choose input source on selected projector.'),
                                            triggers=self.on_select_input)
        self.one_toolbar.add_toolbar_action('view_projector',
                                            text=translate('OpenLP.ProjectorManager', 'View Projector'),
                                            icon=UiIcons().info,
                                            tooltip=translate('OpenLP.ProjectorManager',
                                                              'View selected projector information.'),
                                            triggers=self.on_status_projector)
        self.one_toolbar.addSeparator()
        self.one_toolbar.add_toolbar_action('connect_projector',
                                            text=translate('OpenLP.ProjectorManager',
                                                           'Connect to selected projector.'),
                                            icon=UiIcons().projector_select_connect,
                                            tooltip=translate('OpenLP.ProjectorManager',
                                                              'Connect to selected projector.'),
                                            triggers=self.on_connect_projector)
        self.one_toolbar.add_toolbar_action('connect_projector_multiple',
                                            text=translate('OpenLP.ProjectorManager',
                                                           'Connect to selected projectors'),
                                            icon=UiIcons().projector_connect,
                                            tooltip=translate('OpenLP.ProjectorManager',
                                                              'Connect to selected projectors.'),
                                            triggers=self.on_connect_projector)
        self.one_toolbar.add_toolbar_action('disconnect_projector',
                                            text=translate('OpenLP.ProjectorManager',
                                                           'Disconnect from selected projectors'),
                                            icon=UiIcons().projector_select_disconnect,
                                            tooltip=translate('OpenLP.ProjectorManager',
                                                              'Disconnect from selected projector.'),
                                            triggers=self.on_disconnect_projector)
        self.one_toolbar.add_toolbar_action('disconnect_projector_multiple',
                                            text=translate('OpenLP.ProjectorManager',
                                                           'Disconnect from selected projector'),
                                            icon=UiIcons().projector_disconnect,
                                            tooltip=translate('OpenLP.ProjectorManager',
                                                              'Disconnect from selected projectors.'),
                                            triggers=self.on_disconnect_projector)
        self.one_toolbar.addSeparator()
        self.one_toolbar.add_toolbar_action('poweron_projector',
                                            text=translate('OpenLP.ProjectorManager',
                                                           'Power on selected projector'),
                                            icon=UiIcons().projector_power_on,
                                            tooltip=translate('OpenLP.ProjectorManager',
                                                              'Power on selected projector.'),
                                            triggers=self.on_poweron_projector)
        self.one_toolbar.add_toolbar_action('poweron_projector_multiple',
                                            text=translate('OpenLP.ProjectorManager',
                                                           'Power on selected projector'),
                                            icon=UiIcons().projector_on,
                                            tooltip=translate('OpenLP.ProjectorManager',
                                                              'Power on selected projectors.'),
                                            triggers=self.on_poweron_projector)
        self.one_toolbar.add_toolbar_action('poweroff_projector',
                                            text=translate('OpenLP.ProjectorManager', 'Standby selected projector'),
                                            icon=UiIcons().projector_power_off,
                                            tooltip=translate('OpenLP.ProjectorManager',
                                                              'Put selected projector in standby.'),
                                            triggers=self.on_poweroff_projector)
        self.one_toolbar.add_toolbar_action('poweroff_projector_multiple',
                                            text=translate('OpenLP.ProjectorManager', 'Standby selected projector'),
                                            icon=UiIcons().projector_off,
                                            tooltip=translate('OpenLP.ProjectorManager',
                                                              'Put selected projectors in standby.'),
                                            triggers=self.on_poweroff_projector)
        self.one_toolbar.addSeparator()
        self.one_toolbar.add_toolbar_action('blank_projector',
                                            text=translate('OpenLP.ProjectorManager',
                                                           'Blank selected projector screen'),
                                            icon=UiIcons().blank,
                                            tooltip=translate('OpenLP.ProjectorManager',
                                                              'Blank selected projector screen'),
                                            triggers=self.on_blank_projector)
        self.one_toolbar.add_toolbar_action('blank_projector_multiple',
                                            text=translate('OpenLP.ProjectorManager',
                                                           'Blank selected projectors screen'),
                                            icon=UiIcons().blank,
                                            tooltip=translate('OpenLP.ProjectorManager',
                                                              'Blank selected projectors screen.'),
                                            triggers=self.on_blank_projector)
        self.one_toolbar.add_toolbar_action('show_projector',
                                            text=translate('OpenLP.ProjectorManager',
                                                           'Show selected projector screen'),
                                            icon=UiIcons().desktop,
                                            tooltip=translate('OpenLP.ProjectorManager',
                                                              'Show selected projector screen.'),
                                            triggers=self.on_show_projector)
        self.one_toolbar.add_toolbar_action('show_projector_multiple',
                                            text=translate('OpenLP.ProjectorManager',
                                                           'Show selected projector screen'),
                                            icon=UiIcons().desktop,
                                            tooltip=translate('OpenLP.ProjectorManager',
                                                              'Show selected projectors screen.'),
                                            triggers=self.on_show_projector)
        self.layout.addWidget(self.one_toolbar)
        self.projector_one_widget = QtWidgets.QWidgetAction(self.one_toolbar)
        self.projector_one_widget.setObjectName('projector_one_toolbar_widget')
        # Create projector manager list
        self.projector_list_widget = QtWidgets.QListWidget(widget)
        self.projector_list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.projector_list_widget.setAlternatingRowColors(True)
        self.projector_list_widget.setIconSize(QtCore.QSize(90, 50))
        self.projector_list_widget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.projector_list_widget.setObjectName('projector_list_widget')
        self.layout.addWidget(self.projector_list_widget)
        self.projector_list_widget.customContextMenuRequested.connect(self.context_menu)
        self.projector_list_widget.itemDoubleClicked.connect(self.on_doubleclick_item)
        # Build the context menu
        self.menu = QtWidgets.QMenu()
        self.status_action = create_widget_action(self.menu,
                                                  text=translate('OpenLP.ProjectorManager',
                                                                 '&View Projector Information'),
                                                  icon=UiIcons().info,
                                                  triggers=self.on_status_projector)
        self.edit_action = create_widget_action(self.menu,
                                                text=translate('OpenLP.ProjectorManager',
                                                               '&Edit Projector'),
                                                icon=UiIcons().edit,
                                                triggers=self.on_edit_projector)
        self.view_action = create_widget_action(self.menu,
                                                text=translate('OpenLP.ProjectorManager',
                                                               '&View Projector'),
                                                icon=UiIcons().edit,
                                                triggers=self.on_view_projector)
        self.menu.addSeparator()
        self.connect_action = create_widget_action(self.menu,
                                                   text=translate('OpenLP.ProjectorManager',
                                                                  '&Connect Projector'),
                                                   icon=UiIcons().projector_connect,
                                                   triggers=self.on_connect_projector)
        self.disconnect_action = create_widget_action(self.menu,
                                                      text=translate('OpenLP.ProjectorManager',
                                                                     'D&isconnect Projector'),
                                                      icon=UiIcons().projector_off,
                                                      triggers=self.on_disconnect_projector)
        self.menu.addSeparator()
        self.poweron_action = create_widget_action(self.menu,
                                                   text=translate('OpenLP.ProjectorManager',
                                                                  'Power &On Projector'),
                                                   icon=UiIcons().projector_on,
                                                   triggers=self.on_poweron_projector)
        self.poweroff_action = create_widget_action(self.menu,
                                                    text=translate('OpenLP.ProjectorManager',
                                                                   'Power O&ff Projector'),
                                                    icon=UiIcons().projector_off,
                                                    triggers=self.on_poweroff_projector)
        self.menu.addSeparator()
        self.select_input_action = create_widget_action(self.menu,
                                                        text=translate('OpenLP.ProjectorManager',
                                                                       'Select &Input'),
                                                        icon=UiIcons().projector_hdmi,
                                                        triggers=self.on_select_input)
        self.edit_input_action = create_widget_action(self.menu,
                                                      text=translate('OpenLP.ProjectorManager',
                                                                     'Edit Input Source'),
                                                      icon=UiIcons().edit,
                                                      triggers=self.on_edit_input)
        self.blank_action = create_widget_action(self.menu,
                                                 text=translate('OpenLP.ProjectorManager',
                                                                '&Blank Projector Screen'),
                                                 icon=UiIcons().blank,
                                                 triggers=self.on_blank_projector)
        self.show_action = create_widget_action(self.menu,
                                                text=translate('OpenLP.ProjectorManager',
                                                               '&Show Projector Screen'),
                                                icon=UiIcons().projector,
                                                triggers=self.on_show_projector)
        self.view_action = create_widget_action(self.menu,
                                                text=translate('OpenLP.ProjectorManager',
                                                               '&Show Projector Screen'),
                                                icon=UiIcons().projector,
                                                triggers=self.on_view_projector)
        self.menu.addSeparator()
        self.delete_action = create_widget_action(self.menu,
                                                  text=translate('OpenLP.ProjectorManager',
                                                                 '&Delete Projector'),
                                                  icon=UiIcons().delete,
                                                  triggers=self.on_delete_projector)
        self.update_icons()


class ProjectorManager(QtWidgets.QWidget, RegistryBase, UiProjectorManager, LogMixin, RegistryProperties):
    """
    Manage the projectors.
    """
    def __init__(self, parent=None, projectordb=None):
        """
        Basic initialization.

        :param parent: Who I belong to.
        :param projectordb: Database session inherited from superclass.
        """
        log.debug('__init__()')
        super(ProjectorManager, self).__init__(parent)
        self.settings_section = 'projector'
        self.projectordb = projectordb
        self.projector_list = []
        self.source_select_form = None
        # Dictionary of PJLinkUDP objects to listen for UDP broadcasts from PJLink 2+ projectors.
        # Key is port number
        self.pjlink_udp = {}
        # Dict for matching projector status to display icon
        self.status_icons = {
            S_NOT_CONNECTED: UiIcons().projector_disconnect,
            S_CONNECTING: UiIcons().projector_connect,
            S_CONNECTED: UiIcons().projector_off,
            S_OFF: UiIcons().projector_off,
            S_INITIALIZE: UiIcons().projector_on,
            S_STANDBY: UiIcons().projector_off,
            S_WARMUP: UiIcons().projector_warmup,
            S_ON: UiIcons().projector_on,
            S_COOLDOWN: UiIcons().projector_cooldown,
            E_ERROR: UiIcons().projector_error,
            E_NETWORK: UiIcons().error,
            E_SOCKET_TIMEOUT: UiIcons().authentication,
            E_AUTHENTICATION: UiIcons().authentication,
            E_UNKNOWN_SOCKET_ERROR: UiIcons().error,
            E_NOT_CONNECTED: UiIcons().projector_disconnect
        }
        # update_status debouncer
        self.update_status_timer = QtCore.QTimer(self)
        self.update_status_timer.setInterval(100)
        self.update_status_timer.timeout.connect(self._try_update_status)
        self.is_updating_status = False
        self.ip_status_to_update = (None, None, None)

    def bootstrap_initialise(self):
        """
        Pre-initialize setups.
        """
        self.setup_ui(self)
        if self.projectordb is None:
            # Work around for testing creating a ~/.openlp.data.projector.projector.sql file
            log.debug('Creating new ProjectorDB() instance')
            self.projectordb = ProjectorDB()
        else:
            log.debug('Using existing ProjectorDB() instance')
        self.get_settings()

    def bootstrap_post_set_up(self):
        """
        Post-initialize setups.
        """
        # Set 1.5 second delay before loading all projectors
        if self.autostart:
            log.debug('Delaying 1.5 seconds before loading all projectors')
            QtCore.QTimer().singleShot(1500, self._load_projectors)
        else:
            log.debug('Loading all projectors')
            self._load_projectors()
        self.projector_form = ProjectorEditForm(self, projectordb=self.projectordb)
        self.projector_form.updateProjectors.connect(self._load_projectors)
        self.projector_list_widget.itemSelectionChanged.connect(self.update_icons)

    def udp_listen_add(self, port=PJLINK_PORT):
        """
        Add UDP broadcast listener

        NOTE: Check if PJLinkUDP port needs to be started when adding
        """
        if port in self.pjlink_udp:
            log.warning(f'UDP Listener for port {port} already added - skipping')
        else:
            log.debug(f'Adding UDP listener on port {port}')
            self.pjlink_udp[port] = PJLinkUDP(port=port)
            Registry().execute('udp_broadcast_add', port=port, callback=self.pjlink_udp[port].check_settings)

    def udp_listen_delete(self, port):
        """
        Remove a UDP broadcast listener

        NOTE: Check if PJLinkUDP port needs to be closed/stopped when deleting
        """
        log.debug(f'Checking for UDP port {port} listener deletion')
        if port not in self.pjlink_udp:
            log.warning(f'UDP listener for port {port} not there - skipping delete')
            return
        keep_port = False
        for item in self.projector_list:
            if port == item.link.port:
                keep_port = True
        if keep_port:
            log.warning(f'UDP listener for port {port} needed for other projectors - skipping delete')
            return
        Registry().execute('udp_broadcast_remove', port=port)
        del self.pjlink_udp[port]
        log.debug(f'UDP listener for port {port} deleted')

    def get_settings(self):
        """
        Retrieve the saved settings
        """
        log.debug('Updating ProjectorManager settings')
        self.autostart = self.settings.value('projector/connect on start')
        self.poll_time = self.settings.value('projector/poll time')
        self.socket_timeout = self.settings.value('projector/socket timeout')
        self.source_select_dialog_type = self.settings.value('projector/source dialog type')

    def context_menu(self, point):
        """
        Build the Right Click Context menu and set state.

        :param point: The position of the mouse so the correct item can be found.
        """
        # QListWidgetItem to build menu for.
        item = self.projector_list_widget.itemAt(point)
        if item is None:
            return
        real_projector = item.data(QtCore.Qt.ItemDataRole.UserRole)
        projector_name = str(item.text())
        visible = real_projector.link.status_connect >= S_CONNECTED
        log.debug(f'({projector_name}) Building menu - visible = {visible}')
        self.delete_action.setVisible(True)
        self.edit_action.setVisible(True)
        self.view_action.setVisible(True)
        self.connect_action.setVisible(not visible)
        self.disconnect_action.setVisible(visible)
        self.status_action.setVisible(visible)
        self.select_input_action.setVisible(visible and real_projector.link.power == S_ON)
        self.edit_input_action.setVisible(visible and real_projector.link.power == S_ON)
        self.poweron_action.setVisible(visible and real_projector.link.power == S_STANDBY)
        self.poweroff_action.setVisible(visible and real_projector.link.power == S_ON)
        self.blank_action.setVisible(visible and real_projector.link.power == S_ON and
                                     not real_projector.link.shutter)
        self.show_action.setVisible(visible and real_projector.link.power == S_ON and
                                    real_projector.link.shutter)
        self.menu.projector = real_projector
        self.menu.exec(self.projector_list_widget.mapToGlobal(point))

    def on_edit_input(self, opt=None):
        self.on_select_input(opt=opt, edit=True)

    def on_select_input(self, opt=None, edit=False):
        """
        Builds menu for 'Select Input' option, then calls the selected projector
        item to change input source.

        :param opt: Needed by PySide6
        """
        self.get_settings()  # In case the dialog interface setting was changed
        list_item = self.projector_list_widget.item(self.projector_list_widget.currentRow())
        projector = list_item.data(QtCore.Qt.ItemDataRole.UserRole)
        # QTabwidget for source select
        source = 100
        while source > 99:
            if self.source_select_dialog_type == DialogSourceStyle.Tabbed:
                source_select_form = SourceSelectTabs(parent=self,
                                                      projectordb=self.projectordb,
                                                      edit=edit)
            else:
                source_select_form = SourceSelectSingle(parent=self,
                                                        projectordb=self.projectordb,
                                                        edit=edit)
            source = source_select_form.exec(projector.link)
        log.debug(f'({projector.link.ip}) source_select_form() returned {source}')
        if source is not None and source > 0:
            projector.link.set_input_source(str(source))
        return

    def on_add_projector(self, opt=None):
        """
        Calls edit dialog to add a new projector to the database

        :param opt: Needed by PySide6
        """
        self.projector_form.exec()

    def on_blank_projector(self, item=None, opt=None):
        """
        Calls projector(s) thread to send blank screen command

        :param item: Optional ProjectorItem() instance in case of direct call
        :param opt: (Deprecated)
        """
        if hasattr(item, 'pjlink'):
            return item.pjlink.set_shutter_closed()
        for list_item in self.projector_list_widget.selectedItems():
            list_item.data(QtCore.Qt.ItemDataRole.UserRole).pjlink.set_shutter_closed()

    def on_doubleclick_item(self, item):
        """
        When item is doubleclicked, will connect to projector.

        :param item: List widget item for connection.
        """
        projector = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if QSOCKET_STATE[projector.link.state()] == S_CONNECTED:
            log.debug(f'ProjectorManager: "{projector.pjlink.name}" already connected - skipping')
        else:
            log.debug(f'ProjectorManager: "{projector.pjlink.name}" calling connect_to_host()')
            projector.link.connect_to_host()
        return

    def on_connect_projector(self, item=None, opt=None):
        """
        Calls projector thread to connect to projector

        :param item: (Optional) ProjectorItem() for direct call
        :param opt: (Deprecated)
        """
        if hasattr(item, 'pjlink'):
            return item.pjlink.connect_to_host()
        else:
            for list_item in self.projector_list_widget.selectedItems():
                list_item.data(QtCore.Qt.ItemDataRole.UserRole).pjlink.connect_to_host()

    def on_delete_projector(self, opt=None):
        """
        Deletes a projector from the list and the database

        :param opt: Needed by PySide6
        """
        list_item = self.projector_list_widget.item(self.projector_list_widget.currentRow())
        if list_item is None:
            return
        projector = list_item.data(QtCore.Qt.ItemDataRole.UserRole)
        msg = QtWidgets.QMessageBox()
        msg.setText(translate('OpenLP.ProjectorManager',
                              f'Delete projector ({projector.link.ip}) {projector.link.name}?'))
        msg.setInformativeText(translate('OpenLP.ProjectorManager',
                                         'Are you sure you want to delete this projector?'))
        msg.setStandardButtons(msg.StandardButton.Cancel | msg.StandardButton.Ok)
        msg.setDefaultButton(msg.StandardButton.Cancel)
        ans = msg.exec()
        if ans == msg.StandardButton.Cancel:
            return
        try:
            projector.link.projectorChangeStatus.disconnect(self.update_status)
        except (AttributeError, TypeError):
            pass
        try:
            projector.link.authentication_error.disconnect(self.authentication_error)
        except (AttributeError, TypeError):
            pass
        try:
            projector.link.no_authentication_error.disconnect(self.no_authentication_error)
        except (AttributeError, TypeError):
            pass
        try:
            projector.link.projectorUpdateIcons.disconnect(self.update_icons)
        except (AttributeError, TypeError):
            pass
        try:
            projector.link.poll_timer.stop()
            projector.link.poll_timer.timeout.disconnect(projector.link.poll_loop)
        except (AttributeError, TypeError):
            pass
        try:
            projector.link.socket_timer.stop()
            projector.link.socket_timer.timeout.disconnect(projector.link.socket_abort)
        except (AttributeError, TypeError):
            pass

        old_port = projector.link.port
        # Rebuild projector list
        new_list = []
        for item in self.projector_list:
            if item.link.db_item.id == projector.link.db_item.id:
                log.debug(f'Removing projector "{item.link.name}"')
                continue
            new_list.append(item)
        self.projector_list = new_list
        list_item = self.projector_list_widget.takeItem(self.projector_list_widget.currentRow())
        list_item = None
        if not self.projectordb.delete_projector(projector.db_item):
            log.warning(f'Delete projector {projector.db_item} failed')
        for item in self.projector_list:
            log.debug(f'New projector list - item: {item.link.ip} {item.link.name}')
        self.udp_listen_delete(old_port)

    def on_disconnect_projector(self, item=None, opt=None):
        """
        Calls projector thread to disconnect from projector

        :param item: (Optional) ProjectorItem() for direct call
        :param opt: (Deprecated)
        """
        if hasattr(item, 'pjlink'):
            return item.pjlink.disconnect_from_host()
        else:
            for list_item in self.projector_list_widget.selectedItems():
                list_item.data(QtCore.Qt.ItemDataRole.UserRole).pjlink.disconnect_from_host()

    def on_edit_projector(self, opt=None):
        """
        Calls edit dialog with selected projector to edit information

        :param opt: Needed by PySide6
        """
        list_item = self.projector_list_widget.item(self.projector_list_widget.currentRow())
        projector = list_item.data(QtCore.Qt.ItemDataRole.UserRole)
        if projector is None:
            return
        self.old_projector = projector
        projector.link.disconnect_from_host()
        self.projector_form.exec(projector.db_item)
        projector.db_item = self.projectordb.get_projector_by_id(self.old_projector.db_item.id)

    def on_poweroff_projector(self, item=None, opt=None):
        """
        Calls projector thread to turn projector off

        :param item: (Optional) ProjectorItem() for direct call
        :param opt: (Deprecated)
        """
        if hasattr(item, 'pjlink'):
            return item.pjlink.set_power_off()
        else:
            for list_item in self.projector_list_widget.selectedItems():
                list_item.data(QtCore.Qt.ItemDataRole.UserRole).pjlink.set_power_off()

    def on_poweron_projector(self, item=None, opt=None):
        """
        Calls projector thread to turn projector on

        :param item: (Optional) ProjectorItem() for direct call
        :param opt: (Deprecated)
        """
        if hasattr(item, 'pjlink'):
            return item.pjlink.set_power_on()
        else:
            for list_item in self.projector_list_widget.selectedItems():
                list_item.data(QtCore.Qt.ItemDataRole.UserRole).pjlink.set_power_on()

    def on_show_projector(self, item=None, opt=None):
        """
        Calls projector thread to open shutter

        :param item: (Optional) ProjectorItem() for direct call
        :param opt: (Deprecated)
        """
        if hasattr(item, 'pjlink'):
            return item.pjlink.set_shutter_open()
        else:
            for list_item in self.projector_list_widget.selectedItems():
                list_item.data(QtCore.Qt.ItemDataRole.UserRole).pjlink.set_shutter_open()

    def on_status_projector(self, opt=None):
        """
        Builds message box with projector status information

        :param opt: Needed by PySide6
        """
        lwi = self.projector_list_widget.item(self.projector_list_widget.currentRow())
        projector = lwi.data(QtCore.Qt.ItemDataRole.UserRole)
        message = '<b>{title}</b>: {data}<BR />'.format(title=translate('OpenLP.ProjectorManager', 'Name'),
                                                        data=projector.link.name)
        message += '<b>{title}</b>: {data}<br />'.format(title=translate('OpenLP.ProjectorManager', 'IP'),
                                                         data=projector.link.ip)
        message += '<b>{title}</b>: {data}<br />'.format(title=translate('OpenLP.ProjectorManager', 'Port'),
                                                         data=projector.link.port)
        message += '<b>{title}</b>: {data}<br />'.format(title=translate('OpenLP.ProjectorManager', 'Notes'),
                                                         data=projector.link.notes)
        message += '<hr /><br >'
        if projector.link.manufacturer is None:
            message += translate('OpenLP.ProjectorManager', 'Projector information not available at this time.')
        else:
            message += '<b>{title}</b>: {data}<br />'.format(title=translate('OpenLP.ProjectorManager',
                                                                             'Projector Name'),
                                                             data=projector.link.pjlink_name)
            message += '<b>{title}</b>: {data}<br />'.format(title=translate('OpenLP.ProjectorManager', 'Manufacturer'),
                                                             data=projector.link.manufacturer)
            message += '<b>{title}</b>: {data}<br />'.format(title=translate('OpenLP.ProjectorManager', 'Model'),
                                                             data=projector.link.model)
            message += '<b>{title}</b>: {data}<br />'.format(title=translate('OpenLP.ProjectorManager', 'PJLink Class'),
                                                             data=projector.link.pjlink_class)
            if projector.link.pjlink_class != 1:
                message += '<b>{title}</b>: {data}<br />'.format(title=translate('OpenLP.ProjectorManager',
                                                                                 'Software Version'),
                                                                 data=projector.link.sw_version)
                message += '<b>{title}</b>: {data}<br />'.format(title=translate('OpenLP.ProjectorManager',
                                                                                 'Serial Number'),
                                                                 data=projector.link.serial_no)
                message += '<b>{title}</b>: {data}<br />'.format(title=translate('OpenLP.ProjectorManager',
                                                                                 'Lamp Model Number'),
                                                                 data=projector.link.model_lamp)
                message += '<b>{title}</b>: {data}<br />'.format(title=translate('OpenLP.ProjectorManager',
                                                                                 'Filter Model Number'),
                                                                 data=projector.link.model_filter)
            message += '<b>{title}</b>: {data}<br /><br />'.format(title=translate('OpenLP.ProjectorManager',
                                                                                   'Other info'),
                                                                   data=projector.link.other_info)
            message += '<b>{title}</b>: {data}<br />'.format(title=translate('OpenLP.ProjectorManager', 'Power status'),
                                                             data=STATUS_MSG[projector.link.power])
            message += '<b>{title}</b>: {data}<br />'.format(title=translate('OpenLP.ProjectorManager', 'Shutter is'),
                                                             data=translate('OpenLP.ProjectorManager', 'Closed')
                                                             if projector.link.shutter
                                                             else translate('OpenLP', 'Open'))
            message = '{msg}<b>{source}</b>: {selected}<br />'.format(msg=message,
                                                                      source=translate('OpenLP.ProjectorManager',
                                                                                       'Current source input is'),
                                                                      selected=projector.link.source)
            count = 1
            for item in projector.link.lamp:
                if item['On'] is None:
                    status = translate('OpenLP.ProjectorManager', 'Unavailable')
                elif item['On']:
                    status = translate('OpenLP.ProjectorManager', 'ON')
                else:
                    status = translate('OpenLP.ProjectorManager', 'OFF')
                message += '<b>{title} {count}</b> {status} '.format(title=translate('OpenLP.ProjectorManager',
                                                                                     'Lamp'),
                                                                     count=count,
                                                                     status=status)

                message += '<b>{title}</b>: {hours}<br />'.format(title=translate('OpenLP.ProjectorManager', 'Hours'),
                                                                  hours=item['Hours'])
                count += 1
            message += '<hr /><br />'
            if projector.link.projector_errors is None:
                message += translate('OpenLP.ProjectorManager', 'No current errors or warnings')
            else:
                message += '<b>{data}</b>'.format(data=translate('OpenLP.ProjectorManager', 'Current errors/warnings'))
                for (key, val) in projector.link.projector_errors.items():
                    message += '<b>{key}</b>: {data}<br />'.format(key=key, data=STATUS_MSG[val])
        QtWidgets.QMessageBox.information(self, translate('OpenLP.ProjectorManager', 'Projector Information'), message)

    def on_view_projector(self, opt=None):
        """
        Calls edit dialog as readonly with selected projector to show information

        :param opt: Needed by PySide6
        """
        list_item = self.projector_list_widget.item(self.projector_list_widget.currentRow())
        projector = list_item.data(QtCore.Qt.ItemDataRole.UserRole)
        if projector is None:
            return
        self.old_projector = projector
        self.projector_form.exec(projector.db_item, edit=False)

    def _add_projector(self, projector):
        """
        Helper app to build a projector instance

        :param projector: Dict of projector database information
        :returns: PJLink() instance
        """
        log.debug('_add_projector()')
        return PJLink(projector=projector,
                      poll_time=self.poll_time,
                      socket_timeout=self.socket_timeout)

    def add_projector(self, projector, start=False):
        """
        Builds manager list item, projector thread, and timer for projector instance.


        :param projector: Projector instance to add
        :param start: Start projector if True
        """
        item = ProjectorItem(parent=self, item=self._add_projector(projector))
        item.db_item = projector
        item.icon = QtGui.QIcon(self.status_icons[S_NOT_CONNECTED])
        widget = QtWidgets.QListWidgetItem(item.icon,
                                           item.pjlink.name,
                                           self.projector_list_widget
                                           )
        widget.setData(QtCore.Qt.ItemDataRole.UserRole, item)
        item.pjlink.db_item = item.db_item
        item.widget = widget
        item.pjlink.projectorChangeStatus.connect(self.update_status)
        item.pjlink.projectorAuthentication.connect(self.authentication_error)
        item.pjlink.projectorNoAuthentication.connect(self.no_authentication_error)
        item.pjlink.projectorUpdateIcons.connect(self.update_icons)
        # Add UDP listener for new projector port
        self.udp_listen_add(item.pjlink.port)
        self.projector_list.append(item)
        if start:
            item.pjlink.connect_to_host()
        for item in self.projector_list:
            log.debug(f'New projector list - item: ({item.pjlink.ip}) {item.pjlink.name}')

    @QtCore.Slot(str)
    def add_projector_from_wizard(self, ip, opts=None):
        """
        Add a projector from the edit dialog

        :param ip: IP address of new record item to find
        :param opts: Needed by PySide6
        """
        log.debug(f'add_projector_from_wizard(ip={ip})')
        item = self.projectordb.get_projector_by_ip(ip)
        self.add_projector(item)

    @QtCore.Slot(object)
    def edit_projector_from_wizard(self, projector):
        """
        Update projector from the wizard edit page

        :param projector: Projector() instance of projector with updated information
        """
        log.debug(f'edit_projector_from_wizard(ip={projector.ip})')
        old_port = self.old_projector.link.port
        old_ip = self.old_projector.link.ip
        self.old_projector.link.name = projector.name
        self.old_projector.link.ip = projector.ip
        self.old_projector.link.pin = None if projector.pin == '' else projector.pin
        self.old_projector.link.location = projector.location
        self.old_projector.link.notes = projector.notes
        self.old_projector.widget.setText(projector.name)
        self.old_projector.link.port = int(projector.port)
        # Update projector list items
        for item in self.projector_list:
            if item.link.ip == old_ip:
                item.link.port = int(projector.port)
                # NOTE: This assumes (!) we are using IP addresses as keys
                break
        # Update UDP listeners before setting old_projector.port
        if old_port != projector.port:
            self.udp_listen_delete(old_port)
            self.udp_listen_add(int(projector.port))

    def _load_projectors(self):
        """'
        Load projectors - only call when initializing or after database changes
        """
        log.debug('_load_projectors()')
        self.projector_list_widget.clear()
        for item in self.projectordb.get_projector_all():
            self.add_projector(projector=item, start=self.autostart)

    def get_projector_list(self):
        """
        Return the list of active projectors

        :returns: list
        """
        return self.projector_list

    @QtCore.Slot(str, int, str)
    def update_status(self, ip: str, status: Optional[int] = None, msg: Optional[str] = None):
        """
        Update the status information/icon for selected list item

        :param ip: IP address of projector
        :param status: Optional status code
        :param msg: Optional status message
        """
        if status is None:
            return
        self._try_update_status(ip, status, msg)

    def _try_update_status(self, ip: str, status: int, msg: Optional[str] = None):
        """
        Try to update the status of a projector
        """
        if not self.is_updating_status:
            self.update_status_timer.stop()
            self._update_status(ip, status, msg)
        else:
            self.update_status_timer.stop()
            self.update_status_timer.start()

    def _update_status(self, ip: str, status: int, msg: Optional[str] = None):
        """
        Actually update the status of the projector
        """
        self.is_updating_status = True
        try:
            item = None
            for list_item in self.projector_list:
                if ip == list_item.link.ip:
                    item = list_item
                    break
            if item is None:
                log.error(f'ProjectorManager: Unknown item "{ip}" - not updating status')
                self.is_updating_status = False
                return
            elif item.status == status:
                log.debug(f'ProjectorManager: No status change for "{ip}" - not updating status')
                self.is_updating_status = False
                return

            item.status = status
            item.icon = self.status_icons[status]
            log.debug(f'({item.link.name}) Updating icon with {STATUS_CODE[status]}')
            item.widget.setIcon(item.icon)
            self.is_updating_status = False
            return self.update_icons()
        except RuntimeError:
            # it's probably a "wrapped C/C++ object of type QTreeWidgetItem has been deleted" due to
            # consecutive/parallel repaint_service_list execution. We've added some mitigation to avoid this
            # to happen, but it for any reason it happens again, we'll silent it and try to repaint the list
            # again (to avoid a broken list presented to the user).
            self.is_updating_status = False

    def get_toolbar_item(self, name, enabled=False, hidden=False):
        item = self.one_toolbar.findChild(QtGui.QAction, name)
        if item == 0:
            log.debug(f'No item found with name "{name}"')
            return
        item.setVisible(False if hidden else True)
        item.setEnabled(True if enabled else False)

    @QtCore.Slot()
    def update_icons(self):
        """
        Update the icons when the selected projectors change
        """
        log.debug('update_icons(): Checking for selected projector items in list')
        count = len(self.projector_list_widget.selectedItems())
        projector = None
        if count == 0:
            self.get_toolbar_item('edit_projector')
            self.get_toolbar_item('delete_projector')
            self.get_toolbar_item('view_projector', hidden=True)
            self.get_toolbar_item('source_view_projector', hidden=True)
            self.get_toolbar_item('connect_projector')
            self.get_toolbar_item('disconnect_projector')
            self.get_toolbar_item('poweron_projector')
            self.get_toolbar_item('poweroff_projector')
            self.get_toolbar_item('blank_projector')
            self.get_toolbar_item('show_projector')
            self.get_toolbar_item('connect_projector_multiple', hidden=True)
            self.get_toolbar_item('disconnect_projector_multiple', hidden=True)
            self.get_toolbar_item('poweron_projector_multiple', hidden=True)
            self.get_toolbar_item('poweroff_projector_multiple', hidden=True)
            self.get_toolbar_item('blank_projector_multiple', hidden=True)
            self.get_toolbar_item('show_projector_multiple', hidden=True)
        elif count == 1:
            log.debug('update_icons(): Found one item selected')
            projector = self.projector_list_widget.selectedItems()[0].data(QtCore.Qt.ItemDataRole.UserRole)
            connected = QSOCKET_STATE[projector.link.state()] == S_CONNECTED
            power = projector.link.power == S_ON
            self.get_toolbar_item('connect_projector_multiple', hidden=True)
            self.get_toolbar_item('disconnect_projector_multiple', hidden=True)
            self.get_toolbar_item('poweron_projector_multiple', hidden=True)
            self.get_toolbar_item('poweroff_projector_multiple', hidden=True)
            self.get_toolbar_item('blank_projector_multiple', hidden=True)
            self.get_toolbar_item('show_projector_multiple', hidden=True)
            if connected:
                log.debug('update_icons(): Updating icons for connected state')
                self.get_toolbar_item('view_projector', enabled=True)
                self.get_toolbar_item('source_view_projector',
                                      enabled=projector.link.source_available is not None and connected and power)
                self.get_toolbar_item('edit_projector', hidden=True)
                self.get_toolbar_item('delete_projector', hidden=True)
            else:
                log.debug('update_icons(): Updating for not connected state')
                self.get_toolbar_item('view_projector', hidden=True)
                self.get_toolbar_item('source_view_projector', hidden=True)
                self.get_toolbar_item('edit_projector', enabled=True)
                self.get_toolbar_item('delete_projector', enabled=True)
            self.get_toolbar_item('connect_projector', enabled=not connected)
            self.get_toolbar_item('disconnect_projector', enabled=connected)
            self.get_toolbar_item('poweron_projector', enabled=connected and (projector.link.power == S_STANDBY))
            self.get_toolbar_item('poweroff_projector', enabled=connected and (projector.link.power == S_ON))
            if projector.link.shutter is not None:
                self.get_toolbar_item('blank_projector', enabled=(connected and power and not projector.link.shutter))
                self.get_toolbar_item('show_projector', enabled=(connected and power and projector.link.shutter))
            else:
                self.get_toolbar_item('blank_projector', enabled=False)
                self.get_toolbar_item('show_projector', enabled=False)
        else:
            log.debug('update_icons(): Updating for multiple items selected')
            self.get_toolbar_item('edit_projector', enabled=False)
            self.get_toolbar_item('delete_projector', enabled=False)
            self.get_toolbar_item('view_projector', hidden=True)
            self.get_toolbar_item('source_view_projector', hidden=True)
            self.get_toolbar_item('connect_projector', hidden=True)
            self.get_toolbar_item('disconnect_projector', hidden=True)
            self.get_toolbar_item('poweron_projector', hidden=True)
            self.get_toolbar_item('poweroff_projector', hidden=True)
            self.get_toolbar_item('blank_projector', hidden=True)
            self.get_toolbar_item('show_projector', hidden=True)
            self.get_toolbar_item('connect_projector_multiple', hidden=False, enabled=True)
            self.get_toolbar_item('disconnect_projector_multiple', hidden=False, enabled=True)
            self.get_toolbar_item('poweron_projector_multiple', hidden=False, enabled=True)
            self.get_toolbar_item('poweroff_projector_multiple', hidden=False, enabled=True)
            self.get_toolbar_item('blank_projector_multiple', hidden=False, enabled=True)
            self.get_toolbar_item('show_projector_multiple', hidden=False, enabled=True)

    @QtCore.Slot(str)
    def authentication_error(self, name):
        """
        Display warning dialog when attempting to connect with invalid pin

        :param name: Name from QListWidgetItem
        """
        title = '"{name} {message}" '.format(name=name,
                                             message=translate('OpenLP.ProjectorManager', 'Authentication Error'))
        QtWidgets.QMessageBox.warning(self, title,
                                      '<br />There was an authentication error while trying to connect.'
                                      '<br /><br />Please verify your PIN setting '
                                      'for projector item "{name}"'.format(name=name))

    @QtCore.Slot(str)
    def no_authentication_error(self, name):
        """
        Display warning dialog when pin saved for item but projector does not
        require pin.

        :param name: Name from QListWidgetItem
        """
        title = '"{name} {message}" '.format(name=name,
                                             message=translate('OpenLP.ProjectorManager', 'No Authentication Error'))
        QtWidgets.QMessageBox.warning(self, title,
                                      '<br />PIN is set and projector does not require authentication.'
                                      '<br /><br />Please verify your PIN setting '
                                      'for projector item "{name}"'.format(name=name))


class ProjectorItem(QtCore.QObject):
    """
    Class for the projector list widget item.
    NOTE: Actual PJLink class instance should be saved as self.link
    """
    def __init__(self, parent=None, link=None, item=None):
        """
        Initialization for ProjectorItem instance

        :param link: (Deprecated) PJLink instance for QListWidgetItem
        :param item: PJLink instance for QListWidgetItem
        """
        # Refactor so self.link is renamed self.pjlink to clarify reference
        if link is None:
            self.link = item
            self.pjlink = item
        else:
            self.link = link
            self.pjlink = link
        self.thread = None
        self.icon = None
        self.widget = None
        self.my_parent = None
        self.timer = None
        self.projectordb_item = None
        self.poll_time = None
        self.socket_timeout = None
        self.status = S_NOT_CONNECTED
        self.serial_no = None
        self.sw_version = None
        self.model_filter = None
        self.model_lamp = None
        super().__init__()
