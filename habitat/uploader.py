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
import copy
import base64
import hashlib
import couchdbkit
import couchdbkit.exceptions
import restkit
import restkit.errors
import threading
import Queue
import time
import json
import logging
import strict_rfc3339

from .utils import quick_traceback

logger = logging.getLogger("habitat.uploader")


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
    :meth:`listener_information` in any order. It is however recommended that
    :meth:`listener_information` and :meth:`listener_telemetry` are called once
    before any other uploads.

    :meth:`flights` returns a list of current flight documents.

    Each method that causes an upload accepts an optional kwarg, time_created,
    which should be the unix timestamp of when the doc was created, if it is
    different from the default 'now'. It will add time_uploaded, and turn both
    times into RFC3339 strings using the local offset.

    See the CouchDB schema for more information, both on
    validation/restrictions and data formats.
    """

    def __init__(self, callsign,
                       couch_uri="http://habitat.habhub.org/",
                       couch_db="habitat",
                       max_merge_attempts=20):
        # NB: update default options in /bin/uploader

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

        The format of the document produced is described elsewhere;
        the actual document will be constructed by :class:`Uploader`.
        *data* must be a dict and should typically look something like
        this::

            data = {
                "time": "12:40:12",
                "latitude": -35.11,
                "longitude": 137.567,
                "altitude": 12
            }

        ``time`` is the GPS time for this point, ``latitude`` and ``longitude``
        are in decimal degrees, and ``altitude`` is in metres.

        ``latitude`` and ``longitude`` are mandatory.

        Validation will be performed by the CouchDB server. *data* must not
        contain the key ``callsign`` as that is added by
        :class:`Uploader`.
        """
        return self._listener_doc(data, "listener_telemetry", time_created)

    def listener_information(self, data, time_created=None):
        """
        Upload a listener_information doc. The doc_id is returned

        A listener_information document contains static human readable
        information about a listener.

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
        return self._listener_doc(data, "listener_information", time_created)

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
        time_uploaded = int(round(time.time()))
        time_created = int(round(time_created))

        to_rfc3339 = strict_rfc3339.timestamp_to_rfc3339_localoffset
        thing["time_uploaded"] = to_rfc3339(time_uploaded)
        thing["time_created"] = to_rfc3339(time_created)

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
        ``time_uploaded``, ``latest_listener_information`` or
        ``latest_listener_telemetry``. These are added by :class:`Uploader`.
        """

        if metadata is None:
            metadata = {}

        if time_created is None:
            time_created = time.time()

        for key in ["time_created", "time_uploaded",
                "latest_listener_information", "latest_listener_telemetry"]:
            assert key not in metadata

        receiver_info = copy.deepcopy(metadata)

        with self._lock:
            for doc_type in ["listener_telemetry", "listener_information"]:
                if doc_type in self._latest:
                    receiver_info["latest_" + doc_type] = \
                            self._latest[doc_type]

        for i in xrange(self._max_merge_attempts):
            try:
                self._set_time(receiver_info, time_created)
                doc_id = self._payload_telemetry_update(string, receiver_info)
            except couchdbkit.exceptions.ResourceConflict:
                continue
            except restkit.errors.Unauthorized:
                raise UnmergeableError
            else:
                return doc_id
        else:
            raise UnmergeableError

    def _payload_telemetry_update(self, string, receiver_info):
        doc_id = hashlib.sha256(base64.b64encode(string)).hexdigest()
        doc_ish = {
            "data": {"_raw": base64.b64encode(string)},
            "receivers": {self._callsign: receiver_info}
        }
        url = "_design/payload_telemetry/_update/add_listener/" + doc_id
        self._db.res.put(url, payload=doc_ish).skip_body()
        return doc_id

    def flights(self):
        """
        Return a list of flight documents.
        
        Finished flights are not included; so the returned list contains
        active and not yet started flights (i.e., now <= flight.end).

        Only approved flights are included.

        Flights are sorted by end time.

        Active is (flight.start <= now <= flight.end), i.e., within the launch
        window.

        The key ``_payload_docs`` is added to each flight document and is
        populated with the documents listed in the payloads array, provided
        they exist. If they don't, that _id will be skipped.
        """

        results = []
        now = int(time.time())

        for row in self._db.view("flight/end_start_including_payloads",
                                 include_docs=True, startkey=[now]):
            end, start, flight_id, is_pcfg = row["key"]
            doc = row["doc"]

            if not is_pcfg:
                doc["_payload_docs"] = []
                results.append(doc)
            elif doc is not None:
                assert flight_id == results[-1]["_id"]
                results[-1]["_payload_docs"].append(doc)

        return results

    def payloads(self):
        """
        Returns a list of all payload_configuration docs ever.

        Sorted by name, then time created.
        """

        view = self._db.view("payload_configuration/name_time_created",
                             include_docs=True)
        return [row["doc"] for row in view]


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
     - :meth:`got_payloads`

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
        self.debug("Queuing " + self._describe(item))
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

    def listener_information(self, *args, **kwargs):
        """See :meth:`Uploader.listener_information`"""
        self._do_queue(("listener_information", args, kwargs))

    def flights(self):
        """
        See :meth:`Uploader.flights`.
        
        Flight data is passed to :meth:`got_flights`.
        """
        self._do_queue(("flights", [], {}))

    def payloads(self):
        """
        See :meth:`Uploader.payloads`.
        
        Flight data is passed to :meth:`got_payloads`.
        """
        self._do_queue(("payloads", [], {}))

    def debug(self, msg):
        """Log a debug message"""
        logger.debug(msg)

    def log(self, msg):
        """Log a generic string message"""
        logger.info(msg)

    def warning(self, msg):
        """Alike log, but more important"""
        logger.warn(msg)

    def saved_id(self, doc_type, doc_id):
        """Called when a document is succesfully saved to couch"""
        self.log("Saved {0} doc: {1}".format(doc_type, doc_id))

    def initialised(self):
        """Called immiediately after successful Uploader initialisation"""
        self.debug("Initialised Uploader")

    def reset_done(self):
        """Called immediately after resetting the Uploader object"""
        self.debug("Settings reset")

    def caught_exception(self):
        """Called when the Uploader throws an exception"""
        self.warning("Caught " + quick_traceback.oneline())

    def got_flights(self, flights):
        """
        Called after a successful flights download, with the data.

        Downloads are initiated by calling :meth:`flights`
        """
        self.debug("Default action: got_flights; discarding")

    def got_payloads(self, payloads):
        """
        Called after a successful payloads download, with the data.

        Downloads are initiated by calling :meth:`payloads`
        """
        self.debug("Default action: got_payloads; discarding")

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
        self.debug("Started")

        while True:
            item = self._queue.get()

            self.debug("Running " + self._describe(item))

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
                else:
                    f = getattr(self._uploader, func)
                    r = f(*args, **kwargs)

                    if func in ["flights", "payloads"]:
                        f = getattr(self, "got_" + func)
                        f(r)
                    else:
                        self.saved_id(func, r)

            except:
                self.caught_exception()

            self._queue.task_done()


