# Copyright 2013 (C) Rossen Georgiev
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
import time
import datetime
import re
import math
import copy
import logging
import statsd

logger = logging.getLogger("habitat.aprs")
statsd.init_statsd({'STATSD_BUCKET_PREFIX': 'habitat'})

__all__ = ['APRS', 'APRSModule']

class aprs:
    def __init__(self, host, port, callsign, passwd):
        """
        APRS module that listens and parses sentences passed by aprs.net servers
        """

        self.set_server(host, port)
        self.set_login(callsign, passwd)

        self.sock = None
        self.filter = "b/" # empty bud filter

        self._connected = False;
        self.buf =''

    def callsign_filter(self, callsigns):
        """
        Sets a filter for the specified callsigns. Only those will be send to us by the server
        """

        if type(callsigns) is not list or len(callsigns) == 0:
            return False

        self.filter = "b/%s" % "/".join(callsigns)

        logger.info("Setting filter to: %s" % self.filter)

        if self._connected:
            self.sock.sendall("#filter %s\r\n" % self.filter)

        return True

    def set_login(self, callsign, passwd):
        """
        Set callsign and password
        """
        self.callsign = callsign
        self.passwd = passwd

    def set_server(self, host, port=14850):
        """
        Set server ip/host and port to use
        """
        self.server = (host, port)

    def connect(self, **kwargs):
        """
        Initiate connection to APRS server and attempt to login
        """

        blocking = False  # when true, func wont return until connection is established

        if 'blocking' in kwargs:
            blocking = kwargs['blocking']

        if not self._connected:
            while True:
                try:
                    logger.info("Attempting connection to %s:%s" % (self.server[0], self.server[1]))
                    self._connect()

                    logger.info("Sending login information")
                    self._send_login()

                    logger.info("Login successful")
                    break
                except:
                    if not blocking:
                        raise

                time.sleep(30) # attempt to reconnect after 30 seconds

    def close(self):
        """
        Closes the socket
        Called internally when Exceptions are raised
        """

        self._connected = False
        self.buf = ''

        if self.sock is not None:
            self.sock.close()


    def consumer(self, callback, **kwargs):
        """
        When a position sentence is recieved, it will be passed to the callback function
        """
        blocking = True    # customer runs forever, when false, the cunsumer will return to resume program flow
        immortal = False   # when true, consumer will try to reconnect and stop propagation of Exceptions
        raw = False        # when true, pass raw aprs sentence to callback, otherwise pass parsed data as dict

        for key, value in kwargs.iteritems():
            if key == 'blocking':
                blocking = value
            elif key == 'immortal':
                immortal = value
            elif key == 'raw':
                raw = value

        if not self._connected:
            raise ConnectionError("not connected to a server")

        while True:
            try:
                for line in self._socket_readlines(blocking):
                    if line[0] != "#":
                        if raw:
                            callback(line)
                        else:
                            callback(self._parse(line))
                    #else:
                    #     print "Server: %s" % line
            except KeyboardInterrupt:
                raise
            except (ConnectionDrop, ConnectionError):
                self.close()

                if not immortal:
                    raise
                else:
                    self.connect(blocking=blocking)
                    continue
            except GenericError:
                continue
            except:
                if not immortal:
                    raise
                continue

            if not blocking:
                break


    def _connect(self):
        """
        Attemps to open a connection to the server, retrys if it fails
        """

        try:
            self.sock = socket.create_connection(self.server, 15) # 15 seconds connection timeout
            self.sock.settimeout(5) # 5 second timeout to recieve server banner

            if self.sock.recv(512)[0] != "#":
                raise ConnectionError("invalid banner from server")

            self.sock.setblocking(True)
        except Exception, e:
            self.close()

            if e == "timed out":
                raise ConnectionError("no banner from server")
            else:
                raise ConnectionError(e)


        self._connected = True

    def _send_login(self):
        """
        Sends login string to server
        """
        login_str = "user {0} pass {1} vers habitat-daemon 0.1 filter {2}\r\n".format(self.callsign, self.passwd, self.filter)


        try:
            self.sock.sendall(login_str)
            self.sock.settimeout(5)
            test = self.sock.recv(len(login_str) + 100)
            self.sock.setblocking(True)

            (x, x, callsign, status, x) =  test.split(' ',4)

            if callsign != self.callsign:
                raise LoginError("login callsign does not match")
            if status != "verified,":
                raise LoginError("callsign is not 'verified'")

        except LoginError, e:
            self.close()
            raise LoginError("failed to login: %s" % e)
        except:
            self.close()
            raise LoginError("failed to login")

    def _socket_readlines(self, blocking=False):
        """
        Generator for complete lines, recieved from the server
        """

        try:
            self.sock.setblocking(False)
        except socket.error, e:
            raise ConnectionDrop("connection dropped")

        while True:
            short_buf = ''

            try:
                short_buf = self.sock.recv(64)

                # sock.recv returns empty if the connection drops
                if not short_buf:
                    raise ConnectionDrop("connection dropped")
            except socket.error, e:
                if "Resource temporarily unavailable" in e:
                    if not blocking:
                        if len(self.buf) == 0:
                            break;
            except Exception:
                raise

            self.buf += short_buf

            if "\r\n" in self.buf:
                line, self.buf = self.buf.split("\r\n", 1)
                yield line

            time.sleep(0.5)

    def _get_reciever(self, path):
        path.reverse()

        # reciever callsign is always after q construct
        try:
            while True:
                item = path.pop()
                if item in ['qAR','qAr','qAZ','qAC','qAX','qAU','qAI']:
                    break

            return path.pop()
        except:
            return "UNKNOWN"

    def _parse(self, raw_sentence):
        """
        Parses position sentences and returns a dict with the useful data
        All attributes are in meteric units

        Supported formats:
            FIXED:
                .......!DDMM.hhN/DDDMM.hhW$comments...   (fixed short format)
                       =DDMM.hhN/DDDMM.hhW$comments      (message capable)
                /DDHHMM/DDMM.hhN/DDDMM.hhW$comments...   (no APRS is running)
            MOBILE:
                @DDHHMM/DDMM.hhN/DDDMM.hhW$CSE/SPD/comments...
            DF:
                @DDHHMM/DDMM.hhN/DDDMM.hhWCSE/SPD/BRG/NRQ/Comments
                .......z............................. (indicates Zulu date-time)
                ......./............................. (indicates LOCAL date-time)
                .......h............................. (Zulu time in hhmmss)

            NMAE: (NOT SUPPORTED)
                $GPRMC,151447,A,4034.5189,N,10424.4955,W,6.474,132.5,220406,10.1,E*58

                    1  Time Stamp
                    2  validity - A-ok, V-invalid
                    3  current Latitude
                    4  North/South
                    5  current Longitude
                    6  East/West
                    7  Speed in knots
                    8  True course
                    9  Date Stamp
                    10 Variation
                    11 East/West
                    12 checksum

                $GPGGA,151449,4034.5163,N,10424.4937,W,1,06,1.41,21475.8,M,-21.8,M,,*4D

                    1  UTC of Position
                    2  Latitude
                    3  N or S
                    4  Longitude
                    5  E or W
                    6  GPS quality indicator (0=invalid; 1=GPS fix; 2=Diff. GPS fix)
                    7  Number of satellites in use [not those in view]
                    8  Horizontal dilution of position
                    9  Antenna altitude above/below mean sea level (geoid)
                    10 Meters  (Antenna height unit)
                    11 Geoidal separation (Diff. between WGS-84 earth ellipsoid and
                       mean sea level.  -=geoid is below WGS-84 ellipsoid)
                    12 Meters  (Units of geoidal separation)
                    13 Age in seconds since last update from diff. reference station
                    14 Diff. reference station ID#
                    15 Checksum

            uBlox: (NOT SUPPORTED)
                 $PUBX,00,081350.00,4717.113210,N,00833.915187,E,546.589,G3,2.1,2.0,0.007,77.52,0.007,,0.92,1.19,0.77,9,0,0*5F
                 $PUBX,00,hhmmss.ss,Latitude,N,Longitude,E,AltRef,NavStat,Hacc,Vacc,SOG,COG,Vvel,+ageC,HDOP,VDOP,TDOP,GU,RU,DR,*hh
                 $PUBX,01,hhmmss.ss,Easting,E,Northing,N,AltMSL,NavStat,Hacc,Vacc,SOG,COG,Vvel,ag+eC,HDOP,VDOP,TDOP,GU,RU,DR,*hh

                    $PUBX       - Message ID, UBX protocol header, proprietary sentence
                    00          - Propietary message identifier: 00
                    hhmmss.ss   - UTC Time, Current time
                    ddmm.mmmm   - Latitude, Degrees + minutes
                    [NS]        - N/S Indicator,
                    dddmm.mmmm  - Longitude, Degrees + minutes
                    [EW]        - E/W Indicator,
                    546.589     - (meters) Altitude above user datum ellipsoid.
                    G3          - Navigation Status, See Table below
                    2.1         - Horizontal accuracy estimate.
                    2.0         - Vertical accuracy estimate.
                    0.007       - Speed over ground
                    77.52       - Course over ground
                    0.007       - (m/s) Vertical velocity, positive=downwards
                    -           - Age of most recent DGPS corrections, empty = none available
                    0.92        - HDOP, Horizontal Dilution of Precision
                    1.19        - VDOP, Vertical Dilution of Precision
                    0.77        - TDOP, Time Dilution of Precision
                    9           - Number of GPS satellites used in the navigation solution
                    0           - Number of GLONASS satellites used in the navigation solution
                    0           - DR used
                    *5B         - Checksum

                    Navigation Status
                    -----------------
                    NF No Fix
                    DR Predictive Dead Reckoning Solution
                    G2 Stand alone 2D solution
                    G3 Stand alone 3D solution
                    D2 Differential 2D solution
                    D3 Differential 3D solution

            Custom:
                @DDHHMMhDDMM.hhN/DDDMM.hhWO234/038/A=001563

                    course: 234 degrees
                    speed: 38 kntos
                    altitude: 1563 feet
        """

        logger.info("Parsing: %s" % raw_sentence)

        if len(raw_sentence) < 14:
            raise ParseError("packet is too short to be valid", raw_sentence)

        (header, body) = raw_sentence.split(':',1)
        (source, path) = header.split('>',1)

        # TODO, validate SOURCE callsign and parse path
        # aprs.net should do that for us

        path = path.split(',')
        dest = path[0]
        path = path[1:]
        reciever = self._get_reciever(copy.deepcopy(path))

        parsed = {
                    'raw': raw_sentence,
                    'source': source,
                    'destination': dest,
                    'reciever': reciever,
                    'path': path
                 }

        packet_type = body[0]
        body = body[1:]

        # attempt to parse the body

        # Mic-encoded body
        if packet_type in ("\x27","\x60"):
            raise ParseError("packet seems to be Mic-Encoded, unable to parse", raw_sentence)

        # status messages
        elif packet_type == '>':
            raise ParseError("status messages are not supported", raw_sentence)

        # regular or compressed
        elif packet_type in ('!','=','/','@'):

            # try to parse timestamp
            ts = re.findall(r"^[0-9]{6}[hz\/]$", body[0:7])
            form = ''
            if ts:
                ts = ts[0]
                form = ts[6]
                ts = ts[0:6]
                utc = datetime.datetime.utcnow()

                if form == 'h': # zulu hhmmss format
                    timestamp = utc.strptime("{0} {1} {2} {3}".format(utc.year, utc.month, utc.day, ts), "%Y %m %d %H%M%S")
                elif form == 'z': # zulu ddhhss format
                    timestamp = utc.strptime("{0} {1} {2}".format(utc.year, utc.month, ts), "%Y %m %d%M%S")
                else: # '/' local ddhhss format
                    timestamp = utc.strptime("{0} {1} {2}".format(utc.year, utc.month, ts), "%Y %m %d%M%S")

                parsed.update({ 'timestamp': timestamp.isoformat() + 'Z' })

                # remove datetime from the body for further parsing
                body = body[7:]

            try:
                (
                lat_deg,
                lat_min,
                lat_dir,
                symbol_table,
                lon_deg,
                lon_min,
                lon_dir,
                symbol,
                comment
                ) = re.match(r"^(\d{2})([0-7 ][0-9 ]\.[0-9 ]{2})([NnSs])(.)(\d{3})([0-7 ][0-9 ]\.[0-9 ]{2})([EeWw])([\x21-\x7b\x7d])(.*)$", body).groups()

                logger.debug("Parsing as normal uncompressed format")

                # optional format extention - bearing, speed and altitude (feet)
                extra = re.findall(r"^([0-9]{3})/([0-9]{3})(/A=([0-9]{6})/?)?(.*)$", comment)

                if extra:
                    (bearing, speed, empty, altitude, comment) = extra[0]

                    parsed.update({ 'bearing': int(bearing), 'speed': int(speed)*0.514444 })
                    if altitude:
                        parsed.update({ 'altitude': int(altitude)*0.3048 })

                # TODO throw exception when incorrect symbol table is selected? correct = [\/\\0-9A-Z]
                parsed.update({ 'symbol': symbol, 'symbol_table': symbol_table })

                if int(lat_deg) > 89 or int(lat_deg) < 0:
                    raise ParseError("latitude is out of range (0-90 degrees)", raw_sentence)
                if int(lon_deg) > 179 or int(lon_deg) < 0:
                    raise ParseError("longitutde is out of range (0-180 degrees)", raw_sentence)

                latitude = int(lat_deg) + ( float(lat_min) / 60.0 )
                longitude = int(lon_deg) + ( float(lon_min) / 60.0 )

                parsed.update({'latitude': latitude, 'longitude': longitude})

                # once we have latitude, and we can aproximate local timezone, if we need
                if form not in ('h','z',''):
                    timestamp = timestamp + datetime.timedelta(hours=math.floor(parsed['latitude']/7.5))
                    parsed['timestamp'] = timestamp.isoformat()

            except Exception, e:
                # failed to match normal sentence sentence
                raise ParseError("unknown format", raw_sentence)
        else:
            raise ParseError("format is not supported", raw_sentence)

        logger.info("Parsed ok.")
        return parsed

# Exceptions
class GenericError(Exception):
    def __init__(self, message):
        logger.debug("%s: %s" % (self.__class__.__name__, message))
        self.message = message

    def __str__(self):
        return self.message

class ParseError(GenericError):
    def __init__(self, msg, packet=''):
        GenericError.__init__(self, msg)
        self.packet = packet

class LoginError(GenericError):
    def __init__(self, message):
        logger.error("%s: %s" % (self.__class__.__name__, message))
        self.message = message

class ConnectionError(GenericError):
    pass

class ConnectionDrop(ConnectionError):
    pass
