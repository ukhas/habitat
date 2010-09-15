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
Contains 'Sink', the parent class for all sinks.

A 'Sink' has the following methods:
  update the internal list of message-types which the sink wishes to receive
    Sink.add_type(type), Sink.add_types(set([type, type, ...]))
    Sink.remove_type(type), Sink.remove_types(set([type, type, ...]))
    Sink.set_types(types), Sink.clear_types()

  called internally by the message server
    Sink.push_message(message)

Currently, a sink must inherit this class and in addition define these 
functions:
start(): called once; the sink must call some of the self.*type* functions in
         order to set up the set of types that the sink would like to receive
message(message): called whenever a message is received for the sink to 
                  process

Please note that multiple calls to message() may be made simultaneously by
different threads. Your message() function must not block!
"""

from message import Message

class Sink:
    def __init__(self):
        self.types = set()

        self.add_type = TypeValidator(self.types.add)
        self.add_types = TypesValidator(self.types.update)
        self.remove_type = TypeValidator(self.types.discard)
        self.remove_types = TypesValidator(self.types.difference_update)
        self.clear_types = self.types.clear

    def set_types(self, types):
        self.clear_types()
        self.add_types(types)


class Validator:
    def __init__(self, func):
        self.func = func

class TypeValidator(Validator):
    def __call__(self, type):
        Message.validate_type(type)
        self.func(type)

class TypesValidator(Validator):
    def __call__(self, types):
        if not isinstance(types, (set, frozenset)):
            raise TypeError("types must be a set")

        for type in types:
            Message.validate_type(type)

        self.func(types)
