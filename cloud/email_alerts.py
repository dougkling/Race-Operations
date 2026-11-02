"""Persistent monitor mutes, red incidents, and a bounded SES SMTP outbox."""
import argparse,json,re,secrets,smtplib,ssl,threading,time
from datetime import datetime,timezone
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path
NAMES={'agent-link':'Agent connection','racebot':'RaceBot','racebot-ai':'RaceBot AI','commentator':'Commentator Desk','cloud-proxy':'DVR cloud proxy','judge-cues':'Judge Cues','review-status':'Review Status','iis':'IIS Judge Review','obs':'OBS Studio','uploader':'S3 Uploader','connector':'Cloud Connector','disk-space':'System disk C:','disk-network':'DVR disk space','pilot-review':'Pilot Review','scoring':'Scoring Client','health-monitor':'System Health Check'}

def load_config(path):
 try:
  c=json.loads(Path(path).read_text(encoding='utf-8-sig'))
  if not isinstance(c,dict):raise ValueError()
  if c.get('enabled') is not True:return None,'disabled'
  validate(c);return c,'enabled'
 except FileNotFoundError:return None,'not_configured'
 except (ValueError,OSError,TypeError):return None,'invalid_configuration'

def validate(c):
 if not re.fullmatch(r'[a-z]{2}(?:-[a-z]+){1,2}-\d',str(c.get('region',''))):raise ValueError('Invalid SES region')
 for key in ('fromAddress','toAddress'):
  if not isinstance(c.get(key),str) or not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",c[key]):raise ValueError('Use a single plain email address')
 for key in ('username','password'):
  if not isinstance(c.get(key),str) or not c[key] or '\n' in c[key] or '\r' in c[key]:raise ValueError('SES SMTP credentials required')

class DeliveryError(Exception):
 def __init__(self,kind):self.kind=kind

def send_email(config,event,smtp=smtplib.SMTP):
 """Returns SES acceptance, not proof of inbox delivery. Never log server errors or credentials."""
 validate(config);msg=EmailMessage()
 name=NAMES.get(event['component'],'Monitor');host=event['host']
 msg['Subject']='Race Operations test email' if event.get('test') else f'Race Operations: RED - {name} ({host})'
 msg['From']=config['fromAddress'];msg['To']=config['toAddress'];msg['Date']=format_datetime(datetime.now(timezone.utc));msg['Message-ID']=f"<{event['id']}@raceoperations.local>"
 stamp=datetime.fromtimestamp(event['created'],timezone.utc).isoformat()
 msg.set_content('Race Operations email delivery test.' if event.get('test') else f'{name} on {host} is RED.\n\nFirst detected (UTC): {stamp}\nIncident: {event["id"]}\n\nOpen Race Operations to review current status before recovery.\nThis email was sent once for this red incident. Muting suppresses future notifications, not monitoring.\n')
 client=None;data_started=False
 try:
  client=smtp('email-smtp.'+config['region']+'.amazonaws.com',587,timeout=10)
  client.ehlo();client.starttls(context=ssl.create_default_context());client.ehlo();client.login(config['username'],config['password'])
  data_started=True
  refused=client.send_message(msg,from_addr=config['fromAddress'],to_addrs=[config['toAddress']])
  if refused:raise DeliveryError('rejected')
 except DeliveryError:raise
 except smtplib.SMTPResponseException as e:raise DeliveryError('retryable' if 400<=e.smtp_code<500 else 'rejected') from None
 except smtplib.SMTPRecipientsRefused:raise DeliveryError('rejected') from None
 except (OSError,smtplib.SMTPException):raise DeliveryError('uncertain' if data_started else 'retryable') from None
 finally:
  if client:
   try:client.close()
   except Exception:pass

