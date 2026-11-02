import json,sqlite3,sys,tempfile,threading,unittest,smtplib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cloud'))
from email_alerts import AlertEngine,DeliveryError,send_email,load_config
CONFIG=dict(enabled=True,region='us-east-1',fromAddress='alerts@example.com',toAddress='ops@example.com',username='PRIVATE',password='SECRET')
class Alerts(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'email.json';self.path.write_text(json.dumps(CONFIG));self.now=1000;self.sent=[]
  self.store=SimpleNamespace(db=sqlite3.connect(':memory:'),lock=threading.RLock(),samples={},config={'hosts':[{'id':'cloud','components':[{'id':'racebot'},{'id':'cloud-proxy'}]},{'id':'dvr','components':[{'id':'connector'}]}]})
  self.engine=self.new_engine()
 def new_engine(self):return AlertEngine(self.store,self.path,clock=lambda:self.now,sender=lambda c,e:self.sent.append(e))
 def tearDown(self):self.store.db.close();self.tmp.cleanup()
 def tick(self,status='red',advance=0):
  self.now+=advance;self.store.samples['cloud']={'received':self.now,'components':[{'id':'racebot','status':status}]};self.engine.tick()
 def states(self):return [r[0] for r in self.store.db.execute('SELECT state FROM email_outbox')]
 def test_ai_red_alerts_even_with_racebot_http_green(self):
  self.store.config['hosts'][0]['components'].append({'id':'racebot-ai'})
  def beat(ai):
   self.store.samples['cloud']={'received':self.now,'components':[{'id':'racebot','status':'green'},{'id':'racebot-ai','status':ai}]}
   self.engine.tick()
  beat('red');self.now+=29;beat('red');self.assertFalse(self.sent)
  self.now+=1;beat('red');self.assertEqual(len(self.sent),1)
  self.assertEqual(self.sent[0]['component'],'racebot-ai')
  beat('unknown');self.now+=30;beat('red');self.assertEqual(len(self.sent),1)
  beat('green');beat('red');self.now+=30;beat('red');self.assertEqual(len(self.sent),2)
 def test_delay_once_recovery_new_incident(self):
  self.tick();self.tick(advance=29);self.assertEqual(len(self.sent),0);self.tick(advance=1);self.tick(advance=10);self.assertEqual(len(self.sent),1)
  self.tick('green');self.tick();self.tick(advance=30);self.assertEqual(len(self.sent),2)
 def test_enable_after_long_red(self):
  self.path.write_text('{}');self.tick();self.tick(advance=3600);self.assertFalse(self.sent)
  self.path.write_text(json.dumps(CONFIG));self.tick();self.assertEqual(len(self.sent),1)
 def test_warning_unknown_no_email(self):
  self.tick('yellow');self.tick('unknown',100);self.assertFalse(self.sent)
 def test_mute_persist_unmute_and_status(self):
  self.engine.set_mute('cloud','racebot',True,'admin');self.tick();self.tick(advance=30);self.assertFalse(self.sent)
  self.engine=self.new_engine();self.assertTrue(self.engine.muted('cloud','racebot'));self.assertEqual(self.engine.states()['cloud','racebot'],'red')
  self.engine.set_mute('cloud','racebot',False,'admin');self.tick();self.assertEqual(len(self.sent),1)
 def test_restart_and_unknown_no_duplicate(self):
  self.tick();self.tick(advance=30);self.engine=self.new_engine();self.tick('unknown');self.tick();self.tick(advance=30);self.assertEqual(len(self.sent),1)
 def test_uncertain_sending_not_replayed(self):
  self.tick();self.tick(advance=30);self.store.db.execute("UPDATE email_outbox SET state='sending'");self.store.db.commit()
  self.engine=self.new_engine();self.tick();self.assertEqual(self.states(),['uncertain']);self.assertEqual(len(self.sent),1)
 def test_retry_bounded(self):
  self.engine.sender=Mock(side_effect=DeliveryError('retryable'));self.tick();self.tick(advance=30);self.assertEqual(self.states(),['pending'])
  self.tick(advance=60);self.tick(advance=120);self.assertEqual(self.states(),['failed']);self.tick(advance=200);self.assertEqual(self.engine.sender.call_count,3)
 def test_mute_cancels_retry(self):
  self.engine.sender=Mock(side_effect=DeliveryError('retryable'));self.tick();self.tick(advance=30)
  self.engine.set_mute('cloud','racebot',True,'admin');self.tick(advance=60);self.assertEqual(self.states(),['suppressed']);self.assertEqual(self.engine.sender.call_count,1)
 def test_agent_loss_and_proxy(self):
  self.assertEqual(self.engine.agent_status('dvr'),'unknown');self.engine.seen('dvr');self.now+=60;self.assertEqual(self.engine.agent_status('dvr'),'red')
  self.store.samples['cloud']={'received':self.now,'components':[{'id':'cloud-proxy','status':'green','dvrConnected':False}]}
  self.assertEqual(self.engine.states()['dvr','connector'],'red');self.now+=46;self.assertEqual(self.engine.states()['dvr','connector'],'unknown')
 def test_config_and_safe_summary(self):
  self.assertEqual(load_config(self.path)[1],'enabled');self.assertNotIn('SECRET',json.dumps(self.engine.summary()));self.path.write_text('{}');self.assertEqual(load_config(self.path)[1],'disabled')
  self.path.write_text('bad');self.assertEqual(load_config(self.path)[1],'invalid_configuration')
 def test_smtp_tls_and_uncertainty(self):
  client=Mock();client.send_message.return_value={};factory=Mock(return_value=client);event=dict(id='id',host='cloud',component='racebot',created=self.now)
  send_email(CONFIG,event,smtp=factory);client.starttls.assert_called_once();client.login.assert_called_once_with('PRIVATE','SECRET');client.close.assert_called_once()
  client.send_message.side_effect=OSError()
  with self.assertRaises(DeliveryError) as e:send_email(CONFIG,event,smtp=factory)
  self.assertEqual(e.exception.kind,'uncertain')
 def test_invalid_monitor(self):
  with self.assertRaises(ValueError):self.engine.set_mute('cloud','typo',True,'admin')
  with self.assertRaises(ValueError):self.engine.set_mute('cloud','racebot','false','admin')
