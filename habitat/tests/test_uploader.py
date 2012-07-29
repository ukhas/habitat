# Copyright 2011, 2012 (C) Daniel Richman
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
import sys
import copy
import uuid
import threading

import couchdbkit

from .. import uploader

telemetry_data = {"some_data": 123, "_flag": True}
telemetry_doc = {
    "data": copy.deepcopy(telemetry_data),
    "type": "listener_telemetry",
    "time_created": 1234,
    "time_uploaded": 1234,
}
telemetry_doc["data"]["callsign"] = "TESTCALL"
telemetry_time_doc = copy.deepcopy(telemetry_doc)
telemetry_time_doc["time_created"] = 1232
telemetry_time_doc["time_uploaded"] = 1276

info_data = {"my_radio": "Duga-3", "vehicle": "Tractor"}
info_doc = {
    "data": copy.deepcopy(info_data),
    "type": "listener_information",
    "time_created": 1259,
    "time_uploaded": 1259
}
info_doc["data"]["callsign"] = "TESTCALL"
info_time_doc = copy.deepcopy(info_doc)
info_time_doc["time_created"] = 1254
info_time_doc["time_uploaded"] = 1290

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
            # TODO: this ought to be in the schema/docs
            "frequency": 434075000,
            "misc": "Hi"
        }
    }
}
payload_telemetry_doc_existing = {
    "data": {
        "_raw": "YXNkZiBibGFoIBIgYmluYXIEAA==",
        "some_parsed_data": 12345
    },
    "type": "payload_telemetry",
    "receivers": {
        "SOMEONEELSE": {
            "time_created": 200,
            "time_uploaded": 240,
            "frequency": 434074000,
            "asdf": "World"
        }
    }
}
payload_telemetry_doc_merged = copy.deepcopy(payload_telemetry_doc_existing)
payload_telemetry_doc_merged["receivers"]["TESTCALL"] = \
    copy.deepcopy(payload_telemetry_doc["receivers"]["TESTCALL"])
payload_telemetry_doc_merged["receivers"]["TESTCALL"]["time_uploaded"] += 1
payload_telemetry_doc_existing_collision = \
    copy.deepcopy(payload_telemetry_doc_existing)
