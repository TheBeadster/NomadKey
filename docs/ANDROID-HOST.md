# NomadKey Host: your spare phone becomes a locked cupboard

Imagine keeping your private notes and text messages in a locked cupboard at home.
You want to read them while you are away, but you do not want everyone on the
network to open the door.

NomadKey Host turns a spare Android phone into that cupboard. Columba, on the phone
you carry, is how you look inside. Your Flex or YubiKey is the key to the door.
You first teach the Host which keys are allowed. Later, you tap an approved key
and enter its PIN to open your private pages. The secret inside the key stays there.

Why do this? A network address tells the Host which app is connecting. It does not
prove who is holding the phone. NomadKey adds a separate check using your security
key. You can use a different trusted phone and a new network identity without
copying your usual identity onto it. You must still check that you opened the
right site, and trust the phone and app you are using.

The door closes after five minutes, even if you keep reading. **Forget me** closes
it sooner. Opening another connection does not give it a free pass.

Choose what the cupboard holds:

- **Private pages:** notes or information you want to share only with approved keys.
- **Text messages:** read the messages Android lets the Host see, two at a time.
  Your everyday phone can receive a small alert saying who sent a message and when.
  The alert does not include the message or its login code.

The Host can also warn you when the SIM disappears, changes or loses service.
That is a warning to investigate, not proof that somebody stole your number.
Some Android phones hide login-code messages. This is still a development app,
and these features need checking on your actual phones.

## Setup and technical details

### First setup

1. Install NomadKey Host DEV on the server phone (Android 8/API 26 or later).
   Set a secure screen lock. Keep this phone under trusted local control.
2. Choose a public site name and mode. The TCP default is **Beleth RNS Hub**, `rns.beleth.net:4242`, matching Columba's built-in server.
   An upgrade replaces the old built-in `mh.beady.com:444` setting; other custom
   settings are kept. Press **Start host**. First launch, not package installation, starts setup.
3. The app first tries the standard local TCP shared RNS instance on port 37428.
   If available it attaches; otherwise it starts the official Python Reticulum
   stack with its own TCP uplink. A busy but unusable local port is an error.
   Shared-instance providers using another port or Android IPC are not automatically
   compatible. Connecting to Sideband/Columba on real phones still needs testing.
4. Press **Enrol owner**, unlock the phone and present the FIDO2 key with its PIN.
   The first key gets owner permissions. This is a local, non-exported operation;
   the network has no first-user enrolment route.
5. Add a backup owner: approve with the existing owner, then enrol the backup
   within 60 seconds. Reader-key approvals cannot create an owner.
6. Save the host's service bookmark on a supported FIDO2 key, or verify and pin
   its full destination in Columba. Existing PiMonitor credentials are scoped to
   PiMonitor: enrol a separate credential for this new host.
7. In SMS mode, grant the permissions Android permits and review/trust the SIM
   observation using the owner key. There is no automatic acceptance of a new SIM.

The service shows an ongoing notification and holds a periodically renewed wake
lock while running. **Stop host** invalidates sessions and closes this app's
process, leaving other apps' RNS instances alone. Reopen to change mode/settings.
This version does not restart after reboot or an OS kill. Android battery policy
can stop it; verify screen-off operation on the actual phone.

## Reading and notifications

Open the host from normal NomadNet announces in Columba NomadKey dev9 or newer.
The first page is public and contains no SMS. Use the fingerprint menu to
authenticate. Each protected request checks the same live link and absolute
five-minute lifetime. The server never grants a broad identity allowlist.

The inbox shows two full OS-visible messages at a time, with sender and UTC
timestamp. Next/Back browse a snapshot anchored to the newest message when opened;
Latest starts a new snapshot. Oversized pages fail explicitly instead of silently
truncating a message. Message text is rendered literally, not executed as Micron.
Every protected page includes Forget me. Columba clears its protected view on
expiry, logout or leaving the app. This cannot erase information already copied.

On a protected SMS page, choose **Register this device for SMS/SIM alerts** in the
fingerprint menu. A fresh FIDO2 assertion binds this specific operation to the
current service, link and identified client public key. The server derives that
key's LXMF delivery destination; no arbitrary address field is accepted. The
registration persists independently of the five-minute browsing session and
does not extend it. Forget me ends browsing; use **Remove this device from alerts**
to unsubscribe. Revoking the enrolling credential also removes its subscriptions
on the next delivery sweep (normally five seconds); already-sent alerts cannot be
recalled.

