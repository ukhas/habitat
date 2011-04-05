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

import copy
from nose.tools import raises, assert_raises
from habitat.message_server import Message, Listener

b64_valid = u"SSBrbm93IHdoZXJlIHlvdSBsaXZlLgo="
b64_invalid = u"asdfasd"
# I actually tried using 'None' and '{"lol, a dict": True}' but both,
# when converted by str(), are semi-valid b64. >.>
b64_garbage = {"lol, a dict?": "asdffsa"}
received_telem_truev = { "string": "SSBrbm93IHdoZXJlIHlvdSBsaXZlLgo=",
                         "frequency": 1.23 }
received_telem_valid = { u"string": u"SSBrbm93IHdoZXJlIHlvdSBsaXZlLgo=",
                         u"frequency": 1.23 }
received_telem_equal = { u"string": u"SSBrbm93IHdoZXJ       \n" +
                                     "lIHlvdSBsaXZlLgo=",
                         u"frequency": "1.23" }
received_telem_invalid = { u"string": u"asdfasd", u"frequency": "asd.f" }
received_telem_extra = received_telem_valid.copy()
received_telem_extra["knock_knock"] = "Who's there?"

listener_info_valid = {u"name": u"Daniel", u"location": u"Reading, UK",
                       u"radio": u"Yaesu FT817",
                       u"antenna": u"1/4 wave whip"}
listener_info_extra = listener_info_valid.copy()
listener_info_extra[u"badkey"] = True
listener_info_missing = listener_info_valid.copy()
del listener_info_missing["antenna"]

listener_telem_truev = {"time": {"hour": 12, "minute": 40,
                                 "second": 7},
                        "latitude": -35.11, "longitude": 137.567,
                        "altitude": 12}
listener_telem_valid = {u"time": {u"hour": 12, u"minute": 40,
                                  u"second": 7},
                        u"latitude": -35.11, u"longitude": 137.567,
                        u"altitude": 12}
listener_telem_equal = {u"time": {u"hour": 12.00, u"minute": "40",
                                  u"second": u"7"},
                        u"latitude": u"-35.11", u"longitude": "137.567",
                        u"altitude": "12",
                        u"extrakey": u"Hello world!"}
listener_telem_badkv = {u"time": {u"hour": "noint", u"minute": 90,
                                  u"second": u"100"},
                        u"latitude": u"100", u"longitude": 180.100,
                        u"altitude": "maybe not."}

telem_valid = {"_protocol": "UKHAS", "_raw": b64_valid, "time": {"a": 6},
               "z": 1, "asdf": u"There probably won't be any unicode data",
               u"key": "But the test is that Message doesn't touch the dict.",
               "_listener_metadata": {}}
