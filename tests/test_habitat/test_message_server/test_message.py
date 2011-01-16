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
        self.source = Listener("M0ZDR", "1.2.3.4")

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
        message = Message(self.source, Message.RECEIVED_TELEM,
                          18297895, 1238702, mydata)
        assert message.source == self.source
        assert message.type == Message.RECEIVED_TELEM
        assert message.time_created == 18297895
        assert message.time_received == 1238702
        assert message.data == mydata

    @raises(TypeError)
    def test_initialiser_rejects_garbage_source(self):
        Message("asdf", Message.RECEIVED_TELEM, 123456, 123456, "asdf")

    @raises(TypeError)
    def test_initialiser_rejects_null_source(self):
        Message(None, Message.RECEIVED_TELEM, 123456, 123456, "asdf")

    @raises(ValueError)
    def test_initialiser_rejects_invalid_type(self):
        Message(self.source, 951, 123456, 123456, "asdf")

    @raises(ValueError)
    def test_initialiser_rejects_garbage_type(self):
        Message(self.source, "asdf", 123456, 123456, "asdf")

    def test_initialiser_allows_no_data(self):
        Message(self.source, Message.RECEIVED_TELEM, 123456, 123456, None)

    @raises(TypeError)
    def test_initialiser_rejects_garbage_time_created(self):
        Message(self.source, Message.TELEM, None, 123456, "asdf")

    @raises(ValueError)
    def test_initialiser_rejects_garbage_time_received(self):
        Message(self.source, Message.TELEM, 1235123, "lolol", "asdf")

    @raises(ValueError)
    def test_validate_type_rejects_garbage_type(self):
        Message.validate_type("asdf")

    @raises(ValueError)
    def test_validate_type_rejects_invalid_type(self):
        Message.validate_type(951)

    def test_validate_type_accepts_valid_type(self):
        Message.validate_type(Message.LISTENER_TELEM)

    def test_repr(self):
        repr_format = "<habitat.message_server.Message (%s) from %s>"

        for type in Message.types:
            assert repr(Message(self.source, type, 123345, 123435, None)) == \
                repr_format % (Message.type_names[type], repr(self.source))

class TestListener:
    def setup(self):
        # NB: b & d have different IPs
        self.listenera = Listener("M0ZDR", "1.2.3.4")
        self.listenerb = Listener("M0ZDR", "1.2.3.5")
        self.listenerc = Listener("M0RND", "1.2.3.4")
        self.listenerd = Listener("M0rnd", "001.2.003.5")

    def test_repr(self):
        repr_format = "<habitat.message_server.Listener %s at %s>"
        assert repr(self.listenera) == repr_format % ("M0ZDR", "1.2.3.4")
        assert repr(self.listenerd) == repr_format % ("M0RND", "1.2.3.5")

    def test_initialiser_accepts_and_stores_data(self):
        assert self.listenerb.callsign == "M0ZDR"
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

    def test_allows_good_callsigns(self):
        for call in ["M0ZDR", "M0RND", "G4QQQ", "M0ZDR/MM", "MORND_CHASE",
                     "M0RND_Chase", "_", "/", "/LOLWHATGRR"]:
            self.check_allows_good_callsign(call)

    def check_allows_good_callsign(self, call):
        Listener(call, "1.2.3.4")

    def test_rejects_bad_callsigns(self):
        for call in ["M0ZDR'; DELETE TABLE BALLOONS; --", "",
                     "#", "M0'", "M-", "-", "+", "~", "M0@ND"]:
            self.check_rejects_bad_callsign(call)

    @raises(ValueError)
    def check_rejects_bad_callsign(self, call):
        Listener(call, "1.2.3.4")

    @raises(ValueError) # IPAddress() failures return ValueError
    def test_rejects_invalid_ip(self):
        # We use ipaddr which is well tested, so we don't need to spend too
        # much time making sure it works.
        Listener("M0ZDR", "1234.1.1.1")

    def test_ip_compares(self):
        assert self.listenera.ip == self.listenerc.ip
        assert self.listenera.ip != self.listenerb.ip

    def test_ip_leading_zeros_compare(self):
        assert self.listenerb.ip == self.listenerd.ip
        assert str(self.listenerb.ip) == str(self.listenerd.ip)
