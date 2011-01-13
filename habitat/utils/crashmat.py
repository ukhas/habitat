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
crashmat provides a replacement for :py:class:`threading.Thread` that,
instead of printing unhandled exceptions in threads and then quietly
killing it, will panic when a thread fails: it writes an error message to
the log, attempts to call a graceful shutdown function, but ultimatly
ensures that the process terminates (via :py:func:`signal.alarm`).
"""

import os
import signal
import threading
import logging

__all__ = ["Thread", "set_shutdown_function", "panic"]

shutdown_function = None

def set_shutdown_function(f):
    """Set a shutdown_function; see :py:func:`panic`"""
    global shutdown_function
    shutdown_function = f

def panic():
    """
    **panic()** attempts to terminate the python process completely.

    If a ``shutdown_function`` has been set via
    :py:func:`set_shutdown_function` then this function will call
    :py:func:`signal.alarm`, and then it will call the shutdown
    function. This has the effect that if the shutdown function fails
    to kill the programe cracefully, it will die anyway in 60 seconds.

    Otherwise, this function will simply raise SIGKILL, causing
    immediate death.
    """

    if shutdown_function == None:
        os.kill(os.getpid(), signal.SIGKILL)
    else:
        signal.alarm(60)
        shutdown_function()

# Classes are allowed to subclass threading.Thread and override run().
# For one example, see ThreadedSink.
# Overriding threading.__bootstrap would be vulnerable to breaking if
# the internal workings of Thread changed.
# Admittedly this is a bit hacky, but perhaps more resilient

logger = logging.getLogger("crashmat")

class Thread(threading.Thread):
    """
    A Thread class that kills the process in response to unhandled exceptions.

    This class behaves identically to :py:class:`threading.Thread`,
    with the exception that if there is an unhandled exception,
    :py:meth:`panic` will be called.
    """

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)

        # Incase a subclass of this class wants to override run(),
        # this replaces either threading.Thread.run() or a subclass' run().
        self.old_run = self.run
        self.run = self.new_run

    def new_run(self):
        try:
            self.old_run()
        except SystemExit:
            raise
        except:
            self.handle_exception()

    def handle_exception(self):
        """
        **handle_exception()** is called in response to an unhandled exception

        It will call :py:meth:`logging.Logger.exception` and then
        :py:func:`panic`
        """

        logger.exception("uncaught exception, killing process brutally")
        panic()
