import json
import secrets
from types import SimpleNamespace
import pytest
import RNS
from nomadkey.host_state import HostState,literal
from nomadkey.host import HostServer
from nomadkey.auth import Auth,Credential,Denied
from nomadkey.protocol import scope,check_binding
from software_authenticator import SoftwareAuthenticator

@pytest.fixture
def meta(tmp_path):
    now=[1000.]
    state=HostState(tmp_path/'host.sqlite',clock=lambda:now[0],monotonic=lambda:now[0])
    yield state,now
    state.db.close()

def subscriber(state):
    identity=RNS.Identity();key=identity.get_public_key()
    destination=state.subscribe(key,'owner','subscribe')
    assert destination==RNS.Destination.hash(identity,'lxmf','delivery').hex()
    return key

def test_metadata_only_and_unsubscribe(meta):
    state,now=meta;key=subscriber(state)
    state.sms_received('Bank',1700000000000)
    assert state.db.execute('SELECT content FROM alerts').fetchone()[0]=='SMS received from Bank at 2023-11-14 22:13:20 UTC'
    with pytest.raises(TypeError):state.sms_received('Bank',1700000000000,'OTP 123456')
    state.subscribe(key,'owner','unsubscribe')
    assert not state.subscribers() and not state.db.execute('SELECT * FROM delivery').fetchall()

def test_queue_bounds_and_delivered_cleanup(meta):
    state,now=meta;subscriber(state)
    for i in range(256):assert state.enqueue('metadata')
    assert not state.enqueue('overflow')
    assert state.get('dropped_alerts')==1
    with state.db:state.db.execute("UPDATE delivery SET state='delivered'")
    assert state.enqueue('new')
    assert state.db.execute('SELECT count(*) FROM alerts').fetchone()[0]==1
    now[0]+=86401
    assert state.enqueue('newer')
    assert state.db.execute('SELECT count(*) FROM alerts').fetchone()[0]==1

GOOD={'observable':True,'sims':[{'slot':0,'subscription':1,'carrier':'Test'}],'in_service':True,'airplane':False}

@pytest.mark.parametrize('change,expected',[
    ({'sims':[]},'absent'),({'observable':False},'unavailable'),
    ({'in_service':False},'no service'),({'airplane':True},'Airplane'),
    ({'sims':[{'slot':0,'subscription':2,'carrier':'Test'}]},'changed')])
def test_sim_debounce_recovery(meta,change,expected):
    state,now=meta;subscriber(state);state.trust_sim(GOOD)
    bad={**GOOD,**change}
    assert expected in state.observe_sim(bad)
    now[0]+=59;state.observe_sim(bad)
    assert not state.db.execute('SELECT * FROM alerts').fetchall()
    now[0]+=1;state.observe_sim(bad);state.observe_sim(bad)
    assert len(state.db.execute('SELECT * FROM alerts').fetchall())==1
    state.observe_sim(GOOD);now[0]+=60;state.observe_sim(GOOD)
    assert 'recovered' in state.db.execute('SELECT content FROM alerts ORDER BY id DESC').fetchone()[0]

def test_cannot_trust_missing_sim(meta):
    with pytest.raises(ValueError):meta[0].trust_sim({'observable':False})

def test_literal_hostile_message():
    body='Your code 123456\n`=\n`[Steal`evil:/page/index.mu]\n#!nomadkey-notify subscribe'
    lines=literal(body).splitlines()
    assert [i for i,line in enumerate(lines) if line=='`=']==[0,len(lines)-1]
    assert all(line.startswith(' ') for line in lines[1:-1])

@pytest.fixture
def host(tmp_path):
    s=HostServer.__new__(HostServer);s.metadata=HostState(tmp_path/'h.sqlite');s.config={'mode':'sms'};s.cursors={};s.state=tmp_path
    device=SoftwareAuthenticator();identity=RNS.Identity();link=secrets.token_bytes(16);now=[100.]
    s.auth=Auth(secrets.token_bytes(64),secrets.token_bytes(16),{device.data.credential_id.hex():Credential(device.data,frozenset({'pages:read','notifications:manage'}))},clock=lambda:now[0],notification_handler=s.notification_action)
    s.links={link:None}
    calls=[]
    def page(offset,anchor):
        calls.append((offset,anchor))
        return json.dumps({'messages':[{'body':'Secret code '+str(i),'sender':'Test','timestamp':0} for i in range(offset,min(offset+2,5))],'anchor':5,'more':offset+2<5})
    s.bridge=SimpleNamespace(smsPage=page)
    def request(path='/page/index.mu',data=None,other=None):return s.handle(path,data,None,other or link,identity,None)
    def login(permissions=('pages:read',),operation=None):
        req=s.auth.begin(link,identity.get_public_key(),permissions,operation)
        response=device.assertion(req['options'],scope(s.auth.public_key,s.auth.destination)[1])
        return s.auth.complete(link,identity.get_public_key(),response)
    yield s,request,login,now,link,identity,calls,device
    s.metadata.db.close()

