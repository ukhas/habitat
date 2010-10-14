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
This module implements the high-level insert operations which will be called
by a {{f,s,}cgi,http} server.
"""

from message_server import Message, Listener
import threading

class InsertApplication:
    # We do not allow listeners to insert TELEM messages directly
    FORBIDDEN_TYPES = set([Message.TELEM])

    def __init__(self, server, program, config):
        self.server = server
        self.program = program
        self.config = config

    def push(self, ip, **kwargs):
        """
        Push Action
        ip: string - the IP address of the client

        Arguments should be supplied in **kwargs; the following three are
        required: "callsign", "type", "data". All are user supplied strings
        """

        # "superset" operation: requires every item in the second set to 
        # exist in the first.
        if not set(kwargs.keys()) >= set(["callsign", "type", "data"]):
            raise ValueError("required arguments: callsign, type, data")

        source = Listener(kwargs["callsign"], ip)

        if kwargs["type"] not in Message.type_names:
            raise ValueError("invalid type")

        type = getattr(Message, kwargs["type"])

        if type in self.FORBIDDEN_TYPES:
            raise ValueError("type forbidden for direct insertion")

        message = Message(source, type, kwargs["data"])

        self.server.push_message(message)

class FCGIApplication(InsertApplication):
    def start(self):
        pass

    def run(self):
        pass
