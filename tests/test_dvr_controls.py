import importlib.util,json,sys,tempfile,time,unittest,uuid
from pathlib import Path
from unittest.mock import Mock,patch
from test_controls import Controls
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'dvr'))
from dvr_actions import ACTIONS,guard
from dvr_control import perform,Executor

class DvrAPI(Controls):
 def setUp(self):
  super().setUp();self.cfg['dvrControlsEnabled']=True
  self.cfg['hosts'][1]['components']=[{'id':i} for i in ('judge-cues','review-status','iis','uploader','obs','health-monitor','connector')]
  self.cfg['hosts'][0]['components'].append({'id':'cloud-proxy'})
 def dvrbeat(self,status='red',recording=False,count=1,version='0.8.0',caps=None):
  return self.req('/api/heartbeat',{'hostId':'dvr','agentVersion':version,'capabilities':list(ACTIONS) if caps is None else caps,'components':[
   {'id':'judge-cues','status':status},{'id':'review-status','status':status},{'id':'iis','status':status},{'id':'uploader','status':status},
   {'id':'obs','status':status,'obsConnected':recording is not None,'recording':recording,'processCount':count},
   {'id':'health-monitor','status':'yellow','taskState':'Ready'}]}, {'Authorization':'Bearer dvr-token'})
 def action(self,csrf,action='dvr-judge-cues-restart',jid=None):
  return self.req('/api/actions/'+action,{'requestId':jid or str(uuid.uuid4()),'confirmation':ACTIONS[action][1]}, {'X-CSRF-Token':csrf})
 def test_dvr_host_scoped_dispatch_and_result(self):
  csrf=self.login();self.dvrbeat();jid=str(uuid.uuid4())
  self.assertEqual(self.action(csrf,jid=jid)[0],202)
  self.assertEqual(self.beat()[1]['commands'],[])
  self.assertEqual(self.dvrbeat()[1]['commands'],[{'id':jid,'action':'dvr-judge-cues-restart'}])
  self.assertEqual(self.dvrbeat()[1]['commands'],[])
  result={'hostId':'cloud','id':jid,'state':'succeeded','result':'component_recovered'}
  self.assertEqual(self.req('/api/action-result',result,{'Authorization':'Bearer cloud-token'})[0],403)
  result['hostId']='dvr'
  self.assertEqual(self.req('/api/action-result',result,{'Authorization':'Bearer dvr-token'})[0],200)
  self.assertEqual(self.s.state.jobs()[0]['state'],'succeeded')
 def test_recording_unknown_healthy_and_old_agent_blocked(self):
  csrf=self.login()
  for status,rec,count,version in [('red',True,1,'0.8.0'),('red',None,1,'0.8.0'),('green',False,1,'0.8.0'),('red',False,1,'0.7.0')]:
   self.dvrbeat(status,rec,count,version);self.assertEqual(self.action(csrf)[0],409)
  self.dvrbeat(caps=[]);self.assertEqual(self.action(csrf)[0],409)
  self.dvrbeat();self.s.state.samples['dvr']['received']=time.time()-46;self.assertEqual(self.action(csrf)[0],409)
 def test_health_run_allowed_with_warnings_and_connector_needs_proxy(self):
  csrf=self.login();self.dvrbeat()
  self.assertFalse(self.s.state.eligible('dvr-connector-restart')[0])
  self.s.state.samples['cloud']={'received':time.time(),'components':[{'id':'cloud-proxy','status':'green','dvrConnected':False}]}
  self.assertTrue(self.s.state.eligible('dvr-connector-restart')[0])
  self.assertEqual(self.action(csrf,'dvr-health-run')[0],202)
 def test_dvr_rejects_bad_csrf_confirmation_and_duplicate_target(self):
  self.dvrbeat();csrf=self.login()
  self.assertEqual(self.action('wrong')[0],403)
  jid=str(uuid.uuid4());self.assertEqual(self.action(csrf,jid=jid)[0],202)
  self.assertEqual(self.action(csrf,jid=jid)[0],200)
  self.assertEqual(self.action(csrf,'dvr-iis-restart',jid=jid)[0],409)
 def test_stopped_obs_can_recover_unknown_record_state(self):
  self.dvrbeat(recording=None,count=0)
  self.assertTrue(self.s.state.eligible('dvr-obs-restart')[0])
 def test_test_heartbeat_cannot_consume_dvr_action(self):
  csrf=self.login();self.dvrbeat();self.action(csrf)
  self.assertEqual(self.dvrbeat(version='0.7.0')[1]['commands'],[])

