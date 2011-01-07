================
Database Schema
================

habitat stores information in a CouchDB database. At present four types of
document are stored, identified by a ``type`` key:

    * Configuration documents for habitat itself (``type: "config"``)
    * Flight documents detailing a balloon flight and including payload
      settings (``type: "flight"``)
    * Payload Telemetry documents containing parsed information from a
      telemetry message transmitted by a payload and associated with a Flight
      (``type: "payload_telemetry"``)
    * Listener telemetry documents containing position data on someone
      listening to a payload (``type: "listener_telemetry"``)
    * Listener information documents containing metadata on a listener such as
      name and radio (``type: "listener_info"``)

Ideally all of these documents will be administrated by the web interface but
manual intervention may be required, especially in the case of configuration
and flight documents, so the schema in use is detailed below.


Configuration Documents
=======================

The configuration documents are explained in more detail in the Configuration
section of the documentation, so only a brief overview of the syntax is given
here.

Each document is named depending on the module it configures, for example
``message_server_config`` or ``parser_config``. Besides the ``type`` field,
they are freely structured for that module's needs.

Flight Documents
================

Flight documents are the largest documents involved and also the ones most
likely to be fiddled with manually so a reasonable level of detail is given in
explaining each field.

The high level overview is that each flight document completely describes one
"flight", or "project" or "launch": it has a unique launch time and position
and may contain multiple payloads, each of which may be received by multiple
users. For each payload, the information needed to detect it on a radio, decode
the resulting transmission and then parse it into useful data is given, as well
as any habitat filters that should be applied when parsing data to correct
mistakes. Finally, listeners who are actively chasing after a payload are also
listed with each payload.

Each section is described in more detail below.

Common Flight Data
------------------

The document ID is a standard Couch ID, and each flight document contains the
``type`` field::

    "c89860d6f68b1f31ac9480ff9f95bb62": {
        "_id": "c89860d6f68b1f31ac9480ff9f95bb62",
        "type": "flight",

A start and end date is given as a UNIX timestamp and reflects the time period
that telemetry received for payloads listed on the document will be associated
with this flight. Typically the end date will be 24 hours after the start
date::

    "start": 1292771680,
    "end": 1292772670,

Flight names are used for user interfaces and contain free text::

    "name": "Habitat Test Launch",

The ``launch`` dictionary contains the actual time the flight launched as well
as the timezone it launched in and the location it launched from, in decimal
degrees::

    "launch": {
        "time": 1292771780,
        "timezone": "Europe/London",
        "location": {
            "latitude": 52.2135,
            "longitude": 0.0968,
        }
    },

The ``metadata`` dictionary contains human readable information about the
flight which can be displayed in user interfaces and aid in navigating
archives. All fields are optional and contain free text::

    "metadata": {
        "location": "Churchill College, Cambridge, UK",
        "predicted_landing": "Washed up at sea",
        "project": "habitat",
        "group": "HabHub",
    },

Payload Specific Data
---------------------

The rest of the Flight document contains a ``payloads`` dictionary, which has
payload names as keys and a dictionary containing payload information as the
associated value::
    
    "payloads": {
        "habitat": {
            /* Payload information key:value pairs */
        },
    }

The ``radio`` dictionary details the frequency (in MHz) and mode of
transmissions::

    "radio": {
        "frequency": 434.075,
        "mode": "USB",
    },

The ``telemetry`` dictionary contains information for decoding the received
audio from the radio::
    
    "telemetry": {
        "modulation": "rtty",
        "shift": 425,
        "encoding": "ascii-8",
        "baud": 50,
        "parity": "none",
        "stop": 2
    },

Neither ``radio`` nor ``telemetry`` are actually used by habitat, but instead
are passed on to listeners so they may tune their radios and adjust their
decoding software appropriately.

The ``sentence`` dictionary is used by the habitat parser to retrieve data from
the message strings that listeners upload and as such its design depends on the
parser in use. An example for the UKHAS protocol parser is given below::

    "sentence": {
        "protocol": "UKHAS",
        "checksum": "crc16-ccitt",
        "payload": "habitat",
        "fields": [
            {
                "name": "message_count",
                "type": "int"
            }, {
                "name": "time",
                "type": "time"
            }, {
                "name": "latitude",
                "type": "coordinate",
                "format": "dd.dddd"
            }, {
                "name": "longitude",
                "type": "coordinate",
                "format": "dd.dddd"
            }, {
                "name": "altitude",
                "type": "int"
            }, {
                "name": "speed",
                "type": "float"
            }, {
                "name": "custom_string",
                "type": "string"
            }
        ]
    },

As well as the ``sentence`` dictionary, the parser also uses the ``filters``
dictionary to determine which filters should be applied to telemetry from this
payload. Two levels of filter are available for payloads: "intermediate", which
is applied after the parser has determined which payload the data has been
received from but before that telemetry is parsed for information, and "post",
which is applied to the parsed output data. Both may be specified as a
callable, given as a Python path string, or as code stored in the document
itself, as demonstrated below. In the case of callable filters, a ``config``
dictionary may be given which will be passed to the function along with the
message itself, while hotfix filters specify the text content of a function
which is given ``message`` as its only parameter::

    "filters": {
        "intermediate": [
            {
                "type": "normal",
                "callable": "habitat.filters.ohnonotagain",
                "config": {
                    "fubared": true
                }
            }
        ],
        "post": [
            {
                "type": "hotfix",
                "code": "message['longitude'] = -message['longitude']; return message"
            }
        ]
    },

Finally, the ``chasers`` dictionary lists listeners who are out chasing the
payload and as such may be rendered on the map::

    "chasers": [
        "M0RND",
        "2E0JSO"
    ]

Telemetry Documents
===================

Payload Telemetry
-----------------

Listener Telemetry
------------------

Listener Information Documents
==============================

