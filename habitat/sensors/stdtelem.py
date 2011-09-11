# Copyright 2011 (C) Adam Greig, Daniel Richman
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
Sensor functions for dealing with telemetry.
"""

import math
from time import strptime

__all__ = ["time", "coordinate"]


def time(data):
    """Parses time in ``HH:MM:SS`` format"""

    if len(data) == 8:
        t = strptime(data, "%H:%M:%S")
    elif len(data) == 6:
        t = strptime(data, "%H%M%S")
    elif len(data) == 5:
        t = strptime(data, "%H:%M")
    elif len(data) == 4:
        t = strptime(data, "%H%M")
    else:
        raise ValueError("Invalid time value.")

    parsed_data = {}
    parsed_data["hour"] = t.tm_hour
    parsed_data["minute"] = t.tm_min
    if len(data) == 8 or len(data) == 6:
        parsed_data["second"] = t.tm_sec
    return parsed_data


def coordinate(config, data):
    """
    Parses ascii latitude or longitude into a decimal-degrees float

    ``config["format"]`` dictates what format the input is in.
    Latitude and longitude can be either ``ddmm.mm`` or ``dd.dddd``.
    """

    if "format" not in config:
        raise ValueError("Coordinate format missing")
    coordinate_format = config["format"]

    left, right = coordinate_format.split(".")
    if left[-1] == "d" and right[-1] == "d":
        return float(data)
    elif left[0] == "d" and left[-1] == "m" and right[-1] == "m":
        first, second = data.split(".")
        degrees = float(first[:-2])
        minutes = float(first[-2:] + "." + second)
        if minutes > 60.0:
            raise ValueError("Minutes component > 60.")
        m_to_d = minutes / 60.0
        degrees += math.copysign(m_to_d, degrees)
        return degrees
    else:
        raise ValueError("Invalid coordinate format")
