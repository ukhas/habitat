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
Functions for the listener_telemetry design document.

Contains schema validation and a view by creation time and callsign.
"""

from .utils import rfc3339_to_timestamp, must_be_admin, validate_doc
from .utils import read_json_schema

schema = None

def validate(new, old, userctx, secobj):
    """
    Only allow admins to edit/delete and validate the document against the
    schema for listener_telemetry documents.
    """
    global schema
    if not schema:
        schema = read_json_schema("listener_telemetry.json")
    if new['type'] == "listener_telemetry":
        if old:
            must_be_admin(userctx)
        validate_doc(new, schema)

def time_created_callsign_map(doc):
    """Emit time_created and callsign."""
    if doc['type'] == "listener_telemetry":
        tc = rfc3339_to_timestamp(doc['time_created'])
        yield (tc, doc['data']['callsign']), None
