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
Tests the options component of the habitat "main" package; the component that
reads command line options and a configuration file to set up the couch
connection.
"""

import sys
import os
import errno
import ConfigParser

from nose.tools import raises

from habitat import main

default_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "habitat_default.cfg")
alternate_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "habitat_alternate.cfg")
invalid_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "habitat_invalid.cfg")
missing_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "habitat_missing.cfg")


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
        expect_options = [ ("-f", "--config-file"),
                           ("-c", "--couch-uri"),
                           ("-d", "--couch-db"),
                           ("-s", "--socket") ]
        for (short, long) in expect_options:
            assert main.parser.get_option(short).get_opt_string() == long

    def create_config_file(self, name, couch_db, couch_uri, socket_file):
        config = ConfigParser.RawConfigParser()
        config.add_section("habitat")
        config.set("habitat", "couch_db", couch_db)
        config.set("habitat", "couch_uri", couch_uri)
        config.set("habitat", "socket_file", socket_file)

        with open(name, "wb") as f:
            config.write(f)

    def test_get_options(self):
        self.create_config_file(default_file, "habitat",
            "http://habitat:password@localhost:5984", "/tmp/habitat.sock")
        self.create_config_file(alternate_file, "rehab",
            "http://user:pass@example.com:1234", "/var/run/habitat/sck")

        self.check_get_options(["-f", alternate_file],
            "http://user:pass@example.com:1234", "rehab",
            "/var/run/habitat/sck")
        self.check_get_options(["-c", "cmdline", "-d", "dcmdline", "-s",
            "scmdline"], "cmdline", "dcmdline", "scmdline")
        self.check_get_options([], "http://habitat:password@localhost:5984",
            "habitat", "/tmp/habitat.sock")
        self.check_get_options(["-c", "cmdline",
            "-f", alternate_file], "cmdline", "rehab",
            "/var/run/habitat/sck")

    def test_invalid_config_file_fails(self):
        with open(invalid_file, "wb") as f:
            f.write("lolga\0rbage!&(*&\xff^$_(*&\r\r_)*\n(%0\n*(&()&(*&Adfh")

        self.check_get_options_fails(["-c", "irrelevant", "-f", invalid_file])

    def test_missing_config_file_fails(self):
        self.check_get_options_fails(["-c", "irrelevant", "-f", missing_file])

    def check_get_options(self, argv, expect_c, expect_d, expect_s):
        old_argv = sys.argv
        sys.argv = ["habitat"] + argv
        result = main.get_options()
        sys.argv = old_argv

        assert result["couch_uri"] == expect_c
        assert result["couch_db"] == expect_d
        assert result["socket_file"] == expect_s

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
        self.check_get_options(["-c", "cmdline", "-d", "dcmdline",
            "-s", "scmdline"], "cmdline", "dcmdline", "scmdline")

    def test_missing_explicitly_stated_default_file_does_fail(self):
        self.remove_default()
        self.check_get_options_fails(["-c", "irrelevant", "-f", default_file])

    def test_lack_of_enough_information_fails(self):
        flags = {"-c": "couch", "-s": "socket", "-d": "db"}
        self.remove_default()

        for i in flags.keys():
            new_flags = flags.copy()
            del new_flags[i]

            argv = []
            for (f, v) in new_flags.items():
                argv.append(f)
                argv.append(v)

            self.check_get_options_fails(argv)
