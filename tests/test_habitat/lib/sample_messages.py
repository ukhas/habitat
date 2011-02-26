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

from habitat.message_server import Message, Listener

class SMessage(Message):
    def __init__(self, source=False, type=Message.RECEIVED_TELEM,
                 time_created=12345, time_received=54321, data=False,
                 testid=0):

        if not source:
            source = Listener("M0ZDR", "127.0.0.1")

        if not data:
            if type == Message.RECEIVED_TELEM:
                data = "SSBrbm93IHdoZXJlIHlvdSBsaXZlLgo="
            elif type == Message.LISTENER_INFO:
                data = {"name": "Habitatat", "location": "He's behind you!",
                        "radio": "Nerve endings on my tongue",
                        "antenna": "Flagpole"}
            elif type == Message.LISTENER_TELEM:
                data = {"time": {"hour": 12, "minute": 40, "second": 7},
                        "latitude": 52, "longitude": 137, "altitude": -5}
            elif type == Message.TELEM:
                data = {"_protocol": "URANDOM",
                        "_raw": "SSBrbm93IHdoZXJlIHlvdSBsaXZlLgo=",
                        "sentence": "But what is the question?",
                        "lock_status": "I have no clue where I am"}

        Message.__init__(self, source, type, time_created, time_received, data)
        self.testid = testid
