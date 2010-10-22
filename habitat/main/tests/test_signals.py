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
Tests signals.listen, which listens for signals forever and calls methods
of Program when it receives one that it is looking for.
"""

from habitat.main import SignalListener
import habitat.main.signals as signals_module
from nose.tools import raises
import signal
import threading

class PausedManyTimes(Exception):
    pass

# I know this is actually a class. But think of it as a module,
# in that I can call FakeSignalModule.signal(sig, handler) and .pause()
class FakeSignalModule:
    (SIGTERM, SIGINT, SIGHUP) = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)

    def __init__(self):
        self.signals = {}
        self.pause_hits = 0

    def signal(self, signal, handler):
        assert not signal in self.signals
        self.signals[signal] = handler

    def pause(self):
        self.pause_hits += 1
        if self.pause_hits == 50:
            raise PausedManyTimes

class DumbProgram:
    def __init__(self):
        self.reload_hits = 0
        self.shutdown_hits = 0
        self.panic_hits = 0

    def reload(self):
        self.reload_hits += 1

    def shutdown(self):
        self.shutdown_hits += 1

    def panic(self):
        self.panic_hits += 1

    def hits(self):
        return (self.reload_hits, self.shutdown_hits, self.panic_hits)

class TestSignalListener:
    def setup(self):
        self.fakesignal = FakeSignalModule()
        self.dumbprogram = DumbProgram()

        assert signals_module.signal == signal
        signals_module.signal = self.fakesignal

        self.signal_listener = SignalListener(self.dumbprogram)

    def teardown(self):
        assert signals_module.signal == self.fakesignal
        signals_module.signal = signal

    def test_setup_installs_handlers(self):
        self.signal_listener.setup()
        sigs = self.fakesignal.signals
        handle = self.signal_listener.handle
        assert len(sigs) == 3
        assert sigs[signal.SIGHUP] == handle
        assert sigs[signal.SIGTERM] == handle
        assert sigs[signal.SIGINT] == handle

    @raises(PausedManyTimes)
    def test_listen_calls_pause_repeatedly(self):
        self.signal_listener.listen()

    def test_handle_term_calls_shutdown(self):
        """handle(TERM|INT) calls shutdown"""
        self.signal_listener.handle(signal.SIGTERM, None)
        assert self.dumbprogram.hits() == (0, 1, 0)
        self.signal_listener.handle(signal.SIGINT, None)
        assert self.dumbprogram.hits() == (0, 2, 0)

    def test_handle_hup_calls_reload(self):
        """handle(HUP) calls reload"""
        self.signal_listener.handle(signal.SIGHUP, None)
        assert self.dumbprogram.hits() == (1, 0, 0)

    def check_method_checks_thread(self, method):
        assert threading.current_thread().name == "MainThread"
        threading.current_thread().name = "AnotherThread"

        try:
            raises(AssertionError)(method)()
        finally:
            threading.current_thread().name = "MainThread"

    def test_setup_checks_thread(self):
        self.check_method_checks_thread(self.signal_listener.setup)

    def test_listener_checks_thread(self):
        self.check_method_checks_thread(self.signal_listener.listen)
