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
Tests the Server class, found in ../server.py
""" 

import sys
from nose.tools import raises, with_setup
from message_server import Sink, SimpleSink, Server, Message, Listener

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

# This should confuse dynamicloader.fullname. Muahaha
from fakesink import *

class NonSink:
    """
    Doesn't have a base class of Sink, so shouldn't be loaded
    """
    pass

class TestServer:
    def setup(self):
        self.server = Server()

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

    def clean_server_sinks(self):
        self.server.sinks = []

    @with_setup(clean_server_sinks)
    def check_load_gets_correct_class(self, name):
        real_class = getattr(sys.modules[__name__], name)
        self.server.load(__name__ + "." + name)
        loaded = self.server.sinks[0]
        assert isinstance(loaded, real_class)

    @with_setup(clean_server_sinks)
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

    @with_setup(clean_server_sinks)
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

    @with_setup(clean_server_sinks)
    def check_failed_load_adds_no_sinks(self, sink):
        try:
            self.server.load(sink)
        except:
            # Other tests check that the correct error is produced
            pass

        assert len(self.server.sinks) == 0

    @with_setup(clean_server_sinks)
    def test_pushes_to_sinks(self):
        message_li = Message(Listener(0), Message.LISTENER_INFO, None)
        message_rt = Message(Listener(0), Message.RECEIVED_TELEM, None)
        self.server.load(TestSinkA)
        self.server.load(TestSinkB)
        self.server.push_message(message_li)
        self.server.push_message(message_rt)
        self.server.push_message(message_li)
        assert isinstance(self.server.sinks[0], TestSinkA)
        assert isinstance(self.server.sinks[1], TestSinkB)
        assert self.server.sinks[0].test_messages == [message_li, message_rt,
                                                      message_li]
        assert self.server.sinks[1].test_messages == [message_li, message_li]

    @with_setup(clean_server_sinks)
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
