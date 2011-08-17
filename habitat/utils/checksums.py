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

"""Various checksum calculation utilities."""

import crcmod
from operator import xor as op_xor

__all__ = ["crc16_ccitt", "xor", "fletcher_16"]

def crc16_ccitt(data):
    """
    Calculate the CRC16 CCITT checksum of *data*.

    (CRC16 CCITT: start 0xFFFF, poly 0x1021)
    """
    crc16 = crcmod.predefined.mkCrcFun('crc-ccitt-false')
    return hex(crc16(data))[2:].upper().zfill(4)

def xor(data):
    """Calculate the XOR checksum of *data*."""
    numbers = map(ord, data)
    return hex(reduce(op_xor, numbers))[2:].upper().zfill(2)

def fletcher_16(data, modulus=255):
    """Calculate the Fletcher-16 checksum of *data*, default modulus 255."""
    numbers = map(ord, data)
    a = b = 0
    for number in numbers:
        a += number
        b += a
    a %= modulus
    b %= modulus
    return hex((a << 8) | b)[2:].upper().zfill(4)
