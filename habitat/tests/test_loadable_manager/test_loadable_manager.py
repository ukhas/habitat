# Copyright 2011 (C) Daniel Richman
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
Tests the Loadable Manager
"""

import mox
from nose.tools import raises
from ... import loadable_manager

from . import example_loadable_library_a, example_loadable_library_b

example_path = "habitat.tests.test_loadable_manager.example_loadable_library"

fake_config = {
    "loadables": [
        {"name": "liba", "class": example_path + "_a"},
        {"name": "libb", "class": example_path + "_b"}
    ]
}

empty_config = {
    "loadables": []
}

cfg_c = {"abracadabra": "15802"}


class TestLoadableManager(object):
    def setup(self):
        self.mocker = mox.Mox()
        self.mocker.StubOutWithMock(loadable_manager, "dynamicloader")

    def teardown(self):
        self.mocker.UnsetStubs()

    def test_init_loads_db_listed_modules_and_works(self):
        loadable_manager.dynamicloader.load(example_path + "_a").AndReturn(
            example_loadable_library_a)
        loadable_manager.dynamicloader.load(example_path + "_b").AndReturn(
            example_loadable_library_b)
        f_a = example_loadable_library_a.format_a
        f_b = example_loadable_library_a.format_b
        f_c = example_loadable_library_b.format_c
        loadable_manager.dynamicloader.hasnumargs(f_a, 1).AndReturn(False)
        loadable_manager.dynamicloader.hasnumargs(f_b, 1).AndReturn(False)
        loadable_manager.dynamicloader.hasnumargs(f_c, 1).AndReturn(False)
        self.mocker.ReplayAll()
        self.mgr = loadable_manager.LoadableManager(fake_config)
        assert len(self.mgr.libraries) == 2
        assert self.mgr.run("liba.format_a", None, "thedata") == \
            ('formatted by a', "'thedata'")
        assert self.mgr.run("liba.format_b", None, "asdf") == \
            {"information": 64, "hello": "world"}
        assert self.mgr.run("libb.format_c", cfg_c, "asdf") == \
            "more functions"
        self.mocker.VerifyAll()
        self.mocker.ResetAll()

    @raises(ValueError)
    def test_errors_bubble_up(self):
        loadable_manager.dynamicloader.load(example_path + "_a").AndReturn(
            example_loadable_library_a)
        loadable_manager.dynamicloader.load(example_path + "_b").AndReturn(
            example_loadable_library_b)
        f_d = example_loadable_library_b.format_d
        loadable_manager.dynamicloader.hasnumargs(f_d, 1).AndReturn(False)
        self.mocker.ReplayAll()

        loadable_manager.LoadableManager(fake_config).run("libb.format_d", {},
                                                        "hmm")

        self.mocker.VerifyAll()
        self.mocker.ResetAll()

    def test_run_passes_config_dict(self):
        loadable_manager.dynamicloader.load(example_path + "_a").AndReturn(
            example_loadable_library_a)
        loadable_manager.dynamicloader.load(example_path + "_b").AndReturn(
            example_loadable_library_b)
        f_c = example_loadable_library_b.format_c
        loadable_manager.dynamicloader.hasnumargs(f_c, 1).AndReturn(False)
        self.mocker.ReplayAll()

        loadable_manager.LoadableManager(fake_config).run("libb.format_c",
                                                        cfg_c, "data")

        self.mocker.VerifyAll()
        self.mocker.ResetAll()

    @raises(ValueError)
    def test_cannot_use_loadable_not_in_all(self):
        loadable_manager.dynamicloader.load(example_path + "_a").AndReturn(
            example_loadable_library_a)
        loadable_manager.dynamicloader.load(example_path + "_b").AndReturn(
            example_loadable_library_b)
        self.mocker.ReplayAll()

        loadable_manager.LoadableManager(fake_config).run("libb.somethingelse",
                                                        {}, "hah!")

        self.mocker.VerifyAll()
        self.mocker.ResetAll()

    def test_repr_describes_manager(self):
        mgr = loadable_manager.LoadableManager(empty_config)
        expect = "<habitat.LoadableManager: {num} libraries loaded>"
        assert repr(mgr) == expect.format(num=0)
        mgr.load(example_path + "_a", "liba")
        assert repr(mgr) == expect.format(num=1)
