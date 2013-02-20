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


    def run(self):

        self.fetch_active_flights()

        # halt if there is an error on first connection attempt
        try:
            self.aprs.connect()
        except Exception, e:
            print e
            return

        self.aprs.consumer(self.habitat_upload, blocking=True, immortal=True)

    def habitat_upload(self, data):
        return

    def fetch_active_flights(self):
        """
        Pulls all active flights from habitat and listens for them on aprs servers
        """
        self.callsigns = {}

        # get the current active flights
        for flight in self.db.view("flight/end_start_including_payloads", include_docs=True, startkey=[time.time()]).all():
            if flight['key'][3] == 1 and flight['doc'].has_key('aprs') and len(flight['doc']['aprs']) > 0:
                current = flight['doc']['aprs']

                # separate payloads
                if current.has_key['payloads']:
                    self.callsigns.update({cs: 0 for cs in current['payloads']})

                # separate chaser callsigns
                if current.has_key['chasers']:
                    self.callsigns.update({cs: 1 for cs in current['chasers']})

        # updates aprs.net filter
        self.aprs.callsign_filter([x[0] for x in self.callsigns] + ['LZ1DEV'])

