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

import sys
import os
import signal

from nose.tools import raises
from habitat.utils import crashmat

def fakethread_run(self):
    self.ran = True

class FakeOSModule:
    def __init__(self):
        self.sent_signals = []

    def kill(self, pid, signum):
        assert pid == 1337
        self.sent_signals.append(signum)

    def getpid(self):
        return 1337

class FakeSignalModule:
    def alarm(self, time):
        self.alarm_time = time

# Share code with habitat/tests/test_main/test_signals.py which has exactly
# the same class
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
        assert self.check_run_catches(ValueError) == True

    def test_run_doesnt_catch_sysexit(self):
        assert self.check_run_catches(SystemExit) == False

    def check_run_catches(self, exception):
        t = crashmat.Thread()

        def new_panic():
            pass

        old_panic = crashmat.panic
        crashmat.panic = new_panic

        def err():
            raise exception

        def a():
            a.handled = True
        a.handled = False
        t.handle_exception = a

        t.old_run = err
        t.run()

        crashmat.panic = old_panic

        return a.handled

    def test_handle_exception(self):
        """test handle_exception calls logger.exception and panic"""
        class Logger:
            def exception(self, message):
                self.message = message
                self.exc = sys.exc_info()

        def new_panic():
            new_panic.called = True
        new_panic.called = False

        old_panic = crashmat.panic
        old_logger = crashmat.logger
        crashmat.panic = new_panic
        crashmat.logger = Logger()

        def err():
            raise ValueError
        t = crashmat.Thread(target=err, name="Test Thread: Crashmat")
        t.start()
        t.join()

        assert crashmat.logger.message == \
            "uncaught exception, killing process brutally"
        assert crashmat.logger.exc[0] == ValueError
        assert new_panic.called

        crashmat.logger = old_logger
        crashmat.panic = old_panic

    def test_set_shutdown_function(self):
        def f():
            pass

        assert crashmat.shutdown_function == None
        crashmat.set_shutdown_function(f)
        assert crashmat.shutdown_function == f

        # Clean up...
        crashmat.set_shutdown_function(None)

    def test_panic_without_shutdown_function(self):
        assert crashmat.os == os
        new_os = FakeOSModule()
        crashmat.os = new_os

        crashmat.panic()
        assert new_os.sent_signals == [signal.SIGKILL]

        assert crashmat.os == new_os
        crashmat.os = os

    def test_panic_with_shutdown_function(self):
        assert crashmat.signal == signal
        new_signal = FakeSignalModule()
        crashmat.signal = new_signal

        def f():
            f.called = True
        f.called = False

        crashmat.set_shutdown_function(f)
        crashmat.panic()

        assert new_signal.alarm_time == 60
        assert f.called

        crashmat.set_shutdown_function(None)
        assert crashmat.signal == new_signal
        crashmat.signal = signal
