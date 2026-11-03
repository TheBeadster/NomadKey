import hashlib
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from fido2 import cbor
from fido2.ctap import CtapDevice
from fido2.hid import CAPABILITY
from fido2.webauthn import AuthenticatorData
from nomadkey.native import enroll, authenticate
from nomadkey.auth import Auth, Credential
from nomadkey.protocol import scope
from software_authenticator import SoftwareAuthenticator
import secrets


class SoftwareCtap(CtapDevice):
    """Test-only CTAP2 fixture with simulated UV. It does not prove real user verification."""
    def __init__(self): self.authenticator=SoftwareAuthenticator()
    @property
    def capabilities(self): return CAPABILITY.CBOR
    def call(self,cmd,data=b'',event=None,on_keepalive=None):
        command=data[0]; args=cbor.decode(data[1:]) if len(data)>1 else {}
        d=self.authenticator
        if command==4: result={1:['FIDO_2_0'],3:b'\0'*16,4:{'uv':True,'rk':False},6:[1]}
        elif command==1:
            assert args[7]['uv'] is True
            ad=AuthenticatorData.create(hashlib.sha256(args[2]['id'].encode()).digest(),0x45,0,d.data)
            result={1:'none',2:bytes(ad),3:{}}
        elif command==2:
            if args[5].get('up') is not False: assert args[5]['uv'] is True
            assert args[3][0]['id']==d.data.credential_id
            d.counter+=1
            ad=AuthenticatorData.create(hashlib.sha256(args[1].encode()).digest(),0 if args[5].get('up') is False else 5,d.counter)
            sig=d.key.sign(bytes(ad)+args[2],ec.ECDSA(hashes.SHA256()))
            result={1:{'type':'public-key','id':d.data.credential_id},2:bytes(ad),3:sig}
        else: raise AssertionError(command)
        return b'\0'+cbor.encode(result)
    def close(self): pass
    @classmethod
    def list_devices(cls): return iter(())


def test_native_ctap_enroll_and_login():
    key,destination=secrets.token_bytes(64),secrets.token_bytes(16)
    device=SoftwareCtap()
    bundle=enroll(device,key,destination)
    assert bundle['uv'] is True
    d=device.authenticator
    auth=Auth(key,destination,{d.data.credential_id.hex():Credential(d.data,frozenset({'pages:read'}))})
    link,identity=secrets.token_bytes(16),secrets.token_bytes(64)
    class LocalClient:
        public_key=key
        def begin(self): return auth.begin(link,identity)['options']['publicKey']
        def complete(self,response): return auth.complete(link,identity,response)
    local=LocalClient(); local.destination=destination
    assert authenticate(local,device)['ok']
