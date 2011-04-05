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
The code in this module drives the "main" method

``bin/habitat`` simply does the following::

    import habitat
    habitat.main.Program().main()
"""

import sys
import os
import signal
import threading
import Queue
import errno
import logging
import optparse
import ConfigParser
import couchdbkit
import restkit.errors

import habitat
from habitat.message_server import Server
from habitat.sensor_manager import SensorManager
from habitat.http import SCGIApplication
from habitat.utils import crashmat

__all__ = ["get_options", "setup_logging", "Program", "SignalListener"]

logger = logging.getLogger("habitat.main")

usage = "%prog [options]"
version = "{0} {1}".format(habitat.__name__, habitat.__version__)
header = "{0} is {1}".format(habitat.__name__, habitat.__copyright__)

default_configuration_file = "/etc/habitat/habitat.cfg"
"""The default location to search for a configuration file"""

config_section = "habitat"
"""The section in the config file to search for options"""

# I would use optparse.set_defaults, but instead we need to have command
# line options, config file options, and defaults, overriding each
# other in that order.
default_options = {"couch_uri": None, "couch_db": None, "socket_file": None,
                   "log_stderr_level": "WARN", "log_file": None,
                   "log_file_level": None, "secret": None}

parser = optparse.OptionParser(usage=usage, version=version,
                               description=header)
parser.add_option("-f", "--config-file", metavar="CONFIG_FILE",
                  dest="config_file",
                  help="file from which other options may be read")
parser.add_option("-c", "--couch-uri", metavar="COUCH_URI",
                  dest="couch_uri",
                  help="couch server to connect to" +
                    " (http://username:password@host:port/)")
parser.add_option("-d", "--couch-db", metavar="COUCH_DATABASE",
                  dest="couch_db",
                  help="couch database to use")
parser.add_option("-s", "--socket", metavar="SCGI_SOCKET",
                  dest="socket_file",
                  help="scgi socket file to serve on")
parser.add_option("--secret", metavar="SECRET", dest="secret",
              help="secret used for signing hotfixes, best set in config file")
parser.add_option("-v", "--verbosity", metavar="LOG_STDERR_LEVEL",
                  dest="log_stderr_level",
                  help="minimum loglevel to print on stderr, options: " +\
                       "NONE, DEBUG, INFO, WARN, ERROR, CRITICAL")
parser.add_option("-l", "--log-file", metavar="LOG_FILE",
                  dest="log_file",
                  help="file name to send log messages to")
parser.add_option("-e", "--log-level", metavar="LOG_FILE_LEVEL",
                  dest="log_file_level",
                  help="minimum loglevel to log to file " + \
                       "(see verbosity for options)")

def get_options():
    """
    **get_options** reads command line options and a configuration file

    This function parses command line options, and reads a
    configuration file (which must be in the :py:mod:`ConfigParser`
    format).

    It will read default_configuration_file and will ignore any
    errors that occur while doing so, unless a different config
    file is specified at the command line (failures on an explicitly
    stated config file will raise an execption).

    Command line options have priority over options from a config file.
    """

    cmdline_options = get_options_cmdline()
    config_options = get_options_config(cmdline_options["config_file"])
    del cmdline_options["config_file"]

    options = default_options.copy()

    for dest in default_options:
        if cmdline_options[dest] != None:
            options[dest] = cmdline_options[dest]
        elif dest in config_options and config_options[dest] != None:
            options[dest] = config_options[dest]

    get_options_check_required(options)

    for dest in ["log_stderr_level", "log_file_level"]:
        options[dest] = get_options_parse_log_level(options[dest])

    return options

def get_options_cmdline():
    (option_values, args) = parser.parse_args()

    if len(args) != 0:
        parser.error("did not expect any positional arguments")

    # A dict is arguably easier to use.
    cmdline_options = option_values.__dict__.copy()

    return cmdline_options

def get_options_config(config_file):
    if config_file == None:
        config_file = default_configuration_file
        config_file_explicit = False
    else:
        config_file_explicit = True

    config = ConfigParser.RawConfigParser()
    try:
        with open(config_file, "r") as f:
            config.readfp(f, config_file)
    except IOError, e:
        # If the error was in opening the default config file - not explicitly
        # set - then ignore it.
        if not config_file_explicit:
            return {}
        else:
            parser.error("error opening {0}: {1}".format(config_file, e))
    except ConfigParser.ParsingError, e:
        parser.error("error parsing {0}: {1}".format(config_file, e))
    else:
        return dict(config.items(config_section))

def get_options_check_required(options):
    required_options = ["couch_uri", "couch_db", "socket_file", "secret"]

    if options["log_file"] != None or options["log_file_level"] != None:
        required_options += ["log_file", "log_file_level"]

    for dest in required_options:
        if options[dest] == None or options[dest] == "":
            parser.error("\"{0}\" was not specified".format(dest))

# I would use the "choice" type for parser and have it validate
# these options, but we also need to check options provided in a
# config file, and add a "NONE" option
LOG_LEVELS = ["CRITICAL", "ERROR", "WARN", "INFO", "DEBUG"]
NONE_LEVELS = ["NONE", "SILENT", "QUIET"]

def get_options_parse_log_level(level):
    if level == None:
        return None

    level = level.upper()

    if level in NONE_LEVELS:
        return None
    elif level in LOG_LEVELS:
        return getattr(logging, level)
    else:
        parser.error("invalid value for \"{0}\"".format(levelarg))

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

    if log_stderr_level != None:
        stderr_handler = logging.StreamHandler()
        stderr_handler.setFormatter(logging.Formatter(formatstring))
        stderr_handler.setLevel(log_stderr_level)
        root_logger.addHandler(stderr_handler)
        have_handlers = True

    if log_file_level != None:
        file_handler = logging.FileHandler(log_file_name)
        file_handler.setFormatter(logging.Formatter(formatstring))
        file_handler.setLevel(log_file_level)
        root_logger.addHandler(file_handler)
        have_handlers = True

    if not have_handlers:
        # logging gets annoyed if there isn't atleast one handler.
        # If we're meant to be totally silent...
        root_logger.addHandler(logging.NullHandler())

    logger.info("Log initalised")

def couch_connect(couch_uri, couch_db):
    couch = couchdbkit.Server(couch_uri)
    db = couch[couch_db]

    try:
        # Quickly check that we can access this database
        db.info()
    except restkit.errors.ResourceError:
        raise Exception("Could not connect to the CouchDB database")

    return db

class Program(object):
    """
    Program provides the :py:meth:`main`, :py:meth:`shutdown` and \
    :py:meth:`reload` methods
    """

    (RELOAD, SHUTDOWN) = range(2)

    def __init__(self):
        self.queue = Queue.Queue()
        self.completed_logging_setup = False

    def main(self):
        """
        The main method of habitat

        This method does the following:

        * calls :py:func:`get_options`
        * calls :py:func:`setup_logging` with appropriate arguments
        * creates the CouchDB connection object and tests for connectivity
        * creates a :py:class:`habitat.message_server.Server`
        * creates a :py:class:`habitat.http.SCGIApplication`
        * creates a :py:class:`SignalListener`
        * starts the SCGI app thread
        * starts the Program thread (see :py:meth:`Program.run`)
        * starts the SignalListener thread

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

        # After this point, threads are created and catching & killing
        # the program is harder: crashmat.panic must be used.
        # SystemExit should not be raised by the MainThread.
        try:
            logger.debug("habitat: starting up")
            self.main_execution()
            logger.debug("main_execution finished gracefully")
        except:
            logger.exception("uncaught exception in main_execution, panic!")
            crashmat.panic()

        self.thread.join()
        logger.info("habitat: main() returning gracefully")

    def main_setup(self):
        self.options = get_options()
        setup_logging(self.options["log_stderr_level"],
                      self.options["log_file"],
                      self.options["log_file_level"])
        self.completed_logging_setup = True
        self.db = couch_connect(self.options['couch_uri'],
                                self.options['couch_db'])
        self.sensor_manager = SensorManager(self)
        self.server = Server(self)
        self.scgiapp = SCGIApplication(self.server, self,
                                       self.options["socket_file"])
        self.signallistener = SignalListener(self)
        self.signallistener.setup()
        self.thread = crashmat.Thread(target=self.run,
                                      name="Shutdown Handling Thread")
        crashmat.set_shutdown_function(self.shutdown)

    def main_execution(self):
        self.server.start()
        self.scgiapp.start()
        self.thread.start()

        # This will never return until habitat shuts down
        self.signallistener.listen()

    def reload(self):
        """asks the Program thread to process a **RELOAD** event"""
        self.queue.put(Program.RELOAD)

    def shutdown(self):
        """asks the Program thread to process a **SHUTDOWN** event"""
        self.queue.put(Program.SHUTDOWN)

    def run(self):
        """
        The Program thread processes **SHUTDOWN** and **RELOAD** events

        In order to make :py:meth:`shutdown` and :py:meth:`reload`
        return instantly, the actual work requested by calling those
        methods is done by this thread.

        * **RELOAD**: To be implemented
        * **SHUTDOWN**: shuts down the :py:class:`SignalListener`,
          :py:class:`habitat.http.SCGIApplication` and the
          :py:class:`habitat.message_server.Server`, then returns,
          killing this thread (``Program.thread``).
          Having shut down the above three, there should be only two
          threads executing: MainThread, which will be blocked in
          ``Program.thread.join()``, and this thread. Therefore,
          immediately after this function returns, the process exits.

        """

        while True:
            item = self.queue.get()

            if item == Program.SHUTDOWN:
                logger.info("Graceful shutdown initiated")

                self.signallistener.exit()
                self.scgiapp.shutdown()
                self.server.shutdown()
                self.db.ensure_full_commit()
                self.db.close()
                return
            elif item == Program.RELOAD:
                # TODO: Reload support
                pass

