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
Tests the Message class, found in ../message.py
""" 

# TODO: when validation is implemented modify these tests

from nose.tools import raises
from message_server import Message, Listener

def wrapme(arg):
   """
   Test Docstring
   """
   pass

class TestMessage:
    def test_ids_exist_and_are_unique(self):
        types = set()
        for i in [ "RECEIVED_TELEM", "LISTENER_INFO", "LISTENER_TELEM", 
                   "TELEM" ]:
            type = getattr(Message, i)
            assert type not in types
            types.add(type)

    def test_initialiser_accepts_and_stores_data(self):
        source = Listener(1234)
        mydata = {"asdf": "defg", "hjkl": "yuio"}
        message = Message(source, Message.RECEIVED_TELEM, mydata)
        assert message.source == source
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
        Message(Listener(0), 951, "asdf")

    @raises(TypeError)
    def test_initialiser_rejects_garbage_type(self):
        Message(Listener(0), "asdf", "asdf")

    def test_initialiser_allows_no_data(self):
        Message(Listener(0), Message.RECEIVED_TELEM, None)

    @raises(TypeError)
    def test_validate_type_rejects_garbage_type(self):
        Message.validate_type("asdf")

    @raises(ValueError)
    def test_validate_type_rejects_invalid_type(self):
        Message.validate_type(951)

    def test_validate_type_accepts_valid_type(self):
        Message.validate_type(Message.LISTENER_TELEM)

class TestListener:
    def test_initialiser_accepts_and_stores_data(self):
        listener = Listener(910)
        assert listener.identifier == 910
        listener = Listener(120)
        assert listener.identifier == 120

    def test_listener_compares(self):
        # identifier is still to be implemented, so we'll just try some stuff
        # NB: "astring".__cmp__() doesn't exist so better hope __eq__ is used
        for i in [[1,      2, False],
                  [1,      1, True],
                  [900,    1, False],
                  ["asdf", "asdf", True]]:
            yield self.check_listener_compares, i

    def check_listener_compares(self, i):
        assert (Listener(i[0]) == Listener(i[1])) == i[2]
