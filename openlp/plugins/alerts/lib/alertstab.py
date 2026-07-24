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
The alerts settings tab: a per-priority style preset editor. Each priority
(Info, Notice, Important, Critical) owns a full preset covering type,
position, typography, background and animation; this tab edits one preset at
a time.
"""
from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.registry import Registry
from openlp.core.lib.settingstab import SettingsTab
from openlp.core.widgets.buttons import ColorButton
from openlp.plugins.alerts.lib.presets import (ALERT_TYPES, ANIMATIONS_IN, ANIMATIONS_OUT, BACKGROUND_STYLES,
                                               DEFAULT_PRESETS, EMPHASIS_EFFECTS, ICONS, PRIORITY_KEYS, SHAPES,
                                               ZONES_H, ZONES_V, AlertPriority, get_alert_presets, save_alert_presets)

# Selectable font weights: (label builder index, css weight)
FONT_WEIGHTS = [300, 400, 500, 600, 700, 800, 900]


class AlertsTab(SettingsTab):
    """
    AlertsTab is the alerts settings tab in the settings dialog.
    """
    def setup_ui(self):
        self.setObjectName('AlertsTab')
        super(AlertsTab, self).setup_ui()
        self._loading = False
        self.presets = {}
        self.current_priority_key = PRIORITY_KEYS[0]
        # Priority selector
        self.priority_group_box = QtWidgets.QGroupBox(self.left_column)
        self.priority_group_box.setObjectName('priority_group_box')
        self.priority_layout = QtWidgets.QFormLayout(self.priority_group_box)
        self.priority_label = QtWidgets.QLabel(self.priority_group_box)
        self.priority_combo_box = QtWidgets.QComboBox(self.priority_group_box)
        self.priority_combo_box.setObjectName('priority_combo_box')
        self.priority_layout.addRow(self.priority_label, self.priority_combo_box)
        self.left_layout.addWidget(self.priority_group_box)
        # The preset editor lives in sub-tabs to keep the control count sane
        self.preset_tabs = QtWidgets.QTabWidget(self.left_column)
        self.preset_tabs.setObjectName('preset_tabs')
        self._setup_type_tab()
        self._setup_typography_tab()
        self._setup_background_tab()
        self._setup_animation_tab()
        self.left_layout.addWidget(self.preset_tabs)
        self.left_layout.addStretch()
        # Preview
        self.preview_group_box = QtWidgets.QGroupBox(self.right_column)
        self.preview_group_box.setObjectName('preview_group_box')
        self.preview_layout = QtWidgets.QVBoxLayout(self.preview_group_box)
        self.preview_frame = QtWidgets.QFrame(self.preview_group_box)
        self.preview_frame.setObjectName('preview_frame')
        self.preview_frame.setMinimumHeight(140)
        self.preview_frame_layout = QtWidgets.QVBoxLayout(self.preview_frame)
        self.preview_frame_layout.setContentsMargins(18, 18, 18, 18)
        self.font_preview = QtWidgets.QLabel(self.preview_frame)
        self.font_preview.setObjectName('font_preview')
        self.font_preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.font_preview.setWordWrap(True)
        self.preview_frame_layout.addStretch()
        self.preview_frame_layout.addWidget(self.font_preview)
        self.preview_frame_layout.addStretch()
        self.preview_layout.addWidget(self.preview_frame)
        self.preview_note_label = QtWidgets.QLabel(self.preview_group_box)
        self.preview_note_label.setObjectName('preview_note_label')
        self.preview_note_label.setWordWrap(True)
        self.preview_layout.addWidget(self.preview_note_label)
        self.reset_button = QtWidgets.QPushButton(self.preview_group_box)
        self.reset_button.setObjectName('reset_button')
        self.preview_layout.addWidget(self.reset_button)
        self.right_layout.addWidget(self.preview_group_box)
        self.right_layout.addStretch()
        # Signals
        self.priority_combo_box.currentIndexChanged.connect(self.on_priority_changed)
        self.reset_button.clicked.connect(self.on_reset_clicked)
        for widget in self._value_widgets():
            self._connect_changed(widget)

    def _setup_type_tab(self):
        """Alert type, screen zone and positioning controls."""
        self.type_tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(self.type_tab)
        self.alert_type_label = QtWidgets.QLabel(self.type_tab)
        self.alert_type_combo_box = QtWidgets.QComboBox(self.type_tab)
        self.alert_type_combo_box.setObjectName('alert_type_combo_box')
        layout.addRow(self.alert_type_label, self.alert_type_combo_box)
        # 3x3 zone grid
        self.zone_label = QtWidgets.QLabel(self.type_tab)
        zone_widget = QtWidgets.QWidget(self.type_tab)
        zone_layout = QtWidgets.QGridLayout(zone_widget)
        zone_layout.setSpacing(4)
        zone_layout.setContentsMargins(0, 0, 0, 0)
        self.zone_buttons = {}
        self.zone_button_group = QtWidgets.QButtonGroup(zone_widget)
        for row, zone_v in enumerate(ZONES_V):
            for col, zone_h in enumerate(ZONES_H):
                button = QtWidgets.QToolButton(zone_widget)
                button.setCheckable(True)
                button.setFixedSize(34, 26)
                button.setObjectName(f'zone_button_{zone_v}_{zone_h}')
                self.zone_button_group.addButton(button)
                zone_layout.addWidget(button, row, col)
                self.zone_buttons[(zone_h, zone_v)] = button
        layout.addRow(self.zone_label, zone_widget)
        self.offset_x_label = QtWidgets.QLabel(self.type_tab)
        self.offset_x_spin_box = QtWidgets.QSpinBox(self.type_tab)
        self.offset_x_spin_box.setRange(-50, 50)
        self.offset_x_spin_box.setSuffix(' %')
        layout.addRow(self.offset_x_label, self.offset_x_spin_box)
        self.offset_y_label = QtWidgets.QLabel(self.type_tab)
        self.offset_y_spin_box = QtWidgets.QSpinBox(self.type_tab)
        self.offset_y_spin_box.setRange(-50, 50)
        self.offset_y_spin_box.setSuffix(' %')
        layout.addRow(self.offset_y_label, self.offset_y_spin_box)
        self.margin_x_label = QtWidgets.QLabel(self.type_tab)
        self.margin_x_spin_box = QtWidgets.QSpinBox(self.type_tab)
        self.margin_x_spin_box.setRange(0, 400)
        self.margin_x_spin_box.setSuffix(' px')
        layout.addRow(self.margin_x_label, self.margin_x_spin_box)
        self.margin_y_label = QtWidgets.QLabel(self.type_tab)
        self.margin_y_spin_box = QtWidgets.QSpinBox(self.type_tab)
        self.margin_y_spin_box.setRange(0, 400)
        self.margin_y_spin_box.setSuffix(' px')
        layout.addRow(self.margin_y_label, self.margin_y_spin_box)
        self.preset_tabs.addTab(self.type_tab, '')

    def _setup_typography_tab(self):
        """Font family, weight, spacing and text effect controls."""
        self.typography_tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(self.typography_tab)
        self.font_label = QtWidgets.QLabel(self.typography_tab)
        self.font_combo_box = QtWidgets.QFontComboBox(self.typography_tab)
        self.font_combo_box.setObjectName('font_combo_box')
        layout.addRow(self.font_label, self.font_combo_box)
        self.font_size_label = QtWidgets.QLabel(self.typography_tab)
        self.font_size_spin_box = QtWidgets.QSpinBox(self.typography_tab)
        self.font_size_spin_box.setObjectName('font_size_spin_box')
        self.font_size_spin_box.setRange(8, 200)
        layout.addRow(self.font_size_label, self.font_size_spin_box)
        self.font_weight_label = QtWidgets.QLabel(self.typography_tab)
        self.font_weight_combo_box = QtWidgets.QComboBox(self.typography_tab)
        self.font_weight_combo_box.setObjectName('font_weight_combo_box')
        layout.addRow(self.font_weight_label, self.font_weight_combo_box)
        self.font_color_label = QtWidgets.QLabel(self.typography_tab)
        self.font_color_button = ColorButton(self.typography_tab)
        self.font_color_button.setObjectName('font_color_button')
        layout.addRow(self.font_color_label, self.font_color_button)
        self.letter_spacing_label = QtWidgets.QLabel(self.typography_tab)
        self.letter_spacing_spin_box = QtWidgets.QDoubleSpinBox(self.typography_tab)
        self.letter_spacing_spin_box.setRange(-5.0, 30.0)
        self.letter_spacing_spin_box.setSingleStep(0.5)
        self.letter_spacing_spin_box.setSuffix(' px')
        layout.addRow(self.letter_spacing_label, self.letter_spacing_spin_box)
        self.line_spacing_label = QtWidgets.QLabel(self.typography_tab)
        self.line_spacing_spin_box = QtWidgets.QDoubleSpinBox(self.typography_tab)
        self.line_spacing_spin_box.setRange(0.8, 3.0)
        self.line_spacing_spin_box.setSingleStep(0.1)
        layout.addRow(self.line_spacing_label, self.line_spacing_spin_box)
        self.text_opacity_label = QtWidgets.QLabel(self.typography_tab)
        self.text_opacity_spin_box = QtWidgets.QSpinBox(self.typography_tab)
        self.text_opacity_spin_box.setRange(10, 100)
        self.text_opacity_spin_box.setSuffix(' %')
        layout.addRow(self.text_opacity_label, self.text_opacity_spin_box)
        # Shadow
        self.shadow_check_box = QtWidgets.QCheckBox(self.typography_tab)
        self.shadow_check_box.setObjectName('shadow_check_box')
        self.shadow_color_button = ColorButton(self.typography_tab)
        layout.addRow(self.shadow_check_box, self.shadow_color_button)
        self.shadow_blur_label = QtWidgets.QLabel(self.typography_tab)
        self.shadow_blur_spin_box = QtWidgets.QSpinBox(self.typography_tab)
        self.shadow_blur_spin_box.setRange(0, 60)
        self.shadow_blur_spin_box.setSuffix(' px')
        layout.addRow(self.shadow_blur_label, self.shadow_blur_spin_box)
        # Outline
        self.outline_check_box = QtWidgets.QCheckBox(self.typography_tab)
        self.outline_check_box.setObjectName('outline_check_box')
        self.outline_color_button = ColorButton(self.typography_tab)
        layout.addRow(self.outline_check_box, self.outline_color_button)
        self.outline_width_label = QtWidgets.QLabel(self.typography_tab)
        self.outline_width_spin_box = QtWidgets.QSpinBox(self.typography_tab)
        self.outline_width_spin_box.setRange(1, 12)
        self.outline_width_spin_box.setSuffix(' px')
        layout.addRow(self.outline_width_label, self.outline_width_spin_box)
        # Glow
        self.glow_check_box = QtWidgets.QCheckBox(self.typography_tab)
        self.glow_check_box.setObjectName('glow_check_box')
        self.glow_color_button = ColorButton(self.typography_tab)
        layout.addRow(self.glow_check_box, self.glow_color_button)
        self.glow_radius_label = QtWidgets.QLabel(self.typography_tab)
        self.glow_radius_spin_box = QtWidgets.QSpinBox(self.typography_tab)
        self.glow_radius_spin_box.setRange(1, 80)
        self.glow_radius_spin_box.setSuffix(' px')
        layout.addRow(self.glow_radius_label, self.glow_radius_spin_box)
        self.preset_tabs.addTab(self.typography_tab, '')

    def _setup_background_tab(self):
        """Background style, shape, padding controls."""
        self.background_tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(self.background_tab)
        self.background_style_label = QtWidgets.QLabel(self.background_tab)
        self.background_style_combo_box = QtWidgets.QComboBox(self.background_tab)
        self.background_style_combo_box.setObjectName('background_style_combo_box')
        layout.addRow(self.background_style_label, self.background_style_combo_box)
        self.background_color_label = QtWidgets.QLabel(self.background_tab)
        self.background_color_button = ColorButton(self.background_tab)
        self.background_color_button.setObjectName('background_color_button')
        layout.addRow(self.background_color_label, self.background_color_button)
        self.background_color2_label = QtWidgets.QLabel(self.background_tab)
        self.background_color2_button = ColorButton(self.background_tab)
        layout.addRow(self.background_color2_label, self.background_color2_button)
        self.gradient_angle_label = QtWidgets.QLabel(self.background_tab)
        self.gradient_angle_spin_box = QtWidgets.QSpinBox(self.background_tab)
        self.gradient_angle_spin_box.setRange(0, 360)
        self.gradient_angle_spin_box.setSuffix('°')
        layout.addRow(self.gradient_angle_label, self.gradient_angle_spin_box)
        self.background_opacity_label = QtWidgets.QLabel(self.background_tab)
        self.background_opacity_spin_box = QtWidgets.QSpinBox(self.background_tab)
        self.background_opacity_spin_box.setRange(0, 100)
        self.background_opacity_spin_box.setSuffix(' %')
        layout.addRow(self.background_opacity_label, self.background_opacity_spin_box)
        self.background_blur_label = QtWidgets.QLabel(self.background_tab)
        self.background_blur_spin_box = QtWidgets.QSpinBox(self.background_tab)
        self.background_blur_spin_box.setRange(0, 60)
        self.background_blur_spin_box.setSuffix(' px')
        layout.addRow(self.background_blur_label, self.background_blur_spin_box)
        self.shape_label = QtWidgets.QLabel(self.background_tab)
        self.shape_combo_box = QtWidgets.QComboBox(self.background_tab)
        self.shape_combo_box.setObjectName('shape_combo_box')
        layout.addRow(self.shape_label, self.shape_combo_box)
        self.corner_radius_label = QtWidgets.QLabel(self.background_tab)
        self.corner_radius_spin_box = QtWidgets.QSpinBox(self.background_tab)
        self.corner_radius_spin_box.setRange(0, 80)
        self.corner_radius_spin_box.setSuffix(' px')
        layout.addRow(self.corner_radius_label, self.corner_radius_spin_box)
        self.padding_x_label = QtWidgets.QLabel(self.background_tab)
        self.padding_x_spin_box = QtWidgets.QSpinBox(self.background_tab)
        self.padding_x_spin_box.setRange(0, 200)
        self.padding_x_spin_box.setSuffix(' px')
        layout.addRow(self.padding_x_label, self.padding_x_spin_box)
        self.padding_y_label = QtWidgets.QLabel(self.background_tab)
        self.padding_y_spin_box = QtWidgets.QSpinBox(self.background_tab)
        self.padding_y_spin_box.setRange(0, 200)
        self.padding_y_spin_box.setSuffix(' px')
        layout.addRow(self.padding_y_label, self.padding_y_spin_box)
        self.preset_tabs.addTab(self.background_tab, '')

    def _setup_animation_tab(self):
        """Animation, icon and behaviour controls."""
        self.animation_tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(self.animation_tab)
        self.animation_in_label = QtWidgets.QLabel(self.animation_tab)
        self.animation_in_combo_box = QtWidgets.QComboBox(self.animation_tab)
        self.animation_in_combo_box.setObjectName('animation_in_combo_box')
        layout.addRow(self.animation_in_label, self.animation_in_combo_box)
        self.animation_out_label = QtWidgets.QLabel(self.animation_tab)
        self.animation_out_combo_box = QtWidgets.QComboBox(self.animation_tab)
        self.animation_out_combo_box.setObjectName('animation_out_combo_box')
        layout.addRow(self.animation_out_label, self.animation_out_combo_box)
        self.animation_speed_label = QtWidgets.QLabel(self.animation_tab)
        self.animation_speed_spin_box = QtWidgets.QSpinBox(self.animation_tab)
        self.animation_speed_spin_box.setRange(100, 2000)
        self.animation_speed_spin_box.setSingleStep(50)
        self.animation_speed_spin_box.setSuffix(' ms')
        layout.addRow(self.animation_speed_label, self.animation_speed_spin_box)
        self.emphasis_label = QtWidgets.QLabel(self.animation_tab)
        self.emphasis_combo_box = QtWidgets.QComboBox(self.animation_tab)
        self.emphasis_combo_box.setObjectName('emphasis_combo_box')
        layout.addRow(self.emphasis_label, self.emphasis_combo_box)
        self.scroll_check_box = QtWidgets.QCheckBox(self.animation_tab)
        self.scroll_check_box.setObjectName('scroll_check_box')
        layout.addRow(self.scroll_check_box)
        self.repeat_label = QtWidgets.QLabel(self.animation_tab)
        self.repeat_spin_box = QtWidgets.QSpinBox(self.animation_tab)
        self.repeat_spin_box.setObjectName('repeat_spin_box')
        self.repeat_spin_box.setRange(1, 10)
        layout.addRow(self.repeat_label, self.repeat_spin_box)
        self.icon_check_box = QtWidgets.QCheckBox(self.animation_tab)
        self.icon_check_box.setObjectName('icon_check_box')
        self.icon_combo_box = QtWidgets.QComboBox(self.animation_tab)
        self.icon_combo_box.setObjectName('icon_combo_box')
        layout.addRow(self.icon_check_box, self.icon_combo_box)
        self.timeout_label = QtWidgets.QLabel(self.animation_tab)
        self.timeout_spin_box = QtWidgets.QSpinBox(self.animation_tab)
        self.timeout_spin_box.setObjectName('timeout_spin_box')
        self.timeout_spin_box.setRange(1, 180)
        layout.addRow(self.timeout_label, self.timeout_spin_box)
        self.preset_tabs.addTab(self.animation_tab, '')

    def _value_widgets(self):
        """All widgets that hold preset values."""
        return [
            self.alert_type_combo_box, self.offset_x_spin_box, self.offset_y_spin_box,
            self.margin_x_spin_box, self.margin_y_spin_box,
            self.font_combo_box, self.font_size_spin_box, self.font_weight_combo_box, self.font_color_button,
            self.letter_spacing_spin_box, self.line_spacing_spin_box, self.text_opacity_spin_box,
            self.shadow_check_box, self.shadow_color_button, self.shadow_blur_spin_box,
            self.outline_check_box, self.outline_color_button, self.outline_width_spin_box,
            self.glow_check_box, self.glow_color_button, self.glow_radius_spin_box,
            self.background_style_combo_box, self.background_color_button, self.background_color2_button,
            self.gradient_angle_spin_box, self.background_opacity_spin_box, self.background_blur_spin_box,
            self.shape_combo_box, self.corner_radius_spin_box, self.padding_x_spin_box, self.padding_y_spin_box,
            self.animation_in_combo_box, self.animation_out_combo_box, self.animation_speed_spin_box,
            self.emphasis_combo_box, self.scroll_check_box, self.repeat_spin_box,
            self.icon_check_box, self.icon_combo_box, self.timeout_spin_box,
        ] + list(self.zone_buttons.values())

    def _connect_changed(self, widget):
        """Connect a widget's value-changed signal to the generic handler."""
        if isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
            widget.valueChanged.connect(self.on_value_changed)
        elif isinstance(widget, QtWidgets.QFontComboBox):
            widget.currentFontChanged.connect(self.on_value_changed)
        elif isinstance(widget, QtWidgets.QComboBox):
            widget.currentIndexChanged.connect(self.on_value_changed)
        elif isinstance(widget, QtWidgets.QCheckBox):
            widget.toggled.connect(self.on_value_changed)
        elif isinstance(widget, ColorButton):
            widget.colorChanged.connect(self.on_value_changed)
        elif isinstance(widget, QtWidgets.QToolButton):
            widget.toggled.connect(self.on_value_changed)

    def retranslate_ui(self):
        self.priority_group_box.setTitle(translate('AlertsPlugin.AlertsTab', 'Alert Style Presets'))
        self.priority_label.setText(translate('AlertsPlugin.AlertsTab', 'Edit preset for:'))
        self.priority_combo_box.clear()
        self.priority_combo_box.addItems(AlertPriority.display_names())
        self.preset_tabs.setTabText(0, translate('AlertsPlugin.AlertsTab', 'Type && Position'))
        self.preset_tabs.setTabText(1, translate('AlertsPlugin.AlertsTab', 'Typography'))
        self.preset_tabs.setTabText(2, translate('AlertsPlugin.AlertsTab', 'Background'))
        self.preset_tabs.setTabText(3, translate('AlertsPlugin.AlertsTab', 'Animation && Behaviour'))
        self.alert_type_label.setText(translate('AlertsPlugin.AlertsTab', 'Alert type:'))
        self.alert_type_combo_box.clear()
        self.alert_type_combo_box.addItems([
            translate('AlertsPlugin.AlertsTab', 'Banner (full width)'),
            translate('AlertsPlugin.AlertsTab', 'Toast'),
            translate('AlertsPlugin.AlertsTab', 'Lower third'),
            translate('AlertsPlugin.AlertsTab', 'Center overlay'),
            translate('AlertsPlugin.AlertsTab', 'Full screen'),
        ])
        self.zone_label.setText(translate('AlertsPlugin.AlertsTab', 'Screen position:'))
        for (zone_h, zone_v), button in self.zone_buttons.items():
            button.setToolTip(f'{zone_v} {zone_h}')
        self.offset_x_label.setText(translate('AlertsPlugin.AlertsTab', 'Horizontal offset:'))
        self.offset_y_label.setText(translate('AlertsPlugin.AlertsTab', 'Vertical offset:'))
        self.margin_x_label.setText(translate('AlertsPlugin.AlertsTab', 'Horizontal margin:'))
        self.margin_y_label.setText(translate('AlertsPlugin.AlertsTab', 'Vertical margin:'))
        self.font_label.setText(translate('AlertsPlugin.AlertsTab', 'Font name:'))
        self.font_size_label.setText(translate('AlertsPlugin.AlertsTab', 'Font size:'))
        self.font_size_spin_box.setSuffix(' {unit}'.format(unit=UiStrings().FontSizePtUnit))
        self.font_weight_label.setText(translate('AlertsPlugin.AlertsTab', 'Weight:'))
        self.font_weight_combo_box.clear()
        self.font_weight_combo_box.addItems([
            translate('AlertsPlugin.AlertsTab', 'Light (300)'),
            translate('AlertsPlugin.AlertsTab', 'Regular (400)'),
            translate('AlertsPlugin.AlertsTab', 'Medium (500)'),
            translate('AlertsPlugin.AlertsTab', 'Semi-bold (600)'),
            translate('AlertsPlugin.AlertsTab', 'Bold (700)'),
            translate('AlertsPlugin.AlertsTab', 'Extra-bold (800)'),
            translate('AlertsPlugin.AlertsTab', 'Black (900)'),
        ])
        self.font_color_label.setText(translate('AlertsPlugin.AlertsTab', 'Font color:'))
        self.letter_spacing_label.setText(translate('AlertsPlugin.AlertsTab', 'Letter spacing:'))
        self.line_spacing_label.setText(translate('AlertsPlugin.AlertsTab', 'Line spacing:'))
        self.text_opacity_label.setText(translate('AlertsPlugin.AlertsTab', 'Text opacity:'))
        self.shadow_check_box.setText(translate('AlertsPlugin.AlertsTab', 'Text shadow'))
        self.shadow_blur_label.setText(translate('AlertsPlugin.AlertsTab', 'Shadow blur:'))
        self.outline_check_box.setText(translate('AlertsPlugin.AlertsTab', 'Outline'))
        self.outline_width_label.setText(translate('AlertsPlugin.AlertsTab', 'Outline width:'))
        self.glow_check_box.setText(translate('AlertsPlugin.AlertsTab', 'Glow'))
        self.glow_radius_label.setText(translate('AlertsPlugin.AlertsTab', 'Glow radius:'))
        self.background_style_label.setText(translate('AlertsPlugin.AlertsTab', 'Style:'))
        self.background_style_combo_box.clear()
        self.background_style_combo_box.addItems([
            translate('AlertsPlugin.AlertsTab', 'Solid'),
            translate('AlertsPlugin.AlertsTab', 'Gradient'),
            translate('AlertsPlugin.AlertsTab', 'Glassmorphism (blur)'),
            translate('AlertsPlugin.AlertsTab', 'Semi-transparent'),
            translate('AlertsPlugin.AlertsTab', 'None'),
        ])
        self.background_color_label.setText(UiStrings().BackgroundColorColon)
        self.background_color2_label.setText(translate('AlertsPlugin.AlertsTab', 'Second gradient color:'))
        self.gradient_angle_label.setText(translate('AlertsPlugin.AlertsTab', 'Gradient angle:'))
        self.background_opacity_label.setText(translate('AlertsPlugin.AlertsTab', 'Background opacity:'))
        self.background_blur_label.setText(translate('AlertsPlugin.AlertsTab', 'Backdrop blur:'))
        self.shape_label.setText(translate('AlertsPlugin.AlertsTab', 'Shape:'))
        self.shape_combo_box.clear()
        self.shape_combo_box.addItems([
            translate('AlertsPlugin.AlertsTab', 'Full width'),
            translate('AlertsPlugin.AlertsTab', 'Rounded rectangle'),
            translate('AlertsPlugin.AlertsTab', 'Pill'),
            translate('AlertsPlugin.AlertsTab', 'Floating card'),
        ])
        self.corner_radius_label.setText(translate('AlertsPlugin.AlertsTab', 'Corner radius:'))
        self.padding_x_label.setText(translate('AlertsPlugin.AlertsTab', 'Horizontal padding:'))
        self.padding_y_label.setText(translate('AlertsPlugin.AlertsTab', 'Vertical padding:'))
        self.animation_in_label.setText(translate('AlertsPlugin.AlertsTab', 'Entrance:'))
        self.animation_in_combo_box.clear()
        self.animation_in_combo_box.addItems([
            translate('AlertsPlugin.AlertsTab', 'None'),
            translate('AlertsPlugin.AlertsTab', 'Fade'),
            translate('AlertsPlugin.AlertsTab', 'Slide down'),
            translate('AlertsPlugin.AlertsTab', 'Slide up'),
            translate('AlertsPlugin.AlertsTab', 'Slide in from right'),
            translate('AlertsPlugin.AlertsTab', 'Slide in from left'),
            translate('AlertsPlugin.AlertsTab', 'Zoom'),
            translate('AlertsPlugin.AlertsTab', 'Bounce'),
            translate('AlertsPlugin.AlertsTab', 'Flip'),
        ])
        self.animation_out_label.setText(translate('AlertsPlugin.AlertsTab', 'Exit:'))
        self.animation_out_combo_box.clear()
        self.animation_out_combo_box.addItems([
            translate('AlertsPlugin.AlertsTab', 'None'),
            translate('AlertsPlugin.AlertsTab', 'Fade'),
            translate('AlertsPlugin.AlertsTab', 'Slide down'),
            translate('AlertsPlugin.AlertsTab', 'Slide up'),
            translate('AlertsPlugin.AlertsTab', 'Slide out to left'),
            translate('AlertsPlugin.AlertsTab', 'Slide out to right'),
            translate('AlertsPlugin.AlertsTab', 'Zoom'),
            translate('AlertsPlugin.AlertsTab', 'Flip'),
        ])
        self.animation_speed_label.setText(translate('AlertsPlugin.AlertsTab', 'Speed:'))
        self.emphasis_label.setText(translate('AlertsPlugin.AlertsTab', 'Emphasis:'))
        self.emphasis_combo_box.clear()
        self.emphasis_combo_box.addItems([
            translate('AlertsPlugin.AlertsTab', 'None'),
            translate('AlertsPlugin.AlertsTab', 'Pulse'),
            translate('AlertsPlugin.AlertsTab', 'Flash'),
            translate('AlertsPlugin.AlertsTab', 'Shake'),
        ])
        self.scroll_check_box.setText(translate('AlertsPlugin.AlertsTab', 'Scroll text (marquee)'))
        self.repeat_label.setText(translate('AlertsPlugin.AlertsTab', 'Scroll passes:'))
        self.icon_check_box.setText(translate('AlertsPlugin.AlertsTab', 'Show icon'))
        self.icon_combo_box.clear()
        self.icon_combo_box.addItems([
            translate('AlertsPlugin.AlertsTab', 'Automatic (by priority)'),
            translate('AlertsPlugin.AlertsTab', 'None'),
            translate('AlertsPlugin.AlertsTab', 'Info circle'),
            translate('AlertsPlugin.AlertsTab', 'Bell'),
            translate('AlertsPlugin.AlertsTab', 'Warning triangle'),
            translate('AlertsPlugin.AlertsTab', 'Critical octagon'),
            translate('AlertsPlugin.AlertsTab', 'Megaphone'),
            translate('AlertsPlugin.AlertsTab', 'Clock'),
            translate('AlertsPlugin.AlertsTab', 'Heart'),
        ])
        self.timeout_label.setText(translate('AlertsPlugin.AlertsTab', 'Alert timeout:'))
        self.timeout_spin_box.setSuffix(' {unit}'.format(unit=UiStrings().Seconds))
        self.preview_group_box.setTitle(UiStrings().Preview)
        self.font_preview.setText(UiStrings().OpenLP)
        self.preview_note_label.setText(translate(
            'AlertsPlugin.AlertsTab',
            'The preview is approximate; blur, glow and animations only show on the display.'))
        self.reset_button.setText(translate('AlertsPlugin.AlertsTab', 'Reset this preset to defaults'))

    def on_priority_changed(self, index):
        """A different priority preset was selected for editing."""
        # Guard against signals fired while loading, or during retranslate
        # before the presets have been loaded
        if self._loading or index < 0 or not self.presets:
            return
        self._store_widget_values()
        self.current_priority_key = PRIORITY_KEYS[index]
        self._load_widget_values()

    def on_value_changed(self, *args):
        """Any preset value changed: refresh the preview and mark dirty."""
        if self._loading or not self.presets:
            return
        self._store_widget_values()
        self.changed = True
        self.update_display()

    def on_reset_clicked(self):
        """Reset the currently edited preset to its built-in default."""
        self.presets[self.current_priority_key] = dict(DEFAULT_PRESETS[self.current_priority_key])
        self.changed = True
        self._load_widget_values()

    def _store_widget_values(self):
        """Copy widget values into the preset of the current priority."""
        preset = self.presets[self.current_priority_key]
        preset['alertType'] = ALERT_TYPES[self.alert_type_combo_box.currentIndex()]
        for (zone_h, zone_v), button in self.zone_buttons.items():
            if button.isChecked():
                preset['zoneH'] = zone_h
                preset['zoneV'] = zone_v
        preset['offsetX'] = self.offset_x_spin_box.value()
        preset['offsetY'] = self.offset_y_spin_box.value()
        preset['marginX'] = self.margin_x_spin_box.value()
        preset['marginY'] = self.margin_y_spin_box.value()
        preset['fontFace'] = self.font_combo_box.currentFont().family()
        preset['fontSize'] = self.font_size_spin_box.value()
        preset['fontWeight'] = FONT_WEIGHTS[self.font_weight_combo_box.currentIndex()]
        preset['fontColor'] = self.font_color_button.color
        preset['letterSpacing'] = self.letter_spacing_spin_box.value()
        preset['lineSpacing'] = round(self.line_spacing_spin_box.value(), 2)
        preset['textOpacity'] = self.text_opacity_spin_box.value()
        preset['textShadowEnabled'] = self.shadow_check_box.isChecked()
        preset['textShadowColor'] = self.shadow_color_button.color
        preset['textShadowBlur'] = self.shadow_blur_spin_box.value()
        preset['outlineEnabled'] = self.outline_check_box.isChecked()
        preset['outlineColor'] = self.outline_color_button.color
        preset['outlineWidth'] = self.outline_width_spin_box.value()
        preset['glowEnabled'] = self.glow_check_box.isChecked()
        preset['glowColor'] = self.glow_color_button.color
        preset['glowRadius'] = self.glow_radius_spin_box.value()
        preset['backgroundStyle'] = BACKGROUND_STYLES[self.background_style_combo_box.currentIndex()]
        preset['backgroundColor'] = self.background_color_button.color
        preset['backgroundColor2'] = self.background_color2_button.color
        preset['gradientAngle'] = self.gradient_angle_spin_box.value()
        preset['backgroundOpacity'] = self.background_opacity_spin_box.value()
        preset['backgroundBlur'] = self.background_blur_spin_box.value()
        preset['shape'] = SHAPES[self.shape_combo_box.currentIndex()]
        preset['cornerRadius'] = self.corner_radius_spin_box.value()
        preset['paddingX'] = self.padding_x_spin_box.value()
        preset['paddingY'] = self.padding_y_spin_box.value()
        preset['animationIn'] = ANIMATIONS_IN[self.animation_in_combo_box.currentIndex()]
        preset['animationOut'] = ANIMATIONS_OUT[self.animation_out_combo_box.currentIndex()]
        preset['animationSpeed'] = self.animation_speed_spin_box.value()
        preset['emphasis'] = EMPHASIS_EFFECTS[self.emphasis_combo_box.currentIndex()]
        preset['scroll'] = self.scroll_check_box.isChecked()
        preset['repeat'] = self.repeat_spin_box.value()
        preset['iconEnabled'] = self.icon_check_box.isChecked()
        preset['icon'] = ICONS[self.icon_combo_box.currentIndex()]
        preset['timeout'] = self.timeout_spin_box.value()

    def _load_widget_values(self):
        """Populate the widgets from the preset of the current priority."""
        preset = self.presets[self.current_priority_key]
        self._loading = True
        try:
            self.alert_type_combo_box.setCurrentIndex(self._index_of(ALERT_TYPES, preset['alertType']))
            zone_button = self.zone_buttons.get((preset['zoneH'], preset['zoneV']))
            if zone_button:
                zone_button.setChecked(True)
            self.offset_x_spin_box.setValue(int(preset['offsetX']))
            self.offset_y_spin_box.setValue(int(preset['offsetY']))
            self.margin_x_spin_box.setValue(int(preset['marginX']))
            self.margin_y_spin_box.setValue(int(preset['marginY']))
            font = QtGui.QFont()
            font.setFamily(preset['fontFace'])
            self.font_combo_box.setCurrentFont(font)
            self.font_size_spin_box.setValue(int(preset['fontSize']))
            weight = min(FONT_WEIGHTS, key=lambda candidate: abs(candidate - int(preset['fontWeight'])))
            self.font_weight_combo_box.setCurrentIndex(FONT_WEIGHTS.index(weight))
            self.font_color_button.color = preset['fontColor']
            self.letter_spacing_spin_box.setValue(float(preset['letterSpacing']))
            self.line_spacing_spin_box.setValue(float(preset['lineSpacing']))
            self.text_opacity_spin_box.setValue(int(preset['textOpacity']))
            self.shadow_check_box.setChecked(bool(preset['textShadowEnabled']))
            self.shadow_color_button.color = preset['textShadowColor']
            self.shadow_blur_spin_box.setValue(int(preset['textShadowBlur']))
            self.outline_check_box.setChecked(bool(preset['outlineEnabled']))
            self.outline_color_button.color = preset['outlineColor']
            self.outline_width_spin_box.setValue(int(preset['outlineWidth']))
            self.glow_check_box.setChecked(bool(preset['glowEnabled']))
            self.glow_color_button.color = preset['glowColor']
            self.glow_radius_spin_box.setValue(int(preset['glowRadius']))
            self.background_style_combo_box.setCurrentIndex(
                self._index_of(BACKGROUND_STYLES, preset['backgroundStyle']))
            self.background_color_button.color = preset['backgroundColor']
            self.background_color2_button.color = preset['backgroundColor2']
            self.gradient_angle_spin_box.setValue(int(preset['gradientAngle']))
            self.background_opacity_spin_box.setValue(int(preset['backgroundOpacity']))
            self.background_blur_spin_box.setValue(int(preset['backgroundBlur']))
            self.shape_combo_box.setCurrentIndex(self._index_of(SHAPES, preset['shape']))
            self.corner_radius_spin_box.setValue(int(preset['cornerRadius']))
            self.padding_x_spin_box.setValue(int(preset['paddingX']))
            self.padding_y_spin_box.setValue(int(preset['paddingY']))
            self.animation_in_combo_box.setCurrentIndex(self._index_of(ANIMATIONS_IN, preset['animationIn']))
            self.animation_out_combo_box.setCurrentIndex(self._index_of(ANIMATIONS_OUT, preset['animationOut']))
            self.animation_speed_spin_box.setValue(int(preset['animationSpeed']))
            self.emphasis_combo_box.setCurrentIndex(self._index_of(EMPHASIS_EFFECTS, preset['emphasis']))
            self.scroll_check_box.setChecked(bool(preset['scroll']))
            self.repeat_spin_box.setValue(int(preset['repeat']))
            self.icon_check_box.setChecked(bool(preset['iconEnabled']))
            self.icon_combo_box.setCurrentIndex(self._index_of(ICONS, preset['icon']))
            self.timeout_spin_box.setValue(int(preset['timeout']))
        finally:
            self._loading = False
        self.update_display()

    @staticmethod
    def _index_of(values, value):
        """Index of value in values, falling back to 0."""
        try:
            return values.index(value)
        except ValueError:
            return 0

    def load(self):
        """
        Load the presets into the UI.
        """
        self.presets = get_alert_presets(self.settings)
        self.current_priority_key = PRIORITY_KEYS[self.priority_combo_box.currentIndex()]
        self._load_widget_values()
        self.changed = False

    def save(self):
        """
        Save the presets on exit of the Settings dialog.
        """
        self._store_widget_values()
        save_alert_presets(self.settings, self.presets)
        self.changed = False

    def update_display(self):
        """
        Update the preview after changes have been made. The preview is a Qt
        approximation of the web rendering: font, colors, radius and shape.
        """
        preset = self.presets[self.current_priority_key]
        font = QtGui.QFont()
        font.setFamily(preset['fontFace'])
        font.setWeight(QtGui.QFont.Weight(int(preset['fontWeight'])))
        font.setPointSize(max(8, min(28, int(preset['fontSize']) // 2)))
        if preset['letterSpacing']:
            font.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, float(preset['letterSpacing']) / 2)
        self.font_preview.setFont(font)
        radius = 0
        if preset['shape'] == 'pill':
            radius = 22
        elif preset['shape'] in ('rounded', 'card'):
            radius = min(22, int(preset['cornerRadius']))
        opacity = max(0, min(100, int(preset['backgroundOpacity'])))
        alpha = int(opacity * 255 / 100)
        base_color = QtGui.QColor(preset['backgroundColor'])
        base_color.setAlpha(alpha)
        if preset['backgroundStyle'] == 'gradient':
            second_color = QtGui.QColor(preset['backgroundColor2'])
            second_color.setAlpha(alpha)
            background = ('qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {start}, stop:1 {stop})'
                          .format(start=base_color.name(QtGui.QColor.NameFormat.HexArgb),
                                  stop=second_color.name(QtGui.QColor.NameFormat.HexArgb)))
        elif preset['backgroundStyle'] == 'none':
            background = 'transparent'
        else:
            background = base_color.name(QtGui.QColor.NameFormat.HexArgb)
        self.font_preview.setStyleSheet(
            'QLabel {{ background: {background}; color: {color}; border-radius: {radius}px; '
            'padding: {pad_y}px {pad_x}px; }}'.format(
                background=background, color=preset['fontColor'], radius=radius,
                pad_x=min(40, int(preset['paddingX']) // 2), pad_y=min(24, int(preset['paddingY']) // 2)))

    @property
    def alerts_manager(self):
        """The AlertsManager from the registry (mainly for tests)."""
        return Registry().get('alerts_manager')