class SignalListener(object):
    """
    This class listens for signals

    It responds to the following signals. When it receives one, it
    calls the appropriate method of Program

    The documentation for the :py:mod:`signal` module contains
    information on the various signal constant definitions.

    * **SIGTERM**, **SIGINT**: calls :py:meth:`Program.shutdown`
    * **SIGHUP**: calls :py:meth:`Program.reload`
    * **SIGUSR1**: exits the :py:meth:`listen` loop by
      calling :py:func:`sys.exit` / raising
      :py:exc:`SystemExit <exceptions.SystemExit>`
      (NB: the :py:meth:`listen` loop will be running in **MainThread**)

    **SIGUSR1** is meant for internal use only, and is
    used to terminate the signal-listening thread when the program wishes
    to shut down.
    (see :py:meth:`SignalListener.exit`)
    """

    signals = []
    signal_names = {}

    for signame in ["SIGTERM", "SIGINT", "SIGHUP", "SIGUSR1"]:
        signum = getattr(signal, signame)
        signals.append(signum)
        signal_names[signum] = signame
    del signame, signum

    def __init__(self, program):
        self.program = program
        self.shutdown_event = threading.Event()

    def check_thread(self):
        assert threading.current_thread().name == "MainThread"

    def setup(self):
        """
        **setup()** installs signal handlers for the signals that we want

        Must be called in the **MainThread**
        """

        self.check_thread()

        for signum in self.signals:
            signal.signal(signum, self.handle)

    def listen(self):
        """
        **listen()** listens for signals delivered to the process forever

        It calls :py:func:`signal.pause` indefinitely, meaning that
        any signal sent to the process can be caught instantly and
        unobtrusivly.

        Must be called in the **MainThread**
        """

        self.check_thread()

        try:
            while True:
                signal.pause()
        except SystemExit:
            self.shutdown_event.set()

    def exit(self):
        """
        **exit()** terminates the :py:meth:`listen` loop

        It raises **SIGUSR1** in this process, causing
        the infinite listen() loop to exit
        (:py:meth:`SignalListener.handle` will call
        :py:func:`sys.exit`)
        """

        os.kill(os.getpid(), signal.SIGUSR1)
        self.shutdown_event.wait()

    def handle(self, signum, stack):
        """handles a received signal"""

        if signum != signal.SIGUSR1:
            logger.info("Handling signal #{num} ({name})"
                .format(num=signum, name=self.signal_names[signum]))
        else:
            logger.debug("Handling signal listener exit signal, SIGUSR1")

        if signum == signal.SIGTERM or signum == signal.SIGINT:
            self.program.shutdown()
        elif signum == signal.SIGHUP:
            self.program.reload()
        elif signum == signal.SIGUSR1:
            sys.exit()
