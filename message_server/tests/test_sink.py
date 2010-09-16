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
from message_server import SimpleSink
from message_server import Message, Listener

class EmptySink(SimpleSink):
    def start(self):
        pass

    def message(self):
        pass

class FakeSink(SimpleSink):
    def start(self):
        self.set_types(set([Message.RECEIVED_TELEM, Message.LISTENER_INFO]))
        self.test_messages = []
        self.message = self.test_messages.append

class ChangySink(SimpleSink):
    def start(self):
        self.set_types(set([Message.RECEIVED_TELEM, Message.LISTENER_INFO]))
        self.status = 0

    def message(self, message):
        # Message 1 will be a LISTENER_INFO
        # Message 2 will also be a LISTENER_INFO but we shouldn't get it
        # Message 3 will be a RECEIVED_TELEM

        assert message.data != 2

        if message.data == 1:
            assert self.status == 0
            self.remove_type(Message.LISTENER_INFO)
            self.status = 1
        elif message.data == 3:
            assert self.status == 1
            self.status = 2
        else:
            raise ValueError

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

    def test_start_called(self):
        sink = FakeSink()
        assert sink.types == set([Message.RECEIVED_TELEM,
                                  Message.LISTENER_INFO])
        assert sink.message == sink.test_messages.append

    def test_push_message(self):
        sink = FakeSink()

        # Same story as test_types
        yield self.check_push_unwanted_message, sink
        yield self.check_push_requested_message, sink

    def check_push_unwanted_message(self, sink):
        sink.push_message(Message(Listener(0), Message.TELEM, None))
        assert sink.test_messages == []

    def check_push_requested_message(self, sink):
        message = Message(Listener(0), Message.RECEIVED_TELEM, 100)
        sink.push_message(message)
        assert sink.test_messages == [message]
        assert sink.test_messages[0].data == 100

    def check_sink_changing_types_push(self, sink):
        sink = ChangeySink()
        sink.push_message(Message(Listener(0), Message.LISTENER_INFO, 1))
        sink.push_message(Message(Listener(0), Message.LISTENER_INFO, 2))
        sink.push_message(Message(Listener(0), Message.RECEIVED_TELEM, 3))
        assert sink.status == 2
