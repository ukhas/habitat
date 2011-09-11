__all__ = ["format_a", "format_b"]

def format_a(config, data):
    return ("formatted by a", repr(data))

def format_b(config, data):
    return {"information": 64, "hello": "world"}
