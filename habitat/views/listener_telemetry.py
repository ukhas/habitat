# Copyright 2011 (C) Adam Greig
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
Design document for Listener Telemetry docs providing validation and views.
"""

from .utils import rfc3339_to_timestamp, must_be_admin, validate_doc

schema = {
    "title": "Listener Telemetry Document",
    "type": "object",
    "additionalProperties": False,
    "required": True,
    "properties": {
        "type": {
            "type": "string",
            "pattern": "listener_telemetry",
            "required": True
        },
        "time_created": {
            "type": "string",
            "format": "date-time",
            "required": True
        },
        "time_uploaded": {
            "type": "string",
            "format": "date-time",
            "required": True
        },
        "data": {
            "type": "object",
            "required": True,
            "additionalProperties": False,
            "properties": {
                "callsign": {
                    "type": "string",
                    "required": True
                },
                "latitude": {
                    "type": "number",
                    "required": True
                },
                "longitude": {
                    "type": "number",
                    "required": True
                },
                "altitude": {
                    "type": "number",
                    "required": False
                },
                "time": {
                    "type": "object",
                    "required": True,
                    "additionalProperties": False,
                    "properties": {
                        "hour": {
                            "type": "number",
                            "required": True
                        },
                        "minute": {
                            "type": "number",
                            "required": True
                        },
                        "second": {
                            "type": "number",
                            "required": True
                        }
                    }
                }
            }
        }
    }
}

def validate(new, old, userctx, secobj):
    if new['type'] == "listener_telemetry":
        if old:
            must_be_admin(userctx)
        validate_doc(new, schema)

def time_created_callsign_map(doc):
    if doc['type'] == "listener_telemetry":
        tc = rfc3339_to_timestamp(doc['time_created'])
        yield (tc, doc['data']['callsign']), None
