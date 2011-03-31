# Copyright 2010 (C) Adam Greig
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

# It would require a disproportionate amount of work to create a
# FakeSensorManager
from habitat.sensor_manager import SensorManager

from habitat.parser_modules.ukhas_parser import UKHASParser

# A 'standard' config. Other configs can copy this and change parts.
base_config = {
    "protocol": "UKHAS",
    "checksum": "crc16-ccitt",
    "fields": [
        {
            "name": "message_count",
            "type": "base.ascii_int"
        }, {
            "name": "time",
            "type": "stdtelem.time"
        }, {
            "name": "latitude",
            "type": "stdtelem.coordinate",
            "format": "dd.dddd"
        }, {
            "name": "longitude",
            "type": "stdtelem.coordinate",
            "format": "dd.dddd"
        }, {
            "name": "altitude",
            "type": "base.ascii_int"
        }, {
            "name": "speed",
            "type": "base.ascii_float"
        }, {
            "name": "custom_string",
            "type": "base.string"
        }
    ]
}

# Each of these is a totally invalid stub that should just fail.
# The last one might be valid but has non-hexadecimal checksum characters.
bad_sentences = ["", "bad", "$$bad*", "bad*CC", "bad*CCCC", "bad,bad,bad,bad",
    "$$bad*GH", "$$bad,bad*GHIJ", "$$_invalid_,data*CCCC", "$$good,data,\x01"]

# Each of these short stubs should pass pre-parsing and return a callsign
good_sentences = ["$$good,data", "$$good,data*CC", "$$good,data*CCCC",
        "$$good,lots,of,1234,5678.90,data$CCCC"]

good_callsigns = ["good", "g00d", "G00D", "abcdef", "ABCDEF", "012345",
    "abcDEF123"]
bad_callsigns = ["_", "-", "abcdef_123", "ABC\xFA", "$$", "almost good"]
callsign_template = "$${0},data*CC"

good_checksums = ["abcd", "ABCD", "abCD", "ab12", "AB12", "aB12", "ab", "aB",
    "AB", "a0", "A0"]
bad_checksums = ["abcg", "123G", "$$", "*ABC", "defG", "123\xFA"]
checksum_template = "$$good,data*{0}"

# A configuration with a CRC16-CCITT checksum
config_checksum_crc16_ccitt = deepcopy(base_config)
config_checksum_crc16_ccitt["checksum"] = "crc16-ccitt"

# A configuration with an XOR checksum
config_checksum_xor = deepcopy(base_config)
config_checksum_xor["checksum"] = "xor"

# A configuration with a Fletcher-16 checksum
config_checksum_fletcher_16 = deepcopy(base_config)
config_checksum_fletcher_16["checksum"] = "fletcher-16"

# A configuration with a Fletcher-16 checksum, mod 256 (legacy)
config_checksum_fletcher_16_256 = deepcopy(base_config)
config_checksum_fletcher_16_256["checksum"] = "fletcher-16-256"

# A configuration with no checksum
config_checksum_none = deepcopy(base_config)
config_checksum_none["checksum"] = "none"

# A configuration without a protocol key (should fail)
config_no_protocol = deepcopy(config_checksum_none)
del config_no_protocol["protocol"]

# A configuration with an invalid protocol key (should fail)
config_invalid_protocol = deepcopy(config_checksum_none)
config_invalid_protocol["protocol"] = "invalid"

# A configuration without a checksum key (should fail)
config_no_checksum = deepcopy(config_checksum_none)
del config_no_checksum["checksum"]

# A configuration without a fields dictionary (should fail)
config_no_fields = deepcopy(config_checksum_none)
del config_no_fields["fields"]

# A configuration with an empty fields dictionary (should fail)
config_empty_fields = deepcopy(config_checksum_none)
config_empty_fields["fields"] = {}

# A configuration where a field has no name (should fail)
config_field_without_name = deepcopy(config_checksum_none)
del config_field_without_name["fields"][0]["name"]

# A configuration where a field has no type (should fail)
config_field_without_type = deepcopy(config_checksum_none)
del config_field_without_type["fields"][0]["type"]

# A configuration where a coordinate field lacks a format (should fail)
config_field_without_format = deepcopy(config_checksum_none)
del config_field_without_format["fields"][2]["format"]

# A configuration with an invalid checksum (should fail)
config_checksum_invalid = deepcopy(config_checksum_none)
config_checksum_invalid = "invalid"

# A configuration with an invalid field type (should fail)
config_field_type_invalid = deepcopy(config_checksum_none)
config_field_type_invalid["fields"][0]["type"] = "invalid"

