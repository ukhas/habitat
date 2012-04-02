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
Functions for the core habitat design document.

Contains a validation function that applies to every document.
"""

from couch_named_python import Forbidden

from .utils import must_be_admin

allowed_types = set(
    ("flight", "listener_information", "listener_telemetry",
        "payload_telemetry", "payload_configuration"))

def validate(new, old, userctx, secobj):
    if '_deleted' in new:
        must_be_admin(userctx, "Only administrators may delete documents.")
        return

    if 'type' not in new:
        raise Forbidden("All documents must have a type.")

    if new['type'] not in allowed_types:
        raise Forbidden("Invalid document type.")

    if old and new['type'] != old['type']:
        raise Forbidden("Cannot change document type.")

    if 'owner' in old and 'manager' not in userctx['roles']:
        if 'owner' not in new:
            raise Forbidden("Cannot remove the document owner.")
        if new['owner'] != old['owner']:
            raise Forbidden("Cannot change the document owner.")
        if userctx['name'] != new['owner']:
            raise Forbidden("Only the owner of this document may edit it.")
