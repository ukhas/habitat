# Copyright 2011 (C) Adam Greig, Daniel Richman
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
The parser interprets incoming telemetry strings into useful telemetry data.
"""

import time
import base64
from copy import deepcopy

from habitat.message_server import SimpleSink, Message
from habitat.utils import dynamicloader

__all__ = ["ParserSink", "ParserModule"]

class ParserSink(SimpleSink):
    """
    The Parser Sink

    The parser sink is the interface between the message server and the
    parser modules. It is responsible for receiving raw telemetry from the
    message server, giving it to modules which turn it into beautiful
    telemetry data, and then sending that back to the message server.
    """

    BEFORE_FILTER, DURING_FILTER, AFTER_FILTER = locations = range(3)

    def setup(self):
        """
        Initialises the sink, adding the types of telemetry we care about
        to our types list and setting up lists of filters and modules
        """
        self.add_type(Message.RECEIVED_TELEM)

        self.before_filters = []
        self.during_filters = []
        self.after_filters = []
        self.filters = {
            self.BEFORE_FILTER: self.before_filters,
            self.DURING_FILTER: self.during_filters,
            self.AFTER_FILTER: self.after_filters
        }

        self.modules = []

        for module in self.server.db["parser_config"]["modules"]:
            m = dynamicloader.load(module["class"])
            dynamicloader.expecthasmethod(m, "pre_parse")
            dynamicloader.expecthasmethod(m, "parse")
            dynamicloader.expecthasnumargs(m.pre_parse, 1)
            dynamicloader.expecthasnumargs(m.parse, 2)
            module["module"] = m(self)
            self.modules.append(module)

    def message(self, message):
        """
        Handles a new message from the server, hopefully turning it into
        parsed telemetry data.

        This function attempts to determine which of the loaded parser
        modules should be used to parse the message, and which config
        file it should be given to do so.

        For the priority ordered list self.modules, resolution proceeds as::

            for module in modules:
                module.pre_parse to find a callsign
                if a callsign is found:
                    look up the configuration document for that callsign
                    if a configuration document is found:
                        check it specifies that this module should be used
                        if it does:
                            module.parse to get the data
                            return
            if all modules were attempted but no config docs were found:
                for module in modules:
                    if this module has a default configuration:
                        module.pre_parse to find a callsign
                        if a callsign is found:
                            use this module's default configuration
                            module.parse to get the data
                            return
            if we still can't get any data:
                error

        Note that in the loops below, the pre_parse, _find_config_doc and
        parse methods will all raise a ValueError if failure occurs,
        continuing the loop.

        The output is a new message of type Message.TELEM, with message.data
        being the parsed data as well as any special fields, identified by
        a leading underscore in the key.

        These fields may include:

        * _protocol which gives the parser module name that was used to
          decode this message
        * _used_default_config is a boolean value set to True if a
          default configuration was used for the module as no specific
          configuration could be found
        * _raw gives the original submitted data
        * _sentence gives the ASCII sentence from the UKHAS parser
        * _extra_data from the UKHAS parser, where the sentence contained
          more data than the UKHAS parser was configured for

        Parser modules should be wary when outputting field names with
        leading underscores.
        """

        data = None

        raw_data = base64.b64decode(message.data["string"])

        # Try using real configs
        for module in self.modules:
            try:
                callsign = module["module"].pre_parse(raw_data)
                config = self._find_config_doc(callsign)
                if config["protocol"] == module["name"]:
                    data = module["module"].parse(raw_data, config)
                    data["_protocol"] = module["name"]
                    break
            except ValueError:
                continue

        # If that didn't work, try using default configurations
        if not data:
            for module in self.modules:
                try:
                    config = module["default_config"]
                    callsign = module["module"].pre_parse(raw_data)
                    data = module["module"].parse(raw_data, config)
                    data["_protocol"] = module["name"]
                    data["_used_default_config"] = True
                    break
                except (ValueError, KeyError):
                    continue

        if data:
            data["_raw"] = message.data["string"]

            # Every key apart from string contains RECEIVED_TELEM metadata
            data["_listener_metadata"] = deepcopy(message.data)
            del data["_listener_metadata"]["string"]

            new_message = Message(message.source, Message.TELEM,
                                  message.time_created, message.time_uploaded,
                                  data)
            self.server.push_message(new_message)
        else:
            raise ValueError("No data could be parsed.")

    def _find_config_doc(self, callsign):
        """
        Check Couch for a configuration document we can use for this payload.
        The Couch view first tries to find any Flight documents with this
        callsign in their payloads dictionary, but will also return any
        Sandbox documents with this payload if no valid Flight documents
        could be found. Flight documents only count if their end time is
        in the future.
        If no config can be found, raises
        :py:exc:`ValueError <exceptions.ValueError>`, otherwise returns
        the sentence dictionary out of the payload config dictionary.
        """
        startkey = [callsign, int(time.time())]
        result = self.server.db.view("habitat/payload_config", limit=1,
                                     include_docs=True,
                                     startkey=startkey).first()
        if not result or callsign not in result["doc"]["payloads"]:
            raise ValueError("No configuration document found for callsign.")
        return result["doc"]["payloads"][callsign]["sentence"]


class ParserModule(object):
    """
    **ParserModules** are classes which turn radio strings into useful data.

    ParserModules

    * can be given various configuration parameters.
    * should probably inherit from **ParserModule**.

    """
    def __init__(self, parser):
        """Store the parser reference for later use."""
        self.parser = parser

    def pre_parse(self, string):
        """
        Go though a string and attempt to extract a callsign, returning
        it as a string. If no callsign could be extracted, a
        :py:exc:`ValueError <exceptions.ValueError>` is raised.
        """
        raise ValueError()

    def parse(self, string, config):
        """
        Go through a string which has been identified as the format this
        parser module should be able to parse, extracting the data as per
        the information in the config parameter, which is the ``sentence``
        dictionary extracted from the payload's configuration document.
        """
        raise ValueError()
