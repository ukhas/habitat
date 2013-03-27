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
Test the simple binary protocol parser.
"""

import struct
from nose.tools import assert_raises
from copy import deepcopy

# Mocking the LoadableManager is a heck of a lot of effort. Not worth it.
from ...loadable_manager import LoadableManager
from ...parser_modules.simple_binary_parser import SimpleBinaryParser
from ...parser import CantExtractCallsign

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
    "protocol": "simple_binary",
    "fields": [
        {
            "format": "i",
            "name": "sentence_id"
        }, {
            "format": "d",
            "name": "latitude"
        }, {
            "format": "d",
            "name": "longitude"
        }, {
            "format": "I",
            "name": "altitude"
        }
    ]
}


class TestSimpleBinaryParser:
    def setup(self):
        self.p = SimpleBinaryParser(FakeParser())
    
    def test_pre_parse_just_raises_cantextractcallsign(self):
        assert_raises(CantExtractCallsign, self.p.pre_parse, "test")

    def test_verifies_config(self):
        config = deepcopy(base_config)
        config["protocol"] = "not_simple_binary_at_all"
        assert_raises(ValueError, self.p.parse, "test", config)

        config = deepcopy(base_config)
        del config["fields"]
        assert_raises(ValueError, self.p.parse, "test", config)

        config = deepcopy(base_config)
        del config["fields"][1]["name"]
        assert_raises(ValueError, self.p.parse, "test", config)

        config = deepcopy(base_config)
        del config["fields"][1]["format"]
        assert_raises(ValueError, self.p.parse, "test", config)

        config = deepcopy(base_config)
        config["fields"][1]["name"] = "_test"
        assert_raises(ValueError, self.p.parse, "test", config)

        config = deepcopy(base_config)
        config["fields"][1]["name"] = config["fields"][0]["name"]
        assert_raises(ValueError, self.p.parse, "test", config)

    def test_parses(self):
        data = struct.pack("iddI", 5, 52.1234, -0.0123, 1234)
        output = self.p.parse(data, base_config)
        assert output == {
            "sentence_id": 5,
            "latitude": 52.1234,
            "longitude": -0.0123,
            "altitude": 1234
        }

    def test_error_on_bad_data(self):
        data = "\x01\x02\x03\x04"
        assert_raises(ValueError, self.p.parse, data, base_config)

    def test_error_on_bad_format(self):
        data = struct.pack("iddI", 5, 1.0, 1.0, 1)
        config = deepcopy(base_config)
        config["fields"][3]["format"] = "a"
        assert_raises(ValueError, self.p.parse, data, config)

    def test_error_on_wrong_number_of_fields(self):
        data = struct.pack("iddII", 1, 1.0, 1.0, 1, 1)
        config = deepcopy(base_config)
        config["fields"][3]["format"] = "II"
        assert_raises(ValueError, self.p.parse, data, config)

        data = struct.pack("iddI", 1, 1.0, 1.0, 1)
        config = deepcopy(base_config)
        config["fields"][3]["format"] = ""
        assert_raises(ValueError, self.p.parse, data, config)

    def test_uses_sensor(self):
        data = struct.pack("idd5s", 1, 1.0, 1.0, "12.34")
        config = deepcopy(base_config)
        config["fields"][3]["format"] = "5s"
        config["fields"][3]["sensor"] = "base.ascii_float"
        output = self.p.parse(data, config)
        assert output["altitude"] == 12.34
