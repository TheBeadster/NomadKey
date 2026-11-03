# Android development build — 3 November 2026

Download from the private [development release](https://github.com/TheBeadster/NomadKey/releases/tag/nomadkey-dev1). Keep normal Columba installed. Open the additional **NomadKey DEV** launcher, not the ordinary Columba launcher.

- File: `NomadKey-Columba-2.3.1-beta-dev1.apk` (universal ABI, 133412476 bytes).
- Package: `network.columba.app.nomadkey.dev`.
- Version: `2.3.1-beta-nomadkey.1-nomadkey-dev`; versionCode `20301002`.
- APK SHA-256: `35e9ac0bfebb9c313462a0588b80e8c99589a6b23cbe4b67110d6f17c5dc16cf`.
- Verified APK v2 signature; RSA 2048 **Android Debug** certificate, not upstream Columba's production signature.
- Signing certificate SHA-256: `bcb3ce651b9cdb5bf155705144ac2db4e9becd1f527e6404404621e84c3f9e66`.
- Columba feature commit: `03accc75c1c33dd27b79ed122339fbaea9f9e125`, [private branch](https://github.com/TheBeadster/NomadKey/tree/columba/nomadkey-development).
- Official selected base: `87b513e60a7b0fce8895f138d11949e4fcfa1e0f` (`v2.3.1-beta`). Stable/main comparison is recorded in [integration](INTEGRATION.md).
- NomadKey source: `2f923f04660daccc7d3a9f0eab8cd34949752cb2`; embedded SDK `0.1.0.dev1`, wheel SHA-256 `5810ece06ecb885f592ce8ddd29abef6016e83cc9fc8edcef38bb75e36b64a28`. All 11 packaged Python sources compared to repository sources.
- Build variant: `noSentryPythonBackendDebug`, JDK 21, Android SDK 36, Gradle 9.4.1. Final Gradle result: BUILD SUCCESSFUL, 2m40s after cold dependency build.

The test build includes an uncommitted **public** service preset for `mh.beady.com:444`:

Destination: **aadad40f**40938abef7ab0ef44956**6bcf**

Full destination: `aadad40f40938abef7ab0ef449566bcf`

Public service key: `e7c6236630297641f8c517b79f7c6e62b5422d83b5814ae9bda170732565bd677371764044c87710a1eaed5e3faa3dc61d70a391bcbab369b0d04eb67d7538c9`

This is a separate synthetic-page destination through PiMonitor's existing transport. Its private identity remains only on PiMonitor and in its secure local backup. No existing page or user identity is imported into this APK. Verify the full pin; abbreviated checks are not full-address assurance.

## Observed runtime checks

API 36 emulator installation and launch succeeded. UI readback verified the preset, successful external RNS connection, unauthenticated page denial, NFC-unavailable handling, server-acknowledged Forget me and truthful unacknowledged revocation after disconnection. Background/reopen did not restore authority; window state included SECURE. This was not an NFC test and did not authenticate a human credential. See [hardware checklist](HARDWARE.md).

The server currently has **no enrolled human credentials**. In the app, connect, enroll the physical Flex with its existing FIDO2 PIN, export the public enrollment bundle, then import it through trusted PiMonitor administration before authentication can grant access. Do not send the PIN. Repeat enrollment separately for the backup key. The app does not configure or reset a FIDO2 PIN.
