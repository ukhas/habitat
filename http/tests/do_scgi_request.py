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

import socket
import errno

def do_scgi_request(socket_type, socket_addr, url, data=None, headers=None):
    if headers == None:
        headers = {}

    uhkeys = map(str.upper, headers.keys())
    for i in ["CONTENT_LENGTH", "SCGI", "REQUEST_METHOD", "REQUEST_URI"]:
        assert i not in uhkeys

    if "REMOTE_ADDR" not in headers.keys():
        assert "REMOTE_ADDR" not in uhkeys
        headers["REMOTE_ADDR"] = "127.0.0.1"

    if data is None:
        headers["REQUEST_METHOD"] = "GET"
        headers["CONTENT_LENGTH"] = "0"
        data = ""
    else:
        headers["REQUEST_METHOD"] = "POST"
        headers["CONTENT_LENGTH"] = str(len(data))

    headers["SCGI"] = "1"
    headers["PATH_INFO"] = url

    headers_data = []
    for (k, v) in headers.items():
        headers_data.append(k)
        headers_data.append(v)
    headers_data = "\0".join(headers_data) + "\0" # add a final separator

    request = str(len(headers_data)) + ":" + headers_data + "," + data

    client = socket.socket(socket_type)
    client.connect(socket_addr)
    client.sendall(request)

    response = ""

    try:
        while True:
            data = client.recv(4096)
            response += data

            if len(data) == 0:
                break
    except socket.error, e:
        if e.errno != errno.ECONNRESET:
            raise

    client.close()

    pos = 0
    headers = {}
    while True:
        npos = response.find("\r\n", pos)
        if npos == pos:
            pos = npos + 2
            break

        header = response[pos:npos].split(":")
        if header[1][0] == " ":
            header[1] = header[1][1:]
        headers[header[0]] = header[1]

        pos = npos + 2

    body = response[pos:]

    return (headers, body)
