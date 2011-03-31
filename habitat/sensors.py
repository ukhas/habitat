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
modules, which must have an __all__ list so that ``from x import *``
can be used.

These all libraries listed in the Sensor Manager's configuration are loaded
upon initialisation.
"""

from habitat.utils import dynamicloader

__all__ = ["SensorManager"]

base_functions = {
    "ascii_int": lambda config, data: int(data),
    "ascii_float": lambda config, data: float(data),
    "string": lambda config, data: str(data)
}

class SensorManager:
    """The main Sensor Manager class"""

    def __init__(self, program):
        """
        Initalises the sensor manager

        All modules listed in the config document for the sensor manager
        will be loaded using :py:meth:`load`.
        """

        self.functions = base_functions.copy()

        for module in program.db["sensor_manager_config"]["libraries"]:
            self.load(module)

    def load(self, module):
        """loads all functions in the __all__ list of module **module**"""

        module = dynamicloader.load(module)
        dynamicloader.expecthasattr(module, "__all__")

        for func_name in module.__all__:
            if func_name in self.functions:
                raise ValueError("Attempted to {f} twice".format(f=func_name))

            self.functions[func_name] = getattr(module, func_name)

    def parse(self, name, config, data):
        """
        parses the **data** provided

        **name**: The sensor function to use.

        **config**: The config dict to provide to the sensor function

        **data**: The data to parse.
        """

        if name not in self.functions:
            raise ValueError("{f} not in self.functions".format(f=name))

        return self.functions[name](config, data)

    _repr_format = "<habitat.sensors.SensorManager: {num} functions loaded>"

    def __repr__(self):
        return self._repr_format.format(num=len(self.functions))
