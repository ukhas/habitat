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

import threading

class LockTroll(threading.Thread):
    def __init__(self, lock):
	threading.Thread.__init__(self)
	self.name = "Test Thread: LockTroll"
	self.lock = lock
	self.stop = threading.Event()
	self.started = threading.Event()

    def start(self):
	threading.Thread.start(self)
	self.started.wait()

    def run(self):
	with self.lock:
	    self.started.set()
	    self.stop.wait()

    def release(self):
	self.stop.set()
	self.join()