class ExtractorManager(object):
    """
    Manage one or more :class:`Extractor` objects, and handle their logging.

    The extractor manager maintains a list of :class:`Extractor` objects.
    Any :meth:`push` or :meth:`skipped` calls are passed directly to each
    added Extractor in turn. If any Extractor produces logging output, or
    parsed data, it is returned to the :meth:`status` and :meth:`data` methods,
    which the user should override.

    The ExtractorManager also handles thread safety for all Extractors
    (i.e., it holds a lock while pushing data to each extractor). Your
    :meth:`status` and :meth:`data` methods should be thread safe if you want
    to call the ExtractorManager from more than one thread.
    """

    def __init__(self, uploader):
        """uploader: an :class:`Uploader` or :class:`UploaderThread` object"""
        self.uploader = uploader
        self._lock = threading.RLock()
        self._extractors = []

    def add(self, extractor):
        """Add the extractor object to the manager"""
        with self._lock:
            self._extractors.append(extractor)
            extractor.manager = self

    def push(self, b, **kwargs):
        """
        Push a received byte of data, b, to all extractors.

        b must be of type str (i.e., ascii, not unicode) and of length 1.

        Any kwargs are passed to extractors. The only useful kwarg at the
        moment is the boolean "baudot hack".

        baudot_hack is set to True when decoding baudot, which doesn't support
        the '*' character, as the UKHASExtractor needs to know to replace all
        '#' characters with '*'s.
        """

        assert len(b) == 1 and isinstance(b, str)

        with self._lock:
            for e in self._extractors:
                e.push(b, **kwargs)

    def skipped(self, n):
        """
        Tell all extractors that approximately n undecodable bytes have passed

        This advises extractors that some bytes couldn't be decoded for
        whatever reason, but were transmitted. This can assist some
        fixed-size packet formats in recovering from errors if one byte is
        dropped, say, due to the start bit being flipped. It also causes
        Extractors to 'give up' after a certain amount of time has passed.
        """
        with self._lock:
            for e in self._extractors:
                e.skipped(n)

    def status(self, msg):
        """Logging method, called by Extractors when something happens"""
        logger.info(msg)

    def data(self, d):
        """Called by Extractors if they are able to parse extracted data"""
        logger.debug("Extractor gave us provisional parse: " + json.dumps(d))


