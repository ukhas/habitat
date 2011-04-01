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
Tests the options component of the habitat "main" package; the component that
reads command line options and a configuration file to set up the couch
connection.
"""

import sys
import os
import errno
import logging
import ConfigParser

from nose.tools import raises

from habitat import main

from test_habitat import scratch_dir

default_file = os.path.join(scratch_dir, "habitat_default.cfg")
alternate_file = os.path.join(scratch_dir, "habitat_alternate.cfg")
invalid_file = os.path.join(scratch_dir, "habitat_invalid.cfg")
missing_file = os.path.join(scratch_dir, "habitat_missing.cfg")

class CaughtError(Exception):
    pass

class TestOptions:
    def setup(self):
        assert main.default_configuration_file == "/etc/habitat/habitat.cfg"
        main.default_configuration_file = default_file

    def teardown(self):
        assert main.default_configuration_file == default_file
        main.default_configuration_file = "/etc/habitat/habitat.cfg"

    def test_optparse_is_setup_correctly(self):
        expect_options = [("-f", "--config-file"),
                          ("-c", "--couch-uri"),
                          ("-d", "--couch-db"),
                          ("-s", "--socket"),
                          ("-v", "--verbosity"),
                          ("-l", "--log-file"),
                          ("-e", "--log-level")]

        for (short, long) in expect_options:
            assert main.parser.get_option(short).get_opt_string() == long

    def test_get_options(self):
        self.create_config_file(default_file,
            {"couch_uri": "http://habitat:password@localhost:5984",
             "couch_db": "habitat",
             "socket_file": "/tmp/habitat.sock",
             "secret": "file_secret",
             "log_stderr_level": "QUIET",
             "log_file": "/var/log/habitat",
             "log_file_level": "INFO"})

        self.create_config_file(alternate_file,
            {"couch_uri": "http://user:pass@example.com:1234",
             "couch_db": "rehab",
             "secret": "altfile_secret",
             "socket_file": "/var/run/habitat/sck"})

        # Test loading default config file
        self.check_get_options([],
            {"couch_uri": "http://habitat:password@localhost:5984",
             "couch_db": "habitat",
             "socket_file": "/tmp/habitat.sock",
             "secret": "file_secret",
             "log_stderr_level": None,
             "log_file": "/var/log/habitat",
             "log_file_level": logging.INFO})

        # Test loading config from an alternate file.
        self.check_get_options(["-f", alternate_file],
            {"couch_uri": "http://user:pass@example.com:1234",
             "couch_db": "rehab",
             "socket_file": "/var/run/habitat/sck",
             "secret": "altfile_secret",
             "log_stderr_level": logging.WARN,
             "log_file": None,
             "log_file_level": None})

        # Test config by command line options only
        self.check_get_options(
            ["-c", "cmdline_c", "-d", "cmdline_d", "-s", "cmdline_s",
              "--secret", "cmdline_secret", "-v", "DEBUG", "-l", "~/test",
              "-e", "ERROR"],
            {"couch_uri": "cmdline_c",
             "couch_db": "cmdline_d",
             "socket_file": "cmdline_s",
             "secret": "cmdline_secret",
             "log_stderr_level": logging.DEBUG,
             "log_file": "~/test",
             "log_file_level": logging.ERROR})

        # Test command line options override config options, which
        # override default options
        self.check_get_options(
            ["-c", "cmdline_c", "-l", "asdf", "-e", "DEBUG",
             "--secret", "cmdline_override_secret", "-f", alternate_file],
            {"couch_uri": "cmdline_c",
             "couch_db": "rehab",
             "socket_file": "/var/run/habitat/sck",
             "secret": "cmdline_override_secret",
             "log_stderr_level": logging.WARN,
             "log_file": "asdf",
             "log_file_level": logging.DEBUG})

    def test_invalid_config_file_fails(self):
        with open(invalid_file, "wb") as f:
            f.write("lolga\0rbage!&(*&\xff^$_(*&\r\r_)*\n(%0\n*(&()&(*&Adfh")

        self.check_get_options_fails(["-c", "irrelevant", "-f", invalid_file])

    def test_missing_config_file_fails(self):
        self.check_get_options_fails(["-c", "irrelevant", "-f", missing_file])

    def create_config_file(self, name, settings):
        config = ConfigParser.RawConfigParser()
        config.add_section("habitat")

        for (key, value) in settings.items():
            config.set("habitat", key, value)

        with open(name, "wb") as f:
            config.write(f)

    def check_get_options(self, argv, expect_options):
        old_argv = sys.argv
        sys.argv = ["habitat"] + argv
        result = main.get_options()
        sys.argv = old_argv

        assert result == expect_options

    def check_get_options_fails(self, argv):
        old_argv = sys.argv
        self.old_error = main.parser.error

        def new_error(string):
            raise CaughtError

        main.parser.error = new_error
        sys.argv = ["habitat"] + argv

        raises(CaughtError)(main.get_options)()

        main.parser.error = self.old_error
        sys.argv = old_argv

    def remove_default(self):
        try:
            os.unlink(default_file)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise

    def test_missing_default_file_does_not_fail(self):
        self.remove_default()

        # Test config by command line options only
        self.check_get_options(
            ["-c", "cmdline_c", "-d", "cmdline_d", "-s", "cmdline_s",
             "--secret", "cmdline_secret",
             "-v", "DEBUG", "-l", "~/test", "-e", "ERROR"],
            {"couch_uri": "cmdline_c",
             "couch_db": "cmdline_d",
             "socket_file": "cmdline_s",
             "secret": "cmdline_secret",
             "log_stderr_level": logging.DEBUG,
             "log_file": "~/test",
             "log_file_level": logging.ERROR})

        # Test default options for logging
        self.check_get_options(
            ["-c", "cmdline_c", "--secret", "cmdline_secret",
             "-d", "cmdline_d", "-s", "cmdline_s"],
            {"couch_uri": "cmdline_c",
             "couch_db": "cmdline_d",
             "socket_file": "cmdline_s",
             "secret": "cmdline_secret",
             "log_stderr_level": logging.WARN,
             "log_file": None,
             "log_file_level": None})

    def test_default_stderr_level_override(self):
        self.remove_default()

        for (level, expect) in [("NONE", None), ("ERROR", logging.ERROR)]:
            self.check_get_options(
                ["-c", "cmdline_c", "-d", "cmdline_d", "-s", "cmdline_s",
                 "--secret", "cmdline_secret", "-v", level],
                {"couch_uri": "cmdline_c",
                 "couch_db": "cmdline_d",
                 "socket_file": "cmdline_s",
                 "secret": "cmdline_secret",
                 "log_stderr_level": expect,
                 "log_file": None,
                 "log_file_level": None})

    def test_missing_explicitly_stated_default_file_does_fail(self):
        self.remove_default()
        self.check_get_options_fails(["-c", "irrelevant", "-f", default_file])

    def test_lack_of_compulsory_information_fails(self):
        flags = {"-c": "couch", "-s": "socket", "-d": "db"}
        self.remove_default()

        for i in flags.keys():
            self.check_missing_option_fails(flags, i)

    def test_log_file_without_level_fails(self):
        flags = {"-c": "couch", "-s": "socket", "--secret": "cmdline_secret",
                 "-l": "tmp", "-e": "DEBUG"}
        self.remove_default()

        for i in ["-l", "-e"]:
            self.check_missing_option_fails(flags, i)

    def check_missing_option_fails(self, flags, remove):
        new_flags = flags.copy()
        del new_flags[remove]

        argv = []
        for (f, v) in new_flags.items():
            argv.append(f)
            argv.append(v)

        self.check_get_options_fails(argv)

    def test_log_levels(self):
        levels = [("CRITICAL", logging.CRITICAL),
                  ("ERROR", logging.ERROR),
                  ("WARN", logging.WARN),
                  ("INFO", logging.INFO),
                  ("DEBUG", logging.DEBUG)]
        nlevels = ["QUIET", "SILENT", "NONE"]

        for (level, expect) in levels:
            self.check_log_level(level, expect)

    def check_log_level(self, level, expect):
        options = {"couch_uri": "c", "couch_db": "d", "socket_file": "s",
                   "secret": "cmdline_secret"}

        test = options.copy()
        test["log_stderr_level"] = level
        self.create_config_file(default_file, test)

        test = options.copy()
        test["log_stderr_level"] = expect
        test["log_file"] = None
        test["log_file_level"] = None
        self.check_get_options([], test)

        test = options.copy()
        test["log_stderr_level"] = "QUIET"
        test["log_file"] = "test"
        test["log_file_level"] = level
        self.create_config_file(default_file, test)

        test = options.copy()
        test["log_stderr_level"] = None
        test["log_file"] = "test"
        test["log_file_level"] = expect
        self.check_get_options([], test)

        self.remove_default()

        flags = ["-c", "c",
                 "-d", "d",
                 "--secret", "cmdline_secret",
                 "-s", "s"]

        test = options.copy()
        test["log_stderr_level"] = expect
        test["log_file"] = None
        test["log_file_level"] = None

        test_flags = flags + ["-v", level]

        self.check_get_options(test_flags, test)

        test = options.copy()
        test["log_stderr_level"] = logging.WARN
        test["log_file"] = "asdf"
        test["log_file_level"] = expect

        test_flags = flags + ["-l", "asdf", "-e", level]

        self.check_get_options(test_flags, test)
