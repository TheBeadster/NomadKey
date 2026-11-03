"""Small Columba feature bridge using the reusable native client and official RNS."""
import json
import re
import time
from pathlib import Path
import RNS
from .client import Client
from .android_nfc import AndroidNfcDevice
from .native import authenticate, enroll

client=None
stack=None
stack_host=None


def configure(root,host,destination,public_key):
    global client,stack,stack_host
    if not re.fullmatch(r'[A-Za-z0-9.-]{1,253}',host): raise ValueError('Invalid transport host')
    if client: client.forget()
    client=Client(destination.strip().lower(),public_key.strip().lower())
    if stack and stack_host!=host: raise ValueError('Restart app to change transport host')
    if not stack:
        config=Path(root)/'nomadkey-rns'; config.mkdir(parents=True,exist_ok=True)
        (config/'config').write_text('[reticulum]\n  share_instance = No\n  enable_transport = No\n[interfaces]\n  [[NomadKey test uplink]]\n    type = TCPClientInterface\n    enabled = Yes\n    target_host = '+host+'\n    target_port = 444\n')
        stack=RNS.Reticulum(configdir=str(config),loglevel=RNS.LOG_ERROR); stack_host=host
    return 'Service pin checked; temporary client identity created.'


def connect():
    client.connect()
    return 'Connected. Authentication required.'


def nfc(bridge,pin,operation):
    device=AndroidNfcDevice(bridge)
    try:
        if operation=='enroll':
            return json.dumps(enroll(device,client.public_key,client.destination,pin))
        if operation!='authenticate': raise ValueError('Invalid operation')
        return json.dumps(authenticate(client,device,pin))
    finally: device.close()


def read(): return client.read().decode('utf-8',errors='replace')
def remaining(): return max(0,client.deadline-time.monotonic()) if client else 0
def forget(): return json.dumps(client.forget()) if client else json.dumps({'local_state_cleared':True,'remote_revocation_acknowledged':False})
