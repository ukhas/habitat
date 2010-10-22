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
This class listens for signals forever and calls the appropriate methods
of Program when it receives one that it is looking for.
"""

import signal
import threading

class SignalListener:
    def __init__(self, program):
        self.program = program

    def check_thread(self):
        assert threading.current_thread().name == "MainThread"

    def setup(self):
        self.check_thread()

        for signum in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP]:
            signal.signal(signum, self.handle)

    def listen(self):
        self.check_thread()

        while True:
            signal.pause()

    def handle(self, signum, stack):
        if signum == signal.SIGTERM or signum == signal.SIGINT:
            self.program.shutdown()
        elif signum == signal.SIGHUP:
            self.program.reload()
