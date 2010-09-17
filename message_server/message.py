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

    RECEIVED_TELEM, LISTENER_INFO, LISTENER_TELEM, TELEM = types = range(4)

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

class Listener:
    """
    A Listener objects describes the source from which a message came, by some
    means. The majority of this class is yet to be implemented.
    Once initialised, the identifier is then available as listener.identifier
    """

    def __init__(self, identifier):
        """
        Creates a Listener object
        identifier: to be implemeted. Can be anything that can be compared 
        using __eq__ and should be the same value for the same listener.
        """

        self.identifier = identifier

    def __eq__(self, other):
        return self.identifier == other.identifier

    # compare requests other than __eq__ - we do our best:
    def __cmp__(self, other):
        return self.identifier.__cmp__(other.identifier)

class Validator:
    """
    Parent class of TypeValidator and TypesValidator, which are function
    decorators that ensure that the argument passed to the function passes
    Message.validate_type(type)
    """

    def __init__(self, func):
        self.func = func

class TypeValidator(Validator):
    """
    A function decorator that ensures that when the function is called the
    single argument passes Message.validate_type(type)
    """

    def __call__(self, type):
        Message.validate_type(type)
        self.func(type)

class TypesValidator(Validator):
    """
    A function decorator that ensures that when the function is called the
    single argument is a set, and every item of that set passes
    Message.validate_type(type)
    """

    def __call__(self, types):
        if not isinstance(types, (set, frozenset)):
            raise TypeError("types must be a set")

        for type in types:
            Message.validate_type(type)

        self.func(types)
