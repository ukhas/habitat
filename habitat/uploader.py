# Copyright 2011, 2012 (C) Daniel Richman
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
Python interface to document insertion into CouchDB.

The uploader is a client for end users that pushes documents into a CouchDB
database where they can be used directly by the web client or picked up
by a daemon for further processing.

"""

import sys
import time
import copy
import base64
import hashlib
import couchdbkit
import threading
import Queue
import traceback


class CollisionError(Exception):
    """
    Payload telemetry sha256 hash collision.

    Raised if two strings (in ``payload_telemetry`` docs) have the same
    sha256 hash yet are different.

    Odds you will ever see this error: approximately one in one hundred and
    sixteen quattuorvigintillion (about a thousand times more likely than
    selecting one particular atom at random out of all the atoms in the
    universe).
    """
    pass


class UnmergeableError(Exception):
    """
    Couldn't merge a ``payload_telemetry`` CouchDB conflict after many tries.
    """
    pass


class Uploader(object):
    """
    An easy interface to insert documents into a habitat CouchDB.

    This class is intended for use by a listener.

    After having created an :class:`Uploader` object, call
    :meth:`payload_telemetry`, :meth:`listener_telemetry` or
    :meth:`listener_info` in any order. It is however recommended that
    :meth:`listener_info` and :meth:`listener_telemetry` are called once before
    any other uploads.

    :meth:`flights` returns a list of current flight documents.

    See the CouchDB schema for more information, both on
    validation/restrictions and data formats.
    """

    def __init__(self, callsign,
                       couch_uri="http://habhub.org/",
                       couch_db="habitat",
                       max_merge_attempts=20):
        self._lock = threading.RLock()
        self._callsign = callsign
        self._latest = {}
        self._max_merge_attempts = max_merge_attempts

        server = couchdbkit.Server(couch_uri)
        self._db = server[couch_db]

    def listener_telemetry(self, data, time_created=None):
        """
        Upload a ``listener_telemetry`` doc. The ``doc_id`` is returned

        A ``listener_telemetry`` doc contains information about the listener's
        current location, be it a rough stationary location or a constant
        feed of GPS points. In the former case, you may only need to call
        this function once, at startup. In the latter, you might want to
        call it constantly.

        The format of the document produced is described elsewhere (TODO?);
        the actual document will be constructed by :class:`Uploader`.
        *data* must be a dict and should typically look something like
        this::

            data = {
                "time": {
                    "hour": 12,
                    "minute": 40,
                    "second: 12
                },
                "latitude": -35.11,
                "longitude": 137.567,
                "altitude": 12
            }

        ``time`` is the GPS time for this point, ``latitude`` and ``longitude``
        are in decimal degrees, and ``altitude`` is in metres.

        Validation will be performed by the CouchDB server. *data* must not
        contain the key ``callsign`` as that is added by
        :class:`Uploader`.
        """
        return self._listener_doc(data, "listener_telemetry", time_created)

    def listener_info(self, data, time_created=None):
        """
        Upload a listener_info doc. The doc_id is returned

        A listener_info document contains static human readable information
        about a listener.

        The format of the document produced is described elsewhere (TODO?);
        the actual document will be constructed by ``Uploader``.
        *data* must be a dict and should typically look something like
        this::

            data = {
                "name": "Adam Greig",
                "location": "Cambridge, UK",
                "radio": "ICOM IC-7000",
                "antenna": "9el 434MHz Yagi"
            }

        *data* must not contain the key ``callsign`` as that is added by
        :class:`Uploader`.
        """
        return self._listener_doc(data, "listener_info", time_created)

    def _listener_doc(self, data, doc_type, time_created=None):
        if time_created is None:
            time_created = time.time()

        assert "callsign" not in data

        data = copy.deepcopy(data)
        data["callsign"] = self._callsign

        doc = {
            "data": data,
            "type": doc_type
        }

        self._set_time(doc, time_created)
        self._db.save_doc(doc)

        doc_id = doc["_id"]
        with self._lock:
            self._latest[doc_type] = doc_id
        return doc_id

    def _set_time(self, thing, time_created):
        thing["time_uploaded"] = int(round(time.time()))
        thing["time_created"] = int(round(time_created))

    def payload_telemetry(self, string, metadata=None, time_created=None):
        """
        Create or add to the ``payload_telemetry`` document for *string*.

        This function attempts to create a new ``payload_telemetry`` document
        for the provided string (a new document, with one receiver: you).
        If the document already exists in the database it instead downloads
        it, adds you to the list of receivers, and reuploads.

        *metadata* can contain extra information about your receipt of
        *string*. Nothing has been standardised yet (TODO), but here's an
        example of what you might be able to do in the future::

            metadata = {
                "frequency": 434075000,
                "signal_strength": 5
            }

        *metadata* must not contain the keys ``time_created``,
        ``time_uploaded``, ``latest_listener_info`` or
        ``latest_listener_telemetry``. These are added by :class:`Uploader`.
        """

        if metadata is None:
            metadata = {}

        if time_created is None:
            time_created = time.time()

        for key in ["time_created", "time_uploaded", "latest_listener_info",
                    "latest_listener_telemetry"]:
            assert key not in metadata

        receiver_info = copy.deepcopy(metadata)

        with self._lock:
            for doc_type in ["listener_telemetry", "listener_info"]:
                if doc_type in self._latest:
                    receiver_info["latest_" + doc_type] = \
                            self._latest[doc_type]

        doc_id = hashlib.sha256(base64.b64encode(string)).hexdigest()

        try:
            self._set_time(receiver_info, time_created)
            doc = self._payload_telemetry_new(string, receiver_info)
            self._db[doc_id] = doc
            return doc_id
        except couchdbkit.exceptions.ResourceConflict:
            for i in xrange(self._max_merge_attempts):
                try:
                    doc = self._db[doc_id]
                    self._set_time(receiver_info, time_created)
                    self._payload_telemetry_merge(doc, string, receiver_info)
                    self._db[doc_id] = doc
                except couchdbkit.exceptions.ResourceConflict:
                    continue
                else:
                    return doc_id

            raise UnmergeableError

    def _payload_telemetry_new(self, string, receiver_info):
        doc = {
            "data": {"_raw": base64.b64encode(string)},
            "receivers": {self._callsign: receiver_info},
            "type": "payload_telemetry"
        }

        return doc

    def _payload_telemetry_merge(self, doc, string, receiver_info):
        if doc["data"]["_raw"] != base64.b64encode(string):
            raise CollisionError

        doc["receivers"][self._callsign] = receiver_info
        return doc

    def flights(self):
        """Return a list of current flight documents"""

        results = []
        for row in self._db.view("uploader_v1/flights", include_docs=True,
                                 startkey=int(time.time())):
            results.append(row["doc"])

        return results


class UploaderThread(threading.Thread):
    """
    An easy wrapper around :class:`Uploader` to make a non blocking Uploader

    After creating an UploaderThread object, call :meth:`start` to create 
    a thread. Then, call :meth:`settings` to initialise the underlying
    :class:`Uploader`. You may then call any of the 4 action methods from
    :class:`Uploader` with exactly the same arguments. Note however, that
    they do not return anything (see below for flights() returning).

    Several methods may be overridden in the UploaderThread. They are:

     - :meth:`log`
     - :meth:`warning`
     - :meth:`saved_id`
     - :meth:`initialised`
     - :meth:`reset_done`
     - :meth:`caught_exception`
     - :meth:`got_flights`

    Please note that these must all be thread safe.

    If initialisation fails (bad arguments or similar), a warning will be
    emitted but the UploaderThread will continue to exist. Further calls
    will just emit warnings and do nothing until a successful
    :meth:`settings` call is made.

    The :meth:`reset` method destroys the underlying Uploader. Calls will
    emit warnings in the same fashion as a failed initialisation.
    """
    
    def __init__(self):
        super(UploaderThread, self).__init__(name="habitat UploaderThread")
        self._queue = Queue.Queue()
        self._sent_shutdown = False
        self._sent_shutdown_lock = threading.Lock()

        # For use by run() only
        self._uploader = None

    def start(self):
        """Start the background UploaderThread"""
        super(UploaderThread, self).start()

    def _do_queue(self, item):
        self.log("Queuing " + self._describe(item))
        self._queue.put(item)

    def join(self):
        """Asks the background thread to exit, and then blocks until it has"""
        with self._sent_shutdown_lock:
            if not self._sent_shutdown:
                self._sent_shutdown = True
                self._do_queue(None)

        super(UploaderThread, self).join()

    def settings(self, *args, **kwargs):
        """See :class:`Uploader`'s initialiser"""
        self._do_queue(("init", args, kwargs))

    def reset(self):
        """Destroys the Uploader object, disabling uploads."""
        self._do_queue(("reset", None, None))

    def payload_telemetry(self, *args, **kwargs):
        """See :meth:`Uploader.payload_telemetry`"""
        self._do_queue(("payload_telemetry", args, kwargs))

    def listener_telemetry(self, *args, **kwargs):
        """See :meth:`Uploader.listener_telemetry`"""
        self._do_queue(("listener_telemetry", args, kwargs))

    def listener_info(self, *args, **kwargs):
        """See :meth:`Uploader.listener_info`"""
        self._do_queue(("listener_info", args, kwargs))

    def flights(self):
        """
        See :meth:`Uploader.flights`.
        
        Flight data is passed to the :meth:`got_flights` like a callback.
        """
        self._do_queue(("flights", [], {}))

    def log(self, msg):
        """Log a generic string message"""
        raise NotImplementedError

    def warning(self, msg):
        """Alike log, but more important"""
        self.log("Warning: " + msg)

    def saved_id(self, doc_type, doc_id):
        """Called when a document is succesfully saved to couch"""
        self.log("Saved {0} doc: {1}".format(doc_type, doc_id))

    def initialised(self):
        """Called immiediately after successful Uploader initialisation"""
        self.log("Initialised Uploader")

    def reset_done(self):
        """Called immediately after resetting the Uploader object"""
        self.log("Settings reset")

    def caught_exception(self):
        """Called when the Uploader throws an exception"""
        (exc_type, exc_value, discard_tb) = sys.exc_info()
        exc_tb = traceback.format_exception_only(exc_type, exc_value)
        info = exc_tb[-1].strip()
        self.warning("Caught " + info)

    def got_flights(self, flights):
        """
        Called after a successful flights download, with the data.

        Downloads are initiated by calling :meth:`flights`
        """
        self.log("Default action: got_flights; discarding")
    
    def _describe(self, queue_item):
        if queue_item is None:
            return "Shutdown"
        
        (func, args, kwargs) = queue_item

        if func is "reset":
            return "del Uploader";

        if func is "init":
            func = "Uploader"
        else:
            func = "Uploader." + func

        if args is not None:
            args = [repr(a) for a in args]
            args += ["{0}={1!r}".format(k, kwargs[k]) for k in kwargs]
        else:
            args = ""

        return "{0}({1})".format(func, ', '.join(args))

    def run(self):
        self.log("Started")

        while True:
            item = self._queue.get()

            self.log("Running " + self._describe(item))

            if item is None:
                break

            (func, args, kwargs) = item

            try:
                if func not in ["init", "reset"] and self._uploader is None:
                    raise ValueError("Uploader settings were not initialised")

                if func == "init":
                    self._uploader = Uploader(*args, **kwargs)
                    self.initialised()
                elif func == "reset":
                    self._uploader = None
                    self.reset_done()
                elif func == "flights":
                    r = self._uploader.flights(*args, **kwargs)
                    self.got_flights(r)
                else:
                    f = getattr(self._uploader, func)
                    r = f(*args, **kwargs)
                    self.saved_id(func, r)

            except:
                self.caught_exception()

            self._queue.task_done()
