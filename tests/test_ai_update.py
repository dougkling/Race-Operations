import base64,importlib.util,json,re,tempfile,unittest,zipfile,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ai_update',ROOT/'tools/ai_update.py');up=importlib.util.module_from_spec(spec);spec.loader.exec_module(up)
spec=importlib.util.spec_from_file_location('build_ai_update',ROOT/'tools/build_ai_update.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.rb=ROOT.parent/'RaceBot'
  if not self.rb.exists():self.skipTest('Cross-project updater tests require sibling RaceBot checkout')
  script=builder.build(self.rb,self.root/'output').read_text()
  raw=base64.b64decode(re.search(r"\$payloadText = '([^']+)'",script)[1])
  self.payload=self.root/'payload';zipfile.ZipFile(io.BytesIO(raw)).extractall(self.payload)
  self.target=self.root/'ops';self.target.mkdir();(self.target/'web').mkdir();(self.target/'config').mkdir()
  manifest=json.loads((self.payload/'manifest.json').read_text())
  import subprocess
  for name,baseline in manifest['operations'].items():
   if baseline is None:continue
   data=subprocess.check_output(['git','show','origin/main:cloud/'+name],cwd=ROOT)
   (self.target/name).write_bytes(data)
  self.release=self.root/'release';(self.release/'app').mkdir(parents=True)
  # Reconstruct baseline from the patch's before images plus actual downloaded baseline.
  baseline=self.rb/'app/app.py.baseline'
  if not baseline.exists():self.skipTest('Local baseline fixture not present')
  self.app=self.release/'app/app.py';self.app.write_text('# unrelated installed customization\n'+baseline.read_text())
  self.data=self.root/'data';self.data.mkdir()
  self.deployment=self.root/'deployment.json';self.deployment.write_text(json.dumps({'current_release':str(self.release),'data_dir':str(self.data)}))
  self.server={'hosts':[{'id':'cloud','components':[{'id':'racebot'},{'id':'commentator'}]},{'id':'dvr','components':[{'id':'obs'}]}],'privateSetting':'synthetic','adminTokenHash':'synthetic'}
  self.agent={'hostId':'cloud','components':[{'id':'racebot','enabled':True}],'token':'synthetic-agent'}
  (self.target/'config/server.json').write_text(json.dumps(self.server));(self.target/'config/cloud-agent.json').write_text(json.dumps(self.agent))
  self.folder=self.root/'backup'
 def prepare(self):up.prepare(self.payload,self.target,self.deployment,self.folder)
 def test_apply_preserves_features_credentials_and_rollback(self):
  before=self.app.read_bytes();self.prepare();self.assertEqual(self.app.read_bytes(),before)
  up.apply(self.folder);self.assertTrue(self.app.read_text().startswith('# unrelated installed customization'))
  self.assertIn('AI_HEALTH.start()',self.app.read_text())
  cfg=json.loads((self.target/'config/server.json').read_text());self.assertEqual(cfg['hosts'][1],self.server['hosts'][1]);self.assertEqual(cfg['privateSetting'],'synthetic')
  agent=json.loads((self.target/'config/cloud-agent.json').read_text());self.assertEqual(agent['token'],'synthetic-agent')
  up.rollback(self.folder);self.assertEqual(self.app.read_bytes(),before);self.assertFalse((self.data/'ai-monitor-token').exists())
 def test_installed_timeout_constructor_is_preserved(self):
  source=self.app.read_text().replace('def __init__(self, key, model):','def __init__(self, key, model, timeout=60):',1)
  source=source.replace('        self.key, self.model = key, model\n','        self.key, self.model = key, model\n        self.timeout=timeout\n',1)
  source=source.replace('urllib.request.urlopen(req, timeout=60)','urllib.request.urlopen(req, timeout=self.timeout)',1)
  changes=json.loads((self.payload/'app-patch.json').read_text())
  result=up.patch_app(source,changes)
  self.assertIn('def __init__(self, key, model, timeout=60):',result)
  self.assertIn('        self.timeout=timeout',result)
  self.assertIn('urllib.request.urlopen(req, timeout=self.timeout)',result)
  self.assertEqual(up.patch_app(result,changes),result)
 def test_patch_idempotent(self):
  changes=json.loads((self.payload/'app-patch.json').read_text())
  once=up.patch_app(self.app.read_text(),changes)
  self.assertEqual(up.patch_app(once,changes),once)
 def test_unknown_baseline_rejected_before_mutation(self):
  (self.target/'agent.py').write_text('# custom')
  before=self.app.read_bytes()
  with self.assertRaises(ValueError):self.prepare()
  self.assertEqual(before,self.app.read_bytes())
 def test_concurrent_edit_aborts_before_any_write(self):
  self.prepare();before=self.app.read_bytes();(self.target/'agent.py').write_text('# concurrent')
  with self.assertRaises(ValueError):up.apply(self.folder)
  self.assertEqual(self.app.read_bytes(),before)
 def test_rollback_refuses_later_change(self):
  self.prepare();up.apply(self.folder);self.app.write_text('# subsequent update')
  with self.assertRaises(ValueError):up.rollback(self.folder)
if __name__=='__main__':unittest.main()
