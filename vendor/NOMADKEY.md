# NomadKey SDK provenance

The Python backend installs `nomadkey-0.1.0.dev7-py3-none-any.whl` from this
directory. Its source is the main branch of
https://github.com/TheBeadster/NomadKey at commit
`1990ab124b5c495638e6cff77269056c17074ed0`.

Wheel SHA-256:
`34bba21add0bf89c746c1415cb06a8abeeae9429e529dc856dfb1f735422a73f`.

Build with Python 3.11: `python -m pip wheel . --no-deps -w <columba>/vendor`.
The SDK keeps protocol and CTAP2 logic outside Columba's slim Python adapter
tree. Dev7 adds protected NFC saved-site storage; the existing site-login
protocol and server expiry are unchanged. See the SDK's `docs/NFC_BOOKMARKS.md`
for the format, requirements, recovery limitations and physical test checklist.

Columba uses the existing Python Reticulum backend. This feature branch is based
on official Columba commit `87b513e60a7b0fce8895f138d11949e4fcfa1e0f`.
Physical dev7 bookmark tests remain pending; simulated tests are not hardware
evidence. Earlier wheels remain for historical reproducibility and are not
installed by the current build configuration.
