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
The message server pushes each received :py:class:`Message` to one
more :py:class:`Sinks <Sink>`.
"""

import sys
import inspect
import threading
import Queue
import ipaddr

from habitat.utils import dynamicloader

__all__ = ["Server", "Sink", "SimpleSink",
           "ThreadedSink", "Message", "Listener"]

class Server:
    """
    The **Server** is the main message server class.

    This is the class in which the magic happens. A Server manages the
    loading, unloading and reloading of 'Sinks', and pushes messages to
    each and every sink when message() is called.
    """

    def __init__(self, config, program):
        """
        *config*: the main configuration document for the **Server**

        *program*: a :py:class:`habitat.main.Program` object
        """

        self.config = config
        self.program = program

        self.sinks = []
        self.message_count = 0

        self.lock = threading.RLock()

    def load(self, new_sink):
        """
        Loads the specified sink

        *new_sink*: can be a class, or a string, e.g.,
        ``"myprogram.sinks.my_sink"``, where ``myprogram.sinks`` is a
        module and ``my_sink`` is a class inside that module
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
        """
        Locates a currently loaded sink in the **Server**

        *sink*: either the class, or the name of the class, of the sink
        to locate.
        """

        with self.lock:
            # The easiest way is to just search for the name
            sink_name = dynamicloader.fullname(sink)

            for s in self.sinks:
                if dynamicloader.fullname(s.__class__) == sink_name:
                    return s

            raise ValueError("sink not found")

    def unload(self, sink):
        """
        Opposite of :py:meth:`load`: Removes sink from the **Server**.

        *sink*: either the class, or the name of a class that has been
        loaded by a call to :py:meth:`load`
        """

        with self.lock:
            sink = self.find_sink(sink)
            self.sinks.remove(sink)
            sink.shutdown()

    def reload(self, sink):
        """
        Uses :py:func:`habitat.utils.dynamicloader.load` \
        (with ``force_reload=True``) to reload a sink

        This function removes the old sink and adds a new object
        created from the result of the class reloading.

        *sink*: either the class, or the name of a class that has been
        loaded by a call to :py:meth:`load`
        """

        with self.lock:
            sink = self.find_sink(sink)
            self.sinks.remove(sink)
            sink.shutdown()

            new_sink = dynamicloader.load(sink.__class__, force_reload=True)
            self.load(new_sink)

    def shutdown(self):
        """
        Shuts down the Server

        This function calls :py:meth:`Sink.shutdown` on every
        :py:class:`Sink` currently loaded, and then empties the list of
        loaded sink
        """

        with self.lock:
            for sink in self.sinks:
                sink.shutdown()

            self.sinks = []

    def push_message(self, message):
        """
        Pushes a message to all sinks loaded in the server

        *message*: a :py:class:`habitat.message_server.Message` object
        """

        if not isinstance(message, Message):
            raise TypeError("message must be a Message object")

        with self.lock:
            self.message_count += 1

            for sink in self.sinks:
                sink.push_message(message)

    def __repr__(self):
        """
        Concisely describes the current state of the **Server**

        This is primarily for help debugging from PDB or the python
        console.

        If another thread holds the internal server lock, then a string
        similar to ``<habitat.message_server.Server: locked>` is
        returned. Otherwise, something like
        ``<habitat.message_server.Server: 5 sinks loaded, \
        52 messages so far>`` is returned.
        """

        general_format = "<habitat.message_server.Server: %s>"
        locked_format = general_format % "locked"
        info_format = general_format % "%s sinks loaded, %s messages so far"

        acquired = self.lock.acquire(blocking=False)

        if not acquired:
            return locked_format

        try:
            return info_format % (len(self.sinks), self.message_count)
        finally:
            self.lock.release()

