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
from .utils import read_json_schema, validate_doc

schema = None

def _validate_ukhas(sentence):
    """
    For UKHAS sentences, check that the checksum is an allowable type and that
    fields with structural requirements are valid.
    """
    checksums = ["xor", "crc16-ccitt", "fletcher-16", "fletcher-16-256"]
    if 'checksum' in sentence:
        if sentence['checksum'] not in checksums:
            raise ForbiddenError("Invalid checksum algorithm.")
    if 'fields' in sentence:
        for field in sentence['fields']:
            if field['sensor'] == "stdtelem.coordinate":
                if 'format' not in field['sensor']:
                    raise ForbiddenError(
                        "Coordinate fields must have formats.")

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
    Validate payload_configuration documents against the schema.
    """
    global schema
    if not schema:
        schema = read_json_schema("payload_configuration.json")
    if 'type' in new and new['type'] == "payload_configuration":
        validate_doc(new, schema)

    if 'sentences' in new:
        for sentence in new['sentences']:
            if sentence['protocol'] == "UKHAS":
                _validate_ukhas(sentence)
            if 'filters' in sentence:
                for f in sentence['filters']:
                    _validate_filter(f)

    if 'transmissions' in new:
        for transmission in new['transmissions']:
            if transmission['modulation'] == "RTTY":
                _validate_rtty(transmission)

@version(1)
def name_time_created_map(doc):
    """
    Emit (name, date_created).

    Used to get a list of all current payload configurations.
    """
    if doc['type'] == "payload_configuration":
        yield (doc['name'], doc['date_created']), None

@version(1)
def callsign_time_created_map(doc):
    """
    Emit (callsign, created) -> sentence for each callsign in the document.

    Used by the parser when parsing telemetry not in a flight.
    """
    if doc['type'] == "payload_configuration":
        if 'sentences' in doc:
            for sentence in doc['sentences']:
                yield (sentence['callsign'], doc['created']), sentence
