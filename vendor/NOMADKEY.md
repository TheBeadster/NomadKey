# NomadKey SDK provenance

The Python backend installs `nomadkey-0.1.0.dev9-py3-none-any.whl` from this directory.
Source: https://github.com/TheBeadster/NomadKey/tree/ab6cdafef49d44a55d562858ba34bce5d0edd337

Wheel SHA-256: `d579bdb03d64cc001a2b81c5e93ae2cf5dff611ca79fb10e62097c6fa238ec09`.

Build with Python 3.11: `python -m pip wheel . --no-deps -w <columba>/vendor`.
The external SDK keeps protocol and CTAP2 logic outside the slim Columba Python adapter.
Dev9 adds fresh operation-bound notification subscriptions for the separate Android Host.
The browsing protocol and five-minute absolute expiry remain unchanged. An alert
subscription does not grant page access or renew an existing browsing session.

Official Columba base: `87b513e60a7b0fce8895f138d11949e4fcfa1e0f`.
The earlier user-confirmed Flex/PiMonitor flow is separate from the new Host app;
new host NFC enrolment, carrier SMS/OTP access and real LXMF notification delivery
still require physical tests. Older wheels remain only for historical reproducibility.
