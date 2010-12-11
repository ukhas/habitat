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
Tests the Message class
""" 

from nose.tools import raises

from habitat.message_server import Message, Listener

class TestMessage:
    def setup(self):
        self.source = Listener("2E0DRX", "1.2.3.4")

    def test_ids_exist_and_are_unique(self):
        types = set()
        for i in Message.type_names:
            type = getattr(Message, i)
            assert type not in types
            types.add(type)
        assert types == set(Message.types)
        assert types == set(range(len(types)))

    def test_initialiser_accepts_and_stores_data(self):
        mydata = {"asdf": "defg", "hjkl": "yuio"}
        message = Message(self.source, Message.RECEIVED_TELEM, mydata)
        assert message.source == self.source
        assert message.type == Message.RECEIVED_TELEM
        assert message.data == mydata

    @raises(TypeError)
    def test_initialiser_rejects_garbage_source(self):
        Message("asdf", Message.RECEIVED_TELEM, "asdf")

    @raises(TypeError)
    def test_initialiser_rejects_null_source(self):
        Message(None, Message.RECEIVED_TELEM, "asdf")

    @raises(ValueError)
    def test_initialiser_rejects_invalid_type(self):
        Message(self.source, 951, "asdf")

    @raises(TypeError)
    def test_initialiser_rejects_garbage_type(self):
        Message(self.source, "asdf", "asdf")

    def test_initialiser_allows_no_data(self):
        Message(self.source, Message.RECEIVED_TELEM, None)

    @raises(TypeError)
    def test_validate_type_rejects_garbage_type(self):
        Message.validate_type("asdf")

    @raises(ValueError)
    def test_validate_type_rejects_invalid_type(self):
        Message.validate_type(951)

    def test_validate_type_accepts_valid_type(self):
        Message.validate_type(Message.LISTENER_TELEM)

class TestListener:
    def setup(self):
        # NB: b & d have different IPs
        self.listenera = Listener("2E0DRX", "1.2.3.4")
        self.listenerb = Listener("2E0DRX", "1.2.3.5")
        self.listenerc = Listener("M0RND", "1.2.3.4")
        self.listenerd = Listener("M0rnd", "001.2.003.5")

    def test_initialiser_accepts_and_stores_data(self):
        assert self.listenerb.callsign == "2E0DRX"
        assert str(self.listenerb.ip) == "1.2.3.5"
        assert self.listenerc.callsign == "M0RND"
        assert str(self.listenerc.ip) == "1.2.3.4"

    def test_callsign_compares(self):
        assert self.listenera.callsign == self.listenerb.callsign
        assert self.listenera.callsign != self.listenerc.callsign

    def test_listener_compares_by_callsign(self):
        """self.listener compares by callsign (only)"""
        assert self.listenera == self.listenerb
        assert self.listenera != self.listenerc

    def test_listener_returns_false_on_garbage_compare(self):
        assert self.listenera != 0

    def test_callsign_toupper(self):
        assert self.listenerd.callsign == "M0RND"
        assert self.listenerc == self.listenerd

    @raises(TypeError)
    def test_rejects_garbage_callsign(self):
        Listener(0, "1.2.3.4")

    @raises(ValueError)
    def test_rejects_nonalphanum_callsign(self):
        Listener("2E0DRX'; DELETE TABLE BALLOONS; --", "1.2.3.4")

    @raises(ValueError) # IPAddress() failures return ValueError
    def test_rejects_invalid_ip(self):
        # We use ipaddr which is well tested, so we don't need to spend too
        # much time making sure it works.
        Listener("2E0DRX", "1234.1.1.1")

    def test_ip_compares(self):
        assert self.listenera.ip == self.listenerc.ip
        assert self.listenera.ip != self.listenerb.ip

    def test_ip_leading_zeros_compare(self):
        assert self.listenerb.ip == self.listenerd.ip
        assert str(self.listenerb.ip) == str(self.listenerd.ip)
