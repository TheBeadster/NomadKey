"""Real RNS normal-browser link test with software CTAP only; no live enrollment."""
import json, pathlib, subprocess, sys, tempfile, time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tests'))
import RNS
from test_native import SoftwareCtap
from nomadkey import browser, store
from nomadkey.auth import Credential
from nomadkey.client import Client

root=pathlib.Path(tempfile.mkdtemp(prefix='nomadkey-browser-'))
state=root/'state';state.mkdir()
service=RNS.Identity();service.to_file(str(state/'service.identity'))
dest=RNS.Destination.hash(service,'nomadnetwork','node')
device=SoftwareCtap();data=device.authenticator.data
store.save(state/'credentials.json',{data.credential_id.hex():Credential(data,frozenset({'pages:read'}))})
for side in ('server','client'): (root/side).mkdir()
(root/'server/config').write_text('[reticulum]\n share_instance = No\n enable_transport = Yes\n[interfaces]\n [[test]]\n type = TCPServerInterface\n enabled = Yes\n listen_ip = 127.0.0.1\n listen_port = 44223\n')
(root/'client/config').write_text('[reticulum]\n share_instance = No\n[interfaces]\n [[test]]\n type = TCPClientInterface\n enabled = Yes\n target_host = 127.0.0.1\n target_port = 44223\n')
repo=pathlib.Path(__file__).resolve().parents[1]
log=(root/'server.log').open('w')
proc=subprocess.Popen([sys.executable,'-m','nomadkey.server','--state',str(state),'--rnsconfig',str(root/'server'),'--content',str(repo/'test-content'),'--manifest',str(repo/'test-content/routes.json'),'--lifetime','3','--browser-login','--status-page'],stdout=log,stderr=log)
try:
    time.sleep(3)
    RNS.Reticulum(configdir=str(root/'client'),loglevel=RNS.LOG_ERROR)
    c=Client(dest.hex(),service.get_public_key().hex());c.connect()
    def page(client=c): return client.request('/page/index.mu')
    assert page().startswith(b'#!nomadkey-v1 public')
    browser.operation(c.link,c.identity,'probe')
    browser.AndroidNfcDevice=lambda _:device
    def login():
        request=browser.operation(c.link,c.identity,'begin')
        assertion=browser.sign(None,'software-test',request)
        assert json.loads(browser.operation(c.link,c.identity,'complete',assertion))['ok']
    login()
    body=page();assert body.startswith(b'#!nomadkey-v1 private') and b'Storage free:' in body
    clone=Client(dest.hex(),service.get_public_key().hex());clone.identity=c.identity;clone.connect()
    assert page(clone).startswith(b'#!nomadkey-v1 public')
    until=time.monotonic()+3.5
    while time.monotonic()<until: page();time.sleep(.1)
    assert page().startswith(b'#!nomadkey-v1 public')
    login();assert b'logged out' in c.request('/page/forget.mu')
    assert page().startswith(b'#!nomadkey-v1 public')
    login();assert json.loads(browser.operation(c.link,c.identity,'forget'))['remote_revocation_acknowledged']
    c.connect();assert page().startswith(b'#!nomadkey-v1 public')
    matches=[]
    for path in (root/'client').rglob('*'):
        if path.is_file() and b'Storage free:' in path.read_bytes(): matches.append(str(path.relative_to(root)))
    assert not matches, matches
    c.close();clone.close()
    print(json.dumps({'real_RNS_browser_flow':'PASS','public_login':True,'same_link_FIDO2':True,'cloned_connection_denied':True,'absolute_expiry':True,'page_forget':True,'control_forget_acknowledged':True,'reconnect_public':True,'private_content_found_in_client_files':False,'hardware_tested':False}))
finally:
    proc.terminate();proc.wait(timeout=10);log.close()
