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

__all__ = ["semicolons_to_commas", "numeric_scale", "simple_map"]


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

    return (source, destination)


def numeric_scale(config, data):
    """
    Post filter that scales a key from *data* by a factor in *config*.

    ``data[config["source"]]`` is multiplied by ``config["factor"]`` and
    written back to ``data[config["destination"]]`` if it exists, or
    ``data[config["source"]]`` if not.

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
    data[destination_key] = source * factor
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
