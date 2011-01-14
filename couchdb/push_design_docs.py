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

from couchdbkit import Server
from couchdbkit.designer import push

# Find out the URI and DB to connect to
uri = raw_input("CouchDB URI [http://localhost:5984]: ")
db = raw_input("CouchDB Database [habitat]: ")

if uri == "":
    uri = "http://localhost:5984"
if db == "":
    db = "habitat"

# Establish connection
s = Server(uri)
db = s[db]

# Push documents up
push("habitat", db)