telem_invalid_one = copy.deepcopy(telem_valid)
telem_invalid_one["_raw"] = b64_invalid
telem_invalid_two = copy.deepcopy(telem_valid)
del telem_invalid_two["_listener_metadata"]

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
        message = Message(self.source, Message.RECEIVED_TELEM,
                          18297895, 1238702, received_telem_valid)
        assert message.source == self.source
        assert message.type == Message.RECEIVED_TELEM
        assert message.time_created == 18297895
        assert message.time_uploaded == 1238702
        assert message.data == received_telem_truev

    @raises(TypeError)
    def test_initialiser_rejects_garbage_source(self):
        Message("asdf", Message.RECEIVED_TELEM, 123456, 123456,
                received_telem_valid)

    @raises(TypeError)
    def test_initialiser_rejects_null_source(self):
        Message(None, Message.RECEIVED_TELEM, 123456, 123456,
                received_telem_valid)

    @raises(ValueError)
    def test_initialiser_rejects_invalid_type(self):
        Message(self.source, 951, 123456, 123456,
                received_telem_valid)

    @raises(ValueError)
    def test_initialiser_rejects_garbage_type(self):
        Message(self.source, "asdf", 123456, 123456,
                received_telem_valid)

    @raises(TypeError)
    def test_initialiser_rejects_garbage_time_created(self):
        Message(self.source, Message.RECEIVED_TELEM, None, 123456,
                received_telem_valid)

    @raises(ValueError)
    def test_initialiser_rejects_garbage_time_uploaded(self):
        Message(self.source, Message.RECEIVED_TELEM, 1235123, "lolol",
                received_telem_valid)

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

        valid_data = [ (Message.RECEIVED_TELEM, received_telem_valid),
                       (Message.LISTENER_INFO, listener_info_valid),
                       (Message.LISTENER_TELEM, listener_telem_valid),
                       (Message.TELEM, telem_valid) ]

        for type, data in valid_data:
            assert repr(Message(self.source, type, 123345, 123435, data)) == \
                repr_format % (Message.type_names[type], repr(self.source))

    def good_message_data(self, type, data):
        return Message(self.source, type, 123345, 123435, data)

    def bad_message_data(self, type, data):
        assert_raises(ValueError, self.good_message_data, type, data)

    def wrongtype_message_data(self, type, data):
        assert_raises(TypeError, self.good_message_data, type, data)

    def test_message_coerces_received_telem(self):
        m = self.good_message_data(Message.RECEIVED_TELEM,
                                   received_telem_valid)
        assert m.data == received_telem_truev

        # Also tests that whitespace in the b64 is removed.
        m = self.good_message_data(Message.RECEIVED_TELEM,
                                   received_telem_equal)
        assert m.data == received_telem_truev

        assert isinstance(m.data["string"], str)
        assert isinstance(m.data["frequency"], float)

        for k, v in received_telem_invalid.items():
            t = received_telem_valid.copy()
            t[k] = v
            self.bad_message_data(Message.RECEIVED_TELEM, t)

        m = self.good_message_data(Message.RECEIVED_TELEM,
                                   received_telem_extra)
        assert m.data == received_telem_truev

        self.wrongtype_message_data(Message.RECEIVED_TELEM, None)
        self.wrongtype_message_data(Message.RECEIVED_TELEM, 123)

    def check_all_encodings(self, items, cl):
        for i in items:
            assert isinstance(i, cl)

    def test_message_coerces_listener_info(self):
        self.check_all_encodings(listener_info_valid.keys(), unicode)
        self.check_all_encodings(listener_info_valid.values(), unicode)
        m = self.good_message_data(Message.LISTENER_INFO, listener_info_valid)
        assert m.data == listener_info_valid
        self.check_all_encodings(m.data.keys(), str)
        self.check_all_encodings(m.data.values(), unicode)

        m = self.good_message_data(Message.LISTENER_INFO, listener_info_extra)
        assert m.data == listener_info_valid

        m = self.good_message_data(Message.LISTENER_INFO,
                                   listener_info_missing)
        assert "antenna" not in m.data
        compare = copy.deepcopy(m.data)
        compare["antenna"] = listener_info_valid["antenna"]
        assert compare == listener_info_valid

        self.wrongtype_message_data(Message.LISTENER_INFO, None)
        self.wrongtype_message_data(Message.LISTENER_INFO, 123)

    def test_message_coerces_listener_telem(self):
        self.check_all_encodings(listener_telem_valid.keys(), unicode)
        m = self.good_message_data(Message.LISTENER_TELEM,
                                   listener_telem_valid)
        assert m.data == listener_telem_truev
        self.check_all_encodings(m.data.keys(), str)

        m = self.good_message_data(Message.LISTENER_TELEM,
                                   listener_telem_equal)
        assert m.data == listener_telem_truev

        bad_keys = listener_telem_badkv.copy()

        for key, value in bad_keys["time"].items():
            d = copy.deepcopy(listener_telem_valid)
            d["time"][key] = value
            self.bad_message_data(Message.LISTENER_TELEM, d)

        del bad_keys["time"]

        for key, value in bad_keys.items():
            d = listener_telem_valid.copy()
            d[key] = value
            self.bad_message_data(Message.LISTENER_TELEM, d)

        self.wrongtype_message_data(Message.LISTENER_TELEM, None)
        self.wrongtype_message_data(Message.LISTENER_TELEM, 123)

    def test_message_coerces_telem(self):
        m = self.good_message_data(Message.TELEM, telem_valid)
        for key in telem_valid.keys():
            assert telem_valid[key] == m.data[key]

        str_keys = [k for k in telem_valid.keys() if isinstance(k, str)]
        str_keys2 = [k for k in m.data.keys() if isinstance(k, str)]
        uni_keys = [k for k in telem_valid.keys() if isinstance(k, unicode)]
        uni_keys2 = [k for k in m.data.keys() if isinstance(k, unicode)]

        assert set(str_keys) == set(str_keys2)
        assert set(uni_keys) == set(uni_keys2)

        self.bad_message_data(Message.TELEM, telem_invalid_one)
        self.bad_message_data(Message.TELEM, telem_invalid_two)

        self.wrongtype_message_data(Message.TELEM, None)
        self.wrongtype_message_data(Message.TELEM, 123)

class TestMessageBugs:
    def test_message_listener_telem_allows_24hrs(self):
        """LISTENER_TELEM.data["time"]["hour"] can be > 12 (#9648375)"""
        # https://www.pivotaltracker.com/story/show/9648375
        test_data = copy.deepcopy(listener_telem_valid)
        test_data["time"]["hour"] = 15
        Message(Listener("M0ZDR", "1.2.3.4"), Message.LISTENER_TELEM,
                123345, 123435, test_data)

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
                     "M0RND_Chase", "_", "/", "/LOLWHATGRR", "-"]:
            self.check_allows_good_callsign(call)

    def check_allows_good_callsign(self, call):
        Listener(call, "1.2.3.4")

    def test_rejects_bad_callsigns(self):
        for call in ["M0ZDR'; DELETE TABLE BALLOONS; --", "",
                     "#", "M0'", "M\\", "!", "+", "~", "M0@ND"]:
            self.check_rejects_bad_callsign(call)

    @raises(ValueError)
    def check_rejects_bad_callsign(self, call):
        Listener(call, "1.2.3.4")

    @raises(ValueError)
    def test_rejects_invalid_ip(self):
        # We use ipaddr which is well tested, so we don't need to spend too
        # much time making sure it works. Upon failure it returns ValueError
        Listener("M0ZDR", "1234.1.1.1")

    def test_ip_compares(self):
        assert self.listenera.ip == self.listenerc.ip
        assert self.listenera.ip != self.listenerb.ip

    def test_ip_leading_zeros_compare(self):
        assert self.listenerb.ip == self.listenerd.ip
        assert str(self.listenerb.ip) == str(self.listenerd.ip)
