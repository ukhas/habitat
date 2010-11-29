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
The function here reads command line options and a configuration file to set
up the couch connection.
"""

import errno
import optparse
import ConfigParser

import habitat

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
