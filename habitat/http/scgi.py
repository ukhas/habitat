# Copyright 2010 (C) Daniel Richman
#
# This file is part of habitat.
#
# Some parts of SCGIHandler.read_scgi_req are based off cherokee-pyscgi;
# http://www.alobbs.com/news/1193
# Copyright (c) 2006-2010, Alvaro Lopez Ortega <alvaro@alobbs.com>
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
This module uses SocketServer to create a threaded scgi server inside
the main message server process, that can be shut down gracefully.
"""

from app import InsertApplication, info_message
import os
import time
import errno
import functools
import threading
import SocketServer
import json

class SCGIApplication(InsertApplication,
                      SocketServer.UnixStreamServer):

    def __init__(self, server, program, socket_file, timeout=1):
        InsertApplication.__init__(self, server, program)
        SocketServer.UnixStreamServer.__init__(self, socket_file, 
                                               SCGIHandler, False)
        self.shutdown_timeout = timeout
        self.threads = set()

    def serve_forever_thread(self):
        self.serve_forever(poll_interval=self.shutdown_timeout)

    def start(self):
        self.accept_thread = threading.Thread(target=self.serve_forever_thread,
                                              name="SCGI accept thread")

        try:
            os.unlink(self.server_address)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise

        self.server_bind()
        self.server_activate()
        self.accept_thread.start()

        # Fix for http://pastie.org/1227636 - this is a bit ugly.
        try:
            while not self._BaseServer__serving:
                time.sleep(0.001)
        except AttributeError:
            pass

    def shutdown(self):
        SocketServer.UnixStreamServer.shutdown(self)

        for t in self.threads.copy():
            t.join()

        self.accept_thread.join()
        self.server_close()

    # As in SocketServer.ThreadingMixIn but we want to keep track of our
    # threads
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
        t = threading.Thread(target=self.process_request_thread,
                             args=(request, client_address),
                             name="SCGI Handler Thread")
        self.threads.add(t)
        t.start()

    # TODO: def handle_error(self)

class SCGIHandler(SocketServer.BaseRequestHandler):
    def setup(self):
        self.environ = {}
        self.post_data = ""
        self.buf = ""
        self.read_scgi_req()

    def read_more(self):
        new_data = self.request.recv(4096)
        if len(new_data) == 0:
            raise IOError("Invalid request")
        self.buf += new_data

    def read_scgi_req(self):
        while self.buf.find(":") == -1:
            self.read_more()

        (envlen, sep, self.buf) = self.buf.partition(":")
        envlen = long(envlen)

        while (envlen + 1) > len(self.buf):
            self.read_more()

        assert self.buf[envlen - 1] == "\0"
        assert self.buf[envlen] == ","

        envdata = self.buf[:envlen - 1]
        self.buf = self.buf[envlen + 1:]

        envdata = envdata.split("\0")
        assert len(envdata) % 2 == 0

        for i in xrange(0, len(envdata), 2):
            self.environ[envdata[i]] = envdata[i + 1]

        if self.environ.has_key("CONTENT_LENGTH"):
            post_len = long(self.environ['CONTENT_LENGTH'])

            while post_len > len(self.buf):
                self.read_more()

            self.post_data = self.buf[:post_len]
            self.buf = self.buf[post_len:]

        assert self.buf == ""

    def handle(self):
        try:
            keys = set(self.environ.keys())
            assert keys >= set(["REMOTE_ADDR", "REQUEST_METHOD", "PATH_INFO"])

            url = self.environ["PATH_INFO"]
            assert url[0] == "/"

        except AssertionError:
            self.request.sendall("Status: 500 Internal Server Error\r\n")
            return

        action = url[1:]

        if action == "":
            response = "Status: 200 OK\r\n"
            response += "Content-Type: text/plain\r\n"
            response += "\r\n"
            response += info_message
            self.request.sendall(response)
            return

        if self.environ["REQUEST_METHOD"] != "POST":
            self.request.sendall("Status: 405 Method Not Allowed\r\n\r\n")
            return

        if action not in self.server.actions:
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
            action_function(self.environ["REMOTE_ADDR"], **args)
        except (TypeError, ValueError):
            self.request.sendall("Status: 400 Bad Request\r\n\r\n")
            raise

        response = "Status: 200 OK\r\n"
        response += "Content-Type: text/plain\r\n"
        response += "\r\n"
        response += "OK"
        self.request.sendall(response)
