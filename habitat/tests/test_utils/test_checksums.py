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

from ...utils import checksums


class TestChecksums:
    def setUp(self):
        self.data = "hello, world"

    def test_calculates_crc16_ccitt_checksum(self):
        assert checksums.crc16_ccitt(self.data) == "D4C0"

    def test_calculates_xor_checksum(self):
        assert checksums.xor(self.data) == "0C"

    def test_calculates_fletcher_16_checksum(self):
        assert checksums.fletcher_16(self.data) == "8C65"

    def test_calculates_fletcher_16_checksum_modulus_256(self):
        assert checksums.fletcher_16(self.data, 256) == "8848"
