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

import json
from copy import deepcopy
from nose.tools import assert_raises
import mox

doc = {
    "_id": "54e9ac9ec19a57d6828a737525e3cc792743a16344b1c69dfe1562620b0fac9b",
    "type": "payload_telemetry",
    "data": {
        "_raw": "ABCDEF=="
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

    def test_tolerant_of_float_changes(self):
        old = deepcopy(doc)
        old['data']['value'] = 123.456
        old['data']['recurse'] = {"test_list": [0.00001, 1e20, 4.4],
                                  "value": 1.52142e10}
        
        # these changes should be allowed
        new = deepcopy(doc)
        new['data']['value'] = 123.4560000000001
        new['data']['recurse'] = \
            {"test_list": [0.000010000000000000005, 1e20 - 1e5, 4.4 - 1e-15],
             "value": 1.52142e10 + 1e-4}

        # check that they are actually different first
        assert old['data']['value'] != new['data']['value']
        assert all(old['data']['recurse']['test_list'][i] != 
                   new['data']['recurse']['test_list'][i] for i in range(3))
        assert old['data']['recurse']['value'] != \
                new['data']['recurse']['value']

        payload_telemetry.validate(new, old, {'roles': []}, {})

        # these should be outside of tolerance
        new = deepcopy(old)
        new['data']['value'] = 123.4560001
        assert_raises(UnauthorizedError, payload_telemetry.validate,
                new, old, {'roles': []}, {})

        new = deepcopy(old)
        new['data']['recurse']['test_list'][2] = 1e20 + 1e10
        assert_raises(UnauthorizedError, payload_telemetry.validate,
                new, old, {'roles': []}, {})

        # and some quick checks that the func doesn't miss anything dumb
        new = deepcopy(old)
        new['data']['recurse']['new_key'] = True
        assert_raises(UnauthorizedError, payload_telemetry.validate,
                new, old, {'roles': []}, {})

        new = deepcopy(old)
        new['data']['recurse']['test_list'].append(4)
        assert_raises(UnauthorizedError, payload_telemetry.validate,
                new, old, {'roles': []}, {})

        new = deepcopy(old)
        new['data']['value'] = []
        assert_raises(UnauthorizedError, payload_telemetry.validate,
                new, old, {'roles': []}, {})

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

    def test_new_docs_may_only_have_raw_and_fallbacks(self):
        mydoc = deepcopy(doc)
        mydoc['data']['_fallbacks'] = {'a': 1}
        payload_telemetry.validate(mydoc, {}, {'roles': []}, {})
        mydoc['data']['result'] = 42
        assert_raises(ForbiddenError, payload_telemetry.validate,
                mydoc, {}, {'roles': []}, {})
        del mydoc['data']['_fallbacks']
        assert_raises(ForbiddenError, payload_telemetry.validate,
                mydoc, {}, {'roles': []}, {})

    def test_doc_id_must_be_sha256_of_base64_raw(self):
        mydoc = deepcopy(doc)
        payload_telemetry.validate(doc, {}, {'roles': []}, {})
        mydoc["_id"] = "9e40534c92adfdd55620e786a2b434d3" + \
                       "ffda21cae75b9c2e719853e94fbae3eb"
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

    def test_view_time(self):
        mydoc = deepcopy(doc)
        view = payload_telemetry.time_map
        result = list(view(mydoc))
        assert result == []
        mydoc['data']['_parsed'] = {
            "time_parsed": "2012-07-17T22:05:00+01:00",
            "payload_configuration": "abcdef",
            "configuration_sentence_index": 0
        }
        result = list(view(mydoc))
        assert result == [(1342555406, False)]
        mydoc['data']['_parsed']['flight'] = "fedcba"
        result = list(view(mydoc))
        assert result == [(1342555406, True)]

    def test_add_listener_update_new_doc(self):
        doc_id = \
            "cd4eaf118a9668d4349e7053a6bb388952ccf0c28eb4f2542290d1a3629f9415"
        protodoc = {
            "data": {"_raw": "JCRURVNUCg=="},
            "receivers": {"habitat": {
                "time_created": "2012-12-27T12:02:00Z",
                "time_uploaded": "2012-12-27T12:02:01Z",
                "here_is_some": "metadata"}}}
        req = {"body": json.dumps(protodoc), "id": doc_id}
        result = payload_telemetry.add_listener_update(None, req)
        doc = result[0]

        assert result[1] == "OK"
        assert doc["_id"] == doc_id
        assert doc["type"] == "payload_telemetry"
        assert doc["data"]["_raw"] == "JCRURVNUCg=="
        assert len(doc["receivers"]) == 1
        assert "habitat" in doc["receivers"]
        recv = doc["receivers"]["habitat"]
        assert recv["time_created"] == "2012-12-27T12:02:00Z"
        assert recv["time_uploaded"] == "2012-12-27T12:02:01Z"
        assert recv["here_is_some"] == "metadata"
        assert "time_server" in recv
        payload_telemetry.validate(doc, None, {'roles': []}, {})

    def test_add_listener_update_merge(self):
        doc_id = \
            "cd4eaf118a9668d4349e7053a6bb388952ccf0c28eb4f2542290d1a3629f9415"
        protodoc = {
            "data": {"_raw": "JCRURVNUCg=="},
            "receivers": {"habitat": {
                "time_created": "2012-12-27T12:02:00Z",
                "time_uploaded": "2012-12-27T12:02:01Z",
                "here_is_some": "metadata"}}}
        req = {"body": json.dumps(protodoc), "id": doc_id}
        olddoc = {
            "_id": doc_id,
            "_rev": "123abc",
            "type": "payload_telemetry",
            "data": {"_raw": "JCRURVNUCg=="},
            "receivers": {"first": {
                "time_created": "2012-12-27T12:01:58Z",
                "time_uploaded": "2012-12-27T12:01:59Z",
                "other": "data"}}}
        result = payload_telemetry.add_listener_update(olddoc, req)
        doc = result[0]

        assert result[1] == "OK"
        assert doc["_id"] == doc_id
        assert doc["type"] == "payload_telemetry"
        assert doc["data"]["_raw"] == "JCRURVNUCg=="
        assert len(doc["receivers"]) == 2
        assert "first" in doc["receivers"]
        assert doc["receivers"]["first"] == olddoc["receivers"]["first"]
        assert "habitat" in doc["receivers"]
        recv = doc["receivers"]["habitat"]
        assert recv["time_created"] == "2012-12-27T12:02:00Z"
        assert recv["time_uploaded"] == "2012-12-27T12:02:01Z"
        assert recv["here_is_some"] == "metadata"
        assert "time_server" in recv
        payload_telemetry.validate(doc, olddoc, {'roles': []}, {})

    def test_add_listener_update_sanity_checks(self):
        f = payload_telemetry.add_listener_update

        # no data
        assert_raises(ForbiddenError, f, None, {"body":
            '{"not data": {}, "receivers": {"habitat": {}}}'})

        # no data._raw
        assert_raises(ForbiddenError, f, None, {"body": 
            '{"data": {"not _raw": true}, "receivers": {"habitat":{}}}'})

        # no receivers
        assert_raises(ForbiddenError, f, None, {"body":
            '{"data": {"_raw": "a"}, "not receivers": {"habitat": {}}}'})

        # no one in receivers
        assert_raises(ForbiddenError, f, None, {"body":
            '{"data": {"_raw": "a"}, "receivers": {}}'})

        # too many in receivers
        assert_raises(ForbiddenError, f, None, {"body":
            '{"data": {"_raw": "a"}, "receivers": {"a": {}, "b": {}}}'})

    def test_http_post_update(self):
        formdata = {"data": "$$HELLO", "oob": "blargh"}
        req = {"form": formdata, "query": {}}
        result, status = payload_telemetry.http_post_update(None, req)
        assert status == "OK"
        assert result == {
            "_id":
            "5c38baed0ad4625a39391829a6afb15aedbe03df62b3f72cb58a36ea0a95daf4",
            "type": "payload_telemetry",
            "data": {"_raw": "JCRIRUxMTw==",
                     "_fallbacks": {"data": "$$HELLO", "oob": "blargh"}
                    },
            "receivers": {
                "HTTP POST": result["receivers"]["HTTP POST"]
            }
        }
        assert "time_server" in result["receivers"]["HTTP POST"]
        assert "time_created" in result["receivers"]["HTTP POST"]
        assert "time_uploaded" in result["receivers"]["HTTP POST"]
        assert (result["receivers"]["HTTP POST"]["time_server"] ==
                result["receivers"]["HTTP POST"]["time_created"] ==
                result["receivers"]["HTTP POST"]["time_uploaded"])
        payload_telemetry.validate(doc, None, {'roles': []}, {})
    
    def test_http_post_update_querystring_from(self):
        formdata = {"data": "$$HELLO", "oob": "blargh"}
        req = {"form": formdata, "query": {"from": "testsuite"}}
        result, status = payload_telemetry.http_post_update(None, req)
        assert "testsuite" in result["receivers"]
        payload_telemetry.validate(doc, None, {'roles': []}, {})

    def test_http_post_update_put_request(self):
        formdata = {"data": "$$HELLO", "oob": "blargh"}
        req = {"form": formdata, "query": {}}
        result, status = payload_telemetry.http_post_update({'oh':'no'}, req)
        assert result == {'oh':'no'}
        assert status["headers"]["code"] == 405

    def test_http_post_update_rockblock(self):
        formdata = {
            "imei": "300234010753370",
            "momsn": "12345",
            "transmit_time": "12-10-10 10:41:50",
            "iridium_latitude": "52.3867",
            "iridium_longitude": "0.2938",
            "iridium_cep": "8",
            "data": "48656c6c6f20576f726c6420526f636b424c4f434b"
        }
        req = {"form": formdata, "query": {"from": "testsuite"}}
        result, status = payload_telemetry.http_post_update(None, req)
        assert status == "OK"
        assert result == {
            "_id":
            "b4c31b7ac510a519ef113c3ebdeab8a89bd55df193cc8264098519f6fded82bc",
            "type": "payload_telemetry",
            "data": {"_raw": "SGVsbG8gV29ybGQgUm9ja0JMT0NL",
                     "_fallbacks": {
                         "imei": "300234010753370",
                         "momsn": "12345",
                         "transmit_time": "12-10-10 10:41:50",
                         "iridium_latitude": "52.3867",
                         "iridium_longitude": "0.2938",
                         "iridium_cep": "8",
                         "data": "48656c6c6f20576f726c6420526f636b424c4f434b",
                         "payload": "300234010753370",
                         "latitude": 52.3867,
                         "longitude": 0.2938,
                         "time": "10:41:50"
                     }
            },
            "receivers": {
                "testsuite": result["receivers"]["testsuite"]
            }
        }
        assert "time_server" in result["receivers"]["testsuite"]
        assert "time_created" in result["receivers"]["testsuite"]
        assert "time_uploaded" in result["receivers"]["testsuite"]
        assert (result["receivers"]["testsuite"]["time_server"] ==
                result["receivers"]["testsuite"]["time_uploaded"])
        print result["receivers"]["testsuite"]["time_created"]
        assert (result["receivers"]["testsuite"]["time_created"] ==
                "2012-10-10T10:41:50Z")
        payload_telemetry.validate(doc, None, {'roles': []}, {})
