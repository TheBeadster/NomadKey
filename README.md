# NomadKey: your security key opens your private pages

**Keep your private information at home. Use your key to read it from another trusted phone.**

Imagine a locked cupboard. You can see its door, but you need the right key to
open it. NomadKey puts a door like that in front of private NomadNet pages.
Your Flex or YubiKey is the key. You tap it, enter its PIN, and the site checks
that it is a key the owner has approved. The secret inside the key never leaves it.

Why is this useful? A network address tells the site which app is talking to it.
It does not prove which person is holding the phone. NomadKey adds a separate
check using your security key. Your access follows your approved key, so you can
use a different trusted phone or a fresh network identity without copying your
usual identity onto that phone.

For example, leave a spare phone at home with **NomadKey Host** installed. Use
**Columba** on the phone you carry to visit it. After you use your key, you can
read a private page or the text messages that Android makes available on the
home phone. Access closes after five minutes, even if you keep reading.
**Forget me** closes it sooner.

You can also ask for a small alert when a text arrives. It tells you who sent it
and when, but leaves out the message and any login code. The Host can warn about
a missing SIM or lost service too. That is a warning to check the phone, not
proof of a stolen phone number.

The aim is simple: **let an approved key unlock temporary access, without making
a permanent network identity your password.** You still need a trustworthy phone
and app, and you must check that you opened the genuine site.

This is a **development project**. Some Android phones hide login-code messages.
The new Host app still needs real-phone NFC, SMS and alert tests. Banking
integration is not included. The technical explanation and test details follow below.

## Android download

**New Android Host experiment:** turn a spare NFC Android phone into a secure page server or SMS relay. [Download Host dev2](https://github.com/TheBeadster/NomadKey/releases/tag/nomadkey-host-dev2). See [setup, platform limits and physical test checklist](docs/ANDROID-HOST.md) and [dev2 changes and checks](docs/HOST-DEV2.md). This is a separate app, with a new service identity and new key enrolment; it does not change PiMonitor.

Get the [NomadKey-enabled Columba development APK](https://github.com/TheBeadster/NomadKey/releases/tag/nomadkey-host-dev1) and follow the [installation and NFC instructions](docs/ANDROID_DEV8.md). Use dev6 or newer for a Flex that also stores a website. Upgrade the existing Columba NomadKey DEV app in place; existing enrolled keys remain valid. New users still need trusted administrator enrollment and permission: installing this app alone does not unlock a protected site.

The backend, protocol and tests are on this branch. Columba changes are on [columba/nomadkey-development](https://github.com/TheBeadster/NomadKey/tree/columba/nomadkey-development). APKs are development builds with published checksums, not official upstream Columba releases.

## Technical explanation

Reticulum provides authenticated encrypted transport. FIDO2 separately proves control of an enrolled credential; the administrator assigns its permissions. A session is bound to the genuine service, the requesting link and client public key, a fresh challenge, permitted actions and an absolute expiry. It is not a general identity allowlist.

## Implemented

- Python FIDO2 verifier and native CTAP2 client using Yubico python-fido2.
- Session authority bound to one identified RNS link, its client public key, service identity, permissions and server lifetime.
- Five-minute absolute server expiry using a monotonic clock; single-use 60-second challenges, fail-closed content checks, Forget me and fresh credential-removal authorization.
- Columba 2.3.1-beta normal Announces and NomadNet browser integration: public login page, fingerprint-menu NFC authentication, normal Micron rendering, countdown and Forget me. Protected content bypasses browser caches, history and tab restoration. Uses Columba's configured Python RNS transport and Android ISO-DEP NFC.
- Automatic NFC type detection: normal blank NDEF tags share a public site address without a PIN; FIDO keys use the existing PIN-protected bookmark flow. Shared tags never replace trusted pins. See [dev8](docs/ANDROID_DEV8.md).
- NFC saved-site read/write flow, portable full destination/public-key pins and a Saved NFC sites menu. Requires compatible protected FIDO2 storage; see [status](docs/STATUS.md) for hardware coverage. See [NFC bookmarks](docs/NFC_BOOKMARKS.md).
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