class DvrWorker(unittest.TestCase):
 def setUp(self):self.cfg={'dvrControlsEnabled':True,'dvrCapabilities':list(ACTIONS)}
 def test_fresh_health_preflight_blocks_recovered_target(self):
  runner=Mock()
  outcome=perform(self.cfg,'dvr-iis-restart',lambda:{'components':[{'id':'iis','status':'green'}]},lambda:None,runner=runner)
  self.assertEqual(outcome,('skipped','already_healthy'));runner.assert_not_called()
 def test_fixed_script_action_recovery(self):
  samples=iter([{'components':[{'id':'iis','status':'red'}]},{'components':[{'id':'iis','status':'green'}]}])
  runner=Mock(return_value=Mock(returncode=0))
  with patch('dvr_control.os.name','nt'):
   result=perform(self.cfg,'dvr-iis-restart',lambda:next(samples),lambda:None,runner=runner)
  self.assertEqual(result,('succeeded','component_recovered'))
  argv=runner.call_args.args[0];self.assertEqual(argv[-2:],['-Action','dvr-iis-restart']);self.assertIn('-File',argv)
 def test_no_execution_for_unknown_action_or_recording(self):
  runner=Mock()
  for action,rows in [('arbitrary',[]),('dvr-judge-cues-restart',[{'id':'judge-cues','status':'red'},{'id':'obs','recording':True,'processCount':1}])]:
   self.assertEqual(perform(self.cfg,action,lambda:{'components':rows},lambda:None,runner=runner)[0],'skipped')
  runner.assert_not_called()
 def test_crash_and_acked_journal_never_replay(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'journal.sqlite3';e=Executor({},p,lambda:None,lambda:None)
   jid=str(uuid.uuid4());e.db.execute('INSERT INTO executions VALUES (?,?,?,0)',(jid,'running','executing'));e.db.commit();e.db.close()
   e=Executor({},p,lambda:None,lambda:None);self.assertEqual(e.reports()[0][1],'indeterminate')
   e.acknowledged(jid,'indeterminate');self.assertEqual(e.reports(),[])
   e.accept({'id':jid,'action':'dvr-iis-restart'});self.assertFalse(e.busy);e.db.close()
 def test_timeout_indeterminate(self):
  import subprocess
  runner=Mock(side_effect=subprocess.TimeoutExpired('recovery',90))
  with patch('dvr_control.os.name','nt'):
   result=perform(self.cfg,'dvr-iis-restart',lambda:{'components':[{'id':'iis','status':'red'}]},lambda:None,runner=runner)
  self.assertEqual(result,('indeterminate','execution_uncertain'))
 def test_health_old_report_not_success(self):
  row={'id':'health-monitor','taskState':'Ready','status':'yellow','reportAgeSeconds':30,'lastRunEpoch':time.time()-30,'lastTaskResult':0}
  clock=iter([0,1,121]);runner=Mock(return_value=Mock(returncode=0))
  with patch('dvr_control.os.name','nt'):
   result=perform(self.cfg,'dvr-health-run',lambda:{'components':[row]},lambda:None,runner=runner,sleep=lambda _:None,clock=lambda:next(clock))
  self.assertEqual(result,('failed','recovery_timeout'))
 def test_shared_catalog_identical(self):
  self.assertEqual((ROOT/'cloud/dvr_actions.py').read_bytes(),(ROOT/'dvr/dvr_actions.py').read_bytes())

if __name__=='__main__':unittest.main()
