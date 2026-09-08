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
from openlp.core.ui.themewizard import Ui_ThemeWizard


log = logging.getLogger(__name__)

#: Milliseconds to wait after the last change before refreshing the live preview. This avoids triggering a full
#: (relatively expensive, ~1 second) preview render on every single keystroke/spin/click.
PREVIEW_UPDATE_DELAY = 500


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
        # Debounce timer driving the always-on live preview. Rather than re-rendering the (relatively expensive)
        # preview on every single control change, we wait for a short pause in user activity first.
        self.preview_update_timer = QtCore.QTimer(self)
        self.preview_update_timer.setSingleShot(True)
        self.preview_update_timer.setInterval(PREVIEW_UPDATE_DELAY)
        self.preview_update_timer.timeout.connect(self._refresh_live_preview)
        self._is_refreshing_preview = False
        self.background_page.changed.connect(self.schedule_preview_update)
        self.alignment_page.changed.connect(self.schedule_preview_update)
        self.area_position_page.changed.connect(self.schedule_preview_update)
        for font_page in (self.main_area_page, self.footer_area_page):
            font_page.font_name_changed.connect(self.schedule_preview_update)
            font_page.font_color_changed.connect(self.schedule_preview_update)
            font_page.is_bold_changed.connect(self.schedule_preview_update)
            font_page.is_italic_changed.connect(self.schedule_preview_update)
            font_page.font_size_changed.connect(self.schedule_preview_update)
            font_page.wrap_changed.connect(self.schedule_preview_update)
            font_page.line_spacing_changed.connect(self.schedule_preview_update)
            font_page.letter_spacing_changed.connect(self.schedule_preview_update)
            font_page.is_outline_enabled_changed.connect(self.schedule_preview_update)
            font_page.outline_color_changed.connect(self.schedule_preview_update)
            font_page.outline_size_changed.connect(self.schedule_preview_update)
            font_page.is_shadow_enabled_changed.connect(self.schedule_preview_update)
            font_page.shadow_color_changed.connect(self.schedule_preview_update)
            font_page.shadow_size_changed.connect(self.schedule_preview_update)

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
        # The live preview panel isn't useful on the welcome page (there's nothing to preview yet), so only
        # show it once the user has moved past it, and refresh it immediately whenever landing on a new page
        # rather than waiting for the debounce timer or an explicit control change.
        is_welcome_page = self.page(page_id) == self.welcome_page
        self.preview_area.setVisible(not is_welcome_page)
        if not is_welcome_page:
            self._refresh_live_preview()

    def schedule_preview_update(self, *args):
        """
        (Re)start the debounce timer so the live preview is refreshed shortly after the user stops interacting.
        Called from every relevant control's change signal.
        """
        if self.currentPage() == self.welcome_page:
            return
        self.preview_update_timer.start()

    def _refresh_live_preview(self):
        """
        Actually refresh the live preview panel. This is the debounce timer's timeout slot, but is also called
        directly (bypassing the debounce delay) when the user switches to a new wizard page.
        """
        if self._is_refreshing_preview or self.currentPage() == self.welcome_page:
            return
        self._is_refreshing_preview = True
        try:
            self.update_theme()
            self.resizeEvent()
            self.preview_box.clear_slides()
            self.preview_box.show()
            self.preview_box.generate_preview(self.theme, False, False)
        finally:
            self._is_refreshing_preview = False

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
            # The name field is hidden while editing an existing theme (it's renamed via the "Rename Theme"
            # toolbar action instead), so the final page's copy shouldn't ask the user to name it.
            self.preview_page.setSubTitle(translate('OpenLP.ThemeWizard', 'Save the theme. The preview on '
                                                    'the left reflects all of your changes.'))
            self.next()
        else:
            self.setWindowTitle(UiStrings().NewTheme)
            self.preview_page.setSubTitle(translate('OpenLP.ThemeWizard', 'Give the theme a name and save '
                                                    'it. The preview on the left reflects all of your '
                                                    'changes.'))
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

        Note: every field is set unconditionally (not just the ones matching the theme's current
        background type). The background page's widgets are shared/reused across every Add/Edit Theme
        invocation, so if only the "active" type's fields were refreshed here, switching the background
        type combo box (or a subsequent theme reusing the wizard) would show stale colors left over from
        a previous, unrelated theme instead of that theme's actual (or default) values.
        """
        self.background_page.background_type = self.theme.background_type
        self.background_page.color = self.theme.background_color
        self.background_page.gradient_start = self.theme.background_start_color
        self.background_page.gradient_end = self.theme.background_end_color
        self.background_page.gradient_type = self.theme.background_direction
        self.background_page.image_color = self.theme.background_border_color
        self.background_page.video_color = self.theme.background_border_color
        self.background_page.stream_color = self.theme.background_border_color
        # background_source is a Path for image/video themes and a plain str (or None) for stream themes;
        # the stream MRL field only ever wants a string, so only use it as-is when it already is one and
        # otherwise clear the field (rather than crashing QLineEdit.setText() with a Path).
        stream_mrl = self.theme.background_source if isinstance(self.theme.background_source, str) else ''
        self.background_page.stream_mrl = stream_mrl
        if self.theme.background_type == BackgroundType.to_string(BackgroundType.Image):
            if self.theme.background_source and self.theme.background_source.exists():
                self.background_page.image_path = self.theme.background_source
            else:
                self.background_page.image_path = self.theme.background_filename
        elif self.theme.background_type == BackgroundType.to_string(BackgroundType.Video):
            if self.theme.background_source and self.theme.background_source.exists():
                self.background_page.video_path = self.theme.background_source
            else:
                self.background_page.video_path = self.theme.background_filename

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
        # Force a fresh, fully-settled render of the *final* theme (background file now at its saved
        # location, name finalised) rather than reusing whatever was last grabbed off-screen by the
        # debounced live preview. QWebEngineView content is composited by a separate GPU process, so a
        # bare grab() of "whatever's currently displayed" can occasionally capture a stale or
        # not-yet-flushed frame; generate_preview() re-applies the theme and waits for it to settle
        # before handing back a screenshot, which is far more likely to match what's actually on screen.
        preview_pixmap = self.preview_box.generate_preview(self.theme, False, True)
        self.theme_manager.save_preview(self.theme.theme_name, preview_pixmap)
        return QtWidgets.QDialog.accept(self)
