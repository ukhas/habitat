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
        archive is searched for an existing document and if one is found
        the new listener is appended to the existing listeners dictionary,
        otherwise a new document is created. If the message is a **TELEM**
        and contains data that doesn't exist in the document, that is saved
        as well.

        When new **LISTENER_TELEM** messages come in, they are directly created
        as a new document.

        When new **LISTENER_INFO** messages are received, a check is done on
        this callsign's latest document and a new one is only created if the
        new message is different from the current data in the database.
        """
        if message.type == Message.RECEIVED_TELEM:
            pass
        elif message.type == Message.TELEM:
            pass
        elif message.type == Message.LISTENER_INFO:
            pass
        elif message.type == Message.LISTENER_TELEM:
            self._add_listener_telem_doc(message)

    def _add_listener_telem_doc(self, message):
        """Form a new document out of a LISTENER_TELEM message and save it."""
        doc = {"type": "listener_telem", "data":{}}
        try:
            doc["data"]["callsign"] = str(message.source.callsign)
            doc["data"]["latitude"] = float(message.data["latitude"])
            doc["data"]["longitude"] = float(message.data["longitude"])
            doc["data"]["altitude"] = int(message.data["altitude"])
            doc["data"]["time"] = {}
            doc["data"]["time"]["hour"] = int(message.data["time"]["hour"])
            doc["data"]["time"]["minute"] = int(message.data["time"]["minute"])
            doc["data"]["time"]["second"] = int(message.data["time"]["second"])
        except KeyError:
            raise ValueError(
                "Could not find required data in a LISTENER_TELEM message.")
        except (ValueError, TypeError):
            raise ValueError(
                "Invalid data type found in LISTENER_TELEM message.")
        hour = doc["data"]["time"]["hour"]
        minute = doc["data"]["time"]["minute"]
        second = doc["data"]["time"]["second"]
        if (
            hour < 0 or hour > 12 or minute < 0 or minute > 59 or
            second < 0 or second > 61
            ):
                raise ValueError(
                    "Invalid time value found in LISTENER_TELEM message.")
        self.server.db.save_doc(doc)

