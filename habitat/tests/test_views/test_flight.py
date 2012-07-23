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
Tests Flight document views and functions
"""

from ...views import flight

from ...views.utils import read_json_schema

from couch_named_python import ForbiddenError, UnauthorizedError

from copy import deepcopy
from nose.tools import assert_raises
import mox

doc = {
    "type": "flight",
    "approved": False,
    "start": "2012-07-14T22:54:23+0100",
    "end": "2012-07-15T00:00:00+0100",
    "name": "Test Launch",
    "launch": {
        "time": "2012-07-14T23:30:00+0100",
        "timezone": "Europe/London",
        "location": {
            "latitude": 12.345,
            "longitude": 54.321
        }
    }
}

schema = read_json_schema("flight.json")

class TestFlight(object):
    def setup(self):
        self.m = mox.Mox()
        self.m.StubOutWithMock(flight, 'validate_doc')

    def teardown(self):
        self.m.UnsetStubs()
    
    def test_validates_against_schema(self):
        flight.validate_doc(doc, schema)
        self.m.ReplayAll()
        flight.validate(doc, None, {'roles': []}, {})
        self.m.VerifyAll()

    def test_passes_if_admin(self):
        mydoc = deepcopy(doc)
        mydoc['approved'] = True
        flight.validate(mydoc, mydoc, {'roles': ['_admin']}, {})
    
    def test_only_managers_approve_docs(self):
        unapproved = deepcopy(doc)
        approved = deepcopy(doc)
        approved['approved'] = True
        assert_raises(UnauthorizedError, flight.validate, approved, unapproved,
                {'roles': []}, {})
        assert_raises(UnauthorizedError, flight.validate, approved, approved,
                {'roles': []}, {})
        flight.validate(unapproved, approved, {'roles': ['manager']}, {})
        flight.validate(approved, approved, {'roles': ['manager']}, {})

    def test_only_managers_edit_docs(self):
        new = deepcopy(doc)
        new['name'] = "Edited Launch"
        assert_raises(UnauthorizedError, flight.validate, new, doc,
                {'roles': []}, {})
        flight.validate(new, doc, {'roles': ['manager']}, {})

    def test_start_before_end(self):
        mydoc = deepcopy(doc)
        # start at the same local time but in UTC not +0100, so 'after'
        mydoc['start'] = "2012-07-15T00:00:00Z"
        assert_raises(ForbiddenError, flight.validate, mydoc, {},
                {'roles': []}, {})

    def test_window_less_than_a_week(self):
        mydoc = deepcopy(doc)
        mydoc['start'] = "2012-07-07T00:00:00+0100"
        assert_raises(ForbiddenError, flight.validate, mydoc, {},
                {'roles': []}, {})

    def test_launch_time_within_window(self):
        mydoc = deepcopy(doc)
        mydoc['launch']['time'] = "2012-07-14T22:00:00+0100"
        assert_raises(ForbiddenError, flight.validate, mydoc, {},
                {'roles': []}, {})

    def test_view_launch_time_including_payloads(self):
        mydoc = deepcopy(doc)
        mydoc['approved'] = True
        mydoc['payloads'] = ['a', 'b']
        result = list(flight.launch_time_including_payloads_map(mydoc))
        expected = [
            ((1342305000, 0), None),
            ((1342305000, 1), {'_id': 'a'}),
            ((1342305000, 1), {'_id': 'b'})
        ]

        assert result == expected

    def test_view_end_including_payloads(self):
        mydoc = deepcopy(doc)
        mydoc['approved'] = True
        mydoc['payloads'] = ['a', 'b']
        result = list(flight.end_including_payloads_map(mydoc))
        expected = [
            ((1342306800, 0), ['a', 'b']),
            ((1342306800, 1), {'_id': 'a'}),
            ((1342306800, 1), {'_id': 'b'})
        ]

        assert result == expected

    def test_view_name(self):
        mydoc = deepcopy(doc)
        mydoc['approved'] = True
        result = list(flight.name_map(mydoc))
        assert result == [("Test Launch", None)]
