# Copyright 2011 (C) Daniel Richman, Priyesh Patel
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
Tests common filters
"""

from nose.tools import assert_raises, eq_
from .. import filters as f


class TestFilters:
    def test_semicolons_to_commas(self):
        data = "$$testpayload,1,2,3;4;5;6*8A24\n"
        fixed = f.semicolons_to_commas({}, data)
        assert fixed == "$$testpayload,1,2,3,4,5,6*888F\n"

    def test_semicolons_to_commas_with_other_checksum(self):
        data = "$$testpayload,1,2,3;4;5;6*68\n"
        config = {'checksum': 'xor'}
        fixed = f.semicolons_to_commas(config, data)
        assert fixed == "$$testpayload,1,2,3,4,5,6*7F\n"

    def test_numeric_scale(self):
        config = {"source": "key", "factor": (1.0 / 7.0)}
        data = {"key": 49, "something": True}
        fixed = f.numeric_scale(config, data)
        assert fixed == {"key": 7, "something": True}

    def test_numeric_scale_rounding(self):
        config = {"source": "key", "factor": (1.0 / 7.0), "round": 5}
        data = {"key": 50, "something": True}
        fixed = f.numeric_scale(config, data)
        assert fixed == {"key": 7.1429, "something": True}

    def test_numeric_scale_offset(self):
        config = {"source": "key", "factor": (1.0 / 7.0), "offset": -5}
        data = {"key": 49, "something": True}
        fixed = f.numeric_scale(config, data)
        assert fixed == {"key": 2, "something": True}

    def test_numeric_scale_round_zero(self):
        config = {"source": "key", "factor": 4.0, "round": 3}
        data = {"key": 0.0}
        fixed = f.numeric_scale(config, data)
        assert fixed == {"key": 0.0}

    def test_simple_map(self):
        config = {"source": "key", "destination": "key_thing",
                  "map": {48: "test", 49: "something"}}
        data = {"key": 49}
        fixed = f.simple_map(config, data)
        assert fixed == {"key": 49, "key_thing": "something"}

    def test_invalid_always(self):
        data = {"key": 1235}
        assert f.invalid_always(data) == {"key": 1235, "_fix_invalid": True}

    def test_invalid_location_zero(self):
        data = {"latitude": 12.12, "longitude": 3.14}
        assert f.invalid_location_zero(data.copy()) == data
        data = {"latitude": 0, "longitude": 0}
        expect = data.copy()
        expect.update({"_fix_invalid": True})
        assert f.invalid_location_zero(data) == expect

    def test_invalid_gps_lock(self):
        config = {"ok": [3, 4, "steve"]}
        assert f.invalid_gps_lock(config, {"gps_lock": 1}) == \
                {"gps_lock": 1, "_fix_invalid": True}
        assert f.invalid_gps_lock(config, {"gps_lock": 4}) == \
                {"gps_lock": 4}
        assert f.invalid_gps_lock(config, {"gps_lock": "barry"}) == \
                {"gps_lock": "barry", "_fix_invalid": True}
        assert f.invalid_gps_lock(config, {"gps_lock": "steve"}) == \
                {"gps_lock": "steve"}

    def test_zero_pad_coordinates(self):
        data = {"latitude": 51.2, "longitude": 1.512}
        fixed = {"latitude": 51.00002, "longitude": 1.00512}
        assert f.zero_pad_coordinates({}, data) == fixed

        data = {"latitude": 51.12345, "longitude": 1.54321}
        fixed = {"latitude": 51.12345, "longitude": 1.54321}
        assert f.zero_pad_coordinates({}, data) == fixed

        data = {"latitude": 51.00001, "longitude": 1.00015}
        fixed = {"latitude": 51.00001, "longitude": 1.00015}
        assert f.zero_pad_coordinates({}, data) == fixed

        data = {"latitude": 51.1, "longitude": 1.21}
        fixed = {"latitude": 51.0001, "longitude": 1.0021}
        config = {"width": 4}
        assert f.zero_pad_coordinates(config, data) == fixed

        data = {"latitude": 51.1, "longitude": 1.21}
        fixed = {"latitude": 51.0001, "longitude": 1.21}
        config = {"width": 4, "fields": ["latitude"]}
        assert f.zero_pad_coordinates(config, data) == fixed

        data = {"latitude": 51.1}
        assert_raises(ValueError, f.zero_pad_coordinates, {}, data)

        data = {"latitude": 51.1, "longitude": 1.21}
        config = {"fields": ["latitude", "a"]}
        assert_raises(ValueError, f.zero_pad_coordinates, config, data)

    def test_zero_pad_times(self):
        data = "$$A,1,12:8:3\n"
        fixed = "$$A,1,12:08:03\n"
        config = {"checksum": "none"}
        assert f.zero_pad_times(config, data) == fixed

        data = "$$A,1,2:3\n"
        fixed = "$$A,1,02:03\n"
        config = {"checksum": "none"}
        assert f.zero_pad_times(config, data) == fixed

        data = "$$A,1,2,3,1:2:3\n"
        fixed = "$$A,1,2,3,01:02:03\n"
        config = {"checksum": "none", "field": 4}
        assert f.zero_pad_times(config, data) == fixed

        data = "$$A,1,2:3:4*1503\n"
        fixed = "$$A,1,02:03:04*CF8C\n"
        assert f.zero_pad_times({}, data) == fixed

        data = "$$A,1,2:3:4*45\n"
        fixed = "$$A,1,02:03:04*75\n"
        config = {"checksum": "xor"}
        assert f.zero_pad_times(config, data) == fixed

        data = "$$A\n"
        assert_raises(ValueError, f.zero_pad_times, {}, data)

        data = "$$A,1,120604\n"
        assert_raises(ValueError, f.zero_pad_times, {}, data)

        data = "$$HABE,528,12:6:43,52.3903,-2.2947,10899*0F\n"
        fixed = "$$HABE,528,12:06:43,52.3903,-2.2947,10899*3F\n"
        config = {"checksum": "xor"}
        assert f.zero_pad_times(config, data) == fixed
