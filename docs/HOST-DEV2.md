# Host dev2: Beleth default and simpler introduction

This update makes the Host start with **Beleth RNS Hub**, `rns.beleth.net:4242`,
the server listed in Columba's built-in community servers and bootstrap settings.
The value was checked in the Columba source, not guessed.

The introduction now explains the purpose first: keep private pages or messages
on a spare phone, and use an approved security key to open them temporarily from
another trusted phone. The app, README and Host guide use plain language first,
with setup and technical details afterwards.

Upgrade Host dev1 in place. Opening dev2 changes a saved `mh.beady.com:444`
setting to Beleth; other custom host/port settings are retained. Stop and reopen
the Host to use the new setting. Its service identity, keys and permissions remain
in app storage. Columba dev9 does not need another update for this change.

## Checks and artifact

- Python tests: 82 passed, two hardware-dependent skips.
- Android APK build and lint passed.
- Development signing certificate verified; same certificate as dev1.
- No new hardware or live Beleth reachability test was performed for this update.
  Existing hardware limitations remain in the [Host guide](ANDROID-HOST.md).

APK: `NomadKey-Host-0.1-dev2.apk`, version code 2.

SHA-256: `edf8f48fb9a76af67ba2a66cb248e8639b8d76a25d9631cca93ea74adfa5fb4e`

SDK wheel: `nomadkey-0.1.0.dev10-py3-none-any.whl`.

SHA-256: `8fb51a9df94bc2b76e7210db3ef862aca344549577a7bbe26afebe239979f747`

Development certificate SHA-256:
`bcb3ce651b9cdb5bf155705144ac2db4e9becd1f527e6404404621e84c3f9e66`
