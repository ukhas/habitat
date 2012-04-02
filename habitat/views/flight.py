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
Functions for the flight design document.

Contains schema validation and views by flight launch time, window end time and
payload name and window end time.
"""

from couch_named_python import ForbiddenError, version
from .utils import rfc3339_to_timestamp, validate_doc, read_json_schema

schema = None

@version(1)
def validate(new, old, userctx, secobj):
    """
    Validate this flight document against the schema, then check that
    only managers are approving documents and approved documents are only
    edited by managers.

    TODO: value based validation
    """
    global schema
    if not schema:
        schema = read_json_schema("flight.json")
    if 'type' in new and new['type'] == "flight":
        validate_doc(new, schema)
    
    if '_admin' in userctx['roles']:
        return

    if old['approved']:
        if new['approved']:
            if 'manager' not in userctx['roles']:
                raise ForbiddenError(
                        "Only managers may edit approved documents.")
    else:
        if new['approved']:
            if 'manager' not in userctx['roles']:
                raise ForbiddenError("Only managers may approve documents.")

@version(1)
def end_map(doc):
    """
    Sort by flight window end time.
    If the flight has payloads, emit it with the list of payloads, and emit
    a link for each payload so that they get included with include_docs.

    Only shows approved flights.

    Used by the parser to find active flights and the configurations to use to
    decode telemetry from them.
    """
    if doc['type'] == "flight":
        if 'payloads' in doc and doc['approved']:
            et = rfc3339_to_timestamp(doc['end'])
            yield (et, 0), doc['payloads']
            for payload in doc['payloads']:
                yield (et, 1), {'_id': payload}

@version(1)
def owner_launch_time_map(doc):
    """
    Map by owner then launch time with the launch name in the value.

    Used to show users their own launch documents.
    """
    if doc['type'] == "flight" and 'owner' in doc:
        lt = rfc3339_to_timestamp(doc['launch']['time'])
        yield (doc['owner'], lt), doc['name']

