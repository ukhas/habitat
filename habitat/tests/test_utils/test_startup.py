# Copyright 2012 (C) Daniel Richman
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
Tests for habitat.utils.startup
"""

import sys
import tempfile
import mox
import smtplib
import copy
import logging
import os
import os.path

from ...utils import startup

_example_yaml = \
"""d: 4
blah: moo
o:
    listy:
       - 2
       - cow"""

_example_parsed = {"d": 4, "blah": "moo", "o": {"listy": [2, "cow"]}}

class TestLoadConfig(object):
    def setup(self):
        self.config = tempfile.NamedTemporaryFile()
        self.old_argv = sys.argv
        sys.argv = ["bin/something", self.config.name]

    def teardown(self):
        sys.argv = self.old_argv
        self.config.close()

    def test_works(self):
        self.config.write(_example_yaml)
        self.config.flush()
        assert startup.load_config() == _example_parsed

_logging_config = {
    "log_levels": {},
    "log_emails": {"to": ["addr_1", "addr_2"], "from": "from_bob",
                   "server": "email_server"},
    "mydaemon": {"log_file": "somewhere"}
}

class EqIfIn(mox.Comparator):
    """
    A mox comparator that is 'equal' to something if each of the provided
    arguments to the constructor is 'in' (as in python operator in) the
    right hand side of the equality
    """
    def __init__(self, *objs):
        self._objs = objs
    def equals(self, rhs):
        for obj in self._objs:
            if obj not in rhs:
                return False
        return True
    def __repr__(self):
        return "EqIfIn({0})".format(self._objs)

class TestSetupLogging(object):
    # Rationale for weird tests:
    # Mocking out the handlers and loggers would be a bit silly, since it
    # would just be rewriting startup.py line for line with mox. So these,
    # while a little dodgy in places, actually serve to test something.

    def setup(self):
        self.mocker = mox.Mox()
        self.config = copy.deepcopy(_logging_config)

        self.old_handlers = logging.root.handlers
        # nose creates its own handler
        logging.root.handlers = []

        # manual cleanup needed for check_file's tests
        self.temp_dir = None
        self.temp_files = []

    def teardown(self):
        self.mocker.UnsetStubs()

        # Reset logging
        for h in logging.root.handlers:
            h.close()
        logging.root.handlers = self.old_handlers

        if self.temp_files:
            for f in self.temp_files:
                try:
                    os.unlink(f)
                except:
                    pass

        if self.temp_dir:
            os.rmdir(self.temp_dir)

    def generate_log_messages(self):
        l = logging.getLogger("test_source")
        l.debug("Debug message TEST1")
        l.info("Info message TEST2")
        l.warning("Warning message TEST3")
        l.error("Error message TEST4")
        l.critical("Error message TEST5")
        def function_TEST6():
            raise ValueError("TEST7")
        try:
            function_TEST6()
        except:
            l.exception("Exception TEST8")

    def expected_messages(self, level, initialised=True):
        """
        returns, for each expected message, a tuple of strings that should
        be found in that message
        """
        if level <= logging.INFO and initialised:
            yield "Log initialised",
        if level <= logging.DEBUG:
            yield "TEST1",
        if level <= logging.INFO:
            yield "TEST2",
        if level <= logging.WARNING:
            yield "TEST3",
        if level <= logging.ERROR:
            yield "TEST4",
        if level <= logging.CRITICAL:
            yield "TEST5",
        if level <= logging.ERROR:
            # message must contain function name, exception arg, log msg
            yield "TEST6", "TEST7", "TEST8"

    levels = \
        [logging.CRITICAL, logging.ERROR, logging.WARNING,
         logging.INFO, logging.DEBUG]
    level_names = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]

    checks = zip(levels, level_names)

    def test_stderr(self):
        for a, b in self.checks:
            yield self.check_stderr, a, b

    def test_file(self):
        for a, b in self.checks:
            yield self.check_file, a, b

    def test_email(self):
        for a, b in self.checks:
            yield self.check_email, a, b

    def check_stderr(self, level, level_name):
        self.config["log_levels"]["stderr"] = level_name

        self.mocker.StubOutWithMock(sys, 'stdout')
        self.mocker.StubOutWithMock(sys, 'stderr')

        for things in self.expected_messages(level):
            sys.stderr.write(EqIfIn(*things))
            sys.stderr.flush()

        self.mocker.ReplayAll()

        startup.setup_logging(self.config, "mydaemon")
        self.generate_log_messages()

        self.mocker.VerifyAll()

    def check_file(self, level, level_name):
        # Mocks not used.
        self.mocker.ReplayAll()

        self.temp_dir = tempfile.mkdtemp()
        filename_a = os.path.join(self.temp_dir, "log_a")
        filename_b = os.path.join(self.temp_dir, "log_b")
        self.temp_files = [filename_a, filename_b]

        self.config["log_levels"]["file"] = level_name
        self.config["mydaemon"]["log_file"] = filename_a

        startup.setup_logging(self.config, "mydaemon")
        self.generate_log_messages()
        logging.getLogger("tests").critical("This should be in file b")

        # WatchedFileHandler, so should be able to move log file and it will
        # automatically write to new file at old name.
        os.rename(filename_a, filename_b)
        self.generate_log_messages()
        logging.getLogger("tests").critical("This should be in file a")

        # N.B.: It should flush after each message, so no need to close/flush
        with open(filename_a) as f:
            data_a = f.read()
        with open(filename_b) as f:
            data_b = f.read()

        for things in self.expected_messages(level, initialised=False):
            for match in things:
                assert match in data_a
        for things in self.expected_messages(level):
            for match in things:
                assert match in data_b

        assert "should be in file a" in data_a
        assert "should be in file b" in data_b

        self.mocker.VerifyAll()

    def check_email(self, level, level_name):
        self.config["log_levels"]["email"] = level_name

        # SMTPHandler uses smtplib
        self.mocker.StubOutClassWithMocks(smtplib, 'SMTP')

        for things in self.expected_messages(level):
            if sys.version_info >= (2, 7, 3):
                kwargs = {"timeout": 5.0}
            else:
                kwargs = {}
            smtp = smtplib.SMTP("email_server", 25, **kwargs)
            smtp.sendmail("from_bob", ["addr_1", "addr_2"], EqIfIn(*things))
            smtp.quit()

        self.mocker.ReplayAll()

        startup.setup_logging(self.config, "mydaemon")
        self.generate_log_messages()

        self.mocker.VerifyAll()

    def test_silent(self):
        self.mocker.StubOutWithMock(sys, 'stdout')
        self.mocker.StubOutWithMock(sys, 'stderr')
        # No output on std{err,out}

        self.mocker.ReplayAll()

        startup.setup_logging(self.config, "mydaemon")
        self.generate_log_messages()

        self.mocker.VerifyAll()

class TestMain(object):
    def setup(self):
        self.mocker = mox.Mox()

    def teardown(self):
        self.mocker.UnsetStubs()

    def test_works(self):
        self.mocker.StubOutWithMock(startup, 'load_config')
        self.mocker.StubOutWithMock(startup, 'setup_logging')

        main_class = self.mocker.CreateMockAnything()
        main_class.__name__ = "ExampleDaemon"

        main_object = self.mocker.CreateMockAnything()

        startup.load_config().AndReturn({"the_config": True})
        startup.setup_logging({"the_config": True}, "exampledaemon")
        main_class({"the_config": True}, "exampledaemon")\
                .AndReturn(main_object)
        main_object.run()

        self.mocker.ReplayAll()

        startup.main(main_class)

        self.mocker.VerifyAll()
