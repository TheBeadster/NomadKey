"""Canonical public ceremony binding, not a new cryptographic primitive."""
import hashlib
import json
import re

MAX_MESSAGE = 16384


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def decode(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_MESSAGE:
        raise ValueError("invalid message")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("invalid message")
    return value


def scope(service_public_key, destination):
    if len(service_public_key) != 64 or len(destination) != 16:
        raise ValueError("invalid service")
    digest = hashlib.sha256(b"NomadKey scope v1\0" + service_public_key + destination).hexdigest()
    # Native-client namespace; this is NOT a web origin certified through DNS/TLS.
    rp = "nk-" + digest[:32] + "." + digest[32:] + ".nomadkey.invalid"
    return rp, "https://" + rp


def binding(destination, service_public_key, link_id, client_public_key, nonce, permissions, lifetime, operation):
    return {"v": 1, "service": destination.hex(), "service_key": service_public_key.hex(),
            "link": link_id.hex(), "client": client_public_key.hex(), "nonce": nonce,
            "permissions": sorted(permissions), "lifetime": lifetime, "operation": operation}


def check_binding(value, destination, service_public_key, link_id, client_public_key, permissions, operation):
    expected = binding(destination, service_public_key, link_id, client_public_key,
                       value.get("nonce"), permissions, value.get("lifetime"), operation)
    if value != expected or not isinstance(value["nonce"], str) or not re.fullmatch(r"[0-9a-f]{64}", value["nonce"]):
        raise ValueError("ceremony binding mismatch")
    if type(value["lifetime"]) is not int or not 1 <= value["lifetime"] <= 3600:
        raise ValueError("invalid lifetime")
    return encode(value)
