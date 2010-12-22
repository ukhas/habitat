# Copyright 2010 (C) Daniel Richman
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
Tests the crashmat module, ../crashmat.py
"""

from nose.tools import raises
from habitat.utils import crashmat

def fakethread_run(self):
    self.ran = True

class TestCrashmat:
    def test_init_calls_super_and_works(self):
        def test_func():
            test_func.status = 1234
        t = crashmat.Thread(None, test_func, name="Test Thread: Crashmat")
        assert t.name == "Test Thread: Crashmat"

        t.start()
        t.join()
        assert test_func.status == 1234

    def test_init_replaces_run(self):
        class TestThread(crashmat.Thread):
            def run(self):
                return "Testing!"

        t = TestThread()
        assert t.old_run() == "Testing!"
        assert t.run == t.new_run

    def test_run_calls_original_run(self):
        def tgt():
            tgt.ran = True
        tgt.ran = False

        def a():
            raise AssertionError

        t = crashmat.Thread(target=tgt)
        t.handle_exception = a
        t.run()
        assert tgt.ran

        class TestThread(crashmat.Thread):
            def run(self):
                self.ran = True

        t = TestThread()
        t.handle_exception = a
        t.run()
        assert t.ran

    def test_run_catches_exception(self):
        t = crashmat.Thread()

        def err():
            raise ValueError

        def a():
            a.handled = True
        a.handled = False
        t.handle_exception = a

        t.old_run = err
        t.run()

        assert a.handled
