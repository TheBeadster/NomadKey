import argparse
import json
import os
import threading
import time
from pathlib import Path
import RNS

from .auth import Auth, Denied
from .content import Content
from .protocol import MAX_MESSAGE, decode, encode
from . import store


class Server:
    def __init__(self, state, content, routes, lifetime=300, status_page=False, browser_login=False):
        self.state=Path(state); self.state.mkdir(mode=0o700,parents=True,exist_ok=True)
        identity_path=self.state/'service.identity'
        if identity_path.exists():
            identity=RNS.Identity.from_file(str(identity_path))
            if identity is None: raise RuntimeError('Cannot load service identity')
        else:
            identity=RNS.Identity(); identity.to_file(str(identity_path)); os.chmod(identity_path,0o600)
        self.destination=RNS.Destination(identity,RNS.Destination.IN,RNS.Destination.SINGLE,'nomadnetwork','node')
        self.destination.set_max_request_size(MAX_MESSAGE)
        self.auth=Auth(identity.get_public_key(),self.destination.hash,store.load(self.state/'credentials.json'),lifetime)
        from .status_page import StatusPage
        providers={'/page/index.mu': StatusPage(self.state)} if status_page else None
        self.content=Content(self.auth,content,routes,providers)
        self.browser_login=browser_login
        self.links={}; self.link_times=[]; self.lock=threading.RLock()
        self.destination.set_link_established_callback(self.connected)
        for path in ['/nomadkey/discover','/nomadkey/begin','/nomadkey/complete','/nomadkey/forget',*(['/page/forget.mu'] if browser_login else []),*routes]:
            self.destination.register_request_handler(path,self.handle,allow=RNS.Destination.ALLOW_ALL)
        self.running=True
        threading.Thread(target=self.sweep,daemon=True).start()

    def connected(self,link):
        with self.lock:
            now=time.monotonic()
            self.link_times=[t for t in self.link_times if t>now-60]
            if len(self.links)>=32 or len(self.link_times)>=60:
                link.teardown(); return
            self.link_times.append(now)
            self.links[link.link_id]=(link,now)
            link.set_link_closed_callback(self.closed)

    def closed(self,link):
        with self.lock:
            self.links.pop(link.link_id,None); self.auth.forget(link.link_id)

    def sweep(self):
        while self.running:
            time.sleep(1)
            with self.lock:
                for key,(link,born) in list(self.links.items()):
                    with self.auth.lock:
                        self.auth._sweep()
                        authorized=key in self.auth.sessions
                        pending=key in self.auth.pending
                    if not authorized and not pending and time.monotonic()-born>90:
                        link.teardown()

    def handle(self,path,data,request_id,link_id,remote_identity,requested_at):
        # Transport passes these bindings; request payloads cannot override them.
        try:
            if link_id not in self.links: raise Denied('link rejected')
            if path=='/nomadkey/discover':
                return encode({'v':1,'service':self.destination.hash.hex(),'service_key':self.auth.public_key.hex(),'lifetime':self.auth.lifetime})
            if self.browser_login and path=='/page/forget.mu':
                self.auth.forget(link_id)
                return self.login_page('This connection has been logged out.')
            if self.browser_login and path=='/page/index.mu' and data in (None,b'',{}):
                try:
                    if remote_identity is None: raise Denied('identify required')
                    self.auth.require(link_id,remote_identity.get_public_key())
                except Denied:
                    return self.login_page()
            if remote_identity is None: raise Denied('identify required')
            client=remote_identity.get_public_key()
            if path=='/nomadkey/forget': return encode(self.auth.forget(link_id))
            if path=='/nomadkey/begin':
                value=decode(data)
                if set(value)-{'permissions','operation'}: raise Denied('unknown fields')
                return encode(self.auth.begin(link_id,client,tuple(value.get('permissions',['pages:read'])),value.get('operation')))
            if path=='/nomadkey/complete':
                with self.auth.lock:
                    result=self.auth.complete(link_id,client,decode(data))
                    try: store.save(self.state/'credentials.json',self.auth.credentials)
                    except Exception:
                        self.auth.sessions.clear(); self.auth.pending.clear(); raise
                return encode(result)
            body=self.content.read(path,link_id,client,data)
            if self.browser_login and path.startswith('/page/'):
                body=b'#!nomadkey-v1 private\n#!c=0\n'+body+b'\n\n`[Forget me`/page/forget.mu]\n'
                if len(body)>65536: raise Denied('content too large')
            return body
        except Exception:
            # No assertion, request data, content, exception details or identities in logs.
            return encode({'error':'denied'})

    @staticmethod
    def login_page(message='Authentication is required to read this site.'):
        return ('#!nomadkey-v1 public\n#!c=0\n>PiMonitor private site\n\n'+message+
                '\n\nOpen the fingerprint menu and choose Authenticate with NFC key.\n'
                'Verify the full service address, then use your enrolled Flex or YubiKey.\n'
                'Access lasts five minutes. Browsing never extends it.\n\n'
                '`[Forget me`/page/forget.mu]\n').encode()


def main():
    p=argparse.ArgumentParser(); p.add_argument('--state',required=True); p.add_argument('--rnsconfig',required=True)
    p.add_argument('--content',required=True); p.add_argument('--manifest',required=True); p.add_argument('--lifetime',type=int,default=300)
    p.add_argument('--status-page',action='store_true',help='Serve protected live host status at /page/index.mu')
    p.add_argument('--browser-login',action='store_true',help='Public login index and authenticated normal-browser pages')
    args=p.parse_args()
    RNS.Reticulum(configdir=args.rnsconfig,loglevel=RNS.LOG_ERROR)
    server=Server(args.state,args.content,json.loads(Path(args.manifest).read_text()),args.lifetime,args.status_page,args.browser_login)
    print(json.dumps({'destination':server.destination.hash.hex(),'public_key':server.auth.public_key.hex()}),flush=True)
    # TCP interface startup is asynchronous. An immediate announce can be lost
    # before the uplink exists, leaving stale paths after a service restart.
    for _ in range(3):
        time.sleep(2)
        server.destination.announce(app_data=b'PiMonitor | NomadKey')
    while True:
        time.sleep(300)
        server.destination.announce(app_data=b'PiMonitor | NomadKey')


if __name__=='__main__': main()
