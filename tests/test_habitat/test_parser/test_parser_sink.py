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
from copy import deepcopy
from nose.tools import raises
from test_habitat.lib import fake_couchdb
from habitat.message_server import Message

from habitat.parser import ParserSink

def upper_case_filter(data):
    return data.upper()
def config_filter(data, config):
    return {"result": "config was like " + str(config)}

flight_doc = {
    "_id": "1234567890",
    "start": int(time.time()) - 86400,
    "end": int(time.time()) + 86400,
    "payloads": {
        "habitat": {
            "sentence": {
                "protocol": "Fake",
                "from_flight_doc": True
            }
        }
    }
}

intermediate_filters_doc = deepcopy(flight_doc)
intermediate_filters_doc["payloads"]["habitat"]["filters"] = {
    "intermediate": [
        {
            "type": "hotfix",
            "code": "return 'hotfix'",
            "signature": "cbe83e892c1fd80954dc44bf94abeb9fa3a99e66ab1f" + \
                         "f07eb5d225e8b60b782bab8b1581abdced33e01de2ec" + \
                         "9e8e11dd3d1f8347a3fb29be9152d42030ecdcf4"
        }
    ]
}

post_filters_doc = deepcopy(flight_doc)
post_filters_doc["payloads"]["habitat"]["filters"] = {
    "post": [
        {
            "type": "normal",
            "callable": config_filter,
            "config": "rad!"
        }
    ]
}

wrong_flight_doc = {
    "_id": "abcdef",
    "start": int(time.time()) - 86400,
    "end": int(time.time()) + 86400,
    "payloads": {
        "wrong": {
            "sentence": {
                "protocol": "Fake",
                "from_flight_doc": True
            }
        }
    }
}

wrong_p_flight_doc = {
    "_id": "fedbca",
    "start": int(time.time()) - 86400,
    "end": int(time.time()) + 86400,
    "payloads": {
        "habitat": {
            "sentence": {
                "protocol": "wrong",
                "from_flight_doc": True
            }
        }
    }
}

