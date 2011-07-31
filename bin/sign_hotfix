#!/usr/bin/env python
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
Sign a piece of hotfix code using a provided RSA private key and output
appropriate JSON for inserting into a flight document.
"""

import M2Crypto
import sys
import os.path
import json
import hashlib
import base64

def main():
    if len(sys.argv) != 3:
        print "Usage: {0} <code file> <private key file>".format(sys.argv[0])
        return

    codefilename = sys.argv[1]
    keyfilename = sys.argv[2]

    try:
        with open(codefilename) as f:
            code = f.read().strip()
        key = M2Crypto.RSA.load_key(keyfilename)
    except IOError:
        print "Could not load files. Check filenames."
        return

    digest = hashlib.sha256(code).hexdigest()
    sig = base64.b64encode(key.sign(digest, 'sha256'))

    certfilename = os.path.splitext(os.path.basename(keyfilename))[0] + ".crt"

    filter_obj = {
        "type": "hotfix",
        "code": code,
        "signature": sig,
        "certificate": certfilename
    }

    print json.dumps(filter_obj)

if __name__ == "__main__":
    main()
