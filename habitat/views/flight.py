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

"""
Functions for the flight design document.

Contains schema validation and views by flight launch time, window end time and
payload name and window end time.
"""

from couch_named_python import ForbiddenError, UnauthorizedError, version
from strict_rfc3339 import rfc3339_to_timestamp
from .utils import validate_doc, read_json_schema
from .utils import only_validates

schema = None

@version(1)
@only_validates("flight")
def validate(new, old, userctx, secobj):
    """
    Validate this flight document against the schema, then check that
    only managers are approving documents and approved documents are only
    edited by managers.
    """
    global schema
    if not schema:
        schema = read_json_schema("flight.json")
    validate_doc(new, schema)
    
    if '_admin' in userctx['roles']:
        return

    if new['approved'] and 'manager' not in userctx['roles']:
        raise UnauthorizedError("Only managers may approve documents.")

    if old and 'manager' not in userctx['roles']:
        raise UnauthorizedError("Only managers may edit documents.")

    start = rfc3339_to_timestamp(new['start'])
    end = rfc3339_to_timestamp(new['end'])
    launch = rfc3339_to_timestamp(new['launch']['time'])
    if start > end:
        raise ForbiddenError("Launch window may not end before it starts.")
    if end - start > 7 * 24 * 3600:
        raise ForbiddenError("Launch window may not be greater than one week"
                " (speak to an admin if you have a special requirement).")
    if not start <= launch < end:
        raise ForbiddenError("Launch time must be within launch window.")

    if 'payloads' in new:
        payloads = new['payloads']
        if len(payloads) != len(set(payloads)):
            raise ForbiddenError("Duplicate entries in payloads list")

@version(2)
def end_start_including_payloads_map(doc):
    """
    View: ``flight/end_start_including_payloads``

    Emits::

        [end_time, start_time, flight_id, 0] -> [payload_configuration ids]
        [end_time, start_time, flight_id, 1] -> {linked payload_configuration doc 1}
        [end_time, start_time, flight_id, 1] -> {linked payload_configuration doc 2}
        ...

    Or, when a flight has no payloads::

        [end_time, start_time, flight_id, 0] -> null

    Times are all UNIX timestamps (and therefore in UTC).
    
    Sorts by flight window end time then start time.

    If the flight has payloads, emit it with the list of payloads, and emit
    a link for each payload so that they get included with include_docs. If a
    flight does not have payloads, it is emitted by itself.

    Only shows approved flights.

    Used by the parser to find active flights and get the configurations used
    to decode telemetry from them.

    May otherwise be used to find upcoming flights and their associated
    payloads, though typically the view ``launch_time_including_payloads``
    would be more useful as it sorts by launch time.

    Query using ``startkey=[current_timestamp]`` to get all flights whose
    windows have not yet ended. Use ``include_docs=true`` to have the linked
    payload_configuration documents fetched and returned as the ``"doc"`` key
    for that row, otherwise the row's value will just contain an object that
    holds the linked ID. See the 
    `CouchDB documentation <http://wiki.apache.org/couchdb/Introduction_to_CouchDB_views#Linked_documents>`_
    for details on linked documents.
    """
    if doc['type'] != "flight" or not doc['approved']:
        return
    flight_id = doc['_id']
    et = rfc3339_to_timestamp(doc['end'])
    st = rfc3339_to_timestamp(doc['start'])
    if 'payloads' in doc:
        yield (et, st, flight_id, 0), doc['payloads']
        for payload in doc['payloads']:
            yield (et, st, flight_id, 1), {'_id': payload}
    else:
        yield (et, st, flight_id, 0), None


@version(2)
def launch_time_including_payloads_map(doc):
    """
    View: ``flight/launch_time_including_payloads``

    Emits::

        [launch_time, flight_id, 0] -> [payload_configuration ids]
        [launch_time, flight_id, 1] -> {linked payload_configuration doc 1}
        [launch_time, flight_id, 1] -> {linked payload_configuration doc 2}
        ...

    Or, when a flight has no payloads::
        
        [launch_time, flight_id, 0] -> null

    Times are all UNIX timestamps (and therefore in UTC).

    Sort by flight launch time.
    
    Only shows approved flights.

    Used by the calendar and other interface elements to show a list of
    upcoming flights.

    Query using ``startkey=[current_timestamp]`` to get all upcoming flights.
    Use ``include_docs=true`` to have the linked
    payload_configuration documents fetched and returned as the ``"doc"`` key
    for that row, otherwise the row's value will just contain an object that
    holds the linked ID. See the 
    `CouchDB documentation <http://wiki.apache.org/couchdb/Introduction_to_CouchDB_views#Linked_documents>`_
    for details on linked documents.
    """
    if doc['type'] != "flight" or not doc['approved']:
        return
    flight_id = doc['_id']
    lt = rfc3339_to_timestamp(doc['launch']['time'])
    if 'payloads' in doc:
        yield (lt, flight_id, 0), doc['payloads']
        for payload in doc['payloads']:
            yield (lt, flight_id, 1), {'_id': payload}
    else:
        yield (lt, flight_id, 0), None

@version(1)
def unapproved_name_including_payloads_map(doc):
    """
    View: ``flight/unapproved_name_including_payloads``

    Emits::

        [name, flight_id, 0] -> [payload_configuration ids]
        [name, flight_id, 1] -> {linked payload_configuration doc 1}
        [name, flight_id, 1] -> {linked payload_configuration doc 2}
        ...

    Or, when a flight has no payloads::
        
        [name, flight_id, 0] -> null

    Times are all UNIX timestamps (and therefore in UTC).

    Sort by flight name.
    
    Only shows unapproved flights.

    Used by the administration approval interface to list unapproved flights.

    Use ``include_docs=true`` to have the linked
    payload_configuration documents fetched and returned as the ``"doc"`` key
    for that row, otherwise the row's value will just contain an object that
    holds the linked ID. See the 
    `CouchDB documentation <http://wiki.apache.org/couchdb/Introduction_to_CouchDB_views#Linked_documents>`_
    for details on linked documents.
    """
    if doc['type'] != "flight" or doc['approved']:
        return
    flight_id = doc['_id']
    name = doc['name']
    if 'payloads' in doc:
        yield (name, flight_id, 0), doc['payloads']
        for payload in doc['payloads']:
            yield (name, flight_id, 1), {'_id': payload}
    else:
        yield (name, flight_id, 0), None


@version(1)
def all_name_map(doc):
    """
    View: ``flight/all_name``

    Emits::

        [name] -> null

    Sort by flight name.

    Show all flights, even those unapproved.
    
    Used where the UI must show all the flights in some usefully searchable
    sense, for instance when creating a new flight document based on some old
    or unapproved one, or when approving new flight documents.
    """
    if doc['type'] == "flight":
        yield doc['name'], None
