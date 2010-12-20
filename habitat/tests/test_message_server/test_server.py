# Copyright 2010 (C) Daniel Richman
# Copyright 2010 (C) Adam Greig
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

from nose.tools import raises, with_setup

from habitat.message_server import Sink, SimpleSink, Message, Listener
from habitat.utils.tests.reloadable_module import ReloadableModuleWriter
from habitat.message_server import Server

from locktroll import LockTroll

class FakeSink(SimpleSink):
    def setup(self):
        pass
    def message(self):
        pass

class SinkWithoutSetup(SimpleSink):
    """A sink without a setup method should not be loaded."""
    def message(self):
        pass

class SinkWithoutMessage(SimpleSink):
    """A sink without a message method should not be loaded."""
    def setup(self):
        pass

# This would confuse an earlier version of of the software that would compare
# dynamicloader.fullname with a string "loadable".
from fakesink import *
from pushback import *
from slowsink import SlowShutdownSink

class NonSink:
    """
    Doesn't have a base class of Sink, so shouldn't be loaded
    """
    pass

class TestServer:
    def setup(self):
        self.server = Server(None, None)
        self.source = Listener("M0ZDR", "1.2.3.4")

    def test_message_counter(self):
        message_rt = Message(self.source, Message.RECEIVED_TELEM, None)
        assert self.server.message_count == 0
        self.server.push_message(message_rt)
        assert self.server.message_count == 1
        for i in xrange(10):
            self.server.push_message(message_rt)
        assert self.server.message_count == 11

    def test_repr(self):
        assert self.server.__class__.__name__ == "Server"
        assert self.server.__class__.__module__ == "habitat.message_server"
        expect_format = "<habitat.message_server.Server: %s>"
        info_format = expect_format % "%s sinks loaded, %s messages so far"
        locked_format = expect_format % "locked"

        assert repr(self.server) == info_format % (0, 0)
        troll = LockTroll(self.server.lock)
        troll.start()
        assert repr(self.server) == locked_format
        troll.release()

        message_rt = Message(self.source, Message.RECEIVED_TELEM, None)
        self.server.push_message(message_rt)
        assert repr(self.server) == info_format % (0, 1)

        self.server.load(TestSinkA)
        assert repr(self.server) == info_format % (1, 1)

        self.server.push_message(message_rt)
        self.server.load(TestSinkB)
        self.server.push_message(message_rt)
        self.server.push_message(message_rt)
        assert repr(self.server) == info_format % (2, 4)

        troll = LockTroll(self.server.lock)
        troll.start()
        assert repr(self.server) == locked_format
        troll.release()

    def teardown(self):
        self.server.shutdown()

    def test_can_load_fakesink(self):
        self.server.load(FakeSink)

    def test_can_load_fakesink_by_name(self):
        self.server.load(__name__ + ".FakeSink")

    @raises(ValueError)
    def test_refuses_to_load_nonsink(self):
        """refuses to load a sink that doesn't have Sink as a base class"""
        self.server.load(NonSink)

    @raises(ValueError)
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

    @raises(ValueError)
    def test_refuses_to_load_sink_without_setup_method(self):
        self.server.load(__name__ + ".SinkWithoutSetup")

    @raises(ValueError)
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
        message_li = Message(self.source, Message.LISTENER_INFO, None)
        message_rt = Message(self.source, Message.RECEIVED_TELEM, None)
        self.server.load(TestSinkA)
        self.server.load(TestSinkB)
        self.server.push_message(message_li)
        self.server.push_message(message_rt)
        self.server.push_message(message_li)
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
            Message(self.source, Message.RECEIVED_TELEM, 6293))

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
        rmod = ReloadableModuleWriter(__name__, __file__,
                                      'rsink', 'ReloadableSink')
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
        code = "from fakesink import TestSink\n" + \
               "from habitat.message_server import Message\n" + \
               "class ReloadableSink(TestSink):\n" + \
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
        old_shutdown = self.server.sinks[0].shutdown
        def new_shutdown(*args, **kwargs):
            new_shutdown.hits += 1
            return old_shutdown(*args, **kwargs)
        new_shutdown.hits = 0
        self.server.sinks[0].shutdown = new_shutdown

        unloadfunc()
        assert new_shutdown.hits == 1

    def test_reload_skips_no_messages(self):
        self.server.load(SlowShutdownSink)
        m = Message(self.source, Message.TELEM, None)

        def f():
            self.server.reload(SlowShutdownSink)

        old_object = self.server.sinks[0]

        t = threading.Thread(target=f,
                             name="Test Thread: test_reload_skips_no_messages")
        t.start()

        old_object.shutting_down.wait()
        self.server.push_message(m)
        self.server.push_message(m)
        self.server.push_message(m)

        t.join()
        new_object = self.server.sinks[0]

        assert old_object.messages == 0
        assert new_object.messages == 3

    @raises(TypeError)
    def test_push_message_rejects_non_message(self):
        self.server.load(123)
