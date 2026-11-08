# NFC saved addresses

Dev7 adds portable site bookmarks to Columba. A bookmark contains the full
NomadNet destination, its service public key and your label. It is separate from
the credential that logs you into the site. Reading it does not grant access.

## Save your site once

1. Open the genuine site in Columba's NomadNet browser.
2. In the browser overflow menu choose **Save verified site to NFC key**.
3. Check the displayed full destination and public key against your trusted
   administrator's record. Give it a name, such as PiMonitor, and tick the
   verification box. A familiar announce name is not verification.
4. Enter the key's existing FIDO2 PIN and select **Save to key**.
5. Hold the key steadily against the phone. The operation can take up to
   60 seconds. Wait for **Saved and verified**, move the key away, then Continue.

Repeat separately with your backup key. No private login key is exported.
Existing FIDO credentials and the key's NDEF website are not intentionally
changed. This is an actual write to shared authenticator storage, so do not
interrupt it. The app does not reset keys, delete credentials or repair failures
automatically. A failed/interrupted write can leave an incomplete bookmark;
read the key before retrying. It may require trusted key administration.

## Open on a replacement phone

1. Install a genuine NomadKey-enabled Columba build and configure Reticulum.
2. Open Announces, its overflow menu, then **Read NFC saved address**.
3. Enter the FIDO2 PIN and present your own Flex/YubiKey.
4. Move away when prompted and choose the saved site. Columba saves its full
   identity locally and opens that exact destination in the NomadNet browser.
5. Use the existing Authenticate flow, including another NFC tap, to log in.

Future visits can use **Saved NFC sites** without rereading the key. Opening the
same destination through Announces also checks the saved full public key. A
different destination with a copied name cannot replace a saved pin. No route
or no response means failure, never substitution by an announce of the same name.
Bookmark reading works offline; opening the site needs a working mesh route.
The local public pin file is excluded from Android backup.

## Required key capabilities

The implementation checks CTAP2 `rk`, `clientPin`, `pinUvAuthToken`, `largeBlobs`,
`largeBlobKey`, `credBlob` (at least 32 bytes), and `credProtect`. The existing
FIDO2 PIN must be configured. Creation requires user verification and credential
protection level 3. Reads require user presence and verification. Unsupported
keys fail before any write; there is no NDEF or weaker-authentication fallback.

VivoKey's FIDO2 applet source implements these mechanisms. Yubico documents
large blobs on YubiKey 5 firmware 5.7+. This is not proof that any particular
Flex or YubiKey has suitable firmware, configuration or free storage. Actual
dev7 Flex/YubiKey testing is pending. A key can support ordinary NomadKey login
while lacking the extra storage capabilities.

## Format and security boundaries

The fixed, app-controlled RP is `nomadkey-trust.invalid`. Pages and remote nodes
cannot supply its RP ID. Direct native CTAP2 is used; no browser origin, cloud
account or domain validation is required. Each site uses a distinct discoverable
credential with a random user handle. Thus a fresh phone can discover bookmarks
without the old phone's credential IDs.

Canonical CBOR maps `1` to format version 1, `2` to the 16-byte destination,
`3` to the 64-byte Reticulum identity public key, and `4` to the UTF-8 label.
The SDK derives the `nomadnetwork.node` destination from that public key and
rejects mismatches. Records are bounded to 256 bytes and labels to 64 UTF-8 bytes.
The record is encrypted using standard python-fido2 LargeBlobs. Its SHA-256
digest is anchored in the credential's immutable-at-creation 32-byte credBlob.
Changing the mutable blob alone therefore cannot silently change a bookmark.

The app requires a valid checksum, canonical CBOR and bounded shared storage
before writing, preserves unrelated entries, checks capacity before creating a
credential, checks concurrent changes before writing, then reads back and
rediscovers the saved record. Up to 16 bookmarks are supported, subject to the
key's actual space. Shared arrays above 8 KiB or unsupported entries fail closed.
Wrong PINs and writes are never retried automatically. NFC can be lost after a
write has started, so the app cannot promise atomic creation of both credential
and blob. Ambiguous results are failures, not claimed successful imports.

PINs are kept in memory only, passed within the process rather than Intent
extras, and not logged or persisted. PIN and NFC screens block screenshots.
Cancelling, leaving the screen or reaching the monotonic deadline discards the
pending result. Success requires an explicit button; NFC reader mode suppresses
the separate NDEF website until that screen is closed.

This relies on correct initial provisioning, your own physical key, and a
trusted phone and app. Someone with the key and its PIN plus a malicious local
client may delete/recreate bookmark credentials. The digest does not prevent
that. These bookmarks are a portable trust anchor, not a claim of 100% security.
Native NFC discovery is not a remote server-authentication assertion. Reticulum
verifies the opened service, and the existing separate FIDO2 login still grants
only a link-specific session with the server's absolute expiry and Forget me.

References: [VivoKey applet](https://github.com/VivoKey/FIDO2Applet),
[Yubico large blobs](https://docs.yubico.com/yesdk/users-manual/application-fido2/large-blobs.html),
[Yubico credential blobs](https://docs.yubico.com/yesdk/users-manual/application-fido2/cred-blobs.html).
