# Copyright 2011 (C) Adam Greig, Daniel Richman
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
This module contains the parser for the UKHAS telemetry protocol format.

``$$<payload>,<data>,<data>,...,<last data>*<checksum>``

The typical minimum telemetry string is:
``$$<payload>,<message number>,<time>,<latitude>,<longitude>,<altitude>,\
<data>,...,<last data>*<checksum>``

The number of custom data fields and their types are configurable.

Data fields are typically human readable (or at the least ASCII) readings
of sensors or other system information. See the :py:mod:`sensors` module
for more information on supported formats.

Checksums work on the message content between the ``$$`` and the ``*``,
non-inclusive, and are given as hexadecimal (upper or lower case) after
the ``*`` in the message.

Supported checksums are CRC16-CCITT with polynomial 0x1021 and start 0xFFFF,
Fletcher-16 and an 8bit XOR over the characters. The corresponding values
for configuration are 'crc16-ccitt', 'fletcher-16' and 'xor'.
For compatibility, a varient of Fletcher16 using modulus 256 is also provided,
as 'fletcher-16-256'. Don't use it for new payloads.
'none' may also be specified as a checksum type if no checksum is used; in
this case the message should not include a terminating ``*``.

Typical configuration (part of a payload dictionary in a flight document):

.. code-block:: javascript

    "habitat": {
        "radio": {
            "frequency": 434.075,
            "mode": "usb",
        },
        "telemetry": {
            "modulation": "rtty",
            "shift": 425,
            "encoding": "ascii-8",
            "baud": 50,
            "parity": "none",
            "stop": 1
        },
        "sentence": {
            "protocol": "UKHAS",
            "checksum": "crc16-ccitt",
            "fields": [
                {
                    "name": "message_count",
                    "type": "base.ascii_int"
                }, {
                    "name": "time",
                    "type": "stdtelem.time"
                }, {
                    "name": "latitude",
                    "type": "stdtelem.coordinate",
                    "format": "dd.dddd"
                }, {
                    "name": "longitude",
                    "type": "stdtelem.coordinate",
                    "format": "dd.dddd"
                }, {
                    "name": "altitude",
                    "type": "base.ascii_int"
                }, {
                    "name": "speed",
                    "type": "base.ascii_float"
                }, {
                    "name": "internal_temperature",
                    "type": "base.ascii_float"
                }
            ]
        }
    }

