==============
Configuration
==============

Startup Configuration
=====================

There are two areas of configuration for habitat. At startup, a CouchDB
database must be identified by a URI and database name, and a socket file given
for CGI communications. These can be given either as command line arguments:

.. code-block:: bash

    habitat.py -c http://user:pass@server:port -d database -s /tmp/socket

habitat will also load configuration options from a configuration file. By
default it will attempt to load /etc/habitat/habitat.cfg but won't complain
if it can't. The config file location can be overridden on the command line:

.. code-block:: bash

    habitat.py -f /etc/habitat/habitat_alternative.cfg

The format of the configuration file is as follows:

.. code-block:: ini

    [habitat]
    couch_uri = http://username:password@server:port
    couch_db = database
    socket_file = /tmp/socket

Command line flags override options specified in a configuration file.

Once this information is obtained, habitat can load itself up and the remaining
configuration is obtained from Couch documents.

Startup Configuration Options
=============================

``(short option, long option [, config file option])``

 * ``-f`` / ``--config-file``: Configuration file to load
 * ``-c`` / ``--couch-uri`` / ``couch_uri``: The couch URI to connect to in
   ``http://username:password@host:port/`` form.
 * ``-d`` / ``--couch-db`` / ``couch_db``: The couch database to use.
 * ``-s`` / ``--socket`` / ``socket_file``: UNIX path; where the SCGI Socket
   should be created.
 * ``-v`` / ``--verbosity`` / ``log_stderr_level``: How verbose output to
   the console should be. Options: NONE, DEBUG, INFO, WARN, ERROR, CRITICAL.
 * ``-l`` / ``--log-file`` / ``log_file``: Log file path.
 * ``-e`` / ``--log-level`` / ``log_file_level``: Log file verbosity
   (same options as verbosity/log_stderr_level)

Runtime Configuration
=====================

Configuration for actual habitat functionality is stored in the Couch database
and can be dynamically reloaded at runtime to allow for configuration updates
without restarting the main server.

Currently three documents are checked for configuration data:
``message_server_config``, ``parser_config`` and ``sensor_manager_config``.

Message Server Configuration
----------------------------

The message server takes a list of sinks that should be loaded at startup,
given as Python path strings. An example configuration might be:

.. code-block:: javascript

    "message_server_config": {
        "_id": "message_server_config",
        "type": "config",
        "sinks": [
            "habitat.parser.ParserSink",
            "habitat.archive.ArchiveSink"
        ]
    }

Parser Configuration
--------------------

The parser sink takes a list of parser modules that should be loaded at
startup, again given as Python path strings but with some additional
information:

* Name, to identify the parser module when a payload specifies it should be
  used
* Pre-filters, Python functions that should be executed before any data is
  passed to this module

The list of modules is given in priority order, with the first item on the
list the first module to be attempted. You should sort them in the order
you are most likely to receive data in.

An example configuration would be:

.. code-block:: javascript

    "parser_config": {
        "_id": "parser_config",
        "type": "config",
        "modules": [
            {
                "name": "UKHAS",
                "class": "habitat.parser_modules.ukhas_parser.UKHASParser",
                "pre-filters": [
                    {
                        "type": "normal",
                        "callable": "habitat.filters.dire_emergency"
                    }
                ]
            }
        ]
    }

Note that pre-filters should be used only when they cannot be avoided as they
will be applied to all incoming data regardless of origin. Individual payloads
can configure intermediate and post-parse filters for manipulating their data
server-side and should be used in preference to pre-filters.

See :doc:`filters` for more information on filters.

Sensor Manager Config
---------------------

The sensor manager loads a selection of sensor function libaries at startup
(in addition to the built-in *base* library). Each library loaded is assigned
a shortcut.

The example below loads the module habitat.sensors.stdtelem and assigns it
the shortcut "stdtelem". This means that the function
``habitat.sensors.stdtelem.time`` can be used simply as ``stdtelem.time``.


.. code-block:: javascript

    "sensor_manager_config": {
        "_id": "sensor_manager_config",
        "type": "config",
        "libraries": {"stdtelem": "habitat.sensors.stdtelem"}
    }

