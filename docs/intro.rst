Introduction
============

habitat is a system for uploading, processing, storing and displaying
telemetry and related information transmitted from high altitude balloons.

Typically this telemetry takes the form of a GPS position and potentially
other data, accompanied by information on who received the data, and is
displayed by means of a map or chart (or both) showing the path a balloon
took and the historic trend of sensor readings.

Internally, configuration and data is stored in a CouchDB database. The
back end is written in Python and is responsible for parsing incoming data
and storing it in the database, while the frontend is written independently
in JavaScript and HTML and communicates with CouchDB directly to obtain
data and display it.

This documentation covers setting up a habitat system, describes the format
used to store data in CouchDB, and provides reference documentation for the
habitat source code.

Useful habitat links:

* `habitat on github <http://github.com/ukhas/habitat/>`_
* `habitat's continuous integration server <http://ci.habhub.org/>`_
* `this documentation <http://habitat.habhub.org/docs/>`_
* `habitat home page <http://habitat.habhub.org/>`_
