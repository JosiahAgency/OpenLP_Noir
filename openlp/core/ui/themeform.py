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
The Theme wizard
"""
import logging

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common import is_not_image_file
from openlp.core.common.enum import ServiceItemType
from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.mixins import RegistryProperties
from openlp.core.common.registry import Registry
from openlp.core.lib.theme import BackgroundType
from openlp.core.lib.ui import critical_error_message_box
from openlp.core.ui.themelayoutform import ThemeLayoutForm
from openlp.core.ui.themewizard import Ui_ThemeWizard


log = logging.getLogger(__name__)


class ThemeForm(QtWidgets.QWizard, Ui_ThemeWizard, RegistryProperties):
    """
    This is the Theme Import Wizard, which allows easy creation and editing of
    OpenLP themes.
    """
    log.info('ThemeWizardForm loaded')

    def __init__(self, parent):
        """
        Instantiate the wizard, and run any extra setup we need to.

        :param parent: The QWidget-derived parent of the wizard.
        """
        super(ThemeForm, self).__init__(parent,
                                        QtCore.Qt.WindowType.WindowSystemMenuHint |
                                        QtCore.Qt.WindowType.WindowTitleHint |
                                        QtCore.Qt.WindowType.WindowCloseButtonHint)
        self._setup()

    def _setup(self):
        """
        Set up the class. This method is mocked out by the tests.
        """
        self.setup_ui(self)
        self.can_update_theme = True
        self.temp_background_filename = None
        self.theme_layout_form = ThemeLayoutForm(self)
        self.customButtonClicked.connect(self.on_custom_1_button_clicked)
        self.currentIdChanged.connect(self.on_current_id_changed)
        Registry().register_function('theme_line_count', self.update_lines_text)
        self.main_area_page.font_name_changed.connect(self.calculate_lines)
        self.main_area_page.font_size_changed.connect(self.calculate_lines)
        self.main_area_page.line_spacing_changed.connect(self.calculate_lines)
        self.main_area_page.letter_spacing_changed.connect(self.calculate_lines)
        self.main_area_page.is_outline_enabled_changed.connect(self.on_outline_toggled)
        self.main_area_page.outline_size_changed.connect(self.calculate_lines)
        self.main_area_page.is_shadow_enabled_changed.connect(self.on_shadow_toggled)
        self.main_area_page.shadow_size_changed.connect(self.calculate_lines)
        self.footer_area_page.font_name_changed.connect(self.calculate_lines)
        self.footer_area_page.font_size_changed.connect(self.calculate_lines)
        self.footer_area_page.wrap_changed.connect(self.calculate_lines)
        self.footer_area_page.line_spacing_changed.connect(self.calculate_lines)
        self.footer_area_page.letter_spacing_changed.connect(self.calculate_lines)
        self.setOption(QtWidgets.QWizard.WizardOption.HaveHelpButton, True)
        self.helpRequested.connect(self.provide_help)

    def provide_help(self):
        """
        Provide help within the wizard by opening the appropriate page of the openlp manual in the user's browser
        """
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://manual.openlp.org/themes.html"))

    def set_defaults(self):
        """
        Set up display at start of theme edit.
        """
        self.restart()
        self.set_background_page_values()
        self.set_main_area_page_values()
        self.set_footer_area_page_values()
        self.set_alignment_page_values()
        self.set_position_page_values()
        self.set_preview_page_values()

    def calculate_lines(self, *args):
        """
        Calculate the number of lines on a page by rendering text
        """
        # Do not trigger on start up
        if self.currentPage() != self.welcome_page:
            self.update_theme()
            self.theme_manager.generate_image(self.theme, True)

    def update_lines_text(self, lines):
        """
        Updates the lines on a page on the wizard
        :param lines: then number of lines to be displayed
        """
        self.main_line_count_label.setText(
            translate('OpenLP.ThemeForm', '(approximately %d lines per slide)') % int(lines))

    def resizeEvent(self, event=None):
        """
        Rescale the theme preview thumbnail on resize events.
        """
        if not event:
            event = QtGui.QResizeEvent(self.size(), self.size())
        QtWidgets.QWizard.resizeEvent(self, event)
        try:
            self.display_aspect_ratio = self.renderer.width() / self.renderer.height()
        except ZeroDivisionError:
            self.display_aspect_ratio = 1
        # Make sure we don't resize before the widgets are actually created
        if hasattr(self, 'preview_area_layout'):
            self.preview_area_layout.set_aspect_ratio(self.display_aspect_ratio)
            self.application.process_events()
            self.preview_box.set_scale(float(self.preview_box.width()) / self.renderer.width())

    def validateCurrentPage(self):
        """
        Validate the current page
        """
        if self.page(self.currentId()) == self.background_page:
            background_image = BackgroundType.to_string(BackgroundType.Image)
            background_video = BackgroundType.to_string(BackgroundType.Video)
            background_stream = BackgroundType.to_string(BackgroundType.Stream)
            if self.background_page.background_type == background_image and \
                    is_not_image_file(self.background_page.image_path):
                QtWidgets.QMessageBox.critical(self, translate('OpenLP.ThemeWizard', 'Background Image Empty'),
                                               translate('OpenLP.ThemeWizard', 'You have not selected a '
                                                         'background image. Please select one before continuing.'))
                return False
            elif self.background_page.background_type == background_video and \
                    not self.background_page.video_path:
                QtWidgets.QMessageBox.critical(self, translate('OpenLP.ThemeWizard', 'Background Video Empty'),
                                               translate('OpenLP.ThemeWizard', 'You have not selected a '
                                                         'background video. Please select one before continuing.'))
                return False
            elif self.background_page.background_type == background_stream and \
                    not self.background_page.stream_mrl.strip():
                QtWidgets.QMessageBox.critical(self, translate('OpenLP.ThemeWizard', 'Background Stream Empty'),
                                               translate('OpenLP.ThemeWizard', 'You have not selected a '
                                                         'background stream. Please select one before continuing.'))
                return False
            else:
                return True
        return True

    def on_current_id_changed(self, page_id):
        """
        Detects Page changes and updates as appropriate.
        :param page_id: current page number
        """
        enabled = self.page(page_id) == self.area_position_page
        self.setOption(QtWidgets.QWizard.WizardOption.HaveCustomButton1, enabled)
        if self.page(page_id) == self.preview_page:
            self.update_theme()
            self.resizeEvent()
            self.preview_box.clear_slides()
            self.preview_box.show()
            self.preview_box.generate_preview(self.theme, False, False)

    def on_custom_1_button_clicked(self, number):
        """
        Generate layout preview and display the form.
        """
        self.update_theme()
        width = self.renderer.width()
        height = self.renderer.height()
        pixmap = QtGui.QPixmap(width, height)
        pixmap.fill(QtCore.Qt.GlobalColor.white)
        paint = QtGui.QPainter(pixmap)
        paint.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.blue, 2))
        main_rect = QtCore.QRect(int(self.theme.font_main_x), int(self.theme.font_main_y),
                                 int(self.theme.font_main_width - 1), int(self.theme.font_main_height - 1))
        paint.drawRect(main_rect)
        paint.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.red, 2))
        footer_rect = QtCore.QRect(int(self.theme.font_footer_x), int(self.theme.font_footer_y),
                                   int(self.theme.font_footer_width - 1), int(self.theme.font_footer_height - 1))
        paint.drawRect(footer_rect)
        paint.end()
        self.theme_layout_form.exec(pixmap)

    def on_outline_toggled(self, is_enabled):
        """
        Change state as Outline check box changed
        """
        if self.can_update_theme:
            self.theme.font_main_outline = is_enabled
            self.calculate_lines()

    def on_shadow_toggled(self, is_enabled):
        """
        Change state as Shadow check box changed
        """
        if self.can_update_theme:
            self.theme.font_main_shadow = is_enabled
            self.calculate_lines()

    def exec(self, edit=False):
        """
        Run the wizard.
        """
        log.debug('Editing theme {name}'.format(name=self.theme.theme_name))
        self.temp_background_filename = self.theme.background_source
        self.can_update_theme = False
        self.set_defaults()
        self.can_update_theme = True
        self.theme_name_label.setVisible(not edit)
        self.theme_name_edit.setVisible(not edit)
        self.edit_mode = edit
        if edit:
            self.setWindowTitle(translate('OpenLP.ThemeWizard', 'Edit Theme - {name}'
                                          ).format(name=self.theme.theme_name))
            self.next()
        else:
            self.setWindowTitle(UiStrings().NewTheme)
        return QtWidgets.QWizard.exec(self)

    def initializePage(self, page_id):
        """
        Set up the pages for Initial run through dialog
        """
        log.debug('initializePage {page}'.format(page=page_id))
        wizard_page = self.page(page_id)
        if wizard_page == self.background_page:
            self.set_background_page_values()
        elif wizard_page == self.main_area_page:
            self.set_main_area_page_values()
        elif wizard_page == self.footer_area_page:
            self.set_footer_area_page_values()
        elif wizard_page == self.alignment_page:
            self.set_alignment_page_values()
        elif wizard_page == self.area_position_page:
            self.set_position_page_values()

    def set_background_page_values(self):
        """
        Handle the display and state of the Background page.
        """
        self.background_page.background_type = self.theme.background_type
        if self.theme.background_type == BackgroundType.to_string(BackgroundType.Solid):
            self.background_page.color = self.theme.background_color
        elif self.theme.background_type == BackgroundType.to_string(BackgroundType.Gradient):
            self.background_page.gradient_start = self.theme.background_start_color
            self.background_page.gradient_end = self.theme.background_end_color
            self.background_page.gradient_type = self.theme.background_direction
        elif self.theme.background_type == BackgroundType.to_string(BackgroundType.Image):
            self.background_page.image_color = self.theme.background_border_color
            if self.theme.background_source and self.theme.background_source.exists():
                self.background_page.image_path = self.theme.background_source
            else:
                self.background_page.image_path = self.theme.background_filename
        elif self.theme.background_type == BackgroundType.to_string(BackgroundType.Video):
            self.background_page.video_color = self.theme.background_border_color
            if self.theme.background_source and self.theme.background_source.exists():
                self.background_page.video_path = self.theme.background_source
            else:
                self.background_page.video_path = self.theme.background_filename
        elif self.theme.background_type == BackgroundType.to_string(BackgroundType.Stream):
            self.background_page.stream_color = self.theme.background_border_color
            self.background_page.stream_mrl = self.theme.background_source

    def set_main_area_page_values(self):
        """
        Handle the display and state of the Main Area page.
        """
        self.main_area_page.font_name = self.theme.font_main_name
        self.main_area_page.font_color = self.theme.font_main_color
        self.main_area_page.font_size = self.theme.font_main_size
        self.main_area_page.line_spacing = self.theme.font_main_line_adjustment
        self.main_area_page.letter_spacing = self.theme.font_main_letter_adjustment
        self.main_area_page.is_outline_enabled = self.theme.font_main_outline
        self.main_area_page.outline_color = self.theme.font_main_outline_color
        self.main_area_page.outline_size = self.theme.font_main_outline_size
        self.main_area_page.is_shadow_enabled = self.theme.font_main_shadow
        self.main_area_page.shadow_color = self.theme.font_main_shadow_color
        self.main_area_page.shadow_size = self.theme.font_main_shadow_size
        self.main_area_page.is_bold = self.theme.font_main_bold
        self.main_area_page.is_italic = self.theme.font_main_italics

    def set_footer_area_page_values(self):
        """
        Handle the display and state of the Footer Area page.
        """
        self.footer_area_page.font_name = self.theme.font_footer_name
        self.footer_area_page.font_color = self.theme.font_footer_color
        self.footer_area_page.is_bold = self.theme.font_footer_bold
        self.footer_area_page.is_italic = self.theme.font_footer_italics
        self.footer_area_page.font_size = self.theme.font_footer_size
        self.footer_area_page.wrap = self.theme.font_footer_wrap
        self.footer_area_page.line_spacing = self.theme.font_footer_line_adjustment
        self.footer_area_page.letter_spacing = self.theme.font_footer_letter_adjustment

    def set_position_page_values(self):
        """
        Handle the display and state of the _position page.
        """
        # Main Area
        self.area_position_page.use_main_default_location = not self.theme.font_main_override
        self.area_position_page.main_x = int(self.theme.font_main_x)
        self.area_position_page.main_y = int(self.theme.font_main_y)
        self.area_position_page.main_height = int(self.theme.font_main_height)
        self.area_position_page.main_width = int(self.theme.font_main_width)
        # Footer
        self.area_position_page.use_footer_default_location = not self.theme.font_footer_override
        self.area_position_page.footer_x = int(self.theme.font_footer_x)
        self.area_position_page.footer_y = int(self.theme.font_footer_y)
        self.area_position_page.footer_height = int(self.theme.font_footer_height)
        self.area_position_page.footer_width = int(self.theme.font_footer_width)

    def set_alignment_page_values(self):
        """
        Handle the display and state of the Alignments page.
        """
        self.alignment_page.horizontal_align = self.theme.display_horizontal_align
        self.alignment_page.vertical_align = self.theme.display_vertical_align
        self.alignment_page.horizontal_align_footer = self.theme.display_horizontal_align_footer
        self.alignment_page.vertical_align_footer = self.theme.display_vertical_align_footer
        self.alignment_page.is_transition_enabled = self.theme.display_slide_transition
        self.alignment_page.transition_type = self.theme.display_slide_transition_type
        self.alignment_page.transition_speed = self.theme.display_slide_transition_speed
        self.alignment_page.transition_direction = self.theme.display_slide_transition_direction
        self.alignment_page.is_transition_reverse_enabled = self.theme.display_slide_transition_reverse

    def set_preview_page_values(self):
        """
        Handle the display and state of the Preview page.
        """
        self.theme_name_edit.setText(self.theme.theme_name)
        self.preview_box.set_theme(self.theme, service_item_type=ServiceItemType.Text)

    def update_theme(self):
        """
        Update the theme object from the UI for fields not already updated
        when the are changed.
        """
        if not self.can_update_theme:
            return
        log.debug('update_theme')
        # background page
        self.theme.background_type = self.background_page.background_type
        if self.theme.background_type == BackgroundType.to_string(BackgroundType.Solid):
            self.theme.background_color = self.background_page.color
        elif self.theme.background_type == BackgroundType.to_string(BackgroundType.Gradient):
            self.theme.background_direction = self.background_page.gradient_type
            self.theme.background_start_color = self.background_page.gradient_start
            self.theme.background_end_color = self.background_page.gradient_end
        elif self.theme.background_type == BackgroundType.to_string(BackgroundType.Image):
            self.theme.background_border_color = self.background_page.image_color
            self.theme.background_source = self.background_page.image_path
            self.theme.background_filename = self.background_page.image_path
        elif self.theme.background_type == BackgroundType.to_string(BackgroundType.Video):
            self.theme.background_border_color = self.background_page.video_color
            self.theme.background_source = self.background_page.video_path
            self.theme.background_filename = self.background_page.video_path
        elif self.theme.background_type == BackgroundType.to_string(BackgroundType.Stream):
            self.theme.background_border_color = self.background_page.stream_color
            self.theme.background_source = self.background_page.stream_mrl
            self.theme.background_filename = self.background_page.stream_mrl
        # main page
        self.theme.font_main_name = self.main_area_page.font_name
        self.theme.font_main_color = self.main_area_page.font_color
        self.theme.font_main_size = self.main_area_page.font_size
        self.theme.font_main_line_adjustment = self.main_area_page.line_spacing
        self.theme.font_main_letter_adjustment = self.main_area_page.letter_spacing
        self.theme.font_main_outline = self.main_area_page.is_outline_enabled
        self.theme.font_main_outline_color = self.main_area_page.outline_color
        self.theme.font_main_outline_size = self.main_area_page.outline_size
        self.theme.font_main_shadow = self.main_area_page.is_shadow_enabled
        self.theme.font_main_shadow_size = self.main_area_page.shadow_size
        self.theme.font_main_shadow_color = self.main_area_page.shadow_color
        self.theme.font_main_bold = self.main_area_page.is_bold
        self.theme.font_main_italics = self.main_area_page.is_italic
        # footer page
        self.theme.font_footer_name = self.footer_area_page.font_name
        self.theme.font_footer_color = self.footer_area_page.font_color
        self.theme.font_footer_bold = self.footer_area_page.is_bold
        self.theme.font_footer_italics = self.footer_area_page.is_italic
        self.theme.font_footer_size = self.footer_area_page.font_size
        self.theme.font_footer_wrap = self.footer_area_page.wrap
        self.theme.font_footer_line_adjustment = self.footer_area_page.line_spacing
        self.theme.font_footer_letter_adjustment = self.footer_area_page.letter_spacing
        # position page (main)
        self.theme.font_main_override = not self.area_position_page.use_main_default_location
        if self.theme.font_main_override:
            self.theme.font_main_x = self.area_position_page.main_x
            self.theme.font_main_y = self.area_position_page.main_y
            self.theme.font_main_height = self.area_position_page.main_height
            self.theme.font_main_width = self.area_position_page.main_width
        else:
            self.theme.set_default_header()
        # position page (footer)
        self.theme.font_footer_override = not self.area_position_page.use_footer_default_location
        if self.theme.font_footer_override:
            self.theme.font_footer_x = self.area_position_page.footer_x
            self.theme.font_footer_y = self.area_position_page.footer_y
            self.theme.font_footer_height = self.area_position_page.footer_height
            self.theme.font_footer_width = self.area_position_page.footer_width
        else:
            self.theme.set_default_footer()
        # alignment page
        self.theme.display_horizontal_align = self.alignment_page.horizontal_align
        self.theme.display_vertical_align = self.alignment_page.vertical_align
        self.theme.display_horizontal_align_footer = self.alignment_page.horizontal_align_footer
        self.theme.display_vertical_align_footer = self.alignment_page.vertical_align_footer
        self.theme.display_slide_transition = self.alignment_page.is_transition_enabled
        self.theme.display_slide_transition_type = self.alignment_page.transition_type
        self.theme.display_slide_transition_speed = self.alignment_page.transition_speed
        self.theme.display_slide_transition_direction = self.alignment_page.transition_direction
        self.theme.display_slide_transition_reverse = self.alignment_page.is_transition_reverse_enabled

    def accept(self):
        """
        Lets save the theme as Finish has been triggered
        """
        # Save the theme name
        self.theme.theme_name = self.theme_name_edit.text().strip()
        if not self.theme.theme_name:
            critical_error_message_box(
                translate('OpenLP.ThemeWizard', 'Theme Name Missing'),
                translate('OpenLP.ThemeWizard', 'There is no name for this theme. Please enter one.'))
            return
        if self.theme.theme_name == '-1' or self.theme.theme_name == 'None':
            critical_error_message_box(
                translate('OpenLP.ThemeWizard', 'Theme Name Invalid'),
                translate('OpenLP.ThemeWizard', 'Invalid theme name. Please enter one.'))
            return
        destination_path = None
        if self.theme.background_type == BackgroundType.to_string(BackgroundType.Image) or \
                self.theme.background_type == BackgroundType.to_string(BackgroundType.Video):
            file_name = self.theme.background_filename.name
            destination_path = self.path / self.theme.theme_name / file_name
        if self.theme.background_type == BackgroundType.to_string(BackgroundType.Stream):
            destination_path = self.theme.background_source
        if not self.edit_mode and not self.theme_manager.check_if_theme_exists(self.theme.theme_name):
            return
        # Set the theme background to the cache location
        self.theme.background_filename = destination_path
        self.theme_manager.save_theme(self.theme)
        self.theme_manager.save_preview(self.theme.theme_name, self.preview_box.save_screenshot())
        return QtWidgets.QDialog.accept(self)
