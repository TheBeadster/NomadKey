# Columba private pages — development 2

[Private development release](https://github.com/TheBeadster/NomadKey/releases/tag/nomadkey-dev2).

Install `NomadKey-Columba-2.3.1-beta-dev2.apk` over the previous NomadKey development app. Do not uninstall it; this preserves public connection settings and its normal Columba data. Keep the separately installed official Columba if desired. This build has upstream's full application plus the private-page integration, but is not signed by upstream and cannot replace their package in place.

Open **Columba NomadKey DEV**. Complete its normal onboarding if needed. Under **Settings > Bottom Navigation**, add **NomadNet** if the tab is not already visible. Open **NomadNet > Private pages · NomadKey** (also in the NomadNet overflow menu). Connect, enter the existing FIDO2 PIN, and authenticate with Flex. The private PiMonitor page opens automatically; refresh resamples live metrics without renewing access. A countdown shows remaining access. Forget me clears the view and reports whether remote revocation was acknowledged. Returning to Columba also clears the protected view and requests revocation.

The existing service destination, public pin and enrolled credential are unchanged. Do not re-enroll your already working Flex. This application has its own normal Columba identity; the private page connection still uses a separate temporary identity. It does not import the identity from official Columba.

## Page and scope

The same protected `/page/index.mu` now provides a real, read-only PiMonitor host snapshot: UTC sample time, NomadKey uptime, host uptime, CPU load, memory availability and free storage. It is not an estate-wide health assessment. No remote control, shell execution or forms are enabled. No existing estate pages were migrated.

Protected content remains outside the normal NomadNet browser's disk caches/history. This integration provides a private-page entry within Columba; it does not add FIDO2 to every existing browser route or reuse Columba's BLE/LoRa transport. The configured private TCP path remains `mh.beady.com:444`.

## Build record

- Version: `2.3.1-beta-nomadkey.2-nomadkey-dev`, code `20301010`.
- Package: `network.columba.app.nomadkey.dev`; universal APK, 133428864 bytes.
- APK SHA-256: `f22cec49527f06e4e9adfa9090a57658a206f72952a54a263482cc9831044dca`.
- Verified Android Debug signing certificate SHA-256: `bcb3ce651b9cdb5bf155705144ac2db4e9becd1f527e6404404621e84c3f9e66` (same certificate as dev1).
- Columba feature commit: `5b3e4ee63533937fb15165b46660eca591077928` on base `87b513e60a7b0fce8895f138d11949e4fcfa1e0f`.
- Backend commit: `26de1d4aac06693e2953b7f8e9544aae2d13fdc6`.
- Embedded client SDK remains `0.1.0.dev1`, unchanged from the hardware-tested protocol implementation; only backend and Android UI/navigation changed.
- Build: `:app:assembleNoSentryPythonBackendDebug -PcolumbaVersionName=2.3.1-beta-nomadkey.2 -PcolumbaVersionCode=20301010`, successful in 10m9s, JDK 21 / SDK 36 / Gradle 9.4.1.

## Verification

40 tests passed on PiMonitor. Real RNS software-authenticator testing of the dynamic page passed: unknown client denial, authenticated read, cloned-identity separate-link denial, expiry despite continuous requests and acknowledged Forget me. An external `mh.beady.com:444` probe verified the deployed service pin and unauthenticated denial. Deployment readback confirmed one enrolled credential, byte-identical identity/credential files and unchanged original service process. Hardware success on dev1 is the user's report from 4 November, not a new automated physical test of dev2.

Backup before deployment: `/home/dadmin/codex-backups/nomadkey-dev2-20261104T115842Z` (private, contains credential/identity state; never publish its contents). [Operations and rollback](OPERATIONS.md) describe removing only the status-page override to restore the static page.
