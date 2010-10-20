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

import habitat
import optparse
import ConfigParser

usage = "%prog [-f config_file | -c couch_server]"
version = "{0} {1}".format(habitat.__name__, habitat.__version__)
header = "{0} is {1}".format(habitat.__name__, habitat.__copyright__)
default_configuration_file = "/etc/habitat/habitat.cfg"
config_section = "habitat"

parser = optparse.OptionParser(usage=usage, version=version,
                               description=header)
parser.add_option("-f", "--config-file", metavar="CONFIG_FILE",
                  dest="config_file", default=default_configuration_file,
                  help="file from which other options may be read")
parser.add_option("-c", "--couch", metavar="COUCH_SERVER",
                  dest="couch",
                  help="couch server to connect to")

def get_options():
    (options, args) = parser.parse_args()

    if len(args) != 0:
        parser.error("did not expect any positional arguments")

    config = ConfigParser.RawConfigParser()

    try:
        with open(options.config_file, "r") as f:
            config.readfp(f, options.config_file)
    except Exception, e:
        parser.error("couldn't load {0}: {1}".format(options.config_file, e))

    config_items = dict(config.items(config_section))
    destinations = [o.dest for o in parser.option_list
                    if o.dest != None and o.dest != "config_file"]

    for dest in destinations:
        if getattr(options, dest) == None and config_items.has_key(dest):
            setattr(options, dest, config_items[dest])

    return options
