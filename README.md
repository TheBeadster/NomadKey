# NomadKey for Columba

**NFC hardware-key authentication for NomadNet pages.**

NomadKey is an addition to Columba. It adds an **NFC key reader** to the fingerprint menu in Columba's NomadNet browser, allowing you to authenticate with a registered **YubiKey or Apex Flex**.

**Want to run your own server?** [Read about the separate Android SMS server](ANDROID-SERVER.md).

## Latest development downloads

| App | Direct APK download |
| --- | --- |
| Columba with NomadKey NFC | [Columba 2.3.1-beta dev19](https://github.com/TheBeadster/NomadKey/releases/download/nomadkey-20261119-dev/NomadKey-Columba-2.3.1-beta-dev19.apk) |
| Android SMS / secure-page server | [NomadKey SMS Server 0.2-dev27](https://github.com/TheBeadster/NomadKey/releases/download/nomadkey-20261119-dev/NomadKey-SMS-Server-0.2-dev27.apk) |

[Release notes and validation limits](https://github.com/TheBeadster/NomadKey/releases/tag/nomadkey-20261119-dev) · [SHA-256 checksums](https://github.com/TheBeadster/NomadKey/releases/download/nomadkey-20261119-dev/SHA256SUMS.txt)

These are development builds, not official upstream Columba or production releases. Update the matching NomadKey development app in place to preserve identities and enrollment; do not uninstall to bypass an update error. The Columba APK is universal, including S24-compatible arm64 support.

You can try the backend server on any old Android phone you have. You only need a SIM if you want to receive and forward SMS 2FA codes.

## What is it for?

An LXMF address identifies a messaging endpoint. It does not prove who is holding the phone. NomadKey adds a separate check using an approved hardware key.

Reticulum securely transports the data; your hardware key proves control of the credential registered with the service. You can use a different trusted phone or a new LXMF address, subject to the server's enrollment and access rules, without treating that address as your password.

## What do I need?

- A NomadKey-enabled development build of Columba and a compatible NFC Android phone.
- A supported FIDO2 NFC key, such as a YubiKey or Apex Flex, enrolled with the service.
- A reachable NomadNet server running the NomadKey authentication backend. An ordinary static NomadNet page alone cannot verify the key and grant access.

Open the server's NomadNet page in Columba. Then open the fingerprint menu, choose NFC and follow the PIN/key prompts. The server checks a fresh cryptographic proof before granting temporary access. The private key stays inside the authenticator. Identify alone does not unlock protected pages.

## Example: SMS 2FA while travelling

The separate [NomadKey Android Server](https://github.com/TheBeadster/NomadKey/blob/main/ANDROID-SERVER.md) can keep your SMS receiving SIM at home and provide authenticated access to codes over Reticulum. This is one use of NomadKey; NFC authentication can protect other private pages too.

You can try the backend server on any old Android phone you have. You only need a SIM if you want to receive and forward SMS 2FA codes.

![NomadKey: NFC authentication, identity independent of the endpoint, and SMS access over Reticulum](docs/images/nomadkey-infographic.png)

This is a NomadKey development addition, not an official upstream Columba release. [View the Columba source and development notes](https://github.com/TheBeadster/NomadKey/tree/columba/nomadkey-development).