# A configuration with an invalid coordinate format (should fail)
config_format_invalid = deepcopy(config_checksum_none)
config_format_invalid["fields"][2]["format"] = "invalid"

# A configuration with an invalid field name (should fail)
config_name_invalid = deepcopy(config_checksum_none)
config_name_invalid["fields"][0]["name"] = "_notallowed"

# A valid sentence for testing the configs with
sentence_config = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab"

# A configuration with coordinates in degrees and minutes
config_minutes = deepcopy(config_checksum_none)
config_minutes["fields"][2]["format"] = "ddmm.mm"
config_minutes["fields"][3]["format"] = "ddmm.mm"

# Valid sentences with various valid checksums
sentence_no_checksum = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab"
sentence_crc16_ccitt = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab*EE5E"
sentence_xor = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab*0b"
sentence_fletcher_16 = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab*e3a6"
sentence_fletcher_16_256 = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab*DBF5"

# Valid sentences with various incorrect checksums
sentence_bad_crc16_ccitt = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab*abcd"
sentence_bad_xor = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab*aa"
sentence_bad_fletcher_16 = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab*abcd"
sentence_bad_fletcher_16_256 = "$$habitat,1,00:00:00,0.0,0.0,0,0.0,hab*dcba"

# Sentences with invalid field values
sentence_bad_int = "$$habitat,a,00:00:00,0.0,0.0,0,0.0,hab"
sentence_bad_time = "$$habitat,1,aa:bb:cc,0.0,0.0,0,0.0,hab"
sentence_bad_time_2 = "$$habitat,1,123,0.0,0.0,0,0.0,hab"
sentence_bad_float = "$$habitat,1,00:00:00,abc,0.0,0,0.0,hab"
sentence_bad_minutes = "$$habitat,1,00:00:00,087.123,0000.00,0,0.0,hab"

# Several examples of valid sentences, where the coordinates are variously
# mangled (in minutes, or with funny padding, random 0s and spaces
sentence_good = "$$habitat,123,12:45:06,-35.1032,138.8568,4285,3.6,hab*5681"
sentence_good_2 = "$$habitat,123,12:45,-35.1032,138.8568,4285,3.6,hab*8e78"
sentence_good_3 = \
    "$$habitat,123,12:45:06,-3506.192,13851.408,4285,3.6,hab*6139"
sentence_good_4 = \
    "$$habitat,123,12:45:06, -35.1032,138.8568,4285,3.6,hab*96A2"
sentence_good_5 = \
    "$$habitat,123,12:45:06,-035.1032,138.8568,4285,3.6,hab*C5CA"
sentence_good_6 = \
    "$$habitat,123,12:45:06,035.1032,0138.8568,4285,3.6,hab*D856"

# Correct parser output for the checksum test sentences
output_checksum_test = {
    "payload": "habitat", "message_count": 1,
    "time": {"hour": 0, "minute": 0, "second": 0},
    "latitude": 0.0, "longitude": 0.0, "altitude": 0,
    "speed": 0.0, "custom_string": "hab"}

# Correct parser output for (most) of the good sentences
output_good = {
    "payload": "habitat", "message_count": 123,
    "time": {"hour": 12, "minute": 45, "second": 06},
    "latitude": -35.1032, "longitude": 138.8568,
    "altitude": 4285, "speed": 3.6, "custom_string": "hab"}

# Correct parser output for sentence_good_2 (no seconds on the time)
output_good_2 = deepcopy(output_good)
del output_good_2["time"]["second"]

# Correct parser output for sentence_good_6 (positive latitude)
output_good_6 = deepcopy(output_good)
output_good_6["latitude"] = 35.1032

# A sentence with less fields than the config suggests, but otherwise valid
sentence_short = "$$habitat,123,12:45:06,-35.1032,138.8568,4285*5260"
output_short = deepcopy(output_good)
del output_short["speed"]
del output_short["custom_string"]

# A sentence with more fields than the config suggests, but otherwise valid
sentence_long = "$$habitat,123,12:45:06,-35.1032,138.8568,4285,3.6,hab,123" \
                ",4.56,seven*3253"
output_long = deepcopy(output_good)
output_long["_extra_data"] = ["123", "4.56", "seven"]

# Provide the sensor functions to the parser
class FakeProgram:
    def __init__(self, db):
        self.db = db
    def set_sensor_manager(self, sensor_manager):
        self.sensor_manager = sensor_manager

class FakeServer:
    def __init__(self, program):
        self.program = program

class FakeParser:
    def __init__(self, server):
        self.server = server

fake_sensors_db = {
    "sensor_manager_config": {
        "libraries": { "stdtelem": "habitat.sensors.stdtelem" }
    }
}

