# Copyright 2011, 2012 (C) Adam Greig, Daniel Richman
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
import base64
import pytz

from couch_named_python import UnauthorizedError, ForbiddenError
from jsonschema import Validator
from strict_rfc3339 import validate_rfc3339

timestr_regex = re.compile(r"(\d\d):(\d\d):(\d\d)")

def read_json_schema(schemaname):
    mypath = os.path.dirname(inspect.getfile(inspect.currentframe()))
    path = os.path.join(mypath, "..", "..", "couchdb", "schemas", schemaname)
    with open(path) as f:
        schema = json.load(f)
    return schema

def must_be_admin(user,
                  msg="Only server administrators may edit this document."):
    """Raise UnauthorizedError if the user is not an admin"""
    try:
        if '_admin' not in user['roles']:
            raise UnauthorizedError(msg)
    except (KeyError, TypeError):
        raise UnauthorizedError(msg)

def _validate_timestr(data):
    """Check that a time string is of the format HH:MM:SS"""
    m = timestr_regex.match(data)
    if m is None:
        return False

    hour, minute, second = [int(i) for i in m.groups()]
    return (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 60)

def _validate_base64(data):
    """Check that a string is valid base64. Note: forbids whitespace"""
    try:
        decoded = base64.b64decode(data)
    except TypeError:
        return False

    # Some clients rely on the base64 not containing any whitespace.
    # b64encode produces a string without any whitespace, so...
    if base64.b64encode(decoded) != data:
        return False

    return True

def _validate_timezone(data):
    """Check that a string is a valid Olson specifier"""
    return data in pytz.all_timezones

def _validate_formats(data, schema):
    """Go through schema checking the formats date-time, time and base64"""
    if 'format' in schema:
        format_name = schema['format']
        if format_name == "date-time" and not validate_rfc3339(data):
            raise ForbiddenError("A date-time was not in the required format.")
        elif format_name == "time" and not _validate_timestr(data):
            raise ForbiddenError("A time was not in the required format.")
        elif format_name == "base64" and not _validate_base64(data):
            raise ForbiddenError("A string was not valid base64.")
        elif format_name == "timezone" and not _validate_timezone(data):
            raise ForbiddenError("A string was not a valid timezone.")
    if 'properties' in schema and isinstance(schema['properties'], dict):
        for key, value in data.items():
            try:
                _validate_formats(value, schema['properties'][key])
            except (TypeError, KeyError):
                pass
    if 'additionalProperties' in schema:
        if isinstance(schema['additionalProperties'], dict):
            for value in data.values():
                try:
                    _validate_formats(value, schema['additionalProperties'])
                except TypeError:
                    pass
    if 'items' in schema and isinstance(schema['items'], dict):
        for item in data:
            try:
                _validate_formats(item, schema['items'])
            except TypeError:
                pass

def validate_doc(data, schema):
    """Validate *data* against *schema*, raising descriptive errors"""
    v = Validator()
    errors = list(v.iter_errors(data, schema))
    if errors:
        errors = ', '.join((str(error) for error in errors))
        raise ForbiddenError("Validation errors: {0}".format(errors))
    _validate_formats(data, schema) 

def only_validates(doc_type):
    def decorator(func):
        def wrapped(new, old, userctx, secobj):
            new_type = new.get("type", None)
            new_deleted = new.get("_deleted", False)
            if old:
                old_type = old.get("type", None)
            else:
                old_type = None

            # sanity checks
            if old_type is None:
                assert old == {} or old is None
            if new_deleted:
                assert new_type is None

            if new_type == doc_type and old_type in [None, doc_type]:
                # new doc, or modified doc of correct type. validate:
                return func(new, old, userctx, secobj)

            elif new_deleted and old_type == doc_type:
                # deletion is managed by habitat.validate
                return

            elif new_type == doc_type or old_type == doc_type:
                # one or the other types match but not both, and not a new or deleted doc.
                raise ForbiddenError("You cannot change the type of a doc")

            else:
                # other type: not our business
                return

        # Be a well behaved decorator!
        wrapped.__name__ = func.__name__
        wrapped.__doc__ = func.__doc__
        wrapped.__dict__.update(func.__dict__)

        return wrapped
    return decorator
