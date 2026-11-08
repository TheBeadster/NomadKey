import secrets
import threading
import time
from dataclasses import dataclass

from fido2.server import Fido2Server
from fido2.webauthn import AuthenticationResponse

from .protocol import binding, encode, scope


class Denied(ValueError):
    pass


@dataclass
class Credential:
    data: object
    permissions: frozenset
    counter: int = 0


class Auth:
    """All authority is tied to an authenticated, live RNS Link, never an identity ACL.

    Caller must supply transport-observed link and identified public key, never form fields.
    RNS verifies identification signatures over link_id + identity public key.
    """
    def __init__(self, public_key, destination, credentials, lifetime=300, clock=time.monotonic, notification_handler=None):
        if type(lifetime) is not int or not 1 <= lifetime <= 3600:
            raise ValueError("lifetime must be 1..3600 seconds")
        self.public_key, self.destination = public_key, destination
        self.credentials, self.lifetime, self.clock = credentials, lifetime, clock
        rp, origin = scope(public_key, destination)
        self.fido = Fido2Server({"id": rp, "name": "NomadKey"}, verify_origin=lambda o: o == origin)
        self.pending, self.sessions, self.attempts = {}, {}, {}
        self.global_attempts = []
        self.lock = threading.RLock()
        self.notification_handler = notification_handler

    def _sweep(self):
        now = self.clock()
        self.pending = {k:v for k,v in self.pending.items() if v["deadline"] > now}
        self.sessions = {k:v for k,v in self.sessions.items() if v["deadline"] > now}
        self.attempts = {k:[t for t in v if t > now-60] for k,v in self.attempts.items() if v and v[-1] > now-60}
        self.global_attempts = [t for t in self.global_attempts if t > now-60]

    def begin(self, link, client, permissions=("pages:read",), operation=None):
        with self.lock:
            self._sweep()
            if len(link) != 16 or len(client) != 64:
                raise Denied("identified link required")
            if permissions not in (("pages:read",), ("admin",), ("notifications:manage",)):
                raise Denied("unsupported permission")
            if permissions == ("notifications:manage",):
                if self.notification_handler is None or operation not in ({"notifications":"subscribe"},{"notifications":"unsubscribe"}):
                    raise Denied("unsupported notification operation")
            elif permissions == ("admin",):
                if not isinstance(operation, dict) or set(operation) != {"remove_credential"}:
                    raise Denied("unsupported operation")
                if operation["remove_credential"] not in self.credentials:
                    raise Denied("unknown credential")
            elif operation is not None:
                raise Denied("operation not allowed")
            now = self.clock()
            attempts = self.attempts.setdefault(client, [])
            if len(attempts) >= 5 or len(self.global_attempts) >= 30 or len(self.pending) >= 64:
                raise Denied("throttled")
            attempts.append(now); self.global_attempts.append(now)
            eligible = [c.data for c in self.credentials.values() if set(permissions) <= c.permissions]
            if not eligible:
                raise Denied("no eligible credential")
            value = binding(self.destination, self.public_key, link, client, secrets.token_hex(32),
                            permissions, self.lifetime, operation)
            options, state = self.fido.authenticate_begin(eligible, user_verification="required", challenge=encode(value))
            options = dict(options)
            options["publicKey"]["timeout"] = 60000
            self.pending[link] = {"client": client, "deadline": now+60, "state":state, "binding":value, "eligible":eligible}
            return {"binding": value, "options": options}

    def complete(self, link, client, response):
        with self.lock:
            self._sweep()
            pending = self.pending.pop(link, None)  # every attempt consumes the challenge
            if not pending or pending["client"] != client:
                raise Denied("no matching challenge")
            try:
                parsed = AuthenticationResponse.from_dict(response)
                if parsed.response.client_data.cross_origin:
                    raise ValueError("cross origin")
                credential = self.fido.authenticate_complete(pending["state"], pending["eligible"], parsed)
                key = credential.credential_id.hex()
                record = self.credentials[key]
                counter = parsed.response.authenticator_data.counter
                if (record.counter or counter) and counter <= record.counter:
                    raise ValueError("counter rollback")
                if not set(pending["binding"]["permissions"]) <= record.permissions:
                    raise ValueError("credential permissions changed")
                record.counter = counter
            except Exception as exc:
                raise Denied("invalid assertion") from exc
            operation = pending["binding"]["operation"]
            if operation is not None:
                if "notifications" in operation:
                    self.notification_handler(client, key, operation["notifications"])
                else:
                    self.remove_credential(operation["remove_credential"])
                return {"ok": True, "operation": operation}
            # Restart destroys all objects. No wall clock or refresh mutation exists.
            self.sessions[link] = {"client":client, "credential":key, "deadline":self.clock()+self.lifetime,
                                   "permissions":frozenset(pending["binding"]["permissions"])}
            return {"ok": True, "expires_in": self.lifetime}

    def require(self, link, client, permission="pages:read"):
        with self.lock:
            self._sweep()
            session = self.sessions.get(link)
            if not session or session["client"] != client or permission not in session["permissions"]:
                raise Denied("authentication required")
            record = self.credentials.get(session["credential"])
            if not record or permission not in record.permissions:
                raise Denied("credential revoked")
            return max(0, session["deadline"] - self.clock())

    def forget(self, link):
        with self.lock:
            self.sessions.pop(link, None); self.pending.pop(link, None)
            return {"revoked": True}

    def remove_credential(self, key):
        with self.lock:
            self.credentials.pop(key, None)
            self.sessions = {k:v for k,v in self.sessions.items() if v["credential"] != key}
            self.pending.clear()
