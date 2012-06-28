# Copyright 2012 (C) Daniel Richman
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
Tests for habitat.utils.immortal_changes
"""

import mox
import couchdbkit
import time

from nose.tools import assert_raises

from ...utils import immortal_changes


class DummyConsumer(object):
    # couchdbkit.Consumer, which Consumer is a subclass of, proxies
    # all methods to a backend object (e.g., "sync"). This is the
    # easiest way to get hold of those calls in order to test them,
    # but it's a bit dependent on couchdbkit's internals, which sucks.
 
    def __init__(self, *args, **kwargs):
        pass

    def wait(func, **kwargs):
        raise NotImplementedError

class DummyTimeModule(object):
    # replacing the 'time' item in immortal_changes' namespace is probably
    # nicer than modifying the real time module.

    def sleep(self, length):
        raise NotImplementedError

class TestParser(object):
    def setup(self):
        self.m = mox.Mox()

        self.consumer = immortal_changes.Consumer(None,
            backend='habitat.tests.test_utils.'
                    'test_immortal_changes.DummyConsumer')
        assert isinstance(self.consumer._consumer, DummyConsumer)
        self.m.StubOutWithMock(self.consumer._consumer, "wait")

        assert immortal_changes.time == time
        immortal_changes.time = DummyTimeModule()
        self.m.StubOutWithMock(immortal_changes.time, "sleep")

        self.m.StubOutWithMock(immortal_changes.logger, "exception")

        # for brevity.
        self.backend = self.consumer._consumer.wait
        self.sleep = immortal_changes.time.sleep
        self.exc = immortal_changes.logger.exception
        self.cb = self.m.CreateMockAnything()

    def teardown(self):
        self.m.UnsetStubs()

        assert isinstance(immortal_changes.time, DummyTimeModule)
        immortal_changes.time = time

    def test_works_normally(self):
        # Probably a good start.

        def some_callbacks(cb, **kwargs):
            cb({"seq": 2, "changes": []})
            cb({"seq": 3, "changes": []})
            cb({"seq": 4, "changes": []})
            raise SystemExit

        self.backend(mox.IgnoreArg(), since=0).WithSideEffects(some_callbacks)
        self.cb({"seq": 2, "changes": []})
        self.cb({"seq": 3, "changes": []})
        self.cb({"seq": 4, "changes": []})

        self.m.ReplayAll()

        try:
            self.consumer.wait(self.cb)
        except SystemExit:
            pass

        self.m.VerifyAll()

    def test_handles_callback_exceptions(self):
        def some_callbacks(cb, **kwargs):
            cb({"seq": 2, "changes": []})
            cb({"seq": 3, "changes": []})
            raise SystemExit

        self.backend(mox.IgnoreArg(), since=0).WithSideEffects(some_callbacks)
        self.cb({"seq": 2, "changes": []}).AndRaise(KeyError)
        self.exc("Exception from changes callback")
        self.cb({"seq": 3, "changes": []})

        self.m.ReplayAll()

        try:
            self.consumer.wait(self.cb)
        except SystemExit:
            pass

        self.m.VerifyAll()

    def test_handles_couch_exceptions(self):
        self.backend(mox.IgnoreArg(), since=0).AndRaise(IOError)
        self.exc("Exception from changes (couch)")
        self.sleep(2)
        self.backend(mox.IgnoreArg(), since=0).AndRaise(SystemExit)

        self.m.ReplayAll()

        try:
            self.consumer.wait(self.cb)
        except SystemExit:
            pass

        self.m.VerifyAll()

    def test_resumes_at_correct_seq(self):
        def callbacks_a(cb, **kwargs):
            cb({"seq": 24, "changes": []})
            cb({"seq": 25, "changes": []})
            raise IOError

        def callbacks_b(cb, **kwargs):
            cb({"seq": 26, "changes": []})
            raise SystemExit

        self.backend(mox.IgnoreArg(), since=23).WithSideEffects(callbacks_a)
        self.cb({"seq": 24, "changes": []})
        self.cb({"seq": 25, "changes": []})
        self.exc("Exception from changes (couch)")
        self.sleep(2)
        self.backend(mox.IgnoreArg(), since=25).WithSideEffects(callbacks_b)
        self.cb({"seq": 26, "changes": []})

        self.m.ReplayAll()

        try:
            self.consumer.wait(self.cb, since=23)
        except SystemExit:
            pass

        self.m.VerifyAll()

    def test_backs_off(self):
        for length in [2, 4, 8, 16, 32, 60, 60, 60]:
            self.backend(mox.IgnoreArg(), since=0).AndRaise(IOError)
            self.exc("Exception from changes (couch)")
            self.sleep(length)

        def callbacks(cb, **kwargs):
            cb({"seq": 2, "changes": []})
            raise IOError

        self.backend(mox.IgnoreArg(), since=0).WithSideEffects(callbacks)
        self.cb({"seq": 2, "changes": []})
        self.exc("Exception from changes (couch)")
        self.sleep(2)
        self.backend(mox.IgnoreArg(), since=2).AndRaise(SystemExit)

        self.m.ReplayAll()

        try:
            self.consumer.wait(self.cb)
        except SystemExit:
            pass

        self.m.VerifyAll()
