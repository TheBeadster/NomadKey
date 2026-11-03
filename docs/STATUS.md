# Verification status

## Software evidence

- 31 Python tests passed on Windows and PiMonitor (Python 3.11).
- Tests cover unknown identities, valid/wrong credential, wrong scope/origin/client/link, expired/replayed challenge, missing UP/UV, signature failure, native CTAP software enrollment/authentication, NFC APDU fragmentation, exact 300-second simulated monotonic expiry, Forget me, cloned identities, restart, wall-clock changes, fresh action-bound administration, page/file/media denial, alternate routes/forms, malformed/oversized JSON and global/per-client authentication throttles.
- Real RNS loopback transport smoke passed on Windows and PiMonitor: software FIDO2, unknown denial, cloned-identity separate-link denial, continuous-activity expiry using a three-second configured session, acknowledged Forget me.
- Development systemd service started beside the existing NomadNet/access services; both original services remained active.

## Not established by those results

- Physical Flex/YubiKey NFC and true hardware user verification.
- End-to-end Columba installed-device interaction; APK build/runtime evidence is recorded separately when complete.
- MeshChatX extension in the installed 4.8.3 UI (deferred at user request).
- Offline Android BLE/LoRa transport integration into the new isolated activity; this version uses TCP Reticulum.
- Existing estate-page migration, executable controls, media-rich rendering or all upstream caching paths. The prototype displays static synthetic content in its own native view.
- Independent cryptographic/security audit, denial-of-service immunity, or erasure of previously captured information.

The first Flex hardware milestone is still pending; software passes must never be presented as hardware passes.
