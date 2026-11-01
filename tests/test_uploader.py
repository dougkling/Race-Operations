import json,sys,tempfile,time,unittest,os
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dvr'))
from uploader_monitor import probe,parse_log
class Uploader(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.logs=Path(self.tmp.name);self.now=datetime(2026,10,29,2,10,tzinfo=timezone.utc).timestamp()
 def tearDown(self):self.tmp.cleanup()
 def log(self,text,name='uploader-2026-10-27.log'):(self.logs/name).write_text(text)
 def check(self,state='Running'):return probe(self.logs,self.now,lambda:state,timestamp_basis='utc')
 def test_observed_cadence_not_false_stale(self):
  self.log('2026-10-29 02:04:56Z [INFO] Heartbeat: worker healthy; scanned 0 video file(s).');r=self.check();self.assertEqual(r['status'],'green');self.assertEqual(r['filesScanned'],0);self.assertEqual(r['heartbeatAgeSeconds'],304)
 def test_stale_warning_and_stopped_red(self):
  self.log('2026-10-29 01:00:00Z [INFO] Heartbeat: worker healthy; scanned 4 video file(s).');self.assertEqual(self.check()['status'],'yellow');self.assertEqual(self.check('Ready')['status'],'red')
 def test_unknown_task_never_green(self):
  self.log('2026-10-29 02:09:00Z [INFO] Heartbeat: worker healthy; scanned 0 video file(s).');self.assertEqual(self.check('unknown')['status'],'unknown')
 def test_recent_error_sanitized(self):
  self.log('2026-10-29 02:09:00Z [INFO] Heartbeat: worker healthy; scanned 0 video file(s).\n2026-10-29 02:09:30Z [ERROR] PRIVATE raw credentials failure');r=self.check();self.assertEqual(r['status'],'yellow');self.assertNotIn('PRIVATE',json.dumps(r))
 def test_future_clock_not_healthy(self):
  self.log('2026-10-29 03:00:00Z [INFO] Heartbeat: worker healthy; scanned 0 video file(s).');self.assertEqual(self.check()['uploaderReason'],'clock_warning')
 def test_missing_log_and_zero_scanned(self):
  self.assertEqual(self.check()['status'],'yellow')
 def test_select_modified_not_filename(self):
  self.log('2026-10-29 02:09:00Z [INFO] Heartbeat: worker healthy; scanned 0 video file(s).');self.log('2026-10-29 01:00:00Z [INFO] Heartbeat: worker healthy; scanned 9 video file(s).','uploader-2026-10-29.log');os.utime(self.logs/'uploader-2026-10-29.log',(1,1));self.assertEqual(self.check()['status'],'green')
 def test_upload_is_indeterminate_not_percent(self):
  self.log('2026-10-29 02:09:00Z [INFO] Heartbeat: worker healthy; scanned 3 video file(s).\n2026-10-29 02:09:30Z [INFO] Uploading PRIVATE_FILE (999 bytes)');r=self.check();self.assertEqual(r['operation'],'uploading');self.assertNotIn('PRIVATE_FILE',json.dumps(r));self.assertNotIn('percent',r)
@unittest.skipUnless(hasattr(time,'tzset'),'Timezone simulation uses POSIX tzset; production uses OS local timezone')
class LocalUploaderTime(unittest.TestCase):
 def setUp(self):
  self.previous=os.environ.get('TZ');os.environ['TZ']='America/New_York';time.tzset()
 def tearDown(self):
  if self.previous is None:os.environ.pop('TZ',None)
  else:os.environ['TZ']=self.previous
  time.tzset()
 def sample(self,stamp,utc):
  return parse_log(stamp+'Z [INFO] Heartbeat: worker healthy; scanned 1 video file(s).',datetime.fromisoformat(utc).timestamp(),'local')
 def test_operator_observation(self):
  r=self.sample('2026-10-29 12:22:57','2026-10-29T16:27:21+00:00');self.assertEqual(r['heartbeatAgeSeconds'],264)
 def test_default_probe_uses_local_time(self):
  with tempfile.TemporaryDirectory() as folder:
   Path(folder,'uploader-2026-10-27.log').write_text('2026-10-29 12:22:57Z [INFO] Heartbeat: worker healthy; scanned 1 video file(s).')
   now=datetime.fromisoformat('2026-10-29T16:27:21+00:00').timestamp()
   r=probe(folder,now,lambda:'Running');self.assertEqual(r['status'],'green');self.assertEqual(r['heartbeatAgeSeconds'],264)
   self.assertEqual(probe(folder,now+3600,lambda:'Running')['status'],'yellow')
 def test_winter_offset_and_midnight(self):
  self.assertEqual(self.sample('2026-12-01 12:22:57','2026-12-01T17:27:21+00:00')['heartbeatAgeSeconds'],264)
  self.assertEqual(self.sample('2026-10-28 23:59:00','2026-10-29T04:03:00+00:00')['heartbeatAgeSeconds'],240)
 def test_ambiguous_fall_hour_is_conservative(self):
  self.assertEqual(self.sample('2026-11-01 01:30:00','2026-11-01T06:35:00+00:00')['heartbeatAgeSeconds'],3900)
 def test_future_clock_still_warns(self):
  self.assertTrue(self.sample('2026-10-29 13:22:57','2026-10-29T16:27:21+00:00')['clockWarning'])
if __name__=='__main__':unittest.main()
