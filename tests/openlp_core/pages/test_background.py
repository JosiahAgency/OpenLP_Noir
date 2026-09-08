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
Package to test the openlp.core.pages.background package.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from openlp.core.lib.theme import BackgroundType, BackgroundGradientType
from openlp.core.pages.background import BackgroundPage


def test_init_(settings):
    """
    Test the initialisation of BackgroundPage
    """
    # GIVEN: The BackgroundPage class
    # WHEN: Initialising BackgroundPage
    # THEN: We should have an instance of the widget with no errors
    BackgroundPage()


def test_on_background_type_index_changed(settings):
    """
    Test the _on_background_type_index_changed() slot
    """
    # GIVEN: And instance of BackgroundPage and some mock widgets
    page = BackgroundPage()
    page.color_widgets = [MagicMock()]
    page.gradient_widgets = [MagicMock()]

    # WHEN: _on_background_type_index_changed
    page._on_background_type_index_changed(1)

    # THEN: The correct widgets should be visible
    page.color_widgets[0].hide.assert_called_once()
    page.gradient_widgets[0].hide.assert_called_once()
    page.gradient_widgets[0].show.assert_called_once()


def test_get_background_type(settings):
    """
    Test the background_type getter
    """
    # GIVEN: A BackgroundPage instance with the combobox set to index 1
    page = BackgroundPage()
    page.background_combo_box.setCurrentIndex(1)

    # WHEN: The property is accessed
    result = page.background_type

    # THEN: The result should be correct
    assert result == 'gradient'


def test_set_background_type_int(settings):
    """
    Test the background_type setter with an int
    """
    # GIVEN: A BackgroundPage instance
    page = BackgroundPage()

    # WHEN: The property is set
    page.background_type = BackgroundType.Image

    # THEN: The combobox should be correct
    assert page.background_combo_box.currentIndex() == 2


def test_set_background_type_str(settings):
    """
    Test the background_type setter with a str
    """
    # GIVEN: A BackgroundPage instance
    page = BackgroundPage()

    # WHEN: The property is set
    page.background_type = BackgroundType.to_string(BackgroundType.Gradient)

    # THEN: The combobox should be correct
    assert page.background_combo_box.currentIndex() == 1


def test_set_background_type_exception(settings):
    """
    Test the background_type setter with something other than a str or int
    """
    # GIVEN: A BackgroundPage instance
    page = BackgroundPage()

    # WHEN: The property is set
    # THEN: An exception is raised
    with pytest.raises(TypeError, match='background_type must either be a string or an int'):
        page.background_type = []


def test_get_color(settings):
    """
    Test the color getter
    """
    # GIVEN: A BackgroundPage instance with the color button set to #f0f
    page = BackgroundPage()
    page.color_button.color = '#f0f'

    # WHEN: The property is accessed
    result = page.color

    # THEN: The result should be correct
    assert result == '#f0f'


def test_set_color(settings):
    """
    Test the color setter
    """
    # GIVEN: A BackgroundPage instance
    page = BackgroundPage()

    # WHEN: The property is set
    page.color = '#0f0'

    # THEN: The result should be correct
    assert page.color_button.color == '#0f0'


def test_get_gradient_type(settings):
    """
    Test the gradient_type getter
    """
    # GIVEN: A BackgroundPage instance with the combobox set to index 1
    page = BackgroundPage()
    page.gradient_combo_box.setCurrentIndex(1)

    # WHEN: The property is accessed
    result = page.gradient_type

    # THEN: The result should be correct
    assert result == 'vertical'


def test_set_gradient_type_int(settings):
    """
    Test the gradient_type setter with an int
    """
    # GIVEN: A BackgroundPage instance
    page = BackgroundPage()

    # WHEN: The property is set
    page.gradient_type = BackgroundGradientType.Horizontal

    # THEN: The combobox should be correct
    assert page.gradient_combo_box.currentIndex() == 0


def test_set_gradient_type_str(settings):
    """
    Test the gradient_type setter with a str
    """
    # GIVEN: A BackgroundPage instance
    page = BackgroundPage()

    # WHEN: The property is set
    page.gradient_type = BackgroundGradientType.to_string(BackgroundGradientType.Circular)

    # THEN: The combobox should be correct
    assert page.gradient_combo_box.currentIndex() == 2


def test_set_gradient_type_exception(settings):
    """
    Test the gradient_type setter with something other than a str or int
    """
    # GIVEN: A BackgroundPage instance
    page = BackgroundPage()

    # WHEN: The property is set
    # THEN: An exception is raised
    with pytest.raises(TypeError, match='gradient_type must either be a string or an int'):
        page.gradient_type = []


