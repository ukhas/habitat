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

from habitat.message_server import SimpleSink, ThreadedSink, Message

class PushbackSink():
    def setup(self):
        self.add_type(Message.RECEIVED_TELEM)
        self.add_type(Message.TELEM)
        self.status = 0

    def message(self, message):
        assert message.data == 6293

        if self.status == 0:
            assert message.type == Message.RECEIVED_TELEM
            self.pbmsg = Message(message.source, Message.TELEM, message.data)
            self.status = 1
            self.server.push_message(self.pbmsg)
        elif self.status == 1:
            assert message == self.pbmsg
            self.status = 2
        else:
            raise AssertionError

class PushbackReceiverSink():
    def setup(self):
        self.add_type(Message.TELEM)
        self.status = 0

    def message(self, message):
        assert message.data == 6293
        assert self.status == 0
        self.status = 2

class PushbackSimpleSink(PushbackSink, SimpleSink):
    pass
class PushbackThreadedSink(PushbackSink, ThreadedSink):
    pass
class PushbackReceiverSimpleSink(PushbackReceiverSink, SimpleSink):
    pass
class PushbackReceiverThreadedSink(PushbackReceiverSink, ThreadedSink):
    pass
