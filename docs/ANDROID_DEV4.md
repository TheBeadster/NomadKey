# Dev4: keep NFC ownership until the key is removed

The S24 user confirmed dev3 authenticates in the normal NomadNet browser, but the Flex's stored website opened in the default browser immediately afterwards. That app switch correctly triggered background revocation. Code inspection found the NFC activity finished immediately after CTAP, releasing reader mode while the multi-application Flex could still be in range. Android could then dispatch its NDEF URL.

Dev4 retains reader mode with `FLAG_READER_SKIP_NDEF_CHECK` after the key read. It displays **Move your phone away from Flex (or remove your YubiKey)** and calls Android's [`NfcAdapter.ignore`](https://developer.android.com/reference/android/nfc/NfcAdapter#ignore(android.nfc.Tag,int,android.nfc.NfcAdapter.OnTagRemovedListener,android.os.Handler)) with a one-second removal debounce. Only after the removal callback does the one-use memory broker release the assertion and return to Columba for server verification. The server's five minutes still begin at successful verification, never at a tap or refresh.

If Android cannot register removal detection (including an already removed tag), reader mode stays active and an explicit **Key is away — return to site** button appears. Move the key away before pressing it. Waiting is bounded at 20 seconds; timeout, cancellation or backgrounding discards the staged assertion. The existing challenge expiry is unchanged. There is no automatic PIN retry and no change to the Flex's stored website.

Background logout remains enabled. This fix does not whitelist the browser or extend sessions. Re-tapping the Flex after reader mode ends can still open its saved URL normally. Android documents limitations for changing/random tag UIDs and intermittent RF contact; actual S24/Flex removal behavior must be tested physically.

## Installation and physical check

Install [dev4](https://github.com/TheBeadster/NomadKey/releases/tag/nomadkey-dev4) over the existing development app. No server update or re-enrollment is needed.

1. Open **Announces > PiMonitor | NomadKey**, then **Fingerprint > Authenticate with NFC key**.
2. Enter the existing FIDO2 PIN and hold the phone at Flex until the prompt says the key was read.
3. Move the phone away. Columba should return to the private page without opening the saved website. If prompted, confirm the key is away.
4. Verify both absolute expiry and Forget me still block further access. Deliberately backgrounding Columba should still revoke access.

The change uses the same backend and SDK wheel as dev3. Source/build identifiers, signature and test outcomes are recorded with the release. Software lifecycle tests simulate Android removal callbacks; they do not establish physical NFC compatibility.

## Build and verification record

- APK: `NomadKey-Columba-2.3.1-beta-dev4.apk`, 133452456 bytes; package `network.columba.app.nomadkey.dev`, version code `20301030`, name `2.3.1-beta-nomadkey.4-nomadkey-dev`.
- APK SHA-256: `2d0386528dcdc280bf4fcfeadaa1e5cc76bf2dae75f81a7300e10cf14ce6d691`.
- Verified signing certificate SHA-256: `bcb3ce651b9cdb5bf155705144ac2db4e9becd1f527e6404404621e84c3f9e66` (unchanged).
- Columba feature commit `93c7de527a2e79aa749c5f854b5feb6f0e952545`; implementation commit `d112ea57a003c86a393adfebf55682c1fc266628`; official base `87b513e60a7b0fce8895f138d11949e4fcfa1e0f`.
- Build: `:app:assembleNoSentryPythonBackendDebug -PcolumbaVersionName=2.3.1-beta-nomadkey.4 -PcolumbaVersionCode=20301030`.
- **98 targeted Android tests passed**: 5 real-activity lifecycle tests under Robolectric with mocked NFC, 4 ceremony broker tests, 16 page-cache tests and 73 browser ViewModel tests.
- The NFC tests verify no result/reader release before removal, pause rejecting a late callback, timeout cancelling instead of authorizing, explicit confirmation when removal detection is unavailable, and failed CTAP returning no assertion after removal.
- No new emulator or physical NFC pass is claimed. The signed build and software tests passed; the user must confirm the actual S24/Flex interaction. Server state, enrolled credentials, live sessions and existing site content were not changed for this fix.
