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
    A context manager which helps filters modify data that has been
    checksummed. Tell it what the original protocol was and pass a dict
    containing the data to be mangled in the 'data' key, then use the
    assigned value after entry as a string ignoring its checksum and modify
    it as you please. On exit, if the orignal checksum was valid a new
    and valid checksum will be written to the modified data, otherwise
    the original sentence is placed back into the dict.
    """

    def __init__(self, protocol, data):
        """Store the original data and our protocol"""
        self.original_data = data["data"]
        self.data = data
        self.protocol = protocol

    def __enter__(self):
        """Give back the dict for the user to modify"""
        return self.data

    def __exit__(self, type, value, traceback):
        """Verify the checksum, update if appropriate"""
        if self.protocol != "none":
            checksum_data = self._split_str(self.original_data)
            if checksum_data[1].upper() == self._sum(checksum_data[0]):
                new_string = self._split_str(self.data["data"])[0]
                new_sum = self._sum(new_string)
                self.data["data"] = '$$' + new_string + '*' + new_sum
            else:
                self.data["data"] = self.original_data

    def _sum(self, data):
        if self.protocol == "crc16-ccitt":
            return checksums.crc16_ccitt(data)
        elif self.protocol == "xor":
            return checksums.xor(data)
        elif self.protocol == "fletcher-16":
            return checksums.fletcher_16(data)
        elif self.protocol == "fletcher-16-256":
            return checksums.fletcher_16_256(data)
        else:
            return ""

    def _sum_length(self):
        if self.protocol == "xor":
            return 2
        elif self.protocol in ["crc16-ccitt", "fletcher-16",
                               "fletcher-16-256"]:
            return 4

    def _split_str(self, data):
        l = self._sum_length()
        return (data[2:-(l + 1)], data[-l:])
