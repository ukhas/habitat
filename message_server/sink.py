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

To write a sink, have your sink class either inherit SimpleSink or
ThreadedSink.
"""

import Queue
import threading
from message import Message, TypeValidator, TypesValidator

class Sink:
    """
    All sinks have the following self-explanatory methods, all of which update
    the internal set of message-types which the sink wishes to receive.
    These functions are for use by the sink class.
        Sink.add_type(type), Sink.add_types(set([type, type, ...]))
        Sink.remove_type(type), Sink.remove_types(set([type, type, ...]))
        Sink.set_types(types), Sink.clear_types()

    They also will have the following function, which is used internally by
    the message server
        Sink.push_message(message)

    A sink must define these functions:
    setup(): called once; the sink must call some of the self.*type* functions
             in order to set up the set of types that the sink would like to
             receive
    message(message): called whenever a message is received for the sink to
                      process
    """

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
    """
    A sink that has SimpleSink as its parent class must have a message()
    function that conforms to some very strict criteria. It must:
      - be non blocking
      - be thread safe (however you can't use mutexes, these block)
      - tolerate multiple calls to message() by multiple threads,
        simultaneously
    If the sink wishes to place messages "back into" the server the it must
    tolerate recusrion (i.e., your message() function will indirectly call
    itself.
    """
    def push_message(self, message):
        if not isinstance(message, Message):
            raise TypeError("message must be a Message object")

        if message.type in self.types:
            self.message(message)

class ThreadedSink(Sink, threading.Thread):
    """
    The parent class of a sink that inherits ThreadedSink will execute
    message() exclusively in a thread for your Sink, and two cals to message
    will never occur simultaneously. It uses an internal Python Queue to
    achieve this. Therefore, the requirements of a SimpleSink do not apply.
    """

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
