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

from message_server import SimpleSink, Message

class FakeSink2(SimpleSink):
    def setup(self):
        pass
    def message(self):
        pass

class TestSink(SimpleSink):
    def setup(self):
        self.test_messages = []
        self.set_types(set(self.testtypes))
    def message(self, message):
        self.test_messages.append(message)

class TestSinkA(TestSink):
    testtypes = [Message.RECEIVED_TELEM, Message.LISTENER_INFO]

class TestSinkB(TestSink):
    testtypes = [Message.LISTENER_INFO]
