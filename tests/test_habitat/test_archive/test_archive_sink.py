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

class FakeDB(object):
    def __init__(self):
        self.items = {}
        self.docs = []
    def __getitem__(self, key):
        return self.items[key]
    def __setitem__(self, key, item):
        self.items[key] = item
    def save_doc(self, doc):
        self.docs.append(doc)

class FakeServer(object):
    def __init__(self):
        self.db = FakeDB()
    def push_message(self, message):
        pass

class FakeListener(object):
    def __init__(self):
        self.callsign = "habitat"
        self.ip = "123.123.123.123"

class FakeListenerTelemMessage(object):
    def __init__(self, data=listener_telem_data):
        self.type = Message.LISTENER_TELEM
        self.source = FakeListener()
        self.data = data

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
        # TODO: Should also involve a time
        self.sink.push_message(FakeListenerTelemMessage())
        assert len(self.server.db.docs) == 1
        assert self.server.db.docs[0] == listener_telem_doc

    def test_rejects_LISTENER_TELEM_docs_without_data(self):
        for key in ["latitude", "longitude", "altitude", "time"]:
            data = deepcopy(listener_telem_data)
            del data[key]
            assert_raises(ValueError, self.sink.push_message,
                FakeListenerTelemMessage(data))
        for key in ["hour", "minute", "second"]:
            data = deepcopy(listener_telem_data)
            del data["time"][key]
            assert_raises(ValueError, self.sink.push_message,
                FakeListenerTelemMessage(data))

    def test_rejects_LISTENER_TELEM_docs_with_invalid_data(self):
        for key, newdata in (
                ("latitude", "bad"),
                ("longitude", "bad"),
                ("altitude", "bad"),
                ("time", "bad"),
                ("time", {"hour": "bad", "minute": 32, "second": 32}),
                ("time", {"hour": 12, "minute": "bad", "second": 32}),
                ("time", {"hour": 12, "minute": 32, "second": "bad"}),
                ("time", {"hour": -1, "minute": 23, "second": 23}),
                ("time", {"hour": 13, "minute": 23, "second": 23}),
                ("time", {"hour": 11, "minute": -1, "second": 23}),
                ("time", {"hour": 11, "minute": 64, "second": 23}),
                ("time", {"hour": 11, "minute": 11, "second": -1}),
                ("time", {"hour": 11, "minute": 11, "second": 62})
                ):
            data = deepcopy(listener_telem_data)
            data[key] = newdata
            assert_raises(ValueError, self.sink.push_message,
                FakeListenerTelemMessage(data))
