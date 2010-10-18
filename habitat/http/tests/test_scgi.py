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
Tests the scgi module app, which creates a scgi application server.
"""

from habitat.http.app import info_message
from habitat.http.scgi import SCGIApplication
from habitat.message_server import Message
from nose.tools import raises
from serverstub import ServerStub
from do_scgi_request import do_scgi_request
import os
import sys
import threading
import time
import socket
import functools
import json
import traceback

socket_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sock")
scgi_req = functools.partial(do_scgi_request, socket.AF_UNIX, socket_file)

class TestSCGIStartupShutdown:
    """SCGI Startup & Shutdown"""
    def setup(self):
        self.threads_before = threading.enumerate()
        self.scgiapp = SCGIApplication(ServerStub(), None, socket_file, 0.001)

    def teardown(self):
        self.scgiapp.shutdown()

        # Git won't clean, touch, or acknowledge the existance of the socket
        # We may as well clean up after ourselves. This should not fail,
        # so there isn't an ENOENT check.
        os.unlink(socket_file)

    def test_start_does_not_fork(self):
        old_fork = os.fork
        def new_fork(*args, **kwargs):
            new_fork.hits += 1
            return old_fork(*args, **kwargs)
        new_fork.hits = 0
        os.fork = new_fork

        self.scgiapp.start()
        assert new_fork.hits == 0

    def test_start_creates_one_acceptor_thread(self):
        # The SocketServer library creates one thread that calls accept()
        # and starts a new thread to handle each connection it receives.

        threads_prestart = threading.enumerate()
        self.scgiapp.start()
        threads_poststart = threading.enumerate()

        assert threads_prestart == self.threads_before
        assert len(threads_prestart) == 1
        assert len(threads_poststart) == 2

    def test_shutdown_stops_all_threads(self):
        self.scgiapp.start()
        assert len(threading.enumerate()) == 2
        self.scgiapp.shutdown()
        assert len(threading.enumerate()) == 1

    def test_shutdown_is_quick(self):
        self.scgiapp.start()
        t1 = time.time()
        self.scgiapp.shutdown()
        t2 = time.time()
        assert t2 - t1 < 1

    def test_shutdown_tolerates_stuck_sockets(self):
        client = socket.socket(socket.AF_UNIX)

        # handle_error will kick up a fuss
        old_handle_error = self.scgiapp.handle_error
        def new_handle_error(request, client_address):
            type = sys.exc_info()[0]
            if type != socket.timeout:
                old_handle_error(request, client_address)
        self.scgiapp.handle_error = new_handle_error

        old_process_request_thread = self.scgiapp.process_request_thread
        def new_process_request_thread(request, client_address):
            new_process_request_thread.hits += 1
            new_process_request_thread.event.set()
            old_process_request_thread(request, client_address)
        new_process_request_thread.hits = 0
        new_process_request_thread.event = threading.Event()
        self.scgiapp.process_request_thread = new_process_request_thread

        self.scgiapp.start()
        assert len(threading.enumerate()) == 2

        assert not new_process_request_thread.event.is_set()
        assert new_process_request_thread.hits == 0

        client.connect(socket_file)

        new_process_request_thread.event.wait()
        assert new_process_request_thread.hits == 1
        assert len(threading.enumerate()) == 3

        t1 = time.time()
        self.scgiapp.shutdown()
        t2 = time.time()

        assert len(threading.enumerate()) == 1
        assert t2 - t1 < 5

        client.close()

test_message_d = {}
test_message_d["callsign"] = "2E0DRX"
test_message_d["type"] = "RECEIVED_TELEM"
test_message_d["data"] = "$$Garbage"
test_message = json.dumps(test_message_d)

class TestSCGIBehaviour:
    """SCGI Behaviour when responding to requests"""
    def setup(self):
        server = ServerStub()
        self.messages = server.messages
        self.scgiapp = SCGIApplication(server, None, socket_file, 0.001)
        self.scgiapp.start()

        old_handle_error = self.scgiapp.handle_error
        self.ignore_exceptions = []
        tester = self

        def new_handle_error(request, client_address):
            type = sys.exc_info()[0]
            if type not in tester.ignore_exceptions:
                old_handle_error(request, client_address)

        self.scgiapp.handle_error = new_handle_error

    def teardown(self):
        self.scgiapp.shutdown()

    def test_returns_info_message(self):
        (headers, body) = scgi_req("/")
        assert headers["Status"] == "200 OK"
        assert headers["Content-Type"] == "text/plain"
        assert body == info_message

    def test_handles_nonexistant_action(self):
        (headers, body) = scgi_req("/raaaaawr", test_message)
        assert headers["Status"].startswith("404")
        assert len(self.messages) == 0

    def test_message_action_passes_all_information(self):
        (headers, body) = scgi_req("/message", test_message)
        assert headers["Status"].startswith("200")
        assert len(self.messages) == 1
        assert self.messages[0].source.callsign == "2E0DRX"
        assert self.messages[0].type == Message.RECEIVED_TELEM
        assert self.messages[0].data == "$$Garbage"

    def test_passes_correct_ip(self):
        scgi_req("/message", test_message, {"REMOTE_ADDR": "2.4.6.7"})
        assert str(self.messages[0].source.ip) == "2.4.6.7"

    def test_catches_invalid_requests(self):
        self.check_catches_invalid_requests({"callsign": "invalid:::"})
        self.check_catches_invalid_requests({"callsign": 1})
        self.check_catches_invalid_requests({"callsign": False})
        self.check_catches_invalid_requests({"type": "TELEM"})
        self.check_catches_invalid_requests({"type": "asdf"})
        self.check_catches_invalid_requests({"type": 2})
        self.check_catches_invalid_requests({"type": None})

    def check_catches_invalid_requests(self, mod):
        self.ignore_exceptions.append(ValueError)
        self.ignore_exceptions.append(TypeError)
        modded_test_message = test_message_d.copy()
        modded_test_message.update(mod)
        modded_test_message = json.dumps(modded_test_message)
        (headers, body) = scgi_req("/message", modded_test_message)
        assert headers["Status"].startswith("400")
        assert len(self.messages) == 0

    def test_invalid_request_does_not_crash_server(self):
        self.ignore_exceptions.append(ValueError)
        (headers, body) = scgi_req("/message", "blah{]2!]2")
        assert headers["Status"].startswith("400")
        assert len(self.messages) == 0
        (headers, body) = scgi_req("/")
        assert headers["Status"] == "200 OK"
