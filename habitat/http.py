# Copyright 2010 (C) Daniel Richman
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
``habitat.http``: a HTTP Gateway.

This module lets clients insert messages into the a
:py:class:`habitat.message_server.Server` by HTTP POST
"""

import os
import time
import errno
import functools
import threading
import SocketServer
import json
import logging

from habitat.message_server import Message, Listener
from habitat.utils import crashmat

__all__ = ["InsertApplication", "SCGIApplication", "SCGIHandler"]

logger = logging.getLogger("habitat.http")

info_message = """
"habitat" is a web application for tracking the flight path of high altitude
balloons, relying on a network of users with radios sending in received
telemetry strings which are parsed into position information and displayed
on maps.

This is the information message from the HTTP gateway to habitat; a home page
of sorts. This web application is used to insert messages into the habitat
message server by HTTP post, and is not meant for direct use.

Source code, documentation, and more information:
http://github.com/ukhas/habitat
http://habitat.habhub.org/
"""

class InsertApplication(object):
    """
    **InsertApplication** contains high level "actions" of the HTTP gateway

    The methods in this class are the ones that carry out the action
    requested by the HTTP client, and are independent of the
    CGI or HTTP server or protocol used.
    """

    # We do not allow listeners to insert TELEM messages directly
    FORBIDDEN_TYPES = set([Message.TELEM])

    actions = ["message"]
    """a list of methods that a client is allowed to invoke"""

    def __init__(self, server, program):
        """
        *server*: a :py:class:`habitat.message_server.Server` object into
        which the message action will insert items.

        *program*: a :py:class:`habitat.main.Program` object, of which the
        :py:meth:`habitat.main.Program.shutdown` is used.
        """

        self.server = server
        self.program = program

    def message(self, ip, args):
        """
        Push Action

        *ip*: string - the IP address of the client

        Arguments should be supplied in ``args``; the following arguments are
        required: "callsign", "type", "time_created", "time_uploaded", "data".
        All are user supplied strings.

        .. seealso:: :doc:`../messages`
        """

        # "superset" operation: requires every item in the second set to
        # exist in the first.
        if not set(args.keys()) >= set(["callsign", "type", "time_created",
                                        "time_uploaded", "data"]):
            raise ValueError("required arguments: callsign, type, "
                             "time_created, time_uploaded, data")

        source = Listener(args["callsign"], ip)

        if args["type"] not in Message.type_names:
            raise ValueError("invalid type")

        type = getattr(Message, args["type"])
        Message.validate_type(type)

        if type in self.FORBIDDEN_TYPES:
            raise ValueError("type forbidden for direct insertion")

        time_created = int(args["time_created"])
        time_uploaded = int(args["time_uploaded"])
        time_now = int(time.time())

        clock_difference = time_now - time_uploaded
        time_created += clock_difference

        data = args["data"]

        message = Message(source, type, time_created, time_now, data)

        logger.info("Pushing {type} message from {callsign} at {ip}" \
            .format(type=Message.type_names[type],
                    callsign=source.callsign, ip=source.ip))

        self.server.push_message(message)

class SCGIApplication(InsertApplication,
                      SocketServer.UnixStreamServer):
    """
    **SCGIApplication** is a simple, threaded SCGI server.

    This class uses :py:mod:`SocketServer` to create a threaded SCGI
    server inside the main message server process, that can be shut down
    gracefully.
    It listens on a UNIX socket.
    """

    def __init__(self, server, program, socket_file, timeout=1):
        """
        The following arguments to **__init__** are passed to the
        initialiser of InsertApplication:

        * *server*: the :py:class:`habitat.message_server.Server`
        * *program*: the :py:class:`habitat.main.Program` object

        The following arguments to **__init__** are passed to the
        initialiser of SocketServer.UnixStreamServer

        * *socket_file*: string - the path of the socket to listen on

        *timeout*: the timeout for all connections handled by
        the SCGI server.
        """

        InsertApplication.__init__(self, server, program)
        SocketServer.UnixStreamServer.__init__(self, socket_file,
                                               SCGIHandler, False)
        self.shutdown_timeout = timeout
        self.threads = set()

    def start(self):
        """start the SCGI server"""

        self.accept_thread = crashmat.Thread(target=self.serve_forever_thread,
                                             name="SCGI accept thread")

        try:
            os.unlink(self.server_address)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise

        self.server_bind()
        self.server_activate()
        self.accept_thread.start()

        # Fix for a deadlock. This is a bit ugly, see
        # docs/reference/http.rst "SocketServer.py hack"

        try:
            while not self._BaseServer__serving:
                time.sleep(0.001)
        except AttributeError:
            pass

    def shutdown(self):
        """gracefully shutdown the SCGI server and join every thread"""

        SocketServer.UnixStreamServer.shutdown(self)

        for t in self.threads.copy():
            t.join()

        self.accept_thread.join()
        self.server_close()

    def serve_forever_thread(self):
        self.serve_forever(poll_interval=self.shutdown_timeout)

    # As in SocketServer.ThreadingMixIn but
    #  - we want to keep track of our threads
    #  - we want to use crashmat.Thread instead
    def process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
            self.close_request(request)
        except:
            self.handle_error(request, client_address)
            self.close_request(request)
        finally:
            self.threads.remove(threading.current_thread())

    def process_request(self, request, client_address):
        request.settimeout(self.shutdown_timeout)
        t = crashmat.Thread(target=self.process_request_thread,
                            args=(request, client_address),
                            name="SCGI Handler Thread")
        self.threads.add(t)
        t.start()

    def handle_error(self):
        logger.exception("handle_error -- uncaught exception")
        crashmat.panic()

class BadSCGIRequestError(StandardError):
    pass

class SCGIHandler(SocketServer.BaseRequestHandler):
    """
    **SCGIHandler** objects are responsible for handling a single request

    This class parses and handles the SCGI request, then returns a
    response to the client. An action (``self.server.action_method``,
    e.g., :py:meth:`InsertApplication.message`) is
    called to perform the action requested by the client, where
    ``self.server`` typically is a :py:class:`SCGIApplication` object,
    which is a subclass of :py:class:`InsertApplication`, where those
    action methods are defined.
    """

    def setup(self):
        """prepares the SCGIHandler object for use"""

        self.environ = {}
        self.post_data = ""
        self.buf = ""

    def handle(self):
        """reads the request and performs the action"""

        try:
            self.read_scgi_req()
            self.check_scgi_environ()
            self.perform_req()
        except IOError:
            logger.exception("IOError while handling SCGI request")
            return
        except BadSCGIRequestError:
            logger.exception("BadSCGIRequestError while handling SCGI request")

            try:
                self.request.sendall("Status: 500 Internal Server Error\r\n")
            except IOError:
                logger.warning("IOError while trying to send Status: 500",
                               exc_info=1)

    def read_scgi_req(self):
        """parses the whole SCGI request"""

        while self.buf.find(":") == -1:
            self.read_more()

        (envlen, sep, self.buf) = self.buf.partition(":")
        envlen = long(envlen)

        while (envlen + 1) > len(self.buf):
            self.read_more()

        if self.buf[envlen - 1] != "\0" or self.buf[envlen] != ",":
            raise BadSCGIRequestError

        envdata = self.buf[:envlen - 1]
        self.buf = self.buf[envlen + 1:]

        envdata = envdata.split("\0")
        if len(envdata) % 2 != 0:
            raise BadSCGIRequestError

        for i in xrange(0, len(envdata), 2):
            self.environ[envdata[i]] = envdata[i + 1]

        if "CONTENT_LENGTH" in self.environ:
            post_len = long(self.environ['CONTENT_LENGTH'])

            while post_len > len(self.buf):
                self.read_more()

            self.post_data = self.buf[:post_len]
            self.buf = self.buf[post_len:]

        if self.buf != "":
            raise BadSCGIRequestError

    def read_more(self):
        new_data = self.request.recv(4096)
        if len(new_data) == 0:
            raise BadSCGIRequestError
        self.buf += new_data

    def check_scgi_environ(self):
        """sanity-check the environment provided"""

        keys = set(self.environ.keys())
        required_keys = set(["REMOTE_ADDR", "REQUEST_METHOD", "PATH_INFO"])

        if not keys.issuperset(required_keys):
            raise BadSCGIRequestError

        url = self.environ["PATH_INFO"]
        if not url[0] == "/":
            raise BadSCGIRequestError

    def perform_req(self):
        """perform the action requested by the user and return a response"""

        url = self.environ["PATH_INFO"]
        action = url[1:]
        ip = self.environ["REMOTE_ADDR"]

        if action == "":
            response = "Status: 200 OK\r\n"
            response += "Content-Type: text/plain\r\n"
            response += "\r\n"
            response += info_message
            self.request.sendall(response)
            return

        if self.environ["REQUEST_METHOD"] != "POST":
            logger.warning("request method in request from {ip} was not POST" \
                .format(ip=ip))
            self.request.sendall("Status: 405 Method Not Allowed\r\n\r\n")
            return

        if action not in self.server.actions:
            logger.warning("Action {action} requested by {ip} not found" \
                .format(action=repr(action), ip=ip))

            response = "Status: 404 Not Found\r\n"
            response += "Content-Type: text/plain\r\n"
            response += "\r\n"
            response += "Action not found. Try one of these: "
            response += " ".join(self.server.actions)
            response += "\r\n"
            self.request.sendall(response)
            return

        try:
            args = json.loads(self.post_data)
            action_function = getattr(self.server, action)
            action_function(ip, args)
        except (TypeError, ValueError):
            logger.warning("Bad request from {ip}".format(ip=ip), exc_info=1)
            self.request.sendall("Status: 400 Bad Request\r\n\r\n")
            return

        response = "Status: 200 OK\r\n"
        response += "Content-Type: text/plain\r\n"
        response += "\r\n"
        response += "OK"
        self.request.sendall(response)
