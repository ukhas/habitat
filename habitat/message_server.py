# Copyright 2010 (C) Daniel Richman, Adam Greig
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
import string
import inspect
import threading
import logging
import Queue
import ipaddr
import base64
import couchdbkit.exceptions
from copy import deepcopy

from habitat.utils import dynamicloader, crashmat

__all__ = ["Server", "Sink", "SimpleSink",
           "ThreadedSink", "Message", "Listener"]

logger = logging.getLogger("habitat.message_server")

class Server(object):
    """
    The **Server** is the main message server class.

    This is the class in which the magic happens. A Server manages the
    loading, unloading and reloading of 'Sinks', and pushes messages to
    each and every sink when message() is called.
    """

    def __init__(self, program):
        """
        *program*: a :py:class:`habitat.main.Program` object
        """

        self.program = program
        self.db = self.program.db

        self.sinks = []
        self.message_count = 0

        self.lock = threading.RLock()
        self.queue = Queue.Queue()
        self.thread = crashmat.Thread(name="Message Server Thread",
                                      target=self.run)

        try:
            self.config = self.db["message_server_config"]
        except couchdbkit.exceptions.ResourceNotFound:
            raise Exception("message_server_config couchdb document not found")

    def start(self):
        """
        Starts up the server.
        """

        with self.lock:
            self.thread.start()

            for sink in self.config['sinks']:
                self.load(sink)

            logger.info("Started Server with {num} sinks" \
                .format(num=len(self.sinks)))

    def load(self, new_sink):
        """
        Loads the specified sink

        *new_sink*: can be a class, or a string, e.g.,
        ``"myprogram.sinks.my_sink"``, where ``myprogram.sinks`` is a
        module and ``my_sink`` is a class inside that module
        """

        new_sink = dynamicloader.load(new_sink)
        dynamicloader.expectisclass(new_sink)
        dynamicloader.expecthasmethod(new_sink, "push_message")
        dynamicloader.expecthasmethod(new_sink, "shutdown")
        dynamicloader.expecthasmethod(new_sink, "flush")

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

    def run(self):
        running = True
        while running:
            message = self.queue.get()

            if (hasattr(message, "shutdown_notification") and
                    message.shutdown_notification == True):
                running = False
            else:
                with self.lock:
                    for sink in self.sinks:
                        sink.push_message(message)

                    self.message_count += 1

            self.queue.task_done()

    def push_message(self, message):
        """
        Pushes a message to all sinks loaded in the server

        This method will return instantly, having added the message object
        to an internal queue for processing by a thread.

        *message*: a :py:class:`habitat.message_server.Message` object
        """

        dynamicloader.expecthasattr(message, "type")
        dynamicloader.expecthasattr(message, "source")
        dynamicloader.expecthasattr(message, "data")
        self.queue.put(message)

    def flush(self):
        """
        Blocks until the internal queue of messages has been processed
        """

        self.queue.join()

    def shutdown(self):
        """
        Shuts down the Server

        This function calls :py:meth:`Sink.shutdown` on every
        :py:class:`Sink` currently loaded, and then empties the list of
        loaded sink
        """

        self.queue.put(ShutdownNotification())
        self.flush()
        self.thread.join()

        with self.lock:
            for sink in self.sinks:
                sink.shutdown()

            self.sinks = []

        logger.debug("Server shutdown complete")

    _repr_general_format = "<habitat.message_server.Server: {status}>"
    _repr_locked = _repr_general_format.format(status="locked")
    _repr_info = "{sinks} sinks loaded, {msgs} messages so far, " + \
                 "approx {qsz} queued"
    _repr_info_format = _repr_general_format.format(status=_repr_info)
    del _repr_general_format, _repr_info

    def __repr__(self):
        """
        Concisely describes the current state of the **Server**

        This is primarily for help debugging from PDB or the python
        console.

        If another thread holds the internal server lock, then a string
        similar to ``<habitat.message_server.Server: locked>`` is
        returned. Otherwise, something like
        ``<habitat.message_server.Server: 5 sinks loaded, \
        52 messages so far, approx 1 queued>`` is returned.
        """

        acquired = self.lock.acquire(blocking=False)

        if not acquired:
            return self._repr_locked

        try:
            return self._repr_info_format.format(sinks=len(self.sinks),
                                                 msgs=self.message_count,
                                                 qsz=self.queue.qsize())
        finally:
            self.lock.release()

