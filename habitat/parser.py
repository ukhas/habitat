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
import logging
import hashlib
from copy import deepcopy

from habitat.message_server import SimpleSink, Message
from habitat.utils import dynamicloader

__all__ = ["ParserSink", "ParserModule"]

logger = logging.getLogger("habitat.parser")

class ParserSink(SimpleSink):
    """
    The Parser Sink

    The parser sink is the interface between the message server and the
    parser modules. It is responsible for receiving raw telemetry from the
    message server, giving it to modules which turn it into beautiful
    telemetry data, and then sending that back to the message server.
    """

    def setup(self):
        """
        Initialises the sink, adding the types of telemetry we care about
        to our types list and setting up lists of modules
        """
        self.add_type(Message.RECEIVED_TELEM)

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
        original_data = message.data["string"]
        raw_data = base64.b64decode(original_data)

        # Try using real configs
        for module in self.modules:
            try:
                data = self._pre_filter(raw_data, module)
                callsign = module["module"].pre_parse(data)
                config_doc = self._find_config_doc(callsign,
                    message.time_created)
                config = config_doc["payloads"][callsign]
                if config["sentence"]["protocol"] == module["name"]:
                    data = self._intermediate_filter(data, config)
                    data = module["module"].parse(data, config["sentence"])
                    data = self._post_filter(data, config)
                    data["_protocol"] = module["name"]
                    data["_flight"] = config_doc["_id"]
                    break
            except ValueError as e:
                err = "ValueError from {0}: '{1}'"
                logger.debug(err.format(module["name"], e))
                continue

        # If that didn't work, try using default configurations
        if type(data) is not dict:
            for module in self.modules:
                try:
                    config = module["default_config"]
                except KeyError:
                    continue

                try:
                    data = self._pre_filter(raw_data, module)
                    callsign = module["module"].pre_parse(data)
                    data = self._intermediate_filter(data, config)
                    data = module["module"].parse(data, config["sentence"])
                    data = self._post_filter(data, config)
                    data["_protocol"] = module["name"]
                    data["_used_default_config"] = True
                    logger.info("Using a default configuration document")
                    break
                except ValueError as e:
                    errstr = "Error from {0} with default config: '{1}'"
                    logger.debug(errstr.format(module["name"], e))
                    continue

        if type(data) is dict:
            data["_raw"] = original_data

            # Every key apart from string contains RECEIVED_TELEM metadata
            data["_listener_metadata"] = deepcopy(message.data)
            del data["_listener_metadata"]["string"]

            new_message = Message(message.source, Message.TELEM,
                                  message.time_created, message.time_uploaded,
                                  data)
            self.server.push_message(new_message)

            logger.info("{module} parsed data from {callsign} succesfully" \
                .format(module=module["name"], callsign=callsign))
        else:
            logger.info("Unable to parse any data from '{d}'" \
                .format(d=original_data))

    def _find_config_doc(self, callsign, time_created):
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
        startkey = [callsign, time_created]
        result = self.server.db.view("habitat/payload_config", limit=1,
                                     include_docs=True,
                                     startkey=startkey).first()
        if not result or callsign not in result["doc"]["payloads"]:
            err = "No configuration document for callsign '{0}' found."
            err = err.format(callsign)
            logger.warning(err)
            raise ValueError(err)
        return result["doc"]

    def _pre_filter(self, data, module):
        """
        Apply all the module's pre filters, in order, to the data and
        return the resulting filtered data.
        """
        if "pre-filters" in module:
            for f in module["pre-filters"]:
                data = self._filter(data, f)
        return data
    
    def _intermediate_filter(self, data, config):
        """
        Apply all the intermediate (between getting the callsign and parsing)
        filters specified in the payload's configuration document and return
        the resulting filtered data.
        """
        if "filters" in config:
            if "intermediate" in config["filters"]:
                for f in config["filters"]["intermediate"]:
                    data = self._filter(data, f)
        return data

    def _post_filter(self, data, config):
        """
        Apply all the post (after parsing) filters specified in the payload's
        configuration document and return the resulting filtered data.
        """
        if "filters" in config:
            if "post" in config["filters"]:
                for f in config["filters"]["post"]:
                    data = self._filter(data, f)
        return data

    def _filter(self, data, f):
        """
        Load and run a filter from a dictionary specifying type, the
        relevant callable/code and maybe a config.
        Returns the filtered data, or leaves the data untouched
        if the filter could not be run.
        """
        if "type" not in f:
            logger.warning("A filter didn't have a type: " + repr(f))
            return data
        if f["type"] == "normal":
            # Normal-type filters have a callable which we can load
            # using the dynamicloader, inspect and use
            config = None
            if "config" in f:
                config = f["config"]

            fil = dynamicloader.load(f["callable"])
            if not dynamicloader.iscallable(fil):
                logger.warning("A loaded filter wasn't callable: " + repr(f))
                return data
            if dynamicloader.hasnumargs(fil, 1):
                return fil(data)
            elif dynamicloader.hasnumargs(fil, 2):
                return fil(data, config)
            else:
                logger.warning("A loaded filter had wrong number of args: " +
                        repr(f))
                return data
        elif f["type"] == "hotfix":
            # Hotfix-type filters provide some code which goes in the body
            # of a function, and return a modified version of the body.
            if "code" not in f:
                logger.warning("A hotfix didn't have any code: " + repr(f))
                return data

            try:
                secret = self.server.program.options["secret"]
            except KeyError:
                logger.error("No secret has been set in configuration")
                return data
            
            try:
                signature = f["signature"]
            except KeyError:
                logger.error("No signature on hotfix code")
                return data

            correct_hash = hashlib.sha512(f["code"] + secret).hexdigest()
            if correct_hash != signature:
                logger.error("Invalid signature on hotfix code: " + repr(f))
                return data

            logger.debug("Compiling a hotfix")
            body = "def f(data):\n"
            for line in f["code"].split("\n"):
                body += "    " + line + "\n"
            env = {}
            try:
                code = compile(body, "<filter>", "exec")
                exec code in env
            except (SyntaxError, TypeError):
                logger.warning("Hotfix code didn't compile: " + repr(f))
                return data

            logger.debug("Hotfix compiled, executing")
            try:
                return env["f"](data)
            except:
                # this is a pretty hardcore except! it'l catch anything.
                # but that's desirable as who knows what this crazy code
                # might do.
                logger.warning("An exception occured when trying to run a " +
                        "hotfix: " + repr(f))
                return data


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
        self.sensors = parser.server.program.sensor_manager

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
