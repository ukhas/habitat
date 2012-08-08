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

from nose.tools import assert_raises
from couch_named_python import UnauthorizedError, ForbiddenError

from ...views import utils

def test_rfc3339():
    s = "1996-12-19T16:39:57-08:00"
    d1 = utils.rfc3339_to_datetime(s)
    assert d1.isoformat() == "1996-12-19T16:39:57-08:00"
    d2 = utils.rfc3339_to_utc_datetime(s)
    assert d2.isoformat() == "1996-12-20T00:39:57+00:00"
    t = utils.rfc3339_to_timestamp(s)
    assert t == 851042397
    t = utils.datetime_to_timestamp(d1)
    assert t == 851042397
    t = utils.datetime_to_timestamp(d2)
    assert t == 851042397
    
    assert utils.validate_rfc3339("1234") is False
    assert utils.validate_rfc3339("20000102T030405Z") is True
    assert utils.validate_rfc3339("2000-01-02T03:04:05+0100") is True

def test_must_be_admin():
    nonadmin = {'roles': ['not an admin']}
    noroles = {'noroles': True}
    oddroles = {'roles': 12}
    admin = {'roles': ['_admin']}
    alsoadmin = {'roles': ['lowly', '_admin']}

    assert_raises(UnauthorizedError, utils.must_be_admin, nonadmin)
    assert_raises(UnauthorizedError, utils.must_be_admin, noroles)
    assert_raises(UnauthorizedError, utils.must_be_admin, oddroles)
    
    utils.must_be_admin(admin)
    utils.must_be_admin(alsoadmin)

def test_validate_doc():
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
    assert_raises(ForbiddenError, utils.validate_doc, bad, schema)
    assert_raises(ForbiddenError, utils.validate_doc, badopt, schema)
    assert_raises(ForbiddenError, utils.validate_doc, multibad, schema)
    assert_raises(ForbiddenError, utils.validate_doc, extras, schema)

def test_validate_datetimes():
    schema = {
        "type": "array",
        "additionalProperties": False,
        "items": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "one": {
                        "type": "string",
                        "format": "email"
                    }, "two": {
                        "type": "string",
                        "format": "date-time"
                    }
                }
            }
        }
    }

    good = [{1: {"one": "a@b", "two": "20120402T120942Z"},
             2: {"one": "c@d", "two": "2012-04-02T12:10:04+0100"}},
            {1: {"one": "e@f", "two": "20120402T120942+01:00"},
             2: {"one": "g@h", "two": "20120402T12:10:04+01:00"}}]

    bad =  [{1: {"one": "a@b", "two": "20120402T120942Z"},
             2: {"one": "c@d", "two": "2012-04-02T12:10:04+0100"}},
            {1: {"one": "e@f", "two": "20120402T120942+01:00"},
             2: {"one": "g@h", "two": "20120402T12:10:04"}}] #NB this line

    utils.validate_doc(good, schema)
    assert_raises(ForbiddenError, utils.validate_doc, bad, schema)

def test_only_validates():
    @utils.only_validates("a_document_type")
    def my_validate_func(new, old, userctx, secobj):
        assert userctx == {'roles': ['test role']}
        assert secobj['secobj'] == True
        if "check_old" in new:
            assert old == {"type": "a_document_type", "raise": False}
        elif new["raise"]:
            raise ForbiddenError("raising")

    doc = {"type": "a_document_type", "raise": False}
    bad = {"type": "a_document_type", "raise": True}
    check_old = {"type": "a_document_type", "check_old": True}
    type_change = {"type": "an_unrelated_type", "blah": 123}
    deleted = {"_deleted": True}
    no_type = {"some_data": [1, 2, '4']}

    assert_raises(ForbiddenError, my_validate_func,
            doc, type_change, {'roles': []}, {})
    assert_raises(ForbiddenError, my_validate_func,
            type_change, doc, {'roles': []}, {})

    my_validate_func(deleted, doc, {'roles': []}, {})
    my_validate_func(type_change, {}, {'roles': []}, {})
    my_validate_func(no_type, {}, {'roles': []}, {})

    my_validate_func(doc, {}, {'roles': ['test role']}, {'secobj': True})

    assert_raises(ForbiddenError, my_validate_func, bad, doc,
            {'roles': ['test role']}, {'secobj': True})
    assert_raises(ForbiddenError, my_validate_func, bad, {},
            {'roles': ['test role']}, {'secobj': True})

    my_validate_func(check_old, doc,
            {'roles': ['test role']}, {'secobj': True})
