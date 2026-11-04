# Columba normal-browser authentication — development 3

Development release: https://github.com/TheBeadster/NomadKey/releases/tag/nomadkey-dev3

Install the dev3 APK over Columba NomadKey DEV. Keep the app's data; no new Flex enrollment is needed. This has a separate package from official Columba and uses the same development signing certificate as dev1/dev2.

1. Use Columba's normal Python backend and configured Reticulum interface. The working external TCP transport is `mh.beady.com:444`; this flow now uses normal Columba interfaces, not the older separate launcher's TCP setting.
2. In normal **Announces**, select the NomadNet node **PiMonitor | NomadKey**. Its public page says authentication is required.
3. Open the browser's **fingerprint / Identify** menu and choose **Authenticate with NFC key**. Ordinary identification alone does not unlock this site.
4. Verify the full destination shown in the dialog, confirm it, enter the existing FIDO2 PIN and tap Flex. The same browser opens the private, read-only PiMonitor status page.
5. Refresh updates metrics without renewing authority. Every private page has **Forget me**, also available in the browser's session bar. The server enforces five minutes from authentication success; the client uses a conservative countdown. Expiry clears the private view. Forget me reports whether server revocation was acknowledged.

Verified service destination: **aadad40f**40938abef7ab0ef44956**6bcf**. Use the full value `aadad40f40938abef7ab0ef449566bcf`; no vanity search was performed. A short remembered fragment is not full-address assurance.

## Behavior and limits

The normal Columba installation's own RNS identity proves possession on its actual browser link. FIDO2 grants authority to that link only; another connection with the same identity does not inherit it. A borrowed installation can use its own identity without importing the user's normal identity. Reconnect, service restart and leaving/backgrounding the protected browser require fresh authentication. Launching the short internal NFC prompt is exempt from background logout while its ceremony is pending.

The NFC request derives RP scope from the verified transport service public key and actual NomadNet destination. No page-supplied RP ID is trusted. PIN/assertion handoff stays in process memory, never Intent extras, saved instance state or URLs; cancelled ceremonies reject late results. UV is required. There is no cloud credential service or browser-origin workaround.

NomadKey pages opt out of caching with a protocol marker and Micron no-cache directive. The app refuses disk caching, in-memory history, persisted tab restoration and media/partial prefetch for these pages. Screenshot/task-preview protection is enabled while the protected site is open. Forms, protected downloads, media and executable pages remain disabled in this version; ordinary public NomadNet sites retain their existing behavior. Previously captured information cannot be erased.

The older standalone NomadKey development launcher remains for enrollment compatibility. New first-use enrollment still requires trusted server administration; the public landing page does not enroll credentials.

## Validation and build

Server: 50 tests passed on PiMonitor; Windows 48 passed with two POSIX-only skips. Real RNS software-authenticator browser smoke passed public/private switching, service/link/client binding, cloned-connection denial, continuous-activity absolute expiry, page and control Forget me, reconnect denial and absence of private content in the test client's transport files. These are software tests, not NFC hardware tests.

The user's working dev1/dev2 Flex report is preserved. This new normal-browser NFC flow requires physical S24/Flex confirmation after installing dev3. No software credential was added to the live server; the one existing enrolled credential and service key were byte-identical across deployment.

Build command: `:app:assembleNoSentryPythonBackendDebug -PcolumbaVersionName=2.3.1-beta-nomadkey.3 -PcolumbaVersionCode=20301020`.

Package `network.columba.app.nomadkey.dev`. Official Columba base `87b513e60a7b0fce8895f138d11949e4fcfa1e0f` (v2.3.1-beta). Embedded SDK `0.1.0.dev3`, wheel SHA-256 `3ee21a4a5bdb0ddda0df730a68c97c7d1bc620fe6a20667044448ad370bf6754`.

Signing certificate SHA-256: `bcb3ce651b9cdb5bf155705144ac2db4e9becd1f527e6404404621e84c3f9e66`. APK checksum and source commit identifiers accompany the release.
