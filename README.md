# NomadKey — development prototype

**Use your key to prove you have access, whatever phone or computer you use.**

Think of a Reticulum endpoint ID as the name your app uses on the network. It helps the site recognise the connection, but it does **not** prove which person is holding the phone. It is not a permanent label for the physical device either: you can create a new identity or move one between devices.

NomadKey adds a second check using a **FIDO2 security key**, such as a VivoKey Flex or YubiKey. The site asks your key to prove it is one the administrator has already approved. You use the key and its PIN to answer. The secret inside the key never leaves it.

That means **your access follows your security key, not your endpoint ID**. You can use your own phone, a borrowed phone, or a new temporary Reticulum identity. You do not need to copy your usual identity onto that device. The site recognises the approved key and gives that connection access to the pages you are allowed to read.

For example: borrow a phone with the NomadKey-enabled Columba app, open the site, authenticate with your Flex, and read your private pages. Access ends after five minutes by default, even if you keep browsing. Tap **Forget me** to end it sooner. A different connection must authenticate for itself.

The key proves that you can use an approved credential; the administrator decides whose key it is and what it may access. NomadKey currently protects NomadNet pages. SMS and banking features are outside this prototype.

**Development build.** The user confirmed Android/Flex authentication, five-minute expiry denial and Forget me denial on 4 November 2026. YubiKey and PC hardware remain untested. Existing estate pages remain on their original service. The protected destination now serves live, read-only PiMonitor host status. Follow [status](docs/STATUS.md) for actual checks and outstanding limitations.

## Android download

Get the [NomadKey-enabled Columba development APK](https://github.com/TheBeadster/NomadKey/releases/tag/nomadkey-dev7) and follow the [installation and NFC instructions](docs/ANDROID_DEV7.md). Use dev6 or newer for a Flex that also stores a website. Upgrade the existing Columba NomadKey DEV app in place; existing enrolled keys remain valid. New users still need trusted administrator enrollment and permission: installing this app alone does not unlock a protected site.

The backend, protocol and tests are on this branch. Columba changes are on [columba/nomadkey-development](https://github.com/TheBeadster/NomadKey/tree/columba/nomadkey-development). APKs are development builds with published checksums, not official upstream Columba releases.

## Implemented

- Python FIDO2 verifier and native CTAP2 client using Yubico python-fido2.
- Session authority bound to one identified RNS link, its client public key, service identity, permissions and server lifetime.
- Five-minute absolute server expiry using a monotonic clock; single-use 60-second challenges, fail-closed content checks, Forget me and fresh credential-removal authorization.
- Columba 2.3.1-beta normal Announces and NomadNet browser integration: public login page, fingerprint-menu NFC authentication, normal Micron rendering, countdown and Forget me. Protected content bypasses browser caches, history and tab restoration. Uses Columba's configured Python RNS transport and Android ISO-DEP NFC.
- NFC saved-site read/write flow, portable full destination/public-key pins and a Saved NFC sites menu. Requires compatible protected FIDO2 storage; physical bookmark tests pending. See [NFC bookmarks](docs/NFC_BOOKMARKS.md).
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

[Dev6](docs/ANDROID_DEV6.md) keeps NFC reader mode active until you move the key away and explicitly confirm the return to the site. Background revocation remains enabled.

