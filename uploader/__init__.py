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
import base64
import hashlib
import couchdbkit

class Uploader(object):
    def __init__(self, callsign,
                       couch_uri="http://habhub.org/",
                       couch_db="habitat"):
        self._callsign = callsign

        server = couchdbkit.Server(couch_uri)
        self._db = server[couch_db]

    def listener_telem(self, data, time_created=None):
        self._listener_doc(data, "listener_telem", time_created)

    def listener_info(self, data, time_created=None):
        self._listener_doc(data, "listener_info", time_created)

    def _listener_doc(self, data, type, time_created=None):
        time_uploaded = time.time()

        if time_created is None:
            time_created = time_uploaded

        doc = {
            "data": data,
            "type": type,
            "time_created": time_created,
            "time_uploaded": time_uploaded
        }

        self._db.save_doc(doc)

    def payload_telemetry(self, string, metadata, time_created=None):
        time_uploaded = time.time()

        if time_created is None:
            time_created = time_uploaded

        receiver_info = {
            "time_created": time_created,
            "time_uploaded": time_uploaded,
        }

        doc = {
            "data": {"_raw": base64.b64encode(string)},
            "receivers": {self._callsign: receiver_info},
            "type": "payload_telemetry"
        }

        doc_id = hashlib.sha256(doc["data"]["_raw"]).hexdigest()

        self._db[doc_id] = doc
