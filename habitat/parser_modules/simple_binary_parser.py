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
This module contains a parser for a generic and simple binary protocol. The
protocol does not specify callsigns or checksums, so the assumption is that
both are provided in an outer protocol layer or out of band. Any binary data
that python's struct.unpack may interpret is usable.

Any fields may be submitted but it is recommended that a GPS-provided latitude,
longitude and time are submitted.

The configuration document should specify the format string, a name and
optionally a sensor for each field in the data. The format strings will be
concatenated to unpack the data. A format string prefix may be provided as the
``format_prefix`` key in the configuration, to specify byte order, size and
alignment. Note that at present each field must map to precisely one format
string argument, so while variable length strings are OK, a field cannot have,
for instance, two integers.

Example ``payload_configuration.sentences[0]``::

    {
        "protocol": "simple_binary",
        "callsign": "1234567890",
        "format_prefix": "<",
        "fields": [
            {
                "format": "i",
                "name": "latitude"
            }, {
                "format": "i",
                "name": "longitude"
            }, {
                "format": "I",
                "name": "date",
                "sensor": "std_telem.binary_timestamp"
            }, {
                "format": "b",
                "name": "temperature"
            }
        ],
        "filters": {
            "post": [
                {
                    "type": "normal",
                    "filter": "common.numeric_scale",
                    "source": "latitude",
                    "scale": 1E-7
                },
                {
                    "type": "normal",
                    "filter": "common.numeric_scale",
                    "source": "longitude",
                    "scale": 1E-7
                }
            ]
        }
    }

For the list of format string specifiers, please see:
`<http://docs.python.org/2/library/struct.html>`_.

The filter ``common.numeric_scale`` may be useful for fixed-point data rather
than sending floats, and the various ``std_telem.binary*`` sensors may be
applicable.
"""

import struct
from ..parser import ParserModule, CantExtractCallsign

class SimpleBinaryParser(ParserModule):
    """The Simple Binary Parser Module"""

    def pre_parse(self, string):
        """
        As no callsign is provided by the protocol, assume any string we are
        given is potentially parseable binary data.
        """
        raise CantExtractCallsign()

    def _verify_config(self, config):
        """
        Checks that the provided *config* dict is appropriate for this parser.
        """
        if config["protocol"] != "simple_binary":
            raise ValueError("Configuration document has wrong protocol.")
        if "fields" not in config:
            raise ValueError("Config document missing required key `fields'")
        field_names = []
        for idx, field in enumerate(config["fields"]):
            if "name" not in field or "format" not in field:
                raise ValueError("Field {0} config missing name or format."
                                 .format(idx))
            if field["name"][0] == "_":
                raise ValueError("Field {0} name starts with an underscore."
                                 .format(idx))
            field_names.append(field["name"])
        if len(field_names) != len(set(field_names)):
            raise ValueError("Duplicate field name.")

    def _parse_field(self, field, config):
        """
        Pass off the data from unpacking the binary to the sensor given in
        the configuration for actual parsing.
        """
        name = config["name"]
        if 'sensor' not in config:
            return name, field
        sensor = 'sensors.' + config["sensor"]
        try:
            data = self.loadable_manager.run(sensor, config, field)
        except (ValueError, KeyError) as e:
            error_type = type(e)
            raise error_type("(field {f}): {e!s}".format(f=name, e=e))

        return name, data

    def parse(self, data, config):
        """
        Parse *string*, extracting processed field data.
        
        *config* is the relevant sentence dictionary from the payload's
        configuration document, containing the required binary format and field
        details.

        Returns a dictionary of the parsed data.

        ValueError is raised on invalid messages.
        """
        self._verify_config(config)
        prefix = [config["format_prefix"]] if "format_prefix" in config else []
        fmtstring = ''.join(prefix + [f["format"] for f in config["fields"]])
        
        try:
            data = struct.unpack(str(fmtstring), data)
        except struct.error as exp:
            raise ValueError("Could not unpack binary data: {0}".format(exp))
        
        if len(data) != len(config["fields"]):
            raise ValueError(
                "Number of extracted fields does not match config"
                " (got {0}, expected {1}).".format(
                len(data), len(config["fields"])))
        
        output = {}
        for field, field_config in zip(data, config["fields"]):
            name, data = self._parse_field(field, field_config)
            output[name] = data

        return output
