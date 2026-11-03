"""Trusted native client. No page-originated scope, reusable bearer tokens or cache."""
import threading
import time
import RNS
from fido2.utils import websafe_decode
from .protocol import check_binding, decode, encode, scope


class Client:
    def __init__(self,destination,service_public_key):
        self.destination=bytes.fromhex(destination); self.public_key=bytes.fromhex(service_public_key)
        service=RNS.Identity(create_keys=False); service.load_public_key(self.public_key)
        self.target=RNS.Destination(service,RNS.Destination.OUT,RNS.Destination.SINGLE,'nomadnetwork','node')
        if self.target.hash!=self.destination: raise ValueError('Service pin does not match destination')
        self.identity=RNS.Identity()  # replaceable, memory-only; never user's usual identity
        self.link=None; self.deadline=0

    def connect(self):
        self.close()
        end=time.monotonic()+30
        RNS.Transport.request_path(self.destination)
        while not RNS.Transport.has_path(self.destination):
            if time.monotonic()>=end: raise TimeoutError('No Reticulum path')
            time.sleep(.1)
        self.link=RNS.Link(self.target)
        retries=0
        while self.link.status != RNS.Link.ACTIVE:
            if time.monotonic()>=end: self.close(); raise TimeoutError('Link failed')
            if self.link.status==RNS.Link.CLOSED:
                if retries>=1: self.close(); raise ConnectionError('Link failed; retry after route recovery')
                retries+=1
                RNS.Transport.request_path(self.destination)
                time.sleep(1)
                self.link=RNS.Link(self.target)
            time.sleep(.1)
        self.link.identify(self.identity)

    def request(self,path,data=None,limit=16384):
        if self.link is None or self.link.status!=RNS.Link.ACTIVE:
            self.deadline=0; raise ConnectionError('Disconnected; re-authentication required')
        receipt=self.link.request(path,data=data,timeout=20,max_response_size=limit)
        end=time.monotonic()+25
        while receipt and receipt.status not in (RNS.RequestReceipt.READY,RNS.RequestReceipt.FAILED):
            if time.monotonic()>=end: raise TimeoutError('Request timed out')
            time.sleep(.05)
        if not receipt or receipt.status!=RNS.RequestReceipt.READY: raise ConnectionError('Request failed')
        return receipt.response

    def begin(self,permissions=('pages:read',),operation=None):
        raw=self.request('/nomadkey/begin',encode({'permissions':permissions,'operation':operation}))
        value=decode(raw)
        if 'error' in value: raise ValueError('Authentication unavailable')
        bound=check_binding(value['binding'],self.destination,self.public_key,self.link.link_id,
                            self.identity.get_public_key(),permissions,operation)
        options=value['options']['publicKey']
        rp,_=scope(self.public_key,self.destination)
        if options['rpId']!=rp or websafe_decode(options['challenge'])!=bound or options.get('userVerification')!='required':
            raise ValueError('Untrusted credential request')
        self.pending_lifetime=value['binding']['lifetime']
        return options

    def complete(self,response):
        # Conservative client expiry begins BEFORE submission; server begins at success.
        sent=time.monotonic()
        value=decode(self.request('/nomadkey/complete',encode(dict(response))))
        if not value.get('ok'): raise ValueError('Authentication rejected')
        if 'expires_in' in value:
            if value['expires_in'] != self.pending_lifetime: raise ValueError('Lifetime mismatch')
            self.deadline=sent+value['expires_in']
        return value

    def read(self,path='/page/index.mu'):
        if time.monotonic()>=self.deadline: self.close(); raise ValueError('Expired')
        raw=self.request(path,limit=65536)
        if time.monotonic()>=self.deadline: self.close(); raise ValueError('Expired')
        if raw==encode({'error':'denied'}): self.close(); raise ValueError('Access denied')
        return raw

    def forget(self):
        try: acknowledged=decode(self.request('/nomadkey/forget')).get('revoked') is True
        except Exception: acknowledged=False
        finally: self.close()
        return {'remote_revocation_acknowledged':acknowledged,'local_state_cleared':True}

    def close(self):
        self.deadline=0
        if self.link is not None:
            self.link.teardown(); self.link=None
