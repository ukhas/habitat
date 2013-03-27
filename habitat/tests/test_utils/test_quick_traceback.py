# Copyright 2013 (C) Daniel Richman
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

from ...utils.quick_traceback import oneline


class TestOneline:
    def test_exception_without_value(self):
        try:
            raise ValueError
        except Exception as e:
            assert oneline(e) == oneline() == "ValueError"

    def test_exception_with_value(self):
        try:
            raise ValueError("something weird")
        except Exception as e:
            assert oneline(e) == oneline() == "ValueError: something weird"

    def test_wacky_exception(self):
        class CrazyException(Exception):
            def __str__(self):
                return "Custom stuff"

        try:
            raise CrazyException
        except Exception as e:
            assert oneline(e) == oneline() == "CrazyException: Custom stuff"
