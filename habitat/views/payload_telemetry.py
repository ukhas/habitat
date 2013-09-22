# Copyright 2011, 2012, 2013 (C) Adam Greig
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

"""
Functions for the payload_telemetry design document.

Contains schema validation and a view by flight, payload and received time.
"""

import math
import json
import base64
import hashlib
import datetime
import calendar
from couch_named_python import ForbiddenError, UnauthorizedError, version
from strict_rfc3339 import rfc3339_to_timestamp, now_to_rfc3339_utcoffset
from strict_rfc3339 import timestamp_to_rfc3339_utcoffset
from .utils import validate_doc, read_json_schema
from .utils import only_validates

schema = None

def _check_only_new(new, old):
    """
    Raise an error if any items in old are not present unchanged in new.
    """
    for k in old:
        if k == u'_rev':
            continue
        if k not in new:
            raise ForbiddenError("You may not remove objects.")
        if isinstance(old[k], dict):
            _check_only_new(new[k], old[k])
        else:
            if new[k] != old[k]:
                raise ForbiddenError("You may not edit existing items.")

def _is_equal_relaxed_floats(a, b):
    """
    Check that a == b, allowing small float differences
    """

    if isinstance(a, list) or isinstance(a, dict):
        # recursion
        if isinstance(a, list):
            if not isinstance(b, list):
                return False
            keys_iter = xrange(len(a))
        else:
            if not isinstance(b, dict):
                return False
            keys_iter = a

        if len(a) != len(b):
            return False

        return all(_is_equal_relaxed_floats(a[i], b[i]) for i in keys_iter)

    elif isinstance(a, float) or isinstance(b, float):
        if not (isinstance(a, float) or isinstance(a, int)) or \
           not (isinstance(b, float) or isinstance(b, int)):
            return False

        # fast path
        if a == b:
            return True

        # relaxed float comparison.
        # Doubles provide 15-17 bits of precision. Converting to decimal and
        # back should not introduce an error larger than 1e-15, really.
        tolerance = max(a, b) * 1e-14
        return abs(a - b) < tolerance

    else:
        # string, int, bool, None, ...
        return a == b

@version(2)
@only_validates("payload_telemetry")
def validate(new, old, userctx, secobj):
    """
    Validate this payload_telemetry document against the schema, then perform
    some specific checks:

    * Admins may perform any further editing
    * If edited
        * Only the parser may add new fields to data
        * The receivers list may only get new receivers
    * If created
        * Must have one receiver
        * Must have _raw and nothing but _raw in data
    """
    global schema
    if not schema:
        schema = read_json_schema("payload_telemetry.json")
    validate_doc(new, schema)

    if '_admin' in userctx['roles']:
        return

    expect_id = hashlib.sha256(new['data']['_raw']).hexdigest()
    if '_id' not in new or new['_id'] != expect_id:
        raise ForbiddenError("Document ID must be sha256(base64 _raw data)")

    if old:
        if 'parser' not in userctx['roles'] and \
           not _is_equal_relaxed_floats(new['data'], old['data']):
            raise UnauthorizedError("Only the parser may add data to an"
                                    " existing document.")
        for receiver in old['receivers']:
            if (receiver not in new['receivers'] or
               new['receivers'][receiver] != old['receivers'][receiver]):
                   raise ForbiddenError("May not edit or remove receivers.")
    else:
        if len(new['receivers']) != 1:
            raise ForbiddenError("New documents must have exactly one"
                                 "receiver.")
        if set(new['data'].keys()) - set(('_raw', '_fallbacks')):
            raise ForbiddenError("New documents may only have _raw and/or "
                                 "_fallbacks in data.")


def _estimate_time_received(receivers):
    sum_x, sum_x2, n = 0, 0, 0

    for callsign in receivers:
        x = rfc3339_to_timestamp(receivers[callsign]['time_created'])
        sum_x += x
        sum_x2 += x * x
        n += 1

    mean = sum_x / n
    std_dev = math.sqrt((sum_x2 / n) - (mean * mean))

    new_sum_x, new_n = 0, 0

    for callsign in receivers:
        x = rfc3339_to_timestamp(receivers[callsign]['time_created'])
        if abs(x - mean) > std_dev:
            continue
        new_sum_x += x
        new_n += 1

    return new_sum_x / new_n if new_n != 0 else mean

@version(1)
def flight_payload_time_map(doc):
    """
    View: ``payload_telemetry/flight_payload_time``

    Emits::

        [flight_id, payload_configuration_id, estimated_time_received] -> null

    Useful to find telemetry related to a certain flight.
    """
    if doc['type'] != "payload_telemetry" or '_parsed' not in doc['data']:
        return

    estimated_time = _estimate_time_received(doc['receivers'])

    parsed = doc['data']['_parsed']
    if 'flight' in parsed:
        flight = parsed['flight']
        config = parsed['payload_configuration']
        yield (flight, config, estimated_time), None

@version(1)
def payload_time_map(doc):
    """
    View: ``payload_telemetry/payload_time``

    Emits::

        [payload_configuration_id, estimated_time_received] -> null

    Useful to find telemetry related to a specific payload_configuration.
    """
    if doc['type'] != "payload_telemetry" or '_parsed' not in doc['data']:
        return

    estimated_time = _estimate_time_received(doc['receivers'])

    parsed = doc['data']['_parsed']
    yield (parsed['payload_configuration'], estimated_time), None

