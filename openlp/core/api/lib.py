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
The OpenLP API library.
"""

from functools import wraps
from flask import request
from openlp.core.common.registry import Registry


def login_required(f):
    """
    Checks if a login is required.

    :param: f: The function to call.
    :type f: function
    :return: The decorated function.
    :rtype: function
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        settings = Registry().get('settings_thread')
        if settings is None or not settings.value('api/authentication enabled'):
            return f(*args, **kwargs)
        token = request.headers.get('Authorization', '')
        if token == Registry().get('authentication_token'):
            return f(*args, **kwargs)
        return '', 401
    return decorated
