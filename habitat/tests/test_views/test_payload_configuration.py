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
Tests payload_configuration document views and functions.
"""

from ...views import payload_configuration

from ...views.utils import read_json_schema

from couch_named_python import ForbiddenError, UnauthorizedError

from copy import deepcopy
from nose.tools import assert_raises
import mox

doc = {
    "type": "payload_configuration",
    "name": "Test Payload",
    "time_created": "2012-07-22T18:31:06+0100",
    "transmissions": [
        {
            "frequency": 434000000,
            "mode": "USB",
            "modulation": "RTTY",
            "shift": 300,
            "encoding": "ASCII-8",
            "baud": 300,
            "parity": "none",
            "stop": 2
        }
    ],
    "sentences": [
        {
            "protocol": "UKHAS",
            "checksum": "crc16-ccitt",
            "callsign": "HABITAT",
            "fields": [{'sensor': 'bla'}],
            "filters": {
                "intermediate": [
                    {
                        "type": "normal",
                        "callable": "a.b.c"
                    }
                ],
                "post": [
                    {
                        "type": "hotfix",
                        "code": "test",
                        "signature": "test",
                        "certificate": "test"
                    }
                ]
            }
        }
    ]
}

schema = read_json_schema("payload_configuration.json")

class TestPayloadConfiguration(object):
    def setup(self):
        self.m = mox.Mox()
        self.m.StubOutWithMock(payload_configuration, 'validate_doc')

    def teardown(self):
        self.m.UnsetStubs()
    
    def test_validates_against_schema(self):
        payload_configuration.validate_doc(doc, schema)
        self.m.ReplayAll()
        payload_configuration.validate(doc, {}, {'roles': []}, {})
        self.m.VerifyAll()

    def test_only_admins_may_edit(self):
        mydoc = deepcopy(doc)
        mydoc['name'] = "hi"
        assert_raises(UnauthorizedError, payload_configuration.validate,
                mydoc, doc, {'roles': []}, {})
        payload_configuration.validate(mydoc, doc, {'roles': ['_admin']}, {})

    def test_ukhas_sentences_must_have_valid_checksum(self):
        mydoc = deepcopy(doc)
        sentence = mydoc['sentences'][0]
        sentence['checksum'] = "invalid"
        assert_raises(ForbiddenError, payload_configuration.validate,
                mydoc, {}, {'roles': []}, {})
        mydoc = deepcopy(doc)
        del mydoc['sentences'][0]['checksum']
        assert_raises(ForbiddenError, payload_configuration.validate,
                mydoc, {}, {'roles': []}, {})

    def test_ukhas_sentences_must_put_format_in_coordinate_fields(self):
        mydoc = deepcopy(doc)
        sentence = mydoc['sentences'][0]
        sentence['fields'][0] = {"name": "c", "sensor": "stdtelem.coordinate"}
        assert_raises(ForbiddenError, payload_configuration.validate,
                mydoc, {}, {'roles': []}, {})
        sentence['fields'][0]["format"] = "dd.dddd"
        payload_configuration.validate(mydoc, {}, {'roles': []}, {})

    def test_ukhas_sentences_must_have_fields(self):
        mydoc = deepcopy(doc)
        sentence = mydoc['sentences'][0]
        sentence['fields'] = {}
        assert_raises(ForbiddenError, payload_configuration.validate,
                mydoc, {}, {'roles': []}, {})
        del sentence['fields']
        assert_raises(ForbiddenError, payload_configuration.validate,
                mydoc, {}, {'roles': []}, {})

    def test_rtty_transmissions_must_be_ok(self):
        for key in ['shift', 'encoding', 'baud', 'parity', 'stop']:
            mydoc = deepcopy(doc)
            del mydoc['transmissions'][0][key]
            assert_raises(ForbiddenError, payload_configuration.validate,
                    mydoc, {}, {'roles': []}, {})

    def test_filters_must_be_ok(self):
        mydoc = deepcopy(doc)
        del mydoc['sentences'][0]['filters']['intermediate'][0]['callable']
        assert_raises(ForbiddenError, payload_configuration.validate,
                mydoc, {}, {'roles': []}, {})
        for key in ['code', 'signature', 'certificate']:
            mydoc = deepcopy(doc)
            del mydoc['sentences'][0]['filters']['post'][0][key]
            assert_raises(ForbiddenError, payload_configuration.validate,
                    mydoc, {}, {'roles': []}, {})

    def test_only_validates_payload_configuration(self):
        self.m.ReplayAll()
        mydoc = {"type": "something_else"}
        payload_configuration.validate(mydoc, {}, {'roles': []}, {})
        self.m.VerifyAll()

    def test_forbids_type_change(self):
        other = deepcopy(doc)
        other['type'] = 'another_type'
        assert_raises(ForbiddenError, payload_configuration.validate,
                doc, other, {'roles': ['_admin']}, {})
        assert_raises(ForbiddenError, payload_configuration.validate,
                other, doc, {'roles': ['_admin']}, {})

    def test_view_name_time_created(self):
        view = payload_configuration.name_time_created_map
        result = list(view(doc))
        assert result == [(('Test Payload', 1342978266), None)]

    def test_view_callsign_time_created_index(self):
        mydoc = deepcopy(doc)
        mydoc['sentences'].append(deepcopy(mydoc['sentences'][0]))
        mydoc['sentences'][1]['callsign'] = "TATIBAH"
        meta = {
            "name": "Test Payload",
            "time_created": "2012-07-22T18:31:06+0100",
        }
        view = payload_configuration.callsign_time_created_index_map
        result = list(view(mydoc))
        assert result == [
            (('HABITAT', 1342978266, 0), (meta, mydoc['sentences'][0])),
            (('TATIBAH', 1342978266, 1), (meta, mydoc['sentences'][1]))]

    def test_view_callsign_time_created_index_includes_metadata(self):
        mydoc = deepcopy(doc)
        mydoc['sentences'].append(deepcopy(mydoc['sentences'][0]))
        mydoc['sentences'][1]['callsign'] = "TATIBAH"
        mydoc['metadata'] = {"meta": ["d", "a", "t", "a"]}
        meta = {
            "name": "Test Payload",
            "time_created": "2012-07-22T18:31:06+0100",
            "metadata": {"meta": ["d", "a", "t", "a"]}
        }
        view = payload_configuration.callsign_time_created_index_map
        result = list(view(mydoc))
        assert result == [
            (('HABITAT', 1342978266, 0), (meta, mydoc['sentences'][0])),
            (('TATIBAH', 1342978266, 1), (meta, mydoc['sentences'][1]))]
