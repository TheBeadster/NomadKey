# NomadKey Android Server

**Keep your SMS receiver at home. Use your hardware key to access private pages wherever you have a Reticulum connection.**

NomadKey Host turns a spare Android phone into a secure NomadNet page server and SMS receiver. It works with the separate NomadKey addition to Columba, which supplies the NFC key reader. The server handles authentication, permissions and protected content.

## Two separate parts

| Item | Purpose |
| --- | --- |
| [NomadKey for Columba](https://github.com/TheBeadster/NomadKey/tree/columba/nomadkey-development) | Adds NFC hardware-key authentication to Columba's NomadNet browser. |
| NomadKey Android Server (this project) | Hosts protected pages, verifies hardware-key proofs and provides access to Android-visible SMS. |

An LXMF address identifies a messaging endpoint; it does not prove which person is using it. Reticulum provides encrypted transport. Your registered YubiKey or Apex Flex authenticates you to NomadKey by proving control of an approved credential. A different trusted phone or a fresh LXMF address can be used, subject to the server's enrollment and access rules. The hardware key's private key stays inside it.

## Why I developed it

I travel a lot and now keep my authenticator credentials and passkeys on a YubiKey. If my phone breaks, gets lost or is stolen, I still have those credentials on my separate key.

SMS 2FA is more awkward. If I lose my SIM while abroad, getting a replacement can take a long and inconvenient time. SIM swapping is another concern.

My solution is to keep the SIM used for SMS 2FA safely at home in an old Android phone dedicated to receiving messages and making them available over Reticulum to authenticated endpoints. Services must send their codes to that SIM's number instead of the SIM in my everyday phone.

The published Host dev2 build lets authenticated users read Android-visible SMS on protected pages. Registered endpoints can receive sender/time alerts, without the message body or login code. Access expires after five minutes even while browsing; Forget me ends it sooner.

## Try secure pages without a SIM

**A SIM is not required to try secure NomadNet pages and NFC authentication.** Use a working Reticulum connection, enroll an approved key and test opening a protected page through NomadKey-enabled Columba. Try expiry and Forget me too.

**Without a SIM, this server cannot receive real carrier SMS.** No-SIM testing demonstrates secure-page access and authentication, not carrier SMS reception or real 2FA delivery. Any sample messages used in a walkthrough must be clearly labelled **DEMONSTRATION DATA — not a real SMS or 2FA code**. A no-SIM trial is not a claim that this build has a sample-message generator.

## How it fits together

![NomadKey: NFC authentication, identity independent of the endpoint, and SMS access over Reticulum](docs/images/nomadkey-infographic.png)

The infographic is a conceptual overview. Real SMS requires an active receiving SIM and mobile service. Android may restrict access to OTP messages. Hardware, carrier reception and delivery need checking separately on the actual devices. Keeping the SIM at home does not prevent a carrier-side SIM swap. Reticulum needs a working route, and delivery before a code expires is not guaranteed.

This remains a development project. Use a trusted client phone and app, verify the genuine service, and keep a separately enrolled backup key.

## Android download

For the published development server, use the [Android Host setup guide](docs/ANDROID-HOST.md). The downloads below are development builds; hardware, carrier SMS and alert delivery require testing on your actual devices.

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

