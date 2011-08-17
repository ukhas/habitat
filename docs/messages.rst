=================================
Message Data and HTTP Post Format
=================================

Every :py:class:`Message <habitat.message_server.Message>` object has three
important attributes:

* ``message.source``: a :py:class:`Listener <habitat.message_server.Listener>`
  object that describes where the message came from (essentially only
  ``message.source.callsign`` and ``message.source.ip`` are of importance)
* ``message.type``: one of 4 (integer) types
* ``message.data``: a dict of key:value pairs

The format of the ``data`` dict depends entirely on the type of message it is.

Inserting Messages by HTTP POST
===============================

habitat includes a SCGI server, which would therefore require a web server
infront of it in order to make http requests to habitat. On
`nessie.habhub.org <http://nessie.habhub.org/>`_, the
`cherokee <http://www.cherokee-project.com/>`_ web server is used.

Messages inserted by HTTP POST are in JSON format. All text is Unicode UTF8
(as specified by JSON) and binary data is base64 encoded (examples below).
The JSON is "posted bare" i.e., the POST data is not URLEncoded in HTTP
query string form (NOT ``value=a+string+with+spaces``). The following
javascript snippet details how such an AJAX request could be made:

.. code-block:: javascript

    var post_test = JSON.stringify(data)
    httpreq.open("POST", "/habitat/message", true);
    httpreq.setRequestHeader("Content-type", "application/json");
    httpreq.setRequestHeader("Content-length", post_text.length);
    httpreq.send(post_text);

The JSON sent should be an "object" (JSON 'object'; python 'dict') with four
name/value pairs: **callsign**, **type**, **time** and **data**,
like in this example:

.. code-block:: javascript

    {
        "callsign": "M0ZDR",
        "type": "LISTENER_INFO",
        "time_created": 1295103598,
        "time_uploaded": 1295103707,
        "data": { "name": "Daniel Richman", "icon": "car" }
    }

**callsign** and **type** are strings.

**callsign** and the IP address from which the HTTP request came are passed to
the initialiser of the :py:class:`Listener <habitat.message_server.Listener>`
class, which imposes the restriction that the callsign must be composed of
alphanumeric and /_ characters only (``a-zA-Z0-9/_``).
The resultant Listener object is the first argument to the initialiser of
:py:class:`Message <habitat.message_server.Message>`. Note that the callsign
that the information in **LISTENER_TELEM** and **LISTENER_INFO** messages
applies to is naturally ``message.source.callsign``, whereas for
**TELEM** and **RECEIVED_TELEM** messages it is ``message.data["payload"]``.

**type** must be the name of one of the message types (below), and cannot be
**TELEM** - these types of messages are created by the Parser and cannot be
inserted by HTTP. The type is converted to an integer, and is the second
argument to the Message initialiser.

**time_created** and **time_uploaded** are UNIX timestamps.
**time_created** represents the time when the message was created and queued
to be uploaded, for example, in the case of a **RECEIVED_TELEM** message, this
would be the second in which the last byte of that string was
received. **time_uploaded** is the time that the HTTP request was started.
For the first attempt at uploading the message **time_created** would
typically be the same as **time_uploaded**, however, if the message is
delayed, or the POST fails and has to be retried, **time_uploaded** must be
the UTC time on the local clock when the HTTP request was sent.
When the message is received by habitat, it takes the difference between
**time_uploaded** and UTC on the server running habitat, and adds that
difference to **time_created** to get the time that the message was created,
with any clock-difference compensated, to within a few seconds (which is
accurate enough for our purposes). This "calculated" time is stored;
**time_uploaded** is discarded and replaced with the current server time.

The type and contents of **data** are entirely specific to the message type.
**data** is passed as-is to the Message initialiser, but this intialiser will
check that it contains valid, correct data.

RECEIVED_TELEM: received telemetry string
=========================================

A single string of telemetry, not necessarily correct or without errors,
from a listener with a radio.

**data** is a JSON object/python dict containing name:value pairs. It must
contain the key **string**, which must be a string containing base64
encoded binary data. In addition, some metadata may optionally be included.
The permitted keys feature below in this example:

.. code-block:: javascript

    "data":
    {
        "string": "JCRoYWJpdGF0LDEyMywxMjo0NTowNiwtMzUuMTAzMiwxMzguODU2OCw0Mjg1LDMuNixoYWIqNTY4MQ==",
        "frequency": 434075199.23  // Frequency the data was received on, in Hz
    }

LISTENER_INFO: listener information
===================================

A message of this type provides metadata about a listener, although does not
provide any information about their location. Listeners typically send
**LISTENER_INFO** messages infrequently, or when something changes. Stationary
listeners (at home, etc.) would send a single **LISTENER_TELEM** message at
the same time as sending one **LISTENER_INFO** message, whereas a chase car
might send infrequent **LISTENER_INFO** messages and regular **LISTENER_TELEM**
messages.

**data** is a JSON object/python dict consisting of name:value pairs, where
the value is always a string. The following example shows the permitted
name/value pairs, all of which are optional:

.. code-block:: javascript

    "data":
    {
        "name": "Adam Greig",
        "location": "Cambridge, UK",
        "radio": "ICOM IC-7000",
        "antenna": "9el 434MHz Yagi"
    }

LISTENER_TELEM: listener telemetry
==================================

Stationary or moving, a **LISTENER_TELEM** message describes a listener's
current location, like so:

.. code-block:: javascript

    "data":
    {
        "time":
        {
            "hour": 12,
            "minute": 40,
            "second": 12
        },
        "latitude": -35.11,
        "longitude": 137.567,
        "altitude": 12
    }

Where **time** is the (reliable) GPS time.

TELEM: (parsed) telemetry data
==============================

As mentioned above, **TELEM** messages are created by the
:py:class:`Parser <habitat.parser.ParserSink>` and cannot be created by
HTTP POST.

**data** is a JSON object/python dict as returned by the parser module used
to parse the data. It varies with protocol, but an example is provided below.

Certain keys are normally present:

* **_protocol**: The name of the parser module used, as specified in its
  configuration document (``db["parser_config"]["modules"][n]["name"]``)
* **_raw**: The raw, binary, input to the parser, in base64.
* **_sentence**: If the protocol used was an ASCII protocol, and there were
  no errors, and every character can be represented as an ascii character,
  the input to the parser in ascii form.
* **payload**: The callsign of the payload
* **message_count**: sequential message number, increases for each message
  transmitted by the payload
* **time**, **latitude**, **longitude**, **altitude**, **speed**: GPS data

.. code-block:: javascript

    "data":
    {
        "_protocol": "UKHAS",
        "_raw": "JCRoYWJpdGF0LDEyMywxMjo0NTowNiwtMzUuMTAzMiwxMzguODU2OCw0Mjg1LDMuNixoYWIqNTY4MQ=="
        "_sentence": "$$habitat,123,12:45:06,-35.1032,138.8568,4285,3.6,hab*5681"
        "payload": "habitat",
        "message_count": 123,
        "time":
        {
            "hour": 12,
            "minute": 45,
            "second": 6
        },
        "latitude": -35.1032,
        "longitude": 138.8568,
        "altitude": 0,
        "speed": 0.0,
        "custom_string": "hab"
    },

