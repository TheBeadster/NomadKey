"""Real loopback RNS host test. Only synthetic SMS and software FIDO2 credentials."""
import json,pathlib,subprocess,sys,tempfile,time,socket,sqlite3
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tests'))
import RNS
from test_native import SoftwareCtap
from nomadkey import browser,store
from nomadkey.auth import Credential
from nomadkey.client import Client

root=pathlib.Path(tempfile.mkdtemp(prefix='nomadkey-host-smoke-'))
(root/'state').mkdir();(root/'server').mkdir();(root/'client').mkdir()
service=RNS.Identity();service.to_file(str(root/'state/service.identity'))
destination=RNS.Destination.hash(service,'nomadnetwork','node')
device=SoftwareCtap();data=device.authenticator.data
store.save(root/'state/credentials.json',{data.credential_id.hex():Credential(data,frozenset({'pages:read','notifications:manage'}))})
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
(root/'server/config').write_text(f'[reticulum]\n share_instance = No\n[interfaces]\n [[test]]\n type = TCPServerInterface\n enabled = Yes\n listen_ip = 127.0.0.1\n listen_port = {port}\n')
(root/'client/config').write_text(f'[reticulum]\n share_instance = No\n[interfaces]\n [[test]]\n type = TCPClientInterface\n enabled = Yes\n target_host = 127.0.0.1\n target_port = {port}\n')
code='''
import sys,json,time,RNS
from nomadkey.host import HostServer
class Bridge:
 def smsPage(self,offset,anchor):
  return json.dumps({'messages':[{'sender':'Synthetic','timestamp':0,'body':'TEST-PRIVATE-'+str(i)} for i in range(offset,min(offset+2,5))],'anchor':5,'more':offset+2<5})
RNS.Reticulum(configdir=sys.argv[1]+'/server',loglevel=RNS.LOG_CRITICAL)
s=HostServer(sys.argv[1],Bridge(),{'mode':'sms','lifetime':3})
while True:
 s.destination.announce();time.sleep(1)
'''
log=(root/'test.log').open('w')
process=subprocess.Popen([sys.executable,'-c',code,str(root)],stdout=log,stderr=log)
try:
    time.sleep(2)
    if process.poll() is not None:raise RuntimeError((root/'test.log').read_text())
    RNS.Reticulum(configdir=str(root/'client'),loglevel=RNS.LOG_CRITICAL)
    c=Client(destination.hex(),service.get_public_key().hex());c.connect()
    browser.AndroidNfcDevice=lambda _:device
    def action(name):
        req=browser.operation(c.link,c.identity,name)
        signed=browser.sign(None,'synthetic',req)
        return json.loads(browser.operation(c.link,c.identity,'complete',signed))
    assert b'TEST-PRIVATE' not in c.request('/page/index.mu')
    action('begin')
    assert b'TEST-PRIVATE-0' in c.request('/page/index.mu')
    assert b'TEST-PRIVATE-2' in c.request('/page/older.mu')
    before=json.loads(browser.operation(c.link,c.identity,'state'))['remaining']
    action('subscribe')
    after=json.loads(browser.operation(c.link,c.identity,'state'))['remaining']
    assert after<=before
    db=sqlite3.connect(root/'host.sqlite')
    assert db.execute('SELECT client FROM subscribers').fetchone()[0]==c.identity.get_public_key().hex()
    clone=Client(destination.hex(),service.get_public_key().hex());clone.identity=c.identity;clone.connect()
    assert b'TEST-PRIVATE' not in clone.request('/page/index.mu')
    end=time.monotonic()+3.1
    while time.monotonic()<end:c.request('/page/index.mu');time.sleep(.1)
    assert b'TEST-PRIVATE' not in c.request('/page/older.mu')
    action('begin');action('unsubscribe')
    assert not db.execute('SELECT client FROM subscribers').fetchall()
    assert json.loads(browser.operation(c.link,c.identity,'forget'))['remote_revocation_acknowledged']
    c.connect();assert b'TEST-PRIVATE' not in c.request('/page/index.mu')
    c.close();clone.close();db.close()
    assert not any(b'TEST-PRIVATE' in p.read_bytes() for p in (root/'client').rglob('*') if p.is_file())
    print(json.dumps({'real_RNS_host':'PASS','synthetic_sms_pagination':True,'fresh_subscription':True,'no_lifetime_extension':True,'cloned_link_denied':True,'absolute_expiry':True,'forget_acknowledged':True,'no_private_client_files':True,'hardware_tested':False}))
finally:
    process.terminate();process.wait(timeout=10);log.close()
