# Copyright 2010, 2011 (C) Adam Greig
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
from nose.tools import assert_raises

from ... import parser


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

    def test_init_loads_CAs(self):
        assert len(self.parser.certificate_authorities) == 1
        cert = self.parser.certificate_authorities[0]
        assert cert.get_serial_number() == 9315532607032814920L

    def test_init_doesnt_load_non_CA_cert(self):
        config = deepcopy(self.parser_config)
        base_path = os.path.split(os.path.abspath(__file__))[0]
        cert_path = os.path.join(base_path, 'non_ca_certs')
        config['parser']['certs_dir'] = cert_path
        assert_raises(ValueError, parser.Parser, config)

    def test_init_connects_to_couch(self):
        # This actually tested by setup(), since the parser needs to be
        # initialised with CouchDB mocks in all other tests.
        assert self.parser.db == self.mock_db

    def test_looks_for_config_doc(self):
        callsign = "habitat"
        time_created = 1234567890
        view_result = {'doc': {'payloads': {callsign: True}}}

        mock_view = self.m.CreateMock(couchdbkit.ViewResults)
        self.parser.db.view("habitat/payload_config", limit=1,
                include_docs=True, startkey=[callsign,
                    time_created]).AndReturn(mock_view)
        mock_view.first().AndReturn(None)

        mock_view = self.m.CreateMock(couchdbkit.ViewResults)
        self.parser.db.view("habitat/payload_config", limit=1,
                include_docs=True, startkey=[callsign,
                    time_created]).AndReturn(mock_view)
        mock_view.first().AndReturn(view_result)

        self.m.ReplayAll()
        result = self.parser._find_config_doc(callsign, time_created)
        assert result == False
        result = self.parser._find_config_doc(callsign, time_created)
        assert result == view_result['doc']
        self.m.VerifyAll()

    def test_doesnt_use_bad_config_doc(self):
        callsign = "habitat"
        time_created = 1234567890
        view_result = {'doc': {'payloads': {"not habitat": True}}}
        mock_view = self.m.CreateMock(couchdbkit.ViewResults)
        self.parser.db.view("habitat/payload_config", limit=1,
                include_docs=True, startkey=[callsign,
                    time_created]).AndReturn(mock_view)
        mock_view.first().AndReturn(view_result)
        self.m.ReplayAll()
        assert self.parser._find_config_doc(callsign, time_created) == False
        self.m.VerifyAll()
        self.m.ResetAll()

    def test_doesnt_parse_if_no_callsign_found(self):
        doc = {'data': {}, 'receivers': {'tester': {}}, '_id': 'telem'}
        doc['data']['_raw'] = "dGVzdCBzdHJpbmc="
        doc['receivers']['tester']['time_created'] = 1234567890
        self.mock_module.pre_parse('test string').AndRaise(ValueError)
        self.m.ReplayAll()
        assert self.parser.parse(doc) is None
        self.m.VerifyAll()

    def test_doesnt_parse_if_no_config(self):
        doc = {'data': {}, 'receivers': {'tester': {}}, '_id': 'telem'}
        doc['data']['_raw'] = "dGVzdCBzdHJpbmc="
        doc['receivers']['tester']['time_created'] = 1234567890
        self.m.StubOutWithMock(self.parser, '_find_config_doc')
        self.mock_module.pre_parse('test string').AndReturn('callsign')
        self.parser._find_config_doc('callsign', 1234567890).AndReturn(False)
        self.m.ReplayAll()
        assert self.parser.parse(doc) is None
        self.m.VerifyAll()

    def test_doesnt_parse_if_wrong_config_protocol(self):
        doc = {'data': {}, 'receivers': {'tester': {}}, '_id': 'telem'}
        doc['data']['_raw'] = "dGVzdCBzdHJpbmc="
        doc['receivers']['tester']['time_created'] = 1234567890
        config = {'payloads': {'callsign': {'sentence': {'protocol': 'Fake'}}}}
        config['_id'] = 'test'
        self.m.StubOutWithMock(self.parser, '_find_config_doc')
        self.mock_module.pre_parse('test string').AndReturn('callsign')
        self.parser._find_config_doc('callsign', 1234567890).AndReturn(config)
        self.m.ReplayAll()
        assert self.parser.parse(doc) is None
        self.m.VerifyAll()

    def test_parses(self):
        doc = {'data': {}, 'receivers': {'tester': {}}, '_id': 'telem'}
        doc['data']['_raw'] = "dGVzdCBzdHJpbmc="
        doc['receivers']['tester']['time_created'] = 1234567890
        config = {'payloads': {'callsign': {'sentence': {'protocol': 'Mock'}}}}
        config['_id'] = 'test'
        self.m.StubOutWithMock(self.parser, '_find_config_doc')
        self.mock_module.pre_parse('test string').AndReturn('callsign')
        self.parser._find_config_doc('callsign', 1234567890).AndReturn(config)
        self.mock_module.parse('test string',
                config['payloads']['callsign']['sentence']).AndReturn({})
        self.m.ReplayAll()
        result = self.parser.parse(doc)
        assert result['data']['_parsed']
        assert result['data']['_protocol'] == 'Mock'
        assert result['data']['_flight'] == 'test'
        assert result['data']['_raw'] == "dGVzdCBzdHJpbmc="
        assert result['receivers']['tester']['time_created'] == 1234567890
        assert len(result['receivers']) == 1
        self.m.VerifyAll()

    def setup_parse(self, config=None, doc=None):
        if config is None:
            config = {'payloads': {'callsign': {'sentence': {}}}}
            config['_id'] = 'test'
            config['payloads']['callsign']['sentence']['protocol'] = 'Mock'
        payload_config = config['payloads']['callsign']['sentence']
        if doc is None:
            doc = {'data': {}, 'receivers': {'tester': {}}, '_id': 'test_id'}
            doc['data']['_raw'] = "dGVzdCBzdHJpbmc="
            doc['receivers']['tester']['time_created'] = 123
        self.m.StubOutWithMock(self.parser, '_find_config_doc')
        self.mock_module.pre_parse('test string').AndReturn('callsign')
        self.parser._find_config_doc('callsign', 123).AndReturn(config)
        self.mock_module.parse('test string', payload_config).AndReturn({})
        return doc, config

    def test_calls_filters(self):
        doc, config = self.setup_parse()
        self.m.StubOutWithMock(self.parser, '_pre_filter')
        self.m.StubOutWithMock(self.parser, '_intermediate_filter')
        self.m.StubOutWithMock(self.parser, '_post_filter')
        payload_config = config['payloads']['callsign']
        self.parser._pre_filter('test string',
                self.parser.modules[0]).AndReturn('test string')
        self.parser._intermediate_filter('test string',
                payload_config).AndReturn('test string')
        self.parser._post_filter({}, payload_config).AndReturn({})
        self.m.ReplayAll()
        self.parser.parse(doc)
        self.m.VerifyAll()

    def test_runs_pre_filters(self):
        self.m.StubOutWithMock(self.parser, '_filter')
        data = 'test data'
        module = {'pre-filters': ['f1', 'f2']}
        self.parser._filter('test data', 'f1', str).AndReturn('filtered data')
        self.parser._filter('filtered data', 'f2', str).AndReturn('result')
        self.m.ReplayAll()
        assert self.parser._pre_filter(data, module) == 'result'
        self.m.VerifyAll()

    def test_runs_intermediate_filters(self):
        self.m.StubOutWithMock(self.parser, '_filter')
        data = 'test data'
        config = {'filters': {'intermediate': ['f1', 'f2']}}
        self.parser._filter(data, 'f1', str).AndReturn('filtered data')
        self.parser._filter('filtered data', 'f2', str).AndReturn('result')
        self.m.ReplayAll()
        assert self.parser._intermediate_filter(data, config) == 'result'
        self.m.VerifyAll()

    def test_runs_post_filters(self):
        self.m.StubOutWithMock(self.parser, '_filter')
        data = {'test': 2}
        config = {'filters': {'post': ['f1', 'f2']}}
        self.parser._filter(data, 'f1', dict).AndReturn({'test': 3})
        self.parser._filter({'test': 3}, 'f2', dict)\
                .AndReturn({'result': True})
        self.m.ReplayAll()
        assert self.parser._post_filter(data, config) == {'result': True}
        self.m.VerifyAll()

    def test_filters_must_have_type(self):
        assert self.parser._filter('test data', {}, str) == 'test data'

    def test_calls_loadable_manager_for_normal_filters(self):
        self.m.StubOutWithMock(self.parser, 'loadable_manager')
        data = 'test data'
        f = {'type': 'normal', 'filter': 'some.func'}
        self.parser.loadable_manager.run(
            'filters.some.func', f, 'test data').AndReturn('filtered')
        self.m.ReplayAll()
        assert self.parser._filter(data, f, str) == 'filtered'
        self.m.VerifyAll()

    def test_calls_loadable_manager_for_normal_filters_with_config(self):
        self.m.StubOutWithMock(self.parser, 'loadable_manager')
        data = 'test data'
        f = {'type': 'normal', 'filter': 'some.func', 'config': 'parameters'}
        self.parser.loadable_manager.run(
            'filters.some.func', f, 'test data').AndReturn('filtered')
        self.m.ReplayAll()
        assert self.parser._filter(data, f, str) == 'filtered'
        self.m.VerifyAll()

    def test_calls_hotfix_filter(self):
        self.m.StubOutWithMock(self.parser, '_hotfix_filter')
        data = 'test data'
        f = {'type': 'hotfix'}
        self.parser._hotfix_filter('test data', f).AndReturn('filtered')
        self.m.ReplayAll()
        assert self.parser._filter(data, f, str) == 'filtered'
        self.m.VerifyAll()

    def test_skips_unknown_filter_types(self):
        assert self.parser._filter('tdta', {'type': '?'}, str) == 'tdta'

    def test_unimportable_normal_filters(self):
        f = {'filter': 'fakefakefake.fakepath.is.fake', 'type': 'normal'}
        assert self.parser._filter('test string', f, str) == 'test string'

    def test_sanity_checks_filter_return_type(self):
        self.m.StubOutWithMock(self.parser, 'loadable_manager')
        cases = [("string", str, True), ("string", dict, False),
                 ({"data": True}, dict, True), ({"data": True}, str, False)]

        for (filter_return, want_type, should_work) in cases:
            data_in = 'test string'
            config = {'filter': 'intercept_me', 'type': 'normal'}
            if should_work:
                expect_result = filter_return
            else:
                expect_result = data_in

            self.parser.loadable_manager.run('filters.intercept_me', config,
                    data_in).AndReturn(filter_return)

            self.m.ReplayAll()
            assert self.parser._filter(data_in, config, want_type) == \
                    expect_result
            self.m.VerifyAll()
            self.m.ResetAll()

    def test_incorrect_num_args_normal_filters(self):
        def fil(data, config, too, many, args):
            assert data == 'test string'
            assert config == 'config'
            return 'filtered'
        f = {'callable': fil, 'config': 'config', 'type': 'normal'}
        assert self.parser._filter('test string', f, str) == 'test string'

    def test_hotfix_filters(self):
        self.m.StubOutWithMock(self.parser, '_sanity_check_hotfix')
        self.m.StubOutWithMock(self.parser, '_get_certificate')
        self.m.StubOutWithMock(self.parser, '_verify_certificate')
        self.m.StubOutWithMock(self.parser, '_compile_hotfix')
        f = {'certificate': 'cert'}
        env = {'f': lambda data: 'hotfix ran'}
        self.parser._sanity_check_hotfix(f)
        self.parser._get_certificate('cert').AndReturn('got_cert')
        self.parser._verify_certificate(f, 'got_cert')
        self.parser._compile_hotfix(f).AndReturn(env)
        self.m.ReplayAll()
        assert self.parser._hotfix_filter({}, f) == 'hotfix ran'
        self.m.VerifyAll()

    def test_handles_hotfix_exceptions(self):
        self.m.StubOutWithMock(self.parser, '_sanity_check_hotfix')
        self.m.StubOutWithMock(self.parser, '_get_certificate')
        self.m.StubOutWithMock(self.parser, '_verify_certificate')
        self.m.StubOutWithMock(self.parser, '_compile_hotfix')
        f = {'certificate': 'cert', 'type': 'hotfix'}

        class OhNoError(Exception):
            pass

        def hotfix(data):
            raise OhNoError

        env = {'f': hotfix}
        self.parser._sanity_check_hotfix(f)
        self.parser._get_certificate('cert').AndReturn('got_cert')
        self.parser._verify_certificate(f, 'got_cert')
        self.parser._compile_hotfix(f).AndReturn(env)
        self.m.ReplayAll()
        assert self.parser._filter('unfiltered', f, str) == 'unfiltered'
        self.m.VerifyAll()

    def test_handles_hotfix_syntax_error(self):
        f = {'code': "this isn't python!"}
        assert_raises(ValueError, self.parser._compile_hotfix, f)

    def test_handles_invalid_hotfix_code(self):
        f = {'code': 12}
        assert_raises(ValueError, self.parser._compile_hotfix, f)

    def test_hotfix_doesnt_allow_invalid_signature(self):
        f = {'code': 'return False', 'certificate': 'adamgreig.crt'}
        f['signature'] = "this isn't a signature!"
        cert = self.m.CreateMock(M2Crypto.X509.X509)
        cert.verify(mox.IsA(M2Crypto.EVP.PKey)).AndReturn(True)
        self.m.ReplayAll()
        assert_raises(ValueError, self.parser._verify_certificate, f, cert)
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
        assert_raises(ValueError, self.parser._verify_certificate, f, cert)
        self.m.VerifyAll()

    def test_hotfix_doesnt_allow_missing_signature(self):
        f = {'code': 'bla', 'certificate': 'cert.pem'}
        assert_raises(ValueError, self.parser._sanity_check_hotfix, f)

    def test_hotfix_doesnt_allow_missing_certificate(self):
        f = {'code': 'bla', 'signature': 'sign here'}
        assert_raises(ValueError, self.parser._sanity_check_hotfix, f)

    def test_hotfix_doesnt_allow_missing_code(self):
        f = {'certificate': 'cert.pem', 'signature': 'sign here'}
        assert_raises(ValueError, self.parser._sanity_check_hotfix, f)

    def test_hotfix_doesnt_allow_certs_not_signed_by_ca(self):
        cert = self.m.CreateMock(M2Crypto.X509.X509)
        cert.verify(mox.IsA(M2Crypto.EVP.PKey)).AndReturn(False)
        self.m.ReplayAll()
        assert_raises(ValueError, self.parser._verify_certificate, {}, cert)
        self.m.VerifyAll()

    def test_hotfix_doesnt_allow_unloadable_certs(self):
        assert_raises(ValueError, self.parser._get_certificate, 'doesntexist')

    def test_hotfix_doesnt_allow_certs_with_paths_in_name(self):
        f = {'certificate': '../../dots.pem', 'code': '', 'signature': ''}
        assert_raises(ValueError, self.parser._sanity_check_hotfix, f)
