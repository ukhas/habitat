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
import os
import time
import datetime
import tempfile
import shutil

from nose.tools import raises

from ....utils import dynamicloader

from . import example_module
from .example_module import AClass

unimp_a_name = "unimp.dynamicloadunimp_a"
unimp_b_name = "unimp.dynamicloadunimp_b"


class ReloadableModuleWriter:
    def __init__(self, tempdir, modname, itemname):
        components = [modname, itemname]

        self.loadable = ".".join(components)
        self.fullmodname = ".".join(components[:-1])

        self.filename = os.path.join(tempdir, modname + ".py")

    # Even when the builtin reload is called python will read from the
    # pyc file if the embedded mtime matches that of the py file. That's
    # typically going to be fine, however, if you load, modify, reload
    # within one second then the updated module won't be read.
    # We won't be reloading that fast, but the test will. So hack the
    # mtime two seconds into the future every time.

    def is_loaded(self):
        if self.fullmodname in sys.modules:
            raise ValueError("modname {0} is already in sys.modules".format(
                                 self.fullmodname))

    def write_code(self, code):
        try:
            newtime = os.path.getmtime(self.filename) + 2
        except OSError:
            newtime = int(time.time())

        with open(self.filename, 'w') as f:
            f.write(code)

        os.utime(self.filename, (newtime, newtime))


class TestLoad:
    """dynamicloader.load():"""

    def setup(self):
        """setup a tempdir for messing about in (e.g. reloadablemodulewriter);
        also use it to copy example_module.py into two other names, then put
        this folder on the path so it can be imported from."""
        self.tempdir = tempfile.mkdtemp()
        unimp_dir = os.path.join(self.tempdir, 'unimp')
        os.mkdir(unimp_dir)
        unimp_a = os.path.join(unimp_dir, 'dynamicloadunimp_a.py')
        unimp_b = os.path.join(unimp_dir, 'dynamicloadunimp_b.py')
        this_path = os.path.abspath(os.path.dirname(__file__))
        file_path = os.path.join(this_path, 'example_module.py')
        shutil.copyfile(file_path, unimp_a)
        shutil.copyfile(file_path, unimp_b)
        open(os.path.join(unimp_dir, '__init__.py'), 'w').close()
        sys.path.insert(0, self.tempdir)

    def teardown(self):
        """clean up the temp folder and path entries"""
        sys.path.remove(self.tempdir)
        if 'unimp' in sys.modules:
            del sys.modules['unimp']
        shutil.rmtree(self.tempdir)

    def test_load_gets_correct_object(self):
        # This tests calls of the format load(MyClass) and
        # load("packagea.packageb.aclass")
        for i in [example_module.AClass, example_module.BClass,
                  example_module.AFunction, example_module.BFunction]:
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
        assert "anydbm" not in sys.modules
        # Check to see httplib2.Authentication exists (if it does we've
        # probably got the right module)
        assert dynamicloader.load("anydbm").error

    def test_doublereload(self):
        """force-reloading a not yet been imported module causes one load"""
        # TODO: implementation specific use of __builtins__.
        assert dynamicloader.__builtins__
        assert "whichdb" not in sys.modules

        # Wrap reload to work out how many times it was called.
        def new_reload(*args, **kwargs):
            new_reload.hits += 1
            return new_reload.old(*args, **kwargs)
        new_reload.hits = 0
        new_reload.old = dynamicloader.__builtins__["reload"]

        dynamicloader.__builtins__["reload"] = new_reload

        assert dynamicloader.load("whichdb", force_reload=True).whichdb
        assert new_reload.hits == 0

        assert dynamicloader.load("whichdb", force_reload=True).whichdb
        assert new_reload.hits == 1

        dynamicloader.__builtins__["reload"] = new_reload.old

        assert dynamicloader.load("whichdb", force_reload=True).whichdb
        assert new_reload.hits == 1  # no change; no longer wrapped

    def test_can_load_notyetimported_function(self):
        """can load an object from a module that has not been imported yet"""
        f = dynamicloader.load(unimp_b_name + ".AFunction")
        assert f() == 412314

    def test_can_load_module_not_imported_by_parent_module(self):
        dynamicloader.load(unimp_a_name)

    def test_can_use_loaded_class(self):
        # CClass is subclass of AClass; CClass is callable
        a = dynamicloader.load(example_module.AClass.__fullname__)
        c = dynamicloader.load(example_module.CClass.__fullname__)
        assert issubclass(c, a)
        oa = a()
        oc = c()
        assert isinstance(oa, a)
        assert isinstance(oc, c)
        assert isinstance(oc, a)
        assert oc(None, None) == None

    def test_can_load_generator(self):
        a = dynamicloader.load(example_module.GFunction.__fullname__)
        b = dynamicloader.load(example_module.GFunction)
        t = ["Hello", "World"]
        ta = [i for i in a()]
        tb = [i for i in b()]
        assert ta == tb == t

    @raises(TypeError)
    def test_load_rejects_garbage_target(self):
        """load rejects a target that is neither a function nor a class"""
        dynamicloader.load(example_module.__name__ + ".avariable")

    @raises(TypeError)
    def test_load_rejects_garbage_argument(self):
        dynamicloader.load(1234)

    @raises(ImportError)
    def test_load_rejects_nonexistent_module(self):
        dynamicloader.load("nonexistant_module_asdf.apath.aclass")

    @raises(AttributeError)
    def test_load_rejects_nonexistent_class(self):
        dynamicloader.load(example_module.__name__ + ".nothingasdf")

    @raises(ImportError)
    def test_load_does_not_recurse_into_classes(self):
        dynamicloader.load(example_module.__name__ + ".AClass.afunc")

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
        rmod = ReloadableModuleWriter(self.tempdir, modname, 'asdf')
        assert not rmod.is_loaded()

        roundabout_mod = ReloadableModuleWriter(self.tempdir,
            modname + "_alias", "asdf")
        assert not roundabout_mod.is_loaded()
        roundabout_mod.write_code("from {0} import asdf".format(modname))

        rmod.write_code(modulecode_1)

        asdf_1a = dynamicloader.load(rmod.loadable)
        asdf_1a_object = asdf_1a()
        assert asdf_1a_object.test == 1

        rmod.write_code(modulecode_2)

        # Should not cause a reload, should just re-use sys.moudles[loadable]
        asdf_1b = dynamicloader.load(rmod.loadable)
        assert asdf_1b == asdf_1a
        asdf_1b_object = asdf_1b()
        assert asdf_1b_object.test == asdf_1a_object.test == 1

        # This time we want a reload
        asdf_2a = dynamicloader.load(rmod.loadable, force_reload=True)
        assert asdf_2a != asdf_1b
        asdf_2a_object = asdf_2a()
        assert asdf_2a_object.test == 2

        # It should stay reloaded, even without force_reload
        asdf_2b = dynamicloader.load(rmod.loadable)
        assert asdf_2b == asdf_2a
        asdf_2b_object = asdf_2a()
        assert asdf_2b_object.test == asdf_2a_object.test == 2

        # asdf_1b should still be the old module, though in typical use it
        # would have been discarded by now
        asdf_1b_object = asdf_1b()
        assert asdf_1b_object.test == 1

        rmod.write_code(modulecode_1)

        # We should also be able to reload like this:
        asdf_1c = dynamicloader.load(asdf_2b, force_reload=True)
        assert asdf_1c != asdf_2a
        asdf_1c_object = asdf_1c()
        assert asdf_1c_object.test == 1

        rmod.write_code(modulecode_2)

        # And finally like this:
        asdf_2c = dynamicloader.load(roundabout_mod.loadable,
                                     force_reload=True)
        assert asdf_2c != asdf_1c
        asdf_2c_object = asdf_2c()
        assert asdf_2c_object.test == 2


