import hashlib,json,sys,tempfile,threading,time,unittest,urllib.request,urllib.error,uuid
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
from server import make_server,VERSION
from agent import perform_restart,Executor
class Controls(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.cfg={'port':0,'pitwallRestartEnabled':True,'adminTokenHash':hashlib.sha256(b'admin').hexdigest(),'hosts':[{'id':'cloud','name':'Cloud','token':'cloud-token','components':[{'id':'racebot'},{'id':'commentator'}]},{'id':'dvr','name':'DVR','token':'dvr-token','components':[]}]}
  self.s=make_server(self.cfg,Path(self.tmp.name)/'audit.sqlite3',0);threading.Thread(target=self.s.serve_forever,daemon=True).start();self.base='http://127.0.0.1:'+str(self.s.server_port);self.cookie=''
 def tearDown(self):self.s.shutdown();self.s.server_close();self.s.state.db.close();self.tmp.cleanup()
 def req(self,path,data=None,headers=None):
  hs={'Cookie':self.cookie};hs.update(headers or {});q=urllib.request.Request(self.base+path,data=None if data is None else json.dumps(data).encode(),headers=hs)
  try:
   with urllib.request.urlopen(q) as r:return r.status,json.load(r),r.headers
  except urllib.error.HTTPError as e:return e.code,json.load(e),e.headers
 def login(self):
  _,_,h=self.req('/api/login',{'token':'admin'});self.cookie=h['Set-Cookie'].split(';')[0];return self.req('/api/status')[1]['csrf']
 def beat(self,status='red',token='cloud-token',host='cloud'):
  return self.req('/api/heartbeat',{'hostId':host,'agentVersion':VERSION,'components':[{'id':'racebot','status':status},{'id':'commentator','status':'green'}]}, {'Authorization':'Bearer '+token})
 def request(self,csrf,jid=None):return self.req('/api/actions/pitwall-restart',{'requestId':jid or str(uuid.uuid4()),'confirmation':'Restart RaceBot + Commentator'},{'X-CSRF-Token':csrf})
 def test_auth_csrf_and_health_guards(self):
  self.assertEqual(self.request('bad')[0],401);csrf=self.login();self.assertEqual(self.request('bad')[0],403);self.assertEqual(self.request(csrf)[0],409)
  self.beat('green');self.assertEqual(self.request(csrf)[0],409)
  self.beat('unknown');self.assertEqual(self.request(csrf)[0],409)
  self.beat();self.s.state.samples['cloud']['received']=time.time()-46;self.assertEqual(self.request(csrf)[0],409)
 def test_queue_once_scoped_result_and_audit(self):
  csrf=self.login();self.beat();jid=str(uuid.uuid4());self.assertEqual(self.request(csrf,jid)[0],202);self.assertEqual(self.request(csrf,jid)[0],200);self.assertEqual(self.request(csrf)[0],409)
  self.assertEqual(self.beat(token='dvr-token',host='dvr')[1]['commands'],[])
  self.assertEqual(self.beat()[1]['commands'],[{'id':jid,'action':'pitwall-restart'}]);self.assertEqual(self.beat()[1]['commands'],[])
  result={'hostId':'cloud','id':jid,'state':'succeeded','result':'both_http_checks_passed'}
  self.assertEqual(self.req('/api/action-result',result,{'Authorization':'Bearer dvr-token'})[0],403)
  self.assertEqual(self.req('/api/action-result',result,{'Authorization':'Bearer cloud-token'})[0],200)
  jobs=self.req('/api/status')[1]['jobs'];self.assertEqual(jobs[0]['state'],'succeeded');self.assertEqual(self.s.state.db.execute('SELECT COUNT(*) FROM events').fetchone()[0],3)
 def test_pending_persists_backend_restart(self):
  self.beat();csrf=self.login();self.request(csrf);other=make_server(self.cfg,Path(self.tmp.name)/'audit.sqlite3',0)
  self.assertEqual(other.state.jobs()[0]['state'],'queued');other.server_close();other.state.db.close()
 def test_static_utf8(self):
  with urllib.request.urlopen(self.base+'/app.js') as r:self.assertIn('restartGroup',r.read().decode('utf-8'))
 def test_agent_preflight_no_execution(self):
  cfg={'hostId':'cloud','pitwallRestartEnabled':True}
  probe=lambda _: {'components':[{'id':'racebot','status':'green'},{'id':'commentator','status':'green'}]}
  self.assertEqual(perform_restart(cfg,probe=probe),('skipped','already_healthy'))
  self.assertEqual(perform_restart({'hostId':'dvr'},probe=probe),('skipped','agent_controls_disabled'))
 def test_agent_restart_fixed_command_and_recovery(self):
  cfg={'hostId':'cloud','pitwallRestartEnabled':True};samples=iter([{'components':[{'id':'racebot','status':'red'},{'id':'commentator','status':'green'}]},{'components':[{'id':'racebot','status':'green'},{'id':'commentator','status':'green'}]}]);calls=[]
  def runner(args,**kwargs):calls.append(args);return type('R',(),{'returncode':0})()
  with patch('agent.os.name','nt'),patch('agent.Path') as path:
   path.return_value.is_file.return_value=True
   result=perform_restart(cfg,runner=runner,probe=lambda _:next(samples))
  self.assertEqual(result,('succeeded','both_http_checks_passed'));self.assertEqual(calls[0][-2:],['-Command','restart'])
 def test_crash_journal_never_replays(self):
  p=Path(self.tmp.name)/'agent.sqlite3';e=Executor({},p);e.db.execute('INSERT INTO executions VALUES (?,?,?)',('x'*36,'running','executing'));e.db.commit();e.db.close();e=Executor({},p)
  self.assertEqual(e.reports()[0][1],'indeterminate');e.accept({'id':'x'*36,'action':'pitwall-restart'});self.assertFalse(e.busy);e.db.close()
if __name__=='__main__':unittest.main()

class ProxyControls(Controls):
 def setUp(self):
  super().setUp();self.cfg['proxyRestartEnabled']=True;self.cfg['hosts'][0]['components'].append({'id':'cloud-proxy'})
 def proxybeat(self,status):
  return self.req('/api/heartbeat',{'hostId':'cloud','agentVersion':VERSION,'components':[{'id':'racebot','status':'green'},{'id':'commentator','status':'green'},{'id':'cloud-proxy','status':status}]},{'Authorization':'Bearer cloud-token'})
 def proxyrequest(self,csrf,jid=None):
  return self.req('/api/actions/proxy-restart',{'requestId':jid or str(uuid.uuid4()),'confirmation':'Restart DVR cloud proxy'},{'X-CSRF-Token':csrf})
 def test_independent_proxy_action(self):
  csrf=self.login();self.proxybeat('green');self.assertEqual(self.proxyrequest(csrf)[0],409)
  self.proxybeat('red');status=self.req('/api/status')[1];self.assertTrue(status['proxyRestartAllowed']);self.assertFalse(status['restartAllowed'])
  jid=str(uuid.uuid4());self.assertEqual(self.proxyrequest(csrf,jid)[0],202)
  self.assertEqual(self.proxybeat('red')[1]['commands'],[{'id':jid,'action':'proxy-restart'}])
  self.assertEqual(self.proxybeat('red')[1]['commands'],[])
  result={'hostId':'cloud','id':jid,'state':'succeeded','result':'proxy_health_passed'}
  self.assertEqual(self.req('/api/action-result',result,{'Authorization':'Bearer cloud-token'})[0],200)
  self.assertEqual(self.req('/api/status')[1]['jobs'][0]['action'],'proxy-restart')
 def test_proxy_fixed_task_and_recovery(self):
  from agent import perform_proxy_restart
  cfg={'hostId':'cloud','proxyRestartEnabled':True,'components':[{'id':'cloud-proxy','enabled':True,'url':'http://127.0.0.1:8767/health','requireOk':True}]}
  samples=iter(['red','green']);calls=[]
  def probe(_):return {'components':[{'id':'cloud-proxy','status':next(samples)}]}
  def runner(args,**kwargs):calls.append(args);return type('R',(),{'returncode':0})()
  with patch('agent.os.name','nt'):outcome=perform_proxy_restart(cfg,runner=runner,probe=probe)
  self.assertEqual(outcome,('succeeded','proxy_health_passed'))
  self.assertIn("-TaskName 'Race DVR Judge Proxy'",calls[0][-1]);self.assertNotIn('PitWall',calls[0][-1]);self.assertNotIn('Stop-Process',calls[0][-1])
 def test_proxy_refuses_unknown_and_disabled(self):
  from agent import perform_proxy_restart
  cfg={'hostId':'cloud','proxyRestartEnabled':True,'components':[{'id':'cloud-proxy','enabled':True,'url':'http://127.0.0.1:8767/health','requireOk':True}]}
  self.assertEqual(perform_proxy_restart(cfg,probe=lambda _:{'components':[{'id':'cloud-proxy','status':'unknown'}]}),('skipped','unsafe_preflight'))
  cfg['proxyRestartEnabled']=False;self.assertEqual(perform_proxy_restart(cfg),('skipped','agent_controls_disabled'))
 def test_migrate_old_audit(self):
  import sqlite3
  db=Path(self.tmp.name)/'old.sqlite3';conn=sqlite3.connect(db);conn.execute('CREATE TABLE jobs (id TEXT PRIMARY KEY,actor TEXT,created REAL,state TEXT,pre TEXT,result TEXT)');conn.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?)',('old','administrator',1,'succeeded','[]','both_http_checks_passed'));conn.commit();conn.close()
  server=make_server(self.cfg,db,0);self.assertEqual(server.state.jobs()[0]['action'],'pitwall-restart');server.server_close();server.state.db.close()
