# Copyright 2010 (C) Daniel Richman
# Copyright 2010 (C) Adam Greig
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
A generic dynamic python module loader.

The main function to call is load(). In addition, several functions
to quickly test the loaded object for certain conditions are provided:

* **isclass**
* **isfunction**
* **isgeneratorfunction**
* **isstandardfunction** (``isfunction and not isgeneratorfunction``)
* **iscallable**
* **issubclass**
* **hasnumargs**
* **hasmethod**
* **hasattr**

Further to that, functions expectisclass, expectisfunction, e.t.c, are
provided which are identical to the above except they raise either a
ValueError or a TypeError where the original function would have
returned false.

Example use::

    def loadsomething(loadable):
        loadable = dynamicloader.load(loadable)
        expectisstandardfunction(loadable)
        expecthasattr(loadable, 2)

If you use expectiscallable note that you may get either a function
or a class, an object of which is callable (ie. the class has
``__call__(self, ...))``. In that case you may need to create an object::

    if isclass(loadable):
        loadable = loadable()

Of course if you've used expectisclass then you will be creating an object
anyway. Note that classes are technically "callable" in that calling them
creates objects. expectiscallable ignores this.

A lot of the provided tests are imported straight from inspect and are
therefore not documented here. The ones implemented as a part of this
module are.
"""

import sys
import collections
import functools
import inspect
import imp
import logging

all_tests = ["isclass", "isfunction", "isgeneratorfunction",
             "isstandardfunction", "iscallable", "issubclass",
             "hasnumargs", "hasmethod", "hasattr"]
expect_tests = ["expect" + test for test in all_tests]

__all__ = ["load", "fullname"] + all_tests + expect_tests
del all_tests, expect_tests

logger = logging.getLogger("habitat.utils.dynamicloader")

def load(loadable, force_reload=False):
    """
    Attempts to dynamically load *loadable*

    *loadable*: a class, a function, a module, or a string that is a
    dotted-path to one a class function or module

    Some examples::

        load(MyClass) # returns MyClass
        load(MyFunction) # returns MyFunction
        load("mypackage") # returns the mypackage module
        load("packagea.packageb") # returns the packageb module
        load("packagea.packageb.aclass") # returns aclass

    """

    old_modules = sys.modules.keys()

    if isinstance(loadable, basestring):
        if len(loadable) <= 0:
            raise ValueError("loadable(str) must have non zero length")

        components = loadable.split(".")

        if "" in components or len(components) == 0:
            raise ValueError("loadable(str) contains empty components")

        name_loaded = loadable

        try:
            # This will work if it is a module
            __import__(loadable)
            loadable = sys.modules[loadable]
        except ImportError:
            # This will work if it is a class or a function
            module_name = ".".join(components[:-1])
            target_name = components[-1]

            __import__(module_name)

            try:
                loadable = getattr(sys.modules[module_name], target_name)
            except KeyError:
                raise ImportError("Couldn't import " + loadable)

        # If neither worked; an error will have been raised.

        name_real = fullname(loadable)
        if name_real != name_loaded:
            logger.debug("loaded {0} => {1}".format(name_loaded, name_real))
        else:
            logger.debug("loaded {0}".format(name_real))

    # If force_reload is set, but it's the first time we've loaded this
    # loadable anyway, there's no point calling reload().

    # There could be a race condition between already_loaded and __import__,
    # however the worst that could happen is for already_loaded to be False
    # when infact by the time __import__ was reached, it had been loaded by
    # another thread. In this case the side effect is that reload may be
    # called on it. No bad effects, just a slight performance hit from double
    # loading. No big deal.

    if inspect.isclass(loadable) or inspect.isfunction(loadable):
        already_loaded = loadable.__module__ in old_modules

        if force_reload and already_loaded:
            logger.debug("reloading {0}".format(fullname(loadable)))

            # Reload the module and then find the new version of loadable
            module = sys.modules[loadable.__module__]
            reload(module)
            loadable = getattr(module, loadable.__name__)
    elif inspect.ismodule(loadable):
        already_loaded = loadable.__name__ in old_modules

        if force_reload and already_loaded:
            logger.debug("reloading {0}".format(fullname(loadable)))

            # Module objects are updated in place.
            reload(loadable)
    else:
        raise TypeError("load() takes a string, class, function or module")

    return loadable

def fullname(loadable):
    """
    Determines the full name in ``module.module.class`` form

    *loadable*: a class, module or function.

    If fullname is given a string it will :py:func:`load` it in order to
    resolve it to its true full name.
    """

    # You can import things into classes from all over the place. Therefore
    # you could have two different strings that you can pass to load but
    # load the same thing. If fullname() is given a string, rather than
    # simply return it, it has to load() it and then figure out what its
    # real full name is. See tests

    if isinstance(loadable, basestring):
        loadable = load(loadable)

    if inspect.isclass(loadable) or inspect.isfunction(loadable):
        return loadable.__module__ + "." + loadable.__name__
    elif inspect.ismodule(loadable):
        return loadable.__name__
    else:
        raise TypeError("loadable isn't class, function, or module")

# A large number of the functions we need can just be imported
from inspect import isclass, isfunction, isgeneratorfunction
from __builtin__ import issubclass, hasattr

# Some are very simple
isstandardfunction = lambda loadable: (isfunction(loadable) and not
                                       isgeneratorfunction(loadable))

# The following we have to implement ourselves
def hasnumargs(thing, num):
    """
    Returns true if thing has num arguments.

    If thing is a function, the positional arguments are simply counted up.
    If thing is a method, the positional arguments are counted up and one
    is subtracted in order to account for ``method(self, ...)``
    If thing is a class, the positional arguments of ``cls.__call__`` are
    counted up and one is subtracted (self), giving the number of arguments
    a callable object created from that class would have.
    """

    # Inspect argument list based on type. Class methods will
    # have a self argument, so account for that.
    if inspect.isclass(thing):
        args = len(inspect.getargspec(thing.__call__).args) - 1
    elif inspect.isfunction(thing):
        args = len(inspect.getargspec(thing).args)
    elif inspect.ismethod(thing):
        args = len(inspect.getargspec(thing).args) - 1
    else:
        return False

    return args == num

def hasmethod(loadable, name):
    """Returns true if *loadable*.*name* is callable """
    try:
        expecthasattr(loadable, name)
        expectiscallable(getattr(loadable, name))
        return True
    except:
        return False

# Builtin callable() is not good enough since it returns true for any
# class oboject
def iscallable(loadable):
    """
    Returns true if *loadable* is a method, function or callable class.

    For *loadable* to be a callable class, an object created from it must
    be callable (i.e., it has a ``__call__`` method)
    """

    if inspect.isclass(loadable):
        return hasmethod(loadable, "__call__")
    else:
        return inspect.isroutine(loadable)

# Generate an expect function decorator, which will wrap a function and
# raise error rather than return false.
def expectgenerator(error):
    def decorator(function):
        def new_function(*args, **kwargs):
            if not function(*args, **kwargs):
                raise error
        functools.update_wrapper(new_function, function)
        return new_function
    return decorator

expectisclass = expectgenerator(
        TypeError("Not a class"))(isclass)
expectisfunction = expectgenerator(
        TypeError("Not a function"))(isfunction)
expectisgeneratorfunction = expectgenerator(
        TypeError("Not a generator function"))(isgeneratorfunction)
expectisstandardfunction = expectgenerator(
        TypeError("Not a standard function"))(isstandardfunction)

expectiscallable = expectgenerator(
        TypeError("Not callable"))(iscallable)
expectissubclass = expectgenerator(
        TypeError("Not a correct subclass"))(issubclass)
expecthasnumargs = expectgenerator(
        TypeError("Incorrect number of args"))(hasnumargs)
expecthasmethod = expectgenerator(
        TypeError("Does not have a required method"))(hasmethod)
expecthasattr = expectgenerator(
        TypeError("Does not have a required attribute"))(hasattr)
