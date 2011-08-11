# Copyright 2011 (C) Daniel Richman
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
Tests for the uploader module
"""

import mox
import uuid

import time
import couchdbkit

from ... import uploader

telemetry_data = {"some_data": 123, "_flag": True}
telemetry_doc = {
    "data": telemetry_data,
    "type": "listener_telemetry",
    "time_created": 1234,
    "time_uploaded": 1234,
}
telemetry_time_doc = {
    "data": telemetry_data,
    "type": "listener_telemetry",
    "time_created": 1232,
    "time_uploaded": 1276
}

info_data = {"my_radio": "Duga-3", "vehicle": "Tractor"}
info_doc = {
    "data": info_data,
    "type": "listener_info",
    "time_created": 1259,
    "time_uploaded": 1259
}
info_time_doc = {
    "data": info_data,
    "type": "listener_info",
    "time_created": 1254,
    "time_uploaded": 1290
}

payload_telemetry_string = "asdf blah \x12 binar\x04\x00"
payload_telemetry_metadata = {"frequency": 434075000, "misc": "Hi"}
payload_telemetry_doc = {
    "data": {
        "_raw": "YXNkZiBibGFoIBIgYmluYXIEAA=="
    },
    "type": "payload_telemetry",
    "receivers": {
        "TESTCALL": {
            "time_created": 1234,
            "time_uploaded": 1234,
            "frequency": 434075000, # TODO: this ought to be in the schema/docs
            "misc": "Hi"
        }
    }
}
payload_telemetry_doc_id = "cf4511bba32c4273a13d8f2e39501a96" \
                           "9ec664a4dc5c67bc556b514410087309"

class TestUploaderSetup(object):
    def setup(self):
        self.mocker = mox.Mox()
        self.mocker.StubOutWithMock(uploader, "couchdbkit")

    def teardown(self):
        self.mocker.UnsetStubs()

    def test_connects_to_couch(self):
        fake_server = self.mocker.CreateMock(couchdbkit.Server)

        uploader.couchdbkit.Server("http://username:password@example.com/") \
                .AndReturn(fake_server)
        fake_server.__getitem__("habitat_test")

        self.mocker.ReplayAll()

        u = uploader.Uploader(
            callsign="TESTCALL",
            couch_uri="http://username:password@example.com/",
            couch_db="habitat_test"
        )

        self.mocker.VerifyAll()

    def test_connects_to_default_couch(self):
        fake_server = self.mocker.CreateMock(couchdbkit.Server)

        uploader.couchdbkit.Server("http://habhub.org/") \
                .AndReturn(fake_server)
        fake_server.__getitem__("habitat")

        self.mocker.ReplayAll()

        u = uploader.Uploader("TESTER")

        self.mocker.VerifyAll()

class TestUploader(object):
    def setup(self):
        self.mocker = mox.Mox()
        self.mocker.StubOutWithMock(uploader, "couchdbkit")
        self.mocker.StubOutWithMock(uploader, "time")

        fake_server = self.mocker.CreateMock(couchdbkit.Server)
        self.fake_db = self.mocker.CreateMock(couchdbkit.Database)

        uploader.couchdbkit.Server("http://server/").AndReturn(fake_server)
        fake_server.__getitem__("habitat").AndReturn(self.fake_db)

        self.mocker.ReplayAll()
        self.uploader = uploader.Uploader("TESTCALL",
                                          couch_uri="http://server/")
        self.mocker.VerifyAll()
        self.mocker.ResetAll()

        self.docs = {}

    def teardown(self):
        self.mocker.UnsetStubs()

    def save_doc(self, doc):
        doc_id = str(uuid.uuid1())
        doc["_id"] = doc_id
        self.docs[doc_id] = doc

    def add_sample_listener_docs(self):
        uploader.time.time().AndReturn(1234)
        self.fake_db.save_doc(telemetry_doc).WithSideEffects(self.save_doc)
        uploader.time.time().AndReturn(1259)
        self.fake_db.save_doc(info_doc).WithSideEffects(self.save_doc)
        self.mocker.ReplayAll()

        self.uploader.listener_telemetry(telemetry_data)
        self.uploader.listener_info(info_data)
        self.mocker.VerifyAll()
        self.mocker.ResetAll()

    def test_pushes_listener_docs(self):
        self.add_sample_listener_docs()

        uploader.time.time().AndReturn(1276)
        self.fake_db.save_doc(telemetry_time_doc) \
                .WithSideEffects(self.save_doc)
        uploader.time.time().AndReturn(1290)
        self.fake_db.save_doc(info_time_doc).WithSideEffects(self.save_doc) 
        self.mocker.ReplayAll()

        self.uploader.listener_telemetry(telemetry_data, time_created=1232)
        self.uploader.listener_info(info_data, time_created=1254)
        self.mocker.VerifyAll()

    def test_pushes_payload_telemetry_simple(self):
        uploader.time.time().AndReturn(1234)
        self.fake_db.__setitem__(payload_telemetry_doc_id,
                                 payload_telemetry_doc)
        self.mocker.ReplayAll()

        self.uploader.payload_telemetry(payload_telemetry_string,
                                        payload_telemetry_metadata)
        self.mocker.VerifyAll()

    def ptlm_with_listener_docs(self, doc):
        doc_metadata = doc["receivers"]["TESTCALL"]
        listener_telemetry_id = doc_metadata["latest_listener_telemetry"]
        listener_info_id = doc_metadata["latest_listener_info"]

        # Check that besides the two ids, it equals payload_telemetry_doc
        del doc_metadata["latest_listener_telemetry"]
        del doc_metadata["latest_listener_info"]

        try :
            assert doc == payload_telemetry_doc
            assert self.docs[listener_telemetry_id]["type"] == \
                    "listener_telemetry"
            assert self.docs[listener_info_id]["type"] == "listener_info"
        except:
            return False
        else:
            return True

    def test_adds_latest_listener_docs(self):
        self.add_sample_listener_docs()

        uploader.time.time().AndReturn(1234)
        self.fake_db.__setitem__(payload_telemetry_doc_id, 
                                 mox.Func(self.ptlm_with_listener_docs))
        self.mocker.ReplayAll()

        self.uploader.payload_telemetry(payload_telemetry_string,
                                        payload_telemetry_metadata)
        self.mocker.VerifyAll()

        # TODO: conflict resolution
