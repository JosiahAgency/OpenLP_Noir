from PySide6 import QtWidgets, QtCore

from openlp.core.common.i18n import translate
from openlp.core.common.registry import Registry
from openlp.plugins.alerts.lib.presets import AlertPriority


class AlertMonitorDialog(QtWidgets.QDialog):
    """
        Non-modal view of the alert queue: what is showing, what is waiting, and
        controls to stop, restart or override. Holds no queue logic of its own.
        """

    def __init__(self, plugin):
        flags = (
                QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.WindowTitleHint |
                QtCore.Qt.WindowType.WindowCloseButtonHint)
        super().__init__(Registry().get('main_window'), flags)
        self.plugin = plugin
        self._setup_ui()
        self._countdown_timer = QtCore.QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self.refresh_countdown)
        self.alerts_manager.queue_changed.connect(self.refresh)
        self.retranslate_ui()
        self.refresh()

    @property
    def alerts_manager(self):
        return Registry().get('alerts_manager')

    def _setup_ui(self):
        self.setObjectName('alert_monitor_dialog')
        self.resize(420, 420)
        layout = QtWidgets.QVBoxLayout(self)
        self.current_group_box = QtWidgets.QGroupBox(self)
        current_layout = QtWidgets.QVBoxLayout(self.current_group_box)
        self.current_label = QtWidgets.QLabel(self.current_group_box)
        self.current_label.setWordWrap(True)
        self.remaining_label = QtWidgets.QLabel(self.current_group_box)
        current_layout.addWidget(self.current_label)
        current_layout.addWidget(self.remaining_label)
        current_buttons = QtWidgets.QHBoxLayout()
        self.stop_button = QtWidgets.QPushButton(self.current_group_box)
        self.restart_button = QtWidgets.QPushButton(self.current_group_box)
        self.stop_all_button = QtWidgets.QPushButton(self.current_group_box)
        for button in (self.stop_button, self.restart_button, self.stop_all_button):
            current_buttons.addWidget(button)
        current_layout.addLayout(current_buttons)
        layout.addWidget(self.current_group_box)

        self.queue_group_box = QtWidgets.QGroupBox(self)
        queue_layout = QtWidgets.QVBoxLayout(self.queue_group_box)
        self.queue_list = QtWidgets.QListWidget(self.queue_group_box)
        self.queue_list.setAlternatingRowColors(True)
        queue_layout.addWidget(self.queue_list)
        queue_buttons = QtWidgets.QHBoxLayout()
        self.show_now_button = QtWidgets.QPushButton(self.queue_group_box)
        self.remove_button = QtWidgets.QPushButton(self.queue_group_box)
        self.clear_button = QtWidgets.QPushButton(self.queue_group_box)
        for button in (self.show_now_button, self.remove_button, self.clear_button):
            queue_buttons.addWidget(button)
        queue_layout.addLayout(queue_buttons)
        layout.addWidget(self.queue_group_box)

        self.stop_button.clicked.connect(lambda: self.alerts_manager.stop_current())
        self.stop_all_button.clicked.connect(lambda: self.alerts_manager.stop_current(clear_queue=True))
        self.restart_button.clicked.connect(lambda: self.alerts_manager.restart_current())
        self.show_now_button.clicked.connect(self.on_show_now_clicked)
        self.remove_button.clicked.connect(self.on_remove_clicked)
        self.clear_button.clicked.connect(lambda: self.alerts_manager.clear_queue())
        self.queue_list.currentRowChanged.connect(self._update_queue_buttons)
        self.queue_list.itemDoubleClicked.connect(lambda item: self.on_show_now_clicked())

    def retranslate_ui(self):
        tr = 'AlertsPlugin.AlertMonitor'
        self.setWindowTitle(translate(tr, 'Alert Monitor'))
        self.current_group_box.setTitle(translate(tr, 'Now Showing!'))
        self.queue_group_box.setTitle(translate(tr, 'Queued & Waiting!'))
        self.stop_button.setText(translate(tr, 'Stop'))
        self.restart_button.setText(translate(tr, 'Restart'))
        self.stop_all_button.setText(translate(tr, 'Stop All'))
        self.show_now_button.setText(translate(tr, 'Show Now'))
        self.remove_button.setText(translate(tr, 'Remove'))
        self.clear_button.setText(translate(tr, 'Clear Queue'))
        self.show_now_button.setToolTip(
            translate(tr, 'Override the alert on the screen. It returns to the front of the queue'))

    @staticmethod
    def _caption(alert):
        text = alert['text']
        if len(text) > 60:
            text = text[:60] + '...'
        return f"[{AlertPriority.display_names()[alert['priority']]}] {text}"

    def _selected_id(self):
        item = self.queue_list.currentItem()
        return item.data(QtCore.Qt.ItemDataRole.UserRole) if item else None

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
        self._countdown_timer.start()

    def hideEvent(self, event):
        self._countdown_timer.stop()
        super().hideEvent(event)

    def refresh(self):
        """Re-render from the manager's state."""
        state = self.alerts_manager.get_state()
        current = state['current']
        if current:
            self.current_label.setText(self._caption(current))
        else:
            self.current_label.setText(translate('AlertsPlugin.AlertMonitor', 'No alert is currently showing.'))

        self.stop_button.setEnabled(current is not None)
        self.stop_all_button.setEnabled(current is not None or bool(state['queue']))
        self.restart_button.setEnabled(current is not None or state['last'] is not None)
        selected = self._selected_id()
        self.queue_list.clear()
        for position, alert in enumerate(state['queue'], 1):
            item = QtWidgets.QListWidgetItem(f'{position}. {self._caption(alert)}')
            item.setData(QtCore.Qt.ItemDataRole.UserRole, alert['id'])
            self.queue_list.addItem(item)
            if alert['id'] == selected:
                self.queue_list.setCurrentItem(item)
        self.clear_button.setEnabled(bool(state['queue']))
        self._update_queue_buttons()
        self.refresh_countdown()

    def refresh_countdown(self):
        remaining_ms = self.alerts_manager.get_state()['remaining_ms']
        if remaining_ms:
            self.remaining_label.setText(
                translate('AlertsPlugin.AlertMonitor', 'Time remaining: {seconds}s left').format(
                    seconds=(remaining_ms + 999) // 1000))
        else:
            self.remaining_label.setText('')

    def _update_queue_buttons(self, *args):
        has_selection = self._selected_id() is not None
        self.show_now_button.setEnabled(has_selection)
        self.remove_button.setEnabled(has_selection)

    def on_show_now_clicked(self):
        alert_id = self._selected_id()
        if alert_id is not None:
            self.alerts_manager.show_now(alert_id)

    def on_remove_clicked(self):
        alert_id = self._selected_id()
        if alert_id is not None:
            self.alerts_manager.remove_from_queue(alert_id)
