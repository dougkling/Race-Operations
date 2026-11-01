import json,sys,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dvr'))
import pilot_monitor as pm
import test_controls
class Pilot(unittest.TestCase):
 def setUp(self):
  self.races=[{'url':'races/current%20test.mp4','key':'pilot-review/races/current test.mp4','size':93918,'archive':''},{'url':'races/Archive/2026-10-16/2026-10-16%2016-24-33.mp4','key':'pilot-review/races/Archive/2026-10-16/2026-10-16 16-24-33.mp4','size':425849932,'archive':'2026-10-16'}];self.calls=[];self.now=1793300000
 def manifest(self):return b'\xef\xbb\xbf'+json.dumps({'version':'1.7.1','generatedAt':'2026-10-29T06:25:31.1251720Z','races':self.races,'private':'SECRET'}).encode()
 def fetch(self,url,method,limit):
  self.calls.append((url,method,limit))
  if 'index.html?' in url:return b'<!doctype html><html>page</html>',{}
  if 'manifest.json?' in url:return self.manifest(),{}
  self.assertEqual(method,'HEAD');self.assertEqual(limit,0)
  return b'',{'Content-Type':'video/mp4','Content-Length':str(425849932 if '/Archive/' in url else 93918)}
 def test_verified_bom_and_samples(self):
  row=pm.probe(self.fetch,self.now);self.assertEqual(row['status'],'green');self.assertEqual(row['raceCount'],2);self.assertEqual(row['currentVideo'],'pass');self.assertEqual(row['archivedVideo'],'pass');self.assertEqual([x[1] for x in self.calls],['GET','GET','HEAD','HEAD']);self.assertNotIn('SECRET',json.dumps(row));self.assertNotIn('url',row)
 def test_empty_manifest_valid_no_video_calls(self):
  self.races=[];row=pm.probe(self.fetch,self.now);self.assertEqual(row['status'],'green');self.assertEqual(row['currentVideo'],'absent');self.assertEqual(len(self.calls),2)
 def test_old_manifest_not_a_failure(self):self.assertEqual(pm.probe(self.fetch,self.now+86400*100)['status'],'green')
 def test_future_timestamp_warns(self):self.assertEqual(pm.probe(self.fetch,1000)['pilotReason'],'clock_warning')
 def test_invalid_json_and_page_failure(self):
  def bad(url,method,limit):return b'not json',{}
  self.assertEqual(pm.probe(bad,self.now)['status'],'red')
 def test_invalid_object_paths_never_requested(self):
  for url in ('https://evil.invalid/x.mp4','//evil.invalid/x.mp4','races/%2e%2e/x.mp4','races/file.mp4?token=secret','races/file.mp4#x'):
   self.races[0]['url']=url;row=pm.probe(self.fetch,self.now);self.assertEqual(row['currentVideo'],'failed')
 def test_size_and_type_mismatch(self):
  original=self.fetch
  def bad(url,method,limit):return (b'',{'Content-Type':'text/html','Content-Length':'12'}) if method=='HEAD' else original(url,method,limit)
  row=pm.probe(bad,self.now);self.assertEqual(row['pilotReason'],'video_failed')
 def test_request_does_not_read_video_body_and_disables_redirects(self):
  response=MagicMock();response.status=200
  with patch.object(pm.urllib.request,'build_opener') as build:
   build.return_value.open.return_value.__enter__.return_value=response
   pm.request(pm.BASE+'races/test.mp4','HEAD',0);response.read.assert_not_called();self.assertEqual(build.call_args.args[0].proxies,{});self.assertIsInstance(build.call_args.args[1],pm.NoRedirect)
 def test_snapshot_stale_and_nonblocking(self):
  m=pm.Monitor(check=lambda:None,clock=lambda:601);m.at=0;m.row=pm.empty();m.row['status']='green';self.assertEqual(m.snapshot()['pilotReason'],'stale')
  m=pm.Monitor();self.assertEqual(m.snapshot()['pilotReason'],'checking')
 def test_oversize_response_rejected(self):
  response=MagicMock();response.status=200;response.read.return_value=b'abcdef'
  with patch.object(pm.urllib.request,'build_opener') as build:
   build.return_value.open.return_value.__enter__.return_value=response
   with self.assertRaises(ValueError):pm.request(pm.BASE+'manifest.json','GET',5)
class PilotProjection(test_controls.Controls):
 def test_sanitized_telemetry(self):
  self.cfg['hosts'][1]['components']=[{'id':'pilot-review'}]
  row={'id':'pilot-review','status':'green','pilotReason':'healthy','pageOk':True,'manifestOk':True,'raceCount':339,'currentVideo':'pass','archivedVideo':'pass','private':'SECRET','url':'SECRET'}
  code,_,_=self.req('/api/heartbeat',{'hostId':'dvr','agentVersion':'0.3.0','components':[row]},{'Authorization':'Bearer dvr-token'});self.assertEqual(code,200);clean=self.s.state.samples['dvr']['components'][0];self.assertEqual(clean['raceCount'],339);self.assertNotIn('SECRET',json.dumps(clean))
