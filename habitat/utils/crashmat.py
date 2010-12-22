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
ensures that the process terminates (via :py:meth:`signal.alarm`).
"""

import threading

__all__ = ["Thread"]

# Classes are allowed to subclass threading.Thread and override run().
# For one example, see ThreadedSink.
# Overriding threading.__bootstrap would be vulnerable to breaking if
# the internal workings of Thread changed.
# Admittedly this is a bit hacky, but perhaps more resilient

class Thread(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)

        # Incase a subclass of this class wants to override run(),
        # this replaces either threading.Thread.run() or a subclass' run().
        self.old_run = self.run
        self.run = self.new_run

    def new_run(self):
        try:
            self.old_run()
        except:
            self.handle_exception()

    def handle_exception(self):
        # traceback.format_exc()
        pass
