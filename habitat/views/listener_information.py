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
# along with habitat.  If not, see <http://www.gnu.org/licenses/>.

"""
Functions for the listener_information design document.

Contains schema validation and a view by creation time and callsign.
"""

from couch_named_python import version
from strict_rfc3339 import rfc3339_to_timestamp
from .utils import must_be_admin, validate_doc
from .utils import read_json_schema, only_validates

schema = None

@version(1)
@only_validates("listener_information")
def validate(new, old, userctx, secobj):
    """
    Only allow admins to edit/delete and validate the document against the
    schema for listener_information documents.
    """
    if old:
        must_be_admin(userctx)

    global schema
    if not schema:
        schema = read_json_schema("listener_information.json")
    validate_doc(new, schema)

@version(1)
def time_created_callsign_map(doc):
    """
    View: ``listener_information/time_created_callsign``

    Emits::

        [time_created, callsign] -> null

    Times are UNIX timestamps (and therefore in UTC).

    Sorts by time created. Useful to see the latest listener information.
    """
    if doc['type'] == "listener_information":
        tc = rfc3339_to_timestamp(doc['time_created'])
        yield (tc, doc['data']['callsign']), None

@version(1)
def callsign_time_created_map(doc):
    """
    View: ``listener_information/callsign_time_created``

    Emits::

        [callsign, time_created] -> null

    Times are UNIX timestamps (and therefore in UTC).
    
    Sorts by callsign. Useful to see a certain callsign's latest information.
    """
    if doc['type'] == "listener_information":
        tc = rfc3339_to_timestamp(doc['time_created'])
        yield (doc['data']['callsign'], tc), None
