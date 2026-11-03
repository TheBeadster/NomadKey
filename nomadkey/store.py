import json
import os
from pathlib import Path
from fido2.webauthn import AttestedCredentialData
from .auth import Credential


def load(path):
    path = Path(path)
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    return {k: Credential(AttestedCredentialData(bytes.fromhex(v['public_data'])),
                          frozenset(v['permissions']),v.get('counter',0)) for k,v in raw.items()}


def save(path, credentials):
    path=Path(path); path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    raw={k:{'public_data':bytes(v.data).hex(),'permissions':sorted(v.permissions),'counter':v.counter} for k,v in credentials.items()}
    tmp=path.with_suffix('.tmp')
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as f:
        json.dump(raw,f); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)
