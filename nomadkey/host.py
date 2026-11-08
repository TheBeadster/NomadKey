"""Independent Android/Linux host adapter. Android supplies SMS/telephony observations.

No SMS body is persisted here, logged, or passed into the notification sender.
"""
import json
import os
import re
import threading
import time
from pathlib import Path
import RNS
from .auth import Credential, Denied
from .protocol import encode, scope
from .server import Server
from .host_state import HostState, literal
from . import store

HOST_PATHS=('/page/index.mu','/page/older.mu','/page/newer.mu','/page/alerts.mu','/page/alerts-on.mu','/page/alerts-off.mu')


class HostServer(Server):
    def __init__(self,root,bridge,config):
        self.root=Path(root);self.bridge=bridge;self.config=config
        self.metadata=HostState(self.root/'host.sqlite');self.cursors={}
        content=self.root/'content';content.mkdir(exist_ok=True)
        index=content/'index.mu'
        if not index.exists():index.write_text('>Private site\nWelcome to your secure NomadNet host.\n',encoding='utf-8')
        super().__init__(self.root/'state',content,{'/page/index.mu':'index.mu'},config.get('lifetime',300),browser_login=True)
        self.auth.notification_handler=self.notification_action
        for path in HOST_PATHS:self.destination.register_request_handler(path,self.handle,allow=RNS.Destination.ALLOW_ALL)

    def notification_action(self,client,credential,action):
        if self.config.get('mode')!='sms':raise Denied('notifications disabled')
        store.save(self.state/'credentials.json',self.auth.credentials)
        self.metadata.subscribe(client,credential,action)

    def closed(self,link):
        self.cursors.pop(link.link_id,None);super().closed(link)

    def login_page(self,message='Authenticate to read this site.'):
        return ('#!nomadkey-v1 public\n#!c=0\n>NomadKey Host\n'+literal(self.config.get('name','Private site'))+
                '\n'+literal(message)+'\nUse the Columba fingerprint menu to authenticate.\n'
                'Access expires absolutely; browsing does not extend it.\n'
                'Get Columba NomadKey DEV:\ngithub.com/TheBeadster/NomadKey\n'
                '`[Forget me`/page/forget.mu]\n').encode()

    def handle(self,path,data,request_id,link_id,remote_identity,requested_at):
        if path not in HOST_PATHS:return super().handle(path,data,request_id,link_id,remote_identity,requested_at)
        try:
            if link_id not in self.links or remote_identity is None:raise Denied('identified link required')
            client=remote_identity.get_public_key();self.auth.require(link_id,client)
            if data not in (None,b'',{}):raise Denied('forms not accepted')
            if self.config.get('mode')!='sms':
                if path!='/page/index.mu':raise Denied('unknown route')
                body=self.content.read(path,link_id,client,data)
            elif path.startswith('/page/alerts'):
                current=any(row[0]==client.hex() for row in self.metadata.subscribers())
                text='>Notification destinations\nThis device is '+('registered' if current else 'not registered')+'.\n'
                text+='Alerts contain the sender and time, never the SMS body.\n'
                text+='Registration requires a fresh key authentication.\n'
                text+='`[Register this device`/page/alerts-on.mu]\n`[Remove this device`/page/alerts-off.mu]\n'
                if path!='/page/alerts.mu':
                    action='subscribe' if path=='/page/alerts-on.mu' else 'unsubscribe'
                    text='#!nomadkey-notify '+action+'\n'+text+'Use the notification action shown by Columba.\n'
                body=text.encode()
            else:
                offset,anchor=self.cursors.get(link_id,(0,0))
                if path=='/page/index.mu':offset,anchor=0,0
                elif path=='/page/older.mu':offset+=2
                elif path=='/page/newer.mu':offset=max(0,offset-2)
                value=json.loads(str(self.bridge.smsPage(offset,anchor)))
                if value.get('error'):
                    body=('>SMS access unavailable\n'+literal(value['error'])).encode()
                else:
                    messages=value.get('messages',[])
                    if len(messages)>2:raise Denied('oversized provider result')
                    self.cursors[link_id]=(offset,int(value['anchor']))
                    text='>Received SMS\n'+literal(value.get('capability_note',''))
                    for item in messages:
                        stamp=time.strftime('%Y-%m-%d %H:%M:%S UTC',time.gmtime(int(item['timestamp'])/1000))
                        text+='\n'+literal('From: '+str(item['sender'])+'\n'+stamp+'\n\n'+str(item['body']))
                    if not messages:text+='No messages on this page.\n'
                    if offset:text+='`[Back / newer`/page/newer.mu]\n'
                    if value.get('more'):text+='`[Next / older`/page/older.mu]\n'
                    text+='`[Latest messages`/page/index.mu]\n`[Notification settings`/page/alerts.mu]\n'
                    body=text.encode()
            self.auth.require(link_id,client)
            capability=b'#!nomadkey-notifications v1\n' if self.config.get('mode')=='sms' else b''
            result=b'#!nomadkey-v1 private\n#!c=0\n'+capability+body+b'\n`[Home`/page/index.mu]\n`[Forget me`/page/forget.mu]\n'
            if len(result)>65536:
                return b'#!nomadkey-v1 private\n#!c=0\n>Page too large\nThese messages exceed the safe page size. Read them locally; no SMS has been truncated.\n`[Forget me`/page/forget.mu]\n'
            return result
        except Exception:
            if path=='/page/index.mu':return self.login_page()
            return encode({'error':'denied'})