class Sink:
    """
    **Sink** is the parent class for all sinks.

    To write a sink, have your sink class either inherit from
    :py:class:`SimpleSink` or :py:class:`ThreadedSink`.

    All sinks have the following self-explanatory methods, all of which
    update the internal set of message-types which the sink wishes to
    receive. These functions are for use by the sink class.

     - **Sink.add_type**
     - **Sink.add_types**
     - **Sink.remove_type**
     - **Sink.remove_types**
     - **Sink.set_types**
     - **Sink.clear_types**

    They also will have the following functions, which are used
    internally by the message server

     - :py:meth:`Sink.push_message`
     - :py:meth:`Sink.flush`
     - :py:meth:`Sink.shutdown`

    A sink must define these functions:

     - **setup()**: called once; the sink must call some of the
       ``self.*type*`` functions in order to set up the set of types
       that the sink would like to receive
     - **message(message)**: called whenever a message is received for
       the sink to process

    """

    def __init__(self, server):
        """
        Sinks are automatically initialised by the
        :py:class:`habitat.message_server.Server` that is asked to
        load them.

        *server*: the :py:class:`Server` object that this
        :py:class:`Sink` is now receiving messages from
        """

        if not isinstance(server, Server):
            raise TypeError("server must be a Server object")

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

    def push_message(message):
        """
        Called by the server in order to pass a message to the **Sink**.

        This method is typically implemented by :py:class:`SimpleSink`
        or :py:meth:`ThreadedSink`. Filtering based on **Sink.types** is
        done by this method.
        """

        pass

    def flush():
        """
        Ensures that all current calls to :py:meth:`push_message` finish

        After calling **flush()**, provided that no calls to
        :py:meth:`push_message` are made in the meantime, no threads
        will be executing in this :py:class:`Sink`'s :py:meth:`push_message`
        method. The :py:class:`Server` has a lock to prevent messages
        from being pushed while flushing.
        """

        pass

    def shutdown():
        """
        Shuts down the :py:class:`Sink`

        This method flushes the sink, and then cleans up anything that
        was initalised in the **Sink**'s ``__init__`` method (for
        example, in :py:class:`ThreadedSink` it joins the thread).
        """
        pass

class SimpleSink(Sink):
    """
    A class for light weight, basic sinks to inherit

    A sink that has **SimpleSink** as its parent class must have a
    **message(message)** method that conforms to some very strict
    criteria.

    It must:

      - be non blocking
      - be thread safe (however you can't use mutexes, these block)
      - tolerate multiple calls to **message** by multiple threads,
        simultaneously

    If the sink wishes to place messages "back into" the server the it
    must tolerate recusrion (i.e., your **message** method will
    indirectly call itself.
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
    A class for sinks that need to execute in another thread to inherit

    The parent class of a sink that inherits **ThreadedSink** will execute
    message() exclusively in a thread for your Sink, and two calls to
    message will never occur simultaneously. It uses an internal
    Python :py:class:`Queue.Queue` to achieve this. Therefore, the
    requirements of a :py:class:`SimpleSink` do not apply.
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
    A object used to ask the runner of a :py:class:`ThreadedSink` \
    to shut down
    """
    pass

class Message:
    """
    A Message object describes a single message that the server might handle

    After initialisation, the data is available in

     - **message.source**
     - **message.type**
     - **message.data**

    The following message types are available:

     - **Message.RECEIVED_TELEM**: received telemetry string
     - **Message.LISTENER_INFO**: listener information
     - **Message.LISTENER_TELEM**: listener telemetry
     - **Message.TELEM**: (parsed) telemetry data

    """

    type_names = ["RECEIVED_TELEM", "LISTENER_INFO", "LISTENER_TELEM", "TELEM"]
    types = range(len(type_names))
    for (type, type_name) in zip(types, type_names):
        locals()[type_name] = type
    del type, type_name

    def __init__(self, source, type, data):
        """
        *source*: a Listener object

        *type*: one of the type constants

        *data*: a type-specific data object, which will be validated
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
        """Checks that type is an integer and a valid message type"""

        if not isinstance(type, int):
            raise TypeError("type must be an int")

        if type not in cls.types:
            raise ValueError("type is not a valid type")

    @classmethod
    def validate_types(cls, types):
        """Checks that types is a set of valid integer message types"""

        if not isinstance(types, (set, frozenset)):
            raise TypeError("types must be a set")

        for type in types:
            Message.validate_type(type)

class Listener:
    """
    A **Listener** object describes the source from which a message came.

    It has two attributes: *callsign* and *ip*. *callsign* is
    chosen by the user that created the message, and must be alphanumeric
    and uppercase. It cannot be "trusted". *ip* in typical usage is
    initalised by the server receiving the message (i.e., where it came
    from). When comparing two **Listener** objects (operator overloading),
    only *callsign* is considered.
    """

    def __init__(self, callsign, ip):
        """
        *callsign*: string, must be alphanumeric

        *ip*: string, which will be validated and converted to an
        **IPAddress** object (the ``ipaddr`` module)
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
