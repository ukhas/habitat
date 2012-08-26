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

import copy

from nose.tools import assert_raises
from couch_named_python import UnauthorizedError, ForbiddenError

from ...views import utils

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

test_format_schema = {
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
                    "format": "replace-me"
                }
            }
        }
    }
}

def test_validate_datetimes():
    schema = copy.deepcopy(test_format_schema)
    schema["items"]["additionalProperties"]["properties"]["two"]["format"] = \
            "date-time"

    good = [{1: {"one": "a@b", "two": "2012-04-02T12:09:42Z"},
             2: {"one": "c@d", "two": "2012-04-02T12:10:04+01:00"}},
            {1: {"one": "e@f", "two": "2012-04-02T12:09:42+01:00"},
             2: {"one": "g@h", "two": "2012-04-02T12:10:04+01:00"}}]

    bad =  [{1: {"one": "a@b", "two": "2012-04-02T12:09:42Z"},
             2: {"one": "c@d", "two": "2012-04-02T12:10:04+01:00"}},
            {1: {"one": "e@f", "two": "2012-04-02T12:09:42+01:00"},
             2: {"one": "g@h", "two": "2012-04-02T12:10:04"}}] #NB this line

    utils.validate_doc(good, schema)
    assert_raises(ForbiddenError, utils.validate_doc, bad, schema)

def test_validate_base64():
    schema = copy.deepcopy(test_format_schema)
    schema["items"]["additionalProperties"]["properties"]["two"]["format"] = \
            "base64"

    good = [{1: {"one": "a@b", "two": "aGVsbG8gd29ybGQ="},
             2: {"one": "c@d", "two": "RGFuaWVsIHdhcyBoZXJl"}},
            {1: {"one": "e@f", "two": "U2hpYmJvbGVldA=="},
             2: {"one": "g@h", "two": ""}}]
    utils.validate_doc(good, schema)

    for bad_b64 in ["asd", "U2hpYm\n\n\n\t\t\tJvbGVldA==", "aGVsbG8gd29ybGQ"]:
        bad = copy.deepcopy(good)
        bad[1][2]["two"] = bad_b64
        assert_raises(ForbiddenError, utils.validate_doc, bad, schema)

def test_validate_times():
    schema = copy.deepcopy(test_format_schema)
    schema["items"]["additionalProperties"]["properties"]["two"]["format"] = \
            "time"

    good = [{1: {"one": "a@b", "two": "20:09:00"},
             2: {"one": "c@d", "two": "12:10:04"}},
            {1: {"one": "e@f", "two": "00:09:42"},
             2: {"one": "g@h", "two": "23:59:60"}}]
    utils.validate_doc(good, schema)

    for bad_time in ["12:0:04", "120004", "12:23", "asdf", ""]:
        bad =  [{1: {"one": "a@b", "two": "12:09:42"},
                 2: {"one": "c@d", "two": "12:10:04"}},
                {1: {"one": "e@f", "two": "12:09:42"},
                 2: {"one": "g@h", "two": bad_time}}]
        assert_raises(ForbiddenError, utils.validate_doc, bad, schema)

def test_only_validates():
    @utils.only_validates("a_document_type")
    def my_validate_func(new, old, userctx, secobj):
        """my docstring"""
        assert userctx == {'roles': ['test role']}
        assert secobj['secobj'] == True
        assert new['type'] == "a_document_type"
        if "check_old" in new:
            assert old == {"type": "a_document_type", "raise": False}
        elif new["raise"]:
            raise ForbiddenError("raising")

    assert my_validate_func.__doc__ == "my docstring"
    assert my_validate_func.__name__ == "my_validate_func"

    doc = {"type": "a_document_type", "raise": False}
    bad = {"type": "a_document_type", "raise": True}
    check_old = {"type": "a_document_type", "check_old": True}
    type_change = {"type": "an_unrelated_type", "blah": 123}
    deleted = {"_deleted": True}
    no_type = {"some_data": [1, 2, '4']}

    # should validate, new doc, new doc with error, changed doc with error
    my_validate_func(doc, {}, {'roles': ['test role']}, {'secobj': True})
    assert_raises(ForbiddenError, my_validate_func, bad, {},
            {'roles': ['test role']}, {'secobj': True})
    assert_raises(ForbiddenError, my_validate_func, bad, doc,
            {'roles': ['test role']}, {'secobj': True})

    # check passing all arguments
    my_validate_func(check_old, doc,
            {'roles': ['test role']}, {'secobj': True})

    # both type change directions:
    assert_raises(ForbiddenError, my_validate_func,
            doc, type_change, {'roles': []}, {})
    assert_raises(ForbiddenError, my_validate_func,
            type_change, doc, {'roles': []}, {})

    # deleted doc
    my_validate_func(deleted, doc, {'roles': []}, {})

    # docs of other types
    my_validate_func(type_change, {}, {'roles': []}, {})
    my_validate_func(type_change, type_change, {'roles': []}, {})
    my_validate_func(deleted, type_change, {'roles': []}, {})

    my_validate_func(no_type, {}, {'roles': []}, {})
