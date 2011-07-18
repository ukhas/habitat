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

import os
import sys
import threading
import time
import socket
import functools
import json
import traceback

from nose.tools import raises

from test_habitat import scratch_dir
from test_habitat.lib import threading_checks
from test_habitat.lib.sample_messages import SMessage
from serverstub import ServerStub
from do_scgi_request import do_scgi_request

from habitat.message_server import Message

from habitat.http import info_message
from habitat.http import SCGIApplication

socket_file = os.path.join(scratch_dir, "sock")
scgi_req = functools.partial(do_scgi_request, socket.AF_UNIX, socket_file)

class TestSCGIStartupShutdown:
    """SCGI Startup & Shutdown"""
    def setup(self):
        threading_checks.patch()
        self.scgiapp = SCGIApplication(ServerStub(), None, socket_file, 0.001)

    def teardown(self):
        self.scgiapp.shutdown()
        threading_checks.check_threads(live=0)

        # Git won't clean, touch, or acknowledge the existance of the socket
        # We may as well clean up after ourselves. This should not fail,
        # so there isn't an ENOENT check.
        os.unlink(socket_file)

        threading_checks.restore()

    def test_start_does_not_fork(self):
        def new_fork(*args, **kwargs):
            new_fork.hits += 1
            return new_fork.old(*args, **kwargs)
        new_fork.hits = 0
        new_fork.old = os.fork
        os.fork = new_fork

        self.scgiapp.start()
        assert new_fork.hits == 0

        os.fork = new_fork.old

    def test_start_creates_one_acceptor_thread(self):
        # The SocketServer library creates one thread that calls accept()
        # and starts a new thread to handle each connection it receives.

        self.scgiapp.start()
        threading_checks.check_threads(live=1)

    def test_shutdown_stops_all_threads(self):
        self.scgiapp.start()
        self.scgiapp.shutdown()
        threading_checks.check_threads(live=0)

    def test_shutdown_is_quick(self):
        self.scgiapp.start()
        t1 = time.time()
        self.scgiapp.shutdown()
        t2 = time.time()
        assert t2 - t1 < 1

    def test_shutdown_tolerates_stuck_sockets(self):
        client = socket.socket(socket.AF_UNIX)

        # handle_error will kick up a fuss
        def new_handle_error(request, client_address):
            type = sys.exc_info()[0]
            if type != socket.timeout:
                new_handle_error.old(request, client_address)
        new_handle_error.old = self.scgiapp.handle_error
        self.scgiapp.handle_error = new_handle_error

        def new_process_request_thread(request, client_address):
            new_process_request_thread.hits += 1
            new_process_request_thread.event.set()
            new_process_request_thread.cont.wait()
            new_process_request_thread.old(request, client_address)
        new_process_request_thread.old = self.scgiapp.process_request_thread
        new_process_request_thread.hits = 0
        new_process_request_thread.event = threading.Event()
        new_process_request_thread.cont = threading.Event()
        self.scgiapp.process_request_thread = new_process_request_thread

        self.scgiapp.start()
        threading_checks.check_threads(live=1)

        assert not new_process_request_thread.event.is_set()
        assert new_process_request_thread.hits == 0

        client.connect(socket_file)

        new_process_request_thread.event.wait()
        assert new_process_request_thread.hits == 1
        threading_checks.check_threads(live=2)
        new_process_request_thread.cont.set()

        t1 = time.time()
        self.scgiapp.shutdown()
        t2 = time.time()

        threading_checks.check_threads(live=0)
        assert t2 - t1 < 5

        client.close()

test_message_d = {}
test_message_d["callsign"] = "M0ZDR"
test_message_d["type"] = "LISTENER_INFO"
test_message_d["time_created"] = 0
test_message_d["time_uploaded"] = 0
# Grab some known valid data from the sample_messages module and add some
# unicode.
test_message_d["data"] = SMessage(type=Message.LISTENER_INFO).data
test_message_d["data"]["name"] = u"Snowman " + unichr(0x2603)
test_message = json.dumps(test_message_d)

class TestSCGIBehaviour:
    """SCGI Behaviour when responding to requests"""
    def setup(self):
        server = ServerStub()
        self.messages = server.messages
        self.scgiapp = SCGIApplication(server, None, socket_file, 0.001)
        self.scgiapp.start()

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
        assert self.messages[0].source.callsign == "M0ZDR"
        assert self.messages[0].type == Message.LISTENER_INFO
        assert self.messages[0].data["name"] == "Snowman " + unichr(0x2603)

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
        modded_test_message = test_message_d.copy()
        modded_test_message.update(mod)
        modded_test_message = json.dumps(modded_test_message)
        (headers, body) = scgi_req("/message", modded_test_message)
        assert headers["Status"].startswith("400")
        assert len(self.messages) == 0

    def test_invalid_request_does_not_crash_server(self):
        (headers, body) = scgi_req("/message", "blah{]2!]2")
        assert headers["Status"].startswith("400")
        assert len(self.messages) == 0
        (headers, body) = scgi_req("/")
        assert headers["Status"] == "200 OK"
