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

"""Various utilities for filters to call upon."""

from . import checksums


class UKHASChecksumFixer(object):
    """
    A utility to help filters modify data that has been checksummed. It may be
    used as a context manager or via a class method.

    For use as a context manager:

    Specify the protocol in use with *protocol* and pass in the string being
    modified as ``data["data"]``, then use the return value as a dictionary
    whose ``data`` key you can modify as you desire. On exit, the checksum of
    that string is then updated if the original string's checksum was valid.


    If the original checksum was invalid, the original string is output
    instead.

    >>> data = {"data": "$$hello,world*E408"}
    >>> with UKHASChecksumFixer('crc16-ccitt', data) as fixer:
    ...     fixer["data"] = "$$hi,there,world*E408"
    ...
    >>> fixer["data"]
    '$$hi,there,world*39D3'

    For direct calling as a class method:

    Call UKHASChecksumFixer.fix(protocol, old_data, new_data). The function
    will either return new_data with a fixed checksum if the original checksum
    was valid, or it will return the old_data if the original checksum was
    invalid.

    >>> UKHASChecksumFixer.fix('crc16-ccitt',
    ...                        "$$hello,world*E408", "$$hi,there,world*E408")
    '$$hi,there,world*39D3'
    """

    def __init__(self, protocol, data):
        self.original_data = data["data"]
        self.data = data
        self.protocol = protocol

    def __enter__(self):
        """Give back the dict for the user to modify"""
        return self.data

    def __exit__(self, type, value, traceback):
        """Verify the checksum, update if appropriate"""
        self.data["data"] = self.fix(self.protocol, self.original_data,
                                     self.data["data"])

    @classmethod
    def fix(cls, protocol, old_data, new_data):
        if protocol != "none":
            check_data = cls._split_str(protocol, old_data)
            if check_data[1].upper() == cls._sum(protocol, check_data[0]):
                new_str = cls._split_str(protocol, new_data)[0]
                new_sum = cls._sum(protocol, new_str)
                return "$${0}*{1}\n".format(new_str, new_sum)
            else:
                return old_data
        else:
            return new_data

    @classmethod
    def _sum(cls, protocol, data):
        if protocol == "crc16-ccitt":
            return checksums.crc16_ccitt(data)
        elif protocol == "xor":
            return checksums.xor(data)
        elif protocol == "fletcher-16":
            return checksums.fletcher_16(data)
        elif protocol == "fletcher-16-256":
            return checksums.fletcher_16_256(data)
        else:
            return ""

    @classmethod
    def _sum_length(cls, protocol):
        if protocol == "xor":
            return 2
        elif protocol in ["crc16-ccitt", "fletcher-16", "fletcher-16-256"]:
            return 4
        else:
            return 0

    @classmethod
    def _split_str(cls, protocol, data):
        l = cls._sum_length(protocol)
        return (data[2:-(l + 2)], data[-(l + 1):-1])