def test_get_gradient_start(settings):
    """
    Test the gradient_start getter
    """
    # GIVEN: A BackgroundPage instance with the gradient_start button set to #f0f
    page = BackgroundPage()
    page.gradient_start_button.color = '#f0f'

    # WHEN: The property is accessed
    result = page.gradient_start

    # THEN: The result should be correct
    assert result == '#f0f'


def test_set_gradient_start(settings):
    """
    Test the gradient_start setter
    """
    # GIVEN: A BackgroundPage instance
    page = BackgroundPage()

    # WHEN: The property is set
    page.gradient_start = '#0f0'

    # THEN: The result should be correct
    assert page.gradient_start_button.color == '#0f0'


def test_get_gradient_end(settings):
    """
    Test the gradient_end getter
    """
    # GIVEN: A BackgroundPage instance with the gradient_end button set to #f0f
    page = BackgroundPage()
    page.gradient_end_button.color = '#f0f'

    # WHEN: The property is accessed
    result = page.gradient_end

    # THEN: The result should be correct
    assert result == '#f0f'


def test_set_gradient_end(settings):
    """
    Test the gradient_end setter
    """
    # GIVEN: A BackgroundPage instance
    page = BackgroundPage()

    # WHEN: The property is set
    page.gradient_end = '#0f0'

    # THEN: The result should be correct
    assert page.gradient_end_button.color == '#0f0'


def test_get_image_color(settings):
    """
    Test the image_color getter
    """
    # GIVEN: A BackgroundPage instance with the image_color button set to #f0f
    page = BackgroundPage()
    page.image_color_button.color = '#f0f'

    # WHEN: The property is accessed
    result = page.image_color

    # THEN: The result should be correct
    assert result == '#f0f'


def test_set_image_color(settings):
    """
    Test the image_color setter
    """
    # GIVEN: A BackgroundPage instance
    page = BackgroundPage()

    # WHEN: The property is set
    page.image_color = '#0f0'

    # THEN: The result should be correct
    assert page.image_color_button.color == '#0f0'


def test_get_image_path(settings):
    """
    Test the image_path getter
    """
    # GIVEN: A BackgroundPage instance with the image_path edit set to a path
    page = BackgroundPage()
    page.image_path_edit.path = Path('.')

    # WHEN: The property is accessed
    result = page.image_path

    # THEN: The result should be correct
    assert result == Path('.')


def test_set_image_path(settings):
    """
    Test the image_path setter
    """
    # GIVEN: A BackgroundPage instance
    page = BackgroundPage()

    # WHEN: The property is set
    page.image_path = Path('openlp')

    # THEN: The result should be correct
    assert page.image_path_edit.path == Path('openlp')


def test_get_video_color(settings):
    """
    Test the video_color getter
    """
    # GIVEN: A BackgroundPage instance with the video_color button set to #f0f
    page = BackgroundPage()
    page.video_color_button.color = '#f0f'

    # WHEN: The property is accessed
    result = page.video_color

    # THEN: The result should be correct
    assert result == '#f0f'


def test_set_video_color(settings):
    """
    Test the video_color setter
    """
    # GIVEN: A BackgroundPage instance
    page = BackgroundPage()

    # WHEN: The property is set
    page.video_color = '#0f0'

    # THEN: The result should be correct
    assert page.video_color_button.color == '#0f0'


def test_get_video_path(settings):
    """
    Test the video_path getter
    """
    # GIVEN: A BackgroundPage instance with the video_path edit set to a path
    page = BackgroundPage()
    page.video_path_edit.path = Path('.')

    # WHEN: The property is accessed
    result = page.video_path

    # THEN: The result should be correct
    assert result == Path('.')


def test_set_video_path(settings):
    """
    Test the video_path setter
    """
    # GIVEN: A BackgroundPage instance
    page = BackgroundPage()

    # WHEN: The property is set
    page.video_path = Path('openlp')

    # THEN: The result should be correct
    assert page.video_path_edit.path == Path('openlp')


def test_get_stream_color(settings):
    """
    Test the stream_color getter
    """
    # GIVEN: A BackgroundPage instance with the stream_color edit set to a path
    page = BackgroundPage()
    page.stream_color_button.color = '#000'

    # WHEN: The property is accessed
    result = page.stream_color

    # THEN: The result should be correct
    assert result == '#000'


def test_set_stream_color(settings):
    """
    Test the stream_color setter
    """
    # GIVEN: A BackgroundPage instance
    page = BackgroundPage()

    # WHEN: The property is set
    page.stream_color = '#fff'

    # THEN: The result should be correct
    assert page.stream_color_button.color == '#fff'


