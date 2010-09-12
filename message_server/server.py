# Copyright 2010 (C) Daniel Richman
#
# This file is part of reHAB.
#
# reHAB is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# reHAB is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with reHAB.  If not, see <http://www.gnu.org/licenses/>.

"""
Contains 'Server', the main messager_server class
"""

import inspect
from sink import Sink

class Server:
    def __init__(self):
        self.sinks = []

    def load(self, new_sink):
        """
        Loads the sink module specified by sink_name
        sink_name: can be a class object, or a string, e.g.,
                   "myprogram.sinks.my_sink", where myprogram.sinks
                   is a module and my_sink is a class inside that module
        """

        if not inspect.isclass(new_sink):
            new_sink = self.load_by_name(new_sink)

        if not issubclass(new_sink, Sink):
            raise ValueError("new_sink must inherit message_server.Sink")

        sink = new_sink()
        self.sinks.append(sink)

    def load_by_name(self, sink_name):
        if not isinstance(sink_name, basestring):
            raise TypeError("sink_name must be a string")

        if len(sink_name) <= 0:
            raise ValueError("len(sink_name) must be > 0")

        components = sink_name.split(".")
        assert len(components) != 0

        if len(components) == 1:
            sink = globals()[sink_name]
        elif len(components) == 2:
            module_name = components[0]
            class_name = components[1]

            module = __import__(module_name)
            sink = getattr(module, class_name)
        else:
            parent_module = ".".join(components[:-2])
            module_name = ".".join(components[:-1])
            class_name = components[-1]

            module = __import__(module_name, fromlist=[parent_module])
            sink = getattr(module, class_name)

        return sink
