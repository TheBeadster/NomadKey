# Dev6: clear NFC progress and contact-loss retries

Install [dev6](https://github.com/TheBeadster/NomadKey/releases/tag/nomadkey-dev6) over the existing Columba NomadKey DEV app. No server update or key enrollment is needed.

## What you will see

1. **Present key**: hold Flex or YubiKey against the phone. The attempt has one 15-second window, starting when the prompt opens.
2. **Authenticating…** and a progress bar appear when a key is detected. The bar shows elapsed time within the attempt, not a percentage of cryptographic work completed.
3. If NFC contact briefly drops, the prompt stays open and asks you to hold the key against the phone again. A new NFC detection retries the read within the original window. Bounces do not restart the clock.
4. **Success** and **Continue** mean the key read succeeded. Move the phone away, then press Continue. The site still verifies the assertion and permission before granting access; a successful key read alone is not server authorization.
5. **Failed** and **Try again** appear if no read completes within 15 seconds. Try again closes the prompt and returns to the page, where you can start a fresh authentication attempt. A key/PIN or protocol rejection fails immediately rather than automatically retrying it.

NFC reader mode continues suppressing NDEF website handling while either result screen remains open. The prompt never automatically closes on success, contact loss or timeout. Moving the phone away before pressing a result button avoids immediately opening the website stored on Flex. Cancelling or leaving the app still ends the prompt.

The timeout uses Android's monotonic clock. It closes active NFC transport and ignores late results. A bridge records actual Java I/O failures across the Python boundary; no exception text or credentials are logged. Other FIDO2 failures are not classified as contact loss. No changes to FIDO2 scope, user verification, server challenge expiry, five-minute session lifetime or Forget me.

## Physical S24/Flex checklist

- Detect Flex and check that Authenticating and the progress bar appear immediately.
- Deliberately lose contact briefly, then present Flex again within 15 seconds. Check it can reach Success without closing the prompt.
- Wait without a key, or keep bouncing beyond 15 seconds. Check Failed appears and Try again returns to the page.
- After Success, move away and press Continue; check the private page opens without the saved Flex website.
- Confirm Forget me and absolute expiry still deny access.

Physical dev6 testing remains pending. Software tests cannot establish actual NFC rediscovery behavior on the S24.

## Software verification

104 targeted Android tests passed: 11 NFC activity/bridge tests, 4 ceremony broker tests, 16 page-cache tests and 73 browser ViewModel tests. The NFC tests include an actual reader callback with a simulated ISO-DEP connect failure followed by another detection, Java I/O classification, unchanged deadline across repeated bounces, late-result rejection, transport closure at timeout, and explicit result-button behavior. NFC hardware is mocked.

Columba feature commit: `bdc9b30414f90eccb8de5b438b7ffcb0068f4836`. Official base: `87b513e60a7b0fce8895f138d11949e4fcfa1e0f`. Build uses `:app:assembleNoSentryPythonBackendDebug -PcolumbaVersionName=2.3.1-beta-nomadkey.6 -PcolumbaVersionCode=20301050`. Package remains `network.columba.app.nomadkey.dev`. Backend and Python SDK wheel are unchanged.

Build and signature verification passed; 104 targeted Android tests passed. Physical dev6 NFC verification remains pending.

APK SHA-256: `bad44781d4495b1df62f50afbfcc68972ccb381d9a57f033d33ad42332094a04`.

Signing certificate SHA-256: `bcb3ce651b9cdb5bf155705144ac2db4e9becd1f527e6404404621e84c3f9e66` (unchanged).
