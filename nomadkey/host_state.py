"""Host-only persistent metadata. SMS bodies never enter this database or alerts."""
import hashlib
import json
import re
import sqlite3
import threading
import time
import RNS


def literal(value):
    # Prefix every line so a hostile SMS cannot close Micron literal mode.
    value=str(value).replace('\r\n','\n').replace('\r','\n')
    return '`=\n'+'\n'.join(' '+line for line in value.split('\n'))+'\n`=\n'


def sender_label(value):
    return ''.join(c for c in str(value) if c.isalnum() or c in ' +-_')[:32] or 'unknown sender'


class HostState:
    def __init__(self,path,clock=time.time,monotonic=time.monotonic):
        self.clock,self.monotonic=clock,monotonic
        self.lock=threading.RLock()
        self.db=sqlite3.connect(str(path),check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=DELETE')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY,v TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS subscribers(client TEXT PRIMARY KEY,credential TEXT NOT NULL,destination TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY AUTOINCREMENT,content TEXT NOT NULL,created REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS delivery(alert INTEGER,client TEXT,state TEXT DEFAULT 'queued',attempts INTEGER DEFAULT 0,next REAL DEFAULT 0,PRIMARY KEY(alert,client));
        ''')
        self.db.execute("UPDATE delivery SET state='queued' WHERE state='sending'")
        self.db.commit()
        self.sim_candidate=None;self.sim_since=0

    def get(self,key,default=None):
        with self.lock:
            row=self.db.execute('SELECT v FROM settings WHERE k=?',(key,)).fetchone()
            return json.loads(row[0]) if row else default

    def put(self,key,value):
        with self.lock,self.db:
            self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(key,json.dumps(value)))

    def subscribe(self,client,credential,action):
        if len(client)!=64 or action not in ('subscribe','unsubscribe'):raise ValueError('invalid subscription')
        identity=RNS.Identity(create_keys=False);identity.load_public_key(client)
        destination=RNS.Destination.hash(identity,'lxmf','delivery').hex()
        with self.lock,self.db:
            if action=='unsubscribe':
                self.db.execute('DELETE FROM subscribers WHERE client=?',(client.hex(),))
                self.db.execute('DELETE FROM delivery WHERE client=?',(client.hex(),))
            else:
                count=self.db.execute('SELECT count(*) FROM subscribers').fetchone()[0]
                exists=self.db.execute('SELECT 1 FROM subscribers WHERE client=?',(client.hex(),)).fetchone()
                if count>=64 and not exists:raise ValueError('subscriber limit')
                self.db.execute('INSERT OR REPLACE INTO subscribers VALUES (?,?,?)',(client.hex(),credential,destination))
        return destination

    def subscribers(self):
        with self.lock:return self.db.execute('SELECT client,credential,destination FROM subscribers').fetchall()

    def sweep(self):
        with self.lock,self.db:
            self.db.execute("DELETE FROM delivery WHERE state='delivered' OR alert IN (SELECT id FROM alerts WHERE created<?)",(self.clock()-86400,))
            self.db.execute('DELETE FROM alerts WHERE id NOT IN (SELECT alert FROM delivery)')

    def enqueue(self,content):
        if not isinstance(content,str) or len(content.encode())>256:raise ValueError('alert too large')
        self.sweep()
        with self.lock,self.db:
            if self.db.execute('SELECT count(*) FROM alerts').fetchone()[0]>=256:
                self.put('dropped_alerts',self.get('dropped_alerts',0)+1);return False
            if not self.subscribers():return True
            alert=self.db.execute('INSERT INTO alerts(content,created) VALUES (?,?)',(content,self.clock())).lastrowid
            for client,_,_ in self.subscribers():self.db.execute('INSERT INTO delivery(alert,client) VALUES (?,?)',(alert,client))
        return True

    def sms_received(self,sender,timestamp):
        # Deliberately accepts no message-body argument.
        stamp=time.strftime('%Y-%m-%d %H:%M:%S UTC',time.gmtime(int(timestamp)/1000))
        return self.enqueue('SMS received from '+sender_label(sender)+' at '+stamp)

    @staticmethod
    def sim_fingerprint(snapshot):
        # Metadata only unless the OS exposes a serial digest. No raw SIM ID leaves Android.
        sims=snapshot.get('sims',[])
        return hashlib.sha256(json.dumps(sims,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def trust_sim(self,snapshot):
        if not snapshot.get('observable') or not snapshot.get('sims'):raise ValueError('No observable SIM to trust')
        self.put('trusted_sim',self.sim_fingerprint(snapshot));self.put('sim_last_alert','');self.sim_candidate=None

    def observe_sim(self,snapshot):
        trusted=self.get('trusted_sim')
        if not trusted:return 'SIM not yet trusted'
        if not snapshot.get('observable'):status='SIM monitoring unavailable; check phone permission'
        elif not snapshot.get('sims'):status='Trusted SIM is absent'
        elif self.sim_fingerprint(snapshot)!=trusted:status='SIM subscription changed; local review required'
        elif snapshot.get('airplane'):status='Airplane mode is enabled'
        elif not snapshot.get('in_service'):status='Trusted SIM has no service; outage or SIM problem possible'
        else:status='healthy'
        if status!=self.sim_candidate:self.sim_candidate=status;self.sim_since=self.monotonic()
        if self.monotonic()-self.sim_since>=60 and status!=self.get('sim_last_alert',''):
            if status!='healthy' or self.get('sim_last_alert',''):
                self.enqueue(('SIM service recovered' if status=='healthy' else status)+'; '+time.strftime('%Y-%m-%d %H:%M:%S UTC',time.gmtime(self.clock())))
            self.put('sim_last_alert',status)
        return 'SIM service available (not proof against SIM swap)' if status=='healthy' else status
