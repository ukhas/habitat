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
Tests the Dynamic Loader module, ../dynamicloader.py
""" 

import sys
import time
import os
import functools
import datetime
from utils import dynamicloader
from nose.tools import raises
from utils.tests import dynamicloadme

unimp_name = "utils.tests.dynamicloadunimp"

class TestLoad:
    """dynamicloader.load():"""

    def test_load_gets_correct_object(self):
        # This tests calls of the format load(MyClass) and
        # load("packagea.packageb.aclass")
        for i in [dynamicloadme.AClass, dynamicloadme.BClass,
                  dynamicloadme.AFunction, dynamicloadme.BFunction]:
            assert dynamicloader.load(i) == i

            # if nosetests is running --with-isolation, this is required:
            realitem = getattr(sys.modules[i.__module__], i.__name__)
            assert dynamicloader.load(i.__fullname__) == realitem

    def chcek_load_gets_correct_object(self, loadable, target):
        assert dynamicloader.load(loadable) == target

    def test_can_load_module(self):
        # Test a call in the form load("datetime")
        assert dynamicloader.load("datetime") == datetime

    def test_can_load_notyetimported_module(self):
        """can load a module that has not yet been imported once"""
        # I picked something that probably won't have been loaded yet
        assert "httplib2" not in sys.modules
        # Check to see httplib2.Authentication exists (if it does we've
        # probably got the right module)
        assert dynamicloader.load("httplib2").Authentication

    def test_can_load_notyetimported_function(self):
        """can load an object from a module that has not been imported yet"""
        f = dynamicloader.load(unimp_name + ".AFunction")
        assert f() == 412314

    def test_can_use_loaded_class(self):
        # CClass is subclass of AClass; CClass is callable
        a = dynamicloader.load(unimp_name + ".AClass")
        c = dynamicloader.load(unimp_name + ".CClass")
        assert issubclass(c, a)
        oa = a()
        oc = c()
        assert isinstance(oa, a)
        assert isinstance(oc, c)
        assert isinstance(oc, a)
        assert oc(None, None) == None

    def test_can_load_generator(self):
        a = dynamicloader.load(unimp_name + ".GFunction")
        b = dynamicloader.load(dynamicloadme.GFunction)
        t = ["Hello", "World"]
        ta = []
        tb = []
        for i in a(): ta.append(i)
        for i in b(): tb.append(i)
        assert ta == tb == t

    @raises(TypeError)
    def test_load_rejects_garbage_target(self):
        """load rejects a target that is neither a function nor a class"""
        dynamicloader.load(dynamicloadme.__name__ + ".avariable")

    @raises(TypeError)
    def test_load_rejects_garbage_argument(self):
        dynamicloader.load(1234)

    @raises(ImportError)
    def test_load_rejects_nonexistent_module(self):
        dynamicloader.load("nonexistant_module_asdf.apath.aclass")

    @raises(AttributeError)
    def test_load_rejects_nonexistent_class(self):
        dynamicloader.load(dynamicloadme.__name__ + ".nothingasdf")

    @raises(ImportError)
    def test_load_does_not_recurse_into_classes(self):
        dynamicloader.load(dynamicloadme.__name__ + ".AClass.anattr")

    @raises(TypeError)
    def test_refuses_to_load_garbage_loadable(self):
        dynamicloader.load(1234)

    @raises(ValueError)
    def test_refuses_to_load_empty_str(self):
        dynamicloader.load("")

    def test_refuses_to_load_str_with_empty_components(self):
        for i in ["asdf.", ".", "asdf..asdf"]:
            yield self.check_refuses_to_load_str_with_empty_components, i

    @raises(ValueError)
    def check_refuses_to_load_str_with_empty_components(self, name):
        dynamicloader.load(name)

    def test_reload_module_class(self):
        modulecode_1 = "class asdf:\n    def __init__(self): self.test = 1\n"
        modulecode_2 = "class asdf:\n    def __init__(self): self.test = 2\n"
        self.check_reload_module("reloadablea", modulecode_1, modulecode_2)

    def test_reload_module_function(self):
        modulecode_1 = "def asdf():\n    asdf.test = 1\n    return asdf\n"
        modulecode_2 = "def asdf():\n    asdf.test = 2\n    return asdf\n"
        self.check_reload_module("reloadableb", modulecode_1, modulecode_2)

    def check_reload_module(self, modname, modulecode_1, modulecode_2):
        components = __name__.split(".")
        components[-1:] = [modname, 'asdf']

        loadable = ".".join(components)
        module = ".".join(components[:-1])
        assert module not in sys.modules

        self.write_reloadable_module(modname, modulecode_1)

        asdf_1a = dynamicloader.load(loadable)
        asdf_1a_object = asdf_1a()
        assert asdf_1a_object.test == 1

        self.write_reloadable_module(modname, modulecode_2)

        # Should not cause a reload, should just re-use sys.moudles[loadable]
        asdf_1b = dynamicloader.load(loadable)
        assert asdf_1b == asdf_1a
        asdf_1b_object = asdf_1b()
        assert asdf_1b_object.test == asdf_1a_object.test == 1

        # This time we want a reload
        asdf_2a = dynamicloader.load(loadable, force_reload=True)
        assert asdf_2a != asdf_1b
        asdf_2a_object = asdf_2a()
        assert asdf_2a_object.test == 2

        # It should stay reloaded, even without force_reload
        asdf_2b = dynamicloader.load(loadable)
        assert asdf_2b == asdf_2a
        asdf_2b_object = asdf_2a()
        assert asdf_2b_object.test == asdf_2a_object.test == 2

        # asdf_1b should still be the old module, though in typical use it
        # would have been discarded by now
        asdf_1b_object = asdf_1b()
        assert asdf_1b_object.test == 1

        self.write_reloadable_module(modname, modulecode_1)

        # Finally, we should also be able to reload like this:
        asdf_1c = dynamicloader.load(asdf_1b)
        assert asdf_1c != asdf_2a
        asdf_1c_object = asdf_1c()
        assert asdf_1c_object.test == 1

    def write_reloadable_module(self, modname, code):
        filename = os.path.join(os.path.dirname(__file__), modname + ".py")

        # Even when the builtin reload is called python will read from the
        # pyc file if the embedded mtime matches that of the py file. That's
        # typically going to be fine, however, if you load, modify, reload
        # within one second then the updated module won't be read.
        # We won't be reloading that fast, but the test will. So hack the 
        # mtime two seconds into the future every time.

        try:
            newtime = os.path.getmtime(filename) + 2
        except OSError:
            newtime = int(time.time())

        with open(filename, 'w') as f:
            f.write(code)

        os.utime(filename, (newtime, newtime))

    def test_fullname(self):
        lm = dynamicloadme
        lmn = dynamicloadme.__name__
        assert dynamicloader.fullname(lm.AClass) == lmn + ".AClass"
        assert dynamicloader.fullname(lm.AFunction) == lmn + ".AFunction"
        assert dynamicloader.fullname(lm) == lmn
        assert dynamicloader.fullname("astring") == "astring"

    @raises(TypeError)
    def test_fullname_rejects_garbage(self):
        dynamicloader.fullname(1234)

class TestInspectors:
    def test_isclass(self):
        fn = dynamicloader.isclass
        ex = dynamicloader.expectisclass
        self.check_function_success(fn, ex, dynamicloadme.AClass)
        self.check_function_failure(fn, ex, dynamicloadme.AFunction, TypeError)
        self.check_function_failure(fn, ex, "asdf", TypeError)

    def test_issubclass(self):
        fn = dynamicloader.issubclass
        ex = dynamicloader.expectissubclass
        self.check_value_function(fn, ex, dynamicloadme.CClass,
                                  dynamicloadme.Parent2, dynamicloadme.BClass,
                                  ValueError)

    def test_isfunction(self):
        """isfunction, isgeneratorfunction, isstandardfunction, iscallable"""
        fnn = dynamicloader.isfunction
        exn = dynamicloader.expectisfunction
        fns = dynamicloader.isstandardfunction
        exs = dynamicloader.expectisstandardfunction
        fng = dynamicloader.isgeneratorfunction
        exg = dynamicloader.expectisgeneratorfunction
        fni = dynamicloader.iscallable
        exi = dynamicloader.expectiscallable

        afn = dynamicloadme.AFunction
        gfn = dynamicloadme.GFunction
        acl = dynamicloadme.AClass
        ccl = dynamicloadme.CClass
        dcl = dynamicloadme.DClass
        
        self.check_function_success(fnn, exn, afn)
        self.check_function_success(fnn, exn, gfn)
        self.check_function_failure(fnn, exn, acl, TypeError)
        self.check_function_failure(fnn, exn, "asdf", TypeError)
        self.check_function_success(fns, exs, afn)
        self.check_function_failure(fns, exs, gfn, TypeError)
        self.check_function_failure(fns, exs, acl, TypeError)
        self.check_function_failure(fns, exs, "asdf", TypeError)
        self.check_function_failure(fng, exg, afn, TypeError)
        self.check_function_success(fng, exg, gfn)
        self.check_function_failure(fng, exg, acl, TypeError)
        self.check_function_failure(fng, exg, "asdf", TypeError)
        self.check_function_success(fni, exi, afn)
        self.check_function_success(fni, exi, gfn)
        self.check_function_success(fni, exi, ccl)
        self.check_function_success(fni, exi, dcl)
        self.check_function_failure(fni, exi, acl, ValueError)
        self.check_function_failure(fni, exi, "asdf", ValueError)

    def test_hasnumargs(self):
        for func, val in [ (dynamicloadme.AFunction, 0),
                           (dynamicloadme.BFunction, 3),
                           (dynamicloadme.CClass, 2),
                           (dynamicloadme.DClass, 2),
                           (dynamicloadme.BClass.a_method, 0) ]:
            
            self.check_value_function(dynamicloader.hasnumargs, 
                                      dynamicloader.expecthasnumargs,
                                      func, val, val + 1, ValueError)

    def test_hasstuff(self):
        """hasmethod, hasattr"""
        fna = dynamicloader.hasattr
        exa = dynamicloader.expecthasattr
        fnm = dynamicloader.hasmethod
        exm = dynamicloader.expecthasmethod
        acl = dynamicloadme.AClass
        bcl = dynamicloadme.BClass
        ccl = dynamicloadme.CClass
        mod = dynamicloadme

        self.check_value_function(fna, exa, acl, "anattr", "asdf", ValueError)
        self.check_value_function(fna, exa, ccl, "anattr", "asdf", ValueError)
        self.check_value_function(fna, exa, mod, "avariable", "z", ValueError)
        self.check_value_function(fna, exa, mod, "AFunction", "x", ValueError)

        self.check_value_function(fnm, exm, mod, "AFunction", "avariable",
                                  ValueError)
        self.check_value_function(fnm, exm, ccl, "__call__", "anattr",
                                  ValueError)
        self.check_value_function(fnm, exm, bcl, "a_method", "a", ValueError)

    def check_function_success(self, func, expectfunc, argument):
        assert func(argument) == True
        expectfunc(argument)

    def check_function_failure(self, func, expectfunc, argument, error):
        assert func(argument) == False
        try:
            expectfunc(argument)
        except error:
            return
        raise AssertionError

    def check_value_function(self, func, expectfunc, argument, value,
                             wrongvalue, error):
        assert func(argument, value) == True
        expectfunc(argument, value)
        assert func(argument, wrongvalue) == False
        try:
            expectfunc(argument, wrongvalue)
        except error:
            return
        raise AssertionError
