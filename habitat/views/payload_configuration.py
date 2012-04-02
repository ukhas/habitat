# Copyright 2012 (C) Adam Greig
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
Functions for the payload_configuration design document.

Contains schema validation and a view by payload name and configuration
version.
"""

from couch_named_python import version
from .utils import read_json_schema, validate_doc

schema = None

@version(1)
def validate(new, old, userctx, secobj):
    """
    Validate payload_configuration documents against the schema.
    """
    global schema
    if not schema:
        schema = read_json_schema("payload_configuration.json")
    if 'type' in new and new['type'] == "payload_configuration":
        validate_doc(new, schema)

@version(1)
def name_version_map(doc):
    """Emit (name, version)."""
    if 'type' in doc and doc['type'] == "payload_configuration":
        yield (doc['name'], doc['version']), None

@version(1)
def owner_name_version_map(doc):
    """
    Emit (owner, name, version).
    Used for selecting payload configurations belonging to a particular user.
    """
    if 'type' in doc and doc['type'] == "payload_configuration":
        if 'owner' in doc:
            yield (doc['owner'], doc['name'], doc['version']), None
