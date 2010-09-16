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

class TestParserSink:
    def setup(self):
        self.server = Server()

    def test_sink_can_be_loaded(self):
        self.server.load(ParserSink)

    def test_sink_has_RECEIVED_TELEM_type(self):
        """sink has RECEIVED_TELEM type"""
        sink = ParserSink()
        assert sink.types == set([Message.RECEIVED_TELEM])

