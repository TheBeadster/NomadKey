# Columba dev19 and Android SMS Server dev27

Development APKs, published 19 November 2026. These replace the older Columba dev9 / Host dev2 download recommendations. They are not official upstream Columba or production releases.

## Downloads and updates

- NomadKey-Columba-2.3.1-beta-dev19.apk: universal Android APK, package network.columba.app.nomadkey.dev, versionCode 20301135, Android 7.0 or newer.
- NomadKey-SMS-Server-0.2-dev27.apk: package org.nomadkey.host.dev, versionCode 27, Android 8.0 or newer.
- SHA256SUMS.txt: exact downloadable APK checksums.

Update the existing matching development app in place. Do not uninstall to work around an update failure: that can erase identities, enrollment and configuration. Both APKs verify with the established development signing certificate, SHA-256 bcb3ce651b9cdb5bf155705144ac2db4e9becd1f527e6404404621e84c3f9e66.

## Validation and limits

- Current backend Python suite: 136 passed, 2 skipped.
- Both APK signatures verified. Server Android lint report: 0 errors, 70 warnings.
- Server dev27 APK exactly matches the installed APK on the Moto test phone by SHA-256.
- Earlier Host dev7 / Columba dev15 records document user-performed Flex registration/login and the S24 autofill check. Those results are not a fresh hardware test of this exact pair.
- S24 USB authorization is currently unavailable; this release does not claim a new physical NFC test or an installed-S24 hash match.
- No-SIM trial: use secure pages and authentication with a working Reticulum connection. No real carrier SMS can arrive without an active receiving SIM and service. Any examples are DEMONSTRATION DATA, not actual SMS or 2FA codes. Real carrier SMS/OTP reception and delivery remain unverified on the no-SIM test phone.

## Source provenance

These APKs come from the existing local development workspaces (host/sms-2fa-dev3 and nomadkey/columba-companion-dev10), which contain uncommitted development changes. The release tag identifies the publication documentation, not a reproducible source snapshot of these APKs. The older main/Columba branch source must not be described as the exact source of these binaries. No private server configuration, identity or authenticator key is included in this release bundle.

Fresh Columba Python-backend JVM test run: 66 tests, 0 failures/errors; Gradle BUILD SUCCESSFUL.
