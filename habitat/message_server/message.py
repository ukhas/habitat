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
Contains the 'Message' and 'Listener' classes.
"""

import ipaddr

class Message:
    """
    A Message object describes a single message that the server might handle

    After initialisation, the data is available in
        message.source
        message.type
        message.data

    The following message types are available:
        Message.RECEIVED_TELEM  - received telemetry string
        Message.LISTENER_INFO   - listener information
        Message.LISTENER_TELEM  - listener telemetry
        Message.TELEM           - (parsed) telemetry data
    """

    type_names = ["RECEIVED_TELEM", "LISTENER_INFO", "LISTENER_TELEM", "TELEM"]
    types = range(len(type_names))
    for (type, type_name) in zip(types, type_names):
        locals()[type_name] = type
    del type, type_name

    def __init__(self, source, type, data):
        """
        Create a new Message

        source: a Listener object
        type: one of the type constants
        data: a type-specific data object, which will be validated
        """
        # TODO data validation based on type

        if not isinstance(source, Listener):
            raise TypeError("source must be a Listener object")

        self.validate_type(type)

        self.source = source
        self.type = type
        self.data = data

    @classmethod
    def validate_type(cls, type):
        if not isinstance(type, int):
            raise TypeError("type must be an int")

        if type not in cls.types:
            raise ValueError("type is not a valid type")

    @classmethod
    def validate_types(cls, types):
        if not isinstance(types, (set, frozenset)):
            raise TypeError("types must be a set")

        for type in types:
            Message.validate_type(type)

class Listener:
    """
    A Listener objects describes the source from which a message came.
    It has two properties: callsign and ip. 'callsign' is chosen by the user
    that created the message, and must be alphanumeric and uppercase. It
    cannot be "trusted". 'ip' in typical usage is initalised by the server
    receiving the message (i.e., where it came from). When comparing two
    Listener objects (operator overloading), only callsign is considered.
    """

    def __init__(self, callsign, ip):
        """
        Creates a Listener object.
        callsign: string, must be alphanumeric
        ip: string, will be converted to an IP object
        """

        if not isinstance(callsign, (str, unicode)):
            raise TypeError("callsign must be a string")

        if not callsign.isalnum():
            raise ValueError("callsign must be alphanumeric")

        self.ip = ipaddr.IPAddress(ip)
        self.callsign = str(callsign).upper()

    def __eq__(self, other):
        try:
            return self.callsign == other.callsign
        except:
            return False
