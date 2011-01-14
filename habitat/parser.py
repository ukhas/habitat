# Copyright 2010 (C) Adam Greig
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

        self.modules = {}
        
        for module in self.server.db["parser_config"]["modules"]:
            m = dynamicloader.load(module["class"])
            dynamicloader.expecthasmethod(m, "pre_parse")
            dynamicloader.expecthasmethod(m, "parse")
            dynamicloader.expecthasnumargs(m.pre_parse, 1)
            dynamicloader.expecthasnumargs(m.parse, 2)
            new_module = m(self)
            self.modules[module["name"]] = new_module

    def message(self, message):
        """
        Handles a new message from the server, hopefully turning it into
        parsed telemetry data.
        """

        callsign = None
        for module in self.modules:
            try:
                callsign = self.modules[module].pre_parse(message.data)
            except ValueError:
                continue

        if callsign:
            startkey = '["' + callsign + '", ' + str(int(time.time())) + ']'
            result = self.server.db.view("habitat/payload_config", limit=1,
                include_docs=True, startkey=startkey).first()["doc"]
            config = result["payloads"][callsign]["sentence"]
            if config["protocol"] not in self.modules:
                raise ValueError("Payload configuration document specifies a"
                    " module that is not loaded.")
            else:
                module = config["protocol"]
                data = self.modules[module].parse(message.data, config)
                parsed_message = Message(message.source, Message.TELEM, data)
                self.server.push_message(parsed_message)


    def shutdown(self):
        """Gracefully kills the parser."""
        pass

    def flush(self):
        """Finish processing all incoming messages.""" 
        pass


class ParserModule(object):
    """
    **ParserModules** are classes which turn radio strings into useful data.

    ParserModules

     - can be given various configuration parameters.
     - should probably inherit from **ParserModule**.

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
