"""Portable trusted-site bookmarks. No network calls; separate local FIDO2 RP."""
import hashlib
import json
import secrets
import threading
import zlib
from fido2 import cbor
from fido2.ctap import CtapError
from fido2.ctap2 import Ctap2
from fido2.ctap2.pin import ClientPin
from fido2.ctap2.blob import LargeBlobs, _lb_unpack
from .android_nfc import AndroidNfcDevice
from .client import Client

RP = 'nomadkey-trust.invalid'
MAX_SITES = 16
MAX_RECORD = 256

class BookmarkError(ValueError):
    pass


def pack(site):
    if not isinstance(site, dict) or set(site) != {'destination', 'public_key', 'name'}:
        raise BookmarkError('Invalid saved-site fields.')
    try:
        dest = bytes.fromhex(site['destination']); public = bytes.fromhex(site['public_key'])
        name = site['name']
        if not isinstance(name, str) or not 1 <= len(name.encode()) <= 64 or any(ord(c)<32 for c in name):
            raise ValueError()
        Client(dest.hex(), public.hex())
        raw = cbor.encode({1:1, 2:dest, 3:public, 4:name})
        if len(raw)>MAX_RECORD: raise ValueError()
        return raw
    except Exception as exc:
        raise BookmarkError('The full destination and service public key do not match.') from exc


def unpack(raw, anchor):
    if not isinstance(raw, bytes) or len(raw)>MAX_RECORD or not isinstance(anchor, bytes) or len(anchor)!=32:
        raise BookmarkError('Invalid NFC bookmark.')
    if hashlib.sha256(raw).digest()!=anchor:
        raise BookmarkError('NFC bookmark integrity check failed. Nothing imported.')
    try:
        value=cbor.decode(raw)
        if not isinstance(value,dict) or set(value)!={1,2,3,4} or type(value[1]) is not int or value[1]!=1:
            raise ValueError()
        site={'destination':value[2].hex(),'public_key':value[3].hex(),'name':value[4]}
        if pack(site)!=raw: raise ValueError()
        return site
    except Exception as exc:
        raise BookmarkError('Invalid NFC bookmark identity or format.') from exc


def capabilities(info):
    required={'credBlob','largeBlobKey','credProtect'}
    supported=(required <= set(info.extensions) and all(info.options.get(k) is True for k in ('rk','clientPin','pinUvAuthToken','largeBlobs'))
               and info.max_cred_blob_length>=32 and 17<=info.max_large_blob<=8192)
    return {'supported':supported,'resident_keys':info.options.get('rk',False),
            'pin_configured':info.options.get('clientPin',False),'scoped_pin_tokens':info.options.get('pinUvAuthToken',False),
            'extensions':[x for x in sorted(required) if x in info.extensions],
            'large_blobs':info.options.get('largeBlobs',False),
            'credential_blob_bytes':info.max_cred_blob_length,'large_blob_bytes':info.max_large_blob}


