# Copyright 2010, 2011 (C) Daniel Richman, Adam Greig
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
The code in this module drives the "main" method

``bin/habitat`` simply does the following::

    import habitat
    habitat.main.Program().main()
"""

import logging
import yaml
import os.path

from . import parser

__all__ = ["setup_logging", "Program", "null_logger"]

logger = logging.getLogger("habitat.main")

def setup_logging(log_stderr_level, log_file_name, log_file_level):
    """
    **setup_logging** initalises the :py:mod:`Python logging module <logging>`.

    It will initalise the 'habitat' logger and creates one, two, or no
    Handlers, depending on the values provided for *log_file_level* and
    *log_stderr_level*.
    """

    formatstring = "[%(asctime)s] %(levelname)s %(name)s %(threadName)s: " + \
                   "%(message)s"

    root_logger = logging.getLogger()

    # Enable all messages at the logger level, then filter them in each
    # handler.
    root_logger.setLevel(logging.DEBUG)

    # Bug pivotal:11844615, set restkit's level to WARNING to lower spam
    # Due to nosetests being very odd, restkit_logger and logger_warning
    #     are both nabbed at the top of this script and put into the global
    #     namespace. nose appears to overwrite logging with a FakeLogging
    #     module which lacks logging.WARNING and logging.getLogger(name)
    logging.getLogger("restkit").setLevel(logging.WARNING)

    have_handlers = False

    # TODO: check to ensure that log_*_level is valid.

    if log_stderr_level != None and log_stderr_level != "NONE":
        log_stderr_level = getattr(logging, log_stderr_level)

        stderr_handler = logging.StreamHandler()
        stderr_handler.setFormatter(logging.Formatter(formatstring))
        stderr_handler.setLevel(log_stderr_level)
        root_logger.addHandler(stderr_handler)
        have_handlers = True

    if log_file_level != None and log_file_level != "NONE":
        log_file_level = getattr(logging, log_file_level)

        file_handler = logging.FileHandler(log_file_name)
        file_handler.setFormatter(logging.Formatter(formatstring))
        file_handler.setLevel(log_file_level)
        root_logger.addHandler(file_handler)
        have_handlers = True

    if not have_handlers:
        # logging gets annoyed if there isn't atleast one handler.
        # If we're meant to be totally silent...
        root_logger.addHandler(null_logger())

    logger.info("Log initalised")

class Program(object):
    """
    Program provides the main method for habitat.
    """

    def __init__(self):
        self.completed_logging_setup = False

    def main(self):
        """
        The main method of habitat

        This method does the following:

        * calls :py:func:`setup_logging` with appropriate arguments
        * runs the parser
        """

        # Setup phase: before any threads are started.
        # We allow any execptions to raise and kill this thread - which
        # is the only thread - and therefore kill the program.
        try:
            self.main_setup()
            logger.debug("setup completed: habitat ready")
        except SystemExit:
            raise
        except:
            if self.completed_logging_setup:
                logger.exception("uncaught exception in main_setup, exiting")
                return
            else:
                raise

        try:
            logger.debug("habitat: starting up")
            self.parser.run()
            logger.debug("main_execution finished gracefully")
        except:
            logger.exception("uncaught exception in main_execution, panic!")
            raise

        logger.info("habitat: main() returning gracefully")

    def main_setup(self):
        base_path = os.path.split(os.path.abspath(__file__))[0]
        with open(os.path.join(base_path, "config.yml")) as f:
            self.options = yaml.load(f)
        setup_logging(self.options["log_stderr_level"],
                      self.options["log_file"],
                      self.options["log_file_level"])
        self.completed_logging_setup = True
        self.parser = parser.parser.Parser(self.options)

class null_logger(logging.Handler):
    """a python logging handler that discards log messages silently"""
    def emit(self, record):
        pass
