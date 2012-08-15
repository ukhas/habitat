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
Tests payload_telemetry document views and functions.
"""

from ...views import payload_telemetry

from ...views.utils import read_json_schema

from couch_named_python import ForbiddenError, UnauthorizedError

from copy import deepcopy
from nose.tools import assert_raises
import mox

doc = {
    "type": "payload_telemetry",
    "data": {
        "_raw": "ABCDEF"
    },
    "receivers": {
        "M0RND": {
            "time_created": "2012-07-17T21:03:26+01:00",
            "time_uploaded": "2012-07-17T21:03:29+01:00"
        }
    }
}

schema = read_json_schema("payload_telemetry.json")

class TestPayloadTelemetry(object):
    def setup(self):
        self.m = mox.Mox()
        self.m.StubOutWithMock(payload_telemetry, 'validate_doc')

    def teardown(self):
        self.m.UnsetStubs()
    
    def test_validates_against_schema(self):
        payload_telemetry.validate_doc(doc, schema)
        self.m.ReplayAll()
        payload_telemetry.validate(doc, {}, {'roles': []}, {})
        self.m.VerifyAll()

    def test_only_parser_may_add_data(self):
        mydoc = deepcopy(doc)
        mydoc['data']['result'] = 42
        assert_raises(UnauthorizedError, payload_telemetry.validate,
                mydoc, doc, {'roles': []}, {})
        payload_telemetry.validate(mydoc, doc, {'roles': ['parser']}, {})

    def test_may_only_add_receivers(self):
        mydoc = deepcopy(doc)
        del mydoc['receivers']['M0RND']
        assert_raises(ForbiddenError, payload_telemetry.validate,
                mydoc, doc, {'roles': []}, {})
        mydoc = deepcopy(doc)
        mydoc['receivers']['M0RND']['time_created'] = "changed"
        assert_raises(ForbiddenError, payload_telemetry.validate,
                mydoc, doc, {'roles': []}, {})
        mydoc = deepcopy(doc)
        mydoc['receivers']['2E0SKK'] = {
            "time_created": "2012-07-17T21:03:27+01:00",
            "time_uploaded": "2012-07-17T21:03:32+01:00"
        }
        payload_telemetry.validate(mydoc, doc, {'roles': []}, {})

    def test_must_have_a_receiver(self):
        mydoc = deepcopy(doc)
        mydoc['receivers'] = {}
        assert_raises(ForbiddenError, payload_telemetry.validate,
                mydoc, {}, {'roles': []}, {})

    def test_new_docs_may_only_have_raw(self):
        mydoc = deepcopy(doc)
        mydoc['data']['result'] = 42
        assert_raises(ForbiddenError, payload_telemetry.validate,
                mydoc, {}, {'roles': []}, {})

    def test_only_validates_payload_telemetry(self):
        self.m.ReplayAll()
        mydoc = {"type": "something_else"}
        payload_telemetry.validate(mydoc, {}, {'roles': []}, {})
        self.m.VerifyAll()

    def test_forbids_type_change(self):
        other = deepcopy(doc)
        other['type'] = 'another_type'
        assert_raises(ForbiddenError, payload_telemetry.validate, other, doc,
                {'roles': []}, {})
        assert_raises(ForbiddenError, payload_telemetry.validate, doc, other,
                {'roles': []}, {})

    def test_view_flight_payload_time(self):
        mydoc = deepcopy(doc)
        view = payload_telemetry.flight_payload_time_map
        result = list(view(mydoc))
        assert result == []
        mydoc['data']['_parsed'] = {
            "time_parsed": "2012-07-17T22:05:00+01:00",
            "payload_configuration": "abcdef",
            "configuration_sentence_index": 0
        }
        result = list(view(mydoc))
        assert result == []
        mydoc['data']['_parsed']['flight'] = "fedcba"
        result = list(view(mydoc))
        assert result == [(('fedcba', 'abcdef', 1342555406), None)]

    def test_view_payload_time(self):
        mydoc = deepcopy(doc)
        view = payload_telemetry.payload_time_map
        result = list(view(mydoc))
        assert result == []
        mydoc['data']['_parsed'] = {
            "time_parsed": "2012-07-17T22:05:00+01:00",
            "payload_configuration": "abcdef",
            "configuration_sentence_index": 0
        }
        result = list(view(mydoc))
        assert result == [(('abcdef', 1342555406), None)]
        mydoc['data']['_parsed']['flight'] = "fedcba"
        result = list(view(mydoc))
        assert result == [(('abcdef', 1342555406), None)]
