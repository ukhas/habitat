# Copyright 2013 (C) Adam Greig
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
Test the RockBLOCK binary protocol parser.
"""

from nose.tools import assert_raises
from copy import deepcopy

# Mocking the LoadableManager is a heck of a lot of effort. Not worth it.
from ...loadable_manager import LoadableManager
from ...parser_modules.rockblock_binary_parser import RockBLOCKBinaryParser

# Provide the sensor functions to the parser
fake_sensors_config = {
    "loadables": [
        {"name": "sensors.base", "class": "habitat.sensors.base"},
        {"name": "sensors.stdtelem", "class": "habitat.sensors.stdtelem"}
    ]
}


class FakeParser:
    def __init__(self):
        self.loadable_manager = LoadableManager(fake_sensors_config)

# A 'standard' config. Other configs can copy this and change parts.
base_config = {
    "protocol": "RockBLOCK Binary",
    "format": "IddHB",
    "fields": [
        {
            "name": "time",
            "sensor": "stdtelem.time"
        }, {
            "name": "latitude",
            "sensor": "stdtelem.coordinate",
            "format": "dd.dddd"
        }, {
            "name": "longitude",
            "sensor": "stdtelem.coordinate",
            "format": "dd.dddd"
        }, {
            "name": "altitude",
            "sensor": "base.ascii_int"
        }, {
            "name": "speed",
            "sensor": "base.ascii_float"
        }, {
            "name": "custom_string",
            "sensor": "base.string"
        }
    ]
}


class TestRockBLOCKBinaryParser:
    def setup(self):
        self.p = RockBLOCKBinaryParser(FakeParser())
