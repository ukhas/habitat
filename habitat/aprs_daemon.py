# Copyright 2013 (C) Rossen Georgiev
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
Run the APRS importer as a daemon watching flight docs in CouchDB
and listening for position data on aprs-is
"""

import couchdbkit
import copy
import logging
import statsd
import time
import base64
import datetime
import hashlib

from . import aprs

logger = logging.getLogger("habitat.aprs_daemon")
statsd.init_statsd({'STATSD_BUCKET_PREFIX': 'habitat'})

__all__ = ['APRSDaemon']

class APRSDaemon(object):
    """
    :class:`APRSDaemon` runs persistently, watching flight docs in CouchDB
    and looking for flights set to use APRS. Upon which starts polling aprs.fi
    for position data for every callsign and converting it to habitat telemetry
    """

    def __init__(self, config, daemon_name="aprsdaemon"):
        """
        On construction, it will:

        * Connect to CouchDB using ``self.config["couch_uri"]`` and
          ``config["couch_db"]``.
        """

        self.config = copy.deepcopy(config)

        # holds { callsign : chase (bool) }, chase is true for chaser callsigns
        self.callsigns = {}

        self.couch_server = couchdbkit.Server(config["couch_uri"])
        self.db = self.couch_server[config["couch_db"]]

        self.aprs = aprs.aprs(self.config['aprsdaemon']['server'],
                              self.config['aprsdaemon']['port'],
                              self.config['aprsdaemon']['login']['callsign'],
                              self.config['aprsdaemon']['login']['password'])

        self.next_update = 0


    def run(self):

        self.fetch_active_flights()
        self.aprs.connect(blocking=True) # keeps trying to connect until success

        while True:
            if time.time() > self.next_update:
                self.fetch_active_flights()

            self.aprs.consumer(self.habitat_upload, blocking=False, immortal=True)
            time.sleep(1)

    def habitat_upload(self, data):
        source_callsign = data['source']

        if source_callsign in self.callsigns:
            attempts = 0
            while True:
                try:
                    if self.callsigns[source_callsign] is 0: # payload callsign
                        result = self._save_payload_telemetry_doc(data)
                    else: # 1, chaser callsign
                        result = self._save_listener_telemetry_doc(data)

                    if 'ok' not in result and result['ok'] is not True:
                        raise Exception(result)

                    logger.debug("Saved doc %s successfully" % result['id'])
                    break
                except couchdbkit.exceptions.ResourceConflict:
                    if attempts >= 10:
                        err = "Could not save doc after {1} conflicts." \
                                .format(doc["_id"], attempts)
                        logger.error(err)
                        break;
                    else:
                        logger.debug("Save conflict, trying again (#{0})" \
                            .format(attempts))
                        time.sleep(0.1)
                except Exception, e:
                    logger.error(e)

                attempt += 1
        else:
            logger.debug("no active flight for '%s'" % data['source'])

    def fetch_active_flights(self):
        """
        Pulls all active flights from habitat and listens for them on aprs servers
        """
        self.next_update = time.time() + self.config['aprsdaemon']['flight_check_interval']

        logger.info("Checking for active flights")

        self.callsigns = {}
        flight_count = 0

        # get the current active flights
        for flight in self.db.view("flight/end_start_including_payloads", include_docs=True, startkey=[time.time()]).all():
            if (flight['key'][3] == 1                # is flight doc
                and 'aprs' in flight['doc']          # flight doc contains 'aprs' attribute
                and flight['key'][3] < time.time()   # we are past start time, so inside the flight window
                and len(flight['doc']['aprs'])):      # contains some callsigns

                # separate payloads
                if 'payloads' in flight['doc']['aprs']:
                    self.callsigns.update({cs: 0 for cs in current['payloads']})

                # separate chaser callsigns
                if 'chasers' in flight['doc']['aprs']:
                    self.callsigns.update({cs: 1 for cs in current['chasers']})

                flight_count += 1

        logger.info("%d active flight(s) with %d callsign(s)" % (flight_count, len(self.callsigns)))

        # updates aprs.net filter
        self.aprs.callsign_filter([x for x in self.callsigns])

    def _save_listener_telemetry_doc(self, data):
        doc = {
                'type': "listener_telemetry",
                'time_created': datetime.datetime.utcnow().isoformat() + 'Z',
                'time_uploaded': datetime.datetime.utcnow().isoformat() + 'Z',
                'data': {
                    'callsign': data['source'],
                    'latitude': data['latitude'],
                    'longitude': data['longitude'],
                    'chase': True
                },
              }

        if 'altitude' in data:
            doc['data'].update({'altitude': data['altitude']})

        if 'speed' in data:
            doc['data'].update({'speed': data['speed']})

        return self.db.save_doc(doc)

    def _save_payload_telemetry_doc(self, data):
        doc = {
                'type': "payload_telemetry",
                'data': {
                    '_raw': base64.b64encode(data['raw']),
                    '_sentence': data['raw'],
                    '_protocol': "APRS",
                    'payload': data['source'],
                    'latitude': data['latitude'],
                    'longitude': data['longitude'],
                    '_fix_invalid': True
                },
                'receivers': {
                   data['path'][-2]: { # reciever callsign
                    'time_created': datetime.datetime.utcnow().isoformat() + 'Z',
                    'time_uploaded': datetime.datetime.utcnow().isoformat() + 'Z',
                    }
                }
              }

        if 'altitude' in data:
            doc['data'].update({'altitude': data['altitude']})

        if 'bearing' in data:
            doc['data'].update({'bearing': data['bearing']})

        if 'speed' in data:
            doc['data'].update({'speed': data['speed']})

        if 'comment' in data and not not data['comment']:
            doc['data'].update({'comment': data['comment']})

        doc.update({'_id': hashlib.sha256(doc['data']['_raw']).hexdigest()})

        return self.db.save_doc(doc)


