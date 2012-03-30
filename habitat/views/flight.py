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

"""
Functions for the flight design document.

Contains schema validation and views by flight launch time, window end time and
payload name and window end time.
"""

from .utils import rfc3339_to_timestamp, validate_doc, read_json_schema

schema = None

def validate(new, old, userctx, secobj):
    """
    Validate this flight document against the schema.
    TODO: handle flight document test/approval/other status.
    TODO: value based validation
    """
    global schema
    if not schema:
        schema = read_json_schema("flight.json")
    if new['type'] == "flight":
        validate_doc(new, schema)

def end_map(doc):
    """Map by flight window end date."""
    if doc['type'] == "flight":
        yield rfc3339_to_timestamp(doc['end']), None

def launch_time_map(doc):
    """Map by flight launch time."""
    if doc['type'] == "flight":
        yield doc['launch']['time'], None

def payload_end_map(doc):
    """Map by payload and then flight window end date."""
    if doc['type'] == "flight":
        for payload in doc['payloads']:
            yield (payload, rfc3339_to_timestamp(doc['end'])), None

