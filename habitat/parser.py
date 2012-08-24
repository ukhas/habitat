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
Interpret incoming telemetry strings into useful telemetry data.
"""

import base64
import logging
import hashlib
import M2Crypto
import os
import couchdbkit
import copy
import re
import json
import statsd
import time

from . import loadable_manager
from .utils import dynamicloader, rfc3339

logger = logging.getLogger("habitat.parser")
statsd.init_statsd({'STATSD_BUCKET_PREFIX': 'habitat.parser'})

__all__ = ['Parser', 'ParserModule']


class Parser(object):
    """
    habitat's parser

    :class:`Parser` takes arbitrary unparsed  payload telemetry and
    attempts to use each loaded :class:`ParserModule` to turn this telemetry
    into useful data.
    """

    ascii_exp = re.compile("^[\\x20-\\x7E]+$")

    def __init__(self, config):
        """
        On construction, it will:

        * Use ``config[daemon_name]`` as ``self.config`` (defaults to
          'parser').
        * Load modules from ``self.config["modules"]``.
        * Connects to CouchDB using ``self.config["couch_uri"]`` and
          ``config["couch_db"]``.
        """

        config = copy.deepcopy(config)
        parser_config = config["parser"]

        self.filtering = ParserFiltering(config)

        self.modules = []

        for module in parser_config["modules"]:
            m = dynamicloader.load(module["class"])
            dynamicloader.expecthasmethod(m, "pre_parse")
            dynamicloader.expecthasmethod(m, "parse")
            dynamicloader.expecthasnumargs(m.pre_parse, 1)
            dynamicloader.expecthasnumargs(m.parse, 2)
            module["module"] = m(self)
            self.modules.append(module)

        self.couch_server = couchdbkit.Server(config["couch_uri"])
        self.db = self.couch_server[config["couch_db"]]

    @statsd.StatsdTimer.wrap('time')
    def parse(self, doc, config=None):
        """
        Attempts to parse telemetry information out of a new telemetry
        document *doc*.

        This function attempts to determine which of the loaded parser
        modules should be used to parse the message, and which config
        file it should be given to do so (if *config* is specified, no attempt
        will be made to find any other configuration document).

        The resulting parsed document is returned, or None is returned if no
        data could be parsed.

        Some field names in data["data"] are reserved, as indicated by a
        leading underscore.

        These fields may include:

        * ``_protocol`` which gives the parser module name that was used to
          decode this message

        From the UKHAS parser module in particular:

        * ``_sentence`` gives the ASCII sentence from the UKHAS parser
        * ``_extra_data`` from the UKHAS parser, where the sentence contained
          more data than the UKHAS parser was configured for

        Parser modules should be wary when outputting field names with
        leading underscores.
        """
        data = None
        raw_data = base64.b64decode(doc['data']['_raw'])
        debug_type, debug_data = self._get_debug(raw_data)
        receiver_callsign = doc['receivers'].keys()[0]

        logger.info("Parsing [{type}] {data!r} ({id}) from {who}"
                    .format(id=doc["_id"], data=debug_data, type=debug_type,
                            who=receiver_callsign))

        for module in self.modules:
            try:
                callsign = self._get_callsign(raw_data, module)
                config = self._get_config(callsign, config)
                data = self._get_data(raw_data, callsign, config, module)
            except (CantGetCallsign, CantGetConfig, CantGetData):
                continue
            break

        if type(data) is dict:
            doc['data'].update(data)
            logger.info("{module} parsed data from {callsign} successfully"
                        .format(module=module["name"], callsign=callsign))
            logger.debug("Parsed data: " + json.dumps(data, indent=2))
            statsd.increment("parsed")
            if "_protocol" in data:
                statsd.increment("protocol.{0}".format(data['_protocol']))
            return doc
        else:
            logger.info("All attempts to parse failed")
            statsd.increment("failed")
            return None

    def _get_debug(self, raw_data):
        if self.ascii_exp.search(raw_data):
            statsd.increment("ascii_doc")
            return 'ascii', raw_data
        else:
            statsd.increment("binary_doc")
            return 'b64', base64.b64encode(raw_data)

    def _get_callsign(self, raw_data, module):
        """Attempt to find a callsign from the data."""
        try:
            where = "pre_filter"
            raw_data = self.filtering.pre_filter(raw_data, module)
            where = "pre_parse"
            callsign = module["module"].pre_parse(raw_data)
        except (ValueError, KeyError) as e:
            logger.debug("Exception in {module} {where}: {e}"
                         .format(e=e, module=module['name'], where=where))
            statsd.increment("parse_exception")
            raise CantGetCallsign()
        return callsign

    def _get_config(self, callsign, config=None):
        """
        Attempt to get a config doc given the callsign and maybe a provided
        config doc.
        """
        if config and not self._callsign_in_config(callsign, config):
            logger.debug("Callsign {c!r} not found in configuration doc"
                         .format(c=callsign))
            raise CantGetConfig()

        config = self._find_config_doc(callsign)

        if not config:
            logger.debug("No configuration doc for {callsign!r} found"
                         .format(callsign=callsign))
            statsd.increment("no_config_doc")
            raise CantGetConfig()

        return config

    def _get_data(self, raw_data, callsign, config, module):
        """Attempt to parse data from what we know so far."""
        sentences = config["payload_configuration"]["sentences"]
        for sentence_index, sentence in enumerate(sentences):
            if sentence["callsign"] != callsign:
                continue
            if sentence["protocol"] != module["name"]:
                continue
            try:
                where = "intermediate filter"
                data = self.filtering.intermediate_filter(raw_data, sentence)
                where = "main parse"
                data = module["module"].parse(data, sentence)
                where = "post filter"
                data = self.filtering.post_filter(data, sentence)
            except (ValueError, KeyError) as e:
                logger.debug("Exception in {module} {where}: {e}"
                             .format(module=module['name'], e=e, where=where))
                statsd.increment("parse_exception")
                continue

            data["_protocol"] = module["name"]
            data["_parsed"] = {
                "time_parsed": rfc3339.now_to_rfc3339_utcoffset(),
                "payload_configuration": config["id"],
                "configuration_sentence_index": sentence_index
            }
            if "flight_id" in config:
                data["_parsed"]["flight"] = config["flight_id"]
            return data
        raise CantGetData()

    def _find_config_doc(self, callsign):
        """
        Attempt to locate a payload_configuration document suitable for parsing
        data from *callsign* at the present moment in time.
        Resolution proceeds as:
            1. Check all started-but-not-yet-ended (aka active) flights
               for a reference to a payload_configuration document that
               includes this callsign in at least one sentence.
            2. If no active flights mention the callsign, obtain the single
               most recently created payload_configuration document that does
               and use it.

        Returns an object that contains the payload_configuration document ID,
        the flight ID if appropriate, and the payload_configuration::

        {
            "id": <payload_configuration doc ID>,
            "payload_configuration": <payload_configuration doc>,
            "flight_id": <flight doc ID>
        }

        The returned document may have more than one sentence object, and each
        should be attempted in order.
        If no configuration can be found, None is returned.
        """
        t = int(time.time())
        flights = self.db.view("flight/end_start_including_payloads",
                               startkey=[t])
        for flight in flights:
            if flight["key"][1] < t and flight["key"][2] == 1:
                if self._callsign_in_config(callsign, flight["value"]):
                    return {
                        "id": flight["value"]["_id"],
                        "flight_id": flight["id"],
                        "payload_configuration": flight["value"]
                    }

        config = self.db.view("payload_configuration/callsign_time_created",
                              startkey=[callsign], include_docs=True, limit=1
                              ).first()
        # Note that we check the callsign is in this doc as if no configuration
        # has this callsign, the firt document returned above will be for the
        # closest callsign alphabetically (and thus not useful).
        if config and self._callsign_in_config(callsign, config["doc"]):
            return {
                "id": config["id"],
                "payload_configuration": config["doc"]
            }

        return None

    def _callsign_in_config(self, callsign, config):
        return callsign in (s["callsign"] for s in config["sentences"])


class ParserFiltering(object):
    """
    Handle filtering of data during parsing.
    """
    def __init__(self, config):
        """
        * Scans ``config["parser"]["certs_dir"]`` for CA and developer
          certificates.
        * Loads a :class:`habitat.loadable_manager.LoadableManager` for
          using loaded filters.
        """
        self.config = copy.deepcopy(config)
        self.loadable_manager = loadable_manager.LoadableManager(config)
        self.certificate_authorities = []
        self.cert_path = self.config["parser"]["certs_dir"]
        ca_path = os.path.join(self.cert_path, 'ca')
        for f in os.listdir(ca_path):
            ca = M2Crypto.X509.load_cert(os.path.join(ca_path, f))
            if ca.check_ca():
                self.certificate_authorities.append(ca)
            else:
                raise ValueError("CA certificate is not a CA: {0}"
                                 .format(os.path.join(ca_path, f)))

        self.loaded_certs = {}

    def pre_filter(self, raw_data, module):
        """
        Apply all the module's pre filters, in order, to the data and
        return the resulting filtered data.
        """
        sentence = {"filters": module}
        return self._apply_filters(raw_data, sentence, "pre-filters", str)

    def intermediate_filter(self, raw_data, sentence):
        """
        Apply all the intermediate (between getting the callsign and parsing)
        filters specified in the payload's configuration document and return
        the resulting filtered data.
        """
        return self._apply_filters(raw_data, sentence, "intermediate", str)

    def post_filter(self, data, sentence):
        """
        Apply all the post (after parsing) filters specified in the payload's
        configuration document and return the resulting filtered data.
        """
        return self._apply_filters(data, sentence, "post", dict)

    def _apply_filters(self, data, sentence, filter_type, result_type):
        if "filters" in sentence:
            if filter_type in sentence["filters"]:
                for f in sentence["filters"][filter_type]:
                    data = self._filter(data, f, result_type)
                    statsd.increment("filtes.{0}".format(filter_type))
        return data

    def _filter(self, data, f, result_type):
        """
        Load and run a filter from a dictionary specifying type, the
        relevant filter/code and maybe a config.
        Returns the filtered data, or leaves the data untouched
        if the filter could not be run.
        """
        rollback = data
        data = copy.deepcopy(data)

        try:
            if f["type"] == "normal":
                fil = 'filters.' + f['filter']
                data = self.loadable_manager.run(fil, f, data)
            elif f["type"] == "hotfix":
                data = self._hotfix_filter(data, f)
            else:
                raise ValueError("Invalid filter type")

            if not data or not isinstance(data, result_type):
                raise ValueError("Hotfix returned no output or "
                                 "output of wrong type")
        except:
            logger.exception("Error while applying filter " + repr(f))
            return rollback
        else:
            return data

    def _sanity_check_hotfix(self, f):
        """Perform basic sanity checks on **f**"""
        if "code" not in f:
            raise ValueError("Hotfix didn't have any code")
        if "signature" not in f:
            raise ValueError("Hotfix didn't have a signature")
        if "certificate" not in f:
            raise ValueError("Hotfix didn't specify a certificate")
        if os.path.basename(f["certificate"]) != f["certificate"]:
            raise ValueError("Hotfix's specified certificate was invalid")

    def _verify_certificate(self, f, cert):
        """Check that the certificate is cryptographically signed by a key
        which is signed by a known CA."""
        # Check the certificate is valid
        for ca_cert in self.certificate_authorities:
            if cert.verify(ca_cert.get_pubkey()):
                break
            raise ValueError("Certificate is not signed by a recognised CA.")

        # Check the signature is valid
        try:
            digest = hashlib.sha256(f["code"]).hexdigest()
            sig = base64.b64decode(f["signature"])
            ok = cert.get_pubkey().get_rsa().verify(digest, sig, 'sha256')
        except (TypeError, M2Crypto.RSA.RSAError):
            statsd.increment("filters.hotfix.invalid_signature")
            raise ValueError("Hotfix signature is not valid")
        if not ok:
            statsd.increment("filters.hotfix.invalid_signature")
            raise ValueError("Hotfix signature is not valid")

    def _compile_hotfix(self, f):
        """Compile a hotfix into a function **f** in an empty namespace."""
        logger.debug("Compiling a hotfix")
        body = "def f(data):\n"
        env = {}
        try:
            body += "\n".join("  " + l + "\n" for l in f["code"].split("\n"))
            code = compile(body, "<filter>", "exec")
            exec code in env
        except (SyntaxError, AttributeError, TypeError):
            statsd.increment("filters.hotfix.compile_error")
            raise ValueError("Hotfix code didn't compile: " + repr(f))
        return env

    def _hotfix_filter(self, data, f):
        """Load a filter specified by some code in the database. Check its
        authenticity by verifying its certificate, then run if OK."""
        self._sanity_check_hotfix(f)
        cert = self._get_certificate(f["certificate"])
        self._verify_certificate(f, cert)
        env = self._compile_hotfix(f)

        logger.debug("Executing a hotfix")
        statsd.increment("filters.hotfix.executed")

        return env["f"](data)

    def _get_certificate(self, certname):
        """Fetch the specified certificate, returning the X509 object.
        Uses an instance cache to prevent too much filesystem I/O."""
        if certname in self.loaded_certs:
            return self.loaded_certs[certname]
        cert_path = os.path.join(self.cert_path, "certs", certname)
        if os.path.exists(cert_path):
            try:
                cert = M2Crypto.X509.load_cert(cert_path)
            except (IOError, M2Crypto.X509.X509Error):
                raise ValueError("Certificate could not be loaded.")
            self.loaded_certs[certname] = cert
            return cert
        else:
            raise ValueError("Certificate could not be loaded.")


class ParserModule(object):
    """
    Base class for real ParserModules to inherit from.

    **ParserModules** are classes which turn radio strings into useful data.
    They do not have to inherit from :class:`ParserModule`, but can if they
    want. They must implement :meth:`pre_parse` and :meth:`parse` as described
    below.
    """
    def __init__(self, parser):
        self.parser = parser
        self.loadable_manager = parser.loadable_manager

    def pre_parse(self, string):
        """
        Go though *string* and attempt to extract a callsign, returning
        it as a string. If no callsign could be extracted, a
        :exc:`ValueError <exceptions.ValueError>` is raised.
        """
        raise ValueError()

    def parse(self, string, config):
        """
        Go through *string* which has been identified as the format this
        parser module should be able to parse, extracting the data as per
        the information in *config*, which is the ``sentence`` dictionary
        extracted from the payload's configuration document.
        """
        raise ValueError()


class CantGetCallsign(Exception):
    pass


class CantGetConfig(Exception):
    pass


class CantGetData(Exception):
    pass
