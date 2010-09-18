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
Mock classes to load in test_dynamicloader.py, however, these won't be
imported at the top of test_dynamicloader so the first time load is
called should be the first time python has heard of them
""" 

class Parent:
    pass

class Parent2:
    pass

class AClass(Parent, Parent2):
    anattr = "asdf"

class BClass:
    def __init__():
        self.b_method = CClass()

    def a_method(self):
        pass

class CClass(AClass):
    def __call__(self, argb, argc, **kwords):
        pass

def AFunction():
    return 412314

def BFunction(arg, argz, argx):
    pass

def GFunction():
    yield "Hello"
    yield "World"

AFunction.afuncattr = None

