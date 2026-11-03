# Hardware acceptance checklist

No item here is marked passed until observed on hardware.

## Android first (user currently away from PC)

1. Install the separately named, checksum-verified development APK; keep normal Columba 2.3.1-beta installed.
2. Open **NomadKey DEV**. The user's test build presets the existing `mh.beady.com:444` transport and public service pin. Both host and port remain editable. This project did not change port forwarding or firewall configuration.
3. Verify/pin the full service destination and public key from the trusted administration record. Confirm a wrong key/destination is rejected.
4. Enroll Flex with UV/PIN, export only the public bundle, and have it explicitly imported through local PiMonitor administration. Repeat separately for the backup YubiKey. Do not keep retrying an incorrect PIN.
5. Before authentication, verify the test page remains denied. Authenticate using NFC and read the synthetic page.
6. Refresh repeatedly across the full five-minute boundary. The view must clear, existing links must be denied, and refresh must not renew authority.
7. Authenticate again, select **Forget me**, and check the explicit server acknowledgement; further reads must fail.
8. Repeat Forget me while disconnected: view clears, acknowledgement must say **not acknowledged**, and server expiry still applies.
9. Background/reopen, kill/restart, reconnect and create another temporary identity: no silent restoration. Verify no page/PIN/assertion appears in app files, recents, normal browser history or logs.
10. Test both Flex and YubiKey independently. Note reader/phone model, OS, applet version, PIN/UV support, timing and errors without recording PINs.

## PC later

- ACS ACR1252 PICC reader was enumerated; SAM is not the NFC card reader.
- Use the native python-fido2 PC/SC flow, not an assumption that Electron WebAuthn accesses NFC.
- Test enrollment and authentication with each physical key, correct and cancelled PIN entry, removal mid-ceremony, timeout and deliberate authentication cancellation.
- Complete the MeshChatX extension compatibility work before claiming the original PC UI milestone. The CLI and reader enumeration are not that milestone.
- Verify the same five-minute activity/Forget me checks in the actual protected UI, including archive/history/tab restoration inspection.

Already copied, photographed or recorded content cannot be erased by logout.
