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

from habitat.main import options
from nose.tools import raises, with_setup
import sys
import os
import ConfigParser

default_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "habitat_default.cfg")
alternate_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "habitat_alternate.cfg")
invalid_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "habitat_invalid.cfg")
missing_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "habitat_missing.cfg")

assert options.parser.get_option("-f").default == "/etc/habitat/habitat.cfg"
options.parser.set_defaults(config_file=default_file)

class CaughtError(Exception):
    pass

class TestOptions:
    def test_optparse_is_setup_correctly(self):
        expect_options = [ ("-f", "--config-file"),
                           ("-c", "--couch") ]
        for (short, long) in expect_options:
            assert options.parser.get_option(short).get_opt_string() == long

    def create_config_file(self, name, value):
        config = ConfigParser.RawConfigParser()
        config.add_section("habitat")
        config.set("habitat", "couch", value)

        with open(name, "wb") as f:
            config.write(f)

    def test_get_options(self):
        self.create_config_file(default_file, "default")
        self.create_config_file(alternate_file, "altconfig")

        self.check_get_options(["-f", alternate_file], "altconfig")
        self.check_get_options(["-c", "cmdline"], "cmdline")
        self.check_get_options([], "default")
        self.check_get_options(["-c", "cmdline",
                                "-f", alternate_file], "cmdline")

    def test_invalid_config_file_fails(self):
        with open(invalid_file, "wb") as f:
            f.write("lolga\0rbage!&(*&\xff^$_(*&\r\r_)*\n(%0\n*(&()&(*&Adfh")

        self.check_get_options_fails(["-c", "irrelevant", "-f", invalid_file])

    def test_missing_config_file_fails(self):
        self.check_get_options_fails(["-c", "irrelevant", "-f", missing_file])

    def check_get_options(self, argv, expect):
        old_argv = sys.argv
        sys.argv = ["habitat"] + argv
        result = options.get_options()
        sys.argv = old_argv

        assert result.couch == expect

    def check_get_options_fails(self, argv):
        old_argv = sys.argv
        self.old_error = options.parser.error

        def new_error(string):
            raise CaughtError

        options.parser.error = new_error
        sys.argv = ["habitat"] + argv

        raises(CaughtError)(options.get_options)()

        options.parser.error = self.old_error
        sys.argv = old_argv
