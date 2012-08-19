# Copyright 2012 (C) Daniel Richman, Adam Greig
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
Super simple lightweight RFC3339 functions

Goals
=====

 - Simple with minimal dependencies/libraries so that they are less likely
   to break in complicated situations like DST transitions
 - Convert unix timestamps to and from RFC3339
 - Avoid timezones as much as possible
 - Either produce RFC3339 strings with a UTC offset (Z) or with the offset
   that the C time module reports is the local timezone offset.

Rationale/reasons for this file:
================================

 - Other libraries have trouble with DST transitions and ambiguous times.
   The excellent pytz library doesn't, however it doesn't have a method for
   getting the local timezone or the 'now' time in the local zone.
 - Generally, using the python datetime object seems to be more trouble than
   it's worth, introducing problems with timezones. Also, they don't support
   leap seconds (timestamps don't either, but it's still a bit disappointing).
 - (anecdotal observation): other libraries suffer DST problems (etc.) because
   of information lost when converting or transferring between two libraries
   (e.g., time -> datetime loses DST info in the tuple) - so try to keep that
   to an absolute minimum.
 - Timezones. eww.

The things powering these functions
===================================

These functions are essentially string and integer operations only. A very 
small number of functions do the heavy lifting. These come from two modules:
time and calendar.

time is a thin wrapper around the C platform's time libraries. This is good
because these are most likely of high quality and always correct. From the
time library, we use:

 - time: (actually calls gettimeofday) provides 'now' -> timestamp
 - gmtime: splits a timestamp into a UTC time tuple
 - localtime: splits a timestamp into a local time tuple
   _including_ the 'is DST' flag
 - timezone: variable that provides the local timezone offset
 - altzone: variable that provides the local timezone DST offset

Based on the (probably correct) assumption that gmtime and localtime are
always right, we can use gmtime and localtime, and take the difference in order
to figure out what the local offset is. As clunky as it sounds, it's far easier
than using a fully fledged timezone library.

calendar is implemented in python. From calendar, we use

 - timegm: turns a UTC time tuple into a timestamp. This essentially just
   multiplies each number in the tuple by the number of seconds in it. It
   does use datetime.date to work out the number of days between Jan 1 1970
   and the ymd in the tuple, but that should be OK. It does not perform much
   validation at all.
 - monthrange: gives the number of days in a (year, month). I checked and
   (atleast in my copy of python 2.6) the function used for leap years is
   identical to the one specified in RFC3339.

Notes
=====

 - RFC3339 specifies an offset, not a timezone. Timezones are evil and will
   make you want to hurt yourself.
 - Although slightly roundabout, it might be simpler to consider RFC3339
   times as a human readable method of specifying a moment in time (only).
   Sure, there can be many RFC3339 strings that represent one moment in time,
   but that doesn't really matter.
   An RFC3339 string represents a moment in time unambiguously and you do
   not need to consult timezone data in order to work out the UTC time
   represented by a RFC3339 time.
   Really, these functions merely provide a way of converting RFC3339 times to
   exactly equivalent integers/floats and back.
 - Note that timestamps don't support leap seconds: a day is always 86400.
   Also, validating leap seconds is extra difficult, because you'd to access
   to up-to-date tzdata.
   For this reason I've drawn the line at supporting leap seconds in habitat:
   In validation, seconds == 60 or seconds == 61 are rejected.
   In the case of reverse leap seconds, calendar.timegm will blisfully accept
   it. The result would be about as correct as you could get.
 - RFC3339 generation using gmtime or localtime may be limited by the size
   of time_t on the system: if it is 32 bit, you're limited to dates between
   (approx) 1901 and 2038. This does not affect rfc3339_to_timestamp.

