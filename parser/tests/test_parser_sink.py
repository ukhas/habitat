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
from message_server import Server, Message
from parser import ParserSink

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

class TestParserSink:
    def setUp(self):
        self.sink = ParserSink()

    def test_parser_has_RECEIVED_TELEM_type(self):
        """sink has RECEIVED_TELEM type"""
        assert self.sink.types == set([Message.RECEIVED_TELEM])
    
    def test_parser_does_not_load_filters_with_too_many_args(self):
        for filter in [BadFilterFunc, BadFilterClass, WorseFilterClass]:
            for location in ParserSink.types:
                yield self.check_fails_to_load_filter, location, filter

    @raises(TypeError, ValueError)
    def check_fails_to_load_filter(self, location, filter):
        self.sink.add_filter(location, filter)
    
    def test_parser_loads_filters(self):
        for filter in [FilterFunc, FilterClass]:
            for location in ParserSink.types:
                yield self.check_loads_filter, location, filter

    def check_loads_filter(self, location, filter):
        self.sink.add_filter(location, filter)

