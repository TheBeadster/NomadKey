import secrets
import pytest
from nomadkey.auth import Auth, Credential, Denied
from nomadkey.protocol import scope, check_binding, decode
from nomadkey.content import Content
from software_authenticator import SoftwareAuthenticator


@pytest.fixture
def env():
    now=[100.0]
    device=SoftwareAuthenticator()
    service, dest, link, client = secrets.token_bytes(64), secrets.token_bytes(16), secrets.token_bytes(16), secrets.token_bytes(64)
    auth=Auth(service,dest,{device.data.credential_id.hex():Credential(device.data,frozenset({'pages:read','admin'}))},clock=lambda:now[0])
    return auth,device,link,client,now


def login(env, link=None, client=None):
    a,d,l,c,n=env; l=link or l; c=client or c
    request=a.begin(l,c)
    return a.complete(l,c,d.assertion(request['options'],scope(a.public_key,a.destination)[1]))


def test_unknown_then_login(env):
    a,d,l,c,n=env
    with pytest.raises(Denied): a.require(l,c)
    assert login(env)['expires_in']==300
    assert a.require(l,c)==300


def test_absolute_activity_expiry(env):
    a,d,l,c,n=env; login(env)
    for t in range(100,400):
        n[0]=t; assert a.require(l,c)==400-t
    n[0]=400
    with pytest.raises(Denied): a.require(l,c)


@pytest.mark.parametrize('kind',['wrong_device','wrong_origin','wrong_rp','no_uv','no_up','signature','challenge','wrong_client','wrong_link','expired'])
def test_assertion_rejection(env,kind):
    a,d,l,c,n=env; req=a.begin(l,c); origin=scope(a.public_key,a.destination)[1]
    if kind=='wrong_device': d=SoftwareAuthenticator()
    if kind=='wrong_origin': origin='https://evil.invalid'
    if kind=='wrong_rp': req['options']['publicKey']['rpId']='evil.invalid'
    if kind=='challenge': req['options']['publicKey']['challenge']='AA'*32
    response=d.assertion(req['options'],origin, flags={'no_uv':1,'no_up':4}.get(kind,5))
    if kind=='signature': response['response']['signature']='AA'*64
    if kind=='wrong_client': c=secrets.token_bytes(64)
    if kind=='wrong_link': l=secrets.token_bytes(16)
    if kind=='expired': n[0]+=60
    with pytest.raises(Denied): a.complete(l,c,response)


def test_replay_and_clone(env):
    a,d,l,c,n=env; req=a.begin(l,c); resp=d.assertion(req['options'],scope(a.public_key,a.destination)[1])
    a.complete(l,c,resp)
    with pytest.raises(Denied): a.complete(l,c,resp)
    with pytest.raises(Denied): a.require(secrets.token_bytes(16),c)


def test_forget_and_reconnect(env):
    a,d,l,c,n=env; login(env)
    assert a.forget(l)=={'revoked':True}
    with pytest.raises(Denied): a.require(l,c)
    with pytest.raises(Denied): a.require(secrets.token_bytes(16),c)


def test_restart(env):
    a,d,l,c,n=env; login(env)
    restarted=Auth(a.public_key,a.destination,a.credentials)
    with pytest.raises(Denied): restarted.require(l,c)


def test_wall_clock_irrelevant(env,monkeypatch):
    a,d,l,c,n=env; login(env)
    monkeypatch.setattr('time.time',lambda:-1e15)
    n[0]+=300
    with pytest.raises(Denied): a.require(l,c)


def test_relay_client_binding(env):
    a,d,l,c,n=env; req=a.begin(l,c)
    for args in [(a.destination,a.public_key,secrets.token_bytes(16),c),(secrets.token_bytes(16),a.public_key,l,c),(a.destination,a.public_key,l,secrets.token_bytes(64))]:
        with pytest.raises(ValueError): check_binding(req['binding'],*args,('pages:read',),None)


def test_admin_fresh_operation(env):
    a,d,l,c,n=env; login(env)
    with pytest.raises(Denied): a.require(l,c,'admin')
    op={'remove_credential':d.data.credential_id.hex()}
    req=a.begin(l,c,('admin',),op)
    with pytest.raises(ValueError): check_binding(req['binding'],a.destination,a.public_key,l,c,('admin',),{'remove_credential':'other'})
    resp=d.assertion(req['options'],scope(a.public_key,a.destination)[1])
    assert a.complete(l,c,resp)['operation']==op
    with pytest.raises(Denied): a.require(l,c)
    with pytest.raises(Denied): a.complete(l,c,resp)


@pytest.mark.parametrize('route',['/page/index.mu','/file/test.txt','/media/test.txt'])
def test_all_content_checked(env,tmp_path,route):
    a,d,l,c,n=env; (tmp_path/'test.txt').write_text('private')
    content=Content(a,tmp_path,{route:'test.txt'})
    with pytest.raises(Denied): content.read(route,l,c)
    login(env); assert content.read(route,l,c)==b'private'
    for bad in ['/page/../test.txt','/page/%2e%2e/test.txt',route+'?x=1',route+'/','/unknown']:
        with pytest.raises(Denied): content.read(bad,l,c)
    with pytest.raises(Denied): content.read(route,l,c,{'field_action':'do'})
    n[0]+=300
    with pytest.raises(Denied): content.read(route,l,c)


def test_global_throttle_bounds_identity_churn(env):
    a,d,l,c,n=env
    for _ in range(30): a.begin(secrets.token_bytes(16),secrets.token_bytes(64))
    with pytest.raises(Denied): a.begin(secrets.token_bytes(16),secrets.token_bytes(64))


def test_per_client_throttle(env):
    a,d,l,c,n=env
    for _ in range(5): a.begin(l,c)
    with pytest.raises(Denied): a.begin(l,c)


@pytest.mark.parametrize('raw',[b'[]',b'null',b'{',b'x'*16385,None])
def test_malformed(raw):
    with pytest.raises((ValueError,TypeError)): decode(raw)
