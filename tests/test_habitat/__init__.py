# Copyright 2010 (C) Daniel Richman
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
Tests for the python backend of habitat. For use with nosetests.
"""

__all__ = ["scratch_dir", "scratch_path"]

import os
import errno

assert __name__ == "test_habitat"

test_habitat_dir = os.path.dirname(os.path.abspath(__file__))
scratch_dir = os.path.join(test_habitat_dir, "scratch")
scratch_path = ["test_habitat", "scratch"]

# Create scratch dir
try:
    os.mkdir(scratch_dir)
except OSError, e:
    if e.errno != errno.EEXIST:
        raise

# Touch __init__.py
open(os.path.join(scratch_dir, "__init__.py"), 'w').close()
