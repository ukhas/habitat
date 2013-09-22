# Copyright 2011 (C) Daniel Richman, Adam Greig
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

"""
Load configured Python functions for later use elsewhere.

The manager is configured with modules to use and it loads all the functions
defined in each module's ``__all__``. This ensures that users cannot specify
arbitrary paths in runtime configuration which may lead to undesired or
insecure behaviour.

The modules that functions are loaded from are given shorthand names to ease
referring to them elsewhere, for example :meth:`habitat.sensors.stdtelem.time`
might become ``stdtelem.time``. The shorthand is specified in the configuration
document.

Configuration
=============

*loadable_manager* reads its configuration data from the config argument
to *LoadableManager.__init__*, which is typically parsed from the
configuration YAML file in the following format::

    loadables:
        - name: "sensors.base"
          class: "habitat.sensors.base"
        - name: "filters.common"
          class: "habitat.filters"

``name`` specifies the shorthand name that the module will be available under;
it should begin either ``sensors`` or ``filters`` for use by the respective
parts of habitat, which prepend the relevant prefix themselves.

For example, to use the filter :meth:`habitat.filters.semicolons_to_commas` in
a flight document, having configured as above, you would specify::

    "filters": {
        "intermediate": {
            [
                {
                    "type": "normal",
                    "filter": "common.semicolons_to_commas"
                }
            ]
        }
    }

Sensor Functions
================

One of the major uses of *loadable_manager* (and historically its only
use) is sensor functions, used by parser modules to convert input data into
usable Python data formats. See :mod:`habitat.sensors` for some sensors
included with habitat, but you may also want to write your own for a specific
type of data.

A sensor function may two one or two arguments, *config* and *data* or just
*data*. It can return any Python object which can be stored in the CouchDB
database.

*config* is a dict of options. It is passed to the function from
:meth:`LoadableManager.run`

*data* is the string to parse.


Filter Functions
================

Another use for the *loadable_manager* is filters that are applied against
incoming telemetry strings. Which filters to use is specified in a payload's
flight document, either as user-specified (but signed) hotfix code or a
loadable function name, as with sensors.

See :py:mod:`habitat.filters` for some filters included with habitat.

Filters can take one or two arguments, *config*, *data* or just *data*. They
should return a suitably modified form of data, optionally using anything from
*config* which was specified by the user in the flight document.
"""

from .utils import dynamicloader


class LoadableManager:
    """
    The main Loadable Manager class.
    """

    def __init__(self, config):
        """
        On construction, all modules listed in config["loadables"] will be
        loaded using :py:meth:`load`.
        """

        self.libraries = {}

        for loadable in config["loadables"]:
            self.load(loadable["class"], loadable["name"])

    def load(self, module, shorthand):
        """Loads *module* as a library and assigns it to *shorthand*."""

        module = dynamicloader.load(module)
        self.libraries[shorthand] = module

    def run(self, name, config, data):
        """
        Run the loadable specified by *name*, giving it *config* and *data*.

        If the loadable only takes one argument, it will only be given *data*.
        *config* is ignored in this case.

        Returns the result of running the loadable.
        """

        name_parts = name.split('.')
        library_name = '.'.join(name_parts[0:-1])
        function_name = name_parts[-1]

        if library_name not in self.libraries:
            raise ValueError("Invalid library name: " + library_name)

        library = self.libraries[library_name]

        if function_name not in library.__all__:
            raise ValueError("Invalid function name: " + function_name)

        func = getattr(library, function_name)

        if dynamicloader.hasnumargs(func, 1):
            return func(data)
        else:
            return func(config, data)

    _repr_format = "<habitat.LoadableManager: {l} libraries loaded>"

    def __repr__(self):
        return self._repr_format.format(l=len(self.libraries))
