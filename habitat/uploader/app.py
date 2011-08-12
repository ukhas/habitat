# Copyright 2011 (C) Daniel Richman
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
This module provides a super lightweight flask application that provides an
easy interface to an Uploader for other processes
"""

import flask
import base64
import json
from .. import uploader

app = flask.Flask("habitat.uploader.app")

couch_settings = {
    "couch_uri": "http://localhost:5984/",
    "couch_db": "habitat_test"
}

@app.route("/")
def hello():
    return """
    <html>
    <body>

    <form action="payload_telemetry" method="POST">
    <h3>payload_telemetry</h3>
    <p>Callsign: <input type="text" name="callsign"></p>
    <p>String (b64): <input type="text" name="string"></p>
    <p>Metadata (json): <input type="text" name="metadata" value="{}"></p>
    <p>Time created (int, POSIX): <input type="text" name="time_created"></p>
    <p><input type="submit" value="GO">
    </form>

    <form action="listener_info" method="POST">
    <h3>listener_info</h3>
    <p>Callsign: <input type="text" name="callsign"></p>
    <p>Data (json): <input type="text" name="data" value="{}"></p>
    <p>Time created (int, POSIX): <input type="text" name="time_created"></p>
    <p><input type="submit" value="GO">
    </form>

    <form action="listener_telemetry" method="POST">
    <h3>listener_telemetry</h3>
    <p>Callsign: <input type="text" name="callsign"></p>
    <p>Data (json): <input type="text" name="data" value="{}"></p>
    <p>Time created (int, POSIX): <input type="text" name="time_created"></p>
    <p><input type="submit" value="GO">
    </form>
    """

def get_time_created():
    if "time_created" not in flask.request.form:
        return None

    time_created = flask.request.form["time_created"]
    if not time_created:
        return None

    return int(time_created)

@app.route("/payload_telemetry", methods=["POST"])
def payload_telemetry():
    callsign = flask.request.form["callsign"]
    string = base64.b64decode(flask.request.form["string"])
    metadata = json.loads(flask.request.form["metadata"])
    time_created = get_time_created()

    assert callsign and string
    assert isinstance(metadata, dict)

    u = uploader.Uploader(callsign=callsign, **couch_settings)
    u.payload_telemetry(string, metadata, time_created)

    return "OK"

@app.route("/listener_info", methods=["POST"])
def listener_info():
    callsign = flask.request.form["callsign"]
    data = json.loads(flask.request.form["data"])
    time_created = get_time_created()

    assert callsign and data
    assert isinstance(data, dict)

    u = uploader.Uploader(callsign=callsign, **couch_settings)
    u.listener_info(data, time_created)

    return "OK"

@app.route("/listener_telemetry", methods=["POST"])
def listener_info():
    callsign = flask.request.form["callsign"]
    data = json.loads(flask.request.form["data"])
    time_created = get_time_created()

    assert callsign and data
    assert isinstance(data, dict)

    u = uploader.Uploader(callsign=callsign, **couch_settings)
    u.listener_info(data, time_created)

    return "OK"
