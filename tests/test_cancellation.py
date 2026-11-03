import secrets
import threading
import pytest
from nomadkey.native import enroll
from test_native import SoftwareCtap


def test_cancelled_enrollment_never_creates_credential():
    class NoCreate(SoftwareCtap):
        def call(self,cmd,data=b'',event=None,on_keepalive=None):
            assert data[0]!=1, 'Cancelled enrollment must not reach makeCredential'
            return super().call(cmd,data,event,on_keepalive)
    event=threading.Event(); event.set()
    with pytest.raises(TimeoutError): enroll(NoCreate(),secrets.token_bytes(64),secrets.token_bytes(16),cancel=event)
