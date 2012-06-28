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
Tests the stdtelem sensor functions
"""

from nose.tools import raises
from ...sensors import stdtelem


class TestStdtelem:
    def test_valid_times(self):
        times = [
            ("12:00:00", "12:00:00"),
            ("11:15:10", "11:15:10"),
            ("00:00:00", "00:00:00"),
            ("23:59:59", "23:59:59"),
            ("12:00",  "12:00:00"),
            ("01:24",  "01:24:00"),
            ("123456", "12:34:56"),
            ("0124",   "01:24:00")
        ]

        for i in times:
            assert stdtelem.time(i[0]) == i[1]

    @raises(ValueError)
    def check_invalid_time(self, s):
        stdtelem.time(s)

    def test_invalid_times(self):
        invalid_times = [
            "1:12", "12:2", "1:12:56", "04:42:5", "12:2:25",
            "001:12", "12:002", "001:12:56", "04:42:005", "12:005:25",
            "24:00", "25:00", "11:60", "11:62", "24:12:34", "35:12:34",
            "12:34:66", "12:34:99", "126202", "1234567", "123"
        ]
        for i in invalid_times:
            self.check_invalid_time(i)

    def test_coordinate(self):
        coordinates = [
            ("dd.dddd", "+12.1234", 12.1234),
            ("dd.dddd", " 001.3745", 1.3745),
            ("dd.dddd", "1.37", 1.37),
            ("ddmm.mm", "-3506.192", -35.1032),
            ("ddmm.mm", "03506.0", 35.1),
            ("ddd.dddddd", "+12.1234", 12.1234),
            ("dddmm.mmmm", "-3506.192", -35.1032),
            ("dddmm.mmmm", "-2431.5290", -24.5254833),
            ("dddmm.mmmm", "2431.529", 24.525483),
            ("dddmm.mmmm", "-2431.0", -24.5167)
        ]
        for i in coordinates:
            config = {"format": i[0], "miscellania": True, "asdf": 1234}
            assert stdtelem.coordinate(config, i[1]) == i[2]

    @raises(ValueError)
    def test_wants_config(self):
        stdtelem.coordinate({}, "001.1234")

    @raises(ValueError)
    def check_invalid_coordinate(self, s):
        config = {"format": s[0]}
        stdtelem.coordinate(config, s[1])

    def test_invalid_coordinates(self):
        invalid_coordinates = [
            ("dd.dddd", "asdf"),
            ("ddmm.mm", "03599.1234"),
            ("ddmm.mm", "-12")
        ]
        for i in invalid_coordinates:
            self.check_invalid_coordinate(i)
