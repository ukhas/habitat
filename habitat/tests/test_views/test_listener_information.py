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
Tests listener_information document views and functions.
"""

from ...views import listener_information

from ...views.utils import read_json_schema

from couch_named_python import ForbiddenError, UnauthorizedError

from copy import deepcopy
from nose.tools import assert_raises
import mox

doc = {
    "type": "listener_information",
    "time_created": "2012-07-17T21:03:26+01:00",
    "time_uploaded": "2012-07-17T21:03:29+01:00",
    "data": {
        "callsign": "M0RND",
        "antenna": "2m/70cm Colinear",
        "radio": "ICOM IC-7000"
    }
}

schema = read_json_schema("listener_information.json")

class TestListenerInformation(object):
    def setup(self):
        self.m = mox.Mox()
        self.m.StubOutWithMock(listener_information, 'validate_doc')

    def teardown(self):
        self.m.UnsetStubs()
    
    def test_validates_against_schema(self):
        listener_information.validate_doc(doc, schema)
        self.m.ReplayAll()
        listener_information.validate(doc, None, {'roles': []}, {})
        self.m.VerifyAll()

    def test_only_admins_can_edit(self):
        mydoc = deepcopy(doc)
        mydoc['data']['radio'] = "Yaesu FT817"
        assert_raises(UnauthorizedError, listener_information.validate,
                mydoc, doc, {'roles': []}, {})
        listener_information.validate(mydoc, doc, {'roles': ['_admin']}, {})

    def test_only_validates_listener_information(self):
        self.m.ReplayAll()
        mydoc = {"type": "something_else"}
        listener_information.validate(mydoc, {}, {'roles': []}, {})
        self.m.VerifyAll()

    def test_forbids_type_change(self):
        other = deepcopy(doc)
        other['type'] = 'another_type'
        assert_raises(ForbiddenError, listener_information.validate,
                other, doc, {'roles': ['_admin']}, {})
        assert_raises(ForbiddenError, listener_information.validate,
                doc, other, {'roles': ['_admin']}, {})

    def test_view_time_created_callsign_map(self):
        result = list(listener_information.time_created_callsign_map(doc))
        assert result == [((1342555406, "M0RND"), None)]

    def test_view_callsign_time_created_map(self):
        result = list(listener_information.callsign_time_created_map(doc))
        assert result == [(("M0RND", 1342555406), None)]
