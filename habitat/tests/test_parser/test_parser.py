# Copyright 2010, 2011, 2013 (C) Adam Greig
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
import mox

import couchdbkit
import M2Crypto

from copy import deepcopy
from nose.tools import assert_raises, eq_

from ... import parser, loadable_manager


class TestParser(object):
    def setup(self):
        self.m = mox.Mox()
        self.mock_module = self.m.CreateMock(parser.ParserModule)

        class MockModule(parser.ParserModule):
            def __new__(cls, parser):
                return self.mock_module

        base_path = os.path.split(os.path.abspath(__file__))[0]
        cert_path = os.path.join(base_path, 'certs')
        self.parser_config = {"parser": {"modules": [
            {"name": "Mock", "class": MockModule}],
            "certs_dir": cert_path}, "loadables": [],
            "couch_uri": "http://localhost:5984", "couch_db": "test"}

        self.m.StubOutWithMock(parser, 'couchdbkit')
        self.mock_server = self.m.CreateMock(couchdbkit.Server)
        self.mock_db = self.m.CreateMock(couchdbkit.Database)
        parser.couchdbkit.Server("http://localhost:5984")\
                .AndReturn(self.mock_server)
        self.mock_server.__getitem__("test").AndReturn(self.mock_db)

        self.m.ReplayAll()
        self.parser = parser.Parser(self.parser_config)
        self.m.VerifyAll()
        self.m.ResetAll()

    def teardown(self):
        self.m.UnsetStubs()

    def test_init_doesnt_mess_up_config_modules(self):
        # once upon a time parser didn't deepcopy config, so config['modules']
        # would get all messed up
        assert 'module' not in self.parser_config['parser']['modules'][0]

    def test_init_loads_modules_in_config(self):
        assert len(self.parser.modules) == 1
        assert self.parser.modules[0]["module"] == self.mock_module

    def test_init_doesnt_load_bad_modules(self):
        def try_to_load_module(module):
            new_config = deepcopy(self.parser_config)
            new_config["parser"]["modules"][0]["class"] = module
            parser.Parser(new_config)

        class EmptyModule(object):
            """A mock parser module without any required methods"""
            pass
        assert_raises(TypeError, try_to_load_module, EmptyModule)

        class NoInitModule(parser.ParserModule):
            """A mock parser module which lacks an __init__ method"""
            __init__ = None
        assert_raises(TypeError, try_to_load_module, NoInitModule)

        class BadInitModule(parser.ParserModule):
            """A mock parser module whose init signature is wrong"""
            def __init__(self):
                pass
        assert_raises(TypeError, try_to_load_module, BadInitModule)

        class NoPreParseModule(parser.ParserModule):
            """A mock parser module with no pre_parse method"""
            pre_parse = None
        assert_raises(TypeError, try_to_load_module, NoPreParseModule)

        class BadPreParseModule(parser.ParserModule):
            """A mock parser module with an incorrect pre_parse signature"""
            def pre_parse(self):
                pass
        assert_raises(TypeError, try_to_load_module, BadPreParseModule)

        class NoParseModule(parser.ParserModule):
            """A mock parser module with no parse method"""
            parse = None
        assert_raises(TypeError, try_to_load_module, NoParseModule)

        class BadParseModule(parser.ParserModule):
            """A mock parser module with an incorrect parse signature"""
            def parse(self):
                pass
        assert_raises(TypeError, try_to_load_module, BadParseModule)

    def test_init_connects_to_couch(self):
        # This actually tested by setup(), since the parser needs to be
        # initialised with CouchDB mocks in all other tests.
        assert self.parser.db == self.mock_db

    def test_find_config_doc_looks_for_flights(self):
        view_result = [{"key": [5, 5, 654, 0]}, # this flight has ended
                       {"key": [5, 5, 654, 1], "doc": {
                           "_id": 456, "sentences": [
                                {"callsign": "habitat"}
                            ]}, "id": 654},
                       {"key": [6, 3, 321, 0]},
                       {"key": [6, 3, 321, 1], "doc": {
                           "_id": 123, "sentences": [
                                {"callsign": "habitat"}
                            ]}, "id": 321}]
        self.m.StubOutWithMock(parser, 'time')
        parser.time.time().AndReturn(4)
        self.parser.db.view("flight/end_start_including_payloads",
            include_docs=True, startkey=[4]).AndReturn(view_result)
        self.m.ReplayAll()
        result = self.parser._find_config_doc("habitat")
        assert result == {"id": 123, "flight_id": 321,
                          "payload_configuration": view_result[3]["doc"]}
        self.m.VerifyAll()

    def test_find_config_doc_fallbacks_to_configs(self):
        flight_result = [{"key": [5, 3, 321, 0]},
                         {"key": [5, 3, 321, 1], "doc": {
                             "_id": 123, "sentences": [{"callsign": "bla"}]},
                          "id": 321}]
        config_result = {"id": 123, "doc": {
            "sentences": [{"callsign": "habitat"}]}}
        self.m.StubOutWithMock(parser, 'time')
        mock_view = self.m.CreateMock(couchdbkit.ViewResults)
        parser.time.time().AndReturn(4)
        self.parser.db.view("flight/end_start_including_payloads",
            include_docs=True, startkey=[4]).AndReturn(flight_result)
        self.parser.db.view(
            "payload_configuration/callsign_time_created_index",
            startkey=["habitat", "inf"], include_docs=True, limit=1,
            descending=True
            ).AndReturn(mock_view)
        mock_view.first().AndReturn(config_result)
        self.m.ReplayAll()
        result = self.parser._find_config_doc("habitat")
        eq_(result, {"id": 123, "payload_configuration": config_result["doc"]})
        self.m.VerifyAll()

    def test_is_ok_with_configs_without_sentences(self):
        # issue #255: KeyError because sentences is optional in
        # payload_configuration documents
        config = {"not_sentences": None}
        self.parser._callsign_in_config("habitat", config)

    def test_doesnt_parse_if_no_callsign_found(self):
        doc = {'data': {}, 'receivers': {'tester': {}}, '_id': 'telem'}
        doc['data']['_raw'] = "dGVzdCBzdHJpbmc="
        doc['receivers']['tester']['time_created'] = 1234567890
        self.mock_module.pre_parse('test string').AndRaise(parser.CantParse)
        self.m.ReplayAll()
        assert self.parser.parse(doc) is None
        self.m.VerifyAll()

    def test_doesnt_parse_if_no_config(self):
        doc = {'data': {}, 'receivers': {'tester': {}}, '_id': 'telem'}
        doc['data']['_raw'] = "dGVzdCBzdHJpbmc="
        doc['receivers']['tester']['time_created'] = 1234567890
        self.m.StubOutWithMock(self.parser, '_find_config_doc')
        self.mock_module.pre_parse('test string').AndReturn('callsign')
        self.parser._find_config_doc('callsign').AndReturn(False)
        self.m.ReplayAll()
        assert self.parser.parse(doc) is None
        self.m.VerifyAll()

    def test_doesnt_parse_if_wrong_config_protocol(self):
        doc = {'data': {}, 'receivers': {'tester': {}}, '_id': 'telem'}
        doc['data']['_raw'] = "dGVzdCBzdHJpbmc="
        doc['receivers']['tester']['time_created'] = 1234567890
        config = {'sentences': [{"callsign": "callsign", 'protocol': 'Fake'}]}
        config = {'payload_configuration': config}
        config['id'] = 'test'
        self.m.StubOutWithMock(self.parser, '_find_config_doc')
        self.mock_module.pre_parse('test string').AndReturn('callsign')
        self.parser._find_config_doc('callsign').AndReturn(config)
        self.m.ReplayAll()
        assert self.parser.parse(doc) is None
        self.m.VerifyAll()

    def test_uses_fallback_callsign(self):
        fallbacks = {'payload': 'call'}
        self.mock_module.pre_parse('rawdata').AndRaise(
            parser.CantExtractCallsign)
        self.m.ReplayAll()
        mod = self.parser.modules[0]
        result = self.parser._get_callsign("rawdata", fallbacks, mod)
        assert result == "call"
        self.m.VerifyAll()

    def test_parses(self):
        doc = {'data': {}, 'receivers': {'tester': {}}, '_id': 'telem'}
        doc['data']['_raw'] = "dGVzdCBzdHJpbmc="
        doc['receivers']['tester']['time_created'] = 1234567890
        config = {'sentences': [{"callsign": "callsign", 'protocol': 'Mock'}]}
        config = {'payload_configuration': config}
        config['id'] = 'test'
        self.m.StubOutWithMock(self.parser, '_find_config_doc')
        self.m.StubOutWithMock(parser, 'rfc3339')
        self.mock_module.pre_parse('test string').AndReturn('callsign')
        self.parser._find_config_doc('callsign').AndReturn(config)
        self.mock_module.parse('test string',
            config['payload_configuration']['sentences'][0]).AndReturn({})
        parser.rfc3339.now_to_rfc3339_utcoffset().AndReturn("thetime")
        self.m.ReplayAll()
        result = self.parser.parse(doc)
        assert result['data']['_parsed']
        assert result['data']['_protocol'] == 'Mock'
        assert result['data']['_parsed'] == {
            "payload_configuration": "test",
            "configuration_sentence_index": 0,
            "time_parsed": "thetime"
        }
        assert result['data']['_raw'] == "dGVzdCBzdHJpbmc="
        assert result['receivers']['tester']['time_created'] == 1234567890
        assert len(result['receivers']) == 1
        self.m.VerifyAll()

    def test_uses_fallback_data(self):
        doc = {'data': {}, 'receivers': {'tester': {}}, '_id': 'telem'}
        doc['data']['_raw'] = "dGVzdCBzdHJpbmc="
        doc['data']['_fallbacks'] = {'fall': 'back', 'from': 'fallback'}
        doc['receivers']['tester']['time_created'] = 1234567890
        config = {'sentences': [{"callsign": "callsign", 'protocol': 'Mock'}]}
        config = {'payload_configuration': config}
        config['id'] = 'test'
        self.m.StubOutWithMock(self.parser, '_find_config_doc')
        self.m.StubOutWithMock(parser, 'rfc3339')
        self.mock_module.pre_parse('test string').AndReturn('callsign')
        self.parser._find_config_doc('callsign').AndReturn(config)
        self.mock_module.parse('test string',
            config['payload_configuration']['sentences'][0]).AndReturn(
            {'from': 'parser'})
        parser.rfc3339.now_to_rfc3339_utcoffset().AndReturn("thetime")
        self.m.ReplayAll()
        result = self.parser.parse(doc)
        assert result['data']['_parsed']
        assert result['data']['fall'] == 'back'
        assert result['data']['from'] == 'parser'
        assert result['data']['_protocol'] == 'Mock'
        assert result['data']['_parsed'] == {
            "payload_configuration": "test",
            "configuration_sentence_index": 0,
            "time_parsed": "thetime"
        }
        assert result['data']['_raw'] == "dGVzdCBzdHJpbmc="
        assert result['receivers']['tester']['time_created'] == 1234567890
        assert len(result['receivers']) == 1
        self.m.VerifyAll()

    def setup_parse(self, config=None, doc=None):
        if config is None:
            config = {'payload_configuration': {'sentences': [
                {"callsign": "callsign", "protocol": "Mock"}]}, "id": "test"}
        payload_config = config['payload_configuration']['sentences'][0]
        if doc is None:
            doc = {'data': {}, 'receivers': {'tester': {}}, '_id': 'test_id'}
            doc['data']['_raw'] = "dGVzdCBzdHJpbmc="
            doc['receivers']['tester']['time_created'] = 123
        self.m.StubOutWithMock(self.parser, '_find_config_doc')
        self.mock_module.pre_parse('test string').AndReturn('callsign')
        self.parser._find_config_doc('callsign').AndReturn(config)
        self.mock_module.parse('test string', payload_config).AndReturn({})
        return doc, config

    def test_calls_filters(self):
        doc, config = self.setup_parse()
        mock_filtering = self.m.CreateMock(parser.ParserFiltering)
        payload_config = config['payload_configuration']['sentences'][0]
        mock_filtering.pre_filter('test string',
                self.parser.modules[0]).AndReturn('test string')
        mock_filtering.intermediate_filter('test string',
                payload_config).AndReturn('test string')
        mock_filtering.post_filter({}, payload_config).AndReturn({})
        self.parser.filtering = mock_filtering
        self.m.ReplayAll()
        self.parser.parse(doc)
        self.m.VerifyAll()

    def test_doesnt_use_configs_for_other_protocols(self):
        # This was a bug: by @danielrichman:
        # If we have parsermodules A and B, and call parse("some
        # data"); protocols A and B are similar enough that pre_parse for A
        # might return a callsing for something actually protocol B, but then
        # rejects it later in parse, `config = self._get_config(...)` will
        # remember the old config found.

        # set up a second module
        second_module = self.m.CreateMock(parser.ParserModule)
        class MockTwo(parser.ParserModule):
            def __new__(cls, parser):
                return second_module
        mod_config = {"name": "MockTwo", "class": MockTwo}
        self.parser.modules.append(mod_config)

        # stub out most parse functionality
        self.m.StubOutWithMock(self.parser, '_get_callsign')
        self.m.StubOutWithMock(self.parser, '_get_config')
        self.m.StubOutWithMock(self.parser, '_get_data')

        # fake doc
        doc = {'data': {}, 'receivers': {'tester': {}}, '_id': 'test_id'}
        doc['data']['_raw'] = "dGVzdCBzdHJpbmc="
        doc['receivers']['tester']['time_created'] = 123
        
        # first module gets used, returns valid callsign & config, no data
        mods = self.parser.modules
        self.parser._get_callsign("test string", {},
            mods[0]).AndReturn("callsign one")
        self.parser._get_config("callsign one", None).AndReturn("config one")
        self.parser._get_data("test string", "callsign one", "config one",
            mods[0]).AndRaise(parser.CantGetData())

        # second module gets tried, should be given None as the config as
        # the previously found one is bad. the bug is that it would be given
        # "config one" instead of None.
        self.parser._get_callsign("test string", {},
            mods[1]).AndReturn("callsign two")
        self.parser._get_config("callsign two", None).AndReturn("config two")
        self.parser._get_data("test string", "callsign two", "config two",
            mods[1]).AndRaise(parser.CantGetData())

        self.m.ReplayAll()
        self.parser.parse(doc)
        self.m.VerifyAll()

    def test_uses_provided_config_despite_no_id(self):
        config = {"sentences": [{"callsign": "supply", "protocol": "Mock"}]}
        result = {"id": None, "payload_configuration": config}
        assert self.parser._get_config('supply', config) == result

    def test_uses_provided_config(self):
        config = {"sentences": [{"callsign": "supply", "protocol": "Mock"}],
                  "_id": "some_actual_document"}
        result = {"id": "some_actual_document",
                  "payload_configuration": config}
        assert self.parser._get_config('supply', config) == result

    def test_raises_if_provided_config_doesnt_have_correct_callsign(self):
        config = {"sentences": [{"callsign": "bad", "protocol": "Mock"}]}
        assert_raises(parser.CantGetConfig, self.parser._get_config,
            'good', config)