default_config = {
    "sentence": {
        "protocol": "Fake",
        "default": True
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

fake_view_results = fake_couchdb.ViewResults({"value": None,
    "key": ["habitat", flight_doc["end"]], "doc": flight_doc})

intermediate_filter_view_results = fake_couchdb.ViewResults({"value": None,
    "key": ["habitat", intermediate_filters_doc["end"]],
    "doc": intermediate_filters_doc})

post_filter_view_results = fake_couchdb.ViewResults({"value": None,
    "key": ["habitat", post_filters_doc["end"]], "doc": post_filters_doc})

empty_view_results = fake_couchdb.ViewResults()

wrong_view_results = fake_couchdb.ViewResults({"value": None,
    "key": ["wrong", wrong_flight_doc["end"]], "doc": wrong_flight_doc})

wrong_protocol_view_results = fake_couchdb.ViewResults({"value": None,
    "key": ["habitat", wrong_p_flight_doc["end"]], "doc": wrong_p_flight_doc})

class FakeProgram(object):
    """A mocked up Program object with fake options"""
    def __init__(self):
        self.options = {'secret': 'secret'}

class FakeServer(object):
    """A mocked up server which has a fake CouchDB"""
    def __init__(self, docs=None):
        self.program = FakeProgram()
        self.db = fake_couchdb.Database(docs)
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
        self.time_created = 1234
        self.time_uploaded = 5768
        self.data = { "string": "dGVzdCBtZXNzYWdl", "metametadata": "asdf" }

class WrongMessage(object):
    """A fake message that won't result in a valid callsign"""
    def __init__(self):
        self.source = FakeListener()
        self.type = Message.RECEIVED_TELEM
        self.time_created = 0
        self.time_uploaded = 0
        self.data = { "string": "d3Jvbmc=", "ignorethis": 1234 }

class TestParserSink(object):
    def setup(self):
        docs = {
            "parser_config": {
                "modules": [
                    {
                        "name": "Fake",
                        "class": FakeModule
                    }
                ]
            }
        }
        self.server = FakeServer(docs)
        self.server.db.default_view_results = fake_view_results
        self.sink = ParserSink(self.server)

    def test_sets_data_types(self):
        assert self.sink.types == set([Message.RECEIVED_TELEM])

    def test_loads_modules_in_config(self):
        assert len(self.sink.modules) == 1
        assert isinstance(self.sink.modules[0]["module"], FakeModule)

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
        assert self.server.db.view_params["startkey"][0] == "habitat"
        assert self.server.db.view_params["startkey"][1] == 1234

    def test_calls_parser_with_config(self):
        self.sink.message(FakeMessage())
        assert (self.sink.modules[0]["module"].config ==
                flight_doc["payloads"]["habitat"]["sentence"])

    def test_uses_default_config_with_empty_results(self):
        self.server.db.default_view_results = empty_view_results
        self.server.db["parser_config"]["modules"][0]["default_config"] = \
            default_config
        sink = ParserSink(self.server)
        sink.message(FakeMessage())
        assert sink.modules[0]["module"].config == default_config["sentence"]

    def test_uses_default_config_with_wrong_results(self):
        self.server.db.default_view_results = wrong_view_results
        self.server.db["parser_config"]["modules"][0]["default_config"] = \
            default_config
        sink = ParserSink(self.server)
        sink.message(FakeMessage())
        assert sink.modules[0]["module"].config == default_config["sentence"]

    def test_doesnt_parse_when_no_config_or_default_config_found(self):
        self.server.db.default_view_results = empty_view_results
        sink = ParserSink(self.server)
        sink.message(FakeMessage())
        assert self.server.message == None

    def test_doesnt_parse_when_wrong_config_and_no_default_config_found(self):
        self.server.db.default_view_results = wrong_view_results
        sink = ParserSink(self.server)
        sink.message(FakeMessage())
        assert self.server.message == None

    def test_doesnt_parse_when_config_has_wrong_protocol(self):
        self.server.db.default_view_results = wrong_protocol_view_results
        sink = ParserSink(self.server)
        sink.message(FakeMessage())
        assert self.server.message == None

    def test_doesnt_parse_when_no_callsign_found(self):
        self.sink.message(WrongMessage())
        assert self.server.message == None

    def test_applies_pre_parse_filter(self):
        self.server.db["parser_config"]["modules"][0]["pre-filters"] = [
            {"type": "normal", "callable": upper_case_filter}
        ]
        sink = ParserSink(self.server)
        sink.message(FakeMessage())
        assert sink.modules[0]["module"].pre_parse_string == "TEST MESSAGE"

    def test_applies_intermediate_filter(self):
        self.server.db.default_view_results = intermediate_filter_view_results
        sink = ParserSink(self.server)
        sink.message(FakeMessage())
        assert sink.modules[0]["module"].string == "hotfix"

    def test_doesnt_apply_hotfix_without_signature(self):
        no_signature = deepcopy(intermediate_filters_doc)
        del no_signature["payloads"]["habitat"]["filters"] \
            ["intermediate"][0]["signature"]
        no_signature_view_results = fake_couchdb.ViewResults({"value": None,
            "key": ["habitat", no_signature["end"]],
            "doc": no_signature})
        self.server.db.default_view_results = no_signature_view_results
        sink = ParserSink(self.server)
        sink.message(FakeMessage())
        assert sink.modules[0]["module"].string == "test message"

    def test_doesnt_apply_hotfix_with_invalid_signature(self):
        bad_signature = deepcopy(intermediate_filters_doc)
        bad_signature["payloads"]["habitat"]["filters"] \
            ["intermediate"][0]["signature"] = "bad"
        bad_signature_view_results = fake_couchdb.ViewResults({"value": None,
            "key": ["habitat", bad_signature["end"]],
            "doc": bad_signature})
        self.server.db.default_view_results = bad_signature_view_results
        sink = ParserSink(self.server)
        sink.message(FakeMessage())
        assert sink.modules[0]["module"].string == "test message"

    def test_applies_post_filter(self):
        self.server.db.default_view_results = post_filter_view_results
        sink = ParserSink(self.server)
        sink.message(FakeMessage())
        assert self.server.message.data["result"] == "config was like rad!"

    def test_pushes_message(self):
        self.sink.message(FakeMessage())
        assert self.server.message
        assert self.server.message.source.callsign == "test callsign"
        assert self.server.message.source.ip == "123.123.123.123"
        assert self.server.message.time_created == 1234
        assert self.server.message.time_uploaded == 5768
        assert self.server.message.type == Message.TELEM
        assert self.server.message.data == {"data": True,
            "_protocol": "Fake", "_raw": "dGVzdCBtZXNzYWdl",
            "_flight": "1234567890",
            '_listener_metadata': {'metametadata': 'asdf'}}
