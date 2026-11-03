"""Test-only ES256 authenticator. No production code imports this module."""
import hashlib
import secrets
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from fido2.cose import ES256
from fido2.webauthn import AttestedCredentialData, Aaguid, AuthenticatorData, CollectedClientData
from fido2.utils import websafe_encode


class SoftwareAuthenticator:
    def __init__(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.data = AttestedCredentialData.create(Aaguid.NONE, secrets.token_bytes(32), ES256.from_cryptography_key(self.key.public_key()))
        self.counter = 0

    def assertion(self, options, origin, flags=5):
        options = options["publicKey"]
        self.counter += 1
        cd = CollectedClientData.create("webauthn.get", options["challenge"], origin)
        ad = AuthenticatorData.create(hashlib.sha256(options["rpId"].encode()).digest(), flags, self.counter)
        signature = self.key.sign(bytes(ad) + cd.hash, ec.ECDSA(hashes.SHA256()))
        return {"id": websafe_encode(self.data.credential_id), "rawId": websafe_encode(self.data.credential_id),
                "type":"public-key", "response": {"clientDataJSON":websafe_encode(cd),
                "authenticatorData":websafe_encode(ad), "signature":websafe_encode(signature)}}
