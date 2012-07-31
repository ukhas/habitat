# Copyright 2011, 2012 (C) Adam Greig
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
from couch_named_python import ForbiddenError, UnauthorizedError, version
from .utils import rfc3339_to_timestamp, validate_doc, read_json_schema

schema = None

def _check_only_new(new, old):
    """
    Raise an error if any items in old are not present unchanged in new.
    """
    for k in old:
        if k == u'_rev':
            continue
        if k not in new:
            raise ForbiddenError("You may not remove objects.")
        if isinstance(old[k], dict):
            _check_only_new(new[k], old[k])
        else:
            if new[k] != old[k]:
                raise ForbiddenError("You may not edit existing items.")

@version(1)
def validate(new, old, userctx, secobj):
    """
    Validate this payload_telemetry document against the schema, then perform
    some specific checks:

    * Admins may perform any further editing
    * If edited
        * Only the parser may add new fields to data
        * The receivers list may only get new receivers
    * If created
        * Must have one receiver
        * Must have _raw and nothing but _raw in data
    """
    global schema
    if not schema:
        schema = read_json_schema("payload_telemetry.json")
    if 'type' in new and new['type'] == "payload_telemetry":
        validate_doc(new, schema)

    if '_admin' in userctx['roles']:
        return

    if old:
        if new['data'] != old['data'] and 'parser' not in userctx['roles']:
            raise UnauthorizedError("Only the parser may add data to an"
                                    " existing document.")
        for receiver in old['receivers']:
            if (receiver not in new['receivers'] or
               new['receivers'][receiver] != old['receivers'][receiver]):
                   raise ForbiddenError("May not edit or remove receivers.")
    else:
        if len(new['receivers']) != 1:
            raise ForbiddenError("New documents must have exactly one"
                                 "receiver.")
        if new['data'].keys() != ['_raw']:
            raise ForbiddenError("New documents may only have _raw in data.")


def _estimate_time_received(receivers):
    sum_x, sum_x2, n = 0, 0, 0

    for callsign in receivers:
        x = rfc3339_to_timestamp(receivers[callsign]['time_created'])
        sum_x += x
        sum_x2 += x * x
        n += 1

    mean = sum_x / n
    std_dev = math.sqrt((sum_x2 / n) - (mean * mean))

    new_sum_x, new_n = 0, 0

    for callsign in receivers:
        x = rfc3339_to_timestamp(receivers[callsign]['time_created'])
        if abs(x - mean) > std_dev:
            continue
        new_sum_x += x
        new_n += 1

    return new_sum_x / new_n if new_n != 0 else mean

@version(1)
def flight_payload_time_map(doc):
    """
    View: ``payload_telemetry/flight_payload_time``

    Emits::

        [flight_id, payload_configuration_id, estimated_time_received] -> null

    Useful to find telemetry related to a certain flight.
    """
    if doc['type'] != "payload_telemetry" or '_parsed' not in doc['data']:
        return

    estimated_time = _estimate_time_received(doc['receivers'])

    parsed = doc['data']['_parsed']
    if 'flight' in parsed:
        flight = parsed['flight']
        config = parsed['payload_configuration']
        yield (flight, config, estimated_time), None

@version(1)
def payload_time_map(doc):
    """
    View: ``payload_telemetry/payload_time``

    Emits::

        [payload_configuration_id, estimated_time_received] -> null

    Useful to find telemetry related to a specific payload_configuration.
    """
    if doc['type'] != "payload_telemetry" or '_parsed' not in doc['data']:
        return

    estimated_time = _estimate_time_received(doc['receivers'])

    parsed = doc['data']['_parsed']
    yield (parsed['payload_configuration'], estimated_time), None
