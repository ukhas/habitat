# Copyright 2013 (C) Daniel Richman
#
# This file is part of habitat.
#
# habitat is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# habitat is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with habitat.  If not, see <http://www.gnu.org/licenses/>.

"""Quick traceback module shortcuts for logging"""

import sys
import traceback

def oneline(exc_value=None):
    """
    Return a single line describing 'exc_value'

    *exc_value* shold be either an Exception instance, for example, acquired
    via 'except ValueError as e:'; or None, in which case the exception
    currently being handled is used.

    The string returned is the last line of Python's normal traceback;
    something like 'ValueError: some message', with no newline.
    """
    if exc_value is None:
        (exc_type, exc_value, discard_tb) = sys.exc_info()
    else:
        exc_type = type(exc_value)

    exc_tb = traceback.format_exception_only(exc_type, exc_value)
    info = exc_tb[-1].strip()
    return info
