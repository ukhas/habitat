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

import threading
import functools
from nose.tools import raises
from message_server import SimpleSink, ThreadedSink
from message_server import Message, Listener

from slowsink import *

class EmptySink(SimpleSink):
    def setup(self):
        pass

    def message(self):
        pass

class FakeSink(SimpleSink):
    def setup(self):
        self.set_types(set([Message.RECEIVED_TELEM, Message.LISTENER_INFO]))
        self.test_messages = []
        self.message = self.test_messages.append

class ChangeySink():
    def setup(self):
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

class ChangeySimpleSink(SimpleSink, ChangeySink):
    pass

class ChangeyThreadedSink(ThreadedSink, ChangeySink):
    pass

class FakeThreadedSink(ThreadedSink):
    def setup(self):
        self.set_types(set([Message.RECEIVED_TELEM, Message.LISTENER_INFO]))
        self.status = 0
        self.failed = 0
        self.test_thread = None

    def message(self, message):
        self.status = self.status + 1

        if self.test_thread != None:
            if self.test_thread != threading.current_thread():
                self.failed = 1
        else:
            self.test_thread = threading.current_thread()

class ThreadedPush(threading.Thread):
    def __init__(self, sink, message, event):
        threading.Thread.__init__(self)
        self.sink = sink
        self.message = message
        self.event = event

    def run(self):
        try:
            self.sink.push_message(self.message)
        finally:
            self.event.set()

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

    def test_setup_called(self):
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

    def test_sink_changing_types_push(self):
        yield self.check_sink_changing_types_push, ChangeySimpleSink
        yield self.check_sink_changing_types_push, ChangeyThreadedSink

    def check_sink_changing_types_push(self, sink_class):
        sink = sink_class()

        sink.push_message(Message(Listener(0), Message.LISTENER_INFO, 1))
        sink.push_message(Message(Listener(0), Message.LISTENER_INFO, 2))
        sink.push_message(Message(Listener(0), Message.RECEIVED_TELEM, 3))

        try:
            sink.queue.join()
        except(AttributeError):
            pass

        assert sink.status == 2

    def test_threaded_sink_executes_in_one_thread(self):
        sink = FakeThreadedSink()
        done_a = threading.Event()
        done_b = threading.Event()
        done_c = threading.Event()

        ThreadedPush(sink, Message(Listener(0), Message.LISTENER_INFO, 1),
                     done_a).start()
        ThreadedPush(sink, Message(Listener(0), Message.LISTENER_INFO, 2),
                     done_b).start()
        ThreadedPush(sink, Message(Listener(0), Message.RECEIVED_TELEM, 3),
                     done_c).start()

        done_a.wait()
        done_b.wait()
        done_c.wait()

        sink.queue.join()

        assert sink.failed == 0
        assert sink.status == 3

    def test_flush(self):
        yield self.check_flush_race, SlowSimpleSink
        yield self.check_flush_race, SlowThreadedSink

    def check_flush_race(self, sink_class):
        # Testing a race condition is quite difficult.
        # SlowSink.message() will time.sleep(0.02)
        sink = sink_class()

        push = functools.partial(sink.push_message,
                                 Message(Listener(0), Message.TELEM, None))
        t = threading.Thread(target=push)
        t.start()

        sink.in_message.wait()
        assert sink.in_message.is_set()
        sink.flush()
        assert not sink.in_message.is_set()

        t.join()
