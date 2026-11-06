# Dev5: an explicit return after the NFC tap

The user reported that the automatic return in the previous build still allowed the Flex website to open too quickly. Code inspection found the removal callback immediately finished the NFC activity. Intermittent RF contact can cause that callback before the user has moved the phone safely away; that mechanism has not been established on physical hardware here.

Dev5 always shows **Key is away — return to site** after a key read. Move the phone away from Flex, then tap this button. Android tag-removal detection only updates the instructions; it no longer returns automatically. Reader mode with `FLAG_READER_SKIP_NDEF_CHECK` remains active during this pause. This uses Android's [NFC reader-mode and ignore APIs](https://developer.android.com/reference/android/nfc/NfcAdapter).

The pending assertion is discarded after 20 seconds. Timeout leaves the NFC screen open with a cancellation message, so it does not automatically release NFC handling while the key may still be present. Move away and close the prompt before retrying. Cancellation or backgrounding still clears pending authorization. No PIN retry occurs automatically.

Install [dev5](https://github.com/TheBeadster/NomadKey/releases/tag/nomadkey-dev5) over Columba NomadKey DEV. No server deployment or re-enrollment is required. The Flex's saved website is unchanged. Holding or re-tapping the key after confirming, cancelling or leaving Columba can still cause Android to open it normally: this is a deliberate handoff, not a global NFC block.

## S24 physical check

1. Open PiMonitor from Announces and start NFC authentication from the fingerprint menu.
2. Read Flex. The prompt must stay open even if contact is briefly lost; the saved website should not open while this prompt remains active.
3. Move the phone well away, then tap **Key is away — return to site**. Check the private page opens and remains in Columba.
4. Repeat, waiting more than 20 seconds before pressing the button: it must cancel and require fresh authentication.
5. Confirm Forget me and the absolute five-minute expiry still deny subsequent access.

The server starts the five-minute lifetime only after successful assertion verification. This update does not relax background revocation or extend challenge/session lifetimes. Physical S24/Flex testing of dev5 remains pending.

## Software verification

- 98 targeted Android tests passed: 5 mocked-NFC activity lifecycle tests, 4 ceremony broker tests, 16 page-cache tests and 73 browser ViewModel tests.
- The handoff tests verify removal does not finish the activity or release an assertion, explicit confirmation completes the handoff, timeout clears the assertion while retaining the screen, backgrounding rejects late callbacks, unavailable removal detection still requires confirmation, and failed authentication produces no assertion.
- Columba feature commit: `0ecae6ac5afc322ffd588de7acd88a476547a92a`.
- Official Columba base: `87b513e60a7b0fce8895f138d11949e4fcfa1e0f`.
- Build: `:app:assembleNoSentryPythonBackendDebug -PcolumbaVersionName=2.3.1-beta-nomadkey.5 -PcolumbaVersionCode=20301040`.
- Package: `network.columba.app.nomadkey.dev`; the backend and SDK wheel are unchanged.

Build and signature verification passed; 98 targeted Android tests passed. Physical dev5 NFC verification remains pending.

APK SHA-256: `5670580e72b9c45dfd5aff88c435ec61832958c1c66ecd47c0f305ac0b6cd35c`.

Signing certificate SHA-256: `bcb3ce651b9cdb5bf155705144ac2db4e9becd1f527e6404404621e84c3f9e66` (unchanged).
