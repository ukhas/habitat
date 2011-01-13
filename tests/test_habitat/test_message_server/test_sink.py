# Copyright 2010 (C) Daniel Richman, Adam Greig
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
Tests the Sink class, found in
"""

import threading
import functools

from nose.tools import raises

from habitat.message_server import Message, Listener, Server
from habitat.utils.dynamicloader import fullname
from habitat.utils import crashmat

from test_habitat.lib import threading_checks
from test_habitat.lib.locktroll import LockTroll

from fakesink import SinkWithoutSetup, SinkWithoutMessage
from slowsink import SlowSimpleSink, SlowThreadedSink

from habitat.message_server import SimpleSink, ThreadedSink

class FakeProgram:
    db = {"message_server_config": { "sinks": [] }  }

class EmptySink(SimpleSink):
    def setup(self):
        pass
    def message(self, message):
        pass

class EmptyThreadedSink(ThreadedSink):
    def setup(self):
        pass
    def message(self, message):
        pass

class FakeSink(SimpleSink):
    def setup(self):
        self.set_types(set([Message.RECEIVED_TELEM, Message.LISTENER_INFO]))
        self.test_messages = []
        self.message = self.test_messages.append
    def message(self, message):
        pass

class DelayableMixIn:
    def setup(self):
        self.set_types(set([Message.RECEIVED_TELEM, Message.LISTENER_INFO]))
        self.go = threading.Event()
        self.go.set()
        self.waiting = threading.Event()
    def message(self, message):
        self.waiting.set()
        self.go.wait()
        self.waiting.clear()

class DelayableSink(SimpleSink, DelayableMixIn):
    pass

class DelayableThreadedSink(ThreadedSink, DelayableMixIn):
    pass

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

class ThreadedPush(crashmat.Thread):
    def __init__(self, sink, message):
        crashmat.Thread.__init__(self)
        self.name = "Test Thread: ThreadedPush"
        self.sink = sink
        self.message = message

    def run(self):
        self.sink.push_message(self.message)

class TestSink:
    def setup(self):
        threading_checks.patch()

        self.source = Listener("M0ZDR", "1.2.3.4")

    def teardown(self):
        threading_checks.restore()

    @raises(TypeError)
    def test_init_rejects_garbage_server(self):
        EmptySink("asdf")

    @raises(TypeError)
    def test_sink_init_fails_without_setup_method(self):
        s = SinkWithoutSetup(None)

    @raises(TypeError)
    def test_sink_init_fails_without_message_method(self):
        s = SinkWithoutMessage(None)

    def test_messagecount(self):
        yield self.check_messagecount, FakeSink
        yield self.check_messagecount, FakeThreadedSink

    def check_messagecount(self, sinkclass):
        sink = sinkclass(Server(FakeProgram()))
        assert sink.message_count == 0
        sink.push_message(Message(self.source, Message.TELEM, None))
        sink.push_message(Message(self.source, Message.TELEM, None))
        sink.push_message(Message(self.source, Message.TELEM, None))
        sink.push_message(Message(self.source, Message.TELEM, None))
        sink.flush()
        assert sink.message_count == 0
        sink.push_message(Message(self.source, Message.RECEIVED_TELEM, None))
        sink.flush()
        assert sink.message_count == 1
        sink.push_message(Message(self.source, Message.RECEIVED_TELEM, None))
        sink.push_message(Message(self.source, Message.RECEIVED_TELEM, None))
        sink.push_message(Message(self.source, Message.RECEIVED_TELEM, None))
        sink.flush()
        assert sink.message_count == 4
        sink.shutdown()

    def test_repr_simple(self):
        sink = DelayableSink(Server(FakeProgram()))

        expect_format = "<" + fullname(sink.__class__) + " (SimpleSink): %s>"
        info_format = expect_format % "%s messages so far, %s executing now"
        locked_format = expect_format % "locked"

        assert repr(sink) == info_format % (0, 0)

        troll = LockTroll(sink.cv)
        troll.start()
        assert repr(sink) == locked_format
        troll.release()

        message = Message(self.source, Message.RECEIVED_TELEM, None)

        sink.push_message(message)
        sink.push_message(message)
        assert repr(sink) == info_format % (2, 0)

        thread_a = ThreadedPush(sink, message)
        thread_b = ThreadedPush(sink, message)
        sink.go.clear()
        sink.waiting.clear()
        thread_a.start()
        sink.waiting.wait()
        sink.waiting.clear()
        thread_b.start()
        sink.waiting.wait()
        assert repr(sink) == info_format % (2, 2)
        sink.go.set()
        thread_a.join()
        thread_b.join()
        assert repr(sink) == info_format % (4, 0)
        sink.shutdown()

    def test_repr_threaded(self):
        sink = DelayableThreadedSink(Server(FakeProgram()))

        base_format = "<" + fullname(sink.__class__)  + " (ThreadedSink): %s>"
        info_format = base_format % "%s messages so far, roughly %s queued%s"
        locked_format = base_format % "locked"

        assert repr(sink) == info_format % (0, 0, "")

        troll = LockTroll(sink.stats_lock)
        troll.start()
        assert repr(sink) == locked_format
        troll.release()

        message = Message(self.source, Message.RECEIVED_TELEM, None)

        sink.push_message(message)
        sink.push_message(message)
        sink.flush()
        assert repr(sink) == info_format % (2, 0, "")

        sink.go.clear()

        sink.push_message(message)
        sink.push_message(message)
        sink.waiting.wait()

        assert repr(sink) == info_format % (2, 1, ", currently executing")

        troll = LockTroll(sink.stats_lock)
        troll.start()
        assert repr(sink) == locked_format
        troll.release()

        sink.go.set()
        sink.flush()

        assert repr(sink) == info_format % (4, 0, "")

        sink.shutdown()

    def test_types_is_a_set(self):
        sink = EmptySink(Server(FakeProgram()))
        assert isinstance(sink.types, set)

    def test_sink_stores_server(self):
        server = Server(FakeProgram())
        sink = EmptySink(server)
        assert sink.server == server

    def test_types(self):
        sink = EmptySink(Server(FakeProgram()))

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
        sink = EmptySink(Server(FakeProgram()))
        sink.add_type(Message.RECEIVED_TELEM)
        sink.remove_type(Message.RECEIVED_TELEM)
        sink.remove_type(Message.RECEIVED_TELEM)
        # Should not produce a KeyError

    def test_rejects_garbage(self):
        sink = EmptySink(Server(FakeProgram()))
        for i in [sink.add_type, sink.remove_type]:
            yield self.check_rejects_garbage_type, i
            yield self.check_rejects_invalid_type, i

        for i in [sink.add_types, sink.remove_types,
                  sink.set_types]:
            yield self.check_rejects_garbage_types, i
            yield self.check_rejects_garbage_set, i
            yield self.check_rejects_invalid_types, i

    @raises(ValueError)
    def check_rejects_garbage_type(self, func):
        func("asdf")

    @raises(ValueError)
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
        sink = FakeSink(Server(FakeProgram()))
        assert sink.types == set([Message.RECEIVED_TELEM,
                                  Message.LISTENER_INFO])
        assert sink.message == sink.test_messages.append

    def test_push_message(self):
        sink = FakeSink(Server(FakeProgram()))

        # Same story as test_types
        yield self.check_push_unwanted_message, sink
        yield self.check_push_requested_message, sink

    def check_push_unwanted_message(self, sink):
        sink.push_message(Message(self.source, Message.TELEM, None))
        assert sink.test_messages == []

    def check_push_requested_message(self, sink):
        message = Message(self.source, Message.RECEIVED_TELEM, 100)
        sink.push_message(message)
        assert sink.test_messages == [message]
        assert sink.test_messages[0].data == 100

    def test_sink_changing_types_push(self):
        yield self.check_sink_changing_types_push, ChangeySimpleSink
        yield self.check_sink_changing_types_push, ChangeyThreadedSink

    def check_sink_changing_types_push(self, sink_class):
        sink = sink_class(Server(FakeProgram()))

        sink.push_message(Message(self.source, Message.LISTENER_INFO, 1))
        sink.push_message(Message(self.source, Message.LISTENER_INFO, 2))
        sink.push_message(Message(self.source, Message.RECEIVED_TELEM, 3))

        # Clean up threaded sinks, do nothing to simple sinks.
        sink.shutdown()

        assert sink.status == 2

    def test_threaded_sink_executes_in_one_thread(self):
        sink = FakeThreadedSink(Server(FakeProgram()))

        a = ThreadedPush(sink, Message(self.source,
            Message.LISTENER_INFO, 1))
        b = ThreadedPush(sink, Message(self.source,
            Message.LISTENER_INFO, 2))
        c = ThreadedPush(sink, Message(self.source,
            Message.RECEIVED_TELEM, 3))

        for t in [a, b, c]:
            t.start()
            t.join()

        sink.shutdown()

        assert sink.failed == 0
        assert sink.status == 3

    def test_flush(self):
        yield self.check_flush_race, SlowSimpleSink
        yield self.check_flush_race, SlowThreadedSink

    def check_flush_race(self, sink_class):
        # Testing a race condition is quite difficult. (TODO ?)
        # SlowSink.message() will time.sleep(0.02)
        sink = sink_class(Server(FakeProgram()))
        message = Message(self.source, Message.TELEM, None)
        t = ThreadedPush(sink, message)

        t.start()

        sink.in_message.wait()
        assert sink.in_message.is_set()
        sink.flush()
        assert not sink.in_message.is_set()

        t.join()

        # Does nothing to simple sinks, cleans up a threaded sink's thread
        sink.shutdown()

    def test_simple_shutdown(self):
        self.check_shutdown(EmptySink(Server(FakeProgram())), False)

    def test_threaded_shutdown(self):
        self.check_shutdown(EmptyThreadedSink(Server(FakeProgram())), True)

    def check_shutdown(self, sink, check_thread):
        # For a SimpleSink, shutdown should just call flush
        # For a ThreadedSink, it should call flush and then kill the thread.

        def new_flush():
            new_flush.call_count += 1
        new_flush.call_count = 0

        sink.flush = new_flush

        if check_thread:
            while not sink.is_alive():
                time.sleep(0.01)

        sink.shutdown()

        if check_thread:
            assert not sink.is_alive()

        assert sink.flush.call_count == 1

    def test_threadname(self):
        sink = EmptyThreadedSink(Server(FakeProgram()))
        assert sink.name.startswith("ThreadedSink runner: EmptyThreadedSink")
        sink.shutdown()
