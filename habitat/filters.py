# Copyright 2011 (C) Adam Greig, Daniel Richman, Priyesh Patel
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
Commonly required filters that are supplied with habitat.

Filters are small functions that can be run against incoming payload telemetry
during the parse phase, either before attempts at callsign extraction, before
the actual parse (but after the callsign has been identified) or after parsing
is complete.

This module contains commonly used filters which are supplied with habitat, but
end users are free to write their own and have :mod:`habitat.loadable_manager`
load them for use.
"""

from .utils import filtertools
import math

__all__ = ["semicolons_to_commas", "numeric_scale", "simple_map",
           "invalid_always", "invalid_location_zero", "invalid_gps_lock",
           "zero_pad_coordinates", "zero_pad_times"]


def semicolons_to_commas(config, data):
    """
    Intermediate filter that converts semicolons to commas.

    All semicolons in the string are replaced with colons and the checksum is
    updated; ``crc16-ccitt`` is assumed by default but can be overwritten with
    ``config["checksum"]``.

    >>> semicolons_to_commas({}, '$$testpayload,1,2,3;4;5;6*8A24')
    '$$testpayload,1,2,3,4,5,6*888F'
    """
    data = {"data": data}
    checksum = config['checksum'] if 'checksum' in config else 'crc16-ccitt'
    with filtertools.UKHASChecksumFixer(checksum, data) as c:
        c["data"] = c["data"].replace(";", ",")
    return c["data"]


def _post_singlefield(config):
    source = config["source"]

    if "destination" in config:
        destination = config["destination"]
    else:
        destination = source

    if destination.startswith("_"):
        raise ValueError("destination must not start with _")
    if destination == "payload":
        raise ValueError("destination must not be payload")

    return (source, destination)

def _round_significant(value, significance):
    if value == 0:
        return 0

    position = int(significance - math.ceil(math.log10(abs(value)))) 
    return round(value, position)


def numeric_scale(config, data):
    """
    Post filter that scales a key from *data* by a factor in *config*.

    ``data[config["source"]]`` is multiplied by ``config["factor"]`` and
    written back to ``data[config["destination"]]`` if it exists, or
    ``data[config["source"]]`` if not. ``config["offset"]`` is also optionally
    applied along with ``config["round"]``.

    >>> config = {"source": "key", "factor": 2.0}
    >>> data = {"key": "4", "other": "data"}
    >>> numeric_scale(config, data) == {'key': 8.0, 'other': 'data'}
    True
    >>> config["destination"] = "result"
    >>> numeric_scale(config, data) == {'key': 8.0, 'result': 16.0, 'other':
    ...     'data'}
    ...
    True
    """
    (source_key, destination_key) = _post_singlefield(config)

    factor = float(config["factor"])
    source = float(data[source_key])
    offset = float(0.0)

    if "offset" in config:
        offset = float(config["offset"])

    data[destination_key] = (source * factor) + offset

    if "round" in config:
        significance = int(config["round"])
        data[destination_key] = _round_significant(data[destination_key],
                significance)

    return data


def simple_map(config, data):
    """
    Post filter that maps source to destination values based on a dictionary.

    ``data[config["source"]]`` is used as a lookup key in ``config["map"]`` and
    the resulting value is written to ``data[config["destination"]]`` if it
    exists, or ``data[config["source"]]`` if not.

    A :exc:`ValueError <exceptions.ValueError>` is raised if ``config["map"]``
    is not a dictionary or does not contain the value read from *data*.
    >>> config = {"source": "key", "destination": "result", "map":
    ...     {1: 'a', 2: 'b'}}
    ...
    >>> data = {"key": 2}
    >>> simple_map(config, data) == {'key': 2, 'result': 'b'}
    True
    """
    (source_key, destination_key) = _post_singlefield(config)

    value_map = config["map"]
    if not isinstance(value_map, dict):
        raise ValueError("map should be a dict")

    data[destination_key] = value_map[data[source_key]]
    return data


def invalid_always(data):
    """
    Add the _fix_invalid key to data.
    """
    data["_fix_invalid"] = True
    return data


def invalid_location_zero(data):
    """If the latitude and longitude are zero, the fix is marked invalid."""
    if data["latitude"] == 0.0 and data["longitude"] == 0.0:
        data["_fix_invalid"] = True
    return data


def invalid_gps_lock(config, data):
    """
    Checks a gps_lock field to see if the payload has a lock

    The source key is config["source"], or "gps_lock" if that is not set.

    The fix is marked invalid if data[source] is not in the list config["ok"].
    """
    ok_list = config["ok"]
    if not isinstance(ok_list, list):
        raise ValueError("ok should be a list")

    if "source" in config:
        source = config["source"]
    else:
        source = "gps_lock"

    if data[source] not in ok_list:
        data["_fix_invalid"] = True

    return data

def zero_pad_coordinates(config, data):
    """
    Post filter that inserts zeros after the decimal point in coordinates, to
    fix the common error of having the integer and fractional parts of a
    decimal degree value as two ints and outputting them using something like
    `sprintf("%i.%i", int_part, frac_part);`, resulting in values that should
    be 51.0002 being output as 51.2 or similar.

    The fields to change is the list `config["fields"]` and the correct
    post-decimal-point width is `config["width"]`. By default fields is
    `["latitude", "longitude"]` and width is 5.
    """
    if "fields" not in config:
        config["fields"] = ["latitude", "longitude"]
    if "width" not in config:
        config["width"] = 5
    for field in config["fields"]:
        if field not in data:
            raise ValueError(
                "Field for filtering could not be found: {0}".format(field))
    for field in config["fields"]:
        parts = [int(x) for x in str(data[field]).split(".")]
        fmtstr = "{{0}}.{{1:0{0}n}}".format(config["width"])
        data[field] = float(fmtstr.format(*parts))
    return data

def zero_pad_times(config, data):
    """
    Intermediate filter that zero pads times which have been incorrectly
    transmitted as e.g. `12:3:8` instead of `12:03:08`. Only works when colons
    are used as delimiters.

    The field position to change is `config["field"]` and defaults to 2 (which
    is typical with $$PAYLOAD,ID,TIME). The checksum in use is
    `config["checksum"]` and defaults to `crc16-ccitt`.
    """
    # set defaults
    if "field" not in config:
        config["field"] = 2
    if "checksum" not in config:
        config["checksum"] = "crc16-ccitt"

    # get at individual fields, removing newline and checksum
    fields = data.split(",")
    checksum = ""
    fields[-1] = fields[-1].strip()
    if '*' in fields[-1]:
        fields[-1], checksum = fields[-1].split("*")
        checksum = "*{0}".format(checksum)

    # check field exists
    if len(fields) <= config["field"]:
        raise ValueError("Configured field index is not in sentence.")

    # must use colons
    timefield = fields[config["field"]]
    if ":" not in timefield:
        raise ValueError("Can only zero pad times that use a colon delimiter")

    # reformat the time
    timeparts = [int(x) for x in timefield.split(":")]
    timefield = "{0:02n}:{1:02n}".format(timeparts[0], timeparts[1])
    if len(timeparts) == 3:
        timefield = "{0}:{1:02n}".format(timefield, timeparts[2])
    fields[config["field"]] = timefield

    # add checksum and newline back
    fields[-1] = "{0}{1}\n".format(fields[-1], checksum)
    new = ",".join(fields)
    # fix checksum
    return filtertools.UKHASChecksumFixer.fix(config["checksum"], data, new)
