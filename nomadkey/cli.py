import argparse
import json
from pathlib import Path
import RNS
from fido2.webauthn import AttestedCredentialData
from . import store
from .auth import Credential
from .client import Client
from .native import enroll, authenticate


def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest='command',required=True)
    for name in ['enroll','browse']:
        q=sub.add_parser(name); q.add_argument('--pin-file',required=True,help='Public service pin JSON, NOT a FIDO PIN')
        q.add_argument('--rnsconfig'); q.add_argument('--output')
    q=sub.add_parser('import-credential'); q.add_argument('--state',required=True); q.add_argument('--file',required=True)
    q.add_argument('--admin',action='store_true')
    args=p.parse_args()
    if args.command=='import-credential':
        # Only a local OS administrator can invoke this against the service state.
        identity=RNS.Identity.from_file(str(Path(args.state)/'service.identity'))
        destination=RNS.Destination.hash(identity,'nomadnetwork','node')
        bundle=json.loads(Path(args.file).read_text())
        if bundle['service']!=destination.hex() or bundle['service_key']!=identity.get_public_key().hex() or bundle['uv'] is not True:
            raise ValueError('Enrollment service/UV mismatch')
        data=AttestedCredentialData(bytes.fromhex(bundle['public_data']))
        if data.credential_id.hex()!=bundle['credential_id']: raise ValueError('Credential ID mismatch')
        path=Path(args.state)/'credentials.json'; records=store.load(path)
        records[data.credential_id.hex()]=Credential(data,frozenset(['pages:read','admin'] if args.admin else ['pages:read']),bundle['counter'])
        store.save(path,records)
        print('Imported public credential. Restart NomadKey to load; all sessions invalidate.')
        return
    from fido2.pcsc import CtapPcscDevice
    devices=list(CtapPcscDevice.list_devices())
    if not devices: raise RuntimeError('No NFC FIDO2 authenticator present')
    pin=json.loads(Path(args.pin_file).read_text())
    client=Client(pin['destination'],pin['public_key'])
    if args.command=='enroll':
        bundle=enroll(devices[0],client.public_key,client.destination)
        if not args.output: raise ValueError('--output required for public enrollment bundle')
        Path(args.output).write_text(json.dumps(bundle))
        print('Public credential bundle saved; trusted local import still required.')
    else:
        RNS.Reticulum(configdir=args.rnsconfig,loglevel=RNS.LOG_ERROR)
        client.connect(); authenticate(client,devices[0])
        try:
            while True:
                command=input('read / forget: ').strip()
                if command=='forget': print(client.forget()); break
                if command=='read': print(client.read().decode())
        finally: client.close()


if __name__=='__main__': main()
