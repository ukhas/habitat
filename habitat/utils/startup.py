# Copyright 2011 (C) Daniel Richman
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

"""Useful functions for daemon startup"""

import sys
import logging
import yaml

logger = logging.getLogger("habitat.utils.startup")

def load_config():
    """
    loads the habitat config

    If a single argument is provided (sys.argv) then that yml file is used,
    otherwise './habitat.yml' is used.
    """

    if len(sys.argv) == 2:
        filename = sys.argv[1]
    elif len(sys.argv) <= 1:
        filename = "./habitat.yml"
    else:
        raise ValueError("Expected one command line argument only.")

    with open(filename) as f:
        config = yaml.load(f)

    return config

def _get_logging_level(config, key):
    if key not in config:
        return None

    value = config[key].upper()

    if value == "NONE":
        return None
    else:
        return getattr(logging, value)

class null_logger(logging.Handler):
    """a python logging handler that discards log messages silently"""
    def emit(self, record):
        pass

def setup_logging(config, daemon_name):
    """
    **setup_logging** initalises the :py:mod:`Python logging module <logging>`.

    It will initalise the 'habitat' logger and creates one, two, or no
    Handlers, depending on the values provided for *log_file_level* and
    *log_stderr_level* in **config**.
    """

    formatstring = "[%(asctime)s] %(levelname)s %(name)s %(threadName)s: " + \
                   "%(message)s"

    root_logger = logging.getLogger()

    # Enable all messages at the logger level, then filter them in each
    # handler.
    root_logger.setLevel(logging.DEBUG)

    # Bug pivotal:11844615, set restkit's level to WARNING to lower spam
    logging.getLogger("restkit").setLevel(logging.WARNING)

    have_handlers = False
    stderr_level = _get_logging_level(config, "log_stderr_level")
    file_level = _get_logging_level(config, "log_file_level")

    if stderr_level != None:
        stderr_handler = logging.StreamHandler()
        stderr_handler.setFormatter(logging.Formatter(formatstring))
        stderr_handler.setLevel(stderr_level)
        root_logger.addHandler(stderr_handler)
        have_handlers = True

    if file_level != None:
        file_name = config[daemon_name]["log_file"]
        file_handler = logging.FileHandler(file_name)
        file_handler.setFormatter(logging.Formatter(formatstring))
        file_handler.setLevel(file_level)
        root_logger.addHandler(file_handler)
        have_handlers = True

    if not have_handlers:
        # logging gets annoyed if there isn't atleast one handler.
        # If we're meant to be totally silent...
        root_logger.addHandler(null_logger())

    logger.info("Log initalised")

def main(main_class):
    """
    main function for habitat daemons. Loads config, sets up logging, and runs

    *main_class.__name__.lower()* will be used as the config sub section
    and passed as *daemon_name*.

    *main_class* specifies a class from which an object will be created.
    It will be initialised with arguments (config, daemon_name) and then
    the method run() of the object will be invoked.
    """
    config = load_config()
    daemon_name = main_class.__name__.lower()
    setup_logging(config, daemon_name)
    main_class(config, daemon_name).run()
