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
The code in this module drives the "main" function itself, depending on the
sub-modules of habitat.main.
"""

import sys
import signal
import threading
import Queue

from habitat.message_server import Server
from habitat.http import SCGIApplication
from habitat.main.options import get_options
from habitat.main.signals import SignalListener

class Program:
    (RELOAD, SHUTDOWN) = range(2)

    def __init__(self):
        self.queue = Queue.Queue()

    def main(self):
        self.options = get_options()
        self.server = Server(None, self)
        self.scgiapp = SCGIApplication(self.server, self,
                                       self.options["socket_file"])
        self.signallistener = SignalListener(self)
        self.thread = threading.Thread(target=self.run,
                                       name="Shutdown Handling Thread")

        self.signallistener.setup()
        self.scgiapp.start()
        self.thread.start()

        self.signallistener.listen()

    def reload(self):
        self.queue.put(Program.RELOAD)

    def shutdown(self):
        self.queue.put(Program.SHUTDOWN)

    def panic(self):
        signal.alarm(60)
        self.shutdown()

    # run() does not require an item to terminate its thread. When shutdown
    # is called, after having cleaned up the Program.run() thread should be
    # the only one remaining, and it will then exit, killing the process.
    def run(self):
        while True:
            item = self.queue.get()

            if item == Program.SHUTDOWN:
                self.signallistener.exit()
                self.scgiapp.shutdown()
                self.server.shutdown()
                sys.exit()
            elif item == Program.RELOAD:
                pass
