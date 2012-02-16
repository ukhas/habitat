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

"""
Functions for the flight design document.

Contains schema validation and views by flight launch time, window end time and
payload name and window end time.
"""

from .utils import rfc3339_to_timestamp, validate_doc

schema = {
    "title": "Flight Document",
    "type": "object",
    "additionalProperties": False,
    "required": True,
    "properties": {
        "_id": {
            "type": "string",
            "required": False
        },
        "_rev": {
            "type": "string",
            "required": False
        },
        "type": {
            "type": "string",
            "pattern": "^flight$",
            "required": True
        },
        "start": {
            "type": "string",
            "format": "date-time",
            "required": True
        },
        "end": {
            "type": "string",
            "format": "date-time",
            "required": True
        },
        "name": {
            "type": "string",
            "required": True
        },
        "launch": {
            "type": "object",
            "required": True,
            "additionalProperties": False,
            "properties": {
                "time": {
                    "type": "string",
                    "format": "date-time",
                    "required": True
                },
                "timezone": {
                    "type": "string",
                    "required": True
                },
                "location": {
                    "type": "object",
                    "required": True,
                    "additionalProperties": False,
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "minimum": -90,
                            "maximum": 90,
                            "required": True
                        },
                        "longitude": {
                            "type": "number",
                            "minimum": -180,
                            "maximum": 180,
                            "required": True
                        }
                    }
                }
            }
        },
        "metadata": {
            "type": "object",
            "required": False,
            "additionalProperties": True,
            "properties": {
                "location": {
                    "type": "string",
                    "required": False,
                },
                "project": {
                    "type": "string",
                    "required": False
                },
                "group": {
                    "type": "string",
                    "required": False
                }
            }
        },
        "payloads": {
            "type": "object",
            "required": True,
            "additionalProperties": False,
            "patternProperties": {
                "^[A-Za-z0-9]{1,20}$": {
                    "type": "object",
                    "required": True,
                    "additionalProperties": False,
                    "properties": {
                        "radio": {
                            "type": "object",
                            "additionalProperties": True,
                            "required": True,
                            "properties": {
                                "frequency": {
                                    "type": "number",
                                    "required": True
                                },
                                "mode": {
                                    "type": "string",
                                    "required": True
                                }
                            }
                        },
                        "telemetry": {
                            "type": "object",
                            "additionalProperties": True,
                            "required": True,
                            "properties": {
                                "modulation": {
                                    "type": "string",
                                    "required": True
                                },
                                "shift": {
                                    "type": "number",
                                    "required": False
                                },
                                "encoding": {
                                    "type": "string",
                                    "required": False
                                },
                                "baud": {
                                    "type": "number",
                                    "required": False
                                },
                                "parity": {
                                    "type": "string",
                                    "required": False
                                },
                                "stop": {
                                    "type": "number",
                                    "required": False
                                }
                            }
                        },
                        "sentence": {
                            "type": "object",
                            "required": True,
                            "additionalProperties": False,
                            "properties": {
                                "protocol": {
                                    "type": "string",
                                    "required": True
                                },
                                "checksum": {
                                    "type": "string",
                                    "required": False
                                },
                                "fields": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "required": True
                                            },
                                            "sensor": {
                                                "type": "string",
                                                "required": True
                                            },
                                            "format": {
                                                "type": "string",
                                                "required": False
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "filters": {
                            "type": "object",
                            "required": False,
                            "additionalProperties": False,
                            "properties": {
                                "intermediate": {
                                    "type": "array",
                                    "required": False,
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "type": {
                                                "type": "string",
                                                "required": True,
                                                "enum": ["normal", "hotfix"],
                                            },
                                            "callable": {
                                                "type": "string",
                                                "required": False
                                            },
                                            "config": {
                                                "type": "object",
                                                "required": False,
                                                "additionalProperties": True
                                            },
                                            "code": {
                                                "type": "string",
                                                "required": False
                                            },
                                            "signature": {
                                                "type": "string",
                                                "required": False
                                            },
                                            "certificate": {
                                                "type": "string",
                                                "required": False
                                            }
                                        }
                                    }
                                },
                                "post": {
                                    "type": "array",
                                    "required": False,
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "type": {
                                                "type": "string",
                                                "required": True,
                                                "enum": ["normal", "hotfix"],
                                            },
                                            "callable": {
                                                "type": "string",
                                                "required": False
                                            },
                                            "config": {
                                                "type": "object",
                                                "required": False,
                                                "additionalProperties": True
                                            },
                                            "code": {
                                                "type": "string",
                                                "required": False
                                            },
                                            "signature": {
                                                "type": "string",
                                                "required": False
                                            },
                                            "certificate": {
                                                "type": "string",
                                                "required": False
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "chasers": {
                            "type": "array",
                            "required": False,
                            "items": {
                                "type": "string"
                            }
                        }
                    }
                }
            }
        }
    }
}

def validate(new, old, userctx, secobj):
    """
    Validate this flight document against the schema.
    TODO: handle flight document test/approval/other status.
    TODO: value based validation
    """
    if new['type'] == "listener_telemetry":
        validate_doc(new, schema)

def end_map(doc):
    """Map by flight window end date."""
    if doc['type'] == "flight":
        yield rfc3339_to_timestamp(doc['end']), None

def launch_time_map(doc):
    """Map by flight launch time."""
    if doc['type'] == "flight":
        yield doc['launch']['time'], None

def payload_end_map(doc):
    """Map by payload and then flight window end date."""
    if doc['type'] == "flight":
        for payload in doc['payloads']:
            yield (payload, rfc3339_to_timestamp(doc['end'])), None

