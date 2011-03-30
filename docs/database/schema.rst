===========
Full Schema
===========

habitat stores information in a CouchDB database. At present six types of
document are stored, identified by a ``type`` key:

* Configuration documents for habitat itself (``type: "config"``)
* Flight documents detailing a balloon flight and including payload
  settings (``type: "flight"``)
* Sandbox documents containing test payload configuration settings
  not in a flight (``type: "sandbox"``)
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

.. seealso:: :doc:`example`

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
likely to be fiddled with manually so a reasonable level of detail is given
in explaining each field.

The high level overview is that each flight document completely describes one
"flight", or "project" or "launch": it has a unique launch time and position
and may contain multiple payloads, each of which may be received by multiple
users. For each payload, the information needed to detect it on a radio,
decode the resulting transmission and then parse it into useful data is
given, as well as any habitat filters that should be applied when parsing
data to correct mistakes. Finally, listeners who are actively chasing after a
payload are also listed with each payload.

Each section is described in more detail below.

Common Flight Data
------------------

The document ID is a standard Couch ID, and each flight document contains the
``type`` field:

.. code-block:: javascript

    "c89860d6f68b1f31ac9480ff9f95bb62": {
        "_id": "c89860d6f68b1f31ac9480ff9f95bb62",
        "type": "flight",

A start and end date is given as a UNIX timestamp and reflects the time
period that telemetry received for payloads listed on the document will be
associated with this flight. Typically the end date will be 24 hours after
the start date:

.. code-block:: javascript

    "start": 1292771680,
    "end": 1292772670,

Flight names are used for user interfaces and contain free text:

.. code-block:: javascript

    "name": "Habitat Test Launch",

The ``launch`` dictionary contains the actual time the flight launched as
well as the timezone it launched in and the location it launched from, in
decimal degrees:

.. code-block:: javascript

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
archives. All fields are optional and contain free text:

.. code-block:: javascript

    "metadata": {
        "location": "Churchill College, Cambridge, UK",
        "predicted_landing": "Washed up at sea",
        "project": "habitat",
        "group": "HabHub",
    },

Payload Specific Data
---------------------

The rest of the Flight document contains a ``payloads`` dictionary, which has
payload names/callsigns as keys and a dictionary containing payload
information as the associated value:

.. code-block:: javascript

    "payloads": {
        "habitat": {
            // Payload information key:value pairs
        },
    }

The ``radio`` dictionary details the frequency (in MHz) and mode of
transmissions:

.. code-block:: javascript

    "radio": {
        "frequency": 434.075,
        "mode": "USB",
    },

The ``telemetry`` dictionary contains information for decoding the received
audio from the radio:

.. code-block:: javascript

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

The ``sentence`` dictionary is used by the habitat parser to retrieve data
from the message strings that listeners upload and as such its design depends
on the parser in use. An example for the UKHAS protocol parser is given
below:

.. code-block:: javascript

    "sentence": {
        "protocol": "UKHAS",
        "checksum": "crc16-ccitt",
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
dictionary to determine which filters should be applied to telemetry from
this payload. Two levels of filter are available for payloads:
"intermediate", which is applied after the parser has determined which
payload the data has been received from but before that telemetry is parsed
for information, and "post", which is applied to the parsed output data. Both
may be specified as a callable, given as a Python path string, or as code
stored in the document itself, as demonstrated below. In the case of callable
filters, a ``config`` dictionary may be given which will be passed to the
function along with the message itself, while hotfix filters specify the text
content of a function which is given ``message`` as its only parameter:

.. code-block:: javascript

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
payload and as such may be rendered on the map:

.. code-block:: javascript

    "chasers": [
        "M0RND",
        "2E0JSO"
    ]

Sandbox Documents
-----------------

Sandbox documents are like Flight documents but only contain the *payloads*
dictionary, and configuration from them will be used when no suitable flight
is found for a given payload. They have a ``type`` of ``sandbox``.


Telemetry Documents
===================

There are two forms of telemetry document: payload and listener telemetry.
The former contains information transmitted by payloads such as position and
sensor readings, while the latter contains updates from people listening to
payloads, such as position.

Payload Telemetry
-----------------

Unlike other documents, payload telemetry uses the SHA256 sum of the base64
encoded representation of the uploaded data as their document ID. This helps
prevent a race condition if two people attempt to submit the same string at
the same time -- Couch will prevent them from both adding an identically IDd
document, so one can back off and update the first listener's document
instead:

.. code-block:: javascript

    "8bcee9a6f1d0182f1cf1c23c3650d3e6d50a3f46737205b2f3929c7da674e082": {
        "_id": "8bcee9a6f1d0182f1cf1c23c3650d3e6d50a3f46737205b2f3929c7da674e082",

The ``type`` field is set to ``payload_telemetry``:

.. code-block:: javascript

    "type": "payload_telemetry",

As the listener clocks may be inaccurate, we attempt to calculate the
time each piece of telemetry was received. This estimated value is stored
in ``estimated_time_created``:

.. code-block:: javascript

    "estimated_time_created": 1292772125,

The flight that this telemetry came from is also stored if it was available:

.. code-block:: javascript
    
    "flight": "c89860d6f68b1f31ac9480ff9f95bb62",

The information parsed out of the message string is stored in the ``data``
dictionary, directly as returned by the parser:

.. seealso:: :doc:`../messages`, :doc:`example`,
             :py:mod:`habitat.parser`, :py:mod:`habitat.parser_modules`

.. code-block:: javascript

    "data": {
        "_protocol": "UKHAS",
        "_raw": "JCRoYWJpdGF0LDEyMywxMjo0NTowNiwtMzUuMTAzMiwxMzguODU2OCw0Mjg1LDMuNixoYWIqNTY4MQ=="
        "_sentence": "$$habitat,123,12:45:06,-35.1032,138.8568,4285,3.6,hab*5681"
        "payload": "habitat",
        "message_count": 123,
        "time": {
            "hour": 12,
            "minute": 45,
            "second": 6
        },
        "latitude": -35.1032,
        "longitude": 138.8568,
        "altitude": 0,
        "speed": 0.0,
        "custom_string": "hab"
    }

Finally, there is a list of receivers -- listeners who submitted this
piece of telemetry. For each receiver, we store their callsign or identifier
as the key, and inside that dictionary the time they believe they received
the packet (based on their local clock), the time we received their
submission (based on the server clock), the CouchID of their latest
piece of listener telemetry, used to locate them when they received that
message (see the next section), and the CouchID of their latest listener
information document:

.. code-block:: javascript

    "receivers": {
        "M0RND": {
            "time_created": 1292772125,
            "time_uploaded": 1292772130,
            "latest_telemetry": "10bedc8832fe563c901596c900001906",
            "latest_info": "10bedc8832fe563c901596c900038917"
        },
        "M0ZDR": {
            "time_created": 1292772126,
            "time_uploaded": 1292772122,
            "latest_telemetry": "10bedc8832fe563c901596c9000031dd"
            "latest_info": "10bedc8832fe563c901596c9000079fe"
        }
    }

Listener Telemetry
------------------

Listener telemetry documents are shorter and simpler than payload telemetry.
Each consists of a Couch ID, a ``type`` field of ``listener_telemetry``,
the time the document was uploaded and some basic data about the listener,
typically a callsign, time and GPS position:

.. code-block:: javascript

    "10bedc8832fe563c901596c900001906": {
        "type": "listener_telemetry",
        "time_created": 1292772138,
        "time_uploaded": 1292772140,
        "data": {
            "callsign": "M0RND",
            "time": {
                "hour": 12,
                "minute": 40,
                "second": 12
            },
            "latitude": -35.11,
            "longitude": 137.567,
            "altitude": 12
        }
    }

Listener Information Documents
==============================

Listener information documents make up the fifth document type, with a
``type`` of ``listener_info``. They contain metadata about a listener and
are essentially free-form, used to display information of interest in the
user interface. They use Couch IDs for document IDs, and may typically
contain information such as a human readable location, the radio or antenna
system in use, a real name and a callsign or other identifier. An example
follows:

.. code-block:: javascript

    "10bedc8832fe563c901596c9000026d3": {
        "type": "listener_info",
        "time_created": 1292772133,
        "time_uploaded": 1292772135,
        "data": {
            "callsign": "M0RND",
            "name": "Adam Greig",
            "location": "Cambridge, UK",
            "radio": "ICOM IC-7000",
            "antenna": "9el 434MHz Yagi"
        }
    }
