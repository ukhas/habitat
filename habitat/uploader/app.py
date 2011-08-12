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
    "couch_uri": "http://habitat.habhub.org/",
    "couch_db": "habitat_test"
}

@app.route("/")
def hello():
    return "Hello World! Perhaps you want to POST to somewhere else?"

@app.route("/payload_telemetry", methods=["POST"])
def payload_telemetry():
    callsign = flask.request.form["callsign"]
    string = base64.b64decode(flask.request.form["string"])
    metadata = json.loads(flask.request.form["metadata"])

    assert callsign and string
    assert isinstance(metadata, dict)

    u = uploader.Uploader(callsign=callsign, **couch_settings)
    u.payload_telemetry(string, metadata)

    return "OK"

@app.route("/listener_info", methods=["POST"])
def listener_info():
    callsign = flask.request.form["callsign"]
    data = json.loads(flask.request.form["data"])

    assert callsign and data
    assert isinstance(data, dict)

    u = uploader.Uploader(callsign=callsign, **couch_settings)

    return "OK"

@app.route("/listener_telemetry", methods=["POST"])
def listener_info():
    callsign = flask.request.form["callsign"]
    data = json.loads(flask.request.form["data"])

    assert callsign and data
    assert isinstance(data, dict)

    u = uploader.Uploader(callsign=callsign, **couch_settings)

    return "OK"
