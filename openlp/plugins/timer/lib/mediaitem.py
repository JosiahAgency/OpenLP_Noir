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
Media manager item for timer presets.
"""
from PySide6 import QtCore, QtWidgets

from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.registry import Registry
from openlp.core.lib import check_item_selected
from openlp.core.lib.mediamanageritem import MediaManagerItem
from openlp.core.lib.serviceitem import ItemCapabilities
from openlp.core.ui.icons import UiIcons
from openlp.plugins.timer.forms.edittimerform import EditTimerForm
from openlp.plugins.timer.lib import TimerMode, format_seconds
from openlp.plugins.timer.lib.db import TimerItem


class TimerMediaItem(MediaManagerItem):
    """
    Timer preset list and service-item generation.
    """
    def __init__(self, parent, plugin):
        self.icon_path = 'timer/timer'
        super().__init__(parent, plugin)

    def setup_item(self):
        self.edit_form = None
        self.single_service_item = True
        self.quick_preview_allowed = True
        self.has_search = False
        Registry().register_function('slidecontroller_live_started', self.on_live_item_started)

    def add_middle_header_bar(self):
        self.toolbar.addSeparator()
        self.toolbar.add_toolbar_action(
            'timerStartAction',
            text=translate('TimerPlugin.MediaItem', 'Start'),
            icon=UiIcons().play,
            tooltip=translate('TimerPlugin.MediaItem', 'Start the selected timer as an overlay.'),
            triggers=self.on_start_timer_click)
        self.toolbar.add_toolbar_action(
            'timerPauseAction',
            text=translate('TimerPlugin.MediaItem', 'Pause'),
            icon=UiIcons().pause,
            tooltip=translate('TimerPlugin.MediaItem', 'Pause the running timer overlay.'),
            triggers=self.on_pause_timer_click)
        self.toolbar.add_toolbar_action(
            'timerResumeAction',
            text=translate('TimerPlugin.MediaItem', 'Resume'),
            icon=UiIcons().time,
            tooltip=translate('TimerPlugin.MediaItem', 'Resume the paused timer overlay.'),
            triggers=self.on_resume_timer_click)
        self.toolbar.add_toolbar_action(
            'timerResetAction',
            text=translate('TimerPlugin.MediaItem', 'Reset'),
            icon=UiIcons().undo,
            tooltip=translate('TimerPlugin.MediaItem', 'Reset the running timer overlay.'),
            triggers=self.on_reset_timer_click)
        self.toolbar.add_toolbar_action(
            'timerStopAction',
            text=translate('TimerPlugin.MediaItem', 'Stop'),
            icon=UiIcons().stop,
            tooltip=translate('TimerPlugin.MediaItem', 'Stop the running timer overlay.'),
            triggers=self.on_stop_timer_click)

    def initialise(self):
        timer_items = self.plugin.db_manager.get_all_objects(TimerItem, order_by_ref=TimerItem.title)
        self.load_list(timer_items)

    def load_list(self, timer_items=None, target_group=None):
        self.save_auto_select_id()
        self.list_view.clear()
        if not timer_items:
            timer_items = self.plugin.db_manager.get_all_objects(TimerItem, order_by_ref=TimerItem.title)
        timer_items.sort()
        for timer_item in timer_items:
            mode_prefix = 'CD' if timer_item.mode == TimerMode.Countdown.value else 'CU'
            label = '{title} [{mode} {duration}]'.format(
                title=timer_item.title, mode=mode_prefix, duration=format_seconds(timer_item.duration_seconds))
            widget_item = QtWidgets.QListWidgetItem(label)
            widget_item.setData(QtCore.Qt.ItemDataRole.UserRole, timer_item.id)
            self.list_view.addItem(widget_item)
            if timer_item.id == self.auto_select_id:
                self.list_view.setCurrentItem(widget_item)
        self.auto_select_id = -1

    def on_new_click(self):
        if self.edit_form is None:
            self.edit_form = EditTimerForm(self)
        self.edit_form.load_data(None)
        if self.edit_form.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            payload = self.edit_form.to_payload()
            if not payload['title']:
                return
            item = TimerItem(title=payload['title'],
                             mode=payload['mode'],
                             duration_seconds=payload['duration_seconds'],
                             theme_name=payload['theme_name'])
            self.plugin.db_manager.save_object(item)
            self.load_list()

    def on_edit_click(self):
        if check_item_selected(self.list_view, UiStrings().SelectEdit):
            if self.edit_form is None:
                self.edit_form = EditTimerForm(self)
            list_item = self.list_view.currentItem()
            timer_item = self.plugin.db_manager.get_object(TimerItem, list_item.data(QtCore.Qt.ItemDataRole.UserRole))
            if not timer_item:
                return
            self.edit_form.load_data(timer_item)
            if self.edit_form.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                payload = self.edit_form.to_payload()
                if not payload['title']:
                    return
                timer_item.title = payload['title']
                timer_item.mode = payload['mode']
                timer_item.duration_seconds = payload['duration_seconds']
                timer_item.theme_name = payload['theme_name']
                self.plugin.db_manager.save_object(timer_item)
                self.load_list()

    def on_delete_click(self):
        if check_item_selected(self.list_view, UiStrings().SelectDelete):
            if QtWidgets.QMessageBox.question(
                    self, UiStrings().ConfirmDelete,
                    translate('TimerPlugin.MediaItem',
                              'Are you sure you want to delete the selected timer preset?'),
                    defaultButton=QtWidgets.QMessageBox.StandardButton.No) == QtWidgets.QMessageBox.StandardButton.No:
                return
            list_item = self.list_view.currentItem()
            self.plugin.db_manager.delete_object(TimerItem, list_item.data(QtCore.Qt.ItemDataRole.UserRole))
            self.load_list()

    def _get_selected_timer_item(self):
        if not self.list_view.selectedIndexes():
            self.show_library_hint(translate('TimerPlugin.MediaItem', 'Select a timer preset first.'))
            return None
        list_item = self.list_view.currentItem()
        if list_item is None:
            self.show_library_hint(translate('TimerPlugin.MediaItem', 'Select a timer preset first.'))
            return None
        timer_item = self.plugin.db_manager.get_object(TimerItem, list_item.data(QtCore.Qt.ItemDataRole.UserRole))
        if timer_item is None:
            self.show_library_hint(translate('TimerPlugin.MediaItem', 'Unable to load the selected timer preset.'))
            return None
        return timer_item

    def on_start_timer_click(self):
        if self._get_selected_timer_item() is None:
            return
        self.go_live()

    def on_pause_timer_click(self):
        self.plugin.overlay_manager.pause()

    def on_resume_timer_click(self):
        self.plugin.overlay_manager.resume()

    def on_reset_timer_click(self):
        self.plugin.overlay_manager.reset()

    def on_stop_timer_click(self):
        self.plugin.overlay_manager.stop()

    def on_live_item_started(self, payload):
        """
        Start timer runtime when a timer service item goes live; stop for other items.
        """
        if not payload:
            self.plugin.overlay_manager.stop()
            return
        service_item = payload[0]
        if service_item.name != self.plugin.name:
            self.plugin.overlay_manager.stop()
            return
        timer_data = (service_item.data_string or {}).get('timer')
        if not timer_data:
            self.plugin.overlay_manager.stop()
            return
        self.plugin.overlay_manager.start_for_service_item(service_item)

    def generate_slide_data(self, service_item, *, item=None, **kwargs):
        item_id = self._get_id_of_item_to_generate(item, False)
        if not item_id:
            return False
        timer_item = self.plugin.db_manager.get_object(TimerItem, item_id)
        if not timer_item:
            return False
        service_item.title = timer_item.title
        service_item.add_from_text(format_seconds(timer_item.duration_seconds))
        service_item.data_string = {
            'timer': {
                'id': timer_item.id,
                'title': timer_item.title,
                'mode': timer_item.mode,
                'duration_seconds': timer_item.duration_seconds
            }
        }
        service_item.add_capability(ItemCapabilities.CanPreview)
        service_item.add_capability(ItemCapabilities.CanLoop)
        service_item.add_capability(ItemCapabilities.CanEditTitle)
        if timer_item.theme_name:
            service_item.theme = timer_item.theme_name
        elif self.plugin.settings_tab and self.plugin.settings_tab.timer_theme:
            service_item.theme = self.plugin.settings_tab.timer_theme
        return True
