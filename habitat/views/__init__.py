# Copyright 2011, 2012 (C) Adam Greig
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
View functions for CouchDB with the couch-named-python view server, used by
habitat related design documents.

.. autosummary::
    :toctree: habitat

    habitat.views.flight
    habitat.views.listener_information
    habitat.views.listener_telemetry
    habitat.views.payload_telemetry
    habitat.views.payload_configuration
    habitat.views.habitat
    habitat.views.parser
    habitat.views.utils
"""

from . import flight
from . import listener_information
from . import listener_telemetry
from . import payload_telemetry
from . import payload_configuration
from . import habitat
from . import parser
from . import utils
