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
Design document for SpaceNear.Us uploader, containing a filter to select parsed
payload telemetry documents and all listener telemetry documents.
"""

def spacenearfilter(doc, req):
    if doc['type'] == "listener_telemetry":
        return True
    elif doc['type'] == "payload_telemetry":
        if doc['data'] and doc['data']['_parsed']:
            return True
    else:
        return False
