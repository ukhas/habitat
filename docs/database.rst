====================
Database information
====================

Schema
======

habitat stores information in a CouchDB database. At present five types of
document are stored, identified by a ``type`` key:

* Flight documents detailing a balloon flight (``type: "flight"``)
* Payload Configuration documents containing settings for one payload, such as
  radio transmission data and format (``type: "payload_configuration"``).
* Payload Telemetry documents containing parsed information from a
  telemetry message transmitted by a payload and associated with a Flight
  (``type: "payload_telemetry"``)
* Listener telemetry documents containing position data on someone
  listening to a payload (``type: "listener_telemetry"``)
* Listener information documents containing metadata on a listener such as
  name and radio (``type: "listener_information"``)

The schema are described using JSON Schema and the latest version may be
browsed online via `jsonschema explorer <http://habitat.habhub.org/jse>`_.

Database documents are typically managed through the various web interfaces and
are uploaded and retrieved using the
`CouchDB API <http://wiki.apache.org/couchdb/HTTP_Document_API>`_.


Views, Filters & Validation Functions
=====================================

Documents in the habitat CouchDB are indexed and accessed using CouchDB views,
which are pre-calculated sets of results that are updated automatically and may
be paged and searched through.

A selection of generic views are provided, but it's entirely likely that a
custom view would be required for a given application.

Three types of function may be defined in a CouchDB design document. Views
consist of a map and optionally a reduce and are typically used to query stored
data. Filters selectively include certain documents in a stream from the
database, for example to the parser. Validation functions check all new
incoming documents to ensure they meet whatever requirements are imposed,
making sure that only valid documents are stored in the database.

For more comprehensive information, please refer to the 
`CouchDB documentation <http://wiki.apache.org/couchdb/Introduction_to_CouchDB_views>`_.

Included Views
==============

For documentation on the views currently included with habitat, please refer to
the source documentation for each: :doc:`/habitat/habitat/habitat.views`.

Using Views: Example
====================

Simple Example
--------------

In this simple example we just fetch the list of `payload_configuration`
documents and print out payload names. The full configuration document is
available as `payload["doc"]`.

Python
~~~~~~

.. code-block:: python

    import couchdbkit
    db = couchdbkit.Server("http://habitat.habhub.org")["habitat"]
    payloads = db.view("payload_configuration/name_time_created", include_docs=True)
    for payload in payloads:
        print "Payload: {0}".format(payload["key"][0])


Javascript
~~~~~~~~~~

.. code-block:: html

    <script src="jquery.couch.js"></script>

.. code-block:: javascript

    db = $.couch.db("habitat")
    db.view("payload_configuration/name_time_created", {include_docs: true, success: function(data) {
        for(payload in data.rows) {
            console.log("Payload: " + data.rows[payload].key[0]);
        }
    }});


View Collation
--------------

A more complicated example, which demonstrates
`view collation <http://wiki.apache.org/couchdb/View_collation>`_. The
`flight/launch_time_including_payloads` view returns both `flight` documents
and the associated `payload_configuration` documents, indicated by the second
item in the key (0 for `flight`, 1 for `payload_configuration`). This code
snippet fetches all the flights and prints their name and launch time and the
name of each payload in them.

Python
~~~~~~

.. code-block:: python

    import couchdbkit
    db = couchdbkit.Server("http://habitat.habhub.org")["habitat"]
    flights = db.view("flight/launch_time_including_payloads", include_docs=True)
    for flight in flights:
        if flight["key"][1] == 0:
            print "Flight {0} launches at {1}!".format(
                flight["doc"]["name"], flight["doc"]["launch"]["time"])
            print "  Payloads:"
        else:
            print "    {0}".format(flight["doc"]["name"])
