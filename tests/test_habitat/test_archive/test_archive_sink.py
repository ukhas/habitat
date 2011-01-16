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

view_results_none = fake_couchdb.ViewResults()

view_results_old = fake_couchdb.ViewResults({
    "value": None,
    "key": ["habitat", "123456789"],
    "doc": listener_info_doc})

view_results_wrong = fake_couchdb.ViewResults({
    "value": None,
    "key": ["wrong", "2345"],
    "doc": listener_info_doc_wrong})

class FakeServer(object):
    def __init__(self):
        self.db = fake_couchdb.Database()
    def push_message(self, message):
        pass

class FakeListener(object):
    def __init__(self):
        self.callsign = "habitat"
        self.ip = "123.123.123.123"

class FakeMessage(object):
    def __init__(self, mtype, data):
        self.type = mtype
        self.data = data
        self.source = FakeListener()

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

    def test_does_store_updated_LISTENER_INFO_document(self):
        self.sink.push_message(
            FakeMessage(Message.LISTENER_INFO, listener_info_data))
        self.server.db.view_results = view_results_old
        self.sink.push_message(
            FakeMessage(Message.LISTENER_INFO, listener_info_data_two))
        assert len(self.server.db.docs) == 2
