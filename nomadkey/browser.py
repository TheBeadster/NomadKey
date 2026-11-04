"""Native browser adapter: reuse the transport-owned link, never an address allowlist."""
import json
import threading
import time
import RNS
from fido2.utils import websafe_decode
from .client import Client
from .protocol import decode, scope, check_binding
from .native import fido_client
from .android_nfc import AndroidNfcDevice

_clients = {}
_lock = threading.RLock()


def operation(link, identity, action, payload=''):
    if action not in ('probe','begin','complete','forget','state'):
        raise ValueError('Unsupported operation')
    if len(payload)>16384: raise ValueError('Oversized request')
    key=link.link_id
    with _lock:
        for old,c in list(_clients.items()):
            if c.link is None or c.link.status!=RNS.Link.ACTIVE: _clients.pop(old,None)
        c=_clients.get(key)
        if c is None:
            if action in ('complete','forget','state'): raise ValueError('No current ceremony')
            if len(_clients)>=32: raise ValueError('Too many browser links')
            c=Client(link.destination.hash.hex(),link.destination.identity.get_public_key().hex())
            c.identity=identity; c.link=link; _clients[key]=c
    if action=='probe':
        value=decode(c.request('/nomadkey/discover'))
        if value.get('service')!=c.destination.hex() or value.get('service_key')!=c.public_key.hex():
            raise ValueError('Service verification failed')
    elif action=='begin':
        link.identify(identity)
        options=c.begin()
        # c.begin validates server binding; transport context is independently
        # passed to the NFC process, which validates it again before CTAP.
        value={'options':options,'service':c.destination.hex(),'service_key':c.public_key.hex(),
               'link':key.hex(),'client':identity.get_public_key().hex()}
    elif action=='complete':
        value=c.complete(json.loads(payload))
    elif action=='forget':
        value=c.forget()
        with _lock: _clients.pop(key,None)
    else:
        value={'remaining':max(0,c.deadline-time.monotonic()),'link':key.hex()}
    return json.dumps(value)


def sign(bridge, pin, request_json):
    if len(request_json)>16384: raise ValueError('Oversized ceremony')
    value=json.loads(request_json)
    public=bytes.fromhex(value['service_key']); dest=bytes.fromhex(value['service'])
    Client(dest.hex(),public.hex())  # validates actual destination derived from service key
    options=value['options']; binding=decode(websafe_decode(options['challenge']))
    check_binding(binding,dest,public,bytes.fromhex(value['link']),bytes.fromhex(value['client']),('pages:read',),None)
    rp,_=scope(public,dest)
    if options['rpId']!=rp or options.get('userVerification')!='required': raise ValueError('Untrusted scope')
    device=AndroidNfcDevice(bridge)
    cancel=threading.Event(); timer=threading.Timer(60,cancel.set); timer.start()
    try:
        result=fido_client(device,public,dest,pin).get_assertion(options,cancel).get_response(0)
        if cancel.is_set(): raise TimeoutError('Cancelled')
        return json.dumps(dict(result))
    finally: timer.cancel(); device.close()
