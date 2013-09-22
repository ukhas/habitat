========
Filters
========

Filter Levels
==============

There are three points in the message flow at which a filter can act: before
pre-parsing happens, after the pre-parse but before the main parse, and after
the main parse.

Pre-parsing extracts a callsign from a string and uses it to
look up the rest of the payload's configuration, so pre-parse filters are
specified per module and will act on everything that module receives. These are
called pre-filters and are specified in the parser configuration document.

Intermediate filters act after a callsign has been found but before the message
is parsed for data, so they can correct particular format errors a certain
payload might be transmitting. Post-parse filters act after the data parsing
has happened, so can tweak the output data. Both intermediate and post filters
are specified in the payload section of a flight document.

Filter Syntax
==============

Two types of filters are supported: ``normal`` and ``hotfix``. Normal filters
give a callable object, which must be in the Python path, and optionally may
give a configuration object which will be passed as the second argument to the
callable. Hotfix filters just supply some Python code, which is used as the
body of a function given the incoming data as its sole argument.
In either case, the filter must return the newly processed data.

Example of a normal filter:

.. code-block:: javascript

    {
        "type": "normal",
        "callable": "habitat.filters.upper_case"
    }

.. code-block:: python

    # habitat/filters.py
    def upper_case(data):
        return data.upper()

A normal filter with a configuration object:

.. code-block:: javascript

    {
        "type": "normal",
        "callable": "habitat.filters.daylight_savings",
        "config": {"time_field": 7}
    }

.. code-block:: python

    # habitat/filters.py
    def daylight_savings(data, config):
        time = data[config['time_field']]
        hour = int(time[0:2])
        data[config['time_field']] = str(hour + 1) + time[2:]
        return data

A hotfix filter:

.. code-block:: javascript

    {
        "type": "hotfix",
        "code": "parts = data.split(',')\nreturn '.'.join(parts)\n"
    }

Which would be assembled into:

.. code-block:: python
    
    def f(data):
        parts = data.split(',')
        return '.'.join(parts)

A more complete hotfix example, to fix non-zero-padded time values:

.. code-block:: python

    from habitat.utils.filtertools import UKHASChecksumFixer

    parts = data.split(",")
    timestr = parts[2]
    timeparts = timestr.split(":")
    timestr = "{0:02d}:{1:02d}:{2:02d}".format(*[int(part) for part in timeparts])
    parts[2] = timestr
    newdata = ",".join(parts)

    with UKHASChecksumFixer('xor', {"data": data}) as fixer:
        fixer["data"] = newdata

        return fixer["data"]

Filter Utils
============

Please refer to :doc:`/habitat/habitat/habitat/habitat.utils.filtertools` for
information on available filter tools such as UKHASChecksumFixer used above.