class TestFullname:
    def test_fullname(self):
        lm = example_module
        lmn = example_module.__name__

        assert dynamicloader.fullname(lm.AClass) == lmn + ".AClass"
        assert dynamicloader.fullname(lm.AFunction) == lmn + ".AFunction"
        assert dynamicloader.fullname(lm) == lmn

        # Fullname can be passed a string just like load() can
        assert dynamicloader.fullname(lmn) == lmn
        assert dynamicloader.fullname(lmn + ".AClass") == lmn + ".AClass"

        # Because we import example_module into this module, we *could*
        # import AClass by this route (see above). fullname must tolerate this
        acwn = __name__ + ".AClass"
        assert dynamicloader.fullname(acwn) == lmn + ".AClass"

    @raises(TypeError)
    def test_fullname_rejects_garbage(self):
        dynamicloader.fullname(1234)


class TestInspectors:
    def test_isclass(self):
        fn = dynamicloader.isclass
        ex = dynamicloader.expectisclass
        self.check_function_success(fn, ex, example_module.AClass)
        self.check_function_failure(fn, ex, example_module.AFunction,
            TypeError)
        self.check_function_failure(fn, ex, "asdf", TypeError)

    def test_issubclass(self):
        fn = dynamicloader.issubclass
        ex = dynamicloader.expectissubclass
        self.check_value_function(fn, ex, example_module.CClass,
            example_module.Parent2, example_module.BClass, TypeError)

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

        afn = example_module.AFunction
        gfn = example_module.GFunction
        acl = example_module.AClass
        ccl = example_module.CClass
        dcl = example_module.DClass

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
        self.check_function_failure(fni, exi, acl, TypeError)
        self.check_function_failure(fni, exi, "asdf", TypeError)

    def test_hasnumargs(self):
        for func, val in [(example_module.AFunction, 0),
                          (example_module.BFunction, 3),
                          (example_module.CClass, 2),
                          (example_module.DClass, 2),
                          (example_module.BClass.a_method, 0)]:

            self.check_value_function(dynamicloader.hasnumargs,
                                      dynamicloader.expecthasnumargs,
                                      func, val, val + 1, TypeError)

    def test_hasstuff(self):
        """hasmethod, hasattr"""
        fna = dynamicloader.hasattr
        exa = dynamicloader.expecthasattr
        fnm = dynamicloader.hasmethod
        exm = dynamicloader.expecthasmethod
        acl = example_module.AClass
        bcl = example_module.BClass
        ccl = example_module.CClass
        mod = example_module

        self.check_value_function(fna, exa, acl, "anattr", "asdf", TypeError)
        self.check_value_function(fna, exa, ccl, "anattr", "asdf", TypeError)
        self.check_value_function(fna, exa, mod, "avariable", "z", TypeError)
        self.check_value_function(fna, exa, mod, "AFunction", "x", TypeError)

        self.check_value_function(fnm, exm, mod, "AFunction", "avariable",
            TypeError)
        self.check_value_function(fnm, exm, ccl, "__call__", "anattr",
            TypeError)
        self.check_value_function(fnm, exm, bcl, "a_method", "a", TypeError)

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
