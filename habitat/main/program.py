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
The code in this module drives the "main" function itself, depending on the
sub-modules of habitat.main.
"""

from habitat.message_server import Server
from habitat.http import SCGIApplication
from options import get_options
from signals import SignalListener

class Program:
    def main(self):
        self.options = get_options()
        self.server = Server(None, self)
        self.scgiapp = SCGIApplication(self.server, self,
                                       self.options["socket_file"])
        self.signallistener = SignalListener(self)

        self.signallistener.setup()
        self.scgiapp.start()
        self.signallistener.listen()

    def reload(self):
        pass

    def shutdown(self):
        pass

    def panic(self):
        pass
