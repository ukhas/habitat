# Copyright 2011 (C) Daniel Richman
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
``habitat.sensors``: the sensor-function manager

The sensor function manager provides a collection of sensor functions,
which are used by parser modules to turn extracted fields into useful data.

Sensor functions are grouped into "libraries", which are python
modules. When loaded, these modules are assigned a shorthand. For example,
functions in ``habitat.sensors.stdtelem`` are available simply as
``stdtelem.func``. The shorthand assigned is specified in the config document.

These all libraries listed in the Sensor Manager's configuration are loaded
upon initialisation.

Sensor Functions
================

The sensor_manager provides the *base* library built in; it includes

 * ascii_int
 * ascii_float
 * string

Other libraries are available with habitat. See :py:mod:`sensors`

A sensor function takes two arguments, *config* and *data*. It
can return a string, list, dict, int, float, or any other python
object that can be stored in a couchdb database.

*config* is a dict of options. It is passed to the function from
:py:meth:`SensorManager.parse`

*data* is the string to parse.
"""

from habitat.utils import dynamicloader
from habitat.sensors import base

__all__ = ["SensorManager"]

class SensorManager:
    """The main Sensor Manager class"""

    def __init__(self, program):
        """
        *program*: a :py:class:`habitat.main.Program` object

        All modules listed in the config document for the sensor manager
        will be loaded using :py:meth:`load`.
        """

        self.libraries = {"base": base}

        loadlist = program.db["sensor_manager_config"]["libraries"].items()
        for (shorthand, module) in loadlist:
            self.load(module, shorthand)

    def load(self, module, shorthand):
        """loads *module* as a library and assigns it to *shorthand*"""

        module = dynamicloader.load(module)
        self.libraries[shorthand] = module

    def parse(self, name, config, data):
        """
        parses the *data* provided

        *name*: The sensor function to use.

        *config*: The config dict to provide to the sensor function

        *data*: The data to parse.
        """

        name_parts = name.split('.')
        if len(name_parts) != 2:
            raise ValueError("Invalid sensor name")

        library = self.libraries[name_parts[0]]

        if name_parts[1] not in library.__all__:
            raise ValueError("Invalid sensor name")

        func = getattr(library, name_parts[1])

        return func(config, data)

    _repr_format = "<habitat.sensors.SensorManager: {l} libraries loaded>"

    def __repr__(self):
        return self._repr_format.format(l=len(self.libraries))
