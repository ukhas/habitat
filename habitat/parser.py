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

import base64
import logging
import hashlib
import M2Crypto
import os
import os.path
import couchdbkit

from . import sensor_manager
from .utils import dynamicloader

__all__ = ["Parser", "ParserModule"]

logger = logging.getLogger("habitat.parser")

class Parser(object):
    """
    habitat's parser

    Parser takes arbitrary newly uploaded payload telemetry and attempts to use
    ParserModules to turn this telemetry into useful data, which is then saved
    back to the database.
    """

    def __init__(self, config):
        """
        Loads a SensorManager with config["sensors"].
        Loads modules from config["modules"].
        Scans config["certs_dir"] for CA and developer certificates.
        Connects to CouchDB using config["couch_uri"] and config["couch_db"].
        """

        self.sensor_manager = sensor_manager.SensorManager(config)

        self.modules = []

        for module in config["modules"]:
            m = dynamicloader.load(module["class"])
            dynamicloader.expecthasmethod(m, "pre_parse")
            dynamicloader.expecthasmethod(m, "parse")
            dynamicloader.expecthasnumargs(m.pre_parse, 1)
            dynamicloader.expecthasnumargs(m.parse, 2)
            module["module"] = m(self)
            self.modules.append(module)

        self.certificate_authorities = []

        base_path = os.path.split(os.path.abspath(__file__))[0]
        parent_path = os.path.join(base_path, '..')
        self.cert_path = os.path.join(parent_path, config["certs_dir"])
        ca_path = os.path.join(self.cert_path, 'ca')
        for f in os.listdir(ca_path):
            ca = M2Crypto.X509.load_cert(os.path.join(ca_path, f))
            self.certificate_authorities.append(ca)

        self.loaded_certs = {}

        self.couch_server = couchdbkit.Server(config["couch_uri"])
        self.db = self.couch_server[config["couch_db"]]
        self.last_seq = 0

    def run(self):
        """
        Start a continuous connection to CouchDB's _changes feed, watching for
        new unparsed telemetry.
        """
        consumer = couchdbkit.Consumer(self.db)
        consumer.wait(self.couch_callback, filter="habitat/unparsed",
                since=self.last_seq, heartbeat=1000)

    def couch_callback(self, result):
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
        print "in callback, considering {0}".format(result)
        self.last_seq = result['seq']
        doc = self.db[result['id']]
        data = None
        original_data = doc['data']['_raw']
        raw_data = base64.b64decode(original_data)
        receiver_callsign = doc['receivers'].keys()[0]
        time_created = doc['receivers'][receiver_callsign]['time_created']

        # Try using real configs
        for module in self.modules:
            try:
                data = self._pre_filter(raw_data, module)
                callsign = module["module"].pre_parse(data)
                config_doc = self._find_config_doc(callsign, time_created)
                config = config_doc["payloads"][callsign]
                if config["sentence"]["protocol"] == module["name"]:
                    data = self._intermediate_filter(data, config)
                    data = module["module"].parse(data, config["sentence"])
                    data = self._post_filter(data, config)
                    data["_protocol"] = module["name"]
                    data["_flight"] = config_doc["_id"]
                    data["_parsed"] = True
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
                    data["_parsed"] = True
                    logger.info("Using a default configuration document")
                    break
                except ValueError as e:
                    errstr = "Error from {0} with default config: '{1}'"
                    logger.debug(errstr.format(module["name"], e))
                    continue

        if type(data) is dict:
            doc['data'].update(data)
            print "saving doc: {0}".format(doc)
            self._save_updated_doc(doc)

            logger.info("{module} parsed data from {callsign} succesfully" \
                .format(module=module["name"], callsign=callsign))
        else:
            logger.info("Unable to parse any data from '{d}'" \
                .format(d=original_data))

    def _save_updated_doc(self, doc, attempts=0):
        """Save doc to the database, retrying with a merge in the event of
        resource conflicts. This should definitely be a method of some Telem
        class thing."""
        latest = self.db[doc['_id']]
        latest['data'].update(doc['data'])
        try:
            self.db.save_doc(latest)
        except couchdbkit.exceptions.ResourceConflict:
            attempts += 1
            if attempts >= 30:
                err = "Could not save telemetry doc after 30 conflicts."
                logger.error(err)
                raise RuntimeError(err)
            else:
                self._save_updated_doc(doc, attempts)

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
        result = self.db.view("habitat/payload_config", limit=1,
                include_docs=True, startkey=startkey).first()
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
            return self._normal_filter(data, f)
        elif f["type"] == "hotfix":
            return self._hotfix_filter(data, f)
        else:
            return data

    def _normal_filter(self, data, f):
        """Load and run a filter specified by a callable."""
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

    def _hotfix_filter(self, data, f):
        """Load a filter specified by some code in the database. Check its
        authenticity by verifying its certificate, then run if OK."""
        if "code" not in f:
            logger.warning("A hotfix didn't have any code: " + repr(f))
            return data
        if "signature" not in f:
            logger.warning("A hotfix didn't have a signature: " + repr(f))
            return data
        if "certificate" not in f:
            logger.warning("A hotfix didn't specify a certificate: " + repr(f))
            return data
        if os.path.basename(f["certificate"]) != f["certificate"]:
            logger.warning("A hotfix's specified certificate was invalid: " + \
                           repr(f))
            return data
        
        # Load requested certificate
        try:
            cert = self._get_certificate(f["certificate"])
        except RuntimeError:
            logger.error("Could not load certificate '" +
                f["certificate"] + "'.")
            return data

        # Check the certificate is valid
        valid = False
        for ca_cert in self.certificate_authorities:
            if cert.verify(ca_cert.get_pubkey()):
                valid = True
                break
        if not valid:
            logger.error("Certificate is not signed by a recognised CA.")
            return data

        # Check the signature is valid
        digest = hashlib.sha256(f["code"]).hexdigest()
        sig = base64.b64decode(f["signature"])
        try:
            ok = cert.get_pubkey().get_rsa().verify(digest, sig, 'sha256')
        except M2Crypto.RSA.RSAError:
            logger.error("Signature is invalid.")
            return data

        if not ok:
            logger.error("Hotfix signature is not valid")
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
                raise RuntimeError("Certificate could not be loaded.")
            self.loaded_certs[certname] = cert
            return cert
        else:
            raise RuntimeError("Certificate could not be loaded.")

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
        self.sensors = parser.sensor_manager

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