payload_telemetry_doc_existing_collision["data"]["_raw"] = "cGluZWFwcGxlcw=="

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

        uploader.couchdbkit.Server("http://habitat.habhub.org/") \
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
        uploader.time.time().AndReturn(1233.9)
        uploader.time.time().AndReturn(1234.0)
        self.fake_db.save_doc(telemetry_doc).WithSideEffects(self.save_doc)
        uploader.time.time().AndReturn(1259.1)
        uploader.time.time().AndReturn(1259.1)
        self.fake_db.save_doc(info_doc).WithSideEffects(self.save_doc)
        self.mocker.ReplayAll()

        self.uploader.listener_telemetry(telemetry_data)
        self.uploader.listener_information(info_data)
        self.mocker.VerifyAll()
        self.mocker.ResetAll()

    def test_pushes_listener_docs(self):
        self.add_sample_listener_docs()

        uploader.time.time().AndReturn(1276.1)
        self.fake_db.save_doc(telemetry_time_doc) \
                .WithSideEffects(self.save_doc)
        uploader.time.time().AndReturn(1290.1)
        self.fake_db.save_doc(info_time_doc).WithSideEffects(self.save_doc)
        self.mocker.ReplayAll()

        self.uploader.listener_telemetry(telemetry_data, time_created=1232)
        self.uploader.listener_information(info_data, time_created=1253.8)
        self.mocker.VerifyAll()

    def test_returns_doc_id(self):
        uploader.time.time().AndReturn(1233.9)
        uploader.time.time().AndReturn(1234.0)
        self.fake_db.save_doc(telemetry_doc).WithSideEffects(self.save_doc)
        self.mocker.ReplayAll()

        doc_id = self.uploader.listener_telemetry(telemetry_data)
        assert self.docs[doc_id]["type"] == "listener_telemetry"

    def test_pushes_payload_telemetry_simple(self):
        uploader.time.time().AndReturn(1234.3)
        uploader.time.time().AndReturn(1234.3)
        self.fake_db.__setitem__(payload_telemetry_doc_id,
                                 payload_telemetry_doc)
        self.mocker.ReplayAll()

        doc_id = self.uploader.payload_telemetry(payload_telemetry_string,
                                                 payload_telemetry_metadata)
        assert doc_id == payload_telemetry_doc_id
        self.mocker.VerifyAll()

    def ptlm_with_listener_docs(self, doc):
        doc_metadata = doc["receivers"]["TESTCALL"]
        listener_telemetry_id = doc_metadata["latest_listener_telemetry"]
        listener_information_id = doc_metadata["latest_listener_information"]

        # Check that besides the two ids, it equals payload_telemetry_doc
        del doc_metadata["latest_listener_telemetry"]
        del doc_metadata["latest_listener_information"]

        try:
            assert doc == payload_telemetry_doc
            assert self.docs[listener_telemetry_id]["type"] == \
                    "listener_telemetry"
            assert self.docs[listener_information_id]["type"] == \
                    "listener_information"
        except:
            return False
        else:
            return True

    def test_adds_latest_listener_docs(self):
        self.add_sample_listener_docs()

        uploader.time.time().AndReturn(1234.0)
        uploader.time.time().AndReturn(1234.0)
        self.fake_db.__setitem__(payload_telemetry_doc_id,
                                 mox.Func(self.ptlm_with_listener_docs))
        self.mocker.ReplayAll()

        self.uploader.payload_telemetry(payload_telemetry_string,
                                        payload_telemetry_metadata)
        self.mocker.VerifyAll()

    def test_ptlm_merges_payload_conflicts(self):
        uploader.time.time().AndReturn(1234.0)
        uploader.time.time().AndReturn(1234.0)
        self.fake_db.__setitem__(payload_telemetry_doc_id,
                                 payload_telemetry_doc) \
             .AndRaise(couchdbkit.exceptions.ResourceConflict)
        self.fake_db.__getitem__(payload_telemetry_doc_id) \
             .AndReturn(payload_telemetry_doc_existing)
        uploader.time.time().AndReturn(1235.0)
        self.fake_db.__setitem__(payload_telemetry_doc_id,
                                 payload_telemetry_doc_merged)
        self.mocker.ReplayAll()

        self.uploader.payload_telemetry(payload_telemetry_string,
                                        payload_telemetry_metadata)
        self.mocker.VerifyAll()

    def test_ptlm_refuses_to_merge_collision(self):
        uploader.time.time().AndReturn(1234.0)
        uploader.time.time().AndReturn(1234.0)
        self.fake_db.__setitem__(payload_telemetry_doc_id,
                                 payload_telemetry_doc) \
             .AndRaise(couchdbkit.exceptions.ResourceConflict)
        self.fake_db.__getitem__(payload_telemetry_doc_id) \
             .AndReturn(payload_telemetry_doc_existing_collision)
        uploader.time.time().AndReturn(1235.0)
        self.mocker.ReplayAll()

        try:
            self.uploader.payload_telemetry(payload_telemetry_string,
                                            payload_telemetry_metadata)
        except uploader.CollisionError:
            pass
        else:
            raise AssertionError("Did not raise CollisionError")

        self.mocker.VerifyAll()

    def add_mock_conflicts(self, n):
        uploader.time.time().AndReturn(1234.0)
        uploader.time.time().AndReturn(1234.0)
        self.fake_db.__setitem__(payload_telemetry_doc_id,
                                 payload_telemetry_doc) \
             .AndRaise(couchdbkit.exceptions.ResourceConflict)

        doc = payload_telemetry_doc_existing
        doc_merged = payload_telemetry_doc_merged

        for i in xrange(n):
            self.fake_db.__getitem__(payload_telemetry_doc_id).AndReturn(doc)
            uploader.time.time().AndReturn(1235.0 + i)
            self.fake_db.__setitem__(payload_telemetry_doc_id, doc_merged) \
                .AndRaise(couchdbkit.exceptions.ResourceConflict)

            doc = copy.deepcopy(doc)
            doc_merged = copy.deepcopy(doc_merged)

            new_call = "listener_{0}".format(i)
            new_info = {"time_created": 1000 + i, "time_uploaded": 1001 + i}
            doc["receivers"][new_call] = new_info
            doc_merged["receivers"][new_call] = new_info
            doc_merged["receivers"]["TESTCALL"]["time_uploaded"] += 1

        return (doc, doc_merged)

    def test_merges_multiple_conflicts(self):
        (final_doc, final_doc_merged) = self.add_mock_conflicts(14)

        self.fake_db.__getitem__(payload_telemetry_doc_id).AndReturn(final_doc)
        uploader.time.time().AndReturn(1235.0 + 14)
        self.fake_db.__setitem__(payload_telemetry_doc_id, final_doc_merged)
        self.mocker.ReplayAll()

        self.uploader.payload_telemetry(payload_telemetry_string,
                                        payload_telemetry_metadata)

        self.mocker.VerifyAll()

    def test_gives_up_after_many_conflicts(self):
        self.add_mock_conflicts(20)
        self.mocker.ReplayAll()

        try:
            self.uploader.payload_telemetry(payload_telemetry_string,
                                            payload_telemetry_metadata)
        except uploader.UnmergeableError:
            pass
        else:
            raise AssertionError("Did not raise UnmergeableError")

        self.mocker.VerifyAll()

    def test_flights(self):
        uploader.time.time().AndReturn(1912)
        self.fake_db.view("uploader_v1/flights", include_docs=True,
                          startkey=1912).AndReturn([
            {"doc": {"item": 1}, "key": 1, "value": "moo"},
            {"doc": {"item": "frog"}, "key": 2, "value": "moo"},
            {"doc": {"item": "cow"}, "key": 3, "value": "moo"},
            {"doc": {"item": 1900}, "key": 4, "value": "moo"},
            {"doc": {"item": False}, "key": 5, "value": "moo"}
        ])

        self.mocker.ReplayAll()

        results = self.uploader.flights()
        assert results == [{"item": 1}, {"item": "frog"}, {"item": "cow"},
                           {"item": 1900}, {"item": False}]

        self.mocker.VerifyAll()


