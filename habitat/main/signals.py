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

It responds to the following signals:
 - SIGTERM, SIGINT: calls Program.shutdown()
 - SIGHUP: calls Program.reload()
 - SIGUSR1: exits the listen() loop by calling sys.exit/raising SystemExit
   (NB: the listen() loop will be running in MainThread)
"""

import sys
import os
import signal
import threading

class SignalListener:
    def __init__(self, program):
        self.program = program
        self.shutdown_event = threading.Event()

    def check_thread(self):
        assert threading.current_thread().name == "MainThread"

    def setup(self):
        """
        setup() installs signal handlers for the signals that we want to
        catch.

        Must be called in the MainThread
        """

        self.check_thread()

        for signum in [signal.SIGTERM, signal.SIGINT,
                       signal.SIGHUP, signal.SIGUSR1]:
            signal.signal(signum, self.handle)

    def listen(self):
        """
        listen() calls signal.pause() indefinitely, meaning that any
        signal sent to the process can be caught instantly and unobtrusivly
        (and without messing up someone's system call)

        Must be called in the MainThread
        """

        self.check_thread()

        try:
            while True:
                signal.pause()
        except SystemExit:
            self.shutdown_event.set()
            raise

    def exit(self):
        """
        exit() raises SIGUSR1 in this process, causing the infinite listen()
        loop to exit (the handler will call sys.exit())
        """
        os.kill(os.getpid(), signal.SIGUSR1)
        self.shutdown_event.wait()

    def handle(self, signum, stack):
        if signum == signal.SIGTERM or signum == signal.SIGINT:
            self.program.shutdown()
        elif signum == signal.SIGHUP:
            self.program.reload()
        elif signum == signal.SIGUSR1:
            sys.exit()
