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
The actual exception dialog form.
"""
import logging
import os
import platform
import re

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.common.i18n import UiStrings, translate
from openlp.core.common.mixins import RegistryProperties
from openlp.core.common.platform import is_linux
from openlp.core.ui.exceptiondialog import Ui_ExceptionDialog
from openlp.core.version import get_library_versions, get_version
from openlp.core.widgets.dialogs import FileDialog


log = logging.getLogger(__name__)


class ExceptionForm(QtWidgets.QDialog, Ui_ExceptionDialog, RegistryProperties):
    """
    The exception dialog
    """
    def __init__(self):
        """
        Constructor.
        """
        super(ExceptionForm, self).__init__(None,
                                            QtCore.Qt.WindowType.WindowSystemMenuHint |
                                            QtCore.Qt.WindowType.WindowTitleHint)
        self.setup_ui(self)
        self.settings_section = 'crashreport'
        self.report_text = '**OpenLP Bug Report**\n' \
            'Version: {version}\n\n' \
            '--- Details of the Exception. ---\n\n{description}\n\n ' \
            '--- Exception Traceback ---\n{traceback}\n' \
            '--- System information ---\n{system}\n' \
            '--- Library Versions ---\n{libs}\n'

    def exec(self):
        """
        Show the dialog.
        """
        self.description_text_edit.setPlainText('')
        self.on_description_updated()
        self.file_attachment = None
        return QtWidgets.QDialog.exec(self)

    def _create_report(self):
        """
        Create an exception report.
        """
        openlp_version = get_version()
        description = self.description_text_edit.toPlainText()
        traceback = self.exception_text_edit.toPlainText()
        system = translate('OpenLP.ExceptionForm', 'Platform: {platform}\n').format(platform=platform.platform())
        library_versions = get_library_versions()
        library_versions['PyUNO'] = self._get_pyuno_version()
        libraries = '\n'.join(['{}: {}'.format(library, version) for library, version in library_versions.items()])

        if is_linux():
            if os.environ.get('KDE_FULL_SESSION') == 'true':
                system += 'Desktop: KDE SC\n'
            elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
                system += 'Desktop: GNOME\n'
            elif os.environ.get('DESKTOP_SESSION') == 'xfce':
                system += 'Desktop: Xfce\n'
        # NOTE: Keys match the expected input for self.report_text.format()
        return {'version': openlp_version, 'description': description, 'traceback': traceback,
                'system': system, 'libs': libraries}

    def on_save_report_button_clicked(self):
        """
        Saving exception log and system information to a file.
        """
        while True:
            file_path, filter_used = FileDialog.getSaveFileName(
                self,
                translate('OpenLP.ExceptionForm', 'Save Crash Report'),
                self.settings.value(self.settings_section + '/last directory'),
                translate('OpenLP.ExceptionForm', 'Text files (*.txt *.log *.text)'))
            if file_path is None:
                break
            self.settings.setValue(self.settings_section + '/last directory', file_path.parent)
            opts = self._create_report()
            report_text = self.report_text.format(version=opts['version'], description=opts['description'],
                                                  traceback=opts['traceback'], libs=opts['libs'], system=opts['system'])
            try:
                with file_path.open('w') as report_file:
                    report_file.write(report_text)
                    break
            except OSError as e:
                log.exception('Failed to write crash report')
                QtWidgets.QMessageBox.warning(
                    self, translate('OpenLP.ExceptionDialog', 'Failed to Save Report'),
                    translate('OpenLP.ExceptionDialog', 'The following error occurred when saving the report.\n\n'
                                                        '{exception}').format(file_name=file_path, exception=e))

    def on_send_report_button_clicked(self):
        """
        Opening systems default email client and inserting exception log and system information.
        """
        content = self._create_report()
        source = ''
        exception = ''
        for line in content['traceback'].split('\n'):
            if re.search(r'[/\\]openlp[/\\]', line):
                source = re.sub(r'.*[/\\]openlp[/\\](.*)".*', r'\1', line)
            if ':' in line:
                exception = line.split('\n')[-1].split(':')[0]
        subject = 'Bug report: {error} in {source}'.format(error=exception, source=source)
        mail_urlquery = QtCore.QUrlQuery()
        mail_urlquery.addQueryItem('subject', subject)
        mail_urlquery.addQueryItem('body', self.report_text.format(version=content['version'],
                                                                   description=content['description'],
                                                                   traceback=content['traceback'],
                                                                   system=content['system'],
                                                                   libs=content['libs']))
        if self.file_attachment:
            mail_urlquery.addQueryItem('attach', self.file_attachment)
        mail_to_url = QtCore.QUrl('mailto:mwandajosiah@gmail.com')
        mail_to_url.setQuery(mail_urlquery)
        QtGui.QDesktopServices.openUrl(mail_to_url)

    def on_description_updated(self):
        """
        Update the minimum number of characters needed in the description.
        """
        count = int(20 - len(self.description_text_edit.toPlainText()))
        if count < 0:
            self.__button_state(True)
            self.description_word_count.setText(
                translate('OpenLP.ExceptionDialog', '<strong>Thank you for your description!</strong>'))
        elif count == 20:
            self.__button_state(False)
            self.description_word_count.setText(
                translate('OpenLP.ExceptionDialog', '<strong>Tell us what you were doing when this happened.</strong>'))
        else:
            self.__button_state(False)
            self.description_word_count.setText(
                translate('OpenLP.ExceptionDialog', '<strong>Please enter a more detailed description of the situation'
                                                    '</strong>'))

    def on_attach_file_button_clicked(self):
        """
        Attach files to the bug report e-mail.
        """
        file_path, filter_used = \
            FileDialog.getOpenFileName(self,
                                       translate('ImagePlugin.ExceptionDialog', 'Select Attachment'),
                                       self.settings.value(self.settings_section + '/last directory'),
                                       '{text} (*)'.format(text=UiStrings().AllFiles))
        log.info('New files {file_path}'.format(file_path=file_path))
        if file_path:
            self.file_attachment = str(file_path)

    def __button_state(self, state):
        """
        Toggle the button state.
        """
        self.save_report_button.setEnabled(state)
        self.send_report_button.setEnabled(state)

    def _get_pyuno_version(self):
        """
        Added here to define only when the form is actioned. The uno interface spits out lots of exception messages
        if the import is at a file level.  If uno import is changed this could be reverted.
        This happens in other classes but there it is localised here it is across the whole system and hides real
        errors.
        """
        try:
            import uno
            arg = uno.createUnoStruct('com.sun.star.beans.PropertyValue')
            arg.Name = 'nodepath'
            arg.Value = '/org.openoffice.Setup/Product'
            context = uno.getComponentContext()
            provider = context.ServiceManager.createInstance('com.sun.star.configuration.ConfigurationProvider')
            node = provider.createInstanceWithArguments('com.sun.star.configuration.ConfigurationAccess', (arg,))
            return node.getByName('ooSetupVersion')
        except ImportError:
            return '-'
        except Exception:
            return '- (Possible non-standard UNO installation)'
