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

import os
import time
import mox
from copy import deepcopy
from nose.tools import assert_raises
from nose.plugins.skip import SkipTest
from ... import parser

base_dir = os.path.split(os.path.abspath(__file__))[0]
test_certs_dir = os.path.join(base_dir, "certs")
del base_dir

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
            "code": "return \"hotfix\"",
            "certificate": "adamgreig.crt",
            "signature": "e0IAPkfi0hSJ2PI/OfqUQvSMyXRKzxnpRLqrPy6h8xgru4V4PBuMOa7fMe7wgzQWZGN6DGG6z277fzKILM+Q8YKJcoxneEIDmzKvaL6bb76vhIIDJOsG5MEg6wBefPmSwIVzS1YP7Ao9/gtWIkA3ypw5/2Iy+GtVoFRkU9iZnYEf+A0vtmLFT1brF/DXsBE67EEYzt3ulbmwRpthDlQtcMgpy760upbS0u1ATNW4EdT4gyVQ4sO8HG8vDjL2MwChRuFWXEf8k9dVwlIYRZ5ygirgIfKCifb8sEfcUZqVnD4MJyZekGpknxyfC725DIZMRy+6qXuyY5Jd+WKRiaQqqsN1Ay9HdTzEeRXku0vl+BCk4PEhDwhIwiaUesLGW2hJuKXW4IG8+i2FWH1Lp+3dboaIqDO4dnA4xj90CyeUS9Tuaj05oAOY/mwNAWfdGuvCs2Q4q+SacGoZbh3u5dd0orU4OFiO7qkHjfHKXSnK0LSNDKhsPgS1j0pL3/u+V+gS2JHkmQe4GzN2S8IVednVxPjX+IzLGlGXE8h2fBcb2KqQZZPqju+dfIELmEnCoHzQdsDNW4xNPfXbcAbYdCXXmZ9ItrMLYKe/lNs6Ktkm2goNiuSD2I8b77OjUDY1eBitbgUyaOVMMdQjy8Xsm5+ncJGx5KLfARYY/+GrMd3JfUY="
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


#fake_view_results = fake_couchdb.ViewResults({"value": None,
    #"key": ["habitat", flight_doc["end"]], "doc": flight_doc})

#intermediate_filter_view_results = fake_couchdb.ViewResults({"value": None,
    #"key": ["habitat", intermediate_filters_doc["end"]],
    #"doc": intermediate_filters_doc})

#post_filter_view_results = fake_couchdb.ViewResults({"value": None,
    #"key": ["habitat", post_filters_doc["end"]], "doc": post_filters_doc})

#empty_view_results = fake_couchdb.ViewResults()

#wrong_view_results = fake_couchdb.ViewResults({"value": None,
    #"key": ["wrong", wrong_flight_doc["end"]], "doc": wrong_flight_doc})

#wrong_protocol_view_results = fake_couchdb.ViewResults({"value": None,
    #"key": ["habitat", wrong_p_flight_doc["end"]], "doc": wrong_p_flight_doc})

class FakeMessage(object):
    """A basic fake message"""
    def __init__(self):
        self.time_created = 1234
        self.time_uploaded = 5768
        self.data = { "string": "dGVzdCBtZXNzYWdl", "metametadata": "asdf" }

class WrongMessage(object):
    """A fake message that won't result in a valid callsign"""
    def __init__(self):
        self.time_created = 0
        self.time_uploaded = 0
        self.data = { "string": "d3Jvbmc=", "ignorethis": 1234 }

