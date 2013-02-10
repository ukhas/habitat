# Copyright 2010, 2011, 2012 (C) Adam Greig, Daniel Richman
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
"""

import logging
import couchdbkit
import copy
import statsd
import time

from .utils import immortal_changes

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

    def run(self):

        self.fetch_active_flights()
        print self.callsigns

    def fetch_active_flights(self):
        """
        Pulls all active flights from habitat
        """
        self.callsigns = {}

        for flight in self.db.view("flight/end_start_including_payloads", include_docs=True, startkey=[time.time()]).all():
            if flight['key'][3] == 1 and flight['doc'].has_key('aprs') and len(flight['doc']['aprs']) > 0:
                current = flight['doc']['aprs']

                if current.has_key['payloads']:
                    self.callsigns.update({cs: 0 for cs in current['payloads']})

                if current.has_key['chasers']:
                    self.callsigns.update({cs: 1 for cs in current['chasers']})

    def _couch_callback(self, result):
        """
        Handle a new result from the CouchDB _changes feed. Passes the doc off
        to APRS.parse, then saves the result.
        """
        self.last_seq = result['seq']
        print result
