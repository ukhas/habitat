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

from couch_named_python import ForbiddenError, version
from .utils import read_json_schema, validate_doc, must_be_admin
from .utils import rfc3339_to_timestamp

schema = None

def _validate_ukhas(sentence):
    """
    For UKHAS sentences, check that the checksum is an allowable type and that
    fields with structural requirements are valid.
    """
    checksums = ["xor", "crc16-ccitt", "fletcher-16", "fletcher-16-256",
                 "none"]
    if 'checksum' in sentence:
        if sentence['checksum'] not in checksums:
            raise ForbiddenError("Invalid checksum algorithm.")
    else:
        raise ForbiddenError("UKHAS sentences must have a checksum.")

    if 'fields' in sentence:
        if len(sentence['fields']) < 1:
            raise ForbiddenError(
                "UKHAS sentences must have at least one field.")

        for field in sentence['fields']:
            if field['sensor'] == "stdtelem.coordinate":
                if 'format' not in field:
                    raise ForbiddenError(
                        "Coordinate fields must have formats.")
    else:
        raise ForbiddenError("UKHAS sentences must have fields.")

def _validate_rtty(transmission):
    """
    For RTTY transmissions, verify that required keys are present.
    """
    required_keys = ['shift', 'encoding', 'baud', 'parity', 'stop']
    for k in required_keys:
        if k not in transmission:
            raise ForbiddenError(
                "RTTY transmissions must include '{0}'.".format(k))

def _validate_filter(f):
    """
    Check that filters have the required keys according to their type.
    """
    required_keys = {
        'normal': ['callable'],
        'hotfix': ['code', 'signature', 'certificate']}
    for k in required_keys[f['type']]:
        if k not in f:
            raise ForbiddenError(
                "{0} filters must include '{1}'.".format(f['type'], k))

@version(1)
def validate(new, old, userctx, secobj):
    """
    Validate payload_configuration documents against the schema and then
    against specific validation requirements.

    * Must match schema
    * If editing, must be an administrator
    * If there are any sentences with protocol=UKHAS:
        * Checksum must be a valid type if provided
        * Must have at least one field
        * Coordinate fields must have a format
    * If any sentences have filters:
        * Normal filters must specify a callable
        * Hotfix filters must specify code, a signature and a certificate
    * If any transmissions have modulation=RTTY:
        * Must also specify shift, encoding, baud, parity and stop.

    """
    global schema
    if not schema:
        schema = read_json_schema("payload_configuration.json")
    if 'type' in new and new['type'] == "payload_configuration":
        validate_doc(new, schema)

    if old:
        must_be_admin(userctx)

    if 'sentences' in new:
        for sentence in new['sentences']:
            if sentence['protocol'] == "UKHAS":
                _validate_ukhas(sentence)
            if 'filters' in sentence:
                if 'intermediate' in sentence['filters']:
                    for f in sentence['filters']['intermediate']:
                        _validate_filter(f)
                if 'post' in sentence['filters']:
                    for f in sentence['filters']['post']:
                        _validate_filter(f)

    if 'transmissions' in new:
        for transmission in new['transmissions']:
            if transmission['modulation'] == "RTTY":
                _validate_rtty(transmission)

@version(1)
def name_time_created_map(doc):
    """
    View: ``payload_configuration/name_time_created``

    Emits::

        [name, time_created] -> null

    Used to get a list of all current payload configurations, for display
    purposes or elsewhere where sorting by name is useful.
    """
    if doc['type'] == "payload_configuration":
        created = rfc3339_to_timestamp(doc['time_created'])
        yield (doc['name'], created), None

@version(1)
def callsign_time_created_map(doc):
    """
    View: ``payload_configuration/callsign_time_created``

    Emits::

        [callsign, time_created] -> sentence 1
        [callsign, time_created] -> sentence 2
        [callsign, time_created] -> ...

    Useful to obtain configuration documents for a given callsign if it can't
    be found via upcoming flights, for example parsing test telemetry.
    """
    if doc['type'] == "payload_configuration":
        if 'sentences' in doc:
            created = rfc3339_to_timestamp(doc['time_created'])
            for sentence in doc['sentences']:
                yield (sentence['callsign'], created), sentence
