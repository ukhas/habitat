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
Basic sensor functions.

These sensors cover simple ASCII representations of numbers and strings.
"""

__all__ = ["ascii_int", "ascii_float", "string"]


def ascii_int(data):
    """
    Parse *data* to an integer, or return ``None`` if the string is empty.
    """
    return int(data) if data != '' else None


def ascii_float(data):
    """
    Parse *data* to a float, or return ``None`` if the string is empty.
    """
    return float(data) if data != '' else None


def string(data):
    """
    Returns *data* as a string.
    """
    return str(data)
