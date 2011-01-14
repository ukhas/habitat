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

import time
from nose.tools import raises
from habitat.message_server import Message

from habitat.parser import ParserSink

flight_doc = {
    "start": int(time.time()) - 86400,
    "end": int(time.time()) + 86400,
    "payloads": {
        "habitat": {
            "sentence": {
                "protocol": "Fake",
                "payload": "habitat"
            }
        }
    }
}

class FakeModule(object):
    """An empty mock parser module"""
    def __init__(self, parser):
        self.parser = parser
        self.pre_parse_string = None
        self.string = None
        self.config = None
    def pre_parse(self, string):
        self.pre_parse_string = string
        if string == "test message":
            return "habitat"
        else:
            raise ValueError("No callsign found.")
    def parse(self, string, config):
        self.string = string
        self.config = config
        if string == "test message":
            return {"data": True}
        else:
            raise ValueError("Invalid message string given.")

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

class FakeViewResults(object):
    """
    A mocked up couchdbkit ViewResults that can have first() called on it
    and gives out a dictionary as though it were real.
    """
    def first(self):
        return {"value": None, "id": "1234567890abcdef", "key": ["habitat",
            flight_doc["end"]], "doc": flight_doc}

class FakeDB(object):
    """
    A mocked up CouchDB database which can be queried as normal for
    a document and supports calling views (though it just logs the
    view call).
    """
    def __init__(self):
        self.parser_config = {
            "modules": [
                {
                    "name": "Fake",
                    "class": FakeModule
                }
            ]
        }
        self.view_string = None
        self.view_params = None

    def __getitem__(self, item):
        if item == "parser_config":
            return self.parser_config
        else:
            raise Exception("FakeDB was asked for a non-existant document")

    def view(self, view, **params):
        self.view_string = view
        self.view_params = params
        return FakeViewResults()
        

class FakeServer(object):
    """A mocked up server which has a fake CouchDB"""
    def __init__(self):
        self.db = FakeDB()
        self.message = None
    def push_message(self, message):
        self.message = message

class FakeListener(object):
    def __init__(self):
        self.callsign = "test callsign"
        self.ip = "123.123.123.123"

class FakeMessage(object):
    """A basic fake message"""
    def __init__(self):
        self.source = FakeListener()
        self.type = Message.RECEIVED_TELEM
        self.data = "test message"

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

    def test_calls_view_properly(self):
        self.sink.message(FakeMessage())
        assert self.server.db.view_string == "habitat/payload_config"
        assert self.server.db.view_params["limit"] == 1
        assert self.server.db.view_params["include_docs"] == True
        assert self.server.db.view_params["startkey"][:12] == '["habitat", '
        assert abs(int(self.server.db.view_params["startkey"][12:-1]) -
            int(time.time())) < 2

    def test_calls_parser_with_config(self):
        self.sink.message(FakeMessage())
        assert (self.sink.modules["Fake"].config ==
                flight_doc["payloads"]["habitat"]["sentence"])

    def test_pushes_message(self):
        self.sink.message(FakeMessage())
        assert self.server.message
        assert self.server.message.source.callsign == "test callsign"
        assert self.server.message.source.ip == "123.123.123.123"
        assert self.server.message.type == Message.TELEM
        assert self.server.message.data == {"data": True}
