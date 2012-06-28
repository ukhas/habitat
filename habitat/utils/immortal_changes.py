# Copyright 2012 (C) Daniel Richman
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
An extension to couchdbkit's changes consumer that never dies.
"""

import time
import logging
import couchdbkit

logger = logging.getLogger("habitat.utils.immortal_changes")

class Consumer(couchdbkit.Consumer):
    def wait(self, callback, **kwargs):
        state = {"delay": 2, "seq": 0} # scope hax.

        if "since" in kwargs:
            state["seq"] = kwargs["since"]
            del kwargs["since"]

        def wrapped_callback(changes):
            state["seq"] = changes["seq"]
            state["delay"] = 2

            try:
                callback(changes)
            except (SystemExit, KeyboardInterrupt):
                raise
            except:
                logger.exception("Exception from changes callback")

        while True:
            logger.debug("Starting continuous changes")

            try:
                super(Consumer, self).wait(wrapped_callback,
                        since=state["seq"], **kwargs)
            except (SystemExit, KeyboardInterrupt):
                raise
            except:
                logger.exception("Exception from changes (couch)")
            else:
                logger.debug("Continuous changes connection closed")

            logger.info("Sleeping for {0} seconds before restarting changes"
                            .format(state["delay"]))
            time.sleep(state["delay"])
            state["delay"] = min(2 * state["delay"], 60)