class MyUploaderThread(uploader.UploaderThread):
    def __init__(self):
        super(MyUploaderThread, self).__init__()
        self.thread_error = False

    def log(self, msg):
        print msg

    def caught_exception(self):
        raise

    def run(self):
        try:
            super(MyUploaderThread, self).run()
        except:
            self.thread_error = True
            raise

class TestUploaderThread(object):
    def setup(self):
        self.mocker = mox.Mox()

        self.fake_uploader = self.mocker.CreateMock(uploader.Uploader)
        self.uploader_class = uploader.Uploader
        self.mocker.StubOutWithMock(uploader, "Uploader")

        self.uthr = MyUploaderThread()
        assert not self.uthr.is_alive()
        self.uthr.start()

        uploader.Uploader("CALL1").AndReturn(self.fake_uploader)

        self.mocker.ReplayAll()
        self.uthr.settings("CALL1")
        self.uthr._queue.join()
        self.mocker.VerifyAll()
        self.mocker.ResetAll()

    def teardown(self):
        self.uthr.join()
        self.mocker.UnsetStubs()
        assert not self.uthr.thread_error

    def test_changes_settings(self):
        self.fake_uploader.payload_telemetry("blah")

        fake_two = self.mocker.CreateMock(self.uploader_class)
        uploader.Uploader("CALL2", "url", couch_db="db").AndReturn(fake_two)
        fake_two.payload_telemetry("whatever")

        self.mocker.ReplayAll()

        self.uthr.payload_telemetry("blah")
        self.uthr.settings("CALL2", "url", couch_db="db")
        self.uthr.payload_telemetry("whatever")

        self.uthr.join()
        self.mocker.VerifyAll()

    def test_reset(self):
        self.mocker.StubOutWithMock(self.uthr, "caught_exception")

        def check_exception():
            (exc_type, exc_value, discard_tb) = sys.exc_info()
            assert exc_type == ValueError
            assert str(exc_value) == "Uploader settings were not initialised"

        self.uthr.caught_exception().WithSideEffects(check_exception)

        self.mocker.ReplayAll()
        self.uthr.reset()

        self.uthr.allow_exceptions = True
        self.uthr.listener_telemetry({"blah": "blah"})

        self.uthr.join()
        self.mocker.VerifyAll()

    def test_nonblocking(self):
        delay_event = threading.Event()

        def delay(x):
            delay_event.wait()

        self.fake_uploader.payload_telemetry("meh").WithSideEffects(delay)
        self.fake_uploader.listener_telemetry("blah")
        self.fake_uploader.listener_information("boo")
        self.fake_uploader.flights()

        self.mocker.ReplayAll()

        self.uthr.payload_telemetry("meh")
        self.uthr.listener_telemetry("blah")
        self.uthr.listener_information("boo")
        self.uthr.flights()

        delay_event.set()

        self.uthr.join()
        self.mocker.VerifyAll()

    def test_uploads(self):
        fcns = ["payload_telemetry", "listener_telemetry",
                "listener_information"]
        n = 1

        for i in fcns:
            getattr(self.fake_uploader, i)(*["arglist", n])
            n += 1

        self.mocker.ReplayAll()

        n = 1
        for i in fcns:
            getattr(self.uthr, i)(*["arglist", n])
            n += 1

        self.uthr.join()
        self.mocker.VerifyAll()

    def test_flights(self):
        self.mocker.StubOutWithMock(self.uthr, "got_flights")

        delay_event = threading.Event()
        def delay(x):
            delay_event.wait()

        def check(x):
            assert delay_event.is_set()

        self.fake_uploader.payload_telemetry("delayme").WithSideEffects(delay)
        self.fake_uploader.flights().AndReturn(["item1", "item2", "item3"])
        self.uthr.got_flights(["item1", "item2", "item3"])\
                .WithSideEffects(check)

        self.mocker.ReplayAll()

        self.uthr.payload_telemetry("delayme")
        self.uthr.flights()

        delay_event.set()
        self.uthr.join()

        self.mocker.VerifyAll()


