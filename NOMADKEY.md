# NomadKey development feature

Based on official Columba `v2.3.1-beta`, commit `87b513e60a7b0fce8895f138d11949e4fcfa1e0f`.

Feature source, protocol, tests and operations documentation:
https://github.com/TheBeadster/NomadKey

The `NomadKey DEV` launcher activity is deliberately separate from the normal
NomadNet browser and its persisted page cache. It runs in a separate process,
uses a temporary client identity, and binds FIDO2 to a fully pinned service and
RNS link. It uses Columba's Python backend dependency set and a vendored,
reproducibly buildable pure-Python NomadKey SDK wheel. It does not add a facade
to the existing Columba RNS API. The normal Columba identity is never imported.

Build `:app:assembleNoSentryPythonBackendDebug`. The resulting package is
`network.columba.app.nomadkey.dev`, separately installable beside official
Columba. No Sentry; no LeakCanary heap snapshots; debug test-coverage
instrumentation disabled for this development APK. NFC uses Android IsoDep
and python-fido2; no Google/Apple account or platform passkey provider is used.

Generate `vendor/nomadkey-0.1.0.dev1-py3-none-any.whl` using `pip wheel . --no-deps`
from the NomadKey source. The SDK version/source and wheel checksum must be
recorded with the APK. Do not hand-edit the wheel.

An optional ignored asset `rns-backend-py/src/main/assets/nomadkey-test-pin.json`
can carry public fields `host`, `destination`, `public_key` for the test
deployment. It contains no authenticator PIN or private key. Without it the
user enters those public settings. Full destination/public-key matching is
checked before connection. The TCP port is editable (default 444).

Physical Flex/YubiKey testing is pending. This activity renders static test
content as text; executable pages, forms, rich media and the normal Columba
BLE/LoRa interface manager are not integrated in this milestone. Use the
configured TCP Reticulum transport. Treat this as a development build, not a
production replacement or an upstream release.
