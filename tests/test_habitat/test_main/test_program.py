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

from test_habitat import scratch_dir
from test_habitat.lib import threading_checks

from habitat.utils import crashmat
from habitat.utils.crashmat import set_shutdown_function, panic
from habitat.message_server import Server
from habitat.http import SCGIApplication
from habitat.main import Program, SignalListener, get_options, setup_logging, \
                         default_configuration_file
from habitat.sensor_manager import SensorManager
import habitat.main as program_module

# Replace get_options
def new_get_options():
    new_get_options.hits += 1
    return new_get_options.old()
new_get_options.old = get_options
new_get_options.hits = 0

# Make sure it doesn't read a configuration file
missing_file = os.path.join(scratch_dir, "habitat_missing.cfg")

# Replace setup_logging with a function that does nothing
def new_setup_logging(*args):
    new_setup_logging.calls.append(args)
new_setup_logging.calls = []

# Some classes must be initalised after the Program has connected to
# couch. Calling this function will check that couch is initalised
# when the object is created.
def check_couch(p):
    assert p.db.server_uri == "couchserver"
    assert p.db.database_name == "database"

# A fake CouchDB database
class FakeCouchDatabase:
    def __init__(self, server_uri, database_name):
        self.server_uri = server_uri
        self.database_name = database_name
        self.committed = False
        self.closed = False
    def info(self):
        pass
    def ensure_full_commit(self):
        self.committed = True
    def close(self):
        self.closed = True

# A fake CouchDB server interface
class FakeCouchServer:
    def __init__(self, uri):
        self.accessed_uri = uri
    def __getitem__(self, item):
        return FakeCouchDatabase(self.accessed_uri, item)

program_module.couchdbkit.Server = FakeCouchServer

# Replace the Server class with something that does nothing
class DumbServer:
    def __init__(self, program):
        self.program = program
        self.start_hits = 0
        self.shutdown_hits = 0
        check_couch(program)

    def start(self):
        self.start_hits += 1

    def shutdown(self):
        self.shutdown_hits += 1

# Replace the Sensor Manager class
class DumbSensorManager:
    def __init__(self, program):
        self.program = program
        check_couch(program)

# Replace SCGIApplication with something that does nothing
class DumbSCGIApplication:
    def __init__(self, server, program, socket_file, timeout=1):
        self.server = server
        self.program = program
        self.socket_file = socket_file
        self.timeout = timeout
        self.start_hits = 0
        self.shutdown_hits = 0

    def start(self):
        self.start_hits += 1

    def shutdown(self):
        self.shutdown_hits += 1

# Replace SignalListener with something that returns instantly. It is tested
# in its own unit test, and provided Program.main() calls it and
# Program.shutdown()/Program.reload() work, it's good.

# listen() will block, so it should be the last thing program calls.
# Therefore we raise this in listen; and check that it has been raised
# (therefore the test's asserts check things that have happened before it
# was raised)
# Note that for this to work we have to call main_execution() directly
# since main() wraps it in a try: except:
class Listening(Exception):
    pass

class DumbSignalListener:
    def __init__(self, program):
        self.program = program
        self.setup_hits = 0
        self.listen_hits = 0
        self.exit_hits = 0

    def setup(self):
        self.setup_hits += 1

    def listen(self):
        self.listen_hits += 1
        raise Listening

    def exit(self):
        self.exit_hits += 1

# A replacement for crashmat.set_shutdown_function
def new_set_shutdown_function(func):
    new_set_shutdown_function.funcs.append(func)
new_set_shutdown_function.funcs = []

def new_panic():
    new_panic.calls += 1
new_panic.calls = 0

# Replacement for run so we can keep track of the threads we spawn.
# Anything that tests main will want to replace run first; run is not replaced
# in setup() since it's the initialised object that must be modified
def new_run():
    new_run.queue.put(threading.current_thread())
new_run.queue = Queue.Queue()

# In order to test p.main() we replace main_setup, main_execution,
# and provide a fake p.thread
def action_nothing():
    pass
def action_raise():
    raise Exception
def action_sysexit():
    raise SystemExit

def new_main_setup():
    new_main_setup.calls += 1
    new_main_setup.action()
new_main_setup.calls = 0
new_main_setup.action = action_nothing

def new_main_execution():
    new_main_execution.calls += 1
    new_main_execution.action()
new_main_execution.calls = 0
new_main_execution.action = action_nothing

class DumbThread:
    def __init__(self):
        self.join_calls = 0
    def join(self):
        self.join_calls += 1

