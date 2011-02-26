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

import os
import json
from couchdbkit import Server
from couchdbkit.designer import push
from couchdbkit import exceptions

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

# Load sample documents if they don't exist
docs = os.listdir("docs/")
for doc in docs:
    f = open("docs/" + doc)
    doc = json.loads(f.read())
    f.close()
    try:
        db.save_doc(doc)
    except exceptions.ResourceConflict:
        print "Document <" + doc["_id"] + "> already in database, skipping."
        continue

# Push habitat design documents (this is done second as the design
# doc prevents the creation of non-flight documents by anything except
# the habitat user)
push("habitat", db)
