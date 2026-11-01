import json,sys,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
from agent import collect
import test_controls

class ConnectorProbe(unittest.TestCase):
 def probe(self,body):
  cfg={'hostId':'cloud','components':[{'id':'cloud-proxy','enabled':True,'probe':'http','url':'http://127.0.0.1:8767/health','requireOk':True}]}
  response=MagicMock();response.status=200;response.read.return_value=json.dumps(body).encode()
  with patch('agent.urllib.request.build_opener') as opener:
   opener.return_value.open.return_value.__enter__.return_value=response
   return collect(cfg)['components'][0]
 def test_connected_zero_judges_and_no_secrets(self):
  row=self.probe({'ok':True,'dvrConnected':True,'remoteJudges':0,'token':'PRIVATE'})
  self.assertEqual(row['status'],'green');self.assertIs(row['dvrConnected'],True);self.assertEqual(row['remoteJudges'],0);self.assertNotIn('PRIVATE',json.dumps(row))
 def test_disconnection_does_not_enable_proxy_restart(self):
  row=self.probe({'ok':True,'dvrConnected':False,'remoteJudges':0})
  self.assertEqual(row['status'],'green');self.assertIs(row['dvrConnected'],False)
 def test_missing_and_invalid_types(self):
  for body in ({'ok':True},{'ok':True,'dvrConnected':'true','remoteJudges':False}):
   row=self.probe(body);self.assertIsNone(row['dvrConnected']);self.assertIsNone(row['remoteJudges'])
 def test_malformed_shape(self):
  for body in ([],None,True):
   row=self.probe(body);self.assertEqual(row['status'],'yellow');self.assertNotIn('dvrConnected',row)
 def test_unhealthy_proxy_has_no_link_evidence(self):
  row=self.probe({'ok':False,'dvrConnected':True});self.assertEqual(row['status'],'yellow');self.assertNotIn('dvrConnected',row)

class ConnectorProjection(test_controls.ProxyControls):
 def test_projection_and_action_boundary(self):
  csrf=self.login()
  for value in (True,False,'true'):
   payload={'hostId':'cloud','agentVersion':'0.4.1','components':[{'id':'cloud-proxy','status':'green','dvrConnected':value,'remoteJudges':0,'secret':'PRIVATE'}]}
   code,_,_=self.req('/api/heartbeat',payload,{'Authorization':'Bearer cloud-token'});self.assertEqual(code,200)
   row=self.s.state.samples['cloud']['components'][0]
   self.assertEqual(row['dvrConnected'],value if type(value) is bool else None);self.assertNotIn('PRIVATE',json.dumps(row));self.assertEqual(self.proxyrequest(csrf)[0],409)
