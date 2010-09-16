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

All types of sinks implement this function, which is called internally by the
message server
  Sink.push_message(message)

To write a sink, have your sink class either inherit SimpleSink or 
ThreadedSink.
  - SimpleSinks must be non blocking and thread safe (however can't use
    mutexes to achieve this since that would block. They must tolerate
    multiple calls to message() by multiple threads, simultaneously. If you
    want your sink to be able to place messages "back into" the server then
    it must tolerate recusrion
  - If your sink inherits ThreadedSink then the parent class will execute
    message() exclusively in a thread for your Sink, and two cals to message
    will never occur simultaneously. It uses an internal Python Queue to
    achieve this.

A sink must define these functions:
setup(): called once; the sink must call some of the self.*type* functions in
         order to set up the set of types that the sink would like to receive
message(message): called whenever a message is received for the sink to 
                  process
"""

import Queue
import threading
from message import Message, TypeValidator, TypesValidator

class Sink:
    def __init__(self):
        self.types = set()

        self.add_type = TypeValidator(self.types.add)
        self.add_types = TypesValidator(self.types.update)
        self.remove_type = TypeValidator(self.types.discard)
        self.remove_types = TypesValidator(self.types.difference_update)
        self.clear_types = self.types.clear

        self.setup()

    def set_types(self, types):
        self.clear_types()
        self.add_types(types)

class SimpleSink(Sink):
    def push_message(self, message):
        if not isinstance(message, Message):
            raise TypeError("message must be a Message object")

        if message.type in self.types:
            self.message(message)

class ThreadedSink(Sink, threading.Thread):
    def __init__(self):
        Sink.__init__(self)
        threading.Thread.__init__(self)
        self.daemon = True
        self.queue = Queue.Queue()
        self.start()

    def push_message(self, message):
        if not isinstance(message, Message):
            raise TypeError("message must be a Message object")

        # Between get()ting items from the queue, self.types may change.
        # We should let run() filter for messages we want
        self.queue.put(message)

    def run(self):
        while True:
            message = self.queue.get()

            if message.type in self.types:
                self.message(message)

            self.queue.task_done()
