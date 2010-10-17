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

info_message = """
"habitat" is a web application for tracking the flight path of high altitude
balloons, relying on a network of users with radios sending in received
telemetry strings which are parsed into position information and displayed
on maps.

This is the information message from the HTTP gateway to habitat; a home page
of sorts. This web application is used to insert messages into the habitat
message server by HTTP post, and is not meant for direct use.

Source code, documentation, and more information:
http://github.com/ukhas/habitat
"""

class InsertApplication:
    """
    The InsertApplication class implements the high level functions provided
    by the http gateway, such as message().
    """

    # We do not allow listeners to insert TELEM messages directly
    FORBIDDEN_TYPES = set([Message.TELEM])

    # list of methods (below) that requests may call
    actions = ["message"]

    def __init__(self, server, program):
        """
        Creates a new InsertApplication
        server: message_server.Server object to insert items into
        program: object with shutdown() and panic() methods
        """

        self.server = server
        self.program = program

    def message(self, ip, **kwargs):
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
