function pilotDetail(c){
 if(!c)return 'Pilot Review evidence unavailable';
 const http=v=>v===true?'Pass':v===false?'Failed':'Unknown';
 const sample=v=>({pass:'Pass',failed:'Failed',absent:'No entries',unknown:'Unknown'}[v]||'Unknown');
 const reasons={checking:'Checking',unavailable:'Check unavailable',stale:'Evidence stale',manifest_unavailable:'Manifest unavailable or invalid',page_unavailable:'Page unavailable',clock_warning:'Manifest timestamp in future',video_failed:'Video sample failed',healthy:'Checks passed'};
 return (reasons[c.pilotReason]||'Unknown')+' | Page: '+http(c.pageOk)+' | Manifest: '+http(c.manifestOk)+' | Races: '+(c.raceCount??'Unknown')+' | Current sample: '+sample(c.currentVideo)+' | Archived sample: '+sample(c.archivedVideo)+' | Manifest age: '+(Number.isInteger(c.manifestAgeSeconds)?Math.floor(c.manifestAgeSeconds/3600)+' hr':'Unknown')+' | Checked: '+(Number.isInteger(c.lastCheckedEpoch)?new Date(c.lastCheckedEpoch*1000).toLocaleTimeString():'Unknown');
}
function healthDetail(c){
 if(!c)return 'Health-check evidence unavailable';
 const reasons={healthy:'Completed successfully',warnings:'Completed with warnings',failed:'Last check failed',running:'Check running or queued',disabled:'Task disabled',stale:'Report older than 15 minutes',report_missing:'Report unavailable',report_invalid:'Report not recognized',report_mismatch:'Report does not match task run',task_unknown:'Task evidence unavailable',clock_warning:'Timestamp is in the future'};
 const last=Number.isInteger(c.lastRunEpoch)?new Date(c.lastRunEpoch*1000).toLocaleString():'Unknown';
 const age=Number.isInteger(c.reportAgeSeconds)?Math.floor(c.reportAgeSeconds/60)+' min':'Unknown';
 const counts=Number.isInteger(c.passes)?' | '+c.passes+' pass, '+c.warnings+' warning, '+c.failures+' failure':'';
 return (reasons[c.healthReason]||'Unknown')+' | Task: '+c.taskState+' | Last run: '+last+' | Exit: '+(c.lastTaskResult??'Unknown')+' | Report age: '+age+counts+(c.warningChecks?.length?' | Warnings: '+c.warningChecks.join(', '):'');
}
function diskDetail(c){
 if(!c||!Number.isFinite(c.freeBytes)||!Number.isFinite(c.totalBytes)||!Number.isFinite(c.freePercent))return 'Disk capacity unavailable';
 return (c.freeBytes/1073741824).toFixed(1)+' GiB free / '+(c.totalBytes/1073741824).toFixed(1)+' GiB ('+c.freePercent+'%) | Warning: <15% or <10 GiB; critical: <5% or <2 GiB';
}
// Cloud-observed link health is independent of the DVR management agent.
function connectorEvidence(hosts){
 const cloud=hosts.find(h=>h.id==='cloud');
 const proxy=cloud?.connected?cloud.sample?.components?.find(c=>c.id==='cloud-proxy'):null;
 const known=proxy?.status==='green'&&typeof proxy.dvrConnected==='boolean';
 return {status:known?(proxy.dvrConnected?'green':'red'):'unknown',detail:known?
  'Proxy reports '+(proxy.dvrConnected?'connected':'disconnected')+' | Remote judges: '+(Number.isInteger(proxy.remoteJudges)?proxy.remoteJudges:'Unknown')+' | Heartbeat age unavailable':
  'Cloud connection evidence unavailable'};
}
let csrf="",sending=false,actionTarget="pitwall-restart",dvrActions={};
const names={'racebot':'RaceBot','commentator':'Commentator Desk','cloud-proxy':'DVR cloud proxy','judge-cues':'Judge Cues','review-status':'Review Status','iis':'IIS Judge Review','obs':'OBS Studio','uploader':'S3 Uploader','connector':'Cloud Connector','disk-space':'System disk C:','disk-network':'Disk space · C:\\DVR','pilot-review':'Pilot Review','scoring':'Scoring Client','health-monitor':'System Health Check'};const ids={cloud:['racebot','commentator','cloud-proxy','disk-space'],dvr:['judge-cues','review-status','iis','obs','uploader','connector','disk-network','pilot-review','scoring','health-monitor']};
function node(tag,text,cls){const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e}
function serviceDetail(id,c,h){
 if(id==='disk-space'||id==='disk-network')return diskDetail(c);
 if(id==='pilot-review')return pilotDetail(c);
 if(id==='health-monitor')return healthDetail(c);
 if(id==='connector')return c.detail;
 if(id==='uploader')return c?'Task: '+c.taskState+' | Heartbeat: '+(typeof c.heartbeatAgeSeconds==='number'?Math.round(c.heartbeatAgeSeconds/60)+' min':'Unknown')+' | '+c.operation+' | '+c.uploaderReason:'Uploader evidence unavailable';
 if(id==='obs')return 'OBS: '+(typeof c?.obsConnected==='boolean'?(c.obsConnected?'Connected':'Disconnected'):'Unknown')+' | Recording: '+(typeof c?.recording==='boolean'?(c.recording?'RECORDING'+(c.recordingPaused?' (paused)':''):'Idle'):'Unknown')+(c?.recording&&typeof c.recordingSeconds==='number'?' | '+c.recordingSeconds+' sec':'');
 if(id==='scoring')return 'Awaiting scoring PC verification';
 return c?.latencyMs!=null?'Response: '+c.latencyMs+' ms':h.connected?'Local endpoint monitoring':'Agent evidence unavailable';
}
function actionControl(action,a){
 const box=node('div',null,'service-action'),b=node('button',a.label);b.type='button';b.dataset.action=action;b.disabled=!a.allowed||sending;b.onclick=()=>openConfirm(action);
 const reason=a.reason==='Target is green'?'Recovery available if health check fails.':a.reason;
 box.append(b,node('p',reason,'action-reason'));return box;
}
function render(d){
 const expanded=new Set(Array.from(document.querySelectorAll('details[open]')).map(e=>e.dataset.key));
 const focused=document.activeElement?.dataset?.action;
 const focusedDetail=document.activeElement?.parentElement?.dataset?.key;
 csrf=d.csrf;dvrActions=d.dvrActions||{};
 document.querySelector('#login').hidden=true;document.querySelector('#overview').hidden=false;document.querySelector('#activity-panel').hidden=false;
 document.querySelector('#error').textContent='';document.querySelector('#backend-version').textContent='Backend '+d.version+' / Windows';
 const root=document.querySelector('#hosts');root.replaceChildren();const counts={green:0,yellow:0,red:0,unknown:0};
 for(const h of d.hosts){
  const host=node('section',null,'host host-'+h.id);host.id='host-'+h.id;
  const top=node('div',null,'host-head'),title=node('div',null,'host-title');
  title.append(node('p',h.id==='cloud'?'01 / CLOUD SERVICES':'02 / CAPTURE & JUDGING','eyebrow'),node('h2',h.name));
  top.append(title,node('span',h.connected?'● Agent connected':'○ Disconnected','badge '+(h.connected?'green':'unknown')));host.append(top);
  const grid=node('div',null,'service-grid');
  for(const id of ids[h.id]||[]){
   const c=id==='connector'?connectorEvidence(d.hosts):(h.connected?h.sample?.components?.find(c=>c.id===id):null);
   const status=c?.status||'unknown';counts[status]=(counts[status]||0)+1;
   const card=node('article',null,'service state-'+status),head=node('div',null,'service-top');card.dataset.component=id;
   head.append(node('h3',names[id]||id),node('span',({green:'● Healthy',yellow:'● Degraded',red:'● Offline',unknown:'○ Unknown'}[status]||'○ Unknown'),'badge '+status));card.append(head);
   const body=node('div',null,'service-body');const detail=serviceDetail(id,c,h);const parts=detail.split(' | ');
   let short=parts[0];
   if(id==='obs')short=parts.slice(0,2).join(' · ');
   if(id==='health-monitor')short=(c?((c.passes??'—')+' pass · '+(c.warnings??'—')+' warning · '+(c.failures??'—')+' failure'):'Report unavailable');
   if(id==='pilot-review')short=parts[0]+(c?.raceCount!=null?' · '+c.raceCount+' races':'');
   if(id==='uploader')short=c?'Task '+c.taskState+' · '+c.operation:'Evidence unavailable';
   body.append(node('p',short,'service-summary'));
   if(parts.length>1){
    const details=node('details');details.dataset.key=h.id+'-'+id;details.open=expanded.has(details.dataset.key);
    details.append(node('summary','Details'));const facts=node('div',null,'facts');for(const part of parts)facts.append(node('div',part,'fact'));details.append(facts);body.append(details);
   }
   card.append(body);
   if(h.id==='dvr')for(const [action,a] of Object.entries(dvrActions))if(a.target===id)card.append(actionControl(action,a));
   if(h.id==='cloud'&&id==='commentator')card.append(actionControl('pitwall-restart',{label:'Restart RaceBot + Commentator',allowed:d.restartAllowed,reason:d.restartReason}));
   if(h.id==='cloud'&&id==='cloud-proxy')card.append(actionControl('proxy-restart',{label:'Restart DVR cloud proxy',allowed:d.proxyRestartAllowed,reason:d.proxyRestartReason}));
   grid.append(card);
  }
  host.append(grid);root.append(host);
 }
 const overview=document.querySelector('#overview');overview.replaceChildren();
 for(const [status,label] of [['green','Healthy'],['yellow','Degraded'],['red','Offline'],['unknown','Unknown']]){const metric=node('div',null,'metric');metric.append(node('strong',String(counts[status]),status),node('span',label));overview.append(metric)}
 const activity=document.querySelector('#activity');const signature=JSON.stringify(d.jobs||[]);
 if(signature!==activity.dataset.signature){activity.dataset.signature=signature;activity.replaceChildren();
  if(!d.jobs?.length)activity.append(node('p','No recovery actions recorded yet.','empty'));
  for(const j of d.jobs||[]){
   const event=node('article',null,'event');const info=node('div');
   const label=dvrActions[j.action]?.label||({'pitwall-restart':'Restart RaceBot + Commentator','proxy-restart':'Restart DVR cloud proxy'}[j.action])||j.action;
   info.append(node('p',label,'event-title'),node('p',j.result.replaceAll('_',' '),'event-result'));
   const state=j.state==='succeeded'?'green':j.state==='failed'?'red':['running','queued','dispatched'].includes(j.state)?'yellow':'unknown';
   event.append(node('time',new Date(j.created*1000).toLocaleString()),info,node('span',j.state,'badge '+state),node('p','ID '+j.id,'event-id'));activity.append(event);
  }
 }
 document.querySelector('#updated').textContent='Updated '+new Date().toLocaleTimeString();
 if(focused)Array.from(document.querySelectorAll('button[data-action]')).find(e=>e.dataset.action===focused)?.focus({preventScroll:true});
 else if(focusedDetail)Array.from(document.querySelectorAll('details')).find(e=>e.dataset.key===focusedDetail)?.querySelector('summary')?.focus({preventScroll:true});
}
function clearStatus(message){
 document.querySelector('#hosts').replaceChildren();document.querySelector('#overview').hidden=true;document.querySelector('#activity-panel').hidden=true;
 document.querySelector('#updated').textContent=message;document.querySelector('#backend-version').textContent=message;
}
let updating=false;
async function update(){if(updating)return;updating=true;try{
 const r=await fetch('/api/status');if(r.status===401){document.querySelector('#login').hidden=false;clearStatus('Sign in required');return}
 if(!r.ok)throw Error();const d=await r.json();render(d);
}catch{clearStatus('Connection unavailable');document.querySelector('#error').textContent='Backend unavailable. Current health is unknown.'}finally{updating=false}}
async function signin(){const token=document.querySelector('#token');try{const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:token.value})});token.value='';if(!r.ok){document.querySelector('#error').textContent='Sign-in failed';return}await update()}catch{token.value='';document.querySelector('#error').textContent='Backend unavailable'}};document.querySelector('#signin').onclick=signin;document.querySelector('#token').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();signin()}};document.querySelector('#cancel').onclick=()=>document.querySelector('#confirm').close();document.querySelector('#restart').onclick=restartGroup;update();setInterval(update,5000);

