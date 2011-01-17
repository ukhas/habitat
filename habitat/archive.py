# Copyright 2010 (C) Adam Greig
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
ArchiveSink stores messages in a CouchDB datastore.
"""

from habitat.message_server import SimpleSink, Message
from habitat.utils import dynamicloader

__all__ = ["ArchiveSink"]

class ArchiveSink(SimpleSink):
    """
    The ArchiveSink is responsible for storing data in the Couch database.
    It will create and modify documents as required to store incoming messages,
    listener information and parsed telemetry.
    """
    def setup(self):
        """
        Add all message types to those we should receive.
        """
        self.add_type(Message.RECEIVED_TELEM)
        self.add_type(Message.LISTENER_TELEM)
        self.add_type(Message.LISTENER_INFO)
        self.add_type(Message.TELEM)

    def message(self, message):
        """
        Handle an incoming message, storing it in the datastore.

        There are four varients of incoming message:
        
            * **RECEIVED_TELEM** (raw telemetry strings):
                These are stored as ``payload_telemetry`` documents, with the
                base64 encoded raw data in **_raw** inside **data**,
                information on who received it in **receivers** and the
                document ID set to the sha256 sum of the base64 data.
            * **TELEM** (parsed telemetry data):
                These are stored as per *RECEIVED_TELEM*, with the parsed data
                placed in the **data** dictionary along with the raw data
                in **_raw** and additionally a **_protocol** field specifying
                which parser was used to extract the data.
            * **LISTENER_TELEM** (telemetry concerning listeners):
                Stored in ``listener_telemetry`` documents, typically
                specifying a position and corresponding time and the listener's
                callsign.
            * **LISTENER_INFO** (general information on a listener):
                Stored in ``listener_info`` documents, containing any metadata
                the listener wishes to submit but generally consisting of
                a name, location, radio, antenna or other information along
                with their callsign.

        When a new **RECEIVED_TELEM** or **TELEM** message comes in, the
        database is checked for an existing document for this message. If none
        is found, a new one is created: in the case of **RECEIVED_TELEM**, the
        new one contains the received data in **_raw** in **data**, while for
        **TELEM** messages all the parsed data is put in **data**. If a
        document is found, any new data from the current message is written
        over anything in the database (though no data will be deleted without
        anything to replace it).

        When new **LISTENER_TELEM** messages come in, they are directly
        created as a new document.

        When new **LISTENER_INFO** messages are received, a check is done on
        this callsign's latest document and a new one is only created if the
        new message is different from the current data in the database.
        """
        if message.type == Message.RECEIVED_TELEM:
            pass
        elif message.type == Message.TELEM:
            pass
        elif message.type == Message.LISTENER_INFO:
            doc = {"type": "listener_info", "data": message.data}
            doc["data"]["callsign"] = message.source.callsign
            lastdoc = self._get_listener_telem_doc(message.source.callsign)
            if not lastdoc or doc["data"] != lastdoc["data"]:
                self.server.db.save_doc(doc)
        elif message.type == Message.LISTENER_TELEM:
            doc = {"type": "listener_telem", "data": message.data}
            doc["data"]["callsign"] = message.source.callsign
            self.server.db.save_doc(doc)

    def _get_listener_telem_doc(self, callsign):
        """
        Try to get the latest LISTENER_TELEM document from the database
        for the given callsign, returning None if none could be found.
        """
        startkey = [callsign, None]
        result = self.server.db.view("habitat/payload_config", limit = 1,
                include_docs = True, startkey=startkey).first()
        try:
            if not result or result["doc"]["data"]["callsign"] != callsign:
                return None
        except (KeyError):
            return None

        return result["doc"]    