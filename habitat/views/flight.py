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
    """Map by flight window end date."""
    if 'type' in doc and doc['type'] == "flight":
        yield rfc3339_to_timestamp(doc['end']), None

@version(1)
def launch_time_map(doc):
    """Map by flight launch time."""
    if 'type' in doc and doc['type'] == "flight":
        yield rfc3339_to_timestamp(doc['launch']['time']), None

@version(1)
def owner_launch_time_map(doc):
    """Map by owner then launch time."""
    if 'type' in doc and doc['type'] == "flight" and 'owner' in doc:
        yield (doc['owner'], rfc3339_to_timestamp(doc['launch']['time'])), None

