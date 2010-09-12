
# Copyright 2010 (C) Daniel Richman
#
# This file is part of reHAB.
#
# reHAB is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# reHAB is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with reHAB.  If not, see <http://www.gnu.org/licenses/>.

"""
Basic sanity checks: the classes are in the correct location on the python
path and import successfully
""" 

class TestSanity:
    def test_sink(self):
        from message_server import Sink

