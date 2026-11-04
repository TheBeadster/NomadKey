# Installation, management, enrollment and rollback

## Existing deployment preservation

Before changes, the operator made a mode-0600 archive in a mode-0700 directory on PiMonitor containing original NomadNet configuration, identities, pages, access code and systemd configuration. Archive path and checksum are in the local deployment evidence, not distributed with the source. The archive was reopened and 515 members verified. Do not upload it: it contains private identity/configuration material.

## Isolated installation

The supplied systemd unit is an explicit PiMonitor development example using `/home/dadmin/nomadkey-dev`. It is started for testing, **not automatically enabled at boot**. Existing units and page routes are unchanged.

```sh
python3 -m venv /home/dadmin/nomadkey-dev/venv
/home/dadmin/nomadkey-dev/venv/bin/pip install -r requirements-server.txt
/home/dadmin/nomadkey-dev/venv/bin/pip install --no-deps -e .
mkdir -p /home/dadmin/nomadkey-dev/{state,rns}
chmod 700 /home/dadmin/nomadkey-dev/{state,rns}
cp deploy/rns-config /home/dadmin/nomadkey-dev/rns/config
sudo cp deploy/nomadkey-dev.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start nomadkey-dev
systemctl status nomadkey-dev
```

Keep `state/service.identity` mode 0600. Back up that file securely; it pins the actual stable service destination. A changed service key requires new pin verification and new enrollment. Default absolute expiry is five minutes; set `--lifetime` in a local systemd override (1–3600 seconds), then restart. Restart always clears sessions and challenges. Never edit lifetime on a live session.

## Enrollment — trusted local administration

1. Obtain and verify the full destination and service public key through the trusted SSH administration channel. Put only these PUBLIC fields in the client's service pin. Verify full address before trusting a shortened display.
2. In the Columba development entry, enter a reachable Reticulum TCP host, full destination and service key. Verify/connect. Enter the authenticator's existing FIDO2 PIN and choose **Enroll**, then hold Flex in the NFC field. Required UV must succeed; there is no U2F/TOTP fallback. The app does not set/change the authenticator PIN or retry a rejected PIN automatically.
3. Export the **public enrollment bundle**. It contains public credential data and scope, not a private key or PIN. Transfer it through a trusted administrative channel. Verify which physical authenticator produced it; the bundle is not vendor attestation or proof that it is Flex.
4. On PiMonitor, stop **only NomadKey** and import the verified file locally:

```sh
sudo systemctl stop nomadkey-dev
/home/dadmin/nomadkey-dev/venv/bin/nomadkey import-credential \
  --state /home/dadmin/nomadkey-dev/state --file /trusted/path/public-enrollment.json
sudo systemctl start nomadkey-dev
```

Use `--admin` only for a deliberately authorized administrative credential. Repeat separately with the backup YubiKey. No publicly accessible initial-enrollment endpoint exists and tapping a key never auto-enrolls it at the server.

PC alternative: `nomadkey enroll --pin-file service-public-pin.json --output enrollment-public.json`; then the same trusted import. `--pin-file` means a PUBLIC service identity pin file, never the authenticator PIN.

Local credential file edits must be made with the service stopped to avoid races with counter persistence. Removing a record and restarting revokes it and all current sessions. Recovery is trusted SSH/local administration plus a new authenticator ceremony and public-key import; there is no network reset or private-key export.

## Android build

Apply the feature branch to the recorded 2.3.1-beta base. Build the reusable wheel with `pip wheel . --no-deps -w <columba>/vendor`, then:

```sh
./gradlew :app:assembleNoSentryPythonBackendDebug '-PcolumbaVersionName=2.3.1-beta-nomadkey.1'
```

Requires JDK 17+, Android SDK 36 and a Chaquopy-compatible Python 3.11 build host. The debug APK is a separately installable development app; it is not an update signed by upstream Columba. Do not uninstall the user's normal Columba. Record APK SHA-256 and signing-certificate fingerprint with each artifact. Do not commit signing private keys.

## Rollback

Dev2 live-status page uses `/etc/systemd/system/nomadkey-dev.service.d/20-status-page.conf`, which adds `--status-page` to the original command. To return to the static test page while preserving enrollment, remove only that override, run `sudo systemctl daemon-reload`, then `sudo systemctl restart nomadkey-dev`. Restart invalidates sessions. The original content manifest is still the complete allowlist; no dynamic script execution is enabled. The host snapshot reads local OS metrics and never extends session expiry.

```sh
sudo systemctl stop nomadkey-dev
sudo systemctl disable nomadkey-dev  # harmless if never enabled
systemctl is-active nomadnet-intranet betchton-nomadnet-access
```

Stopping NomadKey invalidates all sessions immediately. Leave its private state and source for review or archive them securely. There is no need to restore original pages because none were migrated. Remove only the separately installed development APK if desired; it has a distinct package ID. Do not delete/reinstall normal Columba.

## Migration gate

No existing page migration is authorized by a passing synthetic-page test alone. Before migration, enumerate every existing executable page, file, media endpoint, form/action and upstream cache path; classify required permissions; back up again; test direct access and denial for every class. Current static handler intentionally rejects executable files and all forms. Existing protected content remains on the original guarded service until that work is complete.

## Vanity

`scripts/vanity.py` requires an explicit eight-hex prefix, output path and bounded attempt budget. It computes the real `nomadnetwork.node` destination. No search was run. Expected work for one fixed 8-hex prefix is 2^32 random trials. A remembered 4-hex suffix plus prefix checks 48 target bits, not full-address assurance. Reading suffix characters backwards adds no entropy. Pin the full verified destination/key.
