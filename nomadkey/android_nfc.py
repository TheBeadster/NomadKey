"""ISO 7816 NFC CTAP transport. Crypto and PIN protocol are in python-fido2.

Short-APDU chaining follows FIDO CTAP NFC; hardware interoperability is pending.
"""
import time
from fido2.ctap import CtapDevice, CtapError
from fido2.hid import CAPABILITY, CTAPHID, STATUS


class AndroidNfcDevice(CtapDevice):
    def __init__(self,bridge):
        self.bridge=bridge
        result=self.exchange(bytes.fromhex('00a4040008a0000006472f000100'))
        if result[-2:]!=b'\x90\x00': raise ValueError('FIDO applet unavailable')

    @property
    def capabilities(self): return CAPABILITY.CBOR

    def exchange(self,apdu):
        result=bytes((int(x)&255 for x in self.bridge.transceive(apdu)))
        if len(result)<2 or len(result)>8192: raise ValueError('Invalid NFC response')
        return result

    def chain(self,cla,ins,p1,p2,data=b''):
        while len(data)>250:
            part,data=data[:250],data[250:]
            response=self.exchange(bytes([cla|0x10,ins,p1,p2,len(part)])+part)
            if response[-2:]!=b'\x90\x00': raise ValueError('NFC chaining failed')
        apdu=bytes([cla,ins,p1,p2])+(bytes([len(data)])+data if data else b'')+b'\0'
        response=self.exchange(apdu); body=response[:-2]; status=response[-2:]
        for _ in range(64):
            if status[0]!=0x61: return body,status
            response=self.exchange(bytes([0,0xc0,0,0,status[1]]))
            body+=response[:-2]; status=response[-2:]
            if len(body)>16384: raise ValueError('NFC response too large')
        raise ValueError('NFC chaining limit')

    def call(self,cmd,data=b'',event=None,on_keepalive=None):
        if cmd!=CTAPHID.CBOR: raise CtapError(CtapError.ERR.INVALID_COMMAND)
        deadline=time.monotonic()+60
        body,status=self.chain(0x80,0x10,0x80,0,data)
        while status==b'\x91\x00':
            if time.monotonic()>=deadline or (event and event.is_set()):
                self.chain(0x80,0x11,0x11,0)
                raise TimeoutError('NFC cancelled')
            if on_keepalive and body: on_keepalive(STATUS(body[0]))
            time.sleep(.1)
            body,status=self.chain(0x80,0x11,0,0)
        if status!=b'\x90\x00': raise CtapError(CtapError.ERR.OTHER)
        return body

    def close(self): self.bridge.close()

    @classmethod
    def list_devices(cls): return iter(())