class Runtime:
    def __init__(self,root,bridge,config):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.bridge=bridge;self.config=config;self.stop=threading.Event();self.admin_lock=threading.Lock()
        host=config.get('uplink','mh.beady.com');port=config.get('port',444)
        if not re.fullmatch(r'[A-Za-z0-9.-]{1,253}',host) or type(port)!=int or not 1<=port<=65535:raise ValueError('invalid uplink')
        rnsdir=self.root/'rns';rnsdir.mkdir(exist_ok=True)
        (rnsdir/'config').write_text('[reticulum]\n share_instance = Yes\n shared_instance_type = tcp\n shared_instance_port = 37428\n instance_control_port = 37429\n enable_transport = No\n[interfaces]\n [[Host uplink]]\n type = TCPClientInterface\n enabled = Yes\n target_host = '+host+'\n target_port = '+str(port)+'\n',encoding='utf-8')
        self.stack=RNS.Reticulum(configdir=str(rnsdir),loglevel=RNS.LOG_CRITICAL,shared_instance_type='tcp')
        if not (self.stack.is_connected_to_shared_instance or self.stack.is_shared_instance):
            raise RuntimeError('Local shared-instance port is occupied but unusable; resolve it before starting')
        self.server=HostServer(self.root,bridge,config)
        self.connection='Using local shared Reticulum' if self.stack.is_connected_to_shared_instance else 'Hosting Reticulum service'
        self.sim_status='Not yet checked';self.sms_status='Not yet checked';self.send_lock=threading.RLock();self.inflight={}
        import LXMF
        self.LXMF=LXMF
        self.router=LXMF.LXMRouter(storagepath=str(self.root/'lxmf'))
        self.source=self.router.register_delivery_identity(self.server.destination.identity,display_name='NomadKey Host',stamp_cost=8)
        threading.Thread(target=self.work,daemon=True).start()

    def status(self):
        return json.dumps({'connection':self.connection,'destination':self.server.destination.hash.hex(),
            'public_key':self.server.auth.public_key.hex(),'credentials':len(self.server.auth.credentials),
            'sim':self.sim_status,'sms':self.sms_status,'mode':self.config.get('mode','pages'),
            'subscribers':len(self.server.metadata.subscribers()),'dropped_alerts':self.server.metadata.get('dropped_alerts',0)})

    def work(self):
        announced=0
        while not self.stop.wait(5):
            try:
                self.server.metadata.sweep()
                if time.monotonic()-announced>300:
                    self.server.destination.announce(app_data=(self.config.get('name','NomadKey Host')+' | NomadKey').encode()[:96]);announced=time.monotonic()
                if self.config.get('mode')=='sms':
                    snapshot=json.loads(str(self.bridge.simSnapshot()));self.sim_status=self.server.metadata.observe_sim(snapshot)
                    last=self.server.metadata.get('last_sms')
                    new=json.loads(str(self.bridge.smsEvents(-1 if last is None else int(last))))
                    self.sms_status='SMS access unavailable' if new.get('error') else 'Reading OS-visible inbox; hidden messages cannot be detected'
                    if 'latest' in new:
                        if last is not None:
                            for sms in new.get('events',[]):self.server.metadata.sms_received(sms['sender'],sms['timestamp'])
                        self.server.metadata.put('last_sms',new['latest'])
                    self.deliver()
            except Exception:
                self.sim_status='Observation or delivery unavailable; check host permissions and connectivity'

    def deliver(self):
        meta=self.server.metadata
        with meta.lock,meta.db:
            # LXMF owns retries for a live message. Bound our outstanding messages,
            # and expire them without sending duplicate copies after a silent stall.
            for key,(msg,born) in list(self.inflight.items()):
                if time.monotonic()-born>=600:
                    msg.state=self.LXMF.LXMessage.FAILED
                    meta.db.execute("UPDATE delivery SET state='failed' WHERE alert=? AND client=?",key)
                    self.inflight.pop(key,None)
            if len(self.inflight)>=4:return
            # Revoking the enrolling credential also revokes all its notification destinations.
            for client,credential,_ in meta.subscribers():
                record=self.server.auth.credentials.get(credential)
                if not record or 'notifications:manage' not in record.permissions:
                    meta.db.execute('DELETE FROM subscribers WHERE client=?',(client,))
                    meta.db.execute('DELETE FROM delivery WHERE client=?',(client,))
            jobs=meta.db.execute("SELECT d.alert,d.client,a.content FROM delivery d JOIN alerts a ON a.id=d.alert JOIN subscribers s ON s.client=d.client WHERE d.state='queued' AND d.next<=? AND d.attempts<8 AND a.created>? LIMIT 2",(time.time(),time.time()-86400)).fetchall()
            for aid,client,body in jobs:
                identity=RNS.Identity(create_keys=False);identity.load_public_key(bytes.fromhex(client))
                dest=RNS.Destination(identity,RNS.Destination.OUT,RNS.Destination.SINGLE,'lxmf','delivery')
                msg=self.LXMF.LXMessage(dest,self.source,body,title='NomadKey notification',desired_method=self.LXMF.LXMessage.DIRECT)
                self.inflight[(aid,client)]=(msg,time.monotonic())
                meta.db.execute("UPDATE delivery SET state='sending',attempts=attempts+1 WHERE alert=? AND client=?",(aid,client))
                def finish(success,aid=aid,client=client,msg=msg):
                    with meta.lock,meta.db:
                        current=self.inflight.get((aid,client))
                        if current is None or current[0] is not msg:return
                        self.inflight.pop((aid,client),None)
                        meta.db.execute('UPDATE delivery SET state=?,next=? WHERE alert=? AND client=?',('delivered' if success else 'queued',time.time()+60,aid,client))
                msg.register_delivery_callback(lambda m,f=finish:f(True))
                msg.register_failed_callback(lambda m,f=finish:f(False))
                try:self.router.handle_outbound(msg)
                except Exception:finish(False)

    def local(self,nfc,pin,operation_json):
        """Only called by the non-exported local NFC activity after device unlock."""
        from .native import fido_client,enroll
        from .android_nfc import AndroidNfcDevice
        from .bookmarks import operate
        from fido2.ctap2 import Ctap2
        from fido2.webauthn import AttestedCredentialData
        operation=json.loads(operation_json)
        if set(operation)-{'action','snapshot','public_data','permissions','credential','page'}:raise ValueError('unknown operation')
        action=operation.get('action')
        if action not in ('enroll','authorize_enroll','trust_sim','save_page','remove','bookmark'):raise ValueError('unsupported operation')
        device=AndroidNfcDevice(nfc);event=threading.Event();timer=threading.Timer(60,event.set);timer.start()
        try:
            with self.admin_lock:
                auth=self.server.auth
                if action=='enroll':
                    permissions=frozenset(operation.get('permissions',['pages:read','notifications:manage']))
                    if not permissions or not permissions<={'pages:read','notifications:manage','admin'}:raise ValueError('Invalid permissions')
                    if auth.credentials:
                        ticket=getattr(self,'enroll_ticket',None);self.enroll_ticket=None
                        if not ticket or time.monotonic()>=ticket[0] or permissions!=ticket[1]:raise ValueError('Fresh administrator authorization required for these permissions')
                    else:permissions=frozenset({'pages:read','notifications:manage','admin'})
                    value=enroll(device,auth.public_key,auth.destination,pin,event)
                    record=AttestedCredentialData(bytes.fromhex(value['public_data']))
                    with auth.lock:
                        if record.credential_id.hex() in auth.credentials:raise ValueError('Credential already enrolled')
                        auth.credentials[record.credential_id.hex()]=Credential(record,permissions,value['counter'])
                        store.save(self.server.state/'credentials.json',auth.credentials)
                    return 'Key enrolled: '+', '.join(sorted(permissions))
                if action=='bookmark':
                    operate(Ctap2(device),pin,'save',{'destination':auth.destination.hex(),'public_key':auth.public_key.hex(),'name':self.config.get('name','NomadKey Host')},event)
                    return 'Protected service bookmark saved and verified.'
                admins=[c.data for c in auth.credentials.values() if 'admin' in c.permissions]
                if not admins:raise ValueError('Enrol an owner key first')
                import secrets
                challenge=encode({'service':auth.destination.hex(),'operation':operation,'nonce':secrets.token_hex(32)})
                options,state=auth.fido.authenticate_begin(admins,user_verification='required',challenge=challenge)
                assertion=fido_client(device,auth.public_key,auth.destination,pin).get_assertion(options.public_key,event).get_response(0)
                with auth.lock:
                    credential=auth.fido.authenticate_complete(state,admins,assertion)
                    saved=auth.credentials[credential.credential_id.hex()];counter=assertion.response.authenticator_data.counter
                    if 'admin' not in saved.permissions:raise ValueError('Administrator revoked')
                    if (saved.counter or counter) and counter<=saved.counter:raise ValueError('Counter rollback')
                    if event.is_set():raise ValueError('Timed out')
                    saved.counter=counter;store.save(self.server.state/'credentials.json',auth.credentials)
                    if action=='authorize_enroll':
                        permissions=frozenset(operation.get('permissions',['pages:read','notifications:manage']))
                        if not permissions or not permissions<={'pages:read','notifications:manage','admin'}:raise ValueError('Invalid permissions')
                        self.enroll_ticket=(time.monotonic()+60,permissions)
                        return 'Administrator approved. Within 60 seconds tap Enrol key with the new key.'
                    if action=='trust_sim':
                        current=json.loads(str(self.bridge.simSnapshot()))
                        if current!=operation['snapshot']:raise ValueError('SIM observation changed; review it again')
                        self.server.metadata.trust_sim(current);return 'Current SIM observation trusted. This is not carrier-side swap detection.'
                    if action=='save_page':
                        page=operation['page']
                        if not isinstance(page,str) or len(page.encode())>60000:raise ValueError('Page too large')
                        (self.root/'content'/'index.mu').write_text(page,encoding='utf-8');return 'Protected page saved.'
                    if action=='remove':
                        key=operation['credential']
                        if key not in auth.credentials:raise ValueError('Unknown credential')
                        auth.remove_credential(key);store.save(self.server.state/'credentials.json',auth.credentials);return 'Credential and its sessions revoked.'
        finally:timer.cancel();device.close()


runtime=None
def start(root,bridge,config_json):
    global runtime
    if runtime is not None:return runtime.status()
    runtime=Runtime(root,bridge,json.loads(config_json));return runtime.status()
def status():return runtime.status() if runtime else json.dumps({'connection':'Stopped'})
def local(nfc,pin,operation):
    if runtime is None:raise ValueError('Start the host first')
    return runtime.local(nfc,pin,operation)

def snapshot():
    if runtime is None:raise ValueError('Start the host first')
    return str(runtime.bridge.simSnapshot())

def credentials():
    if runtime is None:return '[]'
    with runtime.server.auth.lock:
        return json.dumps([{'id':key,'permissions':sorted(value.permissions)} for key,value in runtime.server.auth.credentials.items()])

def shutdown():
    """Stop authority before the Android service exits its dedicated app process."""
    if runtime:
        runtime.stop.set();runtime.server.running=False
        with runtime.server.auth.lock:
            runtime.server.auth.sessions.clear();runtime.server.auth.pending.clear()
        for link,_ in list(runtime.server.links.values()):link.teardown()
