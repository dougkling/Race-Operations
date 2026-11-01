import sys,tempfile,unittest,json,subprocess
from pathlib import Path
from unittest.mock import patch
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dvr'))
import health_monitor as hm
import test_controls
class HealthReport(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'report.log';self.start=int(datetime.fromisoformat('2026-10-29T15:43:29-04:00').timestamp());self.info={'state':'Ready','result':0,'lastRun':self.start}
 def tearDown(self):self.tmp.cleanup()
 def report(self,warnings=3,failures=0,label='REQUIRED SERVICES HEALTHY'):
  self.path.write_text(f'Race DVR post-reboot health check\n2026-10-29 15:43:29 -04:00\nJudge Cues health endpoint  WARN secret version detail\nGraphics race source        WARN private metadata\nHeat tracking arm state     WARN not armed\nRESULT: {label} (23 pass, {warnings} warning, {failures} failure)\nLatest uploader log: SECRET\nRESULT: ATTENTION REQUIRED (0 pass, 0 warning, 9 failure)\n',encoding='utf-8-sig')
 def probe(self,age=30):return hm.probe(self.path,self.start+age,lambda:self.info)
 def test_observed_warnings_and_no_raw_data(self):
  self.report();r=self.probe();self.assertEqual(r['status'],'yellow');self.assertEqual(r['warnings'],3);self.assertEqual(r['reportAgeSeconds'],30);self.assertEqual(len(r['warningChecks']),3);self.assertNotIn('SECRET',json.dumps(r));self.assertNotIn('private',json.dumps(r))
 def test_ready_zero_green_and_stale(self):
  self.report(0);self.assertEqual(self.probe()['status'],'green');self.assertEqual(self.probe(86401)['healthReason'],'stale')
 def test_failure_and_running_code(self):
  self.report();self.info['result']=1;self.assertEqual(self.probe()['status'],'red');self.info.update(state='Running',result=267009);self.assertEqual(self.probe()['healthReason'],'running');self.assertEqual(self.probe()['status'],'yellow')
 def test_failed_summary_even_zero_exit(self):
  self.report(0,1,'ATTENTION REQUIRED');self.assertEqual(self.probe()['status'],'red')
 def test_missing_invalid_and_unknown(self):
  self.assertEqual(self.probe()['healthReason'],'report_missing');self.path.write_text('arbitrary raw failure');self.assertEqual(self.probe()['status'],'unknown');self.assertEqual(hm.probe(self.path,get_task=lambda:None)['status'],'unknown')
 def test_manual_report_mismatch_disabled_future(self):
  self.report(0);self.info['lastRun']-=1000;self.assertEqual(self.probe()['healthReason'],'report_mismatch');self.info['lastRun']=self.start;self.assertEqual(self.probe(-120)['healthReason'],'clock_warning');self.info['state']='Disabled';self.assertEqual(self.probe()['healthReason'],'disabled')
 def test_task_query_fixed_and_timeout(self):
  with patch.object(hm.os,'name','nt'),patch.object(hm.subprocess,'run') as run:
   run.return_value.returncode=0;run.return_value.stdout=json.dumps(self.info);self.assertEqual(hm.task_info(),self.info)
   command=run.call_args.args[0][-1];self.assertIn("Get-ScheduledTask -TaskName 'Race DVR System Health Check'",command);self.assertNotIn('Start-ScheduledTask',command);self.assertEqual(run.call_args.kwargs['timeout'],5)
   run.side_effect=subprocess.TimeoutExpired('powershell',5);self.assertIsNone(hm.task_info())
class HealthProjection(test_controls.Controls):
 def test_allowlist(self):
  self.cfg['hosts'][1]['components']=[{'id':'health-monitor'}]
  payload={'hostId':'dvr','agentVersion':'0.3.0','components':[{'id':'health-monitor','status':'yellow','healthReason':'warnings','taskState':'Ready','warnings':3,'lastTaskResult':0,'warningChecks':['Graphics race source','SECRET'],'raw':'PRIVATE'}]}
  code,_,_=self.req('/api/heartbeat',payload,{'Authorization':'Bearer dvr-token'});self.assertEqual(code,200);row=self.s.state.samples['dvr']['components'][0];self.assertEqual(row['warnings'],3);self.assertEqual(row['warningChecks'],['Graphics race source']);self.assertNotIn('PRIVATE',json.dumps(row));self.assertNotIn('SECRET',json.dumps(row))
