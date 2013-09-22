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
Functions for the core habitat design document.

Contains a validation function that applies to every document.
"""

from couch_named_python import ForbiddenError, version
from .utils import must_be_admin

allowed_types = set(
    ("flight", "listener_information", "listener_telemetry",
        "payload_telemetry", "payload_configuration"))

@version(1)
def validate(new, old, userctx, secobj):
    """
    Core habitat validation function.

    * Prevent deletion by anyone except administrators.
    * Prevent documents without a type.
    * Prevent documents whose type is invalid.
    * Prevent changing document type.

    """
    if '_deleted' in new:
        must_be_admin(userctx, "Only administrators may delete documents.")
        return

    if 'type' not in new:
        raise ForbiddenError("All documents must have a type.")

    if new['type'] not in allowed_types:
        raise ForbiddenError("Invalid document type.")

    if old and new['type'] != old['type']:
        raise ForbiddenError("Cannot change document type.")

