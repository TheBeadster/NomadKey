# Environment and integration decisions

Inspection: 3 November 2026.

## PiMonitor

Live process inspection found `nomadnet-intranet.service` running NomadNet 0.9.11 and RNS 1.2.0 in `/home/dadmin/nomadnet-intranet-venv`, plus `betchton-nomadnet-access.service`. The first invokes `betchton_nomadnet_site/access/secured_nomadnet.py` with `.nomadnetwork-intranet` and `.reticulum`. Access-control drop-in: `50-access-control.conf`. There were 183 files under the page tree and zero files under the separate file tree. A TCP Reticulum hub listens on 444. No running MeshChatX process/service or active MeshChatX checkout was found in the inspected locations; historical MeshChatX backup/helper names exist. This is a correction to the initial assumption, not proof that no other installation exists anywhere.

NomadKey uses its own virtual environment, service identity, RNS config/cache, public credential file and systemd unit. It connects to the existing hub through loopback TCP 444. It does not share the older RNS process's Python runtime, identity or private content. The original services were not restarted for installation.

## PC

Packaged Electron MeshChatX 4.8.3, bundled Python 3.14, installed in the user's Local Programs directory. The changelog and backend manifest establish the packaged version/build context, not a source checkout. Upstream `v4.8.3`: `977c7ad3c2df61fdc2ae9b92fbf2823cab0943e8`. Inspected upstream master: `83670eed8ffbf77847abf7e6b4a9bb5b0250af15`.

Current upstream supports worker frontend plugins and in-process Python backend plugins. A plugin is preferred to a fork, but that current Python plugin interface is not present at the same source path in installed 4.8.3; it must not be assumed available unchanged. The frozen PC package lacks the new FIDO2 dependencies. A separately installed native helper or maintained app build is needed. No patch or upgrade was made to the installed application. PC/SC enumerated an ACS ACR1252 PICC reader and SAM reader. No NFC key was exercised.

Normal MeshChatX NomadNet browser code caches links and supports archives/browser state. Protected pages must stay outside its general archive/history paths unless every persistence path is explicitly amended and tested. The standalone PC native client is implemented; the user subsequently prioritized server and Columba while away from the PC, so the MeshChatX UI extension remains deferred.

## Columba bases

- Official repository: https://github.com/torlando-tech/columba
- Latest stable release inspected: `v2.2.6`, `a402ed1052ba6993454352ce51ddfc336b729d9f`.
- Main inspected: `245eeaf4236c6a35426b0d427c9733a86a52cb8e`.
- User's installed version and selected base: `v2.3.1-beta`, `87b513e60a7b0fce8895f138d11949e4fcfa1e0f`.
- Feature branch: `nomadkey/development`; no upstream issue/comment/PR submitted.
- Python backend uses Columba's pinned torlando-tech Reticulum fork `754654fe8cbca180c784e9274d033cb3ce229312` (1.5.2), preserving its Android compatibility fixes rather than introducing a different stack. Pi/PC use upstream RNS 1.5.7.

The development APK has a separate package suffix `.nomadkey.dev`, a Columba DEV label, and an additional `NomadKey DEV` launcher entry. Its activity runs in a separate process and skips ordinary Columba identity initialization. It uses the reusable NomadKey wheel, python-fido2, and Android `IsoDep` transport. It does not import the usual identity. No-Sentry build; heap snapshot tooling removed. It uses native text views, no WebView, browser history, NomadNetPageCache, tab restoration or form resubmission. Leaving the view clears it and requests revocation; FLAG_SECURE prevents normal Android screenshots/recents capture, without promising protection from a compromised OS or external camera.

This first client connects to a configured TCP Reticulum transport with an editable port. It does not yet reuse the normal Columba BLE/LoRa interface manager. The user supplied `mh.beady.com:444`; the existing public route was verified with service discovery and unenrolled denial. No firewall/forwarding change was made by this project.

## FIDO API choices and sources

- [python-fido2](https://developers.yubico.com/python-fido2/) provides native CTAP2 client, PIN protocols and verifier; [PCSC implementation](https://github.com/Yubico/python-fido2/blob/main/fido2/pcsc.py) supports NFC readers. Pinned 2.2.1.
- [WebAuthn](https://www.w3.org/TR/webauthn-3/) requires browser origin/RP validation. A Reticulum destination is not automatically a secure browser origin. No browser `navigator.credentials` assumption is made.
- [Android Credential Manager](https://developer.android.com/identity/sign-in/credential-manager) and platform FIDO APIs are distinct from raw NFC CTAP2, and have platform/provider and RP association models. They are not used for the offline synthetic namespace.
- [YubiKit Android](https://github.com/Yubico/yubikit-android) was considered; its vendor-specific device discovery must not be assumed compatible with an Apex applet. This prototype uses Android ISO-DEP and Yubico's generic python-fido2 CTAP/PIN stack instead. The APDU transport is small, bounded and software-tested, but actual Apex/YubiKey interoperability is unverified.

No Google/Apple sign-in, central authorization server, synchronized passkey or DNS validation is silently required.
