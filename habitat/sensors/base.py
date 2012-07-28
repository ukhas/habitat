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

__all__ = ["ascii_int", "ascii_float", "string", "constant"]


def ascii_int(data):
    """
    Parse *data* to an integer.
    """
    return int(data)


def ascii_float(data):
    """
    Parse *data* to a float.
    """
    return float(data)


def string(data):
    """
    Returns *data* as a string.
    """
    return str(data)

def constant(config, data):
    """
    Checks that *data* is equal to config["expect"], returning None.
    """
    if "expect" in config:
        expect = config["expect"]
    else:
        expect = ''
    if data != expect:
        raise ValueError("Expected '{0}', got '{1}'".format(expect, data))
    return None
