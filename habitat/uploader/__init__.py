# Copyright 2011 (C) Daniel Richman
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
The uploader is a client for end users that pushes documents into a couchdb
database where they can be used directly by the web client or picked up
by a daemon for further processing.
"""

import time
import copy
import base64
import hashlib
import couchdbkit

class CollisionError(Exception):
    """
    Payload telemetry sha256 hash collision

    Raised if two strings (in payload_telemetry docs) have the same
    sha256 hash yet are different.
    """
    pass

class UnmergeableError(Exception):
    """
    Couldn't merge a payload_telemetry CouchDB conflict after many tries
    """
    pass

class Uploader(object):
    """
    An easy interface to insert documents into a habitat CouchDB.

    This class is intended for use by a listener.

    After having created an Uploader object, call payload_telemetry,
    listener_telemetry or listener_info in any order. It is however
    recommended that listener_info and listener_telem are called once
    before any other uploads

    See the CouchDB schema for more information, both on
    validation/restrictions and data formats.
    """

    def __init__(self, callsign,
                       couch_uri="http://habhub.org/",
                       couch_db="habitat",
                       max_merge_attempts=20):
        self._callsign = callsign
        self._latest = {}
        self._max_merge_attempts = max_merge_attempts

        server = couchdbkit.Server(couch_uri)
        self._db = server[couch_db]

    def listener_telemetry(self, data, time_created=None):
        """
        Upload a listener_telemetry doc. The doc_id is returned

        A listener_telemetry doc contains information about the listener's
        current location, be it a rough stationary location or a constant
        feed of GPS points. In the former case, you may only need to call
        this function once, at startup. In the latter, you might want to
        call it constantly.

        The format of the document produced is described elsewhere (TODO?);
        the actual document will be constructed by the Uploader.
        **data** must be a dict and should typically look something like
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

        Time is the GPS time for this point, latitude and longitude are in
        decimal degrees, and altitude is in metres.

        Validation will be performed by the CouchDB server. **data** must not
        contain the key ''callsign'', since that is added by the Uploader.
        """
        return self._listener_doc(data, "listener_telemetry", time_created)

    def listener_info(self, data, time_created=None):
        """
        Upload a listener_info doc. The doc_id is returned

        A listener_info document contains static human readable information
        about a listener.

        The format of the document produced is described elsewhere (TODO?);
        the actual document will be constructed by the Uploader.
        **data** must be a dict and should typically look something like
        this::

            data = {
                "callsign": "M0RND",
                "name": "Adam Greig",
                "location": "Cambridge, UK",
                "radio": "ICOM IC-7000",
                "antenna": "9el 434MHz Yagi"
            }

        **data** must not contain the key **callsign**, since that is added
        by the Uploader.
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
        self._latest[doc_type] = doc_id
        return doc_id

    def _set_time(self, thing, time_created):
        thing["time_uploaded"] = int(round(time.time()))
        thing["time_created"] = int(round(time_created))

    def payload_telemetry(self, string, metadata, time_created=None):
        """
        Create or add to the payload_telemetry document for `string`

        This function attempts to create a new payload_telemetry document
        for the provided string (a new document, with one receiver: you).
        If the document already exists in the database it instead downloads
        it, adds you to the list of receivers, and reuploads.

        **metadata** can contain extra information about your receipt of
        **string**. Nothing has been standardised yet (TODO), but here's an
        example of what you might be able to do in the future::

            metadata = {
                "frequency": 434075000,
                "signal_strength": 5
            }

        **metadata** must not contain the keys **time_created**,
        **time_uploaded**, **latest_listener_info** or
        **latest_listener_telemetry**. These are added by the Uploader.
        """

        if time_created is None:
            time_created = time.time()

        for key in ["time_created", "time_uploaded", "latest_listener_info",
                    "latest_listener_telemetry"]:
            assert key not in metadata

        receiver_info = copy.deepcopy(metadata)

        for doc_type in ["listener_telemetry", "listener_info"]:
            if doc_type in self._latest:
                receiver_info["latest_" + doc_type] = self._latest[doc_type]

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
