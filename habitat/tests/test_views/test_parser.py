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
Tests Parser document functions
"""

from ...views import parser

from copy import deepcopy

doc = {
    "type": "payload_telemetry",
    "data": {
        "_parsed": "tset tset"
    }
}

def test_unparsed_filter():
    fil = parser.unparsed_filter
    
    wrongtype = deepcopy(doc)
    wrongtype["type"] = "flight"
    assert not fil(wrongtype, {})

    parsed = deepcopy(doc)
    assert not fil(parsed, {})

    nodata = deepcopy(doc)
    del nodata['data']
    assert not fil(nodata, {})

    ok = deepcopy(doc)
    del ok['data']['_parsed']
    assert fil(ok, {})

def test_issue_241():
    # this should not produce an exception
    parser.unparsed_filter({"_deleted": True}, {})