# Class that is 'equal' to another string if the value it is initialised is
# contained in that string; used to avoid writing out the large extractor log
# messages in the tests.
class EqualIfIn:
    def __init__(self, test):
        self.test = test
    def __eq__(self, rhs):
        return isinstance(rhs, basestring) and self.test.lower() in rhs.lower()
    def __repr__(self):
        return "<EqIn " + repr(self.test) + ">"


class TestExtractorManager(object):
    def setup(self):
        self.mocker = mox.Mox()

    def teardown(self):
        self.mocker.UnsetStubs()

    def test_add_push_skip(self):
        uplr = self.mocker.CreateMock(uploader.Uploader)
        mgr = uploader.ExtractorManager(uplr)

        self.mocker.ReplayAll()

        assert mgr.uploader == uplr

        for char in "$$a,string\n":
            mgr.push(char)

        self.mocker.VerifyAll()
        self.mocker.ResetAll()

        extr = self.mocker.CreateMock(uploader.Extractor)
        extr.push("a")
        extr.push("b", baudot_hack=True)
        extr.skipped(100)
        extr.push("c", some_future_kwarg=True)

        self.mocker.ReplayAll()

        mgr.add(extr)
        assert extr.manager == mgr

        mgr.push("a")
        mgr.push("b", baudot_hack=True)
        mgr.skipped(100)
        mgr.push("c", some_future_kwarg=True)

        self.mocker.VerifyAll()

    def test_kwargs_future_proof(self):
        mgr = uploader.ExtractorManager(None)
        mgr.add(uploader.UKHASExtractor())
        mgr.push("a", some_unknown_kwarg=5) # should be ignored w/o error


# Usage: with MoxSilence(self.mocker): ensures that no mock calls happen
# inside block.
class MoxSilence(object):
    def __init__(self, mocker):
        self.mocker = mocker

    def __enter__(self):
        self.mocker.ResetAll()
        self.mocker.ReplayAll()
        return self

    def __exit__(self, *args):
        self.mocker.VerifyAll()
        self.mocker.ResetAll()


