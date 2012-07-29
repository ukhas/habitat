# Copyright 2011 (C) Adam Greig
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
Tests the base sensor functions
"""

from nose.tools import raises
from ...sensors import base


class TestBaseSensors:
    def test_ascii_ints(self):
        assert base.ascii_int("12") == 12
        assert base.ascii_int("012") == 12

    @raises(ValueError)
    def test_ascii_ints_with_invalid_strings(self):
        base.ascii_int("NOT AN INT")

    def test_ascii_floats(self):
        assert base.ascii_float("12") == 12.0
        assert base.ascii_float("12.3") == 12.3
        assert base.ascii_float("0.1") == 0.1

    @raises(ValueError)
    def test_ascii_floats_with_invalid_strings(self):
        base.ascii_float("NOT A FLOAT")

    def test_strings(self):
        assert base.string("hello") == "hello"
        assert base.string("123") == "123"

    @raises(ValueError)
    def test_bad_constant(self):
        base.constant({"expect": "right"}, "wrong")

    def test_good_constant(self):
        assert base.constant({"expect": "right"}, "right") == None

    @raises(ValueError)
    def test_bad_empty_constant(self):
        assert base.constant({}, "something") == None

    def test_good_empty_constant(self):
        assert base.constant({}, "") == None

    def test_strings(self):
        assert base.string("hello") == "hello"
        assert base.string("123") == "123"
