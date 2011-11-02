# Copyright 2010, 2011 (C) Adam Greig
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
Test the UKHAS protocol parser.
"""

from nose.tools import assert_raises
from copy import deepcopy

# Mocking the LoadableManager is a heck of a lot of effort. Not worth it.
from ...loadable_manager import LoadableManager
from ...parser_modules.ukhas_parser import UKHASParser

# Provide the sensor functions to the parser
fake_sensors_config = {
    "loadables": [
        {"name": "sensors.base", "class": "habitat.sensors.base"},
        {"name": "sensors.stdtelem", "class": "habitat.sensors.stdtelem"}
    ]
}


class FakeParser:
    def __init__(self):
        self.loadable_manager = LoadableManager(fake_sensors_config)

# A 'standard' config. Other configs can copy this and change parts.
base_config = {
    "protocol": "UKHAS",
    "checksum": "crc16-ccitt",
    "fields": [
        {
            "name": "message_count",
            "sensor": "base.ascii_int"
        }, {
            "name": "time",
            "sensor": "stdtelem.time"
        }, {
            "name": "latitude",
            "sensor": "stdtelem.coordinate",
            "format": "dd.dddd"
        }, {
            "name": "longitude",
            "sensor": "stdtelem.coordinate",
            "format": "dd.dddd"
        }, {
            "name": "altitude",
            "sensor": "base.ascii_int"
        }, {
            "name": "speed",
            "sensor": "base.ascii_float"
        }, {
            "name": "custom_string",
            "sensor": "base.string"
        }
    ]
}


class TestUKHASParser:
    """UKHAS Parser"""
    def setup(self):
        self.p = UKHASParser(FakeParser())

    def output_append_sentence(self, output, sentence):
        """Helper function to put a sentence in a pre-made output dictionary
        for easy comparison with parser results."""
        output_copy = deepcopy(output)
        output_copy["_sentence"] = sentence
        return output_copy

    def test_pre_parse_rejects_bad_sentences(self):
        # Each of these is a totally invalid stub that should just fail.  The
        # last one might be valid but has non-hexadecimal checksum characters.
        bad_sentences = ["", "\n", "bad\n", "$$bad*\n", "bad*CC\n",
                         "bad*CCCC\n", "bad,bad,bad,bad\n", "$$bad*GH\n",
                         "$$bad,bad*GHIJ\n", "$$@invalid@,data*CCCC\n",
                         "$$good,data,\x01\n", "$$missing,newline*CCCC"]

        for sentence in bad_sentences:
            assert_raises(ValueError, self.p.pre_parse, sentence)
            assert_raises(ValueError, self.p.parse, sentence, base_config)

    def test_pre_parse_accepts_good_setences(self):
        # Each of these short stubs should pass pre-parsing and return a
        # callsign
        good_sentences = ["$$good,data\n", "$$good,data*CC\n",
                          "$$good,data*CCCC\n",
                          "$$good,lots,of,1234,5678.90,data*CCCC\n"]

        for sentence in good_sentences:
            assert self.p.pre_parse(sentence) == "good"

    def test_pre_parse_rejects_bad_callsigns(self):
        bad_callsigns = ["abcdef@123", "ABC\xFA", "$$", "almost good"]
        callsign_template = "$${0},data*CC\n"
        for callsign in bad_callsigns:
            sentence = callsign_template.format(callsign)
            assert_raises(ValueError, self.p.pre_parse, sentence)

    def test_pre_parse_accepts_good_callsigns(self):
        good_callsigns = ["good", "g0_0d", "G0--0D", "abcde/f", "ABCDEF",
                          "012345", "abcDEF123"]
        callsign_template = "$${0},data*CC\n"
        for callsign in good_callsigns:
            sentence = callsign_template.format(callsign)
            assert self.p.pre_parse(sentence) == callsign

    def test_pre_parse_rejects_bad_checksums(self):
        bad_checksums = ["abcg", "123G", "$$", "*ABC", "defG", "123\xFA"]
        checksum_template = "$$good,data*{0}\n"
        for checksum in bad_checksums:
            sentence = checksum_template.format(checksum)
            assert_raises(ValueError, self.p.pre_parse, sentence)

    def test_pre_parse_accepts_good_checksums(self):
        good_checksums = ["abcd", "ABCD", "abCD", "ab12", "AB12", "aB12", "ab",
                          "aB", "AB", "a0", "A0"]
        checksum_template = "$$good,data*{0}\n"
        for checksum in good_checksums:
            sentence = checksum_template.format(checksum)
            assert self.p.pre_parse(sentence) == "good"

    def test_parse_rejects_invalid_configs(self):
        # A valid sentence for testing the configs with
        sentence = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab\n"

        # A configuration with no checksum
        config_checksum_none = deepcopy(base_config)
        config_checksum_none["checksum"] = "none"

        # A configuration without a protocol key (should fail)
        config_no_protocol = deepcopy(config_checksum_none)
        del config_no_protocol["protocol"]
        assert_raises(ValueError, self.p.parse, sentence, config_no_protocol)

        # A configuration without a checksum key (should fail)
        config_no_checksum = deepcopy(config_checksum_none)
        del config_no_checksum["checksum"]
        assert_raises(ValueError, self.p.parse, sentence, config_no_checksum)

        # A configuration without a fields dictionary (should fail)
        config_no_fields = deepcopy(config_checksum_none)
        del config_no_fields["fields"]
        assert_raises(ValueError, self.p.parse, sentence, config_no_fields)

        # A configuration with an empty fields dictionary (should fail)
        config_empty_fields = deepcopy(config_checksum_none)
        config_empty_fields["fields"] = {}
        assert_raises(ValueError, self.p.parse, sentence, config_empty_fields)

        # A configuration where a field has no name (should fail)
        config_field_without_name = deepcopy(config_checksum_none)
        del config_field_without_name["fields"][0]["name"]
        assert_raises(ValueError, self.p.parse, sentence,
                config_field_without_name)

        # A configuration where a field has no sensor (should fail)
        config_field_without_sensor = deepcopy(config_checksum_none)
        del config_field_without_sensor["fields"][0]["sensor"]
        assert_raises(ValueError, self.p.parse, sentence,
                config_field_without_sensor)

        # A configuration where a coordinate field lacks a format (should fail)
        config_field_without_format = deepcopy(config_checksum_none)
        del config_field_without_format["fields"][2]["format"]
        assert_raises(ValueError, self.p.parse, sentence,
                config_field_without_format)

        # A configuration with an invalid checksum (should fail)
        config_checksum_invalid = deepcopy(config_checksum_none)
        config_checksum_invalid = "invalid"
        assert_raises(ValueError, self.p.parse, sentence,
                config_checksum_invalid)

        # A configuration with an invalid protocol key (should fail)
        config_invalid_protocol = deepcopy(config_checksum_none)
        config_invalid_protocol["protocol"] = "invalid"
        assert_raises(ValueError, self.p.parse, sentence,
                config_invalid_protocol)

        # A configuration with an invalid field sensor (should fail)
        config_field_sensor_invalid = deepcopy(config_checksum_none)
        config_field_sensor_invalid["fields"][0]["sensor"] = "invalid"
        assert_raises(ValueError, self.p.parse, sentence,
                config_field_sensor_invalid)

        # A configuration with an invalid coordinate format (should fail)
        config_format_invalid = deepcopy(config_checksum_none)
        config_format_invalid["fields"][2]["format"] = "invalid"
        assert_raises(ValueError, self.p.parse, sentence,
                config_format_invalid)

        # A configuration with an invalid field name (should fail)
        config_name_invalid = deepcopy(config_checksum_none)
        config_name_invalid["fields"][0]["name"] = "_notallowed"
        assert_raises(ValueError, self.p.parse, sentence, config_name_invalid)

    def test_parse_parses_correct_checksums(self):
        # Correct parser output for the checksum test sentences
        output_checksum_test = {
            "payload": "habitat", "message_count": 1,
            "time": {"hour": 0, "minute": 0, "second": 0},
            "latitude": 0.0, "longitude": 0.0, "altitude": 0,
            "speed": 0.0, "custom_string": "hab"}

        # A configuration with no checksum
        config_checksum_none = deepcopy(base_config)
        config_checksum_none["checksum"] = "none"
        sentence_no_checksum = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab\n"
        assert (
            self.p.parse(sentence_no_checksum, config_checksum_none)
            == self.output_append_sentence(output_checksum_test,
                                           sentence_no_checksum))

        # A configuration with a CRC16-CCITT checksum
        config_checksum_crc16_ccitt = deepcopy(base_config)
        config_checksum_crc16_ccitt["checksum"] = "crc16-ccitt"
        sentence_crc16_ccitt = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab*EE5E\n"
        assert (
            self.p.parse(sentence_crc16_ccitt, config_checksum_crc16_ccitt)
            == self.output_append_sentence(output_checksum_test,
                                           sentence_crc16_ccitt))

        # A configuration with an XOR checksum
        config_checksum_xor = deepcopy(base_config)
        config_checksum_xor["checksum"] = "xor"
        sentence_xor = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab*0b\n"
        assert (
            self.p.parse(sentence_xor, config_checksum_xor)
            == self.output_append_sentence(output_checksum_test,
                                           sentence_xor))

        # A configuration with a Fletcher-16 checksum
        config_checksum_fletcher_16 = deepcopy(base_config)
        config_checksum_fletcher_16["checksum"] = "fletcher-16"
        sentence_fletcher_16 = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab*e3a6\n"
        assert (
            self.p.parse(sentence_fletcher_16, config_checksum_fletcher_16)
            == self.output_append_sentence(output_checksum_test,
                                           sentence_fletcher_16))

        # A configuration with a Fletcher-16 checksum, mod 256 (legacy)
        config_checksum_fletcher_16_256 = deepcopy(base_config)
        config_checksum_fletcher_16_256["checksum"] = "fletcher-16-256"
        sentence_fletcher_16_256 = \
            "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab*DBF5\n"
        assert (
            self.p.parse(sentence_fletcher_16_256,
                         config_checksum_fletcher_16_256)
            == self.output_append_sentence(output_checksum_test,
                                           sentence_fletcher_16_256))

    def test_parse_rejects_incorrect_checksums(self):
        sentence_no_checksum = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab\n"

        # A configuration with a CRC16-CCITT checksum
        config_checksum_crc16_ccitt = deepcopy(base_config)
        config_checksum_crc16_ccitt["checksum"] = "crc16-ccitt"
        sentence_bad_crc16_ccitt = \
            "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab*abcd\n"
        assert_raises(ValueError, self.p.parse, sentence_bad_crc16_ccitt,
                      config_checksum_crc16_ccitt)
        assert_raises(ValueError, self.p.parse, sentence_no_checksum,
                      config_checksum_crc16_ccitt)

        # A configuration with an XOR checksum
        config_checksum_xor = deepcopy(base_config)
        config_checksum_xor["checksum"] = "xor"
        sentence_bad_xor = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab*aa\n"
        assert_raises(ValueError, self.p.parse, sentence_bad_xor,
                      config_checksum_xor)
        assert_raises(ValueError, self.p.parse, sentence_no_checksum,
                      config_checksum_crc16_ccitt)

        # A configuration with a Fletcher-16 checksum
        config_checksum_fletcher_16 = deepcopy(base_config)
        config_checksum_fletcher_16["checksum"] = "fletcher-16"
        sentence_bad_fletcher_16 = \
            "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab*abcd\n"
        assert_raises(ValueError, self.p.parse, sentence_bad_fletcher_16,
                      config_checksum_fletcher_16)
        assert_raises(ValueError, self.p.parse, sentence_no_checksum,
                      config_checksum_fletcher_16)

        # A configuration with a Fletcher-16 checksum, mod 256 (legacy)
        config_checksum_fletcher_16_256 = deepcopy(base_config)
        config_checksum_fletcher_16_256["checksum"] = "fletcher-16-256"
        sentence_bad_fletcher_16_256 = \
            "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab*dcba\n"
        assert_raises(ValueError, self.p.parse, sentence_bad_fletcher_16_256,
                      config_checksum_fletcher_16_256)
        assert_raises(ValueError, self.p.parse, sentence_no_checksum,
                      config_checksum_fletcher_16_256)

    def test_parse_rejects_invalid_values(self):
        # A configuration with no checksum
        config = deepcopy(base_config)
        config["checksum"] = "none"

        sentence_bad_int = "$$habitat,a,00:00:00,0.0,0.0,0,0.0,hab\n"
        assert_raises(ValueError, self.p.parse, sentence_bad_int, config)

        sentence_bad_time = "$$habitat,1,aa:bb:cc,0.0,0.0,0,0.0,hab\n"
        assert_raises(ValueError, self.p.parse, sentence_bad_time, config)

        sentence_bad_time_2 = "$$habitat,1,123,0.0,0.0,0,0.0,hab\n"
        assert_raises(ValueError, self.p.parse, sentence_bad_time_2, config)

        sentence_bad_float = "$$habitat,1,00:00:00,abc,0.0,0,0.0,hab\n"
        assert_raises(ValueError, self.p.parse, sentence_bad_float, config)

    def test_parse_rejects_bad_minutes(self):
        # A configuration with coordinates in degrees and minutes
        config_minutes = deepcopy(base_config)
        config_minutes["fields"][2]["format"] = "ddmm.mm"
        config_minutes["fields"][3]["format"] = "ddmm.mm"
        config_minutes["checksum"] = "none"

        sentence_bad_minutes = \
            "$$habitat,1,00:00:00,087.123,0000.00,0,0.0,hab\n"

        assert_raises(ValueError, self.p.parse, sentence_bad_minutes,
                config_minutes)

    def test_parse_parses_good_sentences(self):
        # Several examples of valid sentences, where the coordinates are
        # variously mangled (in minutes, or with funny padding, random 0s and
        # spaces

        # A configuration with coordinates in degrees and minutes
        config_minutes = deepcopy(base_config)
        config_minutes["fields"][2]["format"] = "ddmm.mm"
        config_minutes["fields"][3]["format"] = "ddmm.mm"
        config_minutes["checksum"] = "none"

        # Correct parser output for (most) of the good sentences
        output_good = {
            "payload": "habitat", "message_count": 123,
            "time": {"hour": 12, "minute": 45, "second": 06},
            "latitude": -35.1032, "longitude": 138.8568,
            "altitude": 4285, "speed": 3.6, "custom_string": "hab"}

        sentence_good_1 = \
            "$$habitat,123,12:45:06,-35.1032,138.8568,4285,3.6,hab*5681\n"

        assert(self.p.parse(sentence_good_1, base_config)
               == self.output_append_sentence(output_good, sentence_good_1))

        sentence_good_2 = \
            "$$habitat,123,12:45,-35.1032,138.8568,4285,3.6,hab*8e78\n"

        # Correct parser output for sentence_good_2 (no seconds on the time)
        output_good_2 = deepcopy(output_good)
        del output_good_2["time"]["second"]

        assert(self.p.parse(sentence_good_2, base_config)
               == self.output_append_sentence(output_good_2, sentence_good_2))

        sentence_good_3 = \
            "$$habitat,123,12:45:06,-3506.192,13851.408,4285,3.6,hab*6139\n"

        assert(self.p.parse(sentence_good_3, config_minutes)
               == self.output_append_sentence(output_good, sentence_good_3))

        sentence_good_4 = \
            "$$habitat,123,12:45:06, -35.1032,138.8568,4285,3.6,hab*96A2\n"

        assert(self.p.parse(sentence_good_4, base_config)
               == self.output_append_sentence(output_good, sentence_good_4))

        sentence_good_5 = \
            "$$habitat,123,12:45:06,-035.1032,138.8568,4285,3.6,hab*C5CA\n"

        assert(self.p.parse(sentence_good_5, base_config)
               == self.output_append_sentence(output_good, sentence_good_5))

        sentence_good_6 = \
            "$$habitat,123,12:45:06,035.1032,0138.8568,4285,3.6,hab*D856\n"

        # Correct parser output for sentence_good_6 (positive latitude)
        output_good_6 = deepcopy(output_good)
        output_good_6["latitude"] = 35.1032

        assert(self.p.parse(sentence_good_6, base_config)
               == self.output_append_sentence(output_good_6, sentence_good_6))

    def test_parse_handles_shorter_sentences(self):
        # A sentence with less fields than the config suggests, but otherwise
        # valid
        sentence_short = "$$habitat,123,12:45:06,-35.1032,138.8568,4285*5260\n"

        output_short = {
            "payload": "habitat", "message_count": 123,
            "time": {"hour": 12, "minute": 45, "second": 06},
            "latitude": -35.1032, "longitude": 138.8568,
            "altitude": 4285}

        assert (self.p.parse(sentence_short, base_config) ==
                self.output_append_sentence(output_short, sentence_short))

    def test_parse_handles_longer_sentences(self):
        # A sentence with more fields than the config suggests, but otherwise
        # valid
        sentence_long = \
            "$$habitat,123,12:45:06,-35.1032,138.8568,4285,3.6,hab,123," \
            "4.56,seven*3253\n"

        output_long = {
            "payload": "habitat", "message_count": 123,
            "time": {"hour": 12, "minute": 45, "second": 06},
            "latitude": -35.1032, "longitude": 138.8568,
            "altitude": 4285, "speed": 3.6, "custom_string": "hab",
            "_extra_data": ["123", "4.56", "seven"]}
        assert (self.p.parse(sentence_long, base_config)
                == self.output_append_sentence(output_long, sentence_long))

    def test_parser_rejects_sentence_with_no_newline(self):
        # sentence from test_parse_handles_shorter_sentences with no \n:
        bad_sentence = "$$habitat,123,12:45:06,-35.1032,138.8568,4285*5260"

        assert_raises(ValueError, self.p.parse, bad_sentence, base_config)
