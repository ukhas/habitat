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

import sys
import os
import time
import inspect

class ReloadableModuleWriter:
    def __init__(self, parent_name, parent_file, modname, itemname):
        components = parent_name.split(".")
        components[-1:] = [modname, itemname]

        self.loadable = ".".join(components)
        self.fullmodname = ".".join(components[:-1])

        self.filename = os.path.join(os.path.dirname(parent_file),
                                     modname + ".py")

    # Even when the builtin reload is called python will read from the
    # pyc file if the embedded mtime matches that of the py file. That's
    # typically going to be fine, however, if you load, modify, reload
    # within one second then the updated module won't be read.
    # We won't be reloading that fast, but the test will. So hack the 
    # mtime two seconds into the future every time.

    def is_loaded(self):
        if self.fullmodname in sys.modules:
            raise ValueError("modname %s is already in sys.modules")

    def write_code(self, code):
        try:
            newtime = os.path.getmtime(self.filename) + 2
        except OSError:
            newtime = int(time.time())

        with open(self.filename, 'w') as f:
            f.write(code)

        os.utime(self.filename, (newtime, newtime))
