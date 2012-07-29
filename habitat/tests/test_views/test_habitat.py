# Copyright 2012 (C) Adam Greig
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
Tests general habitat views and functions.
"""

from ...views import habitat
from couch_named_python import ForbiddenError, UnauthorizedError

from nose.tools import assert_raises

def test_only_admins_may_delete():
    assert_raises(UnauthorizedError, habitat.validate,
        {'_deleted': True}, {'whatever': 'whatever'}, {'roles': []}, {})
    habitat.validate(
        {'_deleted': True}, {'whatever': 'whatever'}, {'roles': ['_admin']},
        {})

def test_only_valid_types():
    assert_raises(ForbiddenError, habitat.validate,
        {}, {}, {'roles': []}, {})
    assert_raises(ForbiddenError, habitat.validate,
        {'type': 'mysterious'}, {'type': 'mysterious'}, {'roles': []}, {})
    habitat.validate(
        {'type': 'flight'}, {'type': 'flight'}, {'roles': []}, {})

def test_cannot_change_type():
    assert_raises(ForbiddenError, habitat.validate,
        {'type': 'flight'}, {'type': 'listener_information'}, {'roles': []},
        {})
