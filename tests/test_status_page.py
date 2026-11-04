import pytest
from nomadkey.auth import Denied
from nomadkey.content import Content
from nomadkey.status_page import StatusPage


class Gate:
    def __init__(self): self.allowed = False
    def require(self, *args):
        if not self.allowed: raise Denied('denied')


def setup(tmp_path, provider):
    (tmp_path / 'index.mu').write_text('fallback')
    gate = Gate()
    return gate, Content(gate, tmp_path, {'/page/index.mu': 'index.mu'}, {'/page/index.mu': provider})


def test_provider_not_called_for_unknown_or_form(tmp_path):
    called = []
    gate, content = setup(tmp_path, lambda: called.append(True))
    with pytest.raises(Denied): content.read('/page/index.mu', b'l', b'c')
    gate.allowed = True
    with pytest.raises(Denied): content.read('/page/index.mu', b'l', b'c', {'action':'x'})
    with pytest.raises(Denied): content.read('/page/other.mu', b'l', b'c')
    assert called == []


def test_expiry_during_status_generation(tmp_path):
    def sample():
        gate.allowed = False
        return b'private sample'
    gate, content = setup(tmp_path, sample)
    gate.allowed = True
    with pytest.raises(Denied): content.read('/page/index.mu', b'l', b'c')


@pytest.mark.parametrize('body', [b'x' * 65537, 'not bytes'])
def test_bounded_status_result(tmp_path, body):
    gate, content = setup(tmp_path, lambda: body)
    gate.allowed = True
    with pytest.raises(Denied): content.read('/page/index.mu', b'l', b'c')


def test_live_status_and_revocation(tmp_path):
    gate, content = setup(tmp_path, StatusPage(tmp_path))
    gate.allowed = True
    body = content.read('/page/index.mu', b'l', b'c')
    assert b'PiMonitor | Private status' in body and b'Storage free:' in body
    assert len(body) < 4096
    gate.allowed = False
    with pytest.raises(Denied): content.read('/page/index.mu', b'l', b'c')
