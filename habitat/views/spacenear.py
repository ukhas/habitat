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
Functions for the spacenearus design document.

Contains a filter to select parsed payload telemetry and all listener
telemetry.
"""

from couch_named_python import version

@version(1)
def spacenear_filter(doc, req):
    """Select parsed payload_telemetry and all listener_telemetry documents."""
    if doc['type'] == "listener_telemetry":
        return True
    if doc['type'] == "payload_telemetry":
        if 'data' in doc and '_parsed' in doc['data']:
            return True
    return False
