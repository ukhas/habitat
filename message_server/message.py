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
'Message' describes a single message that the server might handle,
and 'Listener' describes the source from which that message came, by some
means, though does not hold metadata about that listener, and indeed it is
not guaranteed (nor even is it expected) that there is one unique object
per listener.

'Message' has the following initialiser which assigns to the following
members:

my_message = Message(source, mtype, data)
where:
  source is a Listener object
  mtype is one of the type constants below
  data is a type-specific data object, which will be validated

The data is then available in
  message.source
  message.mtype
  message.data

Message types:
  Message.RX_STR - received telemetry string
  Message.LI_INF - listener information
  Message.LI_TLM - listener telemetry
  Message.TELEM  - (parsed) telemetry data

'Listener' has the following initialiser which assigns to the following
members:

my_listener = Listener(identifier)
where:
  identifier is to be implemented

The identifier is then available as Listener.identifier
"""

class Message:
    RX_STR, LI_INF, LI_TLM, TELEM = mtypes = range(4)

    def __init__(self, source, mtype, data):
        # TODO data validation based on type

        if not isinstance(source, Listener):
            raise TypeError("source must be a Listener object")

        if not isinstance(mtype, int):
            raise TypeError("mtype must be an int")

        if mtype not in self.mtypes:
            raise ValueError("mtype is not a valid type")

        self.source = source
        self.mtype = mtype
        self.data = data

class Listener:
    def __init__(self, identifier):
        self.identifier = identifier

    def __eq__(self, other):
        return self.identifier == other.identifier

    # compare requests other than __eq__ - we do our best:
    def __cmp__(self, other):
        return self.identifier.__cmp__(other.identifier)
