#!/usr/bin/python
# Copyright (C) 2010  Daniel Richman
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License,
# see <http://www.gnu.org/licenses/>.

from xml.sax.saxutils import escape
import sys
for l in sys.stdin:
    sys.stdout.write(escape(l))
