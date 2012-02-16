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

allowed_types = set(
    ("flight", "listener_info", "listener_telemetry", "payload_telemetry"))

def validate(new, old, userctx, secobj):
    if 'type' not in new:
        raise Forbidden("All documents must have a type.")
    if new['type'] not in allowed_types:
        raise Forbidden("Invalid document type.")
    if old and new['type'] != old['type']:
        raise Forbidden("Cannot change document type.")

