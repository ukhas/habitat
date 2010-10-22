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
The code in this module drives the tests the "main" function itself. This
function spends most of its time calling functions in other modules in
habitat.main, so the tests are fairly boring.
"""

from habitat.main import Program, SignalListener
from habitat.main.options import get_options
from habitat.message_server import Server
from habitat.http import SCGIApplication
import habitat.main.program as program_module
from nose.tools import raises
import sys

# Replace get_options
old_get_options = get_options
def new_get_options():
    new_get_options.hits += 1
    return old_get_options()
new_get_options.hits = 0

# Replace the Server class with something that does nothing
dumbservers = []
class DumbServer:
    def __init__(self, config, program):
        self.config = config
        self.program = program
        dumbservers.append(self)

# Replace SCGIApplication with something that does nothing
dumbscgiapps = []
class DumbSCGIApplication:
    def __init__(self, server, program, socket_file, timeout=1):
        self.server = server
        self.program = program
        self.socket_file = socket_file
        self.timeout = timeout
        self.start_hits = 0
        dumbscgiapps.append(self)

    def start(self):
        self.start_hits += 1

# Replace signal with something that returns instantly. Signal is tested
# in its own unit test, and provided Program.main() calls it and
# Program.shutdown()/Program.reload()/Program.panic() work, it's good -
# the signal watching function isn't going to return in the real thing

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
        dumbsignallisteners.append(self)

    def setup(self):
        self.setup_hits += 1

    def listen(self):
        self.listen_hits += 1
        raise Listening

class TestProgram:
    def setup(self):
        # Do the replacing:
        assert program_module.get_options == get_options
        assert program_module.Server == Server
        assert program_module.SCGIApplication == SCGIApplication
        assert program_module.SignalListener == SignalListener
        program_module.get_options = new_get_options
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
        self.new_argv = ["habitat", "-c", "couchserver", "-s", "socketfile"]
        sys.argv = self.new_argv

    def teardown(self):
        # Restore argv
        assert sys.argv == self.new_argv
        sys.argv = self.old_argv

        # Restore options, Server, SCGIApplication
        assert program_module.get_options == new_get_options
        assert program_module.Server == DumbServer
        assert program_module.SCGIApplication == DumbSCGIApplication
        assert program_module.SignalListener == DumbSignalListener
        program_module.get_options = get_options
        program_module.Server = Server
        program_module.SCGIApplication = SCGIApplication
        program_module.SignalListener = SignalListener

    def test_main(self):
        # Run main
        p = Program()
        raises(Listening)(p.main)()

        # uses_options
        assert new_get_options.hits == 1

        # TODO:connects_to_couch

        assert len(dumbservers) == 1
        assert dumbservers[0].program == p
        # TODO:gives_server_correct_config_document

        assert len(dumbscgiapps) == 1
        assert dumbscgiapps[0].program == p
        assert dumbscgiapps[0].server == dumbservers[0]
        assert dumbscgiapps[0].socket_file == "socketfile"
        assert dumbscgiapps[0].start_hits == 1

        assert len(dumbsignallisteners) == 1
        assert dumbsignallisteners[0].setup_hits == 1
        assert dumbsignallisteners[0].listen_hits == 1
