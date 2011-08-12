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
from habitat.parser.sensors import base

class TestBaseSensors:
    def test_ascii_ints(self):
        assert base.ascii_int(None, "12") == 12
        assert base.ascii_int(None, "012") == 12

    def test_ascii_ints_with_empty_strings(self):
        assert base.ascii_int(None, "") == None

    @raises(ValueError)
    def test_ascii_ints_with_invalid_strings(self):
        base.ascii_int(None, "NOT AN INT")

    def test_ascii_floats(self):
        assert base.ascii_float(None, "12") == 12.0
        assert base.ascii_float(None, "12.3") == 12.3
        assert base.ascii_float(None, "0.1") == 0.1
    
    def test_ascii_floats_with_empty_strings(self):
        assert base.ascii_float(None, "") == None

    @raises(ValueError)
    def test_ascii_floats_with_invalid_strings(self):
        base.ascii_float(None, "NOT A FLOAT")

    def test_strings(self):
        assert base.string(None, "hello") == "hello"
        assert base.string(None, "123") == "123"
