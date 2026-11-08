# Dev7: read and save NFC site addresses

Install [dev7](https://github.com/TheBeadster/NomadKey/releases/tag/nomadkey-dev7)
over the existing Columba NomadKey DEV app. No PiMonitor update or login-key
re-enrollment is required. This is a development build, not an official Columba
Play Store release.

## New menus

- **Announces → overflow → Read NFC saved address** reads your key and opens
  the selected site in the normal NomadNet browser.
- **Announces → overflow → Saved NFC sites** opens a previously imported site.
- **NomadNet browser → overflow → Save verified site to NFC key** stores the
  current site's full identity on your key after your explicit verification.

Save requires your existing FIDO2 PIN and creates a separate discoverable
bookmark credential. Read requires the PIN but creates nothing. Both use a
60-second NFC window, a progress indicator and an explicit result button.
Move the phone away from the key before pressing Continue/Open. Writes and
wrong PINs are never automatically retried.

The site login flow remains the dev6 flow: 15 seconds, retry after brief contact
loss, Success/Continue or Failed/Try again. Reading a bookmark does not log in.
The site still applies its absolute five-minute expiry and Forget me.

See [the complete provisioning guide and security model](NFC_BOOKMARKS.md).
Your actual Flex/YubiKey must support the checked CTAP storage features. If
unsupported, the app reports failure without writing. An interrupted save can
leave an incomplete bookmark; read/inspect the key before retrying. Do not reset
your authenticator to resolve this: that would destroy unrelated credentials.

## S24 hardware checklist — pending

1. Open the already verified PiMonitor site. Save it as PiMonitor after checking
   the full identity. Confirm the key reports Saved and verified.
2. Read it from Announces and check the exact full destination opens. The
   bookmark should work without the original client Reticulum identity.
3. Authenticate normally with Flex, then confirm expiry and Forget me deny
   access. Check the separate NFC website does not open while the NFC result
   screen is displayed.
4. Confirm the original FIDO2 login still works and the existing NFC website
   remains intact. Save/read your backup YubiKey separately if supported.
5. Try Saved NFC sites without tapping the key; it should open the public site,
   with authentication still required for protected content.

Do not deliberately interrupt a hardware write as an initial test. Interruption
and malformed-data behavior have software tests; recovery can require trusted
key administration. No physical dev7 NFC save/read has been performed by the
agent. Earlier user-confirmed login tests do not establish bookmark compatibility.

## Reproducibility

Official Columba base: `87b513e60a7b0fce8895f138d11949e4fcfa1e0f`.
Columba feature commit: `2e1f022097e20bb3ddff92f11dc423946d8ee46d`.
SDK source commit: `1990ab124b5c495638e6cff77269056c17074ed0`.
SDK wheel SHA-256: `34bba21add0bf89c746c1415cb06a8abeeae9429e529dc856dfb1f735422a73f`.

Package: `network.columba.app.nomadkey.dev`.
Version: `2.3.1-beta-nomadkey.7-nomadkey-dev`, version code `20301060`.

Build:
`./gradlew :app:assembleNoSentryPythonBackendDebug -PcolumbaVersionName=2.3.1-beta-nomadkey.7 -PcolumbaVersionCode=20301060`.

The SDK unit suite passed: 68 passed, 2 skipped. The real-RNS software smoke
test passed unknown-client denial, software FIDO2 login, cloned-identity link
denial, continuous-activity expiry and acknowledged Forget me. It uses synthetic
credentials and does not exercise physical NFC.

The Android run passed 135 targeted tests: 20 Python-backend link/route tests,
10 bookmark UI/persistence tests, 11 existing NFC activity/transport tests,
4 ceremony handoff tests, 16 page-cache tests and 74 browser ViewModel tests.
No failures, errors or skips occurred in that Android run. The UI tests use
Robolectric and simulated NFC, including cancellation, timeout, explicit result
buttons, name/key conflicts, corrupt local pins and cached-page bypass.

APK build and signature verification passed. Signing certificate is unchanged from dev6.

APK SHA-256: `8b774317146defccb5cfd6701f906cb20354ad106b97eacf8130df0e39bcace2`.

Signing certificate SHA-256: `bcb3ce651b9cdb5bf155705144ac2db4e9becd1f527e6404404621e84c3f9e66`.
