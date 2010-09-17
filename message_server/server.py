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

import inspect
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

        if not inspect.isclass(new_sink):
            new_sink = self.load_by_name(new_sink)

        if not (issubclass(new_sink, SimpleSink)
                or issubclass(new_sink, ThreadedSink)):
            raise ValueError(
                "sink must inherit from SimpleSink or ThreadedSink")

        methods = [method[0] for method in
            inspect.getmembers(new_sink, inspect.ismethod)]

        if 'setup' not in methods:
            raise ValueError("sink must implement setup()")
        if 'message' not in methods:
            raise ValueError("sink must implement message()")

        sink = new_sink()
        self.sinks.append(sink)

    def load_by_name(self, sink_name):
        if not isinstance(sink_name, basestring):
            raise TypeError("sink must be passed as a string or class")

        if len(sink_name) <= 0:
            raise ValueError("sink name must have non zero length")

        components = sink_name.split(".")

        if len(components) < 2:
            raise ValueError("sink name must have at least two components")

        if "" in components:
            raise ValueError("sink name contains empty components")

        module_name = ".".join(components[:-1])
        sink = __import__(module_name)

        for i in components[1:]:
            sink = getattr(sink, i)

        return sink

    def push_message(self, message):
        for sink in self.sinks:
            sink.push_message(message)

