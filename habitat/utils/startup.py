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
import logging.handlers
import yaml

logger = logging.getLogger("habitat.utils.startup")


def load_config():
    """
    Loads the habitat config.

    The path to the configuration YAML file can be specified as the single
    command line argument (read from ``sys.argv[1]``) or will default to
    ``./habitat.yml``.
    """

    if len(sys.argv) == 2:
        filename = sys.argv[1]
    elif len(sys.argv) <= 1:
        filename = "./habitat.yml"
    else:
        raise ValueError("Expected one command line argument only.")

    with open(filename) as f:
        config = yaml.safe_load(f)

    return config


def _get_logging_level(value):
    value = value.upper()

    if value == "NONE":
        return None
    else:
        return getattr(logging, value)


class null_logger(logging.Handler):
    """A python logging handler that discards log messages silently."""
    def emit(self, record):
        pass


_format_email = \
"""%(levelname)s from logger %(name)s (thread %(threadName)s)

Time:       %(asctime)s
Location:   %(pathname)s:%(lineno)d
Module:     %(module)s
Function:   %(funcName)s

%(message)s"""

_format_string = \
"[%(asctime)s] %(levelname)s %(name)s %(threadName)s: %(message)s"


def setup_logging(config, daemon_name):
    """
    **setup_logging** initalises the :py:mod:`Python logging module <logging>`.

    It will initalise the 'habitat' logger and creates one, two, or no
    Handlers, depending on the values provided for ``log_file_level`` and
    ``log_stderr_level`` in *config*.
    """

    root_logger = logging.getLogger()

    # Enable all messages at the logger level, then filter them in each
    # handler.
    root_logger.setLevel(logging.DEBUG)

    # Bug pivotal:11844615, set restkit's level to WARNING to lower spam
    logging.getLogger("restkit").setLevel(logging.WARNING)

    have_handlers = False
    levels = config["log_levels"]

    stderr_level = _get_logging_level(levels.get("stderr", "NONE"))
    file_level = _get_logging_level(levels.get("file", "NONE"))
    email_level = _get_logging_level(levels.get("email", "NONE"))

    if stderr_level != None:
        stderr_handler = logging.StreamHandler()
        stderr_handler.setFormatter(logging.Formatter(_format_string))
        stderr_handler.setLevel(stderr_level)
        root_logger.addHandler(stderr_handler)
        have_handlers = True

    if file_level != None:
        file_name = config[daemon_name]["log_file"]
        file_handler = logging.handlers.WatchedFileHandler(file_name)
        file_handler.setFormatter(logging.Formatter(_format_string))
        file_handler.setLevel(file_level)
        root_logger.addHandler(file_handler)
        have_handlers = True

    if email_level != None:
        emails_to = config["log_emails"]["to"]
        emails_from = config["log_emails"]["from"]
        email_server = config["log_emails"]["server"]
        if not isinstance(emails_to, list):
            emails_to = [emails_to]

        mail_handler = logging.handlers.SMTPHandler(
                email_server, emails_from, emails_to, daemon_name)
        mail_handler.setLevel(email_level)
        mail_handler.setFormatter(logging.Formatter(_format_email))
        root_logger.addHandler(mail_handler)
        have_handlers = True

    if not have_handlers:
        # logging gets annoyed if there isn't atleast one handler.
        # If we're meant to be totally silent...
        root_logger.addHandler(null_logger())

    logger.info("Log initialised")


def main(main_class):
    """
    Main function for habitat daemons. Loads config, sets up logging, and runs.

    ``main_class.__name__.lower()`` will be used as the config sub section
    and passed as *daemon_name*.

    *main_class* specifies a class from which an object will be created.
    It will be initialised with arguments (config, daemon_name) and then
    the method run() of the object will be invoked.
    """
    config = load_config()
    daemon_name = main_class.__name__.lower()
    setup_logging(config, daemon_name)
    main_class(config, daemon_name).run()
