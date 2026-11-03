# Verification status

## Software evidence

- 35 Python tests passed on PiMonitor (Python 3.11), including native cancellation and POSIX file/symlink checks. Earlier Windows run: 32 passed before the final three filesystem tests.
- Tests cover unknown identities, valid/wrong credential, wrong scope/origin/client/link, expired/replayed challenge, missing UP/UV, signature failure, native CTAP software enrollment/authentication, NFC APDU fragmentation, exact 300-second simulated monotonic expiry, Forget me, cloned identities, restart, wall-clock changes, fresh action-bound administration, page/file/media denial, alternate routes/forms, malformed/oversized JSON and global/per-client authentication throttles.
- Real RNS loopback transport smoke passed on Windows and PiMonitor: software FIDO2, unknown denial, cloned-identity separate-link denial, continuous-activity expiry using a three-second configured session, acknowledged Forget me.
- Development systemd service started beside the existing NomadNet/access services; both original services remained active.
- Deployed PiMonitor service: real 300-second session with 276 continuous requests; access was blocked at expiry (observation 301.28 seconds including polling). Fresh authentication then acknowledged Forget me; reconnect stayed denied. Test-only software credential removed.
- External route `mh.beady.com:444`: pinned service discovery and unenrolled denial passed. A separate native software-CTAP2 run read the protected page, restarted the service, and verified old-link and new-link denial. Startup announcements were delayed/repeated to avoid losing them before the TCP uplink is ready.
- Final APK built successfully, verified with apksigner, and installed on an Android API 36 emulator. Its actual UI connected over the external transport, blocked an unauthenticated read, reported NFC unavailable, obtained a server Forget me acknowledgement, and truthfully reported no acknowledgement after the link was already closed. Background/reopen did not restore authority. FLAG_SECURE was verified in window state. Initial emulator system ANR dialogs were dismissed before these checks; no application crash was observed.
- Emulator storage inspection found public service preferences and RNS transport/discovery state, plus upstream initialization databases. No authenticated content/PIN was entered in this emulator test, so this is not proof of post-authentication cache cleanup on physical Android.
- Final server audit: all three services active, original NomadNet PID unchanged, 183 original page files, zero enrolled test credentials, private service-key permissions and backup verified. Selected sensitive markers were absent in 55 journal lines; this bounded check is not a universal log-leak proof.

## Not established by those results

- Physical Flex/YubiKey NFC and true hardware user verification.
- End-to-end Columba physical-device NFC authentication and authenticated-view expiry/cache inspection. See [APK build record](ANDROID_BUILD.md) for the narrower emulator results.
- MeshChatX extension in the installed 4.8.3 UI (deferred at user request).
- Offline Android BLE/LoRa transport integration into the new isolated activity; this version uses TCP Reticulum.
- Existing estate-page migration, executable controls, media-rich rendering or all upstream caching paths. The prototype displays static synthetic content in its own native view.
- Independent cryptographic/security audit, denial-of-service immunity, or erasure of previously captured information.

The first Flex hardware milestone is still pending; software passes must never be presented as hardware passes.
