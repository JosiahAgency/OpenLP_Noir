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
The :mod:`~openlp.core.pages.background` module contains the background page used in the theme wizard
"""
from PySide6 import QtCore, QtWidgets

from openlp.core.common import get_images_filter
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.lib.theme import BackgroundGradientType, BackgroundType
from openlp.core.pages import GridLayoutPage
from openlp.core.ui.icons import UiIcons
from openlp.core.ui.media import get_supported_media_suffix
from openlp.core.widgets.buttons import ColorButton
from openlp.core.widgets.edits import PathEdit
from openlp.core.widgets.labels import FormLabel


class BackgroundPage(GridLayoutPage):
    """
    A background selection widget
    """
    Color = 'color'
    Gradient = 'gradient'
    Image = 'image'
    Video = 'video'
    Stream = 'stream'

    changed = QtCore.Signal()

    def setup_ui(self):
        """
        Set up the ui
        """
        # background type
        self.background_label = FormLabel(self)
        self.background_label.setObjectName('background_label')
        self.layout.addWidget(self.background_label, 0, 0)
        self.background_combo_box = QtWidgets.QComboBox(self)
        self.background_combo_box.addItems(['', '', '', '', '', ''])
        self.background_combo_box.setObjectName('background_combo_box')
        self.layout.addWidget(self.background_combo_box, 0, 1, 1, 3)
        # color
        self.color_label = FormLabel(self)
        self.color_label.setObjectName('color_label')
        self.layout.addWidget(self.color_label, 1, 0)
        self.color_button = ColorButton(self)
        self.color_button.setObjectName('color_button')
        self.layout.addWidget(self.color_button, 1, 1)
        self.color_widgets = [self.color_label, self.color_button]
        # gradient
        self.gradient_type_label = FormLabel(self)
        self.gradient_type_label.setObjectName('gradient_type_label')
        self.layout.addWidget(self.gradient_type_label, 2, 0)
        self.gradient_combo_box = QtWidgets.QComboBox(self)
        self.gradient_combo_box.setObjectName('gradient_combo_box')
        self.gradient_combo_box.addItems(['', '', '', '', ''])
        self.layout.addWidget(self.gradient_combo_box, 2, 1, 1, 3)
        self.gradient_start_label = FormLabel(self)
        self.gradient_start_label.setObjectName('gradient_start_label')
        self.layout.addWidget(self.gradient_start_label, 3, 0)
        self.gradient_start_button = ColorButton(self)
        self.gradient_start_button.setObjectName('gradient_start_button')
        self.layout.addWidget(self.gradient_start_button, 3, 1)
        self.gradient_end_label = FormLabel(self)
        self.gradient_end_label.setObjectName('gradient_end_label')
        self.layout.addWidget(self.gradient_end_label, 3, 2)
        self.gradient_end_button = ColorButton(self)
        self.gradient_end_button.setObjectName('gradient_end_button')
        self.layout.addWidget(self.gradient_end_button, 3, 3)
        self.gradient_widgets = [self.gradient_type_label, self.gradient_combo_box, self.gradient_start_label,
                                 self.gradient_start_button, self.gradient_end_label, self.gradient_end_button]
        # image
        self.image_label = FormLabel(self)
        self.image_label.setObjectName('image_label')
        self.layout.addWidget(self.image_label, 4, 0)
        self.image_path_edit = PathEdit(self, dialog_caption=translate('OpenLP.ThemeWizard', 'Select Image'),
                                        show_revert=False)
        self.layout.addWidget(self.image_path_edit, 4, 1, 1, 3)
        self.image_color_label = FormLabel(self)
        self.image_color_label.setObjectName('image_color_label')
        self.layout.addWidget(self.image_color_label, 5, 0)
        self.image_color_button = ColorButton(self)
        self.image_color_button.color = '#000000'
        self.image_color_button.setObjectName('image_color_button')
        self.layout.addWidget(self.image_color_button, 5, 1)
        self.image_widgets = [self.image_label, self.image_path_edit, self.image_color_label, self.image_color_button]
        # video
        self.video_label = FormLabel(self)
        self.video_label.setObjectName('video_label')
        self.layout.addWidget(self.video_label, 6, 0)
        self.video_path_edit = PathEdit(self, dialog_caption=translate('OpenLP.ThemeWizard', 'Select Video'),
                                        show_revert=False)
        self.layout.addWidget(self.video_path_edit, 6, 1, 1, 3)
        self.video_color_label = FormLabel(self)
        self.video_color_label.setObjectName('video_color_label')
        self.layout.addWidget(self.video_color_label, 7, 0)
        self.video_color_button = ColorButton(self)
        self.video_color_button.color = '#000000'
        self.video_color_button.setObjectName('video_color_button')
        self.layout.addWidget(self.video_color_button, 7, 1)
        self.video_widgets = [self.video_label, self.video_path_edit, self.video_color_label, self.video_color_button]
        # streams
        self.stream_label = FormLabel(self)
        self.stream_label.setObjectName('stream_label')
        self.layout.addWidget(self.stream_label, 6, 0)
        self.stream_layout = QtWidgets.QHBoxLayout()
        self.stream_lineedit = QtWidgets.QLineEdit(self)
        self.stream_lineedit.setObjectName('stream_lineedit')
        self.stream_lineedit.setReadOnly(True)
        self.stream_layout.addWidget(self.stream_lineedit)
        # button to open select device stream form
        self.device_stream_select_button = QtWidgets.QToolButton(self)
        self.device_stream_select_button.setObjectName('device_stream_select_button')
        self.device_stream_select_button.setIcon(UiIcons().device_stream)
        self.stream_layout.addWidget(self.device_stream_select_button)
        # button to open select network stream form
        self.network_stream_select_button = QtWidgets.QToolButton(self)
        self.network_stream_select_button.setObjectName('network_stream_select_button')
        self.network_stream_select_button.setIcon(UiIcons().network_stream)
        self.stream_layout.addWidget(self.network_stream_select_button)
        self.layout.addLayout(self.stream_layout, 6, 1, 1, 3)
        self.stream_color_label = FormLabel(self)
        self.stream_color_label.setObjectName('stream_color_label')
        self.layout.addWidget(self.stream_color_label, 7, 0)
        self.stream_color_button = ColorButton(self)
        self.stream_color_button.color = '#000000'
        self.stream_color_button.setObjectName('stream_color_button')
        self.layout.addWidget(self.stream_color_button, 7, 1)
        self.stream_widgets = [self.stream_label, self.stream_lineedit, self.device_stream_select_button,
                               self.network_stream_select_button, self.stream_color_label, self.stream_color_button]
        # Force everything up
        self.layout_spacer = QtWidgets.QSpacerItem(1, 1)
        self.layout.addItem(self.layout_spacer, 8, 0, 1, 4)
        # Connect slots
        self.background_combo_box.currentIndexChanged.connect(self._on_background_type_index_changed)
        self.device_stream_select_button.clicked.connect(self._on_device_stream_select_button_triggered)
        self.network_stream_select_button.clicked.connect(self._on_network_stream_select_button_triggered)
        # Notify listeners (e.g. the live theme preview) whenever anything that affects the rendered
        # background changes.
        self.background_combo_box.currentIndexChanged.connect(self.changed)
        self.color_button.colorChanged.connect(self.changed)
        self.gradient_combo_box.currentIndexChanged.connect(self.changed)
        self.gradient_start_button.colorChanged.connect(self.changed)
        self.gradient_end_button.colorChanged.connect(self.changed)
        self.image_path_edit.pathChanged.connect(self.changed)
        self.image_color_button.colorChanged.connect(self.changed)
        self.video_path_edit.pathChanged.connect(self.changed)
        self.video_color_button.colorChanged.connect(self.changed)
        self.stream_lineedit.textChanged.connect(self.changed)
        self.stream_color_button.colorChanged.connect(self.changed)
        # Force the first set of widgets to show
        self._on_background_type_index_changed(0)

    def retranslate_ui(self):
        """
        Translate the text elements of the widget
        """
        self.background_label.setText(translate('OpenLP.ThemeWizard', 'Background type:'))
        self.background_combo_box.setItemText(BackgroundType.Solid, translate('OpenLP.ThemeWizard', 'Solid color'))
        self.background_combo_box.setItemText(BackgroundType.Gradient, translate('OpenLP.ThemeWizard', 'Gradient'))
        self.background_combo_box.setItemText(BackgroundType.Image, UiStrings().Image)
        self.background_combo_box.setItemText(BackgroundType.Video, UiStrings().Video)
        self.background_combo_box.setItemText(BackgroundType.Transparent,
                                              translate('OpenLP.ThemeWizard', 'Transparent'))
        self.background_combo_box.setItemText(BackgroundType.Stream,
                                              translate('OpenLP.ThemeWizard', 'Live stream'))
        self.color_label.setText(translate('OpenLP.ThemeWizard', 'Color:'))
        self.gradient_start_label.setText(translate('OpenLP.ThemeWizard', 'Starting color:'))
        self.gradient_end_label.setText(translate('OpenLP.ThemeWizard', 'Ending color:'))
        self.gradient_type_label.setText(translate('OpenLP.ThemeWizard', 'Gradient:'))
        self.gradient_combo_box.setItemText(BackgroundGradientType.Horizontal,
                                            translate('OpenLP.ThemeWizard', 'Horizontal'))
        self.gradient_combo_box.setItemText(BackgroundGradientType.Vertical,
                                            translate('OpenLP.ThemeWizard', 'Vertical'))
        self.gradient_combo_box.setItemText(BackgroundGradientType.Circular,
                                            translate('OpenLP.ThemeWizard', 'Circular'))
        self.gradient_combo_box.setItemText(BackgroundGradientType.LeftTop,
                                            translate('OpenLP.ThemeWizard', 'Top Left - Bottom Right'))
        self.gradient_combo_box.setItemText(BackgroundGradientType.LeftBottom,
                                            translate('OpenLP.ThemeWizard', 'Bottom Left - Top Right'))
        self.image_color_label.setText(translate('OpenLP.ThemeWizard', 'Background color:'))
        self.image_label.setText('{text}:'.format(text=UiStrings().Image))
        self.video_color_label.setText(translate('OpenLP.ThemeWizard', 'Background color:'))
        self.video_label.setText('{text}:'.format(text=UiStrings().Video))
        self.stream_color_label.setText(translate('OpenLP.ThemeWizard', 'Background color:'))
        self.stream_label.setText('{text}:'.format(text=UiStrings().LiveStream))
        self.image_path_edit.filters = \
            '{name};;{text} (*)'.format(name=get_images_filter(), text=UiStrings().AllFiles)
        _, video = get_supported_media_suffix()
        video_filter = '{trans} ({visible})'.format(trans=translate('OpenLP', 'Video Files'), visible=' '.join(video))
        self.video_path_edit.filters = '{video};;{ui} (*)'.format(video=video_filter, ui=UiStrings().AllFiles)

    def _on_background_type_index_changed(self, index):
        """
        Hide and show widgets based on index
        """
        widget_sets = [self.color_widgets, self.gradient_widgets, self.image_widgets, [], self.video_widgets,
                       self.stream_widgets]
        for widgets in widget_sets:
            for widget in widgets:
                widget.hide()
        if index < len(widget_sets):
            for widget in widget_sets[index]:
                widget.show()

    def _on_device_stream_select_button_triggered(self):
        """
        Open the Stream selection form.
        """
        from openlp.plugins.media.forms.streamselectorform import StreamSelectorForm

        stream_selector_form = StreamSelectorForm(self, self.set_stream, True)
        # prefill in the form any device stream already defined
        if self.stream_lineedit.text() and self.stream_lineedit.text().startswith('devicestream'):
            stream_selector_form.set_mrl(self.stream_lineedit.text())
        stream_selector_form.exec()
        del stream_selector_form

    def _on_network_stream_select_button_triggered(self):
        """
        Open the Stream selection form.
        """
        from openlp.plugins.media.forms.networkstreamselectorform import NetworkStreamSelectorForm
        stream_selector_form = NetworkStreamSelectorForm(self, self.set_stream, True)
        # prefill in the form any network stream already defined
        if self.stream_lineedit.text() and self.stream_lineedit.text().startswith('networkstream'):
            stream_selector_form.set_mrl(self.stream_lineedit.text())
        stream_selector_form.exec()
        del stream_selector_form

    def set_stream(self, stream_str):
        """
        callback method used to get the stream mrl and options
        """
        self.stream_lineedit.setText(stream_str)

    @property
    def background_type(self):
        return BackgroundType.to_string(self.background_combo_box.currentIndex())

    @background_type.setter
    def background_type(self, value):
        if isinstance(value, str):
            self.background_combo_box.setCurrentIndex(BackgroundType.from_string(value))
        elif isinstance(value, int):
            self.background_combo_box.setCurrentIndex(value)
        else:
            raise TypeError('background_type must either be a string or an int')

    @property
    def color(self):
        return self.color_button.color

    @color.setter
    def color(self, value):
        self.color_button.color = value

    @property
    def gradient_type(self):
        return BackgroundGradientType.to_string(self.gradient_combo_box.currentIndex())

    @gradient_type.setter
    def gradient_type(self, value):
        if isinstance(value, str):
            self.gradient_combo_box.setCurrentIndex(BackgroundGradientType.from_string(value))
        elif isinstance(value, int):
            self.gradient_combo_box.setCurrentIndex(value)
        else:
            raise TypeError('gradient_type must either be a string or an int')

    @property
    def gradient_start(self):
        return self.gradient_start_button.color

    @gradient_start.setter
    def gradient_start(self, value):
        self.gradient_start_button.color = value

    @property
    def gradient_end(self):
        return self.gradient_end_button.color

    @gradient_end.setter
    def gradient_end(self, value):
        self.gradient_end_button.color = value

    @property
    def image_color(self):
        return self.image_color_button.color

    @image_color.setter
    def image_color(self, value):
        self.image_color_button.color = value

    @property
    def image_path(self):
        return self.image_path_edit.path

    @image_path.setter
    def image_path(self, value):
        self.image_path_edit.path = value

    @property
    def video_color(self):
        return self.video_color_button.color

    @video_color.setter
    def video_color(self, value):
        self.video_color_button.color = value

    @property
    def video_path(self):
        return self.video_path_edit.path

    @video_path.setter
    def video_path(self, value):
        self.video_path_edit.path = value

    @property
    def stream_color(self):
        return self.stream_color_button.color

    @stream_color.setter
    def stream_color(self, value):
        self.stream_color_button.color = value

    @property
    def stream_mrl(self):
        return self.stream_lineedit.text()

    @stream_mrl.setter
    def stream_mrl(self, value):
        self.stream_lineedit.setText(value)
