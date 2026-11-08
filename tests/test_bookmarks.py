import hashlib
import secrets
import threading
from types import SimpleNamespace
import pytest
import RNS
from fido2 import cbor
from fido2.ctap import CtapError
from fido2.ctap2.blob import LargeBlobs
from fido2.ctap2.pin import ClientPin
from fido2.webauthn import AuthenticatorData
from nomadkey.bookmarks import RP, BookmarkError, SafeBlobs, pack, unpack, operate, capabilities

class Card:
    """Simulated CTAP commands; real Yubico blob encryption/serialization. No hardware."""
    def __init__(self):
        self.info=SimpleNamespace(options={k:True for k in ('rk','clientPin','pinUvAuthToken','largeBlobs')},
            extensions=['credBlob','largeBlobKey','credProtect'],max_cred_blob_length=32,
            max_large_blob=1024,max_msg_size=128,remaining_disc_creds=10)
        raw=cbor.encode([]);self.data=raw+hashlib.sha256(raw).digest()[:16]
        self.creds=[];self.calls=[];self.pending=None;self.next=[]
    def large_blobs(self,offset,get=None,set=None,length=None,**kwargs):
        if get is not None:return {1:self.data[offset:offset+get]}
        self.calls.append('write')
        if length is not None:
            assert length<=self.info.max_large_blob
            self.pending=bytearray(length)
        self.pending[offset:offset+len(set)]=set
        if offset+len(set)==len(self.pending):self.data=bytes(self.pending)
        return {}
    def make_credential(self,challenge,rp,user,params,extensions,options,**kwargs):
        self.calls.append('create')
        assert rp['id']==RP and options=={'rk':True} and extensions['credProtect']==3
        credential={'anchor':extensions['credBlob'],'key':secrets.token_bytes(32)}
        self.creds.append(credential)
        return SimpleNamespace(auth_data=AuthenticatorData.create(hashlib.sha256(RP.encode()).digest(),0x85,1,
            extensions={'credBlob':True,'credProtect':3}),large_blob_key=credential['key'])
    def get_assertion(self,rp,challenge,**kwargs):
        self.calls.append('read_assertion');assert rp==RP
        if not self.creds:raise CtapError(CtapError.ERR.NO_CREDENTIALS)
        values=[SimpleNamespace(auth_data=AuthenticatorData.create(hashlib.sha256(RP.encode()).digest(),0x85,2,
            extensions={'credBlob':c['anchor']}),large_blob_key=c['key'],number_of_credentials=None) for c in self.creds]
        values[0].number_of_credentials=len(values);self.next=values[1:];return values[0]
    def get_next_assertion(self):return self.next.pop(0)

class Pins:
    def __init__(self,card):self.card=card;self.protocol=self;self.VERSION=2
    def authenticate(self,token,data):return hashlib.sha256(token+data).digest()
    def get_pin_token(self,pin,permissions,rp):
        self.card.calls.append(('pin',permissions));assert rp==RP
        if pin!='correct':raise CtapError(CtapError.ERR.PIN_INVALID)
        return b'x'*32

def site(name='PiMonitor'):
    identity=RNS.Identity()
    return {'destination':RNS.Destination.hash(identity,'nomadnetwork','node').hex(),
        'public_key':identity.get_public_key().hex(),'name':name}

def run(card,action,record=None,pin='correct'):
    return operate(card,pin,action,record,pin_factory=Pins)

def test_new_phone_read_and_duplicate_save_preserve_other_application():
    card=Card();other=secrets.token_bytes(32);LargeBlobs(card).put_blob(other,b'other app')
    s=site();assert run(card,'save',s)['sites']==[s]
    card.calls=[]
    assert run(card,'read')['sites']==[s]
    assert all(x not in ('write','create') for x in card.calls)
    assert all(x[1]==ClientPin.PERMISSION.GET_ASSERTION for x in card.calls if isinstance(x,tuple))
    assert run(card,'save',s)['already_saved']
    assert 'create' not in card.calls and 'write' not in card.calls
    assert LargeBlobs(card).get_blob(other)==b'other app'

