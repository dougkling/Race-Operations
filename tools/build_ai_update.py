"""Build the narrow cross-project updater from checked-out, reviewed source."""
import argparse,base64,difflib,hashlib,io,json,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def norm(b):return b.decode('utf-8-sig').replace('\r\n','\n').encode()
def build(racebot,output):
 racebot,output=Path(racebot),Path(output);output.mkdir(parents=True,exist_ok=True)
 files={'ai_update.py':(ROOT/'tools/ai_update.py').read_bytes(),
        'check-pending.py':(ROOT/'cloud/check-pending.py').read_bytes(),
        'racebot/ai_health.py':(racebot/'app/ai_health.py').read_bytes(),
        'app-patch.json':(racebot/'scripts/ai-monitor.patch.json').read_bytes()}
 operations={}
 for name in ('server.py','agent.py','email_alerts.py','ai_monitor.py','web/app.js'):
  data=(ROOT/'cloud'/name).read_bytes();files['operations/'+name]=data
  try:old=subprocess.check_output(['git','show','origin/main:cloud/'+name],cwd=ROOT,stderr=subprocess.DEVNULL)
  except subprocess.CalledProcessError:old=None
  operations[name]=sha(norm(old)) if old is not None else None
 manifest={'operations':operations,'payload':{name:sha(body) for name,body in files.items()}}
 files['manifest.json']=json.dumps(manifest,indent=2).encode()
 buffer=io.BytesIO()
 with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
  for name,data in files.items():z.writestr(name,data)
 template=(ROOT/'cloud/Update-AI-Monitor.ps1').read_text()
 script=template.replace('__PAYLOAD__',base64.b64encode(buffer.getvalue()).decode())
 p=output/'Update-RaceBot-AI-Monitor.ps1';p.write_text(script)
 (output/(p.name+'.sha256')).write_text(sha(p.read_bytes())+'  '+p.name+'\n')
 print(str(p))
 return p
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--racebot',required=True);p.add_argument('--output',default=str(ROOT/'dist'))
 a=p.parse_args();build(a.racebot,a.output)