class TestParser(object):
    def setup(self):
        self.parser_config = {"modules": [
            {"name": "Fake", "class": FakeModule}],
            "sensors": [], "certs_dir": "habitat/tests/test_parser/certs",
            "couch_uri": "http://localhost:5984", "couch_db": "test"}
        self.parser = parser.Parser(self.parser_config)

    def test_doesnt_mess_up_config_modules(self):
        # once upon a time parser didn't deepcopy config, so config['modules']
        # would get all messed up
        assert 'module' not in self.parser_config['modules'][0]

    def test_loads_modules_in_config(self):
        assert len(self.parser.modules) == 1
        assert isinstance(self.parser.modules[0]["module"], FakeModule)

    def test_doesnt_load_bad_modules(self):
        def try_to_load_module(self, module):
            print self.parser_config
            new_config = deepcopy(self.parser_config) 
            new_config["modules"][0]["class"] = module
            parser.Parser(new_config)

        class EmptyModule(object):
            """A mock parser module without any required methods"""
            pass
        assert_raises(TypeError, try_to_load_module, EmptyModule)

        class NoInitModule(object):
            """A mock parser module which lacks an __init__ method"""
            def pre_parse(self, string):
                pass
            def parse(self, string, config):
                pass
        assert_raises(TypeError, try_to_load_module, NoInitModule)

        class BadInitModule(object):
            """A mock parser module whose init signature is wrong"""
            def __init__(self):
                pass
            def pre_parse(self, string):
                pass
            def parse(self, string, config):
                pass
        assert_raises(TypeError, try_to_load_module, BadInitModule)

        class NoPreParseModule(object):
            """A mock parser module with no pre_parse method"""
            def __init__(self, parser):
                pass
            def parse(self, string, config):
                pass
        assert_raises(TypeError, try_to_load_module, NoPreParseModule)

        class BadPreParseModule(object):
            """A mock parser module with an incorrect pre_parse signature"""
            def __init__(self, parser):
                pass
            def pre_parse(self):
                pass
            def parse(self, string, config):
                pass

        assert_raises(TypeError, try_to_load_module, BadPreParseModule)

        class NoParseModule(object):
            """A mock parser module with no parse method"""
            def __init__(self, parser):
                pass
            def pre_parse(self, string):
                pass
        assert_raises(TypeError, try_to_load_module, NoParseModule)

        class BadParseModule(object):
            """A mock parser module with an incorrect parse signature"""
            def __init__(self, parser):
                pass
            def pre_parse(self, string):
                pass
            def parse(self):
                pass
        assert_raises(TypeError, try_to_load_module, BadParseModule)

    def test_loads_CAs(self):
        assert len(self.parser.certificate_authorities) == 1
        cert = self.parser.certificate_authorities[0]
        assert cert.get_serial_number() == 9315532607032814920L

    def test_doesnt_load_non_CA_cert(self):
        config = deepcopy(self.parser_config)
        config['certs_dir'] = 'habitat/tests/test_parser/non_ca_certs'
        assert_raises(ValueError, parser.Parser, config)

    def test_calls_view_properly(self):
        raise SkipTest
        self.sink.message(FakeMessage())
        assert self.server.db.view_string == "habitat/payload_config"
        assert self.server.db.view_params["limit"] == 1
        assert self.server.db.view_params["include_docs"] == True
        assert self.server.db.view_params["startkey"][0] == "habitat"
        assert self.server.db.view_params["startkey"][1] == 1234

    def test_calls_parser_with_config(self):
        raise SkipTest
        self.sink.message(FakeMessage())
        assert (self.sink.modules[0]["module"].config ==
                flight_doc["payloads"]["habitat"]["sentence"])

    def test_uses_default_config_with_empty_results(self):
        raise SkipTest
        self.server.db.default_view_results = empty_view_results
        self.server.db["parser_config"]["modules"][0]["default_config"] = \
            default_config
        sink = Parser(self.server)
        sink.message(FakeMessage())
        assert sink.modules[0]["module"].config == default_config["sentence"]

    def test_uses_default_config_with_wrong_results(self):
        raise SkipTest
        self.server.db.default_view_results = wrong_view_results
        self.server.db["parser_config"]["modules"][0]["default_config"] = \
            default_config
        sink = Parser(self.server)
        sink.message(FakeMessage())
        assert sink.modules[0]["module"].config == default_config["sentence"]

    def test_doesnt_parse_when_no_config_or_default_config_found(self):
        raise SkipTest
        self.server.db.default_view_results = empty_view_results
        sink = Parser(self.server)
        sink.message(FakeMessage())
        assert self.server.message == None

    def test_doesnt_parse_when_wrong_config_and_no_default_config_found(self):
        raise SkipTest
        self.server.db.default_view_results = wrong_view_results
        sink = Parser(self.server)
        sink.message(FakeMessage())
        assert self.server.message == None

    def test_doesnt_parse_when_config_has_wrong_protocol(self):
        raise SkipTest
        self.server.db.default_view_results = wrong_protocol_view_results
        sink = Parser(self.server)
        sink.message(FakeMessage())
        assert self.server.message == None

    def test_doesnt_parse_when_no_callsign_found(self):
        raise SkipTest
        self.sink.message(WrongMessage())
        assert self.server.message == None

    def test_applies_pre_parse_filter(self):
        raise SkipTest
        self.server.db["parser_config"]["modules"][0]["pre-filters"] = [
            {"type": "normal", "callable": upper_case_filter}
        ]
        sink = Parser(self.server)
        sink.message(FakeMessage())
        assert sink.modules[0]["module"].pre_parse_string == "TEST MESSAGE"

    def test_applies_intermediate_filter(self):
        raise SkipTest
        self.server.db.default_view_results = intermediate_filter_view_results
        sink = Parser(self.server)
        sink.message(FakeMessage())
        assert sink.modules[0]["module"].string == "hotfix"

    def test_doesnt_apply_hotfix_without_signature(self):
        raise SkipTest
        no_signature = deepcopy(intermediate_filters_doc)
        del no_signature["payloads"]["habitat"]["filters"] \
            ["intermediate"][0]["signature"]
        no_signature_view_results = fake_couchdb.ViewResults({"value": None,
            "key": ["habitat", no_signature["end"]],
            "doc": no_signature})
        self.server.db.default_view_results = no_signature_view_results
        sink = Parser(self.server)
        sink.message(FakeMessage())
        assert sink.modules[0]["module"].string == "test message"

    def test_doesnt_apply_hotfix_without_certificate(self):
        raise SkipTest
        no_certificate = deepcopy(intermediate_filters_doc)
        del no_certificate["payloads"]["habitat"]["filters"] \
            ["intermediate"][0]["certificate"]
        no_certificate_view_results = fake_couchdb.ViewResults({"value": None,
            "key": ["habitat", no_certificate["end"]],
            "doc": no_certificate})
        self.server.db.default_view_results = no_certificate_view_results
        sink = Parser(self.server)
        sink.message(FakeMessage())
        assert sink.modules[0]["module"].string == "test message"

    def test_doesnt_apply_hotfix_with_invalid_signature(self):
        raise SkipTest
        bad_signature = deepcopy(intermediate_filters_doc)
        bad_signature["payloads"]["habitat"]["filters"] \
            ["intermediate"][0]["signature"] = "uuRHEgQmyaEUMHiAUenTHWSUK7Zn6C/VITY+2yH6/AVlOgArHX7LlvuifFO7ZO4EtgaiJJTJ3JwGBrrHvIv4bxD/dO76L6qkPWQWXwC+RAxu5yF0IwulTQK9Iyc902RCe9JPv1kc/hgLojzIVc4scggqtJmERoR5r9EUmya8FDE="
        bad_signature_view_results = fake_couchdb.ViewResults({"value": None,
            "key": ["habitat", bad_signature["end"]],
            "doc": bad_signature})
        self.server.db.default_view_results = bad_signature_view_results
        sink = Parser(self.server)
        sink.message(FakeMessage())
        assert sink.modules[0]["module"].string == "test message"

    def test_doesnt_read_certificate_files_with_path_components(self):
        raise SkipTest
        invalid_certfile = deepcopy(intermediate_filters_doc)
        f = invalid_certfile["payloads"]["habitat"]["filters"] \
                ["intermediate"][0]
        f["certificate"] = "../certs/" + f["certificate"]
        invalid_certfile_view_results = \
            fake_couchdb.ViewResults({"value": None,
                "key": ["habitat", invalid_certfile["end"]],
                "doc": invalid_certfile})
        self.server.db.default_view_results = invalid_certfile_view_results
        sink = Parser(self.server)
        sink.message(FakeMessage())
        assert sink.modules[0]["module"].string == "test message"

    def test_applies_post_filter(self):
        raise SkipTest
        self.server.db.default_view_results = post_filter_view_results
        sink = Parser(self.server)
        sink.message(FakeMessage())
        assert self.server.message.data["result"] == "config was like rad!"