class AlertEngine:
 def __init__(self,store,path,clock=time.time,sender=send_email):
  self.store=store;self.db=store.db;self.lock=store.lock;self.path=Path(path);self.clock=clock;self.sender=sender;self.started=clock();self.stop=threading.Event();self.thread=None
  self.db.executescript('''
CREATE TABLE IF NOT EXISTS monitor_mutes(host TEXT,component TEXT,muted INTEGER NOT NULL,updated REAL,PRIMARY KEY(host,component));
CREATE TABLE IF NOT EXISTS mute_events(at REAL,host TEXT,component TEXT,muted INTEGER,actor TEXT);
CREATE TABLE IF NOT EXISTS agent_seen(host TEXT PRIMARY KEY,at REAL);
CREATE TABLE IF NOT EXISTS monitor_incidents(host TEXT,component TEXT,status TEXT,episode INTEGER,active INTEGER,red_since REAL,PRIMARY KEY(host,component));
CREATE TABLE IF NOT EXISTS email_outbox(id TEXT PRIMARY KEY,host TEXT,component TEXT,episode INTEGER,created REAL,state TEXT,attempts INTEGER,next_try REAL,updated REAL,UNIQUE(host,component,episode));
''')
  self.db.execute("UPDATE email_outbox SET state='uncertain',updated=? WHERE state='sending'",(clock(),));self.db.commit()
 def keys(self):return {(h['id'],c['id']) for h in self.store.config['hosts'] for c in h['components']}|{(h['id'],'agent-link') for h in self.store.config['hosts']}
 def muted(self,host,cid):
  row=self.db.execute('SELECT muted FROM monitor_mutes WHERE host=? AND component=?',(host,cid)).fetchone();return bool(row and row[0])
 def set_mute(self,host,cid,muted,actor):
  if (host,cid) not in self.keys() or type(muted) is not bool:raise ValueError('Invalid monitor')
  self.db.execute('INSERT INTO monitor_mutes VALUES (?,?,?,?) ON CONFLICT(host,component) DO UPDATE SET muted=excluded.muted,updated=excluded.updated',(host,cid,int(muted),self.clock()))
  self.db.execute('INSERT INTO mute_events VALUES (?,?,?,?,?)',(self.clock(),host,cid,int(muted),actor))
  if muted:self.db.execute("UPDATE email_outbox SET state='suppressed',updated=? WHERE host=? AND component=? AND state='pending'",(self.clock(),host,cid))
  self.db.commit()
 def seen(self,host):
  self.db.execute('INSERT INTO agent_seen VALUES (?,?) ON CONFLICT(host) DO UPDATE SET at=excluded.at',(host,self.clock()));self.db.commit()
 def agent_status(self,host):
  now=self.clock();sample=self.store.samples.get(host)
  if sample and now-sample.get('received',0)<=45:return 'green'
  known=self.db.execute('SELECT 1 FROM agent_seen WHERE host=?',(host,)).fetchone()
  return 'red' if known and now-self.started>=60 else 'unknown'
 def states(self):
  now=self.clock();result={}
  for host in self.store.config['hosts']:
   hid=host['id'];sample=self.store.samples.get(hid,{})
   current={c['id']:c['status'] for c in sample.get('components',[])} if now-sample.get('received',0)<=45 else {}
   for c in host['components']:result[hid,c['id']]=current.get(c['id'],'unknown')
   result[hid,'agent-link']=self.agent_status(hid)
  if ('dvr','connector') in result:
   cloud=self.store.samples.get('cloud',{})
   proxy=next((c for c in cloud.get('components',[]) if c['id']=='cloud-proxy'),{})
   link=proxy.get('dvrConnected') if now-cloud.get('received',0)<=45 and proxy.get('status')=='green' else None
   result['dvr','connector']='green' if link is True else 'red' if link is False else 'unknown'
  return result
 def observe(self,states,enabled):
  now=self.clock()
  for (host,cid),status in states.items():
   old=self.db.execute('SELECT status,episode,active,red_since FROM monitor_incidents WHERE host=? AND component=?',(host,cid)).fetchone() or ('unknown',0,0,None)
   previous,episode,active,since=old
   if status=='red':
    if not active:episode+=1;active=1
    if previous!='red' or since is None:since=now
   else:
    since=None
    if status in ('green','yellow'):
     active=0;self.db.execute("UPDATE email_outbox SET state='recovered',updated=? WHERE host=? AND component=? AND state IN ('pending','suppressed')",(now,host,cid))
   self.db.execute('INSERT INTO monitor_incidents VALUES (?,?,?,?,?,?) ON CONFLICT(host,component) DO UPDATE SET status=excluded.status,episode=excluded.episode,active=excluded.active,red_since=excluded.red_since',(host,cid,status,episode,active,since))
   if status=='red' and since is not None and now-since>=30 and enabled and not self.muted(host,cid):
    self.db.execute("INSERT OR IGNORE INTO email_outbox VALUES (?,?,?,?,?,'pending',0,?,?)",(secrets.token_hex(16),host,cid,episode,since,now,now))
    self.db.execute("UPDATE email_outbox SET state='pending',next_try=?,updated=? WHERE host=? AND component=? AND episode=? AND state='suppressed'",(now,now,host,cid,episode))
  self.db.commit()
 def summary(self):
  _,mode=load_config(self.path)
  mutes=[{'hostId':h,'componentId':c,'muted':self.muted(h,c)} for h,c in sorted(self.keys())]
  rows=self.db.execute('SELECT id,host,component,created,state,attempts,updated FROM email_outbox ORDER BY created DESC LIMIT 10').fetchall()
  return {'mode':mode,'redDelaySeconds':30,'mutes':mutes,'events':[dict(zip(('id','host','component','created','state','attempts','updated'),r)) for r in rows]}
 def tick(self):
  config,mode=load_config(self.path);now=self.clock()
  with self.lock:
   states=self.states();self.observe(states,mode=='enabled')
   if not config:return
   rows=self.db.execute("SELECT id,host,component,episode,created,attempts FROM email_outbox WHERE state='pending' AND next_try<=? ORDER BY created",(now,)).fetchall()
   event=None
   for jid,host,cid,episode,created,attempts in rows:
    if self.muted(host,cid):continue
    current=self.db.execute('SELECT status,episode,red_since FROM monitor_incidents WHERE host=? AND component=?',(host,cid)).fetchone()
    if not current or current[0]!='red' or current[1]!=episode or current[2] is None or now-current[2]<30:continue
    self.db.execute("UPDATE email_outbox SET state='sending',attempts=attempts+1,updated=? WHERE id=?",(now,jid));event={'id':jid,'host':host,'component':cid,'created':created,'attempts':attempts+1};break
   self.db.commit()
  if event:
   try:self.sender(config,event);outcome='accepted'
   except DeliveryError as e:outcome='pending' if e.kind=='retryable' and event['attempts']<3 else 'failed' if e.kind=='retryable' else e.kind
   except Exception:outcome='uncertain'
   with self.lock:
    if outcome=='pending' and self.muted(event['host'],event['component']):outcome='suppressed'
    self.db.execute('UPDATE email_outbox SET state=?,next_try=?,updated=? WHERE id=?',(outcome,self.clock()+60*event['attempts'],self.clock(),event['id']));self.db.commit()
 def run(self):
  while not self.stop.is_set():
   try:self.tick()
   except Exception:pass
   self.stop.wait(5)
 def start(self):
  self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--test',action='store_true');a=p.parse_args()
 try:
  c=json.loads(Path(a.config).read_text(encoding='utf-8-sig'));validate(c)
  if a.test:send_email(c,{'id':secrets.token_hex(16),'host':'cloud','component':'agent-link','created':time.time(),'test':True});print('SES accepted the test email. Check the destination inbox.')
  else:print('SES configuration validated.')
 except DeliveryError as e:raise SystemExit('Email test '+e.kind+'. Verify SES identity, sandbox status, SMTP credentials and network access.')
 except Exception:raise SystemExit('Invalid email configuration; no credentials displayed.')
