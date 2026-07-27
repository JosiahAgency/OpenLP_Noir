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
The :mod:`~openlp.plugins.alerts.lib.style_editor` module provides
``StyleEditorWidget``: the alert style editor (type & position, typography,
background, animation & behaviour, plus a live-ish preview). It edits one
style dict at a time and knows nothing about where that dict comes from —
it's shared by the Settings tab (which edits the four priority defaults) and
the alert template editor (which edits one template's own style).
"""
from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common.i18n import UiStrings, translate
from openlp.core.widgets.buttons import ColorButton
from openlp.plugins.alerts.lib.presets import (ALERT_TYPES, ANIMATIONS_IN, ANIMATIONS_OUT, BACKGROUND_STYLES,
                                               EMPHASIS_EFFECTS, ICONS, SHAPES, ZONES_H, ZONES_V, _BASE_PRESET)

# Selectable font weights: (label builder index, css weight)
FONT_WEIGHTS = [300, 400, 500, 600, 700, 800, 900]


class StyleEditorWidget(QtCore.QObject):
    """
    Edits a single alert style dict: type/position, typography, background
    and animation/behaviour, in sub-tabs, with a preview. Call
    :meth:`load_style` to display a style, and :meth:`store_style` to read
    the edited values back out.

    Exposes two standalone widgets, ``preset_tabs`` and ``preview_group_box``,
    for a host to place in its own layout (e.g. side by side, or one above
    the other) rather than owning a fixed layout itself.
    """
    #: Emitted whenever the user changes a value (not when load_style() sets one).
    valueChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False
        self._loaded = False
        self._style = dict(_BASE_PRESET)
        self.preset_tabs = QtWidgets.QTabWidget()
        self.preset_tabs.setObjectName('preset_tabs')
        self._setup_type_tab()
        self._setup_typography_tab()
        self._setup_background_tab()
        self._setup_animation_tab()
        self._setup_preview()
        for widget in self._value_widgets():
            self._connect_changed(widget)
        self.retranslate_ui()

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

    def _setup_preview(self):
        """A Qt approximation of the style, plus a reset-to-default button."""
        self.preview_group_box = QtWidgets.QGroupBox()
        self.preview_group_box.setObjectName('preview_group_box')
        preview_layout = QtWidgets.QVBoxLayout(self.preview_group_box)
        self.preview_frame = QtWidgets.QFrame(self.preview_group_box)
        self.preview_frame.setObjectName('preview_frame')
        self.preview_frame.setMinimumHeight(140)
        preview_frame_layout = QtWidgets.QVBoxLayout(self.preview_frame)
        preview_frame_layout.setContentsMargins(18, 18, 18, 18)
        self.font_preview = QtWidgets.QLabel(self.preview_frame)
        self.font_preview.setObjectName('font_preview')
        self.font_preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.font_preview.setWordWrap(True)
        preview_frame_layout.addStretch()
        preview_frame_layout.addWidget(self.font_preview)
        preview_frame_layout.addStretch()
        preview_layout.addWidget(self.preview_frame)
        self.preview_note_label = QtWidgets.QLabel(self.preview_group_box)
        self.preview_note_label.setObjectName('preview_note_label')
        self.preview_note_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_note_label)
        self.reset_button = QtWidgets.QPushButton(self.preview_group_box)
        self.reset_button.setObjectName('reset_button')
        preview_layout.addWidget(self.reset_button)
        preview_layout.addStretch()

    def _value_widgets(self):
        """All widgets that hold style values."""
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
            widget.valueChanged.connect(self._on_widget_changed)
        elif isinstance(widget, QtWidgets.QFontComboBox):
            widget.currentFontChanged.connect(self._on_widget_changed)
        elif isinstance(widget, QtWidgets.QComboBox):
            widget.currentIndexChanged.connect(self._on_widget_changed)
        elif isinstance(widget, QtWidgets.QCheckBox):
            widget.toggled.connect(self._on_widget_changed)
        elif isinstance(widget, ColorButton):
            widget.colorChanged.connect(self._on_widget_changed)
        elif isinstance(widget, QtWidgets.QToolButton):
            widget.toggled.connect(self._on_widget_changed)

    def _on_widget_changed(self, *args):
        if self._loading or not self._loaded:
            return
        self.store_style()
        self.update_display()
        self.valueChanged.emit()

    def retranslate_ui(self):
        self.preset_tabs.setTabText(0, translate('AlertsPlugin.StyleEditor', 'Type && Position'))
        self.preset_tabs.setTabText(1, translate('AlertsPlugin.StyleEditor', 'Typography'))
        self.preset_tabs.setTabText(2, translate('AlertsPlugin.StyleEditor', 'Background'))
        self.preset_tabs.setTabText(3, translate('AlertsPlugin.StyleEditor', 'Animation && Behaviour'))
        self.alert_type_label.setText(translate('AlertsPlugin.StyleEditor', 'Alert type:'))
        self.alert_type_combo_box.clear()
        self.alert_type_combo_box.addItems([
            translate('AlertsPlugin.StyleEditor', 'Banner (full width)'),
            translate('AlertsPlugin.StyleEditor', 'Toast'),
            translate('AlertsPlugin.StyleEditor', 'Lower third'),
            translate('AlertsPlugin.StyleEditor', 'Center overlay'),
            translate('AlertsPlugin.StyleEditor', 'Full screen'),
        ])
        self.zone_label.setText(translate('AlertsPlugin.StyleEditor', 'Screen position:'))
        for (zone_h, zone_v), button in self.zone_buttons.items():
            button.setToolTip(f'{zone_v} {zone_h}')
        self.offset_x_label.setText(translate('AlertsPlugin.StyleEditor', 'Horizontal offset:'))
        self.offset_y_label.setText(translate('AlertsPlugin.StyleEditor', 'Vertical offset:'))
        self.margin_x_label.setText(translate('AlertsPlugin.StyleEditor', 'Horizontal margin:'))
        self.margin_y_label.setText(translate('AlertsPlugin.StyleEditor', 'Vertical margin:'))
        self.font_label.setText(translate('AlertsPlugin.StyleEditor', 'Font name:'))
        self.font_size_label.setText(translate('AlertsPlugin.StyleEditor', 'Font size:'))
        self.font_size_spin_box.setSuffix(' {unit}'.format(unit=UiStrings().FontSizePtUnit))
        self.font_weight_label.setText(translate('AlertsPlugin.StyleEditor', 'Weight:'))
        self.font_weight_combo_box.clear()
        self.font_weight_combo_box.addItems([
            translate('AlertsPlugin.StyleEditor', 'Light (300)'),
            translate('AlertsPlugin.StyleEditor', 'Regular (400)'),
            translate('AlertsPlugin.StyleEditor', 'Medium (500)'),
            translate('AlertsPlugin.StyleEditor', 'Semi-bold (600)'),
            translate('AlertsPlugin.StyleEditor', 'Bold (700)'),
            translate('AlertsPlugin.StyleEditor', 'Extra-bold (800)'),
            translate('AlertsPlugin.StyleEditor', 'Black (900)'),
        ])
        self.font_color_label.setText(translate('AlertsPlugin.StyleEditor', 'Font color:'))
        self.letter_spacing_label.setText(translate('AlertsPlugin.StyleEditor', 'Letter spacing:'))
        self.line_spacing_label.setText(translate('AlertsPlugin.StyleEditor', 'Line spacing:'))
        self.text_opacity_label.setText(translate('AlertsPlugin.StyleEditor', 'Text opacity:'))
        self.shadow_check_box.setText(translate('AlertsPlugin.StyleEditor', 'Text shadow'))
        self.shadow_blur_label.setText(translate('AlertsPlugin.StyleEditor', 'Shadow blur:'))
        self.outline_check_box.setText(translate('AlertsPlugin.StyleEditor', 'Outline'))
        self.outline_width_label.setText(translate('AlertsPlugin.StyleEditor', 'Outline width:'))
        self.glow_check_box.setText(translate('AlertsPlugin.StyleEditor', 'Glow'))
        self.glow_radius_label.setText(translate('AlertsPlugin.StyleEditor', 'Glow radius:'))
        self.background_style_label.setText(translate('AlertsPlugin.StyleEditor', 'Style:'))
        self.background_style_combo_box.clear()
        self.background_style_combo_box.addItems([
            translate('AlertsPlugin.StyleEditor', 'Solid'),
            translate('AlertsPlugin.StyleEditor', 'Gradient'),
            translate('AlertsPlugin.StyleEditor', 'Glassmorphism (blur)'),
            translate('AlertsPlugin.StyleEditor', 'Semi-transparent'),
            translate('AlertsPlugin.StyleEditor', 'None'),
        ])
        self.background_color_label.setText(UiStrings().BackgroundColorColon)
        self.background_color2_label.setText(translate('AlertsPlugin.StyleEditor', 'Second gradient color:'))
        self.gradient_angle_label.setText(translate('AlertsPlugin.StyleEditor', 'Gradient angle:'))
        self.background_opacity_label.setText(translate('AlertsPlugin.StyleEditor', 'Background opacity:'))
        self.background_blur_label.setText(translate('AlertsPlugin.StyleEditor', 'Backdrop blur:'))
        self.shape_label.setText(translate('AlertsPlugin.StyleEditor', 'Shape:'))
        self.shape_combo_box.clear()
        self.shape_combo_box.addItems([
            translate('AlertsPlugin.StyleEditor', 'Full width'),
            translate('AlertsPlugin.StyleEditor', 'Rounded rectangle'),
            translate('AlertsPlugin.StyleEditor', 'Pill'),
            translate('AlertsPlugin.StyleEditor', 'Floating card'),
        ])
        self.corner_radius_label.setText(translate('AlertsPlugin.StyleEditor', 'Corner radius:'))
        self.padding_x_label.setText(translate('AlertsPlugin.StyleEditor', 'Horizontal padding:'))
        self.padding_y_label.setText(translate('AlertsPlugin.StyleEditor', 'Vertical padding:'))
        self.animation_in_label.setText(translate('AlertsPlugin.StyleEditor', 'Entrance:'))
        self.animation_in_combo_box.clear()
        self.animation_in_combo_box.addItems([
            translate('AlertsPlugin.StyleEditor', 'None'),
            translate('AlertsPlugin.StyleEditor', 'Fade'),
            translate('AlertsPlugin.StyleEditor', 'Slide down'),
            translate('AlertsPlugin.StyleEditor', 'Slide up'),
            translate('AlertsPlugin.StyleEditor', 'Slide in from right'),
            translate('AlertsPlugin.StyleEditor', 'Slide in from left'),
            translate('AlertsPlugin.StyleEditor', 'Zoom'),
            translate('AlertsPlugin.StyleEditor', 'Bounce'),
            translate('AlertsPlugin.StyleEditor', 'Flip'),
        ])
        self.animation_out_label.setText(translate('AlertsPlugin.StyleEditor', 'Exit:'))
        self.animation_out_combo_box.clear()
        self.animation_out_combo_box.addItems([
            translate('AlertsPlugin.StyleEditor', 'None'),
            translate('AlertsPlugin.StyleEditor', 'Fade'),
            translate('AlertsPlugin.StyleEditor', 'Slide down'),
            translate('AlertsPlugin.StyleEditor', 'Slide up'),
            translate('AlertsPlugin.StyleEditor', 'Slide out to left'),
            translate('AlertsPlugin.StyleEditor', 'Slide out to right'),
            translate('AlertsPlugin.StyleEditor', 'Zoom'),
            translate('AlertsPlugin.StyleEditor', 'Flip'),
        ])
        self.animation_speed_label.setText(translate('AlertsPlugin.StyleEditor', 'Speed:'))
        self.emphasis_label.setText(translate('AlertsPlugin.StyleEditor', 'Emphasis:'))
        self.emphasis_combo_box.clear()
        self.emphasis_combo_box.addItems([
            translate('AlertsPlugin.StyleEditor', 'None'),
            translate('AlertsPlugin.StyleEditor', 'Pulse'),
            translate('AlertsPlugin.StyleEditor', 'Flash'),
            translate('AlertsPlugin.StyleEditor', 'Shake'),
        ])
        self.scroll_check_box.setText(translate('AlertsPlugin.StyleEditor', 'Scroll text (marquee)'))
        self.repeat_label.setText(translate('AlertsPlugin.StyleEditor', 'Scroll passes:'))
        self.icon_check_box.setText(translate('AlertsPlugin.StyleEditor', 'Show icon'))
        self.icon_combo_box.clear()
        self.icon_combo_box.addItems([
            translate('AlertsPlugin.StyleEditor', 'Automatic (by priority)'),
            translate('AlertsPlugin.StyleEditor', 'None'),
            translate('AlertsPlugin.StyleEditor', 'Info circle'),
            translate('AlertsPlugin.StyleEditor', 'Bell'),
            translate('AlertsPlugin.StyleEditor', 'Warning triangle'),
            translate('AlertsPlugin.StyleEditor', 'Critical octagon'),
            translate('AlertsPlugin.StyleEditor', 'Megaphone'),
            translate('AlertsPlugin.StyleEditor', 'Clock'),
            translate('AlertsPlugin.StyleEditor', 'Heart'),
        ])
        self.timeout_label.setText(translate('AlertsPlugin.StyleEditor', 'Alert timeout:'))
        self.timeout_spin_box.setSuffix(' {unit}'.format(unit=UiStrings().Seconds))
        self.preview_group_box.setTitle(UiStrings().Preview)
        self.font_preview.setText(UiStrings().OpenLP)
        self.preview_note_label.setText(translate(
            'AlertsPlugin.StyleEditor',
            'The preview is approximate; blur, glow and animations only show on the display.'))
        self.reset_button.setText(translate('AlertsPlugin.StyleEditor', 'Reset to default'))

    def load_style(self, style):
        """
        Display the given style dict in the editor.

        :param style: A style dict (e.g. from a preset or a template).
        """
        self._loading = True
        try:
            self.alert_type_combo_box.setCurrentIndex(self._index_of(ALERT_TYPES, style['alertType']))
            zone_button = self.zone_buttons.get((style['zoneH'], style['zoneV']))
            if zone_button:
                zone_button.setChecked(True)
            self.offset_x_spin_box.setValue(int(style['offsetX']))
            self.offset_y_spin_box.setValue(int(style['offsetY']))
            self.margin_x_spin_box.setValue(int(style['marginX']))
            self.margin_y_spin_box.setValue(int(style['marginY']))
            font = QtGui.QFont()
            font.setFamily(style['fontFace'])
            self.font_combo_box.setCurrentFont(font)
            self.font_size_spin_box.setValue(int(style['fontSize']))
            weight = min(FONT_WEIGHTS, key=lambda candidate: abs(candidate - int(style['fontWeight'])))
            self.font_weight_combo_box.setCurrentIndex(FONT_WEIGHTS.index(weight))
            self.font_color_button.color = style['fontColor']
            self.letter_spacing_spin_box.setValue(float(style['letterSpacing']))
            self.line_spacing_spin_box.setValue(float(style['lineSpacing']))
            self.text_opacity_spin_box.setValue(int(style['textOpacity']))
            self.shadow_check_box.setChecked(bool(style['textShadowEnabled']))
            self.shadow_color_button.color = style['textShadowColor']
            self.shadow_blur_spin_box.setValue(int(style['textShadowBlur']))
            self.outline_check_box.setChecked(bool(style['outlineEnabled']))
            self.outline_color_button.color = style['outlineColor']
            self.outline_width_spin_box.setValue(int(style['outlineWidth']))
            self.glow_check_box.setChecked(bool(style['glowEnabled']))
            self.glow_color_button.color = style['glowColor']
            self.glow_radius_spin_box.setValue(int(style['glowRadius']))
            self.background_style_combo_box.setCurrentIndex(
                self._index_of(BACKGROUND_STYLES, style['backgroundStyle']))
            self.background_color_button.color = style['backgroundColor']
            self.background_color2_button.color = style['backgroundColor2']
            self.gradient_angle_spin_box.setValue(int(style['gradientAngle']))
            self.background_opacity_spin_box.setValue(int(style['backgroundOpacity']))
            self.background_blur_spin_box.setValue(int(style['backgroundBlur']))
            self.shape_combo_box.setCurrentIndex(self._index_of(SHAPES, style['shape']))
            self.corner_radius_spin_box.setValue(int(style['cornerRadius']))
            self.padding_x_spin_box.setValue(int(style['paddingX']))
            self.padding_y_spin_box.setValue(int(style['paddingY']))
            self.animation_in_combo_box.setCurrentIndex(self._index_of(ANIMATIONS_IN, style['animationIn']))
            self.animation_out_combo_box.setCurrentIndex(self._index_of(ANIMATIONS_OUT, style['animationOut']))
            self.animation_speed_spin_box.setValue(int(style['animationSpeed']))
            self.emphasis_combo_box.setCurrentIndex(self._index_of(EMPHASIS_EFFECTS, style['emphasis']))
            self.scroll_check_box.setChecked(bool(style['scroll']))
            self.repeat_spin_box.setValue(int(style['repeat']))
            self.icon_check_box.setChecked(bool(style['iconEnabled']))
            self.icon_combo_box.setCurrentIndex(self._index_of(ICONS, style['icon']))
            self.timeout_spin_box.setValue(int(style['timeout']))
        finally:
            self._loading = False
        self._style = dict(style)
        self._loaded = True
        self.update_display()

    def store_style(self):
        """
        Read the widgets back into a style dict.

        :return: The style dict (also kept as this widget's current style).
        """
        style = dict(self._style)
        style['alertType'] = ALERT_TYPES[self.alert_type_combo_box.currentIndex()]
        for (zone_h, zone_v), button in self.zone_buttons.items():
            if button.isChecked():
                style['zoneH'] = zone_h
                style['zoneV'] = zone_v
        style['offsetX'] = self.offset_x_spin_box.value()
        style['offsetY'] = self.offset_y_spin_box.value()
        style['marginX'] = self.margin_x_spin_box.value()
        style['marginY'] = self.margin_y_spin_box.value()
        style['fontFace'] = self.font_combo_box.currentFont().family()
        style['fontSize'] = self.font_size_spin_box.value()
        style['fontWeight'] = FONT_WEIGHTS[self.font_weight_combo_box.currentIndex()]
        style['fontColor'] = self.font_color_button.color
        style['letterSpacing'] = self.letter_spacing_spin_box.value()
        style['lineSpacing'] = round(self.line_spacing_spin_box.value(), 2)
        style['textOpacity'] = self.text_opacity_spin_box.value()
        style['textShadowEnabled'] = self.shadow_check_box.isChecked()
        style['textShadowColor'] = self.shadow_color_button.color
        style['textShadowBlur'] = self.shadow_blur_spin_box.value()
        style['outlineEnabled'] = self.outline_check_box.isChecked()
        style['outlineColor'] = self.outline_color_button.color
        style['outlineWidth'] = self.outline_width_spin_box.value()
        style['glowEnabled'] = self.glow_check_box.isChecked()
        style['glowColor'] = self.glow_color_button.color
        style['glowRadius'] = self.glow_radius_spin_box.value()
        style['backgroundStyle'] = BACKGROUND_STYLES[self.background_style_combo_box.currentIndex()]
        style['backgroundColor'] = self.background_color_button.color
        style['backgroundColor2'] = self.background_color2_button.color
        style['gradientAngle'] = self.gradient_angle_spin_box.value()
        style['backgroundOpacity'] = self.background_opacity_spin_box.value()
        style['backgroundBlur'] = self.background_blur_spin_box.value()
        style['shape'] = SHAPES[self.shape_combo_box.currentIndex()]
        style['cornerRadius'] = self.corner_radius_spin_box.value()
        style['paddingX'] = self.padding_x_spin_box.value()
        style['paddingY'] = self.padding_y_spin_box.value()
        style['animationIn'] = ANIMATIONS_IN[self.animation_in_combo_box.currentIndex()]
        style['animationOut'] = ANIMATIONS_OUT[self.animation_out_combo_box.currentIndex()]
        style['animationSpeed'] = self.animation_speed_spin_box.value()
        style['emphasis'] = EMPHASIS_EFFECTS[self.emphasis_combo_box.currentIndex()]
        style['scroll'] = self.scroll_check_box.isChecked()
        style['repeat'] = self.repeat_spin_box.value()
        style['iconEnabled'] = self.icon_check_box.isChecked()
        style['icon'] = ICONS[self.icon_combo_box.currentIndex()]
        style['timeout'] = self.timeout_spin_box.value()
        self._style = style
        return style

    @staticmethod
    def _index_of(values, value):
        """Index of value in values, falling back to 0."""
        try:
            return values.index(value)
        except ValueError:
            return 0

    def update_display(self):
        """
        Update the preview after changes have been made. The preview is a Qt
        approximation of the web rendering: font, colors, radius and shape.
        """
        style = self._style
        font = QtGui.QFont()
        font.setFamily(style['fontFace'])
        font.setWeight(QtGui.QFont.Weight(int(style['fontWeight'])))
        font.setPointSize(max(8, min(28, int(style['fontSize']) // 2)))
        if style['letterSpacing']:
            font.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, float(style['letterSpacing']) / 2)
        self.font_preview.setFont(font)
        radius = 0
        if style['shape'] == 'pill':
            radius = 22
        elif style['shape'] in ('rounded', 'card'):
            radius = min(22, int(style['cornerRadius']))
        opacity = max(0, min(100, int(style['backgroundOpacity'])))
        alpha = int(opacity * 255 / 100)
        base_color = QtGui.QColor(style['backgroundColor'])
        base_color.setAlpha(alpha)
        if style['backgroundStyle'] == 'gradient':
            second_color = QtGui.QColor(style['backgroundColor2'])
            second_color.setAlpha(alpha)
            background = ('qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {start}, stop:1 {stop})'
                          .format(start=base_color.name(QtGui.QColor.NameFormat.HexArgb),
                                  stop=second_color.name(QtGui.QColor.NameFormat.HexArgb)))
        elif style['backgroundStyle'] == 'none':
            background = 'transparent'
        else:
            background = base_color.name(QtGui.QColor.NameFormat.HexArgb)
        self.font_preview.setStyleSheet(
            'QLabel {{ background: {background}; color: {color}; border-radius: {radius}px; '
            'padding: {pad_y}px {pad_x}px; }}'.format(
                background=background, color=style['fontColor'], radius=radius,
                pad_x=min(40, int(style['paddingX']) // 2), pad_y=min(24, int(style['paddingY']) // 2)))
