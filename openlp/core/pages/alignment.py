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
The :mod:`~openlp.core.pages.alignment` module contains the alignment page used in the theme wizard
"""
from PySide6 import QtCore, QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.lib.theme import HorizontalType, VerticalType, TransitionType, TransitionSpeed, TransitionDirection
from openlp.core.lib.ui import create_halign_selection_widgets, create_valign_selection_widgets
from openlp.core.pages import GridLayoutPage
from openlp.core.widgets.labels import FormLabel


class AlignmentTransitionsPage(GridLayoutPage):
    """
    A widget containing the alignment and transitions options
    """
    changed = QtCore.Signal()

    def setup_ui(self):
        """
        Set up the UI
        """
        # Alignment
        self.main_alignment_group_box = QtWidgets.QGroupBox(self)
        self.main_alignment_group_box.setObjectName('main_alignment_group_box')
        self.main_alignment_layout = QtWidgets.QGridLayout(self.main_alignment_group_box)
        self.main_alignment_layout.setObjectName('main_alignment_layout')
        self.horizontal_label, self.horizontal_combo_box = create_halign_selection_widgets(self)
        self.horizontal_label.setObjectName('horizontal_label')
        self.main_alignment_layout.addWidget(self.horizontal_label, 0, 0)
        self.horizontal_combo_box.setObjectName('horizontal_combo_box')
        self.main_alignment_layout.addWidget(self.horizontal_combo_box, 0, 1)
        self.vertical_label, self.vertical_combo_box = create_valign_selection_widgets(self)
        self.vertical_label.setObjectName('vertical_label')
        self.main_alignment_layout.addWidget(self.vertical_label, 1, 0)
        self.vertical_combo_box.setObjectName('vertical_combo_box')
        self.main_alignment_layout.addWidget(self.vertical_combo_box, 1, 1)
        self.layout.addWidget(self.main_alignment_group_box, 0, 0, 1, 2)
        # Footer alignment
        self.footer_alignment_group_box = QtWidgets.QGroupBox(self)
        self.footer_alignment_group_box.setObjectName('footer_alignment_group_box')
        self.footer_alignment_layout = QtWidgets.QGridLayout(self.footer_alignment_group_box)
        self.footer_alignment_layout.setObjectName('footer_alignment_layout')
        self.footer_horizontal_label, self.footer_horizontal_combo_box = create_halign_selection_widgets(self)
        self.footer_horizontal_label.setObjectName('footer_horizontal_label')
        self.footer_alignment_layout.addWidget(self.footer_horizontal_label, 0, 0)
        self.footer_horizontal_combo_box.setObjectName('footer_horizontal_combo_box')
        self.footer_alignment_layout.addWidget(self.footer_horizontal_combo_box, 0, 1)
        self.footer_vertical_label, self.footer_vertical_combo_box = create_valign_selection_widgets(self)
        self.footer_vertical_label.setObjectName('footer_vertical_label')
        self.footer_alignment_layout.addWidget(self.footer_vertical_label, 1, 0)
        self.footer_vertical_combo_box.setObjectName('footer_vertical_combo_box')
        self.footer_alignment_layout.addWidget(self.footer_vertical_combo_box, 1, 1)
        self.layout.addWidget(self.footer_alignment_group_box, 0, 2, 1, 2)
        # Line
        self.line = QtWidgets.QFrame(self)
        self.line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line.setObjectName('line')
        self.layout.addWidget(self.line, 1, 0, 1, 4)
        # Transitions
        self.transitions_enabled_check_box = QtWidgets.QCheckBox(self)
        self.transitions_enabled_check_box.setObjectName('transitions_enabled_check_box')
        self.layout.addWidget(self.transitions_enabled_check_box, 2, 1)
        self.transition_effect_label = FormLabel(self)
        self.transition_effect_label.setObjectName('transition_effect_label')
        self.layout.addWidget(self.transition_effect_label, 3, 0)
        self.transition_effect_combo_box = QtWidgets.QComboBox(self)
        self.transition_effect_combo_box.setObjectName('transition_effect_combo_box')
        self.transition_effect_combo_box.addItems(['', '', '', '', ''])
        self.layout.addWidget(self.transition_effect_combo_box, 3, 1)
        self.transition_speed_label = FormLabel(self)
        self.transition_speed_label.setObjectName('transition_speed_label')
        self.layout.addWidget(self.transition_speed_label, 4, 0)
        self.transition_speed_combo_box = QtWidgets.QComboBox(self)
        self.transition_speed_combo_box.setObjectName('transition_speed_combo_box')
        self.transition_speed_combo_box.addItems(['', '', ''])
        self.layout.addWidget(self.transition_speed_combo_box, 4, 1)
        self.transition_direction_label = FormLabel(self)
        self.transition_direction_label.setObjectName('transition_direction_label')
        self.layout.addWidget(self.transition_direction_label, 3, 2)
        self.transition_direction_combo_box = QtWidgets.QComboBox(self)
        self.transition_direction_combo_box.setObjectName('transition_direction_combo_box')
        self.transition_direction_combo_box.addItems(['', ''])
        self.layout.addWidget(self.transition_direction_combo_box, 3, 3)
        self.transition_reverse_check_box = QtWidgets.QCheckBox(self)
        self.transition_reverse_check_box.setObjectName('transition_reverse_check_box')
        self.layout.addWidget(self.transition_reverse_check_box, 4, 3)
        # Connect slots
        self.transitions_enabled_check_box.toggled.connect(self._on_transition_enabled_changed)
        # Notify listeners (e.g. the live theme preview) whenever an alignment or transition setting changes.
        self.horizontal_combo_box.currentIndexChanged.connect(self.changed)
        self.vertical_combo_box.currentIndexChanged.connect(self.changed)
        self.footer_horizontal_combo_box.currentIndexChanged.connect(self.changed)
        self.footer_vertical_combo_box.currentIndexChanged.connect(self.changed)
        self.transitions_enabled_check_box.toggled.connect(self.changed)
        self.transition_effect_combo_box.currentIndexChanged.connect(self.changed)
        self.transition_speed_combo_box.currentIndexChanged.connect(self.changed)
        self.transition_direction_combo_box.currentIndexChanged.connect(self.changed)
        self.transition_reverse_check_box.toggled.connect(self.changed)

    def retranslate_ui(self):
        """
        Translate the widgets
        """
        self.main_alignment_group_box.setTitle(translate('OpenLP.ThemeWizard', '&Main Area'))
        self.footer_alignment_group_box.setTitle(translate('OpenLP.ThemeWizard', '&Footer Area'))
        self.transitions_enabled_check_box.setText(translate('OpenLP.ThemeWizard', 'Enable transitions'))
        self.transition_effect_label.setText(translate('OpenLP.ThemeWizard', 'Effect:'))
        self.transition_effect_combo_box.setItemText(TransitionType.Fade, translate('OpenLP.ThemeWizard', 'Fade'))
        self.transition_effect_combo_box.setItemText(TransitionType.Slide, translate('OpenLP.ThemeWizard', 'Slide'))
        self.transition_effect_combo_box.setItemText(TransitionType.Concave, translate('OpenLP.ThemeWizard', 'Concave'))
        self.transition_effect_combo_box.setItemText(TransitionType.Convex, translate('OpenLP.ThemeWizard', 'Convex'))
        self.transition_effect_combo_box.setItemText(TransitionType.Zoom, translate('OpenLP.ThemeWizard', 'Zoom'))
        self.transition_speed_label.setText(translate('OpenLP.ThemeWizard', 'Speed:'))
        self.transition_speed_combo_box.setItemText(TransitionSpeed.Normal, translate('OpenLP.ThemeWizard', 'Normal'))
        self.transition_speed_combo_box.setItemText(TransitionSpeed.Fast, translate('OpenLP.ThemeWizard', 'Fast'))
        self.transition_speed_combo_box.setItemText(TransitionSpeed.Slow, translate('OpenLP.ThemeWizard', 'Slow'))
        self.transition_direction_label.setText(translate('OpenLP.ThemeWizard', 'Direction:'))
        self.transition_direction_combo_box.setItemText(TransitionDirection.Horizontal, translate('OpenLP.ThemeWizard',
                                                                                                  'Horizontal'))
        self.transition_direction_combo_box.setItemText(TransitionDirection.Vertical, translate('OpenLP.ThemeWizard',
                                                                                                'Vertical'))
        self.transition_reverse_check_box.setText(translate('OpenLP.ThemeWizard', 'Reverse'))

    def _on_transition_enabled_changed(self, value):
        """
        Update the UI widgets when the transition is enabled or disabled
        """
        self.transition_effect_label.setEnabled(value)
        self.transition_effect_combo_box.setEnabled(value)
        self.transition_speed_label.setEnabled(value)
        self.transition_speed_combo_box.setEnabled(value)
        self.transition_direction_combo_box.setEnabled(value)
        self.transition_direction_label.setEnabled(value)
        self.transition_reverse_check_box.setEnabled(value)

    @property
    def horizontal_align(self):
        return self.horizontal_combo_box.currentIndex()

    @horizontal_align.setter
    def horizontal_align(self, value):
        if isinstance(value, str):
            self.horizontal_combo_box.setCurrentIndex(HorizontalType.from_string(value))
        elif isinstance(value, int):
            self.horizontal_combo_box.setCurrentIndex(value)
        else:
            raise TypeError('horizontal_align must either be a string or an int')

    @property
    def vertical_align(self):
        return self.vertical_combo_box.currentIndex()

    @vertical_align.setter
    def vertical_align(self, value):
        if isinstance(value, str):
            self.vertical_combo_box.setCurrentIndex(VerticalType.from_string(value))
        elif isinstance(value, int):
            self.vertical_combo_box.setCurrentIndex(value)
        else:
            raise TypeError('vertical_align must either be a string or an int')

    @property
    def horizontal_align_footer(self):
        return self.footer_horizontal_combo_box.currentIndex()

    @horizontal_align_footer.setter
    def horizontal_align_footer(self, value):
        if isinstance(value, str):
            self.footer_horizontal_combo_box.setCurrentIndex(HorizontalType.from_string(value))
        elif isinstance(value, int):
            self.footer_horizontal_combo_box.setCurrentIndex(value)
        else:
            raise TypeError('horizontal_align_footer must either be a string or an int')

    @property
    def vertical_align_footer(self):
        return self.footer_vertical_combo_box.currentIndex()

    @vertical_align_footer.setter
    def vertical_align_footer(self, value):
        if isinstance(value, str):
            self.footer_vertical_combo_box.setCurrentIndex(VerticalType.from_string(value))
        elif isinstance(value, int):
            self.footer_vertical_combo_box.setCurrentIndex(value)
        else:
            raise TypeError('vertical_align_footer must either be a string or an int')

    @property
    def is_transition_enabled(self):
        return self.transitions_enabled_check_box.isChecked()

    @is_transition_enabled.setter
    def is_transition_enabled(self, value):
        self.transitions_enabled_check_box.setChecked(value)

    @property
    def transition_type(self):
        return self.transition_effect_combo_box.currentIndex()

    @transition_type.setter
    def transition_type(self, value):
        if isinstance(value, str):
            self.transition_effect_combo_box.setCurrentIndex(TransitionType.from_string(value))
        elif isinstance(value, int):
            self.transition_effect_combo_box.setCurrentIndex(value)
        else:
            raise TypeError('transition_type must either be a string or an int')

    @property
    def transition_speed(self):
        return self.transition_speed_combo_box.currentIndex()

    @transition_speed.setter
    def transition_speed(self, value):
        if isinstance(value, str):
            self.transition_speed_combo_box.setCurrentIndex(TransitionSpeed.from_string(value))
        elif isinstance(value, int):
            self.transition_speed_combo_box.setCurrentIndex(value)
        else:
            raise TypeError('transition_speed must either be a string or an int')

    @property
    def transition_direction(self):
        return self.transition_direction_combo_box.currentIndex()

    @transition_direction.setter
    def transition_direction(self, value):
        if isinstance(value, str):
            self.transition_direction_combo_box.setCurrentIndex(TransitionDirection.from_string(value))
        elif isinstance(value, int):
            self.transition_direction_combo_box.setCurrentIndex(value)
        else:
            raise TypeError('transition_direction must either be a string or an int')

    @property
    def is_transition_reverse_enabled(self):
        return self.transition_reverse_check_box.isChecked()

    @is_transition_reverse_enabled.setter
    def is_transition_reverse_enabled(self, value):
        self.transition_reverse_check_box.setChecked(value)
