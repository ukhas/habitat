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
The code in this module drives the "main" method; it gets called when 
`habitat` is run.
"""

import sys
import os
import signal
import threading
import Queue
import errno
import optparse
import ConfigParser

import habitat
from habitat.message_server import Server
from habitat.http import SCGIApplication

usage = "%prog [-f config_file | -c couch_server]"
version = "{0} {1}".format(habitat.__name__, habitat.__version__)
header = "{0} is {1}".format(habitat.__name__, habitat.__copyright__)

default_configuration_file = "/etc/habitat/habitat.cfg"
config_section = "habitat"

parser = optparse.OptionParser(usage=usage, version=version,
                               description=header)
parser.add_option("-f", "--config-file", metavar="CONFIG_FILE",
                  dest="config_file",
                  help="file from which other options may be read")
parser.add_option("-c", "--couch", metavar="COUCH_SERVER",
                  dest="couch",
                  help="couch server to connect to")
parser.add_option("-s", "--socket", metavar="SCGI_SOCKET",
                  dest="socket_file",
                  help="scgi socket file to serve on")

def get_options():
    """
    get_options reads command line options and a configuration file to set
    up the couch connection.
    """

    (option_values, args) = parser.parse_args()

    if len(args) != 0:
        parser.error("did not expect any positional arguments")

    # A dict is arguably easier to use.
    options = option_values.__dict__.copy()

    # I would use optparse.set_defaults but we need to know whether
    # the option was explicitly stated
    if options["config_file"] == None:
        config_file = default_configuration_file
        config_file_explicit = False
    else:
        config_file = options["config_file"]
        config_file_explicit = True
    del options["config_file"]

    config = ConfigParser.RawConfigParser()
    try:
        with open(config_file, "r") as f:
            config.readfp(f, config_file)
    except IOError, e:
        # If the error was in opening the default config file - not explicitly
        # set - then ignore it.
        if config_file_explicit:
            parser.error("error opening {0}: {1}".format(config_file, e))
    except ConfigParser.ParsingError, e:
        parser.error("error parsing {0}: {1}".format(config_file, e))
    else:
        config_items = dict(config.items(config_section))
        for dest in options.keys():
            if options[dest] == None and config_items.has_key(dest):
                options[dest] = config_items[dest]

    for dest in options.keys():
        if options[dest] == None:
            parser.error("\"{0}\" was not specified".format(dest))

    return options

class Program:
    """
    The code in this class drives the "main" function itself
    """

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

class SignalListener:
    """
    This class listens for signals forever and calls the appropriate methods
    of Program when it receives one that it is looking for.

    It responds to the following signals:
     - SIGTERM, SIGINT: calls Program.shutdown()
     - SIGHUP: calls Program.reload()
     - SIGUSR1: exits the listen() loop by calling sys.exit/raising SystemExit
       (NB: the listen() loop will be running in MainThread)
    """

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
