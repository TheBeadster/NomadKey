# Host dev1 validation — 8 November 2026

Source implementation: `ab6cdafef49d44a55d562858ba34bce5d0edd337` on
[`host/android-dev1`](https://github.com/TheBeadster/NomadKey/tree/host/android-dev1).
PiMonitor and its live identities/pages were not modified.

## Software evidence

- Python suite: **82 passed, 2 skipped**. The skips are hardware-dependent checks.
- `scripts/host_smoke.py`: real loopback RNS connections, synthetic SMS and software
  CTAP2. Public denial, private pagination, fresh notification registration,
  unchanged browsing expiry, cloned-identity connection denial, absolute expiry,
  unsubscribe, acknowledged Forget me and reconnect denial passed. No private test
  body was found in the client RNS files.
- Separate Python processes: one hosted the standard TCP shared RNS instance and
  a second successfully attached. This is not an Android Sideband/Columba
  interoperability claim.
- Host APK compilation and Android lint passed. Lint warnings include English-only
  UI strings and the intentional NFC hardware requirement; there is no lint baseline.
- Android API 36 emulator instrumentation: **2 tests passed**. The real embedded
  Python/RNS/LXMF runtime started; invalid/denied inbox access failed safely.
  Five synthetic SMS messages were injected using the emulator, and Android's
  actual inbox provider returned two per page with working pagination. The
  metadata event provider contained no synthetic message body.
- The app's first screen was inspected through the emulator UI hierarchy. A real
  small-phone usability check, background battery policy and NFC remain untested.

## Artifact

`NomadKey-Host-0.1-dev1.apk`, package `org.nomadkey.host.dev`, version code 1,
Android API 26+, ARM64/ARMv7/x86_64. Development signing certificate SHA-256:

`bcb3ce651b9cdb5bf155705144ac2db4e9becd1f527e6404404621e84c3f9e66`

APK SHA-256:

`fd6f767b56d1b63fc5f0975a38b0adbc492262ee01bbc1cdc448a3d3d09e7ef6`

Embedded SDK wheel `nomadkey-0.1.0.dev9-py3-none-any.whl` SHA-256:

`d579bdb03d64cc001a2b81c5e93ae2cf5dff611ca79fb10e62097c6fa238ec09`

## Still needs physical evidence

No Flex/YubiKey test was performed against this new host. Real carrier SMS/OTP
visibility, SIM change/outage alerts, direct LXMF delivery to the user's phone,
shared RNS interoperability with Android apps, and sustained screen-off hosting
remain unverified. Older user-confirmed PiMonitor/Columba tests do not establish
these new behaviours. See [the setup and hardware checklist](ANDROID-HOST.md).

The app cannot prove a SIM swap, guarantee Android exposes all OTP messages, or
send an immediate alert over a network connection that has itself failed.

Paired Columba source: `243bdcddb5e93d41e4d22982fd7bc4c1996d09ba` on
`columba/nomadkey-development`. NomadNet browser regression tests: **77 passed**,
zero failures or skips. Development package and signing certificate are unchanged
from dev8 so an in-place upgrade preserves local identity and settings.

Columba dev9 universal APK SHA-256:

`581b3eb8258e38fa8db1ca4e327754c89ba61baf6654de003a2f2ccb6d3b6377`

Version code `20301080`, package `network.columba.app.nomadkey.dev`. Final build
completed successfully with the pinned dev9 SDK wheel above.
