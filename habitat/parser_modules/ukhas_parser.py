# Copyright 2010, 2011 (C) Adam Greig, Daniel Richman
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

The protocol is most succinctly described as::

    $$<callsign>,<data>,<data>,...,<data>*<checksum>

The typical minimum telemetry string is::

    $$<callsign>,<message number>,<time>,<latitude>,<longitude>,<altitude>,\
<data>,...,<data>*<checksum>

The number of custom data fields and their types are configurable.

Data fields are typically human readable (or at the least ASCII) readings
of sensors or other system information. See the :py:mod:`habitat.sensors`
module for more information on supported formats.

Checksums work on the message content between the ``$$`` and the ``*``,
non-inclusive, and are given as hexadecimal (upper or lower case) after
the ``*`` in the message.

Supported checksums are CRC16-CCITT with polynomial 0x1021 and start 0xFFFF,
Fletcher-16 and an 8bit XOR over the characters. The corresponding values
for configuration are ``crc16-ccitt``, ``fletcher-16`` and ``xor``.
For compatibility, a varient of Fletcher16 using modulus 256 is also provided,
as ``fletcher-16-256``. Don't use it for new payloads.
``none`` may also be specified as a checksum type if no checksum is used; in
this case the message should not include a terminating ``*``.

.. seealso:: :ref:`ukhas-parser-config`

"""

import re

from ..parser import ParserModule, CantParse
from ..utils import checksums

checksum_algorithms = [
    "crc16-ccitt", "xor", "fletcher-16", "fletcher-16-256", "none"]


class UKHASParser(ParserModule):
    """The UKHAS Parser Module"""

    string_exp = re.compile("^[\\x20-\\x7E]+$")
    callsign_exp = re.compile("^[a-zA-Z0-9/_\\-]+$")
    checksum_exp = re.compile("^[a-fA-F0-9]+$")

    def _split_basic_format(self, string):
        """
        Verify the basic format and content, and split up the telemetry.

        It:

         - Verifies that the string is long enough to not trip up later,
         - which means 8 characters.
         - Checks the string starts with $$, ends with * and a checksum.
         - Checks the string for non ascii chars
         - Checks the checksum for non hex digits

        It then returns (string, checksum) with delimiters '$$' '*' and '\\n'
        discarded.

        Raises :py:exc:`ValueError <exceptions.ValueError>` on error.
        """

        if len(string) < 8:
            raise ValueError("String is less than 8 characters.")
        if string[:2] != "$$":
            raise ValueError("String does not start `$$'.")
        if string[-1] != "\n":
            raise ValueError("String does not end with '\\n'")

        string = string[2:-1]

        if not self.string_exp.search(string):
            raise ValueError("String contains characters that are not "
                             "printable ASCII.")

        string, checksum = self._split_checksum(string)
        if checksum and not self.checksum_exp.search(checksum):
            raise ValueError("Checksum found but contained non-hex digits.")

        return string, checksum

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

        fields = string.split(",")
        if len(fields) < 2:
            raise ValueError("No fields found.")
        return fields

    def _verify_config(self, config):
        """
        Checks the provided *config* dict.

        This method checks that the *config* dict contains all the
        required information.

        Raises :py:exc:`ValueError <exceptions_raw.ValueError>` otherwise.
        """

        try:
            field_names = ["payload"]
            if config["protocol"] != "UKHAS":
                raise ValueError(
                    "Configuration document is not for UKHAS parser.")
            if config["checksum"] not in checksum_algorithms:
                raise ValueError("Specified checksum algorithm is invalid.")
            if len(config["fields"]) < 1:
                raise ValueError("No fields are defined.")
            for field in config["fields"]:
                field["name"]
                field["sensor"]
                if field["name"][0] == "_":
                    raise ValueError("Field name starts with an underscore.")
                field_names.append(field["name"])
            if len(field_names) != len(set(field_names)):
                raise ValueError("Duplicate field name.")
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

    def _parse_field(self, field, config):
        """
        Parse a *field* string using its configuration dictionary.

        Return the name from the config and the appropriately parsed data.
        :py:exc:`ValueError <exceptions.ValueError>` is raised in invalid
        inputs.
        """

        name = config["name"]
        sensor = 'sensors.' + config["sensor"]

        try:
            data = self.loadable_manager.run(sensor, config, field)
        except (ValueError, KeyError) as e:
            # Annotate error with the field name.
            error_type = type(e)
            raise error_type("(field {f}): {e!s}".format(f=name, e=e))

        return name, data

    def pre_parse(self, string):
        """
        Check if *string* is parsable by this module.

        If it is, :meth:`pre_parse` extracts the payload
        name and return it. Otherwise, a
        :exc:`ValueError <exceptions.ValueError>` is raised.
        """

        try:
            string, checksum = self._split_basic_format(string)
            fields = self._extract_fields(string)
            self._verify_callsign(fields[0])
        except (ValueError, KeyError):
            raise CantParse
        return fields[0]

    def parse(self, string, config):
        """
        Parse *string*, extracting processed field data.

        *config* is a dictionary containing the sentence dictionary
        from the payload's configuration document.

        Returns a dictionary of the parsed data, with field names as
        keys and the result as the value. Also inserts a ``payload`` field
        containing the payload name, and an ``_sentence`` field containing
        the ASCII sentence that data was parsed from.

        :py:exc:`ValueError <exceptions.ValueError>` is raised on invalid
        messages.
        """
        self._verify_config(config)
        strippedstring, checksum = self._split_basic_format(string)
        self._verify_checksum(strippedstring, checksum, config["checksum"])

        fields = self._extract_fields(strippedstring)
        self._verify_callsign(fields[0])

        if len(fields) - 1 != len(config["fields"]):
            raise ValueError("Incorrect number of fields (got {0}, expect {1})"
                    .format(len(fields) - 1, len(config["fields"])))

        output = {"payload": fields[0], "_sentence": string}
        for field, field_config in zip(fields[1:], config["fields"]):
            name, data = self._parse_field(field, field_config)
            output[name] = data
        return output
