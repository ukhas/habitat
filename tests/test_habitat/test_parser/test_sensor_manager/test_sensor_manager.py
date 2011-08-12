# Copyright 2011 (C) Daniel Richman
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
Tests the Sensor Manager
"""

from nose.tools import raises
from habitat.parser.sensor_manager import SensorManager

example_path = "test_habitat.test_parser.test_sensor_manager.example_sensor_library"

fake_config = {
    "sensors": [
        {"name": "liba", "class": example_path + "_a"},
        {"name": "libb", "class": example_path + "_b"}
    ]
}

empty_config = {
    "sensors": []
}

cfg_c = {"abracadabra": "15802"}

class TestSensorManager:
    def test_module_includes_base_functions(self):
        self.mgr = SensorManager(empty_config)
        assert len(self.mgr.libraries) == 1
        assert self.mgr.parse("base.ascii_int", None, "1234") == 1234
        assert self.mgr.parse("base.ascii_float", None, "12.32") == 12.32
        assert self.mgr.parse("base.string", None, "1234") == "1234"

    def test_init_loads_db_listed_modules_and_works(self):
        self.mgr = SensorManager(fake_config)
        assert len(self.mgr.libraries) == 3

        assert self.mgr.parse("liba.format_a", None, "thedata") == \
            ('formatted by a', "'thedata'")
        assert self.mgr.parse("liba.format_b", None, "asdf") == \
            {"information": 64, "hello": "world"}
        assert self.mgr.parse("libb.format_c", cfg_c, "asdf") == \
            "more functions"

    @raises(ValueError)
    def test_errors_bubble_up_a(self):
        SensorManager(empty_config).parse("base.ascii_int", None, "non-int")

    @raises(ValueError)
    def test_errors_bubble_up_b(self):
        SensorManager(fake_config).parse("libb.format_d", {}, "hmm")

    def test_parse_passes_config_dict(self):
        SensorManager(fake_config).parse("libb.format_c", cfg_c,
                                                  "data")

    @raises(ValueError)
    def test_cannot_use_sensor_not_in_all(self):
        SensorManager(fake_config).parse("libb.somethingelse", {},
                                                  "hah!")

    def test_repr_describes_manager(self):
        mgr = SensorManager(empty_config)
        expect = "<habitat.parser.SensorManager: {num} libraries loaded>"
        assert repr(mgr) == expect.format(num=1)
        mgr.load(example_path + "_a", "liba")
        assert repr(mgr) == expect.format(num=2)
