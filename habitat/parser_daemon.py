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
Run the Parser as a daemon connected to CouchDB's _changes feed.
"""

import logging
import couchdbkit
import restkit
import copy
import statsd

from . import parser
from .utils import immortal_changes

logger = logging.getLogger("habitat.parser_daemon")
statsd.init_statsd({'STATSD_BUCKET_PREFIX': 'habitat'})

__all__ = ['ParserDaemon']


class ParserDaemon(object):
    """
    :class:`ParserDaemon` runs persistently, watching CouchDB's _changes feed
    for new unparsed telemetry, parsing it with :class:`Parser` and storing the
    result back in the database.
    """

    def __init__(self, config, daemon_name="parserdaemon"):
        """
        On construction, it will:

        * Connect to CouchDB using ``self.config["couch_uri"]`` and
          ``config["couch_db"]``.
        """

        config = copy.deepcopy(config)
        self.couch_server = couchdbkit.Server(config["couch_uri"])
        self.db = self.couch_server[config["couch_db"]]
        self.last_seq = self.db.info()["update_seq"]

        self.parser = parser.Parser(config)

    def run(self):
        """
        Start a continuous connection to CouchDB's _changes feed, watching for
        new unparsed telemetry.
        """
        consumer = immortal_changes.Consumer(self.db)
        consumer.wait(self._couch_callback, filter="parser/unparsed",
                since=self.last_seq, include_docs=True, heartbeat=1000)

    def _couch_callback(self, result):
        """
        Handle a new result from the CouchDB _changes feed. Passes the doc off
        to Parser.parse, then saves the result.
        """
        self.last_seq = result['seq']
        doc = self.parser.parse(result['doc'])
        if doc:
            self._save_updated_doc(doc)

    @statsd.StatsdTimer.wrap('parser_daemon.save_time')
    def _save_updated_doc(self, doc, attempts=0):
        """
        Save doc to the database, retrying with a merge in the event of
        resource conflicts. This should definitely be a method of some Telem
        class thing.
        """
        latest = self.db[doc['_id']]
        latest['data'].update(doc['data'])
        try:
            self.db.save_doc(latest)
            logger.debug("Saved doc {0} successfully".format(doc["_id"]))
            statsd.increment("parser_daemon.saved")
        except couchdbkit.exceptions.ResourceConflict:
            attempts += 1
            if attempts >= 30:
                err = "Could not save doc {0} after {1} conflicts." \
                        .format(doc["_id"], attempts)
                logger.error(err)
                statsd.increment("parser_daemon.save_error")
                raise RuntimeError(err)
            else:
                logger.debug("Save conflict, trying again (#{0})" \
                    .format(attempts))
                statsd.increment("parser_daemon.save_conflict")
                self._save_updated_doc(doc, attempts)
        except restkit.errors.Unauthorized as e:
            logger.warn("Could not save doc {0}, unauthorized: {1}" \
                .format(doc["_id"], e))
            return
