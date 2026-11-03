"""Real RNS transport smoke using a temporary SOFTWARE credential. Never human hardware."""
import json, os, pathlib, subprocess, sys, tempfile, time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tests'))
import RNS
from software_authenticator import SoftwareAuthenticator
from nomadkey.auth import Credential
from nomadkey import store
from nomadkey.client import Client
from nomadkey.protocol import scope,encode,decode

root=pathlib.Path(tempfile.mkdtemp(prefix='nomadkey-software-'))
state=root/'state'; state.mkdir()
identity=RNS.Identity(); identity.to_file(str(state/'service.identity'))
dest=RNS.Destination.hash(identity,'nomadnetwork','node')
device=SoftwareAuthenticator()
store.save(state/'credentials.json',{device.data.credential_id.hex():Credential(device.data,frozenset({'pages:read'}))})
(root/'server').mkdir(); (root/'client').mkdir()
(root/'server'/'config').write_text('[reticulum]\n share_instance = No\n enable_transport = Yes\n[interfaces]\n [[test]]\n type = TCPServerInterface\n enabled = Yes\n listen_ip = 127.0.0.1\n listen_port = 44221\n')
(root/'client'/'config').write_text('[reticulum]\n share_instance = No\n[interfaces]\n [[test]]\n type = TCPClientInterface\n enabled = Yes\n target_host = 127.0.0.1\n target_port = 44221\n')
repo=pathlib.Path(__file__).resolve().parents[1]
log=(root/'server.log').open('w')
proc=subprocess.Popen([sys.executable,'-m','nomadkey.server','--state',str(state),'--rnsconfig',str(root/'server'),'--content',str(repo/'test-content'),'--manifest',str(repo/'test-content/routes.json'),'--lifetime','3'],stdout=log,stderr=log)
try:
    time.sleep(3)
    if proc.poll() is not None: raise RuntimeError((root/'server.log').read_text())
    RNS.Reticulum(configdir=str(root/'client'),loglevel=RNS.LOG_ERROR)
    client=Client(dest.hex(),identity.get_public_key().hex()); client.connect()
    assert decode(client.request('/page/index.mu'))=={'error':'denied'}
    request=client.begin(); client.complete(device.assertion({'publicKey':request},scope(client.public_key,client.destination)[1]))
    assert b'synthetic protected' in client.read()
    clone=Client(dest.hex(),identity.get_public_key().hex()); clone.identity=client.identity; clone.connect()
    assert decode(clone.request('/page/index.mu'))=={'error':'denied'}
    until=time.monotonic()+3.5
    while time.monotonic()<until:
        client.request('/page/index.mu'); time.sleep(.15)
    assert decode(client.request('/page/index.mu'))=={'error':'denied'}
    request=client.begin(); client.complete(device.assertion({'publicKey':request},scope(client.public_key,client.destination)[1]))
    assert client.forget()['remote_revocation_acknowledged']
    clone.close()
    print(json.dumps({'real_RNS_transport':'PASS','unknown_denied':True,'software_FIDO2':True,'cloned_identity_denied':True,'continuous_activity_expiry':True,'forget_acknowledged':True,'hardware_tested':False}))
finally:
    proc.terminate(); proc.wait(timeout=10); log.close()