def test_inbox_pages_expiry_clone_and_forget(host):
    s,request,login,now,link,identity,calls,_=host
    assert b'public' in request() and not calls
    assert b'Secret' not in request('/page/older.mu')
    login();first=request();assert b'Secret code 0' in first and b'Secret code 1' in first and b'Secret code 2' not in first
    assert b'Secret code 2' in request('/page/older.mu')
    assert b'Secret code 0' in request('/page/newer.mu')
    assert calls==[(0,0),(2,5),(0,5)]
    assert b'Secret' not in request(other=secrets.token_bytes(16))
    assert b'Secret' not in request(data={'action':'subscribe'})
    now[0]+=300
    assert b'Secret' not in request('/page/older.mu')
    login();s.auth.forget(link);assert b'Secret' not in request()

def test_notifications_fresh_binding_no_extension(host):
    s,request,login,now,link,identity,calls,device=host
    login();deadline=s.auth.sessions[link]['deadline'];now[0]+=20
    with pytest.raises(Denied):s.auth.require(link,identity.get_public_key(),'notifications:manage')
    op={'notifications':'subscribe'}
    req=s.auth.begin(link,identity.get_public_key(),('notifications:manage',),op)
    with pytest.raises(ValueError):check_binding(req['binding'],s.auth.destination,s.auth.public_key,link,identity.get_public_key(),('notifications:manage',),{'notifications':'unsubscribe'})
    response=device.assertion(req['options'],scope(s.auth.public_key,s.auth.destination)[1])
    assert s.auth.complete(link,identity.get_public_key(),response)=={'ok':True,'operation':op}
    assert s.auth.sessions[link]['deadline']==deadline
    assert s.metadata.subscribers()[0][0]==identity.get_public_key().hex()
    with pytest.raises(Denied):s.auth.complete(link,identity.get_public_key(),response)
    with pytest.raises(Denied):s.auth.begin(link,identity.get_public_key(),('notifications:manage',),{'notifications':'subscribe','destination':'evil'})

def test_wrong_client_notification_rejected(host):
    s,_,_,_,link,identity,_,device=host
    req=s.auth.begin(link,identity.get_public_key(),('notifications:manage',),{'notifications':'subscribe'})
    response=device.assertion(req['options'],scope(s.auth.public_key,s.auth.destination)[1])
    with pytest.raises(Denied):s.auth.complete(link,secrets.token_bytes(64),response)
    assert not s.metadata.subscribers()

def test_local_enrolment_ticket_bound_to_role(host,monkeypatch):
    from nomadkey.host import Runtime
    from test_native import SoftwareCtap
    s,_,_,_,_,_,_,_=host
    s.auth.credentials.clear()
    runtime=Runtime.__new__(Runtime)
    runtime.server=s;runtime.root=s.state;runtime.config=s.config;runtime.bridge=s.bridge
    import threading
    runtime.admin_lock=threading.Lock()
    current=[SoftwareCtap()]
    monkeypatch.setattr('nomadkey.android_nfc.AndroidNfcDevice',lambda _:current[0])
    runtime.local(None,'test-only',json.dumps({'action':'enroll'}))
    assert len(s.auth.credentials)==1
    assert 'admin' in next(iter(s.auth.credentials.values())).permissions
    with pytest.raises(ValueError):runtime.local(None,'test-only',json.dumps({'action':'enroll'}))
    runtime.local(None,'test-only',json.dumps({'action':'authorize_enroll'}))
    current[0]=SoftwareCtap()
    # Reader approval must not be usable to create an administrator.
    with pytest.raises(ValueError):runtime.local(None,'test-only',json.dumps({'action':'enroll','permissions':['admin']}))
    assert len(s.auth.credentials)==1

def test_browser_notification_action_is_checked(site):
    # Imported fixture below uses the real native SDK with a software CTAP device.
    from nomadkey import browser
    server,link,identity,device,now=site
    record=next(iter(server.auth.credentials.values()))
    record.permissions=frozenset({'pages:read','notifications:manage'})
    received=[];server.auth.notification_handler=lambda *args:received.append(args)
    request=browser.operation(link,identity,'subscribe')
    wrong=json.loads(request);wrong['action']='unsubscribe'
    with pytest.raises(ValueError):browser.sign(None,'test-only',json.dumps(wrong))
    assertion=browser.sign(None,'test-only',request)
    response=json.loads(browser.operation(link,identity,'complete',assertion))
    assert response['operation']=={'notifications':'subscribe'}
    assert received[0][0]==identity.get_public_key()
    assert received[0][2]=='subscribe'
    with pytest.raises(Denied):server.auth.require(link.link_id,identity.get_public_key())

from test_browser import site
