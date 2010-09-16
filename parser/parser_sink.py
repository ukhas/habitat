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

from message_server import SimpleSink, Message

class ParserSink(SimpleSink):
    def setup(self):
        self.add_type(Message.RECEIVED_TELEM)

    def message(self):
        pass

