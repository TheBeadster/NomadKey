# Protocol v1 and threat model

## Trust boundaries

RNS authenticates/encrypts transport; a FIDO2 public credential independently authorizes the user. Unknown RNS identities can connect and identify but receive no private content. Server callbacks receive the actual link ID and RNS-verified remote identity, never an identity named in a form. RNS identification signs the link ID and identity public key. The client pins the full service destination and public key and reconstructs the `nomadnetwork.node` destination before connecting.

The endpoint is a real NomadNet destination with application/aspects `nomadnetwork.node`. Authentication paths use the SAME destination and link as protected reads. Authenticated links are not inserted into an identity allowlist. A clone of the client identity on a different link has no authority.

## Native FIDO scope (not browser WebAuthn)

Compute SHA-256 over `NomadKey scope v1\0 || service-public-key(64 bytes) || actual-destination(16 bytes)`. Split the 64 hex digest into two DNS-sized labels: `nk-<first32>.<last32>.nomadkey.invalid`. The native synthetic client origin is `https://<rp>`. These strings are credential namespaces, NOT a claim that DNS or HTTPS validated a website. No Internet lookup, domain ownership validation, platform account or cloud credential sync is required.

Native trusted client code derives the scope from its pinned service key, validates the active link and compares the complete challenge binding. It accepts no page-provided RP/origin override. Only then does python-fido2 invoke CTAP2. A malicious node with a different public key gets a different scope. A relay which substitutes the attacker's link or client key is rejected by the trusted client. A full transport relay of the genuine authenticated link does not acquire the client's session keys.

This depends on trustworthy client software and an authenticated full pin. Direct CTAP2 does not itself establish website origin and a malicious native app can request arbitrary credential scopes. Do not describe this as unconditional phishing resistance. A compromised phone, PC, server or authenticator is outside this prototype's protection.

## Authentication

1. Client establishes a verified link and identifies with a newly generated, memory-only RNS identity.
2. `/nomadkey/begin` accepts bounded JSON containing requested permissions and, for administration, an exact supported operation. Global limit 30 starts/minute, per-client limit 5/minute, 64 outstanding challenges. Identity churn does not bypass the global limit.
3. Server builds canonical JSON: version, full destination and service key, observed link ID and client public key, random 32-byte nonce, sorted permissions, lifetime and operation. The encoded JSON is the WebAuthn challenge. A server-memory record has a monotonic 60-second deadline.
4. Client independently compares all fields, RP ID, challenge bytes and required UV before asking the authenticator. The scope and request originate in trusted client code, outside served content.
5. `/nomadkey/complete` consumes the challenge before verification. python-fido2 verifies signature, RP hash, exact origin, challenge, UP and required UV. Cross-origin assertions are rejected. Nonzero signature counters must advance; zero-only authenticators remain usable per FIDO semantics. Counters are persisted before success is returned.
6. Server associates the link with that credential and `monotonic_now + lifetime`. No bearer token is returned. Default lifetime is 300 seconds; configuration permits 1–3600. Client uses an earlier conservative deadline starting before assertion submission.

Every protected request, and again after file reading, checks authorization. Refresh, action attempts and keepalives never update the deadline. Reconnect creates a new link and requires a new ceremony. Restart loses all sessions/challenges; only public credential records/counters and the stable server private identity persist.

## Revocation and administration

`/nomadkey/forget` deletes the current link's pending ceremony and authority, returning an explicit acknowledgement. Client always clears its local view/state even on failure, and distinguishes remote acknowledgement from disconnection. Closing the link also revokes server state when the close is observed. Absolute expiry remains the bound if no close reaches the server.

A browsing session cannot administer credentials. The supported remote administrative operation is `remove_credential`, requiring a new challenge with permission `admin` and the exact credential ID. It executes once, removes affected sessions and clears pending ceremonies. Adding credentials/changing permissions are local administrative operations only in this milestone. There is no remote lifetime extension operation. Stop the service before local credential edits; restart invalidates all sessions.

## Content and bounds

The test manifest contains only `/page/index.mu`. Explicitly mapped `/page/`, `/file/` and `/media/` routes all pass the same guard. Unknown routes are unregistered. Exact route comparison prevents alternate encodings/query variants; traversal, escapes, symlinks and executable files are rejected. No directory listing, implicit file route, media proxy, form handling or executable page handler exists. Static content is capped at 64 KiB. This intentionally does not yet migrate executable estate controls.

RNS destination request cap is 16 KiB, checked by RNS before accepting oversized request resources; application JSON is independently capped. At most 32 established links and 60 admitted links/minute; unauthenticated links age out after 90 seconds once no challenge remains. RNS connection handshake occurs before the application admission callback, so upstream transport resource exhaustion remains possible. Systemd limits memory, tasks and open files. A malicious actor can consume the global budget and deny service; availability is not guaranteed on a hostile mesh.

## Residual limitations

- Client UI, NFC APDU interoperability and physical UV/PIN behavior need device testing. Software fixtures simulate UV and cannot prove it.
- Protected bytes already transferred, photographed or copied cannot be erased. Revocation prevents new requests; it cannot recall a resource already transmitted or bytes in an in-flight transfer.
- Static files are administered locally. Concurrent malicious filesystem replacement by a compromised local service owner is outside the threat model; content checks do not sandbox the OS administrator.
- Transport/router caches retain public routing metadata; protected content, assertions and PINs are not intentionally persisted by the custom client. Memory remanence and OS compromise are outside scope.
- This is a development protocol, not an independent security audit or a standard WebAuthn website deployment.

## Normal-browser integration (dev3)

With `--browser-login`, only `/page/index.mu` may return a public authentication landing page without session authority. The same path returns private content only after the existing per-link permission check. `/page/forget.mu` revokes only its requesting link and returns the public page. Minimal discovery remains public. Other configured routes keep the default-deny handler. Private page responses carry `#!nomadkey-v1 private`, `#!c=0` and a Forget me link; public responses carry `#!nomadkey-v1 public`.

The trusted client reuses the actual browser RNS link and proves possession of the current Columba identity. It validates discovery against the link's service identity and validates the canonical FIDO2 challenge against the same service, link and client key. No identity-wide allowlist exists. Native NFC consumes a one-use memory handoff; RP scope is independently derived from verified service key and destination before CTAP. The normal browser suppresses caching, history, restoration, forms, downloads and media/partial prefetch for marked pages. Server expiry remains authoritative on every request regardless of UI state.
