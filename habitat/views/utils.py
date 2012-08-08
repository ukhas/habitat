# Copyright 2011, 2012 (C) Adam Greig
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
Shared utility functions for views.
"""

import os
import json
import inspect
import re

from couch_named_python import UnauthorizedError, ForbiddenError
from jsonschema import Validator
from dateutil.parser import parse
from dateutil.tz import tzutc
from calendar import timegm

rfc3339_regex = re.compile(
    "(\d\d\d\d)(-)?(\d\d)(-)?(\d\d)(T)"
    "(\d\d)(:)?(\d\d)(:)?(\d\d)(\.\d+)?(Z|([+-])(\d\d)(:)?(\d\d))")

def read_json_schema(schemaname):
    mypath = os.path.dirname(inspect.getfile(inspect.currentframe()))
    path = os.path.join(mypath, "..", "..", "couchdb", "schemas", schemaname)
    with open(path) as f:
        schema = json.load(f)
    return schema

def validate_rfc3339(datestring):
    """Check an RFC3339 string is valid via a regex."""
    return rfc3339_regex.match(datestring) is not None

def rfc3339_to_datetime(datestring):
    """Convert an RFC3339 date-time string to a datetime"""
    return parse(datestring)

def rfc3339_to_utc_datetime(datestring):
    """Convert an RFC3339 date-time string to a UTC datetime"""
    return rfc3339_to_datetime(datestring).astimezone(tzutc())

def rfc3339_to_timestamp(datestring):
    """Convert an RFC3339 date-time string to a UTC UNIX timestamp"""
    return timegm(rfc3339_to_utc_datetime(datestring).utctimetuple())

def datetime_to_timestamp(dt):
    """Convert a datetime object to a UTC UNIX timestamp"""
    return timegm(dt.utctimetuple())

def must_be_admin(user,
                  msg="Only server administrators may edit this document."):
    """Raise UnauthorizedError if the user is not an admin"""
    try:
        if '_admin' not in user['roles']:
            raise UnauthorizedError(msg)
    except (KeyError, TypeError):
        raise UnauthorizedError(msg)

def _validate_timestamps(data, schema):
    """Go through schema finding format:date-time and validate it's RFC3339."""
    if 'format' in schema and schema['format'] == "date-time":
        if not validate_rfc3339(data):
            raise ForbiddenError("A date-time was not in the required format.")
    if 'properties' in schema and isinstance(schema['properties'], dict):
        try:
            for key, value in data.items():
                _validate_timestamps(value, schema['properties'][key])
        except (TypeError, KeyError):
            pass
    if 'additionalProperties' in schema:
        if isinstance(schema['additionalProperties'], dict):
            try:
                for value in data.values():
                    _validate_timestamps(value, schema['additionalProperties'])
            except TypeError:
                pass
    if 'items' in schema and isinstance(schema['items'], dict):
        try:
            for item in data:
                _validate_timestamps(item, schema['items'])
        except TypeError:
            pass

def validate_doc(data, schema):
    """Validate *data* against *schema*, raising descriptive errors"""
    v = Validator()
    errors = list(v.iter_errors(data, schema))
    if errors:
        errors = ', '.join((str(error) for error in errors))
        raise ForbiddenError("Validation errors: {0}".format(errors))
    _validate_timestamps(data, schema) 
