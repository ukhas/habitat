# Copyright 2012 (C) Adam Greig
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
Tests SpaceNear document functions
"""

from ...views import spacenear

from copy import deepcopy

doc = {
    "type": "payload_telemetry",
    "data": {
        "_parsed": "test test"
    }
}

def test_unparsed_filter():
    fil = spacenear.spacenear_filter
    
    wrongtype = deepcopy(doc)
    wrongtype["type"] = "flight"
    assert not fil(wrongtype, {})

    listener = deepcopy(doc)
    listener["type"] = "listener_telemetry"
    assert fil(listener, {})

    parsed = deepcopy(doc)
    assert fil(parsed, {})

    nodata = deepcopy(doc)
    del nodata['data']
    assert not fil(nodata, {})

    notparsed = deepcopy(doc)
    del notparsed['data']['_parsed']
    assert not fil(notparsed, {})