class TestParserFiltering(object):
    def setup(self):
        self.m = mox.Mox()

        base_path = os.path.split(os.path.abspath(__file__))[0]
        cert_path = os.path.join(base_path, 'certs')
        self.parser_config = {"parser": {
            "certs_dir": cert_path}, "loadables": [],
            "couch_uri": "http://localhost:5984", "couch_db": "test"}

        lmgr = self.m.CreateMock(loadable_manager.LoadableManager)
        self.fil = parser.ParserFiltering(self.parser_config, lmgr)

    def teardown(self):
        self.m.UnsetStubs()

    def test_init_loads_CAs(self):
        assert len(self.fil.certificate_authorities) == 1
        cert = self.fil.certificate_authorities[0]
        assert cert.get_serial_number() == 9315532607032814920L

    def test_init_doesnt_load_non_CA_cert(self):
        config = deepcopy(self.parser_config)
        base_path = os.path.split(os.path.abspath(__file__))[0]
        cert_path = os.path.join(base_path, 'non_ca_certs')
        config['parser']['certs_dir'] = cert_path
        assert_raises(ValueError, parser.Parser, config)

    def test_runs_pre_filters(self):
        self.m.StubOutWithMock(self.fil, '_filter')
        data = 'test data'
        module = {'pre-filters': ['f1', 'f2']}
        self.fil._filter('test data', 'f1', str).AndReturn('filtered data')
        self.fil._filter('filtered data', 'f2', str).AndReturn('result')
        self.m.ReplayAll()
        assert self.fil.pre_filter(data, module) == 'result'
        self.m.VerifyAll()

    def test_runs_intermediate_filters(self):
        self.m.StubOutWithMock(self.fil, '_filter')
        data = 'test data'
        config = {'filters': {'intermediate': ['f1', 'f2']}}
        self.fil._filter(data, 'f1', str).AndReturn('filtered data')
        self.fil._filter('filtered data', 'f2', str).AndReturn('result')
        self.m.ReplayAll()
        assert self.fil.intermediate_filter(data, config) == 'result'
        self.m.VerifyAll()

    def test_runs_post_filters(self):
        self.m.StubOutWithMock(self.fil, '_filter')
        data = {'test': 2}
        config = {'filters': {'post': ['f1', 'f2']}}
        self.fil._filter(data, 'f1', dict).AndReturn({'test': 3})
        self.fil._filter({'test': 3}, 'f2', dict)\
                .AndReturn({'result': True})
        self.m.ReplayAll()
        assert self.fil.post_filter(data, config) == {'result': True}
        self.m.VerifyAll()

    def test_filters_must_have_type(self):
        assert self.fil._filter('test data', {}, str) == 'test data'

    def test_calls_loadable_manager_for_normal_filters(self):
        data = 'test data'
        f = {'type': 'normal', 'filter': 'some.func'}
        self.fil.loadable_manager.run(
            'filters.some.func', f, 'test data').AndReturn('filtered')
        self.m.ReplayAll()
        assert self.fil._filter(data, f, str) == 'filtered'
        self.m.VerifyAll()

    def test_calls_loadable_manager_for_normal_filters_with_config(self):
        data = 'test data'
        f = {'type': 'normal', 'filter': 'some.func', 'config': 'parameters'}
        self.fil.loadable_manager.run(
            'filters.some.func', f, 'test data').AndReturn('filtered')
        self.m.ReplayAll()
        assert self.fil._filter(data, f, str) == 'filtered'
        self.m.VerifyAll()

    def test_calls_hotfix_filter(self):
        self.m.StubOutWithMock(self.fil, '_hotfix_filter')
        data = 'test data'
        f = {'type': 'hotfix'}
        self.fil._hotfix_filter('test data', f).AndReturn('filtered')
        self.m.ReplayAll()
        assert self.fil._filter(data, f, str) == 'filtered'
        self.m.VerifyAll()

    def test_skips_unknown_filter_types(self):
        assert self.fil._filter('tdta', {'type': '?'}, str) == 'tdta'

    def test_unimportable_normal_filters(self):
        f = {'filter': 'fakefakefake.fakepath.is.fake', 'type': 'normal'}
        assert self.fil._filter('test string', f, str) == 'test string'

    def test_sanity_checks_filter_return_type(self):
        cases = [("string", str, True), ("string", dict, False),
                 ({"data": True}, dict, True), ({"data": True}, str, False)]

        for (filter_return, want_type, should_work) in cases:
            data_in = 'test string'
            config = {'filter': 'intercept_me', 'type': 'normal'}
            if should_work:
                expect_result = filter_return
            else:
                expect_result = data_in

            self.fil.loadable_manager.run('filters.intercept_me', config,
                    data_in).AndReturn(filter_return)

            self.m.ReplayAll()
            assert self.fil._filter(data_in, config, want_type) == \
                    expect_result
            self.m.VerifyAll()
            self.m.ResetAll()

    def test_incorrect_num_args_normal_filters(self):
        def fil(data, config, too, many, args):
            assert data == 'test string'
            assert config == 'config'
            return 'filtered'
        f = {'callable': fil, 'config': 'config', 'type': 'normal'}
        assert self.fil._filter('test string', f, str) == 'test string'

    def test_hotfix_filters(self):
        self.m.StubOutWithMock(self.fil, '_sanity_check_hotfix')
        self.m.StubOutWithMock(self.fil, '_get_certificate')
        self.m.StubOutWithMock(self.fil, '_verify_certificate')
        self.m.StubOutWithMock(self.fil, '_compile_hotfix')
        f = {'certificate': 'cert'}
        env = {'f': lambda data: 'hotfix ran'}
        self.fil._sanity_check_hotfix(f)
        self.fil._get_certificate('cert').AndReturn('got_cert')
        self.fil._verify_certificate(f, 'got_cert')
        self.fil._compile_hotfix(f).AndReturn(env)
        self.m.ReplayAll()
        assert self.fil._hotfix_filter({}, f) == 'hotfix ran'
        self.m.VerifyAll()

    def test_handles_hotfix_exceptions(self):
        self.m.StubOutWithMock(self.fil, '_sanity_check_hotfix')
        self.m.StubOutWithMock(self.fil, '_get_certificate')
        self.m.StubOutWithMock(self.fil, '_verify_certificate')
        self.m.StubOutWithMock(self.fil, '_compile_hotfix')
        f = {'certificate': 'cert', 'type': 'hotfix'}

        class OhNoError(Exception):
            pass

        def hotfix(data):
            raise OhNoError

        env = {'f': hotfix}
        self.fil._sanity_check_hotfix(f)
        self.fil._get_certificate('cert').AndReturn('got_cert')
        self.fil._verify_certificate(f, 'got_cert')
        self.fil._compile_hotfix(f).AndReturn(env)
        self.m.ReplayAll()
        assert self.fil._filter('unfiltered', f, str) == 'unfiltered'
        self.m.VerifyAll()

    def test_handles_hotfix_syntax_error(self):
        f = {'code': "this isn't python!"}
        assert_raises(ValueError, self.fil._compile_hotfix, f)

    def test_handles_invalid_hotfix_code(self):
        f = {'code': 12}
        assert_raises(ValueError, self.fil._compile_hotfix, f)

    def test_hotfix_doesnt_allow_invalid_signature(self):
        f = {'code': 'return False', 'certificate': 'adamgreig.crt'}
        f['signature'] = "this isn't a signature!"
        cert = self.m.CreateMock(M2Crypto.X509.X509)
        cert.verify(mox.IsA(M2Crypto.EVP.PKey)).AndReturn(True)
        self.m.ReplayAll()
        assert_raises(ValueError, self.fil._verify_certificate, f, cert)
        self.m.VerifyAll()

    def test_hotfix_doesnt_allow_wrong_signature(self):
        f = {'code': 'return False', 'certificate': 'adamgreig.crt'}
        f['signature'] = "c2lnbmF0dXJl"
        d = "e706fa9325ded821b93ed8bde1093c7c1394b3342739239f6f5f848b8ea76eb4"
        cert = self.m.CreateMock(M2Crypto.X509.X509)
        pubkey = self.m.CreateMock(M2Crypto.EVP.PKey)
        rsa = self.m.CreateMock(M2Crypto.RSA.RSA_pub)
        cert.verify(mox.IsA(M2Crypto.EVP.PKey)).AndReturn(True)
        cert.get_pubkey().AndReturn(pubkey)
        pubkey.get_rsa().AndReturn(rsa)
        rsa.verify(d, "signature", 'sha256').AndReturn(False)
        self.m.ReplayAll()
        assert_raises(ValueError, self.fil._verify_certificate, f, cert)
        self.m.VerifyAll()

    def test_hotfix_doesnt_allow_missing_signature(self):
        f = {'code': 'bla', 'certificate': 'cert.pem'}
        assert_raises(ValueError, self.fil._sanity_check_hotfix, f)

    def test_hotfix_doesnt_allow_missing_certificate(self):
        f = {'code': 'bla', 'signature': 'sign here'}
        assert_raises(ValueError, self.fil._sanity_check_hotfix, f)

    def test_hotfix_doesnt_allow_missing_code(self):
        f = {'certificate': 'cert.pem', 'signature': 'sign here'}
        assert_raises(ValueError, self.fil._sanity_check_hotfix, f)

    def test_hotfix_doesnt_allow_certs_not_signed_by_ca(self):
        cert = self.m.CreateMock(M2Crypto.X509.X509)
        cert.verify(mox.IsA(M2Crypto.EVP.PKey)).AndReturn(False)
        self.m.ReplayAll()
        assert_raises(ValueError, self.fil._verify_certificate, {}, cert)
        self.m.VerifyAll()

    def test_hotfix_doesnt_allow_unloadable_certs(self):
        assert_raises(ValueError, self.fil._get_certificate, 'doesntexist')

    def test_hotfix_doesnt_allow_certs_with_paths_in_name(self):
        f = {'certificate': '../../dots.pem', 'code': '', 'signature': ''}
        assert_raises(ValueError, self.fil._sanity_check_hotfix, f)

