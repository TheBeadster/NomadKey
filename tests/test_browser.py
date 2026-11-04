import copy
import json
import secrets
from types import SimpleNamespace
import pytest
import RNS
from nomadkey import browser
from nomadkey.auth import Auth, Credential
from nomadkey.content import Content
from nomadkey.server import Server
from nomadkey.protocol import decode
from test_native import SoftwareCtap


@pytest.fixture
def site(tmp_path, monkeypatch):
    browser._clients.clear()
    device=SoftwareCtap()
    service=RNS.Identity(); identity=RNS.Identity()
    dest=RNS.Destination.hash(service,'nomadnetwork','node')
    now=[100.0]
    server=Server.__new__(Server)
    server.auth=Auth(service.get_public_key(),dest,{device.authenticator.data.credential_id.hex():Credential(device.authenticator.data,frozenset({'pages:read'}))},300,clock=lambda:now[0])
    server.destination=SimpleNamespace(hash=dest)
    server.state=tmp_path
    server.browser_login=True
    (tmp_path/'index.mu').write_text('Private operational data')
    server.content=Content(server.auth,tmp_path,{'/page/index.mu':'index.mu','/page/other.mu':'index.mu'})
    class Link:
        link_id=secrets.token_bytes(16)
        status=RNS.Link.ACTIVE
        destination=SimpleNamespace(hash=dest,identity=service)
        remote=None
        def identify(self,value): self.remote=value
        def request(self,path,data=None,**kwargs):
            response=server.handle(path,data,None,self.link_id,self.remote,None)
            return SimpleNamespace(status=RNS.RequestReceipt.READY,response=response)
        def teardown(self): self.status=RNS.Link.CLOSED;server.auth.forget(self.link_id)
    link=Link();server.links={link.link_id:(link,100)}
    monkeypatch.setattr(browser,'AndroidNfcDevice',lambda bridge:device)
    yield server,link,identity,device,now
    browser._clients.clear()


def authenticate(site):
    server,link,identity,device,now=site
    request=browser.operation(link,identity,'begin')
    assertion=browser.sign(None,'test-only',request)
    result=json.loads(browser.operation(link,identity,'complete',assertion))
    assert result['ok']
    return assertion


def test_public_login_and_authenticated_same_page(site):
    server,link,identity,_,_=site
    public=link.request('/page/index.mu').response
    assert public.startswith(b'#!nomadkey-v1 public')
    assert b'Private operational data' not in public
    assert b'Authentication is required' in public
    assert b'Columba upgrade required' in public
    assert b'github.com/TheBeadster/NomadKey' in public
    assert b'Tap Releases for downloads.' in public
    assert b'alone does not grant access.' in public
    assert decode(link.request('/page/other.mu').response)=={'error':'denied'}
    probe=json.loads(browser.operation(link,identity,'probe'))
    assert probe['service']==link.destination.hash.hex()
    authenticate(site)
    private=link.request('/page/index.mu').response
    assert private.startswith(b'#!nomadkey-v1 private') and b'Private operational data' in private
    assert b'`[Forget me`/page/forget.mu]' in private
    assert json.loads(browser.operation(link,identity,'state'))['remaining']>0


@pytest.mark.parametrize('field',['service','service_key','link','client','rp','uv'])
def test_nfc_rejects_wrong_transport_context(site,field):
    _,link,identity,_,_=site
    value=json.loads(browser.operation(link,identity,'begin'))
    if field=='rp': value['options']['rpId']='other.invalid'
    elif field=='uv': value['options']['userVerification']='preferred'
    else: value[field]='00'*(len(value[field])//2)
    with pytest.raises(Exception): browser.sign(None,'test-only',json.dumps(value))


def test_replay_expiry_and_forget_page(site):
    server,link,identity,_,now=site
    assertion=authenticate(site)
    with pytest.raises(ValueError): browser.operation(link,identity,'complete',assertion)
    # Replay consumes no new authority. Explicitly authenticate again.
    authenticate(site)
    now[0]+=300
    assert link.request('/page/index.mu').response.startswith(b'#!nomadkey-v1 public')
    assert decode(link.request('/page/other.mu').response)=={'error':'denied'}
    authenticate(site)
    assert b'logged out' in link.request('/page/forget.mu').response
    assert link.request('/page/index.mu').response.startswith(b'#!nomadkey-v1 public')


def test_forget_control_and_closed_link(site):
    _,link,identity,_,_=site
    authenticate(site)
    result=json.loads(browser.operation(link,identity,'forget'))
    assert result['remote_revocation_acknowledged']
    assert link.status==RNS.Link.CLOSED
    with pytest.raises(ValueError): browser.operation(link,identity,'state')


def test_login_opt_in_and_rejected_forms(site):
    server,link,_,_,_=site
    assert decode(link.request('/page/index.mu',{'action':'x'}).response)=={'error':'denied'}
    server.browser_login=False
    assert decode(link.request('/page/index.mu').response)=={'error':'denied'}
