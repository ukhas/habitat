# Copyright 2010 (C) Daniel Richman, Adam Greig
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
The code in this module drives the tests the "main" function itself. This
function spends most of its time calling functions in other modules in
habitat.main, so the tests are fairly boring.
"""

import sys
import os
import signal
import threading
import Queue
import logging

from nose.tools import raises

from habitat.utils.tests import threading_checks

from habitat.message_server import Server
from habitat.http import SCGIApplication
from habitat.main import Program, SignalListener, get_options, setup_logging, \
                         default_configuration_file
import habitat.main as program_module

# Replace get_options
old_get_options = get_options
def new_get_options():
    new_get_options.hits += 1
    return old_get_options()
new_get_options.hits = 0

# Make sure it doesn't read a configuration file
missing_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "habitat_missing.cfg")

# Replace setup_logging with a function that does nothing
def new_setup_logging(*args):
    new_setup_logging.calls.append(args)
new_setup_logging.calls = []

# A fake CouchDB database
class FakeCouchDatabase:
    def __init__(self, server_uri, database_name):
        self.server_uri = server_uri
        self.database_name = database_name
    def info(self):
        pass

# A fake CouchDB server interface
class FakeCouchServer:
    def __init__(self, uri):
        self.accessed_uri = uri
    def __getitem__(self, item):
        return FakeCouchDatabase(self.accessed_uri, item)
    
program_module.couchdbkit.Server = FakeCouchServer

# Replace the Server class with something that does nothing
dumbservers = []
class DumbServer:
    def __init__(self, program):
        self.program = program
        self.shutdown_hits = 0
        dumbservers.append(self)

    def shutdown(self):
        self.shutdown_hits += 1

# Replace SCGIApplication with something that does nothing
dumbscgiapps = []
class DumbSCGIApplication:
    def __init__(self, server, program, socket_file, timeout=1):
        self.server = server
        self.program = program
        self.socket_file = socket_file
        self.timeout = timeout
        self.start_hits = 0
        self.shutdown_hits = 0
        dumbscgiapps.append(self)

    def start(self):
        self.start_hits += 1

    def shutdown(self):
        self.shutdown_hits += 1

# Replace SignalListener with something that returns instantly. It is tested
# in its own unit test, and provided Program.main() calls it and
# Program.shutdown()/Program.reload() work, it's good.

# listen() will block, so it should be the last thing program calls.
# Therefore we raise this in listen; and check that it has been raised
# (and the test's asserts check things that have happened before it was
# raised)
class Listening(Exception):
    pass

dumbsignallisteners = []
class DumbSignalListener:
    def __init__(self, program):
        self.program = program
        self.setup_hits = 0
        self.listen_hits = 0
        self.exit_hits = 0
        dumbsignallisteners.append(self)

    def setup(self):
        self.setup_hits += 1

    def listen(self):
        self.listen_hits += 1
        raise Listening

    def exit(self):
        self.exit_hits += 1

# Replacement for run so we can keep track of the threads we spawn.
# Anything that tests main will want to replace run first; run is not replaced
# in setup() since it's the initialised object that must be modified
def new_run():
    new_run.queue.put(threading.current_thread())
new_run.queue = Queue.Queue()

class TestProgram:
    def setup(self):
        threading_checks.patch()

        # Do the replacing:
        assert program_module.default_configuration_file == \
               default_configuration_file
        assert program_module.get_options == get_options
        assert program_module.setup_logging == setup_logging
        assert program_module.Server == Server
        assert program_module.SCGIApplication == SCGIApplication
        assert program_module.SignalListener == SignalListener
        program_module.default_configuration_file = missing_file
        program_module.get_options = new_get_options
        program_module.setup_logging = new_setup_logging
        program_module.Server = DumbServer
        program_module.SCGIApplication = DumbSCGIApplication
        program_module.SignalListener = DumbSignalListener

        # Clear the list, reset the counter
        new_get_options.hits = 0
        dumbservers[:] = []
        dumbscgiapps[:] = []
        dumbsignallisteners[:] = []

        # Replace argv
        self.old_argv = sys.argv
        self.new_argv = ["habitat", "-c", "couchserver", "-d", "database",
                         "-s", "socketfile",
                         "-v", "WARN", "-l", "debugfile", "-e", "DEBUG"]
        sys.argv = self.new_argv

    def teardown(self):
        # Restore argv
        assert sys.argv == self.new_argv
        sys.argv = self.old_argv

        # Restore everything we replaced in setup()
        assert program_module.default_configuration_file == missing_file
        assert program_module.get_options == new_get_options
        assert program_module.setup_logging == new_setup_logging
        assert program_module.Server == DumbServer
        assert program_module.SCGIApplication == DumbSCGIApplication
        assert program_module.SignalListener == DumbSignalListener
        program_module.default_configuration_file = default_configuration_file
        program_module.get_options = get_options
        program_module.setup_logging = setup_logging
        program_module.Server = Server
        program_module.SCGIApplication = SCGIApplication
        program_module.SignalListener = SignalListener

        threading_checks.restore()

    def test_init(self):
        p = Program()
        assert isinstance(p.queue, Queue.Queue)

    def test_main(self):
        # Run main
        p = Program()
        p.run = new_run
        raises(Listening)(p.main)()

        # uses_options
        assert new_get_options.hits == 1

        # calls setup_logging correctly
        assert len(new_setup_logging.calls) == 1
        assert new_setup_logging.calls[0] == \
            (logging.WARN, "debugfile", logging.DEBUG)

        # connects to couch
        assert p.db.server_uri == "couchserver"
        assert p.db.database_name == "database"

        assert len(dumbservers) == 1
        assert dumbservers[0].program == p

        assert len(dumbscgiapps) == 1
        assert dumbscgiapps[0].program == p
        assert dumbscgiapps[0].server == dumbservers[0]
        assert dumbscgiapps[0].socket_file == "socketfile"
        assert dumbscgiapps[0].start_hits == 1

        assert len(dumbsignallisteners) == 1
        assert dumbsignallisteners[0].setup_hits == 1
        assert dumbsignallisteners[0].listen_hits == 1

        assert new_run.queue.get() == p.thread
        assert new_run.queue.qsize() == 0
        p.thread.join()

    def test_shutdown(self):
        p = Program()
        p.shutdown()
        assert p.queue.qsize() == 1
        assert p.queue.get() == Program.SHUTDOWN

    def test_reload(self):
        p = Program()
        p.reload()
        assert p.queue.qsize() == 1
        assert p.queue.get() == Program.RELOAD

    def test_shutdown_fullrun(self):
        p = Program()
        # We did not replace p.run, so a new thread will be started:
        raises(Listening)(p.main)()

        p.shutdown()
        p.thread.join()

        assert dumbsignallisteners[0].exit_hits == 1
        assert dumbscgiapps[0].shutdown_hits == 1
        assert dumbservers[0].shutdown_hits == 1

    # TODO: tests for main() split & proper error handling
    # (see todo in main.py)
    # - test main_setup creates no threads
    # - test errors in main_setup (before threads are created) are raised
    # - test errors after main_setup cause crashmat.panic()
