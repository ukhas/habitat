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
Filters that might be applied to incoming payload telemetry which are supplied
with habitat as commonly used pieces of code.
"""

from habitat.utils import filtertools

__all__ = ["semicolons_to_commas", "numeric_scale", "simple_map"]

def semicolons_to_commas(config, data):
    """intermediate filter that converts semicolons to commas"""
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
    """post filter that scales a numeric key of data linearly"""
    (source_key, destination_key) = _post_singlefield(config)
    factor = float(config["factor"])

    source = float(data[source_key])
    data[destination_key] = source * factor
    return data

def simple_map(config, data):
    """post filter that maps source to destination values based on a dict"""
    (source_key, destination_key) = _post_singlefield(config)

    value_map = config["map"]
    if not isinstance(value_map, dict):
        raise ValueError("map should be a dict")

    data[destination_key] = value_map[data[source_key]]
    return data