class TestUKHASParser:
    """UKHAS Parser"""
    def setUp(self):
        fake_program = FakeProgram(fake_sensors_db)
        sensor_manager = SensorManager(fake_program)
        fake_program.set_sensor_manager(sensor_manager)
        fake_parser = FakeParser(FakeServer(fake_program))
        self.p = UKHASParser(fake_parser)

    def test_pre_parse_rejects_bad_sentences(self):
        for sentence in bad_sentences:
            assert_raises(ValueError, self.p.pre_parse, sentence)

    def test_pre_parse_accepts_good_setences(self):
        for sentence in good_sentences:
            assert self.p.pre_parse(sentence) == "good"

    def test_pre_parse_rejects_bad_callsigns(self):
        for callsign in bad_callsigns:
            sentence = callsign_template.format(callsign)
            assert_raises(ValueError, self.p.pre_parse, sentence)

    def test_pre_parse_accepts_good_callsigns(self):
        for callsign in good_callsigns:
            sentence = callsign_template.format(callsign)
            assert self.p.pre_parse(sentence) == callsign

    def test_pre_parse_rejects_bad_checksums(self):
        for checksum in bad_checksums:
            sentence = checksum_template.format(checksum)
            assert_raises(ValueError, self.p.pre_parse, sentence)

    def test_pre_parse_accepts_good_checksums(self):
        for checksum in good_checksums:
            sentence = checksum_template.format(checksum)
            assert self.p.pre_parse(sentence) == "good"

    def test_parse_rejects_bad_sentences(self):
        for sentence in bad_sentences:
            assert_raises(ValueError, self.p.parse, sentence, base_config)

    def test_parse_rejects_invalid_configs(self):
        for config in [
                config_no_protocol, config_no_checksum, config_no_fields,
                config_empty_fields, config_field_without_name,
                config_field_without_type, config_field_without_format,
                config_checksum_invalid, config_field_type_invalid,
                config_format_invalid, config_name_invalid,
                config_invalid_protocol
            ]:
            assert_raises(ValueError, self.p.parse, sentence_config, config)

    def test_parse_parses_correct_checksums(self):
        for sentence, config in [
                [sentence_no_checksum, config_checksum_none],
                [sentence_crc16_ccitt, config_checksum_crc16_ccitt],
                [sentence_xor, config_checksum_xor],
                [sentence_fletcher_16, config_checksum_fletcher_16],
                [sentence_fletcher_16_256, config_checksum_fletcher_16_256]
            ]:
            assert (self.p.parse(sentence, config) ==
                    self.output_append_sentence(output_checksum_test,
                        sentence))

    def test_parse_rejects_incorrect_checksums(self):
        for sentence, config in [
                [sentence_bad_crc16_ccitt, config_checksum_crc16_ccitt],
                [sentence_no_checksum, config_checksum_crc16_ccitt],
                [sentence_bad_xor, config_checksum_xor],
                [sentence_no_checksum, config_checksum_xor],
                [sentence_bad_fletcher_16, config_checksum_fletcher_16],
                [sentence_no_checksum, config_checksum_fletcher_16],
                [sentence_no_checksum, config_checksum_fletcher_16_256],
                [sentence_bad_fletcher_16_256, config_checksum_fletcher_16_256]
            ]:
            assert_raises(ValueError, self.p.parse, sentence, config)

    def test_parse_rejects_invalid_values(self):
        for sentence in [
                sentence_bad_int, sentence_bad_float, sentence_bad_time]:
            assert_raises(ValueError, self.p.parse, sentence,
                    config_checksum_none)

    def test_parse_rejects_bad_minutes(self):
        assert_raises(ValueError, self.p.parse, sentence_bad_minutes,
                config_minutes)

    def test_parse_parses_good_sentences(self):
        for sentence, output, config in [
                [sentence_good, output_good, base_config],
                [sentence_good_2, output_good_2, base_config],
                [sentence_good_3, output_good, config_minutes],
                [sentence_good_4, output_good, base_config],
                [sentence_good_5, output_good, base_config],
                [sentence_good_6, output_good_6, base_config]
            ]:
            assert (self.p.parse(sentence, config) ==
                    self.output_append_sentence(output, sentence))

    def test_parse_handles_shorter_sentences(self):
        assert (self.p.parse(sentence_short, base_config) ==
                self.output_append_sentence(output_short, sentence_short))

    def test_parse_handles_longer_sentences(self):
        assert (self.p.parse(sentence_long, base_config)
                == self.output_append_sentence(output_long, sentence_long))

    def output_append_sentence(self, output, sentence):
        output_copy = deepcopy(output)
        output_copy["_sentence"] = sentence
        return output_copy
