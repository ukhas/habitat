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
Patches threading.Thread.__init__ to check that every thread created is
a crashmat.Thread instance, rather than a thread created directly.
"""

import re
import threading
from habitat.utils import crashmat

__all__ = ["patch", "restore"]

def new_init(self, *args, **kwargs):
    assert isinstance(self, crashmat.Thread)
    return new_init.old(self, *args, **kwargs)
new_init.old = threading.Thread.__init__

default_threadname = re.compile("^Thread-\d+$")

def new_start(self, *args, **kwargs):
    assert default_threadname.match(self.name) == None
    return new_start.old(self, *args, **kwargs)
new_start.old = threading.Thread.start

magic = 157346

def patch():
    assert threading.Thread.__init__ == new_init.old
    assert threading.Thread.start == new_start.old
    threading.Thread.__init__ = new_init
    threading.Thread.start = new_start

    # When restoring, it's worth being sure that something else hasn't
    # put a patch on top of the patch, so save a copy of what
    # __init__ and start looked like when we finished with them
    threading.Thread.threading_checks_patch = \
        (magic, threading.Thread.__init__, threading.Thread.start)

def restore():
    # Check that __init__ and start haven't been further modified
    # since we patched them...
    assert threading.Thread.threading_checks_patch == \
        (magic, threading.Thread.__init__, threading.Thread.start)
    del threading.Thread.threading_checks_patch

    threading.Thread.__init__ = new_init.old
    threading.Thread.start = new_start.old
