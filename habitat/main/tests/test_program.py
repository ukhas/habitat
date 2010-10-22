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

from habitat.main import Program, get_options
from habitat.message_server import Server
from habitat.http import SCGIApplication
import habitat.main.program as program_module
import sys

# Replace get_options
old_get_options = get_options
def new_get_options():
    new_get_options.hits += 1
    return old_get_options()
new_get_options.hits = 0

assert program_module.get_options == get_options
program_module.get_options = new_get_options

# Replace the Server class with something that does nothing
dumbservers = []
class DumbServer:
    def __init__(self, config, program):
        self.config = config
        self.program = program
        dumbservers.append(self)

assert program_module.Server == Server
program_module.Server = DumbServer

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

assert program_module.SCGIApplication == SCGIApplication
program_module.SCGIApplication = DumbSCGIApplication

# Replace signal with something that returns instantly. Signal is tested
# in its own unit test, and provided Program.main() calls it and
# Program.shutdown()/Program.reload()/Program.panic() work, it's good -
# the signal watching function isn't going to return in the real thing
# TODO

class TestProgram:
    def setup(self):
        # Clear the list, reset the counter
        dumbservers[:] = []
        dumbscgiapps[:] = []
        new_get_options.hits = 0

        # Replace argv
        self.old_argv = sys.argv
        sys.argv = ["habitat", "-c", "couchserver", "-s", "socketfile"]

    def test_main(self):
        # Run main
        p = Program()
        p.main()

        # uses_options
        assert new_get_options.hits == 1

        # creates_message_server
        assert len(dumbservers) == 1

        # gives_message_server_program_object
        assert dumbservers[0].program == p

        # creates_scgi_application
        assert len(dumbscgiapps) == 1

        # gives_scgi_application_server_and_program_objects
        assert dumbscgiapps[0].program == p
        assert dumbscgiapps[0].server == dumbservers[0]

        # gives_scgi_application_socket_file
        assert dumbscgiapps[0].socket_file == "socketfile"

        # starts_scgi_server
        assert dumbscgiapps[0].start_hits == 1

        # connects_to_couch
        pass

        # gives_server_correct_config_document
        pass

    def teardown(self):
        # Restore argv
        sys.argv = self.old_argv