def test_get_stream_mrl(settings):
    """
    Test the stream_mrl getter
    """
    # GIVEN: A BackgroundPage instance with the stream_mrl edit set to a path
    page = BackgroundPage()
    page.stream_lineedit.setText('devicestream:/dev/vid2')

    # WHEN: The property is accessed
    result = page.stream_mrl

    # THEN: The result should be correct
    assert result == 'devicestream:/dev/vid2'


def test_set_stream_mrl(settings):
    """
    Test the stream_mrl setter
    """
    # GIVEN: A BackgroundPage instance
    page = BackgroundPage()

    # WHEN: The property is set
    page.stream_mrl = 'devicestream:/dev/vid3'

    # THEN: The result should be correct
    assert page.stream_lineedit.text() == 'devicestream:/dev/vid3'


@patch('openlp.plugins.media.forms.streamselectorform.StreamSelectorForm')
def test_on_device_stream_select_button_triggered(MockStreamSelectorForm, settings):
    """Test the device streaming selection

    NOTE: Due to the inline import statement, the source of the form needs to be mocked, not the imported object
    """
    # GIVEN: A BackgroundPage object and some mocks
    mocked_stream_selector_form = MagicMock()
    MockStreamSelectorForm.return_value = mocked_stream_selector_form
    page = BackgroundPage()
    page.stream_lineedit = MagicMock(**{'text.return_value': 'devicestream:/dev/vid0'})

    # WHEN: _on_device_stream_select_button_triggered() is called
    page._on_device_stream_select_button_triggered()

    # THEN: The error should have been shown
    MockStreamSelectorForm.assert_called_once_with(page, page.set_stream, True)
    mocked_stream_selector_form.set_mrl.assert_called_once_with('devicestream:/dev/vid0')
    mocked_stream_selector_form.exec.assert_called_once_with()


@patch('openlp.plugins.media.forms.networkstreamselectorform.NetworkStreamSelectorForm')
def test_on_network_stream_select_button_triggered(MockStreamSelectorForm, settings):
    """Test the network streaming selection

    NOTE: Due to the inline import statement, the source of the form needs to be mocked, not the imported object
    """
    # GIVEN: A BackgroundPage object and some mocks
    mocked_stream_selector_form = MagicMock()
    MockStreamSelectorForm.return_value = mocked_stream_selector_form
    page = BackgroundPage()
    page.stream_lineedit = MagicMock(**{'text.return_value': 'networkstream:/dev/vid0'})

    # WHEN: _on_network_stream_select_button_triggered() is called
    page._on_network_stream_select_button_triggered()

    # THEN: The error should have been shown
    MockStreamSelectorForm.assert_called_once_with(page, page.set_stream, True)
    mocked_stream_selector_form.set_mrl.assert_called_once_with('networkstream:/dev/vid0')
    mocked_stream_selector_form.exec.assert_called_once_with()


def test_set_stream(settings):
    """Test the set_stream() method"""
    # GIVEN: A BackgroundPage object with a mocked stream_lineedit object
    page = BackgroundPage()
    page.stream_lineedit = MagicMock()

    # WHEN: set_stream is called
    page.set_stream('devicestream:/dev/vid1')

    # THEN: The line edit should have been updated
    page.stream_lineedit.setText.assert_called_once_with('devicestream:/dev/vid1')


def test_changed_signal_emitted_on_background_type_change(settings):
    """
    Test that the changed signal fires when the background type combo box changes
    """
    # GIVEN: A BackgroundPage instance with a slot connected to the changed signal
    page = BackgroundPage()
    mocked_slot = MagicMock()
    page.changed.connect(mocked_slot)

    # WHEN: The background type is changed
    page.background_combo_box.setCurrentIndex(BackgroundType.Gradient)

    # THEN: The changed signal should have fired
    mocked_slot.assert_called_once()


def test_changed_signal_emitted_on_color_change(settings):
    """
    Test that the changed signal fires when a color button changes
    """
    # GIVEN: A BackgroundPage instance with a slot connected to the changed signal
    page = BackgroundPage()
    mocked_slot = MagicMock()
    page.changed.connect(mocked_slot)

    # WHEN: The solid color is changed by the user (via the color dialog, which emits colorChanged)
    page.color_button.colorChanged.emit('#ff0000')

    # THEN: The changed signal should have fired
    mocked_slot.assert_called_once()


def test_changed_signal_emitted_on_image_path_change(settings, tmp_path):
    """
    Test that the changed signal fires when the background image path changes
    """
    # GIVEN: A BackgroundPage instance with a slot connected to the changed signal
    page = BackgroundPage()
    mocked_slot = MagicMock()
    page.changed.connect(mocked_slot)

    # WHEN: The image path is changed by the user (which emits pathChanged)
    page.image_path_edit.pathChanged.emit(tmp_path / 'background.png')

    # THEN: The changed signal should have fired
    mocked_slot.assert_called_once()
