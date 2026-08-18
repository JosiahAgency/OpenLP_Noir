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
The GUI widgets of the exception dialog.
"""

from PySide6 import QtWidgets

from openlp.core.common.i18n import translate
from openlp.core.lib.ui import create_button, create_button_box
from openlp.core.ui.icons import UiIcons


class Ui_ExceptionDialog(object):
    """
    The GUI widgets of the exception dialog.
    """
    def setup_ui(self, exception_dialog):
        """
        Set up the UI.
        """
        exception_dialog.setObjectName('exception_dialog')
        exception_dialog.setWindowIcon(UiIcons().main_icon)
        self.exception_layout = QtWidgets.QVBoxLayout(exception_dialog)
        self.exception_layout.setObjectName('exception_layout')
        self.message_layout = QtWidgets.QHBoxLayout()
        self.message_layout.setObjectName('messageLayout')
        # Set margin to make the box a bit wider so the traceback is easier to read. (left, top, right, bottom)
        self.message_layout.setContentsMargins(0, 0, 50, 0)
        self.message_layout.addSpacing(12)
        self.bug_label = QtWidgets.QLabel(exception_dialog)
        self.bug_label.setPixmap(UiIcons().exception.pixmap(40, 40))
        self.bug_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        self.bug_label.setObjectName('bug_label')
        self.message_layout.addWidget(self.bug_label)
        self.message_layout.addSpacing(12)
        self.message_label = QtWidgets.QLabel(exception_dialog)
        self.message_label.setWordWrap(True)
        self.message_label.setObjectName('message_label')
        self.message_layout.addWidget(self.message_label)
        self.exception_layout.addLayout(self.message_layout)
        self.description_explanation = QtWidgets.QLabel(exception_dialog)
        self.description_explanation.setObjectName('description_explanation')
        self.exception_layout.addWidget(self.description_explanation)
        self.description_text_edit = QtWidgets.QPlainTextEdit(exception_dialog)
        self.description_text_edit.setObjectName('description_text_edit')
        self.exception_layout.addWidget(self.description_text_edit)
        self.description_word_count = QtWidgets.QLabel(exception_dialog)
        self.description_word_count.setObjectName('description_word_count')
        self.exception_layout.addWidget(self.description_word_count)
        self.exception_text_edit = QtWidgets.QPlainTextEdit(exception_dialog)
        self.exception_text_edit.setReadOnly(True)
        self.exception_text_edit.setObjectName('exception_text_edit')
        self.exception_layout.addWidget(self.exception_text_edit)
        self.send_report_button = create_button(exception_dialog, 'send_report_button',
                                                icon=UiIcons().email,
                                                click=self.on_send_report_button_clicked)
        self.save_report_button = create_button(exception_dialog, 'save_report_button',
                                                icon=UiIcons().save,
                                                click=self.on_save_report_button_clicked)
        self.attach_file_button = create_button(exception_dialog, 'attach_file_button',
                                                icon=UiIcons().open,
                                                click=self.on_attach_file_button_clicked)
        self.button_box = create_button_box(exception_dialog, 'button_box', ['close'],
                                            [self.send_report_button, self.save_report_button, self.attach_file_button])
        self.exception_layout.addWidget(self.button_box)

        self.retranslate_ui(exception_dialog)
        self.description_text_edit.textChanged.connect(self.on_description_updated)

    def retranslate_ui(self, exception_dialog):
        """
        Translate the widgets on the fly.
        """
        # Note that bugs mail is not clickable, but it adds the blue color and underlining and makes the test copyable.
        exception_dialog.setWindowTitle(translate('OpenLP.ExceptionDialog', 'Error Occurred'))
        # Explanation text, &nbsp; adds a small space before: If possible, write in English.
        self.description_explanation.setText(
            translate('OpenLP.ExceptionDialog', '<strong>Please describe what you were trying to do.</strong> '
                                                '&nbsp;If possible, write in English.'))
        exception_part1 = (translate('OpenLP.ExceptionDialog',
                                     '<strong>Oops, OpenLP hit a problem and couldn\'t recover!<br><br>'
                                     'You can help </strong> the OpenLP developers to <strong>fix this</strong>'
                                     ' by<br> sending them a <strong>bug report to {email}</strong>{newlines}'
                                     ).format(
                                         email='<a href = "mailto:mwandajosiah@gmail.com" > '
                                               'mwandajosiah@gmail.com</a>',
                                         newlines='<br><br>'
                                     ))
        message_text = translate(
            'OpenLP.ExceptionDialog', '{first_part}'
            '<strong>No email app? </strong> You can <strong>save</strong> this '
            'information to a <strong>file</strong> and<br>'
            'send it from your <strong>mail on browser</strong> via an <strong>attachment.</strong><br><br>'
            '<strong>Thank you</strong> for being part of making OpenLP better!<br>'
        ).format(first_part=exception_part1)
        self.message_label.setText(message_text)
        self.send_report_button.setText(translate('OpenLP.ExceptionDialog', 'Send E-Mail'))
        self.save_report_button.setText(translate('OpenLP.ExceptionDialog', 'Save to File'))
        self.attach_file_button.setText(translate('OpenLP.ExceptionDialog', 'Attach File'))
