import pytest
from nomadkey.android_nfc import AndroidNfcDevice
from fido2.hid import CTAPHID


class Bridge:
    def __init__(self,responses): self.responses=iter(responses); self.sent=[]
    def transceive(self,data): self.sent.append(data); return next(self.responses)
    def close(self): pass


def test_short_chaining():
    b=Bridge([b'FIDO_2_0\x90\0',b'\x90\0',b'abc\x61\x02',b'de\x90\0'])
    d=AndroidNfcDevice(b)
    assert d.call(CTAPHID.CBOR,b'x'*251)==b'abcde'
    assert b.sent[1][0]==0x90
    assert b.sent[-1]==bytes.fromhex('00c0000002')


def test_bad_applet():
    with pytest.raises(ValueError): AndroidNfcDevice(Bridge([b'\x6a\x82']))
