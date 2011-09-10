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
import logging

from nose.tools import raises

from ... import main

# Replace setup_logging with a function that does nothing
def new_setup_logging(*args):
    new_setup_logging.calls.append(args)
new_setup_logging.calls = []

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

class FakeParser:
    class parser:
        class Parser:
            def __init__(self, config):
                self.config = config
            def run(self):
                pass

class TestProgram:
    def setup(self):

        # Store old stuff
        self.main_setup_logging = main.setup_logging
        self.main_logging = main.logging
        self.main_parser = main.parser

        # Do the replacing:
        main.default_configuration_file = "/doesnt/exist"
        main.setup_logging = new_setup_logging
        main.parser = FakeParser()
        self.new_logging = FakeLogging()
        self.old_logger = main.logger
        main.logging = self.new_logging
        main.logger = self.new_logging.getLogger("habitat.main")

        # Clear the list, reset the counter, reset the functions
        new_main_setup.action = action_nothing
        new_main_setup.calls = 0

    def teardown(self):
        # Restore everything we replaced in setup()
        main.setup_logging = self.main_setup_logging
        main.logging = self.main_logging
        main.logger = self.old_logger
        main.parser = self.main_parser

    def create_main_tester(self):
        p = main.Program()
        p.main_setup = new_main_setup
        p.parser = FakeParser.parser.Parser('config')
        return p

    def test_main_calls_setup(self):
        p = self.create_main_tester()
        p.main()
        assert new_main_setup.calls == 1

        # Check that main_setup is called first.
        new_main_setup.action = action_sysexit
        raises(SystemExit)(p.main)()
        assert new_main_setup.calls == 2

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

    def test_main_setup_execution(self):
        """main_setup and main_execution"""
        p = main.Program()

        # setup phase
        p.main_setup()

        # calls setup_logging correctly
        assert len(new_setup_logging.calls) == 1

        # for this to work properly we have to be able to change
        # the config file main loads, which we can't do yet, so
        # the call will depend on config.yml, so don't test it
        #assert (new_setup_logging.calls[0] ==
            #(logging.WARN, "debugfile", logging.DEBUG))
