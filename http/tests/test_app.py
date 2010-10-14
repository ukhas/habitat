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

from message_server import Message
from http.app import InsertApplication
from nose.tools import raises

class ServerStub:
    def __init__(self):
        self.messages = []

    def push_message(self, message):
        self.messages.append(message)

class TestInsertApplication:
    """Application (base class)"""
    def setup(self):
        server = ServerStub()
        self.messages = server.messages
        self.app = InsertApplication(server, None, None)
        self.app.push("2.7.5.8", callsign="2E0DRX", type="RECEIVED_TELEM",
                      data="some$data")

    def test_push_pushes_message(self):
        assert len(self.messages) == 1

    def test_push_pushes_callsign_correctly(self):
        assert self.messages[0].source.callsign == "2E0DRX"

    def test_push_pushes_ip_correctly(self):
        assert str(self.messages[0].source.ip) == "2.7.5.8"

    def test_push_pushes_type_correctly(self):
        assert self.messages[0].type == Message.RECEIVED_TELEM

    def test_push_pushes_data_correctly(self):
        assert self.messages[0].data == "some$data"

    @raises(ValueError)
    def test_push_refuses_forbidden_types(self):
        self.app.push("2.7.5.8", callsign="2E0DRX", type="TELEM", data="haxx")

    @raises(ValueError)
    def test_push_raises_listener_callsign_errors(self):
        self.app.push("2.7.5.8", callsign="invalid char:",
                      type="RECEIVED_TELEM", data="haxx")

    @raises(ValueError)
    def test_push_raises_message_type_errors(self):
        self.app.push("2.7.5.8", callsign="2E0DRX", type="NOT_A_TYPE",
                      data="haxx")

    # So that it's easy to extent/update later 
    def test_push_allows_other_args(self):
        self.app.push("2.7.5.8", callsign="2E0DRX", type="RECEIVED_TELEM",
                      data="some$data", cookieplease=True)
        assert len(self.messages) == 2
        self.messages.pop(1)

    def test_push_requires_args(self):
        for i in ["callsign", "type", "data"]:
            self.check_push_requires_arg(i)

    @raises(ValueError)
    def check_push_requires_arg(self, arg):
        kwargs = { "callsign": "2E0DRX", "type": "RECEIVED_TELEM", 
                   "data": "some$data" }
        del kwargs[arg]
        self.app.push("2.7.5.8", **kwargs)
