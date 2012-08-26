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
        self.check_fixer("crc16-ccitt", "$$habitat,bad*ABCD\n",
            "$$habitat,good*ABCD\n", "$$habitat,bad*ABCD\n")

    def test_updates_checksum(self):
        self.check_fixer("crc16-ccitt", "$$habitat,good*4918\n",
            "$$habitat,other*4918\n", "$$habitat,other*2E0C\n")

    def test_updates_xor_checksum(self):
        self.check_fixer("xor", "$$habitat,good*4c\n",
            "$$habitat,other*4c\n", "$$habitat,other*2B\n")

    def test_leaves_when_protocol_is_none(self):
        self.check_fixer("none", "$$habitat,boring\n",
            "$$habitat,sucky\n", "$$habitat,sucky\n")

    def check_fixer(self, protocol, old, new, expect):
        data = {"data": old}
        with filtertools.UKHASChecksumFixer(protocol, data) as c:
            c["data"] = new
        assert c["data"] == expect
        assert filtertools.UKHASChecksumFixer.fix(protocol, old, new) == expect
