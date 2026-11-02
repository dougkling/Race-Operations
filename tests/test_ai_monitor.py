import json,sys,time,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
import ai_monitor
from server import Store
from agent import perform_restart

class Tests(unittest.TestCase):
 def sample(self,**values):
  return dict(schema=1,status='green',reason='healthy',observedAt=1000,lastCheckedEpoch=999,latencyMs=100,**values)
 def test_green_requires_test_evidence(self):
  for data in [self.sample(),dict(schema=1,status='green',reason='healthy',observedAt=1000),dict(schema=1,status='green',reason='healthy',observedAt=1000,lastCheckedEpoch=1)]:
   with patch.object(ai_monitor,'call',return_value=data):
    r=ai_monitor.sample({},clock=lambda:1000)
    self.assertEqual(r['status'],'green' if data.get('lastCheckedEpoch')==999 else 'unknown')
 def test_unavailable_unknown_and_no_sensitive_fields(self):
  with patch.object(ai_monitor,'call',side_effect=OSError('PRIVATE')):
   r=ai_monitor.sample({});self.assertEqual(r['status'],'unknown');self.assertNotIn('PRIVATE',json.dumps(r))
 def test_reconnect_checks_current_failure_and_completion(self):
  cfg={'hostId':'cloud','aiReconnectEnabled':True};rid='a'*36
  with patch.object(ai_monitor,'sample',side_effect=[{'status':'red'},{'status':'green','completedRequestId':rid}]),patch.object(ai_monitor,'call',return_value={'requestId':rid}):
   self.assertEqual(ai_monitor.reconnect(cfg,rid),('succeeded','ai_health_passed'))
  with patch.object(ai_monitor,'sample',return_value={'status':'unknown'}):
   self.assertEqual(ai_monitor.reconnect(cfg,rid),('skipped','unsafe_preflight'))
 def test_ai_failure_enables_both_recovery_paths(self):
  with tempfile.TemporaryDirectory() as folder:
   cfg={'hosts':[],'pitwallRestartEnabled':True,'aiReconnectEnabled':True}
   s=Store(cfg,Path(folder)/'db')
   try:
    s.samples['cloud']={'received':time.time(),'agentVersion':'0.10.0','components':[{'id':'racebot','status':'green'},{'id':'commentator','status':'green'},{'id':'racebot-ai','status':'red'}]}
    self.assertTrue(s.eligible('pitwall-restart')[0]);self.assertTrue(s.eligible('racebot-ai-reconnect')[0])
    s.samples['cloud']['components'][-1]['status']='unknown'
    self.assertFalse(s.eligible('pitwall-restart')[0]);self.assertFalse(s.eligible('racebot-ai-reconnect')[0])
    s.samples['cloud']['components'][-1]['status']='red';s.samples['cloud']['received']-=46
    self.assertFalse(s.eligible('racebot-ai-reconnect')[0])
   finally:s.db.close()
 def test_old_agent_cannot_enable_ai_recovery(self):
  with tempfile.TemporaryDirectory() as folder:
   s=Store({'hosts':[],'aiReconnectEnabled':True},Path(folder)/'db')
   try:
    s.samples['cloud']={'received':time.time(),'agentVersion':'0.7.0','components':[{'id':'racebot-ai','status':'red'}]}
    self.assertFalse(s.eligible('racebot-ai-reconnect')[0])
   finally:s.db.close()
 def test_shared_restart_does_not_skip_failed_ai(self):
  cfg={'hostId':'cloud','pitwallRestartEnabled':True}
  probe=lambda _:{'components':[{'id':'racebot','status':'green'},{'id':'commentator','status':'green'},{'id':'racebot-ai','status':'red'}]}
  # On the test host native operations are deliberately blocked, but preflight
  # must no longer return already_healthy merely because HTTP is green.
  with patch('agent.os.name','posix'):
   self.assertNotEqual(perform_restart(cfg,probe=probe),('skipped','already_healthy'))
if __name__=='__main__':unittest.main()
