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
Tests habitat.main.setup_logging()
"""

import logging

from nose.tools import raises

from habitat import main

class FakeLogging:
    DEBUG = logging.DEBUG
    WARNING = logging.WARNING

    def __init__(self):
        self.rt = self.Logger()
        self.restkitlogger = self.Logger()

    def getLogger(self, name=None):
        if name == None:
            return self.rt
        elif name == "restkit":
            return self.restkitlogger
        else:
            raise ValueError("Requested an unexpected logger")

    class Logger:
        def __init__(self):
            self.handlers = []
        def addHandler(self, hdlr):
            self.handlers.append(hdlr)
        def setLevel(self, level):
            self.level = level

    class FakeHandler:
        def setFormatter(self, formatter):
            self.formatter = formatter
        def setLevel(self, level):
            self.level = level

    class FileHandler(FakeHandler):
        def __init__(self, filename, mode='a'):
            self.filename = filename
            self.mode = mode

    class StreamHandler(FakeHandler):
        # Expect no arguments to initialiser.
        pass

    class NullHandler:
        # Don't let it call setLevel or anything
        pass

    class Formatter:
        def __init__(self, formatstring, dateformatstring=None):
            self.formatstring = formatstring
            self.dateformatstring = dateformatstring

expect_formatstring = "[%(asctime)s] %(levelname)s %(name)s " + \
                      "%(threadName)s: %(message)s"

class TestSetupLogging:
    def setup(self):
        assert main.logging == logging
        main.logging = FakeLogging()

    def teardown(self):
        assert isinstance(main.logging, FakeLogging)
        main.logging = logging

    def test_adds_file_handler_correctly(self):
        main.setup_logging(None, "testfile", logging.DEBUG)
        assert main.logging.rt.level == logging.DEBUG
        assert len(main.logging.rt.handlers) == 1
        self.check_file_handler(main.logging.rt.handlers[0])

    def check_file_handler(self, h):
        assert isinstance(h, main.logging.FileHandler)
        assert h.formatter.formatstring == expect_formatstring
        assert h.formatter.dateformatstring == None
        assert h.level == logging.DEBUG
        assert h.filename == "testfile"
        assert h.mode == "a"

    def test_adds_stderr_handler_correctly(self):
        main.setup_logging(logging.WARN, None, None)
        assert main.logging.rt.level == logging.DEBUG
        assert len(main.logging.rt.handlers) == 1
        self.check_stderr_handler(main.logging.rt.handlers[0])

    def check_stderr_handler(self, h):
        assert isinstance(h, main.logging.StreamHandler)
        assert h.formatter.formatstring == expect_formatstring
        assert h.formatter.dateformatstring == None
        assert h.level == logging.WARN

    def test_adds_both_handlers_correctly(self):
        main.setup_logging(logging.WARN, "testfile", logging.DEBUG)
        assert len(main.logging.rt.handlers) == 2

        if isinstance(main.logging.rt.handlers[0], main.logging.StreamHandler):
            sh = main.logging.rt.handlers[0]
            fh = main.logging.rt.handlers[1]
        else:
            fh = main.logging.rt.handlers[0]
            sh = main.logging.rt.handlers[1]

        self.check_stderr_handler(sh)
        self.check_file_handler(fh)

    def test_adds_atleast_null_handler(self):
        main.setup_logging(None, None, None)
        assert len(main.logging.rt.handlers) == 1
        assert isinstance(main.logging.rt.handlers[0],
                          main.logging.NullHandler)