Alerts contain only `SMS received from <sender> at <UTC time>`, or SIM-monitoring
status. The queue API has no SMS-body parameter. It is bounded to 256 alerts,
64 recipients and 24-hour retention, with bounded retries. Notifications use
encrypted direct LXMF delivery. Offline recipients may not receive an alert
before retention/retry limits; this is not guaranteed delivery. Synthetic test
messages are not evidence of real SMS, OTP or hardware interoperability.

## SIM and Android limits

The app records a hash of local subscription metadata, not an exported ICCID or
IMSI. On setup it asks the owner to trust that observation. Sustained removal,
metadata change, service loss, airplane mode or unavailable monitoring causes an
alert after 60 seconds; recovery is also reported. Brief signal changes are
debounced using monotonic time. Dual-SIM mode monitors the observed set and requires
all observed subscriptions to report service; selecting one SIM is not implemented.

These observations **cannot prove a carrier-side SIM swap**. A swap may make the old
SIM lose service, but so can an outage. Some replacements may leave observable
metadata unchanged. A monitoring-permission failure is reported as unavailable,
never healthy.

Android restricts SMS permissions and, on newer releases, access to sensitive/OTP
messages. A normal permission grant does not prove all messages are exposed. This
app does not become the default SMS application, scrape notifications, request a
cloud account or bypass Android permission controls. The inbox explicitly states
that Android may hide messages. Compare an ordinary SMS and a test OTP locally
against the remote inbox on the actual phone.

Android also requires approximate-location permission for the service-state API.
No coordinates are stored or transmitted; Android 13+ is asked to omit location
data. Background permission restrictions may still make the check unavailable.
If the monitored SIM is the only network path, its failure also prevents immediate
alert delivery. Use Wi-Fi or an independent Reticulum route; otherwise alerts can
only queue until a path returns.

References: [Android SMS permissions](https://developer.android.com/reference/android/Manifest.permission),
[service-state permission](https://developer.android.com/reference/android/telephony/TelephonyManager#getServiceState(int)),
[device identifier restrictions](https://source.android.com/docs/core/connect/device-identifiers),
[foreground service types](https://developer.android.com/develop/background-work/services/fgs/service-types).

## Local recovery and storage

Private service identity, enrolled public keys and metadata live only in the
app-private directory. Android backup and device-transfer extraction are disabled.
SMS bodies are queried from Android's inbox on demand; this app does not keep an
extra SMS database. PINs and assertions are not written to preferences or logs.
The app uses FLAG_SECURE for local administration screens.

Keep a separately enrolled backup owner key. A reader cannot recover an owner.
If all owner keys are lost, a trusted local administrator may clear app storage
and create a **new** host identity, then enrol keys and re-verify all client pins.
This loses the old destination, subscriptions and settings. There is no network
reset or authenticator-private-key export. Uninstall likewise destroys this host's
identity; do not uninstall merely to upgrade.

## Build and test

Source: `android-host/`, reusable backend: `nomadkey/host.py` and `host_state.py`.
Python 3.11, Chaquopy 17.0.0, AGP 9.1.0, official RNS 1.5.7, LXMF 1.2.1,
python-fido2 2.2.1. The client remains based on official Columba commit
`87b513e60a7b0fce8895f138d11949e4fcfa1e0f` with the existing isolated NomadKey changes.

Build the SDK wheel first and place it in `android-host/vendor/`, then run
`gradlew :app:assembleDebug :app:lintDebug`. Set Android SDK location locally;
do not commit local.properties or signing keys. APKs are development-signed and
must retain the same certificate for in-place updates.

## Physical test checklist — not yet performed for this app

- Enrol Flex and backup YubiKey; prove wrong key/PIN fails and reader cannot enrol
  an owner. Check NFC removal does not open the Flex's NDEF website.
- Verify startup with and without a shared RNS provider, including screen-off
  operation. Stop/reboot must invalidate all outstanding sessions/challenges.
- Read ordinary SMS and a safe test OTP through Columba; compare full content and
  timestamps with the local inbox. Verify pagination and new arrivals.
- Register the client, receive a metadata-only LXMF alert, and confirm no OTP/body
  appears in notification previews. Unsubscribe and revoke the enrolling key.
- Continuously refresh for five minutes: access must still expire. Test Forget me,
  direct links, reconnecting, and a second connection with the same RNS identity.
- Trust the SIM, remove/disable it for over 60 seconds, restore it, and observe
  alerts over Wi-Fi. Test denial of phone/SMS/location permissions and no network.
- Do not treat these tests as proof that every carrier-side SIM swap is detectable.
