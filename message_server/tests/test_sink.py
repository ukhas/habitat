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
Tests the Sink class, found in ../sink.py
""" 

from nose.tools import raises
from message_server import Sink
from message_server import Message

class EmptySink(Sink):
    def start(self):
        pass

    def message(self):
        pass

class FakeSink(Sink):
    def start(self):
        self.set_types(set([Message.RECEIVED_TELEM, Message.LISTENER_INFO]))
        self.test_messages = []
        self.message = self.test_messages.append

class TestSink:
    def test_types_is_a_set(self):
        sink = EmptySink()
        assert isinstance(sink.types, set)

    def test_types(self):
        sink = EmptySink()

        # We need these executed in this precise order but it'd be nice if
        # they were printed by spec as separate tests:
        yield self.check_add_types, sink
        yield self.check_remove_type_a, sink
        yield self.check_add_type_a, sink
        yield self.check_add_type_b, sink
        yield self.check_add_type_c, sink
        yield self.check_remove_types, sink
        yield self.check_remove_type_b, sink
        yield self.check_set_types, sink
        yield self.check_clear_types, sink

    def check_add_types(self, sink):
        sink.add_types(set([Message.RECEIVED_TELEM, Message.LISTENER_INFO]))
        assert sink.types == set([Message.RECEIVED_TELEM, 
                                  Message.LISTENER_INFO])

    def check_remove_type_a(self, sink):
        sink.remove_type(Message.RECEIVED_TELEM)
        assert sink.types == set([Message.LISTENER_INFO])

    def check_add_type_a(self, sink):
        sink.add_type(Message.TELEM)
        assert sink.types == set([Message.LISTENER_INFO, Message.TELEM])

    def check_add_type_b(self, sink):
        sink.add_type(Message.TELEM)
        assert sink.types == set([Message.LISTENER_INFO, Message.TELEM])

    def check_add_type_c(self, sink):
        sink.add_type(Message.RECEIVED_TELEM)
        assert sink.types == set([Message.LISTENER_INFO, Message.TELEM,
                                  Message.RECEIVED_TELEM])

    def check_remove_types(self, sink):
        sink.remove_types(set([Message.LISTENER_INFO, Message.TELEM]))
        assert sink.types == set([Message.RECEIVED_TELEM])

    def check_remove_type_b(self, sink):
        sink.remove_type(Message.RECEIVED_TELEM)
        assert sink.types == set([])

    def check_set_types(self, sink):
        sink.set_types(set([Message.LISTENER_INFO, Message.LISTENER_INFO,
                            Message.LISTENER_TELEM]))
        assert sink.types == set([Message.LISTENER_INFO,
                                  Message.LISTENER_TELEM])

    def check_clear_types(self, sink):
        sink.clear_types()
        assert sink.types == set([])

    def test_can_remove_type_twice(self):
        sink = EmptySink()
        sink.add_type(Message.RECEIVED_TELEM)
        sink.remove_type(Message.RECEIVED_TELEM)
        sink.remove_type(Message.RECEIVED_TELEM)
        # Should not produce a KeyError
    
    def test_rejects_garbage(self):
        sink = EmptySink()
        for i in [sink.add_type, sink.remove_type]:
            yield self.check_rejects_garbage_type, i
            yield self.check_rejects_invalid_type, i
    
        for i in [sink.add_types, sink.remove_types,
                  sink.set_types]:
            yield self.check_rejects_garbage_types, i
            yield self.check_rejects_garbage_set, i
            yield self.check_rejects_invalid_types, i
    
    @raises(TypeError)
    def check_rejects_garbage_type(self, func):
        func("asdf")
    
    @raises(TypeError)
    def check_rejects_garbage_types(self, func):
        func(set(["asdf", Message.RECEIVED_TELEM]))
    
    @raises(TypeError)
    def check_rejects_garbage_set(self, func):
        func(1337) # An int, not a set
    
    @raises(ValueError)
    def check_rejects_invalid_type(self, func):
        func(951)
    
    @raises(ValueError)
    def check_rejects_invalid_types(self, func):
        func(set([Message.RECEIVED_TELEM, 952]))
