import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
from disk_monitor import sample,GIB
import test_controls

class Disk(unittest.TestCase):
 def check(self,total,free):return sample('disk-space',usage=lambda _:SimpleNamespace(total=total,free=free))
 def test_observed_capacities(self):
  for total,free in ((99,72.4),(231.8,67.9)):
   self.assertEqual(self.check(int(total*GIB),int(free*GIB))['status'],'green')
  self.assertEqual(self.check(int(29.5*GIB),int(2.6*GIB))['status'],'yellow')
 def test_either_threshold_and_boundaries(self):
  for total,free,status in ((100,15,'green'),(100,14,'yellow'),(100,5,'yellow'),(100,4,'red'),(20,10,'green'),(20,9,'yellow'),(20,2,'yellow'),(20,1,'red')):
   self.assertEqual(self.check(total*GIB,free*GIB)['status'],status)
 def test_unknown_invalid(self):
  for total,free in ((0,0),(100,-1),(100,101),(True,1),(100,float('nan'))):self.assertEqual(self.check(total,free)['status'],'unknown')
  def fail(_):raise PermissionError()
  self.assertEqual(sample('disk-space',usage=fail)['status'],'unknown')
 def test_verified_paths_and_no_directory_fallback(self):
  paths=[]
  def usage(path):paths.append(path);return SimpleNamespace(total=100*GIB,free=50*GIB)
  sample('disk-space',usage=usage);sample('disk-network',recordings=True,usage=usage)
  self.assertEqual(paths,['C:\\','C:\\DVR'])
 def test_both_deployment_copies_identical(self):
  root=Path(__file__).resolve().parents[1];self.assertEqual((root/'cloud/disk_monitor.py').read_bytes(),(root/'dvr/disk_monitor.py').read_bytes())

class DiskTelemetry(test_controls.Controls):
 def test_disk_severity_recomputed_and_bad_values_unknown(self):
  self.cfg['hosts'][0]['components'].append({'id':'disk-space'})
  for total,free,expected in ((99*GIB,72*GIB,'green'),(100*GIB,1*GIB,'red'),(0,0,'unknown'),(100,True,'unknown')):
   code,_,_=self.req('/api/heartbeat',{'hostId':'cloud','agentVersion':'0.5.0','components':[{'id':'disk-space','status':'green','totalBytes':total,'freeBytes':free,'freePercent':100,'private':'SECRET'}]},{'Authorization':'Bearer cloud-token'})
   self.assertEqual(code,200);row=self.s.state.samples['cloud']['components'][0];self.assertEqual(row['status'],expected);self.assertNotIn('private',row)