async function restartGroup(){if(sending)return;sending=true;document.querySelector('#restart').disabled=true;document.querySelector('#confirm').close();const bytes=crypto.getRandomValues(new Uint8Array(16));bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');const requestId=[hex.slice(0,8),hex.slice(8,12),hex.slice(12,16),hex.slice(16,20),hex.slice(20)].join('-');try{const r=await fetch('/api/actions/'+actionTarget,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({requestId,confirmation:dvrActions[actionTarget]?.label||(actionTarget==='proxy-restart'?'Restart DVR cloud proxy':'Restart RaceBot + Commentator')})});const d=await r.json();if(!r.ok)alert(d.error||'Restart request rejected');}catch{alert('Request outcome unknown. Check activity before retrying.')}finally{sending=false;document.querySelector('#restart').disabled=false;await update()}}

function openConfirm(target){actionTarget=target;if(dvrActions[target]){const a=dvrActions[target];document.querySelector('#actiontitle').textContent=a.label+'?';document.querySelector('#actionimpact').textContent=target==='dvr-health-run'?'Runs the existing health-check task and refreshes the report.':target==='dvr-obs-restart'?'OBS may close and reopen in the logged-in desktop session. Recovery is blocked while recording or when recording state cannot be established. Verify capture after recovery.':target==='dvr-judge-cues-restart'?'Judge Cues sessions will disconnect. Recording must be idle. Verify the Lead Judge arm state after recovery.':'Only '+(names[a.target]||a.target)+' will restart. Its clients or transfers may be interrupted. Confirm no critical judging transaction is in progress.';document.querySelector('#restart').textContent='Confirm';document.querySelector('#confirm').showModal();return;}const proxy=target==='proxy-restart';document.querySelector('#actiontitle').textContent=proxy?'Restart DVR cloud proxy?':'Restart RaceBot + Commentator?';document.querySelector('#actionimpact').textContent=proxy?'Remote judge sessions will disconnect temporarily. Confirm no critical judging transaction is in progress. Only the Race DVR Judge Proxy task will restart; RaceBot and Commentator keep running. Recovery checks the proxy health endpoint, not reconnection of every judge.':'Both RaceBot and Commentator will be interrupted. The DVR proxy keeps running. Both HTTP endpoints are checked after restart.';document.querySelector('#restart').textContent=proxy?'Confirm proxy restart':'Restart both applications';document.querySelector('#confirm').showModal()}
