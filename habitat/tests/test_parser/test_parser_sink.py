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
from habitat.parser import ParserSink
import habitat.parser

class FakeModule(object):
    """An empty mock parser module"""
    def __init__(self, parser):
        pass
    def pre_parse(self, string):
        pass
    def parse(self, string, config):
        pass

class EmptyModule(object):
    """A mock parser module without any required methods"""
    pass

class BadInitModule(object):
    """A mock parser module whose init signature is wrong"""
    def __init__(self):
        pass
    def pre_parse(self, string):
        pass
    def parse(self, string, config):
        pass

class BadPreParseModule(object):
    """A mock parser module with an incorrect pre_parse signature"""
    def __init__(self, parser):
        pass
    def pre_parse(self):
        pass
    def parse(self, string, config):
        pass

class BadParseModule(object):
    """A mock parser module with an incorrect parse signature"""
    def __init__(self, parser):
        pass
    def pre_parse(self, string):
        pass
    def parse(self):
        pass

class NoInitModule(object):
    """A mock parser module which lacks an __init__ method"""
    def pre_parse(self, string):
        pass
    def parse(self, string, config):
        pass

class NoPreParseModule(object):
    """A mock parser module with no pre_parse method"""
    def __init__(self, parser):
        pass
    def parse(self, string, config):
        pass

class NoParseModule(object):
    """A mock parser module with no parse method"""
    def __init__(self, parser):
        pass
    def pre_parse(self, string):
        pass

class FakeServer(object):
    """A mocked up server which has a configuration document"""
    def __init__(self):
        self.db = {}
        self.db["parser_config"] = {
            "modules": [
                {
                    "name": "Fake",
                    "class": FakeModule
                }
            ]
        }
    def push_message(self, message):
        pass

class TestParserSink(object):
    def setup(self):
        self.server = FakeServer()
        self.sink = ParserSink(self.server)
    
    def test_sets_data_types(self):
        assert self.sink.types == set([Message.RECEIVED_TELEM])

    def test_loads_modules_in_config(self):
        assert len(self.sink.modules) == 1
        assert isinstance(self.sink.modules["Fake"], FakeModule)

    def try_to_load_module(self, module):
        self.server.db["parser_config"]["modules"][0]["class"] = module
        ParserSink(self.server)

    @raises(TypeError)
    def test_doesnt_load_modules_with_no_required_methods(self):
        self.try_to_load_module(EmptyModule)

    @raises(TypeError)
    def test_doesnt_load_module_with_no_init(self):
        self.try_to_load_module(NoInitModule)

    @raises(TypeError)
    def test_doesnt_load_modules_with_wrong_init(self):
        self.try_to_load_module(BadInitModule)

    @raises(TypeError)
    def test_doesnt_load_module_with_no_pre_parse(self):
        self.try_to_load_module(NoPreParseModule)

    @raises(TypeError)
    def test_doesnt_load_modules_with_wrong_pre_parse(self):
        self.try_to_load_module(BadPreParseModule)

    @raises(TypeError)
    def test_doesnt_load_module_with_no_parse(self):
        self.try_to_load_module(NoParseModule)

    @raises(TypeError)
    def test_doesnt_load_modules_with_wrong_parse(self):
        self.try_to_load_module(BadParseModule)