"""

import time
import math
import re
from string import ascii_lowercase, ascii_uppercase, digits, hexdigits

from habitat.parser import ParserModule
from habitat.utils import checksums

__all__ = ["UKHASParser"]

checksum_algorithms = [
    "crc16-ccitt", "xor", "fletcher-16", "fletcher-16-256", "none"]

class UKHASParser(ParserModule):
    """The UKHAS Parser Module"""

    string_exp = re.compile("^[\\x20-\\x7E]+$")
    callsign_exp = re.compile("^[a-zA-Z0-9]+$")

    def _split_checksum(self, string):
        """
        Splits off a two or four digit checksum from the end of the string.

        Returns a list of the start of the string and the checksum, discarding
        the ``*`` separator between the two. Returns :py:data:`None` for the
        checksum if no ``*`` was found.
        """

        if string[-3] == '*':
            return [string[:-3], string[-2:]]
        elif string[-5] == '*':
            return [string[:-5], string[-4:]]
        else:
            return [string, None]

    def _extract_fields(self, string):
        """
        Splits the string into comma-separated fields.

        Raises a :py:exc:`ValueError <exceptions.ValueError>` if no
        fields were found.
        """

        string = string[2:]
        string, checksum = self._split_checksum(string)
        fields = string.split(",")
        if len(fields) < 2:
            raise ValueError("No fields found.")
        return fields

    def _verify_basic_format(self, string):
        """
        Check the string starts with $$, ends with * and a checksum.

        Verify that the string is at least long enough to not trip up later,
        which means 7 characters.

        Raises :py:exc:`ValueError <exceptions.ValueError>` on error.
        """
        if not self.string_exp.search(string):
            raise ValueError("String contains characters that are not "
                             "printable ASCII.")
        if len(string) < 7:
            raise ValueError("String is less than 7 characters.")
        if string[:2] != "$$":
            raise ValueError("String does not start `$$'.")
        string, checksum = self._split_checksum(string)
        if checksum:
            for letter in checksum:
                if letter not in hexdigits:
                    raise ValueError(
                        "Checksum found but contained non-hexadecimal digits.")

    def _verify_config(self, config):
        """
        Checks the provided *config* dict.

        This method checks that the *config* dict contains all the
        required information.

        Raises :py:exc:`ValueError <exceptions.ValueError>` otherwise.
        """

        try:
            if config["protocol"] != "UKHAS":
                raise ValueError(
                    "Configuration document is not for UKHAS parser.")
            if config["checksum"] not in checksum_algorithms:
                raise ValueError("Specified checksum algorithm is invalid.")
            if len(config["fields"]) < 1:
                raise ValueError("Less than one fields are defined.")
            for field in config["fields"]:
                field["name"]
                field["type"]
                if field["name"][0] == "_":
                    raise ValueError("Field name starts with an underscore.")
        except (KeyError, TypeError):
            raise ValueError("Invalid configuration document.")

    def _verify_checksum(self, string, checksum, algorithm):
        """
        Verifies *string*'s checksum.

        Computes the checksum defined by *algorithm* over *string*
        and compares it to that given in *checksum*.
        Raises :py:exc:`ValueError <exceptions.ValueError>`
        on discrepancy.
        """

        if checksum == None and algorithm != "none":
            raise ValueError("No checksum found but config specifies one.")
        elif algorithm == "crc16-ccitt":
            if checksums.crc16_ccitt(string) != checksum.upper():
                raise ValueError("Invalid CRC16-CCITT checksum.")
        elif algorithm == "xor":
            if checksums.xor(string) != checksum.upper():
                raise ValueError("Invalid XOR checksum.")
        elif algorithm == "fletcher-16":
            if checksums.fletcher_16(string) != checksum.upper():
                raise ValueError("Invalid Fletcher-16 checksum.")
        elif algorithm == "fletcher-16-256":
            if checksums.fletcher_16(string, 256) != checksum.upper():
                raise ValueError("Invalid Fletcher-16-256 checksum.")

    def _verify_callsign(self, callsign):
        if not self.callsign_exp.search(callsign):
            raise ValueError("Invalid callsign, contains characters "
                             "besides A-Z and 0-9.")

    def _parse_field(self, field, field_config):
        """
        Parse a *field* string using its configuration dictionary.

        Return the name from the config and the appropriately parsed data.
        :py:exc:`ValueError <exceptions.ValueError>` is raised in invalid
        inputs.
        """

        field_name = field_config["name"]
        field_type = field_config["type"]
        field_data = self.sensors.parse(field_type, field_config, field)
        return [field_name, field_data]

    def pre_parse(self, string):
        """
        Check if this message is parsable by this module.

        If the message is pasable, **pre_parse** extracts the payload
        name and return it. Otherwise, a
        :py:exc:`ValueError <exceptions.ValueError>` is raised.
        """

        self._verify_basic_format(string)
        fields = self._extract_fields(string)
        self._verify_callsign(fields[0])
        return fields[0]

    def parse(self, string, config):
        """
        Parse the message, extracting processed field data.

        *config* is a dictionary containing the sentence dictionary
        from the payload's configuration document.

        Returns a dictionary of the parsed data, with field names as
        keys and the result as the value. Also inserts a "payload" field
        containing the payload name, a "_extra_data" field if more data
        was in the sentence but not in the configuration, so could not be
        parsed, and an _sentence field containing the ASCII sentence
        that data was parsed from.

        :py:exc:`ValueError <exceptions.ValueError>` is raised on invalid
        messages. Return a dict of name:data.
        """
        self._verify_config(config)
        self._verify_basic_format(string)
        fields = self._extract_fields(string)
        strippedstring, checksum = self._split_checksum(string[2:])
        self._verify_checksum(strippedstring, checksum, config["checksum"])
        self._verify_callsign(fields[0])
        output = {"payload": fields[0], "_sentence": string}
        for field_num in range(len(fields) - 1):
            try:
                field = fields[field_num + 1]
                field_config = config["fields"][field_num]
            except IndexError:
                # This will happen when config["fields"] does not have
                # enough fields for the sentence, so return everything
                # we haven't been able to parse instead
                output["_extra_data"] = fields[field_num + 1:]
                break
            name, data = self._parse_field(field, field_config)
            output[name] = data
        return output