class Sink(object):
    """
    **Sink** is the parent class for all sinks.

    To write a sink, have your sink class either inherit from
    :py:class:`SimpleSink` or :py:class:`ThreadedSink`.

    All sinks have the following self-explanatory methods, all of which
    update the internal set of message-types which the sink wishes to
    receive. These functions are for use by the sink class.

    * **Sink.add_type**
    * **Sink.add_types**
    * **Sink.remove_type**
    * **Sink.remove_types**
    * **Sink.set_types**
    * **Sink.clear_types**

    They also will have the following functions, which are used
    internally by the message server

    * :py:meth:`Sink.push_message`
    * :py:meth:`Sink.flush`
    * :py:meth:`Sink.shutdown`

    A sink must define these functions:

    * **setup()**: called once; the sink must call some of the
      ``self.*type*`` functions in order to set up the set of types
      that the sink would like to receive
    * **message(message)**: called whenever a message is received for
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

        # Some basic checking that we're getting a server
        dynamicloader.expecthasmethod(server, "push_message")

        # And that we are a sensible class
        dynamicloader.expecthasmethod(self, "setup")
        dynamicloader.expecthasmethod(self, "message")
        dynamicloader.expecthasnumargs(self.setup, 0)
        dynamicloader.expecthasnumargs(self.message, 1)

        self.server = server
        self.types = set()

        # message_count is initialised here but must be incremented
        # by the subclass if it is to be useful. Only messages that
        # match self.types (and are therefore processed) should
        # increment the counter, and only after processing has completed.
        self.message_count = 0

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
        or :py:class:`ThreadedSink`. Filtering based on **Sink.types** is
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

    * be non blocking
    * be thread safe (however you can't use mutexes, these block)
    * tolerate multiple calls to **message** by multiple threads,
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
        dynamicloader.expecthasattr(message, "type")
        dynamicloader.expecthasattr(message, "source")
        dynamicloader.expecthasattr(message, "data")

        if message.type in self.types:
            with self.cv:
                self.executing_count += 1

            self.message(message)

            with self.cv:
                self.message_count += 1
                self.executing_count -= 1
                self.cv.notify_all()

    def flush(self):
        with self.cv:
            while self.executing_count != 0:
                self.cv.wait()

    def shutdown(self):
        self.flush()

    _repr_general_format = "<{{fullname}} (SimpleSink): {status}>"
    _repr_locked_format = _repr_general_format.format(status="locked")
    _repr_info = "{msgs} messages so far, {exc} executing now"
    _repr_info_format = _repr_general_format.format(status=_repr_info)
    del _repr_general_format, _repr_info

    def __repr__(self):
        """
        Concisely describes the current state of the **Sink**

        This is primarily for help debugging from PDB or the python
        console.

        If another thread holds the internal server lock, then a string
        similar to ``<module.class (SimpleSink): locked>`` is returned.
        Otherwise, something like
        ``<module.class (SimpleSink): 5 messages so far, 2 executing now>``
        is returned.
        """

        fullname = dynamicloader.fullname(self.__class__)
        acquired = self.cv.acquire(blocking=False)

        if not acquired:
            return self._repr_locked_format.format(fullname=fullname)

        try:
            return self._repr_info_format.format(fullname=fullname,
                                                 msgs=self.message_count,
                                                 exc=self.executing_count)
        finally:
            self.cv.release()

class ThreadedSink(Sink, crashmat.Thread):
    """
    A class for sinks that need to execute in another thread to inherit

    The parent class of a sink that inherits **ThreadedSink** will execute
    message() exclusively in a thread for your Sink, and two calls to
    message will never occur simultaneously. It uses an internal
    Python :py:class:`Queue.Queue` to achieve this. Therefore, the
    requirements of a :py:class:`SimpleSink` do not apply.
    """

    def __init__(self, server):
        crashmat.Thread.__init__(self)
        self.name = "ThreadedSink runner: " + self.__class__.__name__

        Sink.__init__(self, server)
        self.queue = Queue.Queue()

        self.stats_lock = threading.RLock()
        self.executing = 0

        self.start()

    def push_message(self, message):
        # Between get()ting items from the queue, self.types may change.
        # We should let run() filter for messages we want
        self.queue.put(message)

    def run(self):
        running = True
        while running:
            message = self.queue.get()

            if (hasattr(message, "shutdown_notification") and
                    message.shutdown_notification == True):
                running = False
            else:
                dynamicloader.expecthasattr(message, "type")
                dynamicloader.expecthasattr(message, "source")
                dynamicloader.expecthasattr(message, "data")

                if message.type in self.types:
                    with self.stats_lock:
                        self.executing = 1

                    self.message(message)

                    with self.stats_lock:
                        self.message_count += 1
                        self.executing = 0

            self.queue.task_done()

    def flush(self):
        self.queue.join()

    def shutdown(self):
        self.queue.put(ShutdownNotification())
        self.flush()
        self.join()

    _repr_info = "{msgs} messages so far, roughly {qsz} queued"
    _repr_einfo = _repr_info + ", currently executing"
    _repr_general_format = "<{{fullname}} (ThreadedSink): {status}>"
    _repr_locked_format = _repr_general_format.format(status="locked")
    _repr_info_format = _repr_general_format.format(status=_repr_info)
    _repr_einfo_format = _repr_general_format.format(status=_repr_einfo)
    del _repr_info, _repr_einfo, _repr_general_format

    def __repr__(self):
        """
        Concisely describes the current state of the **Sink**

        This is primarily for help debugging from PDB or the python
        console.

        If another thread holds the internal server lock, then a string
        similar to ``<module.class (ThreadedSink): locked>`` is returned.
        Otherwise, something like
        ``<module.class (ThreadedSink): 5 messages so far, roughly 2 queued>``
        is returned.
        """

        fullname = dynamicloader.fullname(self.__class__)
        acquired = self.stats_lock.acquire(blocking=False)

        if not acquired:
            return self._repr_locked_format.format(fullname=fullname)

        try:
            if self.executing:
                info_format = self._repr_einfo_format
            else:
                info_format = self._repr_info_format

            return info_format.format(fullname=fullname,
                                      msgs=self.message_count,
                                      qsz=self.queue.qsize())
        finally:
            self.stats_lock.release()

class ShutdownNotification(object):
    """
    A object used to ask the runner of a :py:class:`Server` or a \
    :py:class:`ThreadedSink` to shut down
    """
    shutdown_notification = True

class Message(object):
    """
    A Message object describes a single message that the server might handle

    After initialisation, the data is available in

     - **message.source**
     - **message.type**
     - **message.time_created**
     - **message.time_uploaded**
     - **message.data**

    The following message types are available:

    * **Message.RECEIVED_TELEM**: received telemetry string
    * **Message.LISTENER_INFO**: listener information
    * **Message.LISTENER_TELEM**: listener telemetry
    * **Message.TELEM**: (parsed) telemetry data

    .. seealso:: `../messages`

    """

    type_names = ["RECEIVED_TELEM", "LISTENER_INFO", "LISTENER_TELEM", "TELEM"]
    types = range(len(type_names))
    for (type, type_name) in zip(types, type_names):
        locals()[type_name] = type
    del type, type_name

    def __init__(self, source, type, time_created, time_uploaded, data):
        """
        *source*: a Listener object

        *type*: one of the type constants

        *time_created*: the time that the event that eventually caused this
        Message to be created, e.g., for TELEM and RECEIVED_TELEM, this is
        the time that the telemetry string was received over the radio.
        (UNIX Timestamp format)

        *time_uploaded*: the time that habitat received the message.
        (UNIX Timestamp)

        *data*: a type-specific data object, which will be validated
        """

        self.validate_type(type)
        data = self.validate_data(type, data)

        dynamicloader.expecthasattr(source, "callsign")
        dynamicloader.expecthasattr(source, "ip")

        time_created = int(time_created)
        time_uploaded = int(time_uploaded)

        self.source = source
        self.type = type
        self.time_created = time_created
        self.time_uploaded = time_uploaded
        self.data = data

    _repr_format = "<habitat.message_server.Message ({type}) from {source}>"

    def __repr__(self):
        """
        Concisely describes the **Message**

        This is primarily for help debugging from PDB or the python
        console.

        Returns something like:
        ``<RECEIVED_TELEM habitat.message_server.Message from \
        <habitat.message_server.Listener M0ZDR at 127.0.0.1>>``
        """

        return self._repr_format.format(type=self.type_names[self.type],
                                        source=repr(self.source))

    @classmethod
    def validate_type(cls, type):
        """Checks that type is an integer and a valid message type"""

        if type not in cls.types:
            raise ValueError("message.type is not a valid type")

    @classmethod
    def validate_types(cls, types):
        """Checks that types is a set of valid integer message types"""

        dynamicloader.expecthasattr(types, "__iter__")

        for type in types:
            Message.validate_type(type)

    @classmethod
    def validate_data(cls, type, data):
        if type == cls.RECEIVED_TELEM:
            return cls._coerce_data_received_telem(data)
        elif type == cls.LISTENER_INFO:
            return cls._coerce_data_listener_info(data)
        elif type == cls.LISTENER_TELEM:
            return cls._coerce_data_listener_telem(data)
        elif type == cls.TELEM:
            return cls._coerce_data_telem(data)

    @classmethod
    def _coerce_data_dict(cls, data):
        try:
            data = deepcopy(dict(data))
        except:
            raise TypeError("data should be a dictionary")

        return data

    @classmethod
    def _coerce_data_base64(cls, string):
        try:
            binary_data = base64.b64decode(str(string))
        except TypeError:
            raise ValueError("string was not valid base64.")
        return str(base64.b64encode(binary_data))

    @classmethod
    def _coerce_data_received_telem(cls, data):
        data = cls._coerce_data_dict(data)

        clean_data = {}

        try:
            clean_data["string"] = cls._coerce_data_base64(data["string"])
        except KeyError:
            raise ValueError("A required key couldn't be found in data")

        try:
            clean_data["frequency"] = float(data["frequency"])
        except KeyError:
            pass
        except (TypeError, ValueError):
            raise ValueError("Invalid frequency")
        else:
            if clean_data["frequency"] < 0:
                raise ValueError("Invalid frequency")

        return clean_data

    @classmethod
    def _coerce_data_listener_info(cls, data):
        data = cls._coerce_data_dict(data)

        clean_data = {}

        for i in ["name", "location", "radio", "antenna"]:
            try:
                clean_data[i] = unicode(data[i])
            except KeyError:
                pass
            except (TypeError, ValueError):
                raise ValueError("Invalid value in data")

        return clean_data

    @classmethod
    def _coerce_data_listener_telem(cls, data):
        data = cls._coerce_data_dict(data)

        clean_data = {}

        try:
            for i in ["latitude", "longitude"]:
                clean_data[i] = float(data[i])

            clean_data["altitude"] = int(data["altitude"])

            clean_data["time"] = {}
            for i in ["hour", "minute", "second"]:
                clean_data["time"][i] = int(data["time"][i])
        except KeyError:
            raise ValueError("A required key couldn't be found in data")
        except (TypeError, ValueError):
            raise ValueError("Invalid value in data")

        hour = clean_data["time"]["hour"]
        minute = clean_data["time"]["minute"]
        second = clean_data["time"]["second"]

        if hour < 0 or hour > 24 or \
           minute < 0 or minute > 59 or \
           second < 0 or second > 61:
            raise ValueError("Invalid time value in data")

        latitude = clean_data["latitude"]
        longitude = clean_data["longitude"]

        if latitude < -90.0 or latitude > 90.0 or \
           longitude < -180.0 or longitude > 180.0:
            raise ValueError("Invalid location value in data")

        return clean_data

    @classmethod
    def _coerce_data_telem(cls, data):
        data = cls._coerce_data_dict(data)

        clean_data = {}

        try:
            clean_data["_raw"] = cls._coerce_data_base64(data["_raw"])
            clean_data["_listener_metadata"] = \
                cls._coerce_data_dict(data["_listener_metadata"])
        except KeyError:
            raise ValueError("A required key couldn't be found in data")

        # Remove _raw and _listener_metadata, then copy all keys across
        del data["_raw"]
        del data["_listener_metadata"]
        clean_data.update(data)

        return clean_data

class Listener(object):
    """
    A **Listener** object describes the source from which a message came.

    It has two attributes: *callsign* and *ip*. *callsign* is
    chosen by the user that created the message, and must be alphanumeric
    and uppercase. It cannot be "trusted". *ip* in typical usage is
    initalised by the server receiving the message (i.e., where it came
    from). When comparing two **Listener** objects (operator overloading),
    only *callsign* is considered.
    """

    allowed_callsign_characters = string.letters + string.digits + "/_-"

    def __init__(self, callsign, ip):
        """
        *callsign*: string, must be composed of alphanumeric and /_-
        characters only (a-zA-Z0-9/_-)

        *ip*: string, which will be validated and converted to an
        **IPAddress** object (the ``ipaddr`` module)
        """

        if not isinstance(callsign, basestring):
            raise TypeError("callsign must derive from basestring")

        if len(callsign) == 0:
            raise ValueError("callsign cannot be empty")

        for letter in callsign:
            if letter not in self.allowed_callsign_characters:
                raise ValueError("callsign may only include " + 
                    self.allowed_callsign_characters)

        self.ip = ipaddr.IPAddress(ip)
        self.callsign = callsign.upper()

    def __eq__(self, other):
        try:
            return self.callsign == other.callsign
        except:
            return False

    _repr_format = "<habitat.message_server.Listener {callsign} at {ip}>"

    def __repr__(self):
        """
        Concisely describes the **Listener**

        This is primarily for help debugging from PDB or the python
        console.

        Returns something like:
        ``<habitat.message_server.Listener M0ZDR at 127.0.0.1>``
        """

        return self._repr_format.format(callsign=self.callsign,
                                        ip=str(self.ip))
