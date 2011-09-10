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
Tests common filters
"""

import habitat.filters as f

class TestFilters:
    def test_semicolons_to_commas(self):
        data = "$$testpayload,1,2,3;4;5;6*8A24"
        fixed = f.semicolons_to_commas(data, {})
        assert fixed == "$$testpayload,1,2,3,4,5,6*888F"

    def test_numeric_scale(self):
        config = {"source": "key", "factor": (1.0/7.0)}
        data = {"key": 49, "something": True}
        fixed = f.numeric_scale(data, config)
        assert fixed == {"key": 7, "something": True}

    def test_simple_map(self):
        config = {"source": "key", "destination": "key_thing",
                  "map": {48: "test", 49: "something"}}
        data = {"key": 49}
        fixed = f.simple_map(data, config)
        assert fixed == {"key": 49, "key_thing": "something"}
