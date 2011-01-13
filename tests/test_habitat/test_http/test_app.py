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

class TestInsertApplication:
    """Application (base class)"""
    def setup(self):
        server = ServerStub()
        self.messages = server.messages
        self.app = InsertApplication(server, None)
        args = {"callsign": "M0ZDR", "type": "RECEIVED_TELEM",
                "data": "some$data"}
        self.app.message("2.7.5.8", args)

    def test_message_pushes_message(self):
        assert len(self.messages) == 1

    def test_message_pushes_callsign_correctly(self):
        assert self.messages[0].source.callsign == "M0ZDR"

    def test_message_pushes_ip_correctly(self):
        assert str(self.messages[0].source.ip) == "2.7.5.8"

    def test_message_pushes_type_correctly(self):
        assert self.messages[0].type == Message.RECEIVED_TELEM

    def test_message_pushes_data_correctly(self):
        assert self.messages[0].data == "some$data"

    @raises(ValueError)
    def test_message_refuses_forbidden_types(self):
        args = {"callsign": "M0ZDR", "type": "TELEM", "data": "haxx"}
        self.app.message("2.7.5.8", args)

    @raises(ValueError)
    def test_message_raises_listener_callsign_errors(self):
        args = {"callsign": "invalid char:", "type": "RECEIVED_TELEM",
                "data": "haxx"}
        self.app.message("2.7.5.8", args)

    @raises(ValueError)
    def test_message_raises_message_type_errors(self):
        args = {"callsign": "M0ZDR", "type": "NOT_A_TYPE", "data": "haxx"}
        self.app.message("2.7.5.8", args)

    # So that it's easy to extend/update later
    def test_message_allows_other_args(self):
        args = {"callsign": "M0ZDR", "type": "RECEIVED_TELEM",
                "data": "some$data", "cookieplease": True}
        self.app.message("2.7.5.8", args)
        assert len(self.messages) == 2
        self.messages.pop(1)

    def test_message_requires_args(self):
        for i in ["callsign", "type", "data"]:
            self.check_message_requires_arg(i)

    @raises(ValueError)
    def check_message_requires_arg(self, arg):
        args = { "callsign": "M0ZDR", "type": "RECEIVED_TELEM",
                 "data": "some$data" }
        del args[arg]
        self.app.message("2.7.5.8", args)
