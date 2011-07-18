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
Tests the Server class
"""

import sys
import time
import threading
import copy

from nose.tools import raises, with_setup

from habitat.message_server import Sink, SimpleSink, Message, Listener
from habitat.utils import crashmat, dynamicloader

from test_habitat.lib import threading_checks
from test_habitat.lib.sample_messages import SMessage
from test_habitat.lib.reloadable_module_writer import ReloadableModuleWriter
from test_habitat.lib.locktroll import LockTroll

from habitat.message_server import Server

# This would confuse an earlier version of of the software that would compare
# dynamicloader.fullname with a string "loadable".
from fakesink import TestSinkA, TestSinkB, TestSinkC, FakeSink2, \
                     SinkWithoutSetup, SinkWithoutMessage
from pushback import PushbackSimpleSink, PushbackThreadedSink, \
                     PushbackReceiverSimpleSink, PushbackReceiverThreadedSink
from slowsink import SlowShutdownSink

class FakeSink(SimpleSink):
    def setup(self):
        pass
    def message(self, message):
        pass

class FakeProgram:
    db = {"message_server_config": {"sinks": []}}
    def __init__(self, sinks=[]):
        self.db = copy.deepcopy(self.db)
        self.db["message_server_config"]["sinks"] = sinks

class NonSink:
    """
    Doesn't have push_message(), so doesn't "look like" a Sink.
    Therefore shouldn't be loaded. Whether it has message or setup
    methods is irrelevant since it is not a subclass of Sink.
    """
    def message():
        pass
    def setup():
        pass

class TestServer:
    def setup(self):
        threading_checks.patch()

        self.server = Server(FakeProgram())
        self.server.start()
        self.source = Listener("M0ZDR", "1.2.3.4")

    def teardown(self):
        if self.server.thread.is_alive():
            self.server.shutdown()

        threading_checks.restore()

    def test_message_counter(self):
        m = SMessage()
        assert self.server.message_count == 0
        self.server.push_message(m)
        self.server.flush()
        assert self.server.message_count == 1
        for i in xrange(10):
            self.server.push_message(m)
        self.server.flush()
        assert self.server.message_count == 11

    def test_repr(self):
        assert self.server.__class__.__name__ == "Server"
        assert self.server.__class__.__module__ == "habitat.message_server"
        expect_format = "<habitat.message_server.Server: %s>"
        info_format = expect_format % ("%s sinks loaded, " +
                                       "%s messages so far, approx %s queued")
        locked_format = expect_format % "locked"

        assert repr(self.server) == info_format % (0, 0, 0)
        troll = LockTroll(self.server.lock)
        troll.start()
        assert repr(self.server) == locked_format
        troll.release()

        m = SMessage()
        self.server.push_message(m)
        self.server.flush()
        assert repr(self.server) == info_format % (0, 1, 0)

        self.server.load(TestSinkA)
        assert repr(self.server) == info_format % (1, 1, 0)

        self.server.push_message(m)
        self.server.flush()
        self.server.load(TestSinkB)
        self.server.push_message(m)
        self.server.push_message(m)
        self.server.flush()
        assert repr(self.server) == info_format % (2, 4, 0)

        troll = LockTroll(self.server.lock)
        troll.start()
        assert repr(self.server) == locked_format
        troll.release()

        self.server.shutdown()
        assert repr(self.server) == info_format % (0, 4, 0)

        self.server.push_message(m)
        self.server.push_message(m)

        assert repr(self.server) == info_format % (0, 4, 2)

    def test_can_load_fakesink(self):
        self.server.load(FakeSink)

    def test_can_load_fakesink_by_name(self):
        self.server.load(__name__ + ".FakeSink")

    @raises(TypeError)
    def test_refuses_to_load_nonsink(self):
        """refuses to load a sink that doesn't have Sink as a base class"""
        self.server.load(NonSink)

    @raises(TypeError)
    def test_refuses_to_load_nonsink_by_name(self):
        """refuses to load a sink that doesn't have Sink as a base class"""
        self.server.load(__name__ + ".NonSink")

    @raises(TypeError)
    def test_refuses_to_load_garbage_type(self):
        self.server.load(1)

    @raises(ValueError)
    def test_refuses_to_load_empty_str(self):
        self.server.load("")

    @raises(TypeError)
    def test_refuses_to_load_module(self):
        self.server.load("test")

    def test_refuses_to_load_str_with_empty_components(self):
        for i in ["asdf.", ".", "asdf..asdf"]:
            yield self.check_refuses_to_load_str_with_empty_components, i

    @raises(ValueError)
    def check_refuses_to_load_str_with_empty_components(self, name):
        self.server.load(name)

    @raises(AttributeError)
    def test_refuses_to_load_nonexistant_sink_class_by_name(self):
        self.server.load(__name__ + ".FakeSink99")

    @raises(ImportError)
    def test_refuses_to_load_nonexistant_module_by_name(self):
        self.server.load(__name__ + "asdf.FakeSink")

    @raises(TypeError)
    def test_refuses_to_load_sink_without_setup_method(self):
        self.server.load(__name__ + ".SinkWithoutSetup")

    @raises(TypeError)
    def test_refuses_to_load_sink_without_message_method(self):
        self.server.load(SinkWithoutMessage)

    @raises(ValueError)
    def test_refuses_to_load_two_of_the_same_sink(self):
        self.server.load(FakeSink)
        self.server.load(FakeSink)

    def test_load_gets_correct_class(self):
        for i in ["FakeSink", "FakeSink2"]:
            yield self.check_load_gets_correct_class, i

    def test_loaded_sink_is_given_server_object(self):
        self.server.load(FakeSink)
        assert self.server.sinks[0].server == self.server

    def check_load_gets_correct_class(self, name):
        real_class = getattr(sys.modules[__name__], name)
        self.server.load(__name__ + "." + name)
        loaded = self.server.sinks[0]
        assert isinstance(loaded, real_class)

    def test_does_not_load_two_of_the_same_sink(self):
        self.server.load(FakeSink)
        try:
            self.server.load(FakeSink)
        except ValueError:
            pass
        assert len(self.server.sinks) == 1

    def test_load_adds_correct_sink(self):
        for i in ["FakeSink", "FakeSink2", FakeSink, FakeSink2]:
            yield self.check_load_adds_correct_sink, i

    def check_load_adds_correct_sink(self, sink):
        if isinstance(sink, basestring):
            self.server.load(__name__ + "." + sink)
            real_class = getattr(sys.modules[__name__], sink)
        else:
            assert issubclass(sink, Sink)
            self.server.load(sink)
            real_class = sink

        assert len(self.server.sinks) == 1
        assert self.server.sinks[0].__class__ == real_class

    def test_failed_load_adds_no_sinks(self):
        for i in [__name__ + ".FakeSink99",
                  __name__ + "asdf.FakeSink",
                  __name__ + ".NonSink",
                  "", 1, NonSink]:
            yield self.check_failed_load_adds_no_sinks, i

    def check_failed_load_adds_no_sinks(self, sink):
        try:
            self.server.load(sink)
        except:
            # Other tests check that the correct error is produced
            pass

        assert len(self.server.sinks) == 0

    def test_pushes_to_sinks(self):
        message_li = SMessage(type=Message.LISTENER_INFO)
        message_rt = SMessage(type=Message.RECEIVED_TELEM)
        self.server.load(TestSinkA)
        self.server.load(TestSinkB)
        self.server.push_message(message_li)
        self.server.push_message(message_rt)
        self.server.push_message(message_li)
        self.server.flush()
        assert isinstance(self.server.sinks[0], TestSinkA)
        assert isinstance(self.server.sinks[1], TestSinkB)
        self.server.sinks[0].flush()
        self.server.sinks[1].flush()
        assert self.server.sinks[0].test_messages == [message_li, message_rt,
                                                      message_li]
        assert self.server.sinks[1].test_messages == [message_li, message_li]

    def test_pushback(self):
        yield self.check_pushback, PushbackSimpleSink, \
                                   PushbackReceiverSimpleSink
        yield self.check_pushback, PushbackThreadedSink, \
                                   PushbackReceiverThreadedSink

    def check_pushback(self, pushback_class, pushbackreceiver_class):
        self.server.load(pushback_class)
        self.server.load(pushbackreceiver_class)
        self.server.push_message(
            SMessage(type=Message.RECEIVED_TELEM, testid=6293))

        # Flush twice
        for r in xrange(0, 2):
            self.server.flush()

            for i in self.server.sinks:
                i.flush()

        # Now check the results
        for i in self.server.sinks:
            assert i.status == 2

    def test_unload(self):
        self.server.load(TestSinkA)
        self.server.load(TestSinkB)
        assert len(self.server.sinks) == 2
        assert isinstance(self.server.sinks[0], TestSinkA)
        assert isinstance(self.server.sinks[1], TestSinkB)

        self.server.unload(TestSinkA)
        assert len(self.server.sinks) == 1
        assert isinstance(self.server.sinks[0], TestSinkB)

        self.server.load(TestSinkA)
        assert len(self.server.sinks) == 2
        assert isinstance(self.server.sinks[1], TestSinkA)

        self.server.unload(__name__ + ".TestSinkA")
        assert len(self.server.sinks) == 1
        assert isinstance(self.server.sinks[0], TestSinkB)

    def test_reload(self):
        rmod = ReloadableModuleWriter('rsink', 'ReloadableSink')
        assert not rmod.is_loaded()

        # dynamicloader.reload's functionality is tested quite thoroughly in
        # utils/tests

        (code, values) = self.generate_rmod_code("RECEIVED_TELEM",
                                                 "LISTENER_TELEM")
        rmod.write_code(code)
        self.server.load(rmod.loadable)
        assert self.server.sinks[0].types == values

        (code, values) = self.generate_rmod_code("LISTENER_TELEM")
        rmod.write_code(code)
        self.server.reload(rmod.loadable)
        assert len(self.server.sinks) == 1
        assert self.server.sinks[0].types == values

    def generate_rmod_code(self, *types):
        values = set([getattr(Message, i) for i in types])
        values_string = ", ".join(["Message.%s" % t for t in types])
        code = "from test_habitat.test_message_server import fakesink\n" + \
               "from habitat.message_server import Message\n" + \
               "class ReloadableSink(fakesink.TestSink):\n" + \
               "    testtypes = [%s]\n"
        return (code % values_string, values)

    def test_unload_shuts_down_sink(self):
        def f():
            self.server.unload(FakeSink)
        self.check_shuts_down_sink(f)

    def test_shutdown_shuts_down_sink(self):
        def f():
            self.server.shutdown()
        self.check_shuts_down_sink(f)

    def test_reload_shuts_down_sink(self):
        def f():
            self.server.reload(FakeSink)
        self.check_shuts_down_sink(f)

    def check_shuts_down_sink(self, unloadfunc):
        self.server.load(FakeSink)

        # Wrap sink shutdown
        def new_shutdown(*args, **kwargs):
            new_shutdown.hits += 1
            return new_shutdown.old(*args, **kwargs)
        new_shutdown.old = self.server.sinks[0].shutdown
        new_shutdown.hits = 0
        self.server.sinks[0].shutdown = new_shutdown

        unloadfunc()
        assert new_shutdown.hits == 1

    def test_reload_skips_no_messages(self):
        self.server.load(SlowShutdownSink)
        m = SMessage(type=Message.TELEM)

        def f():
            self.server.reload(SlowShutdownSink)

        old_object = self.server.sinks[0]

        t = crashmat.Thread(target=f,
                            name="Test Thread: test_reload_skips_no_messages")
        t.start()

        old_object.shutting_down.wait()
        self.server.push_message(m)
        self.server.push_message(m)
        self.server.push_message(m)

        t.join()
        new_object = self.server.sinks[0]

        self.server.flush()

        assert old_object.messages == 0
        assert new_object.messages == 3

    @raises(TypeError)
    def test_push_message_rejects_non_message(self):
        self.server.push_message(123)

    def test_shutdown_shuts_down_thread_and_flushes_queue(self):
        assert self.server.thread.is_alive()
        self.check_function_clears_queue(self.server.shutdown)
        assert not self.server.thread.is_alive()

    def test_flush_clears_queue(self):
        self.check_function_clears_queue(self.server.flush)

    def check_function_clears_queue(self, f):
        with self.server.lock:
            m = SMessage()
            self.server.push_message(m)
            self.server.push_message(m)
            self.server.push_message(m)
            assert self.server.queue.qsize() > 1

        f()

        assert self.server.queue.qsize() == 0

    def test_push_message_is_instant(self):
        lt = LockTroll(self.server.lock)
        lt.start()
        # If it wasn't instant/Queue, this would deadlock
        m = SMessage()
        self.server.push_message(m)
        self.server.push_message(m)
        self.server.push_message(m)
        lt.release()

class TestServerStartup:
    def setup(self):
        threading_checks.patch()

    def teardown(self):
        threading_checks.restore()

    def test_uses_config(self):
        tserver = Server(FakeProgram([FakeSink]))
        tserver.start()
        assert len(tserver.sinks) == 1
        tserver.shutdown()

    def test_init_starts_no_threads(self):
        tserver = Server(FakeProgram([dynamicloader.fullname(TestSinkC)]))
        threading_checks.check_threads(created=1, live=0)
        tserver.start()
        threading_checks.check_threads(live=2)
        tserver.shutdown()
