# Copyright 2011 (C) Adam Greig
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

from couch_named_python import Unauthorized, Forbidden
from jsonschema import ValidationError, validate
from dateutil.parser import parse
from dateutil.tz import tzutc
from calendar import timegm

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

def must_be_admin(user):
    """Raise Unauthorized if the user is not an admin"""
    try:
        if 'admin' not in user['roles']:
            raise Unauthorized("Only administrators may edit this document.")
    except (KeyError, TypeError):
        raise Unauthorized("Only administrators may edit this document.")

def validate_doc(data, schema):
    """Validate *data* against *schema*, raising descriptive errors"""
    try:
        validate(data, schema, unknown_property="skip", stop_on_error=False)
    except ValidationError as e:
        out = "Validation errors: " + "; ".join(sorted(e.errors))
        raise Forbidden(out)