class TestUKHASExtractor(object):
    def setup(self):
        self.mocker = mox.Mox()
        self.uplr = self.mocker.CreateMock(uploader.Uploader)
        self.mgr = uploader.ExtractorManager(self.uplr)
        self.ukhas_extractor = uploader.UKHASExtractor()
        self.mgr.add(self.ukhas_extractor)

        self.mocker.StubOutWithMock(self.mgr, "status")
        self.mocker.StubOutWithMock(self.mgr, "data")

    def teardown(self):
        self.mocker.UnsetStubs()

    def push(self, string):
        for char in string:
            self.mgr.push(char)

    def expect_extraction_of(self, string):
        self.uplr.payload_telemetry(string)
        self.mgr.status(EqualIfIn("extracted"))
        self.mgr.status(EqualIfIn("parse failed"))
        self.mgr.data({"_sentence": string})

    def check_newline_no_upload(self):
        with MoxSilence(self.mocker):
            self.push("\n")

    def test_finds_start_delimiter(self):
        with MoxSilence(self.mocker):
            # expect no method calls:
            self.mgr.push("$")

        # now expect calls after second $
        self.mgr.status(EqualIfIn("start delim"))
        self.mocker.ReplayAll()
        self.mgr.push("$")
        self.mocker.VerifyAll()

    def test_extracts(self):
        s = "$$a,simple,test*00\n"
        self.mgr.status(EqualIfIn("start delim"))
        self.expect_extraction_of(s)
        self.mocker.ReplayAll()

        self.push(s)
        self.mocker.VerifyAll()

    def test_can_restart(self):
        # no calls
        with MoxSilence(self.mocker):
            self.push("this is some garbage just to mess things up")

        # check $$ produces start delim
        self.mgr.status(EqualIfIn("start delim"))
        self.mocker.ReplayAll()

        self.push("$$")

        self.mocker.VerifyAll()
        self.mocker.ResetAll()

        # check more delimiters restarts
        self.mgr.status(EqualIfIn("start delim"))
        self.mgr.status(EqualIfIn("start delim"))
        self.mocker.ReplayAll()

        self.push("garbage: after seeing the delimiter, we lose signal.")
        self.push("some extra $s to con$fuse it $")
        self.push("$$")
        self.push("helloworld")

        self.mocker.VerifyAll()
        self.mocker.ResetAll()

        # extract string
        self.expect_extraction_of("$$helloworld\n")

        self.mocker.ReplayAll()
        self.push("\n")
        self.mocker.VerifyAll()

    def test_gives_up_after_1k(self):
        self.mgr.status(EqualIfIn("start delim"))
        self.mgr.status(EqualIfIn("giving up"))

        self.mocker.ReplayAll()
        self.push("$$")
        self.push("a" * 1022)
        self.mocker.VerifyAll()
        self.mocker.ResetAll()

        self.check_newline_no_upload()
        # Check it still works:
        self.test_extracts()

    def test_gives_up_after_16skipped(self):
        self.mgr.status(EqualIfIn("start delim"))
        self.mgr.status(EqualIfIn("giving up"))

        self.mocker.ReplayAll()
        self.push("$$")
        self.mgr.skipped(17)
        self.mocker.VerifyAll()
        self.mocker.ResetAll()

        self.check_newline_no_upload()
        self.test_extracts()

    def test_gives_up_after_16garbage(self):
        self.mgr.status(EqualIfIn("start delim"))
        self.mgr.status(EqualIfIn("giving up"))

        self.mocker.ReplayAll()
        self.push("$$some,legit,data")
        self.push("\t some printable data" * 17)
        self.mocker.VerifyAll()
        self.mocker.ResetAll()

        self.check_newline_no_upload()
        self.test_extracts()

    def test_skipped(self):
        self.mgr.status(EqualIfIn("start delim"))
        self.expect_extraction_of("$$some\0\0\0\0\0data\n")
        self.mocker.ReplayAll()

        self.push("$$some")
        self.mgr.skipped(5)
        self.push("data\n")
        self.mocker.VerifyAll()
