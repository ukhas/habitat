==============
Configuration
==============

Command Line Configuration
==========================

habitat daemons takes zero or one command line arguments: an optional filename
specifying the configuration to use, or "./habitat.yml" by default:

.. code-block:: bash

    ./bin/parser
    # or
    ./bin/parser /path/to/config.yml


Configuration File
==================

The configuration file is written in `YAML <http://www.yaml.org/>`_ as several
key: value pairs. Various habitat components may require certain pieces of
configuration; where possible these are all documented here.

habitat-wide Configuration
--------------------------

.. code-block:: yaml

    couch_uri: "http://localhost:5984"
    couch_db: habitat
    log_stderr_level: DEBUG
    log_file_level: INFO

*couch_uri* and *couch_db* specify how to connect to the CouchDB database. The
URI may contain authentication details if required.

*log_stderr_level* and *log_file_level* set the log levels for a log file and
the stderr output and may be "NONE", "ERROR", "WARN", "INFO" or "DEBUG".

parser configuration
--------------------

.. code-block:: yaml

    parser:
        certs_dir: "/path/to/certs"
        modules:
            - name: "UKHAS"
              class: "habitat.parser_modules.ukhas_parser.UKHASParser"
    parserdaemon:
        log_file: "/path/to/parser/log"

Inside the *parser* and *parserdaemon* objects:

* *certs_dir* specifies where the habitat certificates (used for code signing)
  are kept
* *log_file* specifies where the parser daemon should write its log file to
* *modules* gives a list of all the parser modules that should be loaded, with
  a name (that must match names used in flight documents) and the Python path
  to load.

This configuration is used by :doc:`/habitat/habitat/habitat.parser` and
:doc:`/habitat/habitat/habitat.parser_daemon`.

loadable_manager configuration
------------------------------

.. code-block:: yaml
    
    loadables:
        - name: "sensors.base"
          class: "habitat.sensors.base"
        - name: "sensors.stdtelem"
          class: "habitat.sensors.stdtelem"
        - name: "filters.common"
          class: "habitat.filters"

Inside the *loadables* object is a list of modules to load and the short name
they should be loaded against. This is used by :doc:`/habitat/habitat/habitat.loadable_manager`.
