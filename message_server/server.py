# Copyright 2010 (C) Daniel Richman
# Copyright 2010 (C) Adam Greig
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
Contains 'Server', the main messager_server class
"""

import sys
import inspect
from utils import dynamicloader
from sink import Sink, SimpleSink, ThreadedSink

class Server:
    def __init__(self):
        self.sinks = []

    def load(self, new_sink):
        """
        Loads the sink module specified by sink_name
        new_sink: can be a class object, or a string, e.g.,
                  "myprogram.sinks.my_sink", where myprogram.sinks
                  is a module and my_sink is a class inside that module
        """

        new_sink = dynamicloader.load(new_sink)
        dynamicloader.expectisclass(new_sink)
        dynamicloader.expectissubclass(new_sink, Sink)
        dynamicloader.expecthasmethod(new_sink, "setup")
        dynamicloader.expecthasmethod(new_sink, "message")

        fullnames = (dynamicloader.fullname(s.__class__) for s in self.sinks)
        new_sink_name = dynamicloader.fullname(new_sink)

        if new_sink_name in fullnames:
            raise ValueError("this sink is already loaded")

        sink = new_sink()
        self.sinks.append(sink)

    def find_sink(self, sink):
        # The easiest way is to just search for the name
        sink_name = dynamicloader.fullname(sink)

        for s in self.sinks:
            if dynamicloader.fullname(s.__class__) == sink_name:
                return s

        raise ValueError("sink not found")

    def unload(self, sink):
        """
        Opposite of load(); Removes sink from the server.
        sink must represent a class that has been loaded by a call to load().
        Just like load() this can accept a string instead of a class.
        """

        self.sinks.remove(self.find_sink(sink))

    def reload(self, sink):
        """
        Calls utils.dynamicloader.load(force_reload=True) on the sink,
        removes the old sink and adds a new object created from the result
        of the class reloading.
        """

        sink = self.find_sink(sink)
        self.sinks.remove(sink)
        new_sink = dynamicloader.load(sink.__class__, force_reload=True)
        self.load(new_sink)

    def push_message(self, message):
        for sink in self.sinks:
            sink.push_message(message)