class Extractor(object):
    """
    A base class for an Extractor.

    An extractor is responsible for identifying telemetry in a stream of bytes,
    and extracting them as standalone strings. This may be by using start/end
    delimiters, or packet lengths, or whatever. Extracted strings are passed
    to :meth:`Uploader.payload_telemetry` via the ExtractorManager.

    An extractor may optionally attempt to parse the data it has extracted.
    This does not affect the upload of extracted data, and offical parsing
    is done by the habitat server, but may be useful to display in a GUI.
    It could even be a stripped down parser capable of only a subset of the
    full protocol, or able to parse the bare minimum only. If it succeeds,
    the result is passed to :meth:`ExtractorManager.data`.
    """

    def __init__(self):
        self.manager = None

    def push(self, b, **kwargs):
        """see :meth:`ExtractorManager.push`"""
        raise NotImplementedError

    def skipped(self, n):
        """see :meth:`ExtractorManager.skipped`"""
        raise NotImplementedError


class UKHASExtractor(Extractor):
    def __init__(self):
        super(UKHASExtractor, self).__init__()
        self.last = None
        self.buffer = ""
        self.garbage_count = 0
        self.extracting = False

    def push(self, b, **kwargs):
        if b == '\r':
            b = '\n'

        if self.last == '$' and b == '$':
            self.buffer = self.last + b
            self.garbage_count = 0
            self.extracting = True

            self.manager.status("UKHAS: found start delimiter")

        elif self.extracting and b == '\n':
            self.buffer += b
            self.manager.uploader.payload_telemetry(self.buffer)

            self.manager.status("UKHAS: extracted string")

            try:
                # TODO self.manager.data(self.crude_parse(self.buffer))
                raise ValueError("crude parse doesn't exist yet")

            except (ValueError, KeyError) as e:
                self.manager.status("UKHAS: crude parse failed: " + str(e))
                self.manager.data({"_sentence": self.buffer})

            self.buffer = None
            self.extracting = False

        elif self.extracting:
            if "baudot_hack" in kwargs and kwargs["baudot_hack"] and b == '#':
                # baudot doesn't support '*', we use '#'
                b = '*'

            self.buffer += b

            if ord(b) < 0x20 or ord(b) > 0x7E:
                # Non ascii chars
                self.garbage_count += 1

            # Sane limits to avoid uploading tonnes of garbage
            if len(self.buffer) > 1000 or self.garbage_count > 16:
                self.manager.status("UKHAS: giving up")

                self.buffer = None
                self.extracting = False

        self.last = b

    def skipped(self, n):
        for i in xrange(n):
            self.push("\0")
