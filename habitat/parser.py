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
The parser interprets incoming telemetry strings into useful telemetry data.
"""

import inspect

from habitat.message_server import SimpleSink, Message

__all__ = ["ParserSink", "ParserModule"]

class ParserSink(SimpleSink):
    """
    The Parser Sink

    The parser sink is the interface between the message server and the
    parser modules. It is responsible for receiving raw telemetry from the
    message server, giving it to modules which turn it into beautiful
    telemetry data, and then sending that back to the message server.
    """

    BEFORE_FILTER, DURING_FILTER, AFTER_FILTER = locations = range(3)

    def setup(self):
        self.add_type(Message.RECEIVED_TELEM)

        self.before_filters = []
        self.during_filters = []
        self.after_filters = []
        self.filters = {
            self.BEFORE_FILTER: self.before_filters,
            self.DURING_FILTER: self.during_filters,
            self.AFTER_FILTER: self.after_filters
        }

        self.modules = []


class ParserModule(object):
    """
    **ParserModules** are classes which turn radio strings into useful data.

    ParserModules

     - can be given various configuration parameters.
     - inherit from **ParserModule**.

    """

    pass
