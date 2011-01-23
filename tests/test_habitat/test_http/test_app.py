# Copyright 2010 (C) Daniel Richman
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
Tests the habitat http app, which creates a {{f,s,}cgi,http} server.
"""

from nose.tools import raises
from habitat.message_server import Message
from serverstub import ServerStub
from habitat.http import InsertApplication

import habitat.http as http_module
import time

fake_time_now = 129830
fake_time_created = 125232
fake_time_lag = 100

class FakeTime:
    def time(self):
        return fake_time_now

class TestInsertApplication:
    """Application (base class)"""
    def setup(self):
        assert http_module.time == time
        self.faketime = FakeTime()
        http_module.time = self.faketime

        server = ServerStub()
        self.messages = server.messages
        self.app = InsertApplication(server, None)
        self.args = {"callsign": "M0ZDR",
                     "type": "RECEIVED_TELEM",
                     "time_created": fake_time_created,
                     "time_uploaded": fake_time_now - fake_time_lag,
                     "data": "SSBrbm93IHdoZXJlIHlvdSBsaXZlLgo="}
        self.app.message("2.7.5.8", self.args)

    def teardown(self):
        assert http_module.time == self.faketime
        http_module.time = time

    def test_message_pushes_message(self):
        assert len(self.messages) == 1

    def test_message_pushes_callsign_correctly(self):
        assert self.messages[0].source.callsign == "M0ZDR"

    def test_message_pushes_ip_correctly(self):
        assert str(self.messages[0].source.ip) == "2.7.5.8"

    def test_message_pushes_type_correctly(self):
        assert self.messages[0].type == Message.RECEIVED_TELEM

    def test_message_pushes_times_correctly(self):
        # time_received should be fake_time_now
        # time_uploaded is 100 seconds 'behind' FakeTime.time(), that is,
        # server time, so habitat should assume that all the times submitted
        # by this client are 100 seconds too low.
        # Therefore, time_created should become
        # fake_time_created + fake_time_lag
        assert self.messages[0].time_created == fake_time_created + \
                                               fake_time_lag
        assert self.messages[0].time_received == fake_time_now

    def test_message_pushes_data_correctly(self):
        assert self.messages[0].data == "SSBrbm93IHdoZXJlIHlvdSBsaXZlLgo="

    @raises(ValueError)
    def test_message_refuses_forbidden_types(self):
        args = self.args.copy()
        args["type"] = "TELEM"
        self.app.message("2.7.5.8", args)

    @raises(ValueError)
    def test_message_raises_listener_callsign_errors(self):
        args = self.args.copy()
        args["callsign"] = "invalid char"
        self.app.message("2.7.5.8", args)

    @raises(ValueError)
    def test_message_raises_message_type_errors(self):
        args = self.args.copy()
        args["type"] = "NOT_A_TYPE"
        self.app.message("2.7.5.8", args)

    @raises(ValueError)
    def test_message_raises_time_created_int_errors(self):
        args = self.args.copy()
        args["time_created"] = "lol"
        self.app.message("2.7.5.8", args)

    @raises(ValueError)
    def test_message_raises_time_uploaded_int_errors(self):
        args = self.args.copy()
        args["time_uploaded"] = "..."
        self.app.message("2.7.5.8", args)

    # So that it's easy to extend/update later
    def test_message_allows_other_args(self):
        args = self.args.copy()
        args["one_more_thing"] = "cookie please?"
        self.app.message("2.7.5.8", args)
        assert len(self.messages) == 2
        self.messages.pop(1)

    def test_message_requires_args(self):
        for i in ["callsign", "type", "time_created", "time_uploaded", "data"]:
            self.check_message_requires_arg(i)

    @raises(ValueError)
    def check_message_requires_arg(self, arg):
        args = self.args.copy()
        del args[arg]
        self.app.message("2.7.5.8", args)
