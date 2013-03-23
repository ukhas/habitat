# Copyright 2013 (C) Adam Greig
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
This module contains the parser for RockBLOCK units submitting data in a
flexible binary format (anything that Python's struct module can interpret).

Any fields may be submitted but it is recommended that a GPS-provided latitude,
longitude and time are submitted. A message ID is automatically assigned by the
Iridium system so is not required but may be included if desired.

Fields from the RockBLOCK HTTP post will also be output, so that the
Iridium-provided position information is made available.

The following copies will be made automatically if the target key is not in the
configuration fields list, for compatibility with other systems:

``momsn`` -> ``sentence_id``
``transmit_time`` -> ``time`` (and appropriately converted)
``iridium_latitude`` -> ``latitude``
``iridium_longitude`` -> ``longitude``

"""

import json
import struct
import datetime
from ..parser import ParserModule

class RockBLOCKBinaryParser(ParserModule):
    """The RockBLOCK Binary Parser Module"""
    rockblock_keys = ["iridium_cep", "iridium_latitude",
                      "iridium_longitude", "momsn", "transmit_time"]

    def pre_parse(self, string):
        """
        Attempt to extract an IMEI from JSON data in *string*.

        If an IMEI is found and other keys indicative of a RockBLOCK submission
        are also present, the IMEI is returned as the callsign so the parser
        may find the correct configuration document.

        If no IMEI is found or the data does not appear to be from a RockBLOCK
        submission, ValueError is raised.
        """
        data = json.loads(string)
        if "imei" not in data:
            raise ValueError("No IMEI available.")
        for k in self.rockblock_keys:
            if k not in data:
                raise ValueError("Expected key '{0}' not found.".format(k))
        return data["imei"]

    def _verify_config(self, config):
        """
        Checks that the provided *config* dict is appropriate for this parser.
        """
        if config["protocol"] != "RockBLOCK Binary":
            raise ValueError("Configuration document has wrong protocol.")
        if "format" not in config or "fields" not in config:
            raise ValueError("Config document missing required field")
        field_names = []
        for field in config["fields"]:
            if "name" not in field or "sensor" not in field:
                raise ValueError("Field config missing required key.")
            if field["name"][0] == "_":
                raise ValueError("Field name starts with an underscore.")
            field_names.append(field["name"])
        if len(field_names) != len(set(field_names)):
            raise ValueError("Duplicate field name.")

    def _parse_field(self, field, config):
        """
        Pass off the data from unpacking the binary to the sensor given in
        the configuration for actual parsing.
        """
        name = config["name"]
        sensor = 'sensors.' + config["sensor"]
        try:
            data = self.loadable_manager.run(sensor, config, field)
        except (ValueError, KeyError) as e:
            error_type = type(e)
            raise error_type("field {f}): {e!s}".format(f=name, e=e))

        return name, data

    def _copy_iridium(self, data, output):
        """
        If any missing keys in *output* can be usefully filled in by data
        provided by the Iridium / RockBLOCK system, do so.
        """
        if "sentence_id" not in output:
            output["sentence_id"] = int(data["momsn"])
        if "time" not in output:
            txt = data["transmit_time"]
            tc = datetime.datetime.strptime(txt, "%y-%m-%d %H:%M:%S")
            output["time"] = tc.strftime("%H:%M:%S")
        if "latitude" not in output:
            output["latitude"] = float(data["iridium_latitude"])
        if "longitude" not in output:
            output["longitude"] = float(data["iridium_longitude"])

    def parse(self, string, config):
        """
        Parse *string*, extracting processed field data.
        
        *config* is the relevant sentence dictionary from the payload's
        configuration document, containing the required binary format and field
        details.

        Returns a dictionary of the parsed data.

        ValueError is raised on invalid messages.
        """
        self._verify_config(config)
        data = json.loads(string)
        
        try:
            data = struct.unpack(config["format"], data["data"])
        except struct.error as exp:
            raise ValueError("Could not unpack binary data: {0}".format(exp))
        
        if len(data) != len(config["fields"]):
            raise ValueError(
                "Number of extracted fields does not match config"
                " (got {0}, expected {1}).".format(
                len(data), len(config["fields"])))
        
        output = {}
        for k in self.rockblock_keys:
            output[k] = data[k]

        for field, field_config in zip(data, config["fields"]):
            name, data = self._parse_field(field, field_config)
            output[name] = data

        self._copy_iridium(data, output)

        return output