# p.main() does call some logging methods, so replace logging
class FakeLogging:
    for level in ["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]:
        locals()[level] = getattr(logging, level)
    del level

    def __init__(self):
        self.rt = self.Logger()
        self.hbt = self.Logger()

    def getLogger(self, name=None):
        if name == None:
            return self.rt
        elif name == "habitat.main":
            return self.hbt
        else:
            raise AssertionError

    class Logger:
        def __init__(self):
            self.exceptions = []
            self.handlers = []
        def exception(self, msg):
            self.exceptions.append( (msg, sys.exc_info()[0]) )
        def debug(self, msg):
            pass
        def info(self, msg):
            pass

class TestProgram:
    def setup(self):
        threading_checks.patch()

        # Do the replacing:
        assert program_module.default_configuration_file == \
               default_configuration_file
        assert program_module.get_options == get_options
        assert program_module.setup_logging == setup_logging
        assert program_module.Server == Server
        assert program_module.SensorManager == SensorManager
        assert program_module.SCGIApplication == SCGIApplication
        assert program_module.SignalListener == SignalListener
        assert crashmat.set_shutdown_function == set_shutdown_function
        assert crashmat.panic == panic
        assert program_module.logging == logging
        program_module.default_configuration_file = missing_file
        program_module.get_options = new_get_options
        program_module.setup_logging = new_setup_logging
        program_module.Server = DumbServer
        program_module.SensorManager = DumbSensorManager
        program_module.SCGIApplication = DumbSCGIApplication
        program_module.SignalListener = DumbSignalListener
        crashmat.set_shutdown_function = new_set_shutdown_function
        crashmat.panic = new_panic
        self.new_logging = FakeLogging()
        self.old_logger = program_module.logger
        program_module.logging = self.new_logging
        program_module.logger = self.new_logging.getLogger("habitat.main")

        # Clear the list, reset the counter, reset the functions
        new_get_options.hits = 0
        new_main_setup.action = action_nothing
        new_main_execution.action = action_nothing
        new_main_setup.calls = 0
        new_main_execution.calls = 0
        new_panic.calls = 0
        assert new_run.queue.qsize() == 0
        new_set_shutdown_function.funcs[:] = []

        # Replace argv
        self.old_argv = sys.argv
        self.new_argv = ["habitat", "-c", "couchserver", "-d", "database",
                         "-s", "socketfile", "--secret", "secret",
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
        assert program_module.SensorManager == DumbSensorManager
        assert program_module.SCGIApplication == DumbSCGIApplication
        assert program_module.SignalListener == DumbSignalListener
        assert crashmat.set_shutdown_function == new_set_shutdown_function
        assert crashmat.panic == new_panic
        assert program_module.logging == self.new_logging
        assert program_module.logger == self.new_logging.hbt
        program_module.default_configuration_file = default_configuration_file
        program_module.get_options = get_options
        program_module.setup_logging = setup_logging
        program_module.Server = Server
        program_module.SensorManager = SensorManager
        program_module.SCGIApplication = SCGIApplication
        program_module.SignalListener = SignalListener
        crashmat.set_shutdown_function = set_shutdown_function
        crashmat.panic = panic
        program_module.logging = logging
        program_module.logger = self.old_logger

        threading_checks.restore()

    def test_init(self):
        p = Program()
        assert isinstance(p.queue, Queue.Queue)

    def create_main_tester(self):
        p = Program()
        p.main_setup = new_main_setup
        p.main_execution = new_main_execution
        p.thread = DumbThread()
        return p

    def test_main_calls_setup_and_execution(self):
        p = self.create_main_tester()
        p.main()
        assert new_main_setup.calls == 1
        assert new_main_execution.calls == 1
        assert p.thread.join_calls == 1

        # Check that main_setup is called first.
        new_main_setup.action = action_sysexit
        raises(SystemExit)(p.main)()
        assert new_main_setup.calls == 2
        assert new_main_execution.calls == 1
        assert p.thread.join_calls == 1

    @raises(SystemExit)
    def test_main_reraises_setup_sysexit_despite_logging(self):
        new_main_setup.action = action_sysexit
        self.new_logging.rt.handlers.append(None)
        p = self.create_main_tester()
        assert p.completed_logging_setup == False
        p.completed_logging_setup = True
        p.main()

    @raises(Exception)
    def test_main_without_logging_reraises_setup_errors(self):
        new_main_setup.action = action_raise
        self.create_main_tester().main()

    def test_main_with_logging_calls_exception_on_setup_errors(self):
        expect_message = "uncaught exception in main_setup, exiting"
        new_main_setup.action = action_raise
        p = self.create_main_tester()
        assert p.completed_logging_setup == False
        p.completed_logging_setup = True
        p.main()
        assert len(self.new_logging.hbt.exceptions) == 1
        assert self.new_logging.hbt.exceptions[0] == \
            (expect_message, Exception)

    def test_main_panics_on_execution_errors(self):
        new_main_execution.action = action_raise
        self.check_panic_caused()

    def test_main_panics_on_execution_sysexit(self):
        new_main_execution.action = action_sysexit
        self.check_panic_caused()

    def check_panic_caused(self):
        self.create_main_tester().main()
        assert new_panic.calls == 1

    def test_main_setup_execution(self):
        """main_setup and main_execution"""
        p = Program()
        p.run = new_run

        # setup phase
        p.main_setup()

        # uses_options
        assert new_get_options.hits == 1

        # calls setup_logging correctly
        assert len(new_setup_logging.calls) == 1
        assert new_setup_logging.calls[0] == \
            (logging.WARN, "debugfile", logging.DEBUG)

        # connects to couch
        check_couch(p)

        # creates a server
        assert p.server.program == p
        assert p.server.start_hits == 0

        # creates a sensor manager
        assert p.sensor_manager.program == p

        # creates a scgiapp
        assert p.scgiapp.program == p
        assert p.scgiapp.server == p.server
        assert p.scgiapp.socket_file == "socketfile"
        assert p.scgiapp.start_hits == 0

        # creates a signal listener
        assert p.signallistener.setup_hits == 1
        assert p.signallistener.listen_hits == 0

        # creates a thread, but doesn't run it yet
        assert p.thread.is_alive() == False

        # calls set_shutdown_function
        assert len(new_set_shutdown_function.funcs) == 1
        assert new_set_shutdown_function.funcs[0] == p.shutdown

        # execution phase
        raises(Listening)(p.main_execution)()

        # starts the server, the scgiapp and calls listen
        assert p.server.start_hits == 1
        assert p.scgiapp.start_hits == 1
        assert p.signallistener.listen_hits == 1

        # starts p.thread
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
        # We did not replace p.run, so a new thread will be started.
        p.main_setup()
        raises(Listening)(p.main_execution)()
        p.shutdown()
        p.thread.join()

        assert p.signallistener.exit_hits == 1
        assert p.scgiapp.shutdown_hits == 1
        assert p.server.shutdown_hits == 1
        assert p.db.committed
        assert p.db.closed
