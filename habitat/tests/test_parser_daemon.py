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

import mox
import couchdbkit

from copy import deepcopy
from nose.tools import assert_raises

from ..utils import immortal_changes

from .. import parser_daemon


class TestParserDaemon(object):
    def setup(self):
        self.m = mox.Mox()

        self.config = {
            "couch_uri": "http://localhost:5984", "couch_db": "test"}

        self.m.StubOutWithMock(parser_daemon, 'couchdbkit')
        self.m.StubOutWithMock(parser_daemon, 'immortal_changes')
        self.m.StubOutWithMock(parser_daemon, 'parser')
        self.mock_server = self.m.CreateMock(couchdbkit.Server)
        self.mock_db = self.m.CreateMock(couchdbkit.Database)
        parser_daemon.couchdbkit.Server("http://localhost:5984")\
                .AndReturn(self.mock_server)
        self.mock_server.__getitem__("test").AndReturn(self.mock_db)
        self.mock_db.info().AndReturn({"update_seq": 191238})
        parser_daemon.parser.Parser(self.config)

        self.m.ReplayAll()
        self.daemon = parser_daemon.ParserDaemon(self.config)
        self.m.VerifyAll()
        self.m.ResetAll()

    def teardown(self):
        self.m.UnsetStubs()

    def test_init_connects_to_couch(self):
        # This actually tested by setup(), since the parser needs to be
        # initialised with CouchDB mocks in all other tests.
        assert self.daemon.db == self.mock_db

    def test_run_calls_wait_and_uses_update_seq(self):
        c = self.m.CreateMock(immortal_changes.Consumer)
        parser_daemon.immortal_changes.Consumer(self.daemon.db).AndReturn(c)
        c.wait(self.daemon._couch_callback, filter="habitat/unparsed",
               since=191238, include_docs=True, heartbeat=1000)
        self.m.ReplayAll()
        self.daemon.run()
        self.m.VerifyAll()

    def test_couch_callback(self):
        result = {'doc': {'hello': 'world'}, 'seq': 1}
        parsed = {'hello': 'parser'}
        self.m.StubOutWithMock(self.daemon, 'parser')
        self.m.StubOutWithMock(self.daemon, '_save_updated_doc')
        self.daemon.parser.parse(result['doc']).AndReturn(parsed)
        self.daemon._save_updated_doc(parsed)
        self.m.ReplayAll()
        self.daemon._couch_callback(result)
        self.m.VerifyAll()

    def test_saving_saves(self):
        orig_doc = {"_id": "id", "receivers": [1], 'data': {'a': 1}}
        parsed_doc = deepcopy(orig_doc)
        parsed_doc['data']['b'] = 2
        self.daemon.db.__getitem__('id').AndReturn(orig_doc)
        self.daemon.db.save_doc(parsed_doc)
        self.m.ReplayAll()
        self.daemon._save_updated_doc(parsed_doc)
        self.m.VerifyAll()

    def test_saving_merges(self):
        orig_doc = {"_id": "id", "receivers": [1], 'data': {'a': 1}}
        parsed_doc = deepcopy(orig_doc)
        parsed_doc['data']['b'] = 2
        updated_doc = deepcopy(orig_doc)
        updated_doc['receivers'].append(2)
        merged_doc = deepcopy(parsed_doc)
        merged_doc['receivers'] = deepcopy(updated_doc['receivers'])
        self.daemon.db.__getitem__('id').AndReturn(updated_doc)
        self.daemon.db.save_doc(merged_doc)
        self.m.ReplayAll()
        self.daemon._save_updated_doc(parsed_doc)
        self.m.VerifyAll()

    def test_saving_merges_after_conflict(self):
        orig_doc = {"_id": "id", "receivers": [1], 'data': {'a': 1}}
        parsed_doc = deepcopy(orig_doc)
        parsed_doc['data']['b'] = 2
        updated_doc = deepcopy(orig_doc)
        updated_doc['receivers'].append(2)
        merged_doc = deepcopy(parsed_doc)
        merged_doc['receivers'] = deepcopy(updated_doc['receivers'])
        self.daemon.db.__getitem__('id').AndReturn(orig_doc)
        self.daemon.db.save_doc(parsed_doc).AndRaise(
            couchdbkit.exceptions.ResourceConflict())
        self.daemon.db.__getitem__('id').AndReturn(updated_doc)
        self.daemon.db.save_doc(merged_doc)
        self.m.ReplayAll()
        self.daemon._save_updated_doc(parsed_doc)
        self.m.VerifyAll()

    def test_saving_quits_after_many_conflicts(self):
        orig_doc = {"_id": "id", "receivers": [1], 'data': {'a': 1}}
        parsed_doc = deepcopy(orig_doc)
        parsed_doc['data']['b'] = 2
        for i in xrange(30):
            self.daemon.db.__getitem__('id').AndReturn(orig_doc)
            self.daemon.db.save_doc(parsed_doc).AndRaise(
                couchdbkit.exceptions.ResourceConflict())
        self.m.ReplayAll()
        assert_raises(RuntimeError, self.daemon._save_updated_doc, parsed_doc)
        self.m.VerifyAll()

