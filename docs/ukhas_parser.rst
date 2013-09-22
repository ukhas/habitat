.. _ukhas-parser-config:

==========================
UKHAS Parser Configuration
==========================

Introduction
============

The UKHAS protocol is the most widely used at time of writing, and is
implemented by the UKHAS parser module. This document provides information
on how what configuration settings the UKHAS parser module expects.

Parser module configuration is given in the "sentence" dictionary of the
payload dictionary in a flight document.

Generating Payload Configuration Documents
==========================================

The easiest and recommended way to generate configuration documents is using
the web tool `genpayload <http://habitat.habhub.org/genpayload>`_.

Standard UKHAS Sentences
========================

A typical minimum UKHAS protocol sentence may be::

    $$habitat,123,13:16:24,51.123,0.123,11000*ABCD

This sentence starts with a double dollar sign (``$$``) followed by the
payload name (here ``habitat``), several comma-delimited fields and is then
terminated by an asterisk and four-digit CRC16 CCITT checksum (``*ABCD``).

In this typical case, the fields are a message ID, the time, a GPS
latitude and longitude in decimal degrees, and the current altitude.

However, both the checksum algorithm in use and the number, type and order of
fields may be configured per-payload.

Parser Module Configuration
===========================

The parser module expects to be given the callsign, the checksum algorithm,
the protocol name ("UKHAS") and a list of fields, each of which should at
least specify the field name and data type.

Checksum Algorithms
-------------------

Three algorithms are available:

* CRC16 CCITT (``crc16-ccitt``):

  The recommended algorithm, uses two bytes
  transmitted as four ASCII digits in hexadecimal. Can often be
  calculated using libraries for your payload hardware platform.
  In particular, note that we use a polynomial of 0x1021 and a start
  value of 0xFFFF, without reversing the input. If implemented
  correctly, the string ``habitat`` should checksum to 0x3EFB.

* XOR (``xor``):

  The simplest algorithm, calculating the one-byte XOR
  over all the message data and transmitting as two ASCII digits in
  hexadecimal. ``habitat`` checksums to 0x63.

* Fletcher-16 (``fletcher-16``):

  Not recommended but supported. Uses a modulus of 255 by default, if
  modulus 256 is required use ``fletcher-16-256``.

In all cases, the checksum is of everything after the ``$$`` and before
the ``*``.

Field Names
-----------

Field names may be any string that does not start with an underscore. It is
recommended that they follow the basic pattern of
``prefix[_suffix[_suffix[...]]]`` to aid presentation: for example,
``temperature_internal`` and ``temperature_external`` could then be grouped
together automatically by a user interface.

In addition, several common field names have been standardised on, and their
use is strongly encouraged:

.. list-table::
    :header-rows: 1

    * - **Field**
      - **Name To Use**
      - **Notes**
    * - **Sentence ID** (aka count, message count, sequence number)
      - ``sentence_id``
      - An increasing integer
    * - **Time**
      - ``time``
      - Something like HH:MM:SS or HHMMSS or HHMM or HH:MM.
    * - **Latitude**
      - ``latitude``
      - Will be converted to decimal degrees based on *format* field.
    * - **Longitude**
      - ``longitude``
      - Will be converted to decimal degrees based on *format* field.
    * - **Altitude**
      - ``altitude``
      - In, or converted to, metres.
    * - **Temperature**
      - ``temperature``
      - Should specify a suffix, such as ``_internal`` or ``_external``. In or
        converted to degrees Celsius.
    * - **Satellites In View**
      - ``satellites``
      -
    * - **Battery Voltage**
      - ``battery``
      - Suffixes allowable, e.g., ``_backup``, ``_cutdown``, but without the
        suffix it is treated as the main battery voltage. In volts.
    * - **Pressure**
      - ``pressure``
      - Suffixes allowable, e.g., ``_balloon``. Should be in or converted to
        Pa.
    * - **Speed**
      - ``speed``
      - For speed over the ground. Should be converted to m/s (SI units).
    * - **Ascent Rate**
      - ``ascentrate``
      - For vertical speed. Should be m/s.

Standard user interfaces will use title case to render these names, so
``flight_mode`` would become ``Flight Mode`` and so on. Some exceptions may be
made in the case of the common field names specified above.


Field Types
-----------

Supported types are:

* ``string``: a plain text string which is not interpreted in any way.
* ``float``: a value that should be interpreted as a floating point
  number. Transmitted as a string, e.g., "123.45", rather than in
  binary.
* ``int``: a value that should be interpreted as an integer.
* ``time``: a field containing the time as either ``HH:MM:SS`` or just
  ``HH:MM``. Will be interpreted into a time representation.
* ``time``: a field containing the time of day, in one of the following
  formats: ``HH:MM:SS``, ``HHMMSS``, ``HH:MM``, ``HHMM``.
* ``coordinate``: a coordinate, see below

Coordinate Fields
-----------------

Coordinate fields are used to contain, for instance, payload latitude and
longitude. They have an additional configuration parameter, ``format``, which
is used to define how the coordinate should be parsed. Options are:

* ``dd.dddd``: decimal degrees, with any number of digits after the
  decimal point. Leading zeros are allowed.
* ``ddmm.mm``: degrees and decimal minutes, with the two digits just before the
  decimal point representing the number of minutes and all digits before those
  two representing the number of degrees.

In both cases, the number can be prefixed by a space or + or - sign.

Please note that the the options reflect the style of coordinate (degrees only
vs degrees and minutes), not the number of digits in either case.

Units
-----

Received data may use any convenient unit, however it is strongly recommended
that filters (see below) be used to convert the incoming data into SI units.
These then allow for standardisation and ease of display on user interface
layers.

Filters
-------

See :doc:`filters`
