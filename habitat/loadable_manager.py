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
``habitat.loadable_manager``: the loadable-function manager

This manager is given a list of modules to load from the configuration file,
and it loads all of the functions in each module such that they can later be
used by other pieces of habitat code while ensuring that only modules specified
on the command line can be used in such a way; this prevents user-specified
Python code paths being used.

The modules that functions are loaded from are given shorthand names to ease
referring to them from configuration documents et cetera, for example
``habitat.sensors.stdtelem.time`` might become ``stdtelem.time``. The shorthand
is specified in the configuration document.

Sensor Functions
================

One of the major uses of loadable_manager (and historically its only use) is
sensor functions, used by parser modules to convert input data into usable
Python data formats. See :py:mod:`habitat.sensors` for some sensors included
with habitat, but you may also want to write your own for a specific type of
data.

A sensor function may two one or two arguments, *config* and *data* or just
*data*. It can return any Python object which can be stored in the CouchDB
database.

*config* is a dict of options. It is passed to the function from
:py:meth:`LoadableManager.run`

*data* is the string to parse.


Filter Functions
================

Another use for the loadable_manager is filters that are applied against
incoming telemetry strings. Which filters to use is specified in a payload's
flight document, either as user-specified (but signed) hotfix code or a
loadable function name, as with sensors.

See :py:mod:`habitat.filters` for some filters included with habitat.

Filters can take one or two arguments, *config*, *data* or just *data*. They
should return a suitably modified form of data, optionally using anything from
*config* which was specified by the user in the flight document.
"""

from .utils import dynamicloader

__all__ = ["LoadableManager"]

class LoadableManager:
    """The main Loadable Manager class"""

    def __init__(self, config):
        """
        *program*: a :py:class:`habitat.main.Program` object

        All modules listed in config["loadables"] will be loaded using
        :py:meth:`load`.
        """

        self.libraries = {}

        for loadable in config["loadables"]:
            self.load(loadable["class"], loadable["name"])

    def load(self, module, shorthand):
        """loads *module* as a library and assigns it to *shorthand*"""

        module = dynamicloader.load(module)
        self.libraries[shorthand] = module

    def run(self, name, config, data):
        """
        Runs *name* loadable using *config* and *data* (though *config* is only
        passed to *name* if *name* takes two arguments).

        *name*: The loaded function to use.

        *config*: The config dict to provide to the function

        *data*: The data to parse.
        """

        name_parts = name.split('.')
        if len(name_parts) != 2:
            raise ValueError("Invalid function library name")

        library = self.libraries[name_parts[0]]

        if name_parts[1] not in library.__all__:
            raise ValueError("Invalid function name")

        func = getattr(library, name_parts[1])

        if dynamicloader.hasnumargs(func, 1):
            return func(data)
        else:
            return func(config, data)

    _repr_format = "<habitat.LoadableManager: {l} libraries loaded>"

    def __repr__(self):
        return self._repr_format.format(l=len(self.libraries))
