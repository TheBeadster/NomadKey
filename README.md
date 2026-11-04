# NomadKey — development prototype

FIDO2 authorization for short-lived access to a separate NomadNet service, using replaceable Reticulum client identities. No SMS or banking integration.

**Development build.** The user confirmed Android/Flex authentication, five-minute expiry denial and Forget me denial on 4 November 2026. YubiKey and PC hardware remain untested. Existing estate pages remain on their original service. The protected destination now serves live, read-only PiMonitor host status. Follow [status](docs/STATUS.md) for actual checks and outstanding limitations.

## Android download

Get the [NomadKey-enabled Columba development APK](https://github.com/TheBeadster/NomadKey/releases/tag/nomadkey-dev4) and follow the [installation and NFC instructions](docs/ANDROID_DEV4.md). Use dev4 or newer for a Flex that also stores a website. Upgrade the existing Columba NomadKey DEV app in place; existing enrolled keys remain valid. New users still need trusted administrator enrollment and permission: installing this app alone does not unlock a protected site.

The backend, protocol and tests are on this branch. Columba changes are on [columba/nomadkey-development](https://github.com/TheBeadster/NomadKey/tree/columba/nomadkey-development). APKs are development builds with published checksums, not official upstream Columba releases.

## Implemented

- Python FIDO2 verifier and native CTAP2 client using Yubico python-fido2.
- Session authority bound to one identified RNS link, its client public key, service identity, permissions and server lifetime.
- Five-minute absolute server expiry using a monotonic clock; single-use 60-second challenges, fail-closed content checks, Forget me and fresh credential-removal authorization.
- Columba 2.3.1-beta normal Announces and NomadNet browser integration: public login page, fingerprint-menu NFC authentication, normal Micron rendering, countdown and Forget me. Protected content bypasses browser caches, history and tab restoration. Uses Columba's configured Python RNS transport and Android ISO-DEP NFC.
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

The [dev3 Android guide](docs/ANDROID_DEV3.md) describes the normal-browser flow. The older separate development launcher remains available for trusted enrollment.

[Dev4](docs/ANDROID_DEV4.md) fixes the NFC handoff when Flex also stores a website: keep reader mode until the key is removed, then return to the protected page. Background revocation remains enabled.
