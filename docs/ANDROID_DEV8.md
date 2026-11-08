# Dev8: automatic NFC sharing or protected storage

Upgrade the existing Columba NomadKey DEV app with
[dev8](https://github.com/TheBeadster/NomadKey/releases/tag/nomadkey-dev8).
No server change or login-key enrollment is required.

## Save a site

Open the site, then browser overflow **Save site to NFC → Detect and save**.
Present the card, sticker, Flex or YubiKey:

- **Normal NFC tag:** a blank, writable NDEF tag gets the public landing-page
  address without a PIN. The app reads it back before showing Success. Move the
  tag away and press Continue. You can give this tag to someone else.
- **FIDO security key:** the app shows Security key detected. Move away, press
  Continue, verify the full site identity and enter the existing FIDO2 PIN.
  Present the key again to save using the existing protected bookmark mechanism.

FIDO detection takes priority when a key also contains an NFC website. The
ordinary writer never falls back to NDEF after a FIDO error or an ambiguous
probe. The FIDO storage capability checks and verification remain those of dev7.

## Read a tag or key

Choose **Announces → overflow → Read NFC address** and present it.

- A normal shared tag displays **Shared address — not verified** and its full
  destination. Move away and press Open site. It opens the normal NomadNet
  landing page. No PIN is needed just to read this public address.
- A FIDO key is detected first, then uses the existing PIN-protected read flow
  with a second tap. The imported full identity remains a trusted bookmark.

**Saved NFC sites** still lists the protected bookmarks imported from FIDO keys.
Reading an ordinary shared tag never adds to that list, replaces a trusted
identity, authenticates the user or grants protected access. Protected pages
still require an enrolled FIDO2 key and PIN. The five-minute absolute session
expiry and Forget me are unchanged.

## Tag format and limitations

The public record is a standard NDEF URI:
`nomadnetwork://<32 lowercase hex destination>:/page/index.mu`.
It contains no name, credential, public-key pin, token, private-page path,
query, fragment or form data. The one-record message fits within 137 NDEF bytes.
The reader accepts only this landing-address format, a single URI record and a
maximum 256-byte NDEF message. Alternate schemes, paths and extra records fail.

Use a compatible, already NDEF-formatted blank tag with sufficient capacity.
This release does not format unformatted chips, erase other data, permanently
lock tags or change tag passwords. Existing website or different-address data
is refused. An identical address is read back without rewriting. Not every
contactless chip supports NDEF, and not every security key supports the protected
bookmark extensions.

There is a 30-second monotonic detection/public-tag window and no automatic
write retry. An interrupted write may be incomplete: read the tag before
retrying. The result screen retains reader mode until you explicitly close it;
move away first. Leaving the activity cancels pending results and closes I/O.

The supported read entry is the in-app menu, not an assurance that tapping a
tag while Columba is closed will launch it on every Android version. Opening a
site needs a working Reticulum route; reading the address does not.

For ISO-DEP tags, the detector sends only the standard SELECT FIDO application
APDU (the same selection used by the existing SDK). Success routes to protected
storage, including older FIDO applets which may subsequently fail its capability
checks. Only explicit application-not-found permits ordinary NDEF handling.
Uncertain responses or contact loss cause failure without a public write.

Shared tags are public links, not proof of who handed them out. An attacker can
replace a physical tag with a different address. Existing trusted pins still
apply when that exact destination is opened; the public reader does not change
them. For a portable trusted identity, use the FIDO bookmark path.

Android references: [NDEF read/write API](https://developer.android.com/reference/android/nfc/tech/Ndef)
and [foreground reader mode](https://developer.android.com/reference/android/nfc/NfcAdapter).

## Physical checklist — dev8 pending

1. Write a blank NDEF card from Save site to NFC. Confirm no PIN prompt and a
   successful readback. Read it from Announces and open the public site.
2. Confirm reading the card does not authenticate or add a trusted bookmark.
3. Present Flex/YubiKey to the same Save action. Confirm security-key detection
   and a PIN request before protected writing. Check the separate NFC website
   and existing FIDO login still work.
4. Check an occupied tag is refused and its data remains intact. Check a
   read-only tag can be read but cannot be newly written.
5. Authenticate normally and confirm expiry and Forget me still deny access.

No dev8 physical NFC tests have been performed by the agent. Simulated tests
cannot prove compatibility with a particular chip or phone antenna behavior.

## Build and software checks

136 targeted Android tests passed: 21 public-tag/detection tests, 10 protected
bookmark tests, 11 existing authentication NFC activity/transport tests,
4 ceremony handoff tests, 16 cache tests and 74 browser ViewModel tests. All
passed without skips. NDEF and ISO-DEP transports are simulated. Cases cover
FIDO priority over existing NDEF websites, failed/ambiguous detection with no
fallback, normal Type 4 tags, malformed/multiple/oversized records, unwanted
paths or queries, blank/read-only/full/occupied tags, lost writes, readback
mismatch, explicit Open, timeout and unchanged trusted pins.

Official Columba base: `87b513e60a7b0fce8895f138d11949e4fcfa1e0f`.
Feature source: `7c915a47eadfeba8552c4da1594aac9677a377c9`.
The Python SDK remains `0.1.0.dev7`, with the wheel documented in dev7.

Package: `network.columba.app.nomadkey.dev`.
Version: `2.3.1-beta-nomadkey.8-nomadkey-dev`; version code `20301070`.
Build with `:app:assembleNoSentryPythonBackendDebug
-PcolumbaVersionName=2.3.1-beta-nomadkey.8 -PcolumbaVersionCode=20301070`.

APK build, package/version and signature verification passed.

APK SHA-256: `54fbbb52ff6a26dde8ff2358e5ad8c7324c4ab13b753194b1af6dd8c1e0afc15`.

Signing certificate SHA-256: `bcb3ce651b9cdb5bf155705144ac2db4e9becd1f527e6404404621e84c3f9e66` (unchanged).

All 21 sharing/detection tests also passed in a second regression run.
