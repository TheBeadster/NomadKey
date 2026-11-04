# NomadKey — development prototype

FIDO2 authorization for short-lived access to a separate NomadNet service, using replaceable Reticulum client identities. No SMS or banking integration.

**Development build.** The user confirmed Android/Flex authentication, five-minute expiry denial and Forget me denial on 4 November 2026. YubiKey and PC hardware remain untested. Existing estate pages remain on their original service. The protected destination now serves live, read-only PiMonitor host status. Follow [status](docs/STATUS.md) for actual checks and outstanding limitations.

## Implemented

- Python FIDO2 verifier and native CTAP2 client using Yubico python-fido2.
- Session authority bound to one identified RNS link, its client public key, service identity, permissions and server lifetime.
- Five-minute absolute server expiry using a monotonic clock; single-use 60-second challenges, fail-closed content checks, Forget me and fresh credential-removal authorization.
- A separate Columba 2.3.1-beta development entry point, Python RNS transport and Android ISO-DEP NFC adapter. Protected content is rendered in a memory-only native text view, outside the normal NomadNet browser cache.
- Trusted local public-credential import; no network first-user enrollment or reset.
- Standalone PC NFC CLI. MeshChatX UI integration and PC hardware work deferred after the user requested server/Columba priority while away from the PC.

## Local development

```sh
python -m venv .venv
.venv/bin/pip install -e '.[test]' -r requirements-server.txt
.venv/bin/python -m pytest -q
.venv/bin/python scripts/network_smoke.py
```

Windows uses `.venv\Scripts\python` and `.venv\Scripts\pip`. PC NFC additionally needs `.[pc]` and a PC/SC reader driver. The network smoke test opens a temporary loopback TCP Reticulum listener on port 44221 and uses an ephemeral **software** authenticator. It does not access production content.

See [protocol and threat model](docs/PROTOCOL.md), [integration decisions](docs/INTEGRATION.md), [installation and rollback](docs/OPERATIONS.md), and [hardware checklist](docs/HARDWARE.md). Documentation is prepared for eventual publication; GitHub Pages is not enabled.