"""

import re
import time
import calendar

rfc3339_regex = re.compile(
    r"(\d\d\d\d)\-(\d\d)\-(\d\d)T"
    r"(\d\d):(\d\d):(\d\d)(\.\d+)?(Z|([+\-])(\d\d):(\d\d))")

def validate_rfc3339(datestring):
    """Check an RFC3339 string is valid via a regex and some range checks"""

    m = rfc3339_regex.match(datestring)
    if m is None:
        return False

    groups = m.groups()

    year, month, day, hour, minute, second = [int(i) for i in groups[:6]]

    if not 1 <= month <= 12:
        return False

    (_, max_day) = calendar.monthrange(year, month)
    if not 1 <= day <= max_day:
        return False

    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        # forbid leap seconds :-(. See above
        return False

    if groups[7] != "Z":
        (offset_sign, offset_hours, offset_mins) = groups[8:]
        if not (0 <= int(offset_hours) <= 23 and 0 <= int(offset_mins) <= 59):
            return False

    # all OK
    return True

def rfc3339_to_timestamp(datestring):
    """Convert an RFC3339 date-time string to a UTC UNIX timestamp"""

    validate_rfc3339(datestring)
    groups = rfc3339_regex.match(datestring).groups()

    time_tuple = [int(p) for p in groups[:6]]
    timestamp = calendar.timegm(time_tuple)

    seconds_part = groups[6]
    if seconds_part is not None:
        timestamp += float("0" + seconds_part)

    if groups[7] != "Z":
        (offset_sign, offset_hours, offset_mins) = groups[8:]
        offset_seconds = int(offset_hours) * 3600 + int(offset_mins) * 60
        if offset_sign == '-':
            offset_seconds = -offset_seconds
        timestamp -= offset_seconds

    return timestamp

def _make_datestring_start(time_tuple, seconds_part):
    ds_format = "{0:04d}-{1:02d}-{2:02d}T{3:02d}:{4:02d}:{5:02d}"
    datestring = ds_format.format(*time_tuple)

    seconds_part_str = "{0:06d}".format(int(round(seconds_part * 1e6)))
    seconds_part_str = seconds_part_str.rstrip("0")
    if seconds_part_str != "":
        datestring += "." + seconds_part_str

    return datestring

def timestamp_to_rfc3339_utcoffset(timestamp):
    """Convert a UTC UNIX timestamp to RFC3339, with the offset as 'Z'"""
    timestamp_int = int(timestamp)
    seconds_part = timestamp % 1

    time_tuple = time.gmtime(timestamp_int)
    datestring = _make_datestring_start(time_tuple, seconds_part)
    datestring += "Z"

    assert abs(rfc3339_to_timestamp(datestring) - timestamp) < 0.000001
    return datestring

def timestamp_to_rfc3339_localoffset(timestamp):
    """
    Convert a UTC UNIX timestamp to RFC3339, using the local offset.
    
    localtime() provides the time parts. The difference between gmtime and
    localtime tells us the offset.
    """

    timestamp_int = int(timestamp)
    seconds_part = timestamp % 1

    time_tuple = time.localtime(timestamp_int)
    datestring = _make_datestring_start(time_tuple, seconds_part)

    gm_time_tuple = time.gmtime(timestamp_int)
    offset = calendar.timegm(time_tuple) - calendar.timegm(gm_time_tuple)

    if abs(offset) % 60 != 0:
        raise ValueError("Your local offset is not a whole minute")

    offset_minutes = abs(offset) / 60
    offset_hours = offset_minutes // 60
    offset_minutes %= 60

    offset_string = "{0:02d}:{1:02d}".format(offset_hours, offset_minutes)

    if offset < 0:
        datestring += "-"
    else:
        datestring += "+"

    datestring += offset_string
    assert abs(rfc3339_to_timestamp(datestring) - timestamp) < 0.000001

    return datestring

def now_to_rfc3339_utcoffset(integer=True):
    """Convert the current time to RFC3339, with the offset as 'Z'"""

    timestamp = time.time()
    if integer:
        timestamp = int(timestamp)
    return timestamp_to_rfc3339_utcoffset(timestamp)

def now_to_rfc3339_localoffset(integer=True):
    """Convert the current time to RFC3339, using the local offset."""

    timestamp = time.time()
    if integer:
        timestamp = int(timestamp)
    return timestamp_to_rfc3339_localoffset(timestamp)