class SafeBlobs(LargeBlobs):
    """Reject corruption and overflow BEFORE writes; retain other applications' entries."""
    def __init__(self, ctap, protocol=None, token=None):
        super().__init__(ctap,protocol,token)
        self.max_fragment_length=min(self.max_fragment_length,1024)
        if self.max_fragment_length<1 or not 17<=ctap.info.max_large_blob<=8192:
            raise BookmarkError('Unsupported NFC storage limits.')
        self.snapshot=None

    def read_blob_array(self):
        buf=b''; limit=self.ctap.info.max_large_blob
        while len(buf)<=limit:
            frag=self.ctap.large_blobs(len(buf),get=min(self.max_fragment_length,limit-len(buf)+1))[1]
            if not isinstance(frag,bytes) or len(frag)>self.max_fragment_length:
                raise BookmarkError('Invalid NFC storage response.')
            buf+=frag
            if len(buf)>limit: raise BookmarkError('NFC storage is oversized.')
            if len(frag)<self.max_fragment_length: break
        try:
            raw,check=buf[:-16],buf[-16:]
            if len(check)!=16 or hashlib.sha256(raw).digest()[:16]!=check: raise ValueError()
            entries=cbor.decode(raw)
            if not isinstance(entries,list) or len(entries)>64 or cbor.encode(entries)!=raw: raise ValueError()
            for e in entries:
                if (not isinstance(e,dict) or set(e)!={1,2,3} or not isinstance(e[1],bytes)
                    or not isinstance(e[2],bytes) or len(e[2])!=12 or type(e[3]) is not int or not 0<=e[3]<=65536):
                    raise ValueError()
            self.snapshot=buf
            return entries
        except Exception as exc:
            raise BookmarkError('NFC storage is corrupt or unsupported. No write attempted.') from exc

    def get_blob(self, key):
        for entry in self.read_blob_array():
            try: compressed,size=_lb_unpack(key,entry)
            except ValueError: continue
            if not 0<=size<=MAX_RECORD:raise BookmarkError('NFC bookmark is oversized.')
            try:
                stream=zlib.decompressobj(wbits=-zlib.MAX_WBITS)
                raw=stream.decompress(compressed,MAX_RECORD+1)
                if len(raw)!=size or not stream.eof or stream.unconsumed_tail or stream.unused_data:
                    raise ValueError()
                return raw
            except (ValueError,zlib.error) as exc:raise BookmarkError('Invalid compressed bookmark.') from exc
        return None

    def write_blob_array(self, entries):
        data=cbor.encode(entries)
        if len(data)+16>self.ctap.info.max_large_blob:
            raise BookmarkError('Not enough NFC storage. Nothing overwritten.')
        expected=self.snapshot
        self.read_blob_array()
        if expected is None or self.snapshot!=expected:
            raise BookmarkError('NFC storage changed. Stop other key applications and retry.')
        super().write_blob_array(entries)
        if self.read_blob_array()!=entries:
            raise BookmarkError('NFC write could not be verified. Read the key before retrying.')


def _assertions(ctap, protocol, token, event):
    challenge=secrets.token_bytes(32)
    try:
        first=ctap.get_assertion(RP,challenge,extensions={'credBlob':True,'largeBlobKey':True},
            pin_uv_param=protocol.authenticate(token,challenge),pin_uv_protocol=protocol.VERSION,event=event)
    except CtapError as exc:
        if exc.code==CtapError.ERR.NO_CREDENTIALS:return []
        raise
    count=first.number_of_credentials or 1
    if not 1<=count<=MAX_SITES:raise BookmarkError('Too many saved sites. Nothing imported.')
    results=[first]
    for _ in range(count-1):
        if event.is_set():raise BookmarkError('NFC operation timed out.')
        results.append(ctap.get_next_assertion())
    return results


def read_sites(ctap, protocol, token, event):
    blobs=SafeBlobs(ctap); blobs.read_blob_array()
    sites=[]; seen=set()
    for a in _assertions(ctap,protocol,token,event):
        if not a.auth_data.is_user_present() or not a.auth_data.is_user_verified() or a.auth_data.rp_id_hash!=hashlib.sha256(RP.encode()).digest():
            raise BookmarkError('Key verification failed.')
        anchor=(a.auth_data.extensions or {}).get('credBlob')
        key=a.large_blob_key
        if not isinstance(key,bytes) or len(key)!=32:raise BookmarkError('Saved credential has no bookmark storage key.')
        raw=blobs.get_blob(key)
        if raw is None:raise BookmarkError('An incomplete NFC bookmark was found. No automatic repair or overwrite.')
        site=unpack(raw,anchor)
        if site['destination'] in seen:raise BookmarkError('Duplicate NFC bookmarks. Resolve them in trusted administration.')
        seen.add(site['destination']);sites.append(site)
    return sites


