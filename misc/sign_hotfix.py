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
import traceback
import ConfigParser
import hashlib
import json

def main():
    if len(sys.argv) == 2:
        config_file = sys.argv[1]
    elif len(sys.argv) == 1:
        config_file = "/etc/habitat/habitat.cfg"
    else:
        sys.stderr.write("Usage: {0} [config file]\n".format(sys.argv[0]))
        return

    try:
        config = ConfigParser.RawConfigParser()
        with open(config_file, "r") as f:
            config.readfp(f, config_file)
        config = dict(config.items("habitat"))
        secret = config["secret"]
    except:
        sys.stderr.write("Couldn't load secret from {0}:\n".format(config_file))
        traceback.print_exc()
        return
    else:
        sys.stderr.write("Loaded secret from {0}.\n".format(config_file))

    code = sys.stdin.read().strip()
    sig = hashlib.sha512(code + secret).hexdigest()
    filter_obj = {"type": "hotfix", "code": code, "signature": sig}

    print json.dumps(filter_obj)

if __name__ == "__main__":
    main()
