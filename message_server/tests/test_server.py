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
Tests the Server class, found in ../server.py
""" 

from nose.tools import raises, with_setup
from message_server import Sink, Server

class FakeSink(Sink):
    def start(self):
        pass
    def message(self):
        pass

class FakeSink2(Sink):
    def start(self):
        pass
    def message(self):
        pass

class NonSink:
    """
    Doesn't have a base class of Sink, so shouldn't be loaded
    """
    pass

class TestServerSinkLoader:
    def setup(self):
        self.server = Server()

    def test_can_load_fakesink(self):
        self.server.load(FakeSink)

    def test_can_load_fakesink_by_name(self):
        self.server.load("message_server.tests.test_server.FakeSink")

    @raises(ValueError)
    def test_refuses_to_load_nonsink(self):
        """refuses to load a sink that doesn't have Sink as a base class"""
        self.server.load(NonSink)

    @raises(ValueError)
    def test_refuses_to_load_nonsink_by_name(self):
        """refuses to load a sink that doesn't have Sink as a base class"""
        self.server.load("message_server.tests.test_server.NonSink")

    @raises(TypeError)
    def test_refuses_to_load_garbage_type(self):
        self.server.load(1)

    @raises(ValueError)
    def test_refuses_to_load_empty_str(self):
        self.server.load("")

    @raises(ValueError)
    def test_refuses_to_str_without_enough_components(self):
        self.server.load("test")

    def test_refuses_to_str_with_empty_components(self):
        for i in ["asdf.", ".", "asdf..asdf"]:
            yield self.check_refuses_to_str_with_empty_components, i

    @raises(ValueError)
    def check_refuses_to_str_with_empty_components(self, name):
        self.server.load(name)

    @raises(AttributeError)
    def test_refuses_to_load_nonexistant_sink_class_by_name(self):
        self.server.load("message_server.tests.test_server.FakeSink99")

    @raises(ImportError)
    def test_refuses_to_load_nonexistant_module_by_name(self):
        self.server.load("message_server.tests.test_server99.FakeSink")

    def test_load_by_name_gets_correct_class(self):
        for i in ["FakeSink", "FakeSink2"]:
            yield self.check_load_by_name_gets_correct_class, i

    def check_load_by_name_gets_correct_class(self, name):
        real_class = globals()[name]
        loaded_class = self.server.load_by_name(
          "message_server.tests.test_server.%s" % name)
        assert real_class == loaded_class

    def clean_server_sinks(self):
        self.server.sinks = []

    def test_load_adds_correct_sink(self):
        for i in ["FakeSink", "FakeSink2", FakeSink, FakeSink2]:
            yield self.check_load_adds_correct_sink, i

    @with_setup(clean_server_sinks)
    def check_load_adds_correct_sink(self, sink):
        if isinstance(sink, basestring):
            self.server.load("message_server.tests.test_server.%s" % sink)
            real_class = globals()[sink]
        else:
            assert issubclass(sink, Sink)
            self.server.load(sink)
            real_class = sink

        assert len(self.server.sinks) == 1
        assert self.server.sinks[0].__class__ == real_class

    def test_failed_load_adds_no_sinks(self):
        for i in ["message_server.tests.test_server.FakeSink99",
                  "message_server.tests.test_server99.FakeSink",
                  "message_server.tests.test_server.NonSink",
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
