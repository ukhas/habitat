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
The parser sink is the interface between the message server and the
parser. It is responsible for receiving raw telemetry from the message
server, turning it into beautiful telemetry data, and then sending that
back.
"""

import inspect

from message_server import SimpleSink, Message

class ParserSink(SimpleSink):
    BEFORE_FILTER, DURING_FILTER, AFTER_FILTER = types = range(3)

    def setup(self):
        self.add_type(Message.RECEIVED_TELEM)
        self.before_filters = []
        self.during_filters = []
        self.after_filters = []

    def add_filter(self, location, filter):
        """
        Add a new filter to the Parser.
        location: when the filter should be run. one of
            ParserSink.BEFORE_FILTER, ParserSink.DURING_FILTER or
            ParserSink.AFTER_FILTER
        filter: a function (or a __call__able class) to run, with
            the single parameter message and which returns a message
        """
        
        if not hasattr(filter, '__call__'):
            raise TypeError("filter must be callable")

        # Inspect argument list based on type. Class __call__ methods will
        # have a self argument, so account for that.
        if inspect.isclass(filter):
            args = len(inspect.getargspec(filter.__call__).args) - 1
        elif inspect.isfunction(filter):
            args = len(inspect.getargspec(filter).args)
        else:
            raise TypeError("filter must be a class or a function")
        
        if args != 1:
            raise ValueError("filter must only take one argument")

        if location == self.BEFORE_FILTER:
            self.before_filters.append(filter)
        elif location == self.DURING_FILTER:
            self.during_filters.append(filter)
        elif location == self.AFTER_FILTER:
            self.after_filters.append(filter)

    def message(self, message):
        for filter in self.before_filters:
            message = filter(message)
        for filter in self.during_filters:
            message = filter(message)
        for filter in self.after_filters:
            message = filter(message)
