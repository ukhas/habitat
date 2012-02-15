# Copyright 2011 (C) Adam Greig
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
Unit tests for the view function utilities
"""

import mox

from nose.tools import assert_raises
from couch_named_python import Unauthorized, Forbidden

from ...views import utils

class TestViewUtils(object):
    def test_must_be_admin(self):
        nonadmin = {'roles': ['not an admin']}
        noroles = {'noroles': True}
        oddroles = {'roles': 12}
        admin = {'roles': ['admin']}
        alsoadmin = {'roles': ['lowly', 'admin']}

        assert_raises(Unauthorized, utils.must_be_admin, nonadmin)
        assert_raises(Unauthorized, utils.must_be_admin, noroles)
        assert_raises(Unauthorized, utils.must_be_admin, oddroles)
        
        utils.must_be_admin(admin)
        utils.must_be_admin(alsoadmin)

    def test_validate_doc(self):
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": True,
            "properties": {
                "test": {
                    "type": "string",
                    "required": True
                },
                "opt": {
                    "type": "number"
                }
            }
        }

        ok = {"test": "hello"}
        wopt = {"test": "hi", "opt": 123}
        bad = {"not test": "hello"}
        badopt = {"test": "hey", "opt": "oh no a string"}
        multibad = {"not test": "hello", "opt": "not a number"}
        extras = {"test": "heya", "opt": 123, "extra": "not allowed!"}

        utils.validate_doc(ok, schema)
        utils.validate_doc(wopt, schema)
        assert_raises(Forbidden, utils.validate_doc, bad, schema)
        assert_raises(Forbidden, utils.validate_doc, badopt, schema)
        assert_raises(Forbidden, utils.validate_doc, multibad, schema)
        assert_raises(Forbidden, utils.validate_doc, extras, schema)
