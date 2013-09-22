# Copyright 2010, 2011 (C) Daniel Richman, Adam Greig
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
The top level habitat package.

habitat is an application for tracking the flight path of high altitude
balloons, relying on a network of users with radios sending in received
telemetry strings which are parsed into position information and displayed
on maps.

See http://habitat.habhub.org for more information.

.. autosummary::
    :toctree: habitat

    habitat.parser
    habitat.parser_daemon
    habitat.parser_modules
    habitat.loadable_manager
    habitat.sensors
    habitat.filters
    habitat.uploader
    habitat.utils
    habitat.views
"""

__name__ = "habitat"
__version__ = "0.2.0"
__authors__ = "Adam Greig, Daniel Richman"
__short_copyright__ = "2010-2012 " + __authors__
__copyright__ = "Copyright " + __short_copyright__

from . import filters
from . import parser
from . import parser_daemon
from . import parser_modules
from . import loadable_manager
from . import sensors
from . import uploader
from . import utils
from . import views