def operate(ctap, pin, action, site=None, event=None, pin_factory=ClientPin):
    event=event or threading.Event()
    if action not in ('read','save'):raise BookmarkError('Unsupported bookmark operation.')
    raw=pack(site) if action=='save' else None
    if raw is not None:site=unpack(raw,hashlib.sha256(raw).digest())
    if not capabilities(ctap.info)['supported']:
        raise BookmarkError('This key does not support the required protected bookmark storage, or its FIDO2 PIN is not configured. Nothing changed.')
    if not isinstance(pin,str) or not pin:raise BookmarkError('Enter your existing FIDO2 PIN.')
    blobs=SafeBlobs(ctap);entries=blobs.read_blob_array()
    pc=pin_factory(ctap)
    token=pc.get_pin_token(pin,ClientPin.PERMISSION.GET_ASSERTION,RP)
    sites=read_sites(ctap,pc.protocol,token,event)
    if action=='read':
        if not sites:raise BookmarkError('No NFC saved addresses found on this key.')
        return {'sites':sites}
    for saved in sites:
        if saved['destination']==site['destination']:
            if saved['public_key']!=site['public_key']:raise BookmarkError('Saved identity conflict. Nothing changed.')
            return {'sites':[saved],'already_saved':True}
    if len(sites)>=MAX_SITES:raise BookmarkError('Saved-site limit reached. Nothing changed.')
    # Conservative compressed/encrypted-entry allowance; reject before credential creation.
    estimate=entries+[{1:bytes(len(raw)+128),2:bytes(12),3:len(raw)}]
    if len(cbor.encode(estimate))+16>ctap.info.max_large_blob:
        raise BookmarkError('Not enough free NFC storage. Nothing changed.')
    if ctap.info.remaining_disc_creds==0:raise BookmarkError('No free resident credential slots. Nothing changed.')
    perms=ClientPin.PERMISSION.MAKE_CREDENTIAL|ClientPin.PERMISSION.GET_ASSERTION|ClientPin.PERMISSION.LARGE_BLOB_WRITE
    token=pc.get_pin_token(pin,perms,RP)
    if event.is_set():raise BookmarkError('NFC operation timed out before saving.')
    challenge=secrets.token_bytes(32);anchor=hashlib.sha256(raw).digest()
    made=ctap.make_credential(challenge,{'id':RP,'name':'NomadKey saved addresses'},
        {'id':secrets.token_bytes(32),'name':site['destination'],'displayName':site['name']},
        [{'type':'public-key','alg':-7}],extensions={'credBlob':anchor,'largeBlobKey':True,'credProtect':3},
        options={'rk':True},pin_uv_param=pc.protocol.authenticate(token,challenge),pin_uv_protocol=pc.protocol.VERSION,event=event)
    ext=made.auth_data.extensions or {}
    if (not made.auth_data.is_user_present() or not made.auth_data.is_user_verified() or made.auth_data.rp_id_hash!=hashlib.sha256(RP.encode()).digest()
        or ext.get('credBlob') is not True or ext.get('credProtect')!=3
        or not isinstance(made.large_blob_key,bytes) or len(made.large_blob_key)!=32):
        raise BookmarkError('Key did not confirm protected bookmark creation. Do not retry automatically; inspect the key.')
    if event.is_set():raise BookmarkError('Save interrupted after credential creation. Read the key before retrying.')
    writer=SafeBlobs(ctap,pc.protocol,token)
    writer.put_blob(made.large_blob_key,raw)
    if unpack(writer.get_blob(made.large_blob_key),anchor)!=site:
        raise BookmarkError('Saved address readback failed.')
    verified=read_sites(ctap,pc.protocol,token,event)
    if site not in verified:raise BookmarkError('Saved address could not be rediscovered. Read the key before retrying.')
    return {'sites':[site],'already_saved':False}


def android(bridge,pin,action,site_json=''):
    device=None; event=threading.Event();timer=threading.Timer(60,event.set);timer.start()
    try:
        if len(site_json)>1024:raise BookmarkError('Saved address is too large.')
        device=AndroidNfcDevice(bridge);ctap=Ctap2(device)
        result=operate(ctap,pin,action,json.loads(site_json) if site_json else None,event)
        if event.is_set():raise BookmarkError('NFC operation timed out. A save may be incomplete; read the key before retrying.')
        return json.dumps({'ok':True,**result})
    except BookmarkError as exc:return json.dumps({'ok':False,'message':str(exc)})
    except Exception:return json.dumps({'ok':False,'message':'NFC operation failed. Check the key and PIN. If saving, read the key before retrying; no automatic retry or deletion.'})
    finally:
        timer.cancel()
        if device is not None:device.close()
