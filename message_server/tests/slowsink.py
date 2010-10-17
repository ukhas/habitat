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

# This would confuse an earlier version of of the software that would compare
# dynamicloader.fullname with a string "loadable".

import threading
import time
from habitat.message_server import SimpleSink, ThreadedSink, Message

class SlowSink():
    def setup(self):
        self.add_type(Message.TELEM)
        self.in_message = threading.Event()
    def message(self, message):
        self.in_message.set()
        time.sleep(0.02)
        self.in_message.clear()

class SlowSimpleSink(SlowSink, SimpleSink):
    pass
class SlowThreadedSink(SlowSink, ThreadedSink):
    pass

class SlowShutdownSink(SimpleSink):
    def setup(self):
        self.add_type(Message.TELEM)
        self.shutting_down = threading.Event()
        self.messages = 0

    def message(self, message):
        self.messages += 1

    def shutdown(self):
        SimpleSink.shutdown(self)
        self.shutting_down.set()
        time.sleep(0.02)
        self.shutting_down.clear()
