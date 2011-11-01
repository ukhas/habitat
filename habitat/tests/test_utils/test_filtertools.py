# Copyright 2010 (C) Adam Greig
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

from ...utils import filtertools


class TestUKHASChecksumFixer:
    """UKHAS Checksum Fixer"""
    def test_leaves_bad_data(self):
        data = {"data": "$$habitat,bad*ABCD"}
        with filtertools.UKHASChecksumFixer("crc16-ccitt", data) as c:
            c["data"] = "$$habitat,good*ABCD"
        assert c["data"] == "$$habitat,bad*ABCD"

    def test_updates_checksum(self):
        data = {"data": "$$habitat,good*4918"}
        with filtertools.UKHASChecksumFixer("crc16-ccitt", data) as c:
            c["data"] = "$$habitat,other*4918"
        assert c["data"] == "$$habitat,other*2E0C"

    def test_updates_xor_checksum(self):
        data = {"data": "$$habitat,good*4c"}
        with filtertools.UKHASChecksumFixer("xor", data) as c:
            c["data"] = "$$habitat,other*4c"
        assert c["data"] == "$$habitat,other*2B"

    def test_leaves_when_protocol_is_none(self):
        data = {"data": "$$habitat,boring"}
        with filtertools.UKHASChecksumFixer("none", data) as c:
            c["data"] = "$$habitat,sucky"
        assert c["data"] == "$$habitat,sucky"
