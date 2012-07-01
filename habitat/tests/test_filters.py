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
        assert f.invalid_always(data) == {"key": 1235, "fix_invalid": True}

    def test_invalid_location_zero(self):
        data = {"latitude": 12.12, "longitude": 3.14}
        assert f.invalid_location_zero(data.copy()) == data
        data = {"latitude": 0, "longitude": 0}
        expect = data.copy()
        expect.update({"fix_invalid": True})
        assert f.invalid_location_zero(data) == expect

    def test_invalid_gps_lock(self):
        config = {"ok": [3, 4, "steve"]}
        assert f.invalid_gps_lock(config, {"gps_lock": 1}) == \
                {"gps_lock": 1, "fix_invalid": True}
        assert f.invalid_gps_lock(config, {"gps_lock": 4}) == \
                {"gps_lock": 4}
        assert f.invalid_gps_lock(config, {"gps_lock": "barry"}) == \
                {"gps_lock": "barry", "fix_invalid": True}
        assert f.invalid_gps_lock(config, {"gps_lock": "steve"}) == \
                {"gps_lock": "steve"}
