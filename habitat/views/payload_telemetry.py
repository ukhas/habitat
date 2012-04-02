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
Functions for the payload_telemetry design document.

Contains schema validation and a view by flight, payload and received time.
"""

import math
from couch_named_python import Forbidden
from .utils import rfc3339_to_timestamp, validate_doc, read_json_schema

schema = None

def _check(new, old):
    """
    Raise an error if any items in old are not present unchanged in new.
    """
    for k in old:
        if k == u'_rev':
            continue
        if k not in new:
            raise Forbidden("You may not remove objects.")
        if isinstance(old[k], dict):
            _check(new[k], old[k])
        else:
            if new[k] != old[k]:
                raise Forbidden("You may not edit existing items.")

def validate(new, old, userctx, secobj):
    """
    Validate this payload_telemetry document against the schema, then check
    that new is strictly a superset of old (except for _rev).
    """
    global schema
    if not schema:
        schema = read_json_schema("payload_telemetry.json")
    if 'type' in new and new['type'] == "payload_telemetry":
        validate_doc(new, schema)
    _check(new, old)

def flight_payload_estimated_received_time_map(doc):
    """Map by flight, payload, estimated received time."""
    if 'type' not in doc or doc['type'] != "payload_telemetry":
        return
    if 'data' not in doc or '_parsed' not in doc['data']:
        return

    sum_x, sum_x2, n = 0, 0, 0

    for callsign in doc['receivers']:
        x = rfc3339_to_timestamp(doc['receivers'][callsign]['time_created'])
        sum_x += x
        sum_x2 += x * x
        n += 1

    mean = sum_x / n
    std_dev = math.sqrt((sum_x2 / n) - (mean * mean))

    new_sum_x, new_n = 0, 0

    for callsign in doc['receivers']:
        x = rfc3339_to_timestamp(doc['receivers'][callsign]['time_created'])
        if math.abs(x - mean) > std_dev:
            continue
        new_sum_x += x
        new_n += 1

    estimated_time = new_sum_x / new_n if new_n != 0 else mean
    
    val = None
    if '_sentence' in doc['data']:
        val = doc['data']['_sentence']

    yield (doc['data']['_flight'], doc['data']['payload'], estimated_time), val

