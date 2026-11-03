"""Native FIDO2 ceremonies; no browser or platform/cloud credential provider."""
import getpass
import threading
from fido2.client import Fido2Client, DefaultClientDataCollector, UserInteraction
from fido2.server import Fido2Server
from .protocol import scope


class Interaction(UserInteraction):
    def __init__(self,pin=None): self.pin=pin
    def request_pin(self,permissions,rp_id):
        return self.pin if self.pin is not None else getpass.getpass('Authenticator PIN: ')
    def request_uv(self,permissions,rp_id): return True


def fido_client(device,public_key,destination,pin=None):
    rp,origin=scope(public_key,destination)
    collector=DefaultClientDataCollector(origin,verify=lambda requested,observed:requested==rp and observed==origin)
    return Fido2Client(device,collector,Interaction(pin))


def authenticate(client,device,pin=None,cancel=None):
    options=client.begin()
    fido=fido_client(device,client.public_key,client.destination,pin)
    event=cancel if cancel is not None else threading.Event()
    timer=threading.Timer(60,event.set); timer.start()
    try:
        if event.is_set(): raise TimeoutError('Cancelled')
        response=fido.get_assertion(options,event).get_response(0)
        if event.is_set(): raise TimeoutError('Cancelled')
        return client.complete(response)
    finally: timer.cancel()


def enroll(device,public_key,destination,pin=None,cancel=None):
    rp,origin=scope(public_key,destination)
    server=Fido2Server({'id':rp,'name':'NomadKey'},verify_origin=lambda o:o==origin)
    options,state=server.register_begin({'id':b'nomadkey-local-enrollment','name':'NomadKey owner','displayName':'NomadKey owner'},
                                        user_verification='required',resident_key_requirement='discouraged')
    client=fido_client(device,public_key,destination,pin)
    event=cancel if cancel is not None else threading.Event()
    timer=threading.Timer(60,event.set); timer.start()
    try:
        if event.is_set(): raise TimeoutError('Cancelled')
        response=client.make_credential(options.public_key,event)
        if event.is_set(): raise TimeoutError('Cancelled')
        result=server.register_complete(state,response)
        return {'service':destination.hex(),'service_key':public_key.hex(),
                'public_data':bytes(result.credential_data).hex(),'credential_id':result.credential_data.credential_id.hex(),
                'counter':result.counter,'uv':result.is_user_verified()}
    finally: timer.cancel()