def test_multi_site_discovery_needs_no_local_credential_id():
    card=Card();a,b=site('A'),site('B');run(card,'save',a);run(card,'save',b)
    assert run(card,'read')['sites']==[a,b]

@pytest.mark.parametrize('option',['rk','clientPin','pinUvAuthToken','largeBlobs'])
def test_unsupported_key_fails_before_pin_or_write(option):
    card=Card();card.info.options[option]=False
    with pytest.raises(BookmarkError):run(card,'save',site())
    assert not card.calls

@pytest.mark.parametrize('extension',['credBlob','largeBlobKey','credProtect'])
def test_missing_extensions_fail_before_pin(extension):
    card=Card();card.info.extensions.remove(extension)
    with pytest.raises(BookmarkError):run(card,'read')
    assert not card.calls

def test_wrong_pin_not_retried():
    card=Card()
    with pytest.raises(CtapError):run(card,'save',site(),pin='wrong')
    assert len([x for x in card.calls if isinstance(x,tuple)])==1
    assert 'create' not in card.calls and 'write' not in card.calls

def test_corrupt_shared_store_is_not_overwritten():
    card=Card();card.data=b'corrupt'
    before=card.data
    with pytest.raises(BookmarkError):run(card,'save',site())
    assert card.data==before and not card.calls

def test_capacity_failure_precedes_credential_creation():
    card=Card();LargeBlobs(card).put_blob(secrets.token_bytes(32),secrets.token_bytes(760));card.calls=[]
    with pytest.raises(BookmarkError):run(card,'save',site())
    assert 'create' not in card.calls and 'write' not in card.calls

def test_changed_encrypted_record_rejected_by_credential_anchor():
    card=Card();run(card,'save',site());LargeBlobs(card).put_blob(card.creds[0]['key'],pack(site()))
    with pytest.raises(BookmarkError):run(card,'read')

def test_incomplete_write_never_triggers_automatic_repair():
    card=Card();card.creds.append({'anchor':b'a'*32,'key':b'b'*32})
    with pytest.raises(BookmarkError):run(card,'save',site())
    assert 'create' not in card.calls and 'write' not in card.calls

def test_cancel_before_creation_does_not_write():
    card=Card();event=threading.Event();event.set()
    with pytest.raises(BookmarkError):operate(card,'correct','save',site(),event,pin_factory=Pins)
    assert 'create' not in card.calls and 'write' not in card.calls

def test_pin_permissions_for_save_are_scoped():
    card=Card();run(card,'save',site())
    perms=[x[1] for x in card.calls if isinstance(x,tuple)]
    assert perms[0]==ClientPin.PERMISSION.GET_ASSERTION
    assert perms[1]==ClientPin.PERMISSION.GET_ASSERTION|ClientPin.PERMISSION.MAKE_CREDENTIAL|ClientPin.PERMISSION.LARGE_BLOB_WRITE

def test_mismatched_identity_is_rejected_without_touching_key():
    card=Card();s=site();s['destination']='00'*16
    with pytest.raises(BookmarkError):run(card,'save',s)
    assert not card.calls

def test_missing_uv_is_rejected():
    card=Card();run(card,'save',site());original=card.get_assertion
    def no_uv(*args,**kwargs):
        a=original(*args,**kwargs);a.auth_data=AuthenticatorData.create(hashlib.sha256(RP.encode()).digest(),0x81,1,extensions={'credBlob':card.creds[0]['anchor']});return a
    card.get_assertion=no_uv
    with pytest.raises(BookmarkError):run(card,'read')

def test_oversized_decompressed_record_is_rejected():
    card=Card();key=secrets.token_bytes(32);LargeBlobs(card).put_blob(key,b'a'*10000)
    with pytest.raises(BookmarkError):SafeBlobs(card).get_blob(key)

def test_bad_anchor_and_control_label_rejected():
    s=site()
    with pytest.raises(BookmarkError):unpack(pack(s),b'x'*32)
    s['name']='bad\nlabel'
    with pytest.raises(BookmarkError):pack(s)
