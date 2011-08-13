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
habitat is a web application for tracking the flight path of high altitude
balloons, relying on a network of users with radios sending in received
telemetry strings which are parsed into position information and displayed
on maps.

.. autosummary::
    :toctree: habitat

    habitat.parser
    habitat.uploader
    habitat.main
    habitat.utils
"""

__name__ = "habitat"
__version__ = "0.0.1"
__authors__ = "Adam Greig, Daniel Richman"
__short_copyright__ = "2010 " + __authors__
__copyright__ = "Copyright " + __short_copyright__

__all__ = ["parser", "uploader", "main", "utils"]

from . import main
