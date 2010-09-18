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
Implements a generic dynamic loader. The main function to call is load().
In addition, several functions to quickly test the loaded object are provided:
    isclass
    isfunction
    isgeneratorfunction
    isstandardfunction (isfunction and not isgeneratorfunction)
    iscallable
    hasnumargs
    hasmethod
    hasattr
Further to that, functions expectisclass, expectisfunction are provided which
are identical to the above except they raise either a ValueError or a TypeError
where the original function would have returned false.

Example use:
def loadsomething(loadable):
    loadable = dynamicloader.load(loadable)
    expectisstandardfunction(loadable)
    expecthasattr(loadable, 2)

If you use expectiscallable note that you may get either a function or a class,
an object of which is callable (ie. the class has __call__(self, ...)). In that
case you may need to create an object:
    if isclass(loadable):
        loadable = loadable()
Of course if you've used expectiscallable then you will be creating an object
anyway.
"""

import sys
import collections
import functools
import inspect

def load(loadable):
    """
    Attempts to dynamically load "loadable", which is either a class,
    a function, a module, or a string: a dotted-path to one of those.

    e,g.:
        load(MyClass) returns MyClass
        load(MyFunction) returns MyFunction
        load("mypackage") returns the mypackage module
        load("packagea.packageb") returns the packageb module
        load("packagea.packageb.aclass") returns aclass
        e.t.c.
    """

    if isinstance(loadable, (str, unicode)):
        if len(loadable) <= 0:
            raise ValueError("loadable(str) must have non zero length")

        components = loadable.split(".")

        if "" in components or len(components) == 0:
            raise ValueError("loadable(str) contains empty components")

        if len(components) == 1:
            __import__(loadable)
            loadable = sys.modules[loadable]
        else:
            module_name = ".".join(components[:-1])
            target_name = components[-1]

            __import__(module_name)
            loadable = getattr(sys.modules[module_name], target_name)

    if inspect.isclass(loadable) or inspect.isfunction(loadable):
        pass
    elif inspect.ismodule(loadable):
        pass
    else:
        raise TypeError("load() takes a string, class, function or module")

    return loadable

# A large number of the functions we need can just be imported from inspect
from inspect import isclass, isfunction, isgeneratorfunction

# Some are very simple
isstandardfunction = lambda loadable: (isfunction(loadable) and not 
                                       isgeneratorfunction(loadable))

# The following we have to implement ourselves
def hasnumargs(thing, num):
    """
    Returns true if thing has num arguments.

    If thing is a function, the positional arguments are simply counted up.
    If thing is a method, the positional arguments are counted up and one
    is subtracted in order to account for method(self, ...)
    If thing is a class, the positional arguments of cls.__call__ are
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
    """
    Returns true if loadable.name is callable
    """
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
    Returns true if loadable is a method or function, OR if it is a class
    with a __call__ method (i.e., when an object is created from the class
    the object is callable)
    """
    if inspect.isclass(loadable):
        return hasmethod(loadable, "__call__")
    else:
        return inspect.isroutine(loadable)

# These functions are builtin, just transplant them into dynamicloader
issubclass = issubclass
hasattr = hasattr

# Generate an expect function decorator, which will wrap a function and 
# raise error rather than return false.
def expectgenerator(error):
    def decorator(function):
        def new_function(*args, **kwargs):
            if not function(*args, **kwargs):
                raise error()
        functools.update_wrapper(new_function, function)
        return new_function
    return decorator

expectisclass = expectgenerator(TypeError)(isclass)
expectisfunction = expectgenerator(TypeError)(isfunction)
expectisgeneratorfunction = expectgenerator(TypeError)(isgeneratorfunction)
expectisstandardfunction = expectgenerator(TypeError)(isstandardfunction)

expectiscallable = expectgenerator(ValueError)(iscallable)
expecthasnumargs = expectgenerator(ValueError)(hasnumargs)
expecthasmethod = expectgenerator(ValueError)(hasmethod)
expecthasattr = expectgenerator(ValueError)(hasattr)

