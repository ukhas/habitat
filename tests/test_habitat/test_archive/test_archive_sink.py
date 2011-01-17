# Copyright 2010 (C) Adam Greig
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
"""

from nose.tools import assert_raises
from copy import deepcopy
from test_habitat.lib import fake_couchdb

from habitat.message_server import Message
from habitat.archive import ArchiveSink

class FakeServer(object):
    def __init__(self):
        self.db = fake_couchdb.Database()
    def push_message(self, message):
        pass

class FakeListener(object):
    def __init__(self, callsign="habitat", ip="123.123.123.123"):
        self.callsign = callsign
        self.ip = ip

class FakeMessage(object):
    def __init__(self, mtype, data, source=None, time_created=12345,
            time_received=54321):
        if source:
            self.source = source
        else:
            self.source = FakeListener()
        self.type = mtype
        self.data = data
        self.time_created = time_created
        self.time_received = time_received

###########################################################
# Listener Telem docs

listener_telem_data = {
    "time": {
        "hour": 12,
        "minute": 40,
        "second": 12
    },
    "latitude": -35.5,
    "longitude": 137.5,
    "altitude": 12
}

listener_telem_doc = {"type": "listener_telem"}
listener_telem_doc["data"] = deepcopy(listener_telem_data)
listener_telem_doc["data"]["callsign"] = "habitat"

###########################################################
# Listener Info docs

listener_info_data = {
    "name": "habitat project",
    "rating": "awesome"
}

listener_info_doc = {"type": "listener_info"}
listener_info_doc["data"] = deepcopy(listener_info_data)
listener_info_doc["data"]["callsign"] = "habitat"

listener_info_doc_wrong = deepcopy(listener_info_doc)
listener_info_doc_wrong["data"]["callsign"] = "wrong"

listener_info_data_two = deepcopy(listener_info_data)
listener_info_data_two["rating"] = "xtreme"

listener_info_doc_two = {"type": "listener_info"}
listener_info_doc_two["data"] = deepcopy(listener_info_data_two)
listener_info_doc_two["data"]["callsign"] = "habitat"

view_results_none = fake_couchdb.ViewResults()

view_results_old = fake_couchdb.ViewResults({
    "value": None,
    "key": ["habitat", "123456789"],
    "doc": listener_info_doc})

view_results_wrong = fake_couchdb.ViewResults({
    "value": None,
    "key": ["wrong", "2345"],
    "doc": listener_info_doc_wrong})

###########################################################
# Telem and Received Telem docs
listener_one = FakeListener("habitat_one")
listener_two = FakeListener("habitat_two")
raw_data = "dGVzdCBtZXNzYWdl"
parsed_data = {"_raw": "dGVzdCBtZXNzYWdl", "parsed_data": True}
parsed_data_two = {"_raw": "dGVzdCBtZXNzYWdl", "parsed_data": "two"}
parsed_data_three = {"_raw": "dGVzdCBtZXNzYWdl", "newly_parsed": True}
doc_id = "03bde3390e8a8e803c4cebdc24c73ea6e1fed09d5bb3ab15f3dc364d82cfccc0"

raw_type = Message.RECEIVED_TELEM
parsed_type = Message.TELEM

message_raw_from_one = FakeMessage(raw_type, raw_data, listener_one)
message_raw_from_two = FakeMessage(raw_type, raw_data, listener_two)
message_parsed_from_one = FakeMessage(parsed_type, parsed_data, listener_one)
message_parsed_from_two = FakeMessage(parsed_type, parsed_data, listener_two)
message_different_parsed_from_one = FakeMessage(parsed_type, parsed_data_two,
        listener_one)
message_different_parsed_from_two = FakeMessage(parsed_type, parsed_data_two,
        listener_two)
message_new_parsed_from_one = FakeMessage(parsed_type, parsed_data_three,
        listener_one)
message_new_parsed_from_two = FakeMessage(parsed_type, parsed_data_three,
        listener_two)

class TestArchiveSink(object):
    def setup(self):
        self.server = FakeServer()
        self.sink = ArchiveSink(self.server)

    def test_receives_RECEIVED_TELEM_messages(self):
        assert Message.RECEIVED_TELEM in self.sink.types

    def test_receives_LISTENER_INFO_messages(self):
        assert Message.LISTENER_INFO in self.sink.types

    def test_receives_LISTENER_TELEM_messages(self):
        assert Message.LISTENER_INFO in self.sink.types

    def test_receives_TELEM_messages(self):
        assert Message.TELEM in self.sink.types

    def test_stores_new_LISTENER_TELEM_documents(self):
        self.sink.push_message(
            FakeMessage(Message.LISTENER_TELEM, listener_telem_data))
        assert len(self.server.db.docs) == 1
        print self.server.db.saved_docs[0]
        print listener_telem_doc
        assert self.server.db.saved_docs[0] == listener_telem_doc

    def test_stores_new_LISTENER_INFO_documents(self):
        for view_results in [view_results_none, view_results_wrong]:
            self.server.db = fake_couchdb.Database()
            self.server.db.view_results = view_results
            self.sink.push_message(
                FakeMessage(Message.LISTENER_INFO, listener_info_data))
            assert len(self.server.db.docs) == 1
            assert self.server.db.saved_docs[0] == listener_info_doc

    def test_doesnt_store_duplicate_LISTENER_INFO_document(self):
        self.sink.push_message(
            FakeMessage(Message.LISTENER_INFO, listener_info_data))
        self.server.db.view_results = view_results_old
        self.sink.push_message(
            FakeMessage(Message.LISTENER_INFO, listener_info_data))
        assert len(self.server.db.docs) == 1
        assert self.server.db.saved_docs[0] == listener_info_doc

    def test_does_store_updated_LISTENER_INFO_document(self):
        self.sink.push_message(
            FakeMessage(Message.LISTENER_INFO, listener_info_data))
        self.server.db.view_results = view_results_old
        self.sink.push_message(
            FakeMessage(Message.LISTENER_INFO, listener_info_data_two))
        assert len(self.server.db.docs) == 2
        assert self.server.db.saved_docs[0] == listener_info_doc
        assert self.server.db.saved_docs[1] == listener_info_doc_two
    
    def test_raw__no_existing__no_receiver(self):
        """handles RECEIVED_TELEM with no existing data"""
        pass

    def test_raw__raw_existing__same_receiver(self):
        """handles RECEIVED_TELEM with existing raw data from """
        """the same receiver"""
        pass

    def test_raw__raw_existing__new_receiver(self):
        """handles RECEIVED_TELEM with existing raw data from """
        """another receiver"""
        pass

    def test_raw__parsed_existing__same_receiver(self):
        """handles RECEIVED_TELEM with existing parsed data from """
        """the same receiver"""
        pass
    
    def test_raw__parsed_existing__new_receiver(self):
        """handles RECEIVED_TELEM with existing parsed data from """
        """another receiver"""
        pass

    def test_parsed__no_existing__no_receiver(self):
        """handles TELEM with no existing data"""
        pass

    def test_parsed__raw_existing__same_receiver(self):
        """handles TELEM with existing raw data from the same receiver"""
        pass
    
    def test_parsed__raw_existing__new_receiver(self):
        """handles TELEM with existing raw data from another receiver"""
        pass

    def test_parsed__parsed_existing__same_receiver(self):
        """handles TELEM with existing parsed data from the same receiver"""
        pass

    def test_parsed__parsed_existing__new_receiver(self):
        """handles TELEM with existing parsed data from another receiver"""
        pass

    def test_parsed__old_parsed_existing__same_receiver(self):
        """handles TELEM containing changed data with existing parsed """
        """data from the same receiver"""
        pass

    def test_parsed__old_parsed_existing__new_receiver(self):
        """handles TELEM containing changed data with existing parsed """
        """data from another receiver"""
        pass
    
    def test_new_parsed__old_parsed_existing__same_receiver(self):
        """handles TELEM containing new data with existing parsed data """
        """from the same receiver"""
        pass

    def test_new_parsed__old_parsed_existing__new_receiver(self):
        """handles TELEM containing new data with existing parsed data """
        """from another receiver"""
        pass