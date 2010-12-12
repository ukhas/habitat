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
The message server receives messages and pushes each message to one
or more 'sinks'.
"""

import sys
import inspect
import threading
import Queue
import ipaddr

from habitat.utils import dynamicloader

class Server:
    """
    The 'Server', the main messager_server class, is the class in which the
    magic happens. A Server manages the loading, unloading and reloading of
    'Sinks', and pushes messages to each and every sink when message() is
    called.
    """

    def __init__(self, config, program):
        self.config = config
        self.program = program

        self.sinks = []
        self.lock = threading.RLock()

    def load(self, new_sink):
        """
        Loads the sink module specified by sink_name
        new_sink: can be a class object, or a string, e.g.,
                  "myprogram.sinks.my_sink", where myprogram.sinks
                  is a module and my_sink is a class inside that module
        """

        new_sink = dynamicloader.load(new_sink)
        dynamicloader.expectisclass(new_sink)
        dynamicloader.expectissubclass(new_sink, Sink)
        dynamicloader.expecthasmethod(new_sink, "setup")
        dynamicloader.expecthasmethod(new_sink, "message")

        with self.lock:
            fullnames = (dynamicloader.fullname(s.__class__)
                         for s in self.sinks)
            new_sink_name = dynamicloader.fullname(new_sink)

            if new_sink_name in fullnames:
                raise ValueError("this sink is already loaded")

            sink = new_sink(self)
            self.sinks.append(sink)

    def find_sink(self, sink):
        with self.lock:
            # The easiest way is to just search for the name
            sink_name = dynamicloader.fullname(sink)

            for s in self.sinks:
                if dynamicloader.fullname(s.__class__) == sink_name:
                    return s

            raise ValueError("sink not found")

    def unload(self, sink):
        """
        Opposite of load(); Removes sink from the server.
        sink must represent a class that has been loaded by a call to load().
        Just like load() this can accept a string instead of a class.
        """

        with self.lock:
            sink = self.find_sink(sink)
            self.sinks.remove(sink)
            sink.shutdown()

    def reload(self, sink):
        """
        Calls utils.dynamicloader.load(force_reload=True) on the sink,
        removes the old sink and adds a new object created from the result
        of the class reloading.
        """

        with self.lock:
            sink = self.find_sink(sink)
            self.sinks.remove(sink)
            sink.shutdown()

            new_sink = dynamicloader.load(sink.__class__, force_reload=True)
            self.load(new_sink)

    def shutdown(self):
        with self.lock:
            for sink in self.sinks:
                sink.shutdown()

            self.sinks = []

    def push_message(self, message):
        with self.lock:
            for sink in self.sinks:
                sink.push_message(message)

class Sink:
    """
    'Sink' is the parent class for all sinks.

    To write a sink, have your sink class either inherit SimpleSink or
    ThreadedSink.

    All sinks have the following self-explanatory methods, all of which update
    the internal set of message-types which the sink wishes to receive.
    These functions are for use by the sink class.
        Sink.add_type(type), Sink.add_types(set([type, type, ...]))
        Sink.remove_type(type), Sink.remove_types(set([type, type, ...]))
        Sink.set_types(types), Sink.clear_types()

    They also will have the following functions, which are used internally by
    the message server
        Sink.__init__(server)
        Sink.push_message(message)
        Sink.flush()

    A sink must define these functions:
    setup(): called once; the sink must call some of the self.*type* functions
             in order to set up the set of types that the sink would like to
             receive
    message(message): called whenever a message is received for the sink to
                      process
    """

    def __init__(self, server):
        # NB: We can't reject a garbage server since doing so would require
        # circular-importing Server (since Server imports Sink)
        self.server = server
        self.types = set()
        self.setup()

    def add_type(self, type):
        Message.validate_type(type)
        self.types.add(type)

    def add_types(self, types):
        Message.validate_types(types)
        self.types.update(types)

    def remove_type(self, type):
        Message.validate_type(type)
        self.types.discard(type)

    def remove_types(self, types):
        Message.validate_types(types)
        self.types.difference_update(types)

    def clear_types(self):
        self.types.clear()

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

    def __init__(self, server):
        Sink.__init__(self, server)
        self.cv = threading.Condition()
        self.executing_count = 0

    def push_message(self, message):
        if not isinstance(message, Message):
            raise TypeError("message must be a Message object")

        if message.type in self.types:
            with self.cv:
                self.executing_count += 1

            self.message(message)

            with self.cv:
                self.executing_count -= 1
                self.cv.notify_all()

    def flush(self):
        with self.cv:
            while self.executing_count != 0:
                self.cv.wait()

    def shutdown(self):
        self.flush()

class ThreadedSink(Sink, threading.Thread):
    """
    The parent class of a sink that inherits ThreadedSink will execute
    message() exclusively in a thread for your Sink, and two calls to message
    will never occur simultaneously. It uses an internal Python Queue to
    achieve this. Therefore, the requirements of a SimpleSink do not apply.
    """

    def __init__(self, server):
        threading.Thread.__init__(self)
        self.name = "ThreadedSink runner: " + self.__class__.__name__

        Sink.__init__(self, server)
        self.queue = Queue.Queue()

        self.start()

    def push_message(self, message):
        if not isinstance(message, Message):
            raise TypeError("message must be a Message object")

        # Between get()ting items from the queue, self.types may change.
        # We should let run() filter for messages we want
        self.queue.put(message)

    def run(self):
        running = True
        while running:
            message = self.queue.get()

            if isinstance(message, Message):
                if message.type in self.types:
                    self.message(message)
            elif isinstance(message, ThreadedSinkShutdown):
                running = False

            self.queue.task_done()

    def flush(self):
        self.queue.join()

    def shutdown(self):
        self.queue.put(ThreadedSinkShutdown())
        self.flush()
        self.join()

class ThreadedSinkShutdown:
    """
    A object used to ask the runner of a ThreadedSink to shut down
    """
    pass

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
