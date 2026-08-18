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
The splash screen
"""

from PySide6 import QtCore, QtGui, QtWidgets

from openlp.core.ui.style import get_noir_theme_tokens, is_ui_theme_noir_family


class SplashScreen(QtWidgets.QSplashScreen):
    """
    The splash screen
    """

    def __init__(self):
        """
        Constructor
        """
        super(SplashScreen, self).__init__()
        self.setup_ui()

    def _apply_noir_background(self, splash_image):
        """
        Keep a transparent splash canvas in Noir mode. The splash is shown
        before set_default_theme() runs, so the app-wide Noir palette isn't
        applied yet and can't be relied on here.
        """
        canvas = QtGui.QPixmap(370, 370)
        canvas.setDevicePixelRatio(self.devicePixelRatioF())
        canvas.fill(QtGui.QColor(get_noir_theme_tokens()['ink0']))
        painter = QtGui.QPainter(canvas)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(QtCore.QRect(0, 0, 370, 370), splash_image)
        painter.end()
        return canvas

    def setup_ui(self):
        """
        Set up the UI
        """
        self.setObjectName('splashScreen')
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.PreventContextMenu)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        source_image = QtGui.QPixmap(':/graphics/openlp-splash-screen.png')
        source_image.setDevicePixelRatio(self.devicePixelRatioF())
        splash_image = source_image.scaled(370, 370, mode=QtCore.Qt.TransformationMode.SmoothTransformation)
        source_image = None
        if is_ui_theme_noir_family():
            splash_image = self._apply_noir_background(splash_image)
        self.setPixmap(splash_image)
        self.resize(370, 370)