@version(1)
def time_map(doc):
    """
    View: ``payload_telemetry/time``

    Emits::

        estimated_time_received -> is_flight_telemetry

    Useful to get recent telemetry uploaded to habitat.

    This can also be used to make a simple map application. It's worth noting
    that such a technique is a bit of a bodge, since estimated_time_received
    will not necessarily (but could) update if another receiver is added to
    the doc, so asking this view for all telemetry since
    min(the last poll, the most recent telemetry I have) is not infallible.
    That said, doing a proper sync is quite difficult.
    """
    if doc['type'] != "payload_telemetry" or '_parsed' not in doc['data']:
        return

    estimated_time = _estimate_time_received(doc['receivers'])
    parsed = doc['data']['_parsed']
    yield estimated_time, ('flight' in parsed)

@version(1)
def add_listener_update(doc, req):
    """
    Update function: ``payload_telemetry/_update/add_listener``

    Given a prototype payload_telemetry JSON document in the request body,
    containing just the _raw telemetry string and one entry in receivers,
    create the document or merge this listener into it as appropriate.

    Used by listeners when a new payload telemetry string has been received.

    Usage::

        PUT /habitat/_design/payload_telemetry/_update/add_listener/<doc ID>

        {
            "data": {
                "_raw": "<base64 raw telemetry data>"
            },
            "receivers": {
                "<receiver callsign>": {
                    "time_created": "<RFC3339 timestamp>",
                    "time_uploaded": "<RFC3339 timestamp>",
                    <other keys as desired, for instance
                     latest_listener_telemetry, latest_listener_info, etc>
                }
            }
        }

    The document ID should be sha256(doc["data"]["_raw"]) in hexadecimal.

    Returns "OK" if everything was fine, otherwise CouchDB will raise an error.
    Errors might occur in validation (in which case the validation error is
    returned) or because of a save conflict. In the event of a save conflict,
    uploaders should retry the same request until the conflict is resolved.
    """
    protodoc = json.loads(req["body"])
    if "data" not in protodoc or "_raw" not in protodoc["data"]:
        raise ForbiddenError("doc.data._raw is required")
    if "receivers" not in protodoc or len(protodoc["receivers"]) != 1:
        raise ForbiddenError("doc.receivers must exist and have one receiver")
    callsign = protodoc["receivers"].keys()[0]
    protodoc["receivers"][callsign]["time_server"] = now_to_rfc3339_utcoffset()
    if not doc:
        doc = {"_id": req["id"], "type": "payload_telemetry",
               "data": {"_raw": protodoc["data"]["_raw"]}, "receivers": {}}
    doc["receivers"][callsign] = protodoc["receivers"][callsign]
    return doc, "OK"

@version(3)
def http_post_update(doc, req):
    """
    Update function: ``payload_telemetry/_update/http_post``

    Creates a new payload_telemetry document with all keys present in the HTTP
    POST form data available in ``doc.data._fallbacks`` and the ``from`` HTTP
    querystring key as the receiver callsign if available. The ``data`` field
    will be base64 encoded and used as ``doc.data._raw``.

    This function has additional functionality specific to RockBLOCKs: if all
    of the keys ``imei``, ``momsn``, ``transmit_time``, ``iridium_latitude``,
    ``iridium_longitude``, ``iridium_cep`` and ``data`` are present in the form
    data, then:
    * ``imei`` will be copied to ``doc.data._fallbacks.payload`` so it can be
      used as a payload callsign.
    * ``iridium_latitude`` and ``iridium_longitude`` will be copied to
      ``doc.data._fallbacks.latitude`` and ``longitude`` respectively.
    * ``data`` will be hex decoded before base64 encoding so it can be directly
      used by the binary parser module.
    * ``transmit_time`` will be decoded into an RFC3339 timestamp and used for
      the ``time_created`` field in the receiver section.
    * ``transmit_time`` will be decoded into hours, minutes and seconds and
      copied to ``doc.data._fallbacks.time``.

    Usage::

        POST /habitat/_design/payload_telemetry/_update/http_post?from=callsign
        
        data=hello&imei=whatever&so=forth

    This update handler may not currently be used on existing documents or
    with a PUT request; such requests will fail.

    Returns "OK" if everything was fine, otherwise CouchDB will return a
    (hopefully instructive) error.
    """
    if doc is not None:
        resp = {"headers": {"code": 405,
                            "body": "This update function may only be used to "
                                    "create new documents via POST, not with  "
                                    "an existing document ID on a PUT request."
                           }
        }
        return doc, resp

    form = req["form"]
    tc = ts = now_to_rfc3339_utcoffset()
    rawdata = base64.b64encode(form["data"])
    if set(("imei", "momsn", "transmit_time", "iridium_latitude",
           "iridium_longitude", "iridium_cep", "data")) <= set(form.keys()):
        form["payload"] = form["imei"]
        form["latitude"] = float(form["iridium_latitude"])
        form["longitude"] = float(form["iridium_longitude"])
        rawdata = base64.b64encode(form["data"].decode("hex"))
        fmt = "%y-%m-%d %H:%M:%S"
        tc = datetime.datetime.strptime(form["transmit_time"], fmt)
        form["time"] = tc.strftime("%H:%M:%S")
        tc = timestamp_to_rfc3339_utcoffset(calendar.timegm(tc.timetuple()))
    receiver = req["query"]["from"] if "from" in req["query"] else "HTTP POST"
    doc_id = hashlib.sha256(rawdata).hexdigest()
    doc = {"_id": doc_id, "type": "payload_telemetry",
            "data": {"_raw": rawdata, "_fallbacks": form}, "receivers": {}}
    doc["receivers"][receiver] = {"time_created": tc, "time_uploaded": ts,
                                  "time_server": ts}
    return doc, "OK"
