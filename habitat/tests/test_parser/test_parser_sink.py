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
Unit tests for the Parser's Sink class.
"""

from nose.tools import raises
from habitat.message_server import Server, Message
from habitat.parser import ParserSink, ParserModule

class FilterClass:
    def __call__(self, message):
        pass
class BadFilterClass:
    def __call__(self):
        pass
class WorseFilterClass:
    pass
def FilterFunc(msg):
    pass
def BadFilterFunc():
    pass
class Module(ParserModule):
    pass
class Module2(ParserModule):
    pass

class TestParserSink:
    def setUp(self):
        self.sink = ParserSink(Server(None, None))

    def test_parser_has_RECEIVED_TELEM_type(self):
        """sink has RECEIVED_TELEM type"""
        assert self.sink.types == set([Message.RECEIVED_TELEM])

    def test_empty_parser_has_no_filters(self):
        assert len(self.sink.before_filters) == 0
        assert len(self.sink.during_filters) == 0
        assert len(self.sink.after_filters) == 0

    def test_parser_does_not_load_filters_with_too_many_args(self):
        for filter in [BadFilterFunc, BadFilterClass, WorseFilterClass]:
            for location in ParserSink.locations:
                yield self.check_fails_to_load_filter, location, filter

    def test_parser_does_not_load_filters_with_invalid_locations(self):
        invalid_location = ParserSink.locations[-1] + 1
        yield self.check_fails_to_load_filter, invalid_location, FilterFunc

    def test_parser_loads_filters(self):
        for filter in [FilterFunc, FilterClass]:
            for location in ParserSink.locations:
                yield self.check_loads_filter, location, filter

    def test_parser_removes_filters(self):
        for location in ParserSink.locations:
            yield self.check_removes_filter, location

    def test_parser_does_not_load_non_modules(self):
        yield self.check_fails_to_load_module, FilterClass

    def test_parser_loads_modules(self):
        yield self.check_loads_module, Module

    def test_parser_removes_modules(self):
        yield self.check_removes_module, Module

    def test_parser_reloads_module(self):
        class mod(ParserModule):
            pass

        self.check_loads_module(mod)

        class mod(ParserModule):
            pass

        assert self.sink.modules[0] != mod
        self.sink.reload_module(mod)
        assert self.sink.modules[0] == mod

    def check_loads_filter(self, location, filter):
        self.sink.add_filter(location, filter)
        assert len(self.sink.filters[location]) == 1
        assert self.sink.filters[location][0] == filter

    @raises(TypeError, ValueError)
    def check_fails_to_load_filter(self, location, filter):
        self.sink.add_filter(location, filter)

    def check_removes_filter(self, location):
        self.check_loads_filter(location, FilterFunc)
        self.sink.remove_filter(location, FilterFunc)
        assert len(self.sink.filters[location]) == 0

    def check_loads_module(self, module):
        self.sink.add_module(module)
        assert len(self.sink.modules) == 1
        assert self.sink.modules[0] == module

    @raises(TypeError, ValueError)
    def check_fails_to_load_module(self, module):
        self.sink.add_module(module)

    def check_removes_module(self, module):
        self.check_loads_module(module)
        self.sink.remove_module(module)
        assert len(self.sink.modules) == 0

