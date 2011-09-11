# Copyright 2011 (C) Daniel Richman, Adam Greig
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

"""
Basic sensor functions
"""

__all__ = ["ascii_int", "ascii_float", "string"]


def ascii_int(data):
    """parse a string to an integer, or None if the string is empty"""
    if data == '':
        return None
    return int(data)


def ascii_float(data):
    """parse a string to a float, or None if the string is empty"""
    if data == '':
        return None
    return float(data)


def string(data):
    """null sensor; just returns the data as a string"""
    return str(data)
