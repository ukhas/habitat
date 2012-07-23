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

from couch_named_python import ForbiddenError, UnauthorizedError, version
from .utils import rfc3339_to_timestamp, validate_doc, read_json_schema

schema = None

@version(1)
def validate(new, old, userctx, secobj):
    """
    Validate this flight document against the schema, then check that
    only managers are approving documents and approved documents are only
    edited by managers.
    """
    global schema
    if not schema:
        schema = read_json_schema("flight.json")
    if 'type' in new and new['type'] == "flight":
        validate_doc(new, schema)
    
    if '_admin' in userctx['roles']:
        return

    if new['approved'] and 'manager' not in userctx['roles']:
        raise UnauthorizedError("Only managers may approve documents.")

    if old and 'manager' not in userctx['roles']:
        raise UnauthorizedError("Only managers may edit documents.")

    start = rfc3339_to_timestamp(new['start'])
    end = rfc3339_to_timestamp(new['end'])
    launch = rfc3339_to_timestamp(new['launch']['time'])
    if start > end:
        raise ForbiddenError("Launch window may not end before it starts.")
    if end - start > 7 * 24 * 3600:
        raise ForbiddenError("Launch window may not be greater than one week"
                " (speak to an admin if you have a special requirement).")
    if not start <= launch < end:
        raise ForbiddenError("Launch time must be within launch window.")

@version(1)
def end_including_payloads_map(doc):
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
def launch_time_including_payloads_map(doc):
    """
    Sort by flight launch time.
    
    Only shows approved flights.

    Used by the calendar and other interface elements to show a list of
    upcoming flights.
    """
    if doc['type'] == "flight":
        if doc['approved']:
            lt = rfc3339_to_timestamp(doc['launch']['time'])
            yield (lt, 0), None
            for payload in doc['payloads']:
                yield (lt, 1), {'_id': payload}

@version(1)
def name_map(doc):
    """
    Sort by flight name.
    
    Used where the UI must show all the flights in some usefully searchable
    sense.
    """
    if doc['type'] == "flight":
        if doc['approved']:
            yield doc['name'], None
