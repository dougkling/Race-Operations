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
const names={'agent-link':'Agent connection','racebot':'RaceBot','racebot-ai':'RaceBot AI','commentator':'Commentator Desk','cloud-proxy':'DVR cloud proxy','judge-cues':'DVR Control Server','review-status':'Review Status','iis':'IIS Judge Review','obs':'OBS Studio','uploader':'S3 Uploader','connector':'Cloud Connector','disk-space':'System disk C:','disk-network':'Disk space · C:\\DVR','pilot-review':'Pilot Review','scoring':'Scoring Stream Deck Client','health-monitor':'System Health Check'};const ids={cloud:['agent-link','racebot','racebot-ai','commentator','cloud-proxy','disk-space'],dvr:['agent-link','obs','judge-cues','review-status','iis','uploader','connector','disk-network','pilot-review','health-monitor']};
function monitorEvidence(hosts,hostId,id){
 const h=hosts.find(h=>h.id===hostId);
 if(id==='agent-link')return {status:h?.agentStatus||(h?.connected?'green':'unknown')};
 if(id==='connector')return connectorEvidence(hosts);
 return h?.connected?h.sample?.components?.find(c=>c.id===id):null;
}
function monitorTarget(hostId,id){return 'monitor-'+hostId+'-'+id}
function node(tag,text,cls){const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e}
function serviceDetail(id,c,h){
 if(id==='racebot-ai'){const reasons={healthy:'Moderation and generation passed',checking:'Waiting for AI test',stale:'AI evidence is stale',credentials_missing:'AI key missing',credentials_unreadable:'Saved key cannot be loaded',timeout:'AI request timed out',connection_failed:'OpenAI connection failed',authentication_failed:'AI credentials rejected',rate_limited:'OpenAI rate limit reached',quota_exhausted:'OpenAI quota exhausted',provider_error:'OpenAI service error',request_rejected:'AI request or model rejected',invalid_response:'AI response did not complete',request_stalled:'AI request is stalled',monitor_unavailable:'AI monitor unavailable',reconnecting:'AI reconnect in progress'};return (reasons[c?.aiReason]||'AI evidence unavailable')+' | Last result: '+(c?.lastCheckedEpoch?new Date(c.lastCheckedEpoch*1000).toLocaleTimeString():'None')+' | '+(c?.aiReconnecting?'Reconnect pending':'Periodic test every 5 minutes; real failures tracked immediately');}
 if(id==='agent-link')return c.status==='red'?'No recent agent heartbeat':c.status==='green'?'Receiving agent heartbeats':'Waiting for agent evidence';
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
 const box=node('div',null,'service-action'),b=node('button',a.label.replace('Judge Cues','DVR Control Server'));b.type='button';b.dataset.action=action;b.disabled=!a.allowed||sending;b.onclick=()=>openConfirm(action);
 const reason=a.reason==='Target is green'?'Recovery available if health check fails.':a.reason;
 box.append(b,node('p',reason,'action-reason'));return box;
}
const muting=new Set();
async function setMute(hostId,componentId,muted,button){
 const key=hostId+':'+componentId;if(muting.has(key))return;muting.add(key);button.disabled=true;
 try{
  const r=await fetch('/api/monitor-mute',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({hostId,componentId,muted})});
  if(!r.ok){const d=await r.json();throw Error(d.error||'Mute update failed')}
 }catch(e){alert(e.message||'Mute outcome unknown. Refresh to verify.')}finally{muting.delete(key);await update()}
}
function render(d){
 const expanded=new Set(Array.from(document.querySelectorAll('details[open]')).map(e=>e.dataset.key));
 const focused=document.activeElement?.dataset?.action;
 const focusedMute=document.activeElement?.dataset?.mute;
 const focusedDetail=document.activeElement?.parentElement?.dataset?.key;
 const focusedMonitor=document.activeElement?.dataset?.monitorTarget;
 csrf=d.csrf;dvrActions=d.dvrActions||{};
 document.querySelector('#login').hidden=true;document.querySelector('#overview').hidden=false;document.querySelector('#activity-panel').hidden=false;
 document.querySelector('#error').textContent='';document.querySelector('#backend-version').textContent='Backend '+d.version+' / Windows';
 const root=document.querySelector('#hosts');root.replaceChildren();const counts={green:0,yellow:0,red:0,unknown:0};
 for(const h of d.hosts){
  const host=node('section',null,'host host-'+h.id);host.id='host-'+h.id;
  const top=node('div',null,'host-head'),title=node('div',null,'host-title');
  title.append(node('p',h.id==='cloud'?'01 / CLOUD SERVICES':'02 / CAPTURE & JUDGING','eyebrow'),node('h2',h.id==='cloud'?'CLOUD WINDOWS PC':'OBS / DVR PC'),node('p',h.id==='cloud'?'RaceBot · Commentator · Remote judge proxy':'Capture · Scoring control · Review · Uploads','host-description'));
  top.append(title,node('span',h.connected?'● Agent connected':'○ Disconnected','badge '+(h.connected?'green':'unknown')));host.append(top);
  const grid=node('div',null,'service-grid');
  const sections=h.id==='cloud'?{'agent-link':'HOST TELEMETRY','racebot':'APPLICATION SERVICES','disk-space':'CAPACITY'}:{'agent-link':'HOST TELEMETRY','obs':'CAPTURE & CONTROL','review-status':'REVIEW & DELIVERY','disk-network':'CAPACITY & VALIDATION'};
  for(const id of ids[h.id]||[]){
   if(sections[id])grid.append(node('div',sections[id],'section-label'));
   const c=monitorEvidence(d.hosts,h.id,id);
   const status=c?.status||'unknown';counts[status]=(counts[status]||0)+1;
   const card=node('article',null,'service state-'+status),head=node('div',null,'service-top');card.dataset.component=id;card.id=monitorTarget(h.id,id);card.tabIndex=-1;card.dataset.monitorTarget=card.id;card.setAttribute('aria-label',(names[id]||id)+' on '+h.name);
   if(id==='obs')card.classList.add('capture-row');
   head.append(node('h3',names[id]||id),node('span',({green:'● Healthy',yellow:'● Degraded',red:'● Offline',unknown:'○ Unknown'}[status]||'○ Unknown'),'badge '+status));card.append(head);
   const body=node('div',null,'service-body');const detail=serviceDetail(id,c,h);const parts=detail.split(' | ');
   let short=parts[0];
   if(id==='obs')short=parts.slice(0,2).join(' · ');
   if(id==='health-monitor')short=(c?((c.passes??'—')+' pass · '+(c.warnings??'—')+' warning · '+(c.failures??'—')+' failure'):'Report unavailable');
   if(id==='pilot-review')short=parts[0]+(c?.raceCount!=null?' · '+c.raceCount+' races':'');
   if(id==='uploader')short=c?'Task '+c.taskState+' · '+c.operation:'Evidence unavailable';
   body.append(node('p',short,'service-summary'));
   if((id==='disk-space'||id==='disk-network')&&Number.isFinite(c?.freePercent)){const meter=node('meter');meter.min=0;meter.max=100;meter.value=c.freePercent;meter.setAttribute('aria-label','Disk space free percent');body.append(meter)}
   if(id==='obs'){const rec=node('span',c?.recording===true?'● RECORDING':c?.recording===false?'IDLE':'RECORDING UNKNOWN','recording-flag'+(c?.recording===true?' active':''));body.prepend(rec)}
   if(parts.length>1){
    const details=node('details');details.dataset.key=h.id+'-'+id;details.open=expanded.has(details.dataset.key);
    details.append(node('summary','Details'));const facts=node('div',null,'facts');for(const part of parts)facts.append(node('div',part,'fact'));details.append(facts);body.append(details);
   }
   card.append(body);
   const muteEntry=d.alerts?.mutes?.find(m=>m.hostId===h.id&&m.componentId===id);
   const muted=muteEntry?.muted===true;const mute=node('button',null,'mute-toggle'+(muted?' is-muted':''));
   mute.append(node('span','Mute','toggle-label'),node('span',null,'switch-track'));
   mute.type='button';mute.setAttribute('role','switch');mute.setAttribute('aria-checked',String(muted));mute.dataset.mute=h.id+':'+id;mute.setAttribute('aria-pressed',String(muted));mute.setAttribute('aria-label','Mute email alerts for '+(names[id]||id)+' on '+h.name);
   mute.disabled=!muteEntry||muting.has(mute.dataset.mute);mute.onclick=()=>setMute(h.id,id,!muted,mute);
   const signals=node('div',null,'service-signals');signals.append(head.lastElementChild,mute);head.append(signals);
   if(h.id==='dvr')for(const [action,a] of Object.entries(dvrActions))if(a.target===id)card.append(actionControl(action,a));
   if(h.id==='cloud'&&id==='racebot-ai'){card.append(actionControl('racebot-ai-reconnect',{label:'Reconnect RaceBot AI',allowed:d.aiReconnectAllowed,reason:d.aiReconnectReason}));card.append(actionControl('pitwall-restart',{label:'Restart RaceBot + Commentator',allowed:d.restartAllowed,reason:d.restartReason}));}
   if(h.id==='cloud'&&id==='commentator')card.append(actionControl('pitwall-restart',{label:'Restart RaceBot + Commentator',allowed:d.restartAllowed,reason:d.restartReason}));
   if(h.id==='cloud'&&id==='cloud-proxy')card.append(actionControl('proxy-restart',{label:'Restart DVR cloud proxy',allowed:d.proxyRestartAllowed,reason:d.proxyRestartReason}));
   grid.append(card);
  }
  host.append(grid);root.append(host);
 }
 const scoring=node('section',null,'host host-scoring');scoring.id='host-scoring';
 const scoringHead=node('div',null,'host-head'),scoringTitle=node('div',null,'host-title');
 scoringTitle.append(node('p','03 / SCORING WORKSTATION','eyebrow'),node('h2','SCORING PC'),node('p','Reserved for scoring workstation integration','host-description'));
 scoringHead.append(scoringTitle,node('span','Not configured','badge unknown'));scoring.append(scoringHead);
 for(const [pendingId,label] of [['agent-link','Management agent'],['streamdeck','Stream Deck plugin'],['control','Scoring control client']]){
  const row=node('div',null,'pending-row');row.id=monitorTarget('scoring',pendingId);row.tabIndex=-1;row.dataset.monitorTarget=row.id;row.append(node('h3',label),node('span','Pending setup','pending-state'),node('p','Monitoring and controls will be enabled after integration.','service-summary'));scoring.append(row)
 }
 root.append(scoring);
 const email=document.querySelector('#email-status');email.hidden=false;
 const mode=d.alerts?.mode||'not_configured';const modeLabels={enabled:'SES email alerts enabled',disabled:'Email sending disabled',not_configured:'Email setup required',invalid_configuration:'Email configuration needs attention'};
 email.replaceChildren(node('strong',modeLabels[mode]||'Email status unknown'),node('p','Red for 30 seconds → one email per incident. Muting suppresses email, not health checks.','sub'));
 const recent=d.alerts?.events||[];
 if(recent.length){const log=node('details');log.dataset.key='email-log';log.open=expanded.has('email-log');log.append(node('summary','Recent email notifications'));for(const e of recent)log.append(node('p',new Date(e.updated*1000).toLocaleString()+' · '+(names[e.component]||e.component)+' / '+e.host+' · '+e.state,'fact'));email.append(log)}
 const overview=document.querySelector('#overview');overview.replaceChildren();
 for(const [status,label] of [['green','Healthy'],['yellow','Degraded'],['red','Offline'],['unknown','Unknown']]){const metric=node('div',null,'metric');metric.append(node('strong',String(counts[status]),status),node('span',label));overview.append(metric)}
 const activity=document.querySelector('#activity');const signature=JSON.stringify(d.jobs||[]);
 if(signature!==activity.dataset.signature){activity.dataset.signature=signature;activity.replaceChildren();
  if(!d.jobs?.length)activity.append(node('p','No recovery actions recorded yet.','empty'));
  for(const j of d.jobs||[]){
   const event=node('article',null,'event');const info=node('div');
   const label=dvrActions[j.action]?.label||({'pitwall-restart':'Restart RaceBot + Commentator','proxy-restart':'Restart DVR cloud proxy','racebot-ai-reconnect':'Reconnect RaceBot AI'}[j.action])||j.action;
   info.append(node('p',label,'event-title'),node('p',j.result.replaceAll('_',' '),'event-result'));
   const state=j.state==='succeeded'?'green':j.state==='failed'?'red':['running','queued','dispatched'].includes(j.state)?'yellow':'unknown';
   event.append(node('time',new Date(j.created*1000).toLocaleString()),info,node('span',j.state,'badge '+state),node('p','ID '+j.id,'event-id'));activity.append(event);
  }
 }
 renderTopology(d,counts);
 document.querySelector('#updated').textContent='Updated '+new Date().toLocaleTimeString();
 if(focused)Array.from(document.querySelectorAll('button[data-action]')).find(e=>e.dataset.action===focused)?.focus({preventScroll:true});
 else if(focusedMute)Array.from(document.querySelectorAll('button[data-mute]')).find(e=>e.dataset.mute===focusedMute)?.focus({preventScroll:true});
 else if(focusedMonitor)document.getElementById(focusedMonitor)?.focus({preventScroll:true});
 else if(focusedDetail)Array.from(document.querySelectorAll('details')).find(e=>e.dataset.key===focusedDetail)?.querySelector('summary')?.focus({preventScroll:true});
}
function clearStatus(message){
 document.querySelector('#hosts').replaceChildren();document.querySelector('#overview').hidden=true;document.querySelector('#activity-panel').hidden=true;
 document.querySelector('#email-status').hidden=true;
 document.querySelector('#topology-panel').hidden=true;
 document.querySelector('#updated').textContent=message;document.querySelector('#backend-version').textContent=message;
}
let updating=false;
async function update(){if(updating)return;updating=true;try{
 const r=await fetch('/api/status');if(r.status===401){document.querySelector('#login').hidden=false;clearStatus('Sign in required');return}
 if(!r.ok)throw Error();const d=await r.json();render(d);
}catch{clearStatus('Connection unavailable');document.querySelector('#error').textContent='Backend unavailable. Current health is unknown.'}finally{updating=false}}
async function signin(){const token=document.querySelector('#token');try{const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:token.value})});token.value='';if(!r.ok){document.querySelector('#error').textContent='Sign-in failed';return}await update()}catch{token.value='';document.querySelector('#error').textContent='Backend unavailable'}};document.querySelector('#signin').onclick=signin;document.querySelector('#token').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();signin()}};document.querySelector('#cancel').onclick=()=>document.querySelector('#confirm').close();document.querySelector('#restart').onclick=restartGroup;update();setInterval(update,5000);

async function restartGroup(){if(sending)return;sending=true;document.querySelector('#restart').disabled=true;document.querySelector('#confirm').close();const bytes=crypto.getRandomValues(new Uint8Array(16));bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');const requestId=[hex.slice(0,8),hex.slice(8,12),hex.slice(12,16),hex.slice(16,20),hex.slice(20)].join('-');try{const r=await fetch('/api/actions/'+actionTarget,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({requestId,confirmation:dvrActions[actionTarget]?.label||(actionTarget==='racebot-ai-reconnect'?'Reconnect RaceBot AI':actionTarget==='proxy-restart'?'Restart DVR cloud proxy':'Restart RaceBot + Commentator')})});const d=await r.json();if(!r.ok)alert(d.error||'Restart request rejected');}catch{alert('Request outcome unknown. Check activity before retrying.')}finally{sending=false;document.querySelector('#restart').disabled=false;await update()}}

function openConfirm(target){actionTarget=target;if(target==='racebot-ai-reconnect'){document.querySelector('#actiontitle').textContent='Reconnect RaceBot AI?';document.querySelector('#actionimpact').textContent='Reloads the saved AI key and runs a small moderation and generation test. Does not post chat or restart applications. Cannot resolve quota, rate limits, model errors or a stuck application worker; use the shared restart if needed.';document.querySelector('#restart').textContent='Reconnect AI';document.querySelector('#confirm').showModal();return;}if(dvrActions[target]){const a=dvrActions[target];document.querySelector('#actiontitle').textContent=a.label.replace('Judge Cues','DVR Control Server')+'?';document.querySelector('#actionimpact').textContent=target==='dvr-health-run'?'Runs the existing health-check task and refreshes the report.':target==='dvr-obs-restart'?'OBS may close and reopen in the logged-in desktop session. Recovery is blocked while recording or when recording state cannot be established. Verify capture after recovery.':target==='dvr-judge-cues-restart'?'DVR Control Server sessions will disconnect. Recording must be idle. Verify the Lead Judge arm state after recovery.':'Only '+(names[a.target]||a.target)+' will restart. Its clients or transfers may be interrupted. Confirm no critical judging transaction is in progress.';document.querySelector('#restart').textContent='Confirm';document.querySelector('#confirm').showModal();return;}const proxy=target==='proxy-restart';document.querySelector('#actiontitle').textContent=proxy?'Restart DVR cloud proxy?':'Restart RaceBot + Commentator?';document.querySelector('#actionimpact').textContent=proxy?'Remote judge sessions will disconnect temporarily. Confirm no critical judging transaction is in progress. Only the Race DVR Judge Proxy task will restart; RaceBot and Commentator keep running. Recovery checks the proxy health endpoint, not reconnection of every judge.':'Both RaceBot and Commentator will be interrupted. The DVR proxy keeps running. HTTP and configured AI health are checked after restart. Live chat integrations may need reconnecting.';document.querySelector('#restart').textContent=proxy?'Confirm proxy restart':'Restart both applications';document.querySelector('#confirm').showModal()}

// Live topology uses the same evidence as the service list, never inferred link health.
function svgNode(tag,attrs={},text){
 const e=document.createElementNS('http://www.w3.org/2000/svg',tag);
 for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));
 if(text!==undefined)e.textContent=text;
 return e;
}
function jumpToMonitor(targetId){
 const target=document.getElementById(targetId);if(!target)return;
 const details=target.querySelector('details');if(details)details.open=true;
 history.replaceState(null,'','#'+targetId);
 target.focus({preventScroll:true});target.scrollIntoView({block:'start',behavior:'auto'});
}
function focusMapArea(area){
 const views={dvr:[390,420],cloud:[1030,170],scoring:[390,90],s3:[60,480]};
 const point=views[area],canvas=document.querySelector('#topology-canvas'),svg=canvas.querySelector('svg');
 if(!point||!svg)return;
 const scale=svg.getBoundingClientRect().width/1800;
 canvas.scrollTo({left:Math.max(0,point[0]*scale-12),top:Math.max(0,point[1]*scale-12),behavior:'auto'});
}
function positionInitialTopology(){
 const panel=document.querySelector('#topology-panel');
 if(topologyPositioned||panel.hidden||!panel.open)return;
 topologyPositioned=true;
 if(matchMedia('(max-width:900px)').matches)focusMapArea('dvr');
}
function buildTopology(){
 const panel=document.querySelector('#topology-panel');
 try{panel.open=localStorage.getItem('raceops.topology.collapsed')!=='true'}catch{panel.open=true}
 panel.addEventListener('toggle',()=>{try{localStorage.setItem('raceops.topology.collapsed',String(!panel.open))}catch{}positionInitialTopology()});
 for(const button of document.querySelectorAll('[data-map-view]'))button.addEventListener('click',()=>focusMapArea(button.dataset.mapView));
 const svg=svgNode('svg',{viewBox:'0 0 1800 1180',class:'topology-svg',role:'group','aria-labelledby':'topology-svg-title topology-svg-description'});
 svg.append(svgNode('title',{id:'topology-svg-title'},'Race Operations live topology'),svgNode('desc',{id:'topology-svg-description'},'Scoring PC above DVR PC on the left, Cloud PC on the right, S3 storage and Internet connections. Each monitored service links to its detailed row below. Unmonitored services have no health status.'));
 const wires=svgNode('g',{'aria-hidden':'true',class:'map-wires'}),frames=svgNode('g'),rows=svgNode('g'),ports=svgNode('g',{'aria-hidden':'true','pointer-events':'none'});svg.append(wires,frames,rows,ports);
 const entries=[];
 function box(x,y,w,h,title,subtitle,kind='context'){
  const g=svgNode('g',{class:'map-frame map-'+kind});
  g.append(svgNode('rect',{x,y,width:w,height:h,rx:9}),svgNode('text',{x:x+18,y:y+32,class:'map-host-title'},title));
  if(subtitle)g.append(svgNode('text',{x:x+18,y:y+57,class:'map-context-note'},subtitle));
  frames.append(g);
 }
 function row(x,y,w,label,host,id,context){
  const target=host?monitorTarget(host,id):null;
  const a=svgNode(target?'a':'g',{class:'map-node '+(host&&host!=='scoring'?'map-live state-unknown':'map-context'),...(target?{href:'#'+target,'data-map-target':target}:{}),...(host&&host!=='scoring'?{'data-monitor-key':host+':'+id}:{})});
  const title=svgNode('title');a.append(title,svgNode('rect',{x,y,width:w,height:56,rx:3,class:'map-node-bg'}));
  const dot=svgNode('circle',{cx:x+17,cy:y+21,r:5,class:'map-status-dot'});
  const name=svgNode('text',{x:x+31,y:y+25,class:'map-node-name'},label);
  const status=svgNode('text',{x:x+31,y:y+45,class:'map-node-status'},context||'Waiting for evidence');
  const mute=svgNode('text',{x:x+w-12,y:y+45,class:'map-muted','text-anchor':'end'});
  a.append(dot,name,status,mute);rows.append(a);
  if(target)a.addEventListener('click',event=>{if(event.button===0&&!event.ctrlKey&&!event.metaKey&&!event.shiftKey&&!event.altKey){event.preventDefault();jumpToMonitor(target)}});
  if(host&&host!=='scoring')entries.push({element:a,title,status,mute,host,id,label});
  else{title.textContent=label+': '+context;a.setAttribute('aria-label',label+': '+context+(target?'. View pending setup.':''))}
 }
 function group(x,y,w,title,kind,items){
  box(x,y,w,52+56*items.length,title,null,kind);
  items.forEach((r,i)=>row(x,y+52+56*i,w,...r));
 }
 function wire(points,label,at,kind='data'){
  const pointText=points.map(p=>p.join(',')).join(' ');
  wires.append(svgNode('polyline',{points:pointText,class:'wire-underlay'}),svgNode('polyline',{points:pointText,class:'wire-'+kind}));
  if(label){const [x,y]=at;ports.append(svgNode('rect',{x:x-31,y:y-16,width:62,height:32,rx:6,class:'port-bg'}),svgNode('text',{x,y:y+7,'text-anchor':'middle',class:'port-text'},label))}
 }
 group(390,90,400,'SCORING PC','scoring',[
  ['Management agent','scoring','agent-link','Pending setup'],['Stream Deck plugin','scoring','streamdeck','Pending setup'],['Scoring control client','scoring','control','Pending setup']]);
 group(390,420,400,'OBS / DVR PC','dvr',[
  ['Management agent','dvr','agent-link'],['DVR Control Server','dvr','judge-cues'],['OBS Studio','dvr','obs'],['Race tracking app',null,null,'Not monitored'],['Review Status','dvr','review-status'],['IIS Judge Review','dvr','iis'],['S3 uploader','dvr','uploader'],['Cloud connector','dvr','connector'],['DVR disk space','dvr','disk-network'],['System health check','dvr','health-monitor']]);
 group(1030,170,400,'CLOUD WINDOWS PC','cloud',[
  ['Management agent','cloud','agent-link'],['Remote judge proxy','cloud','cloud-proxy'],['Race Operations dashboard',null,null,'This page · no separate monitor'],['RaceBot','cloud','racebot'],['RaceBot AI','cloud','racebot-ai'],['Commentator Desk','cloud','commentator'],['System disk C:','cloud','disk-space']]);
 group(60,480,250,'AMAZON S3','storage',[
  ['Pilot Review','dvr','pilot-review'],['DVR files',null,null,'No direct bucket check']]);
 box(60,190,250,72,'STREAM DECK','Pending scoring setup');
 box(1550,620,200,240,'INTERNET','Not monitored');
 box(1190,1060,320,80,'LIVETIME EVENT','Not monitored');
 wire([[310,226],[390,226]],null);
 wire([[390,282],[350,282],[350,556],[390,556]],'8766',[350,380],'control');
 wire([[790,170],[870,170],[870,362],[1030,362]],'8799',[870,265],'management');
 wire([[790,500],[930,500],[930,382],[1030,382]],'8799',[930,450],'management');
 wire([[1030,250],[990,250],[990,342],[1030,342]],'8799',[990,296],'management');
 wire([[790,556],[835,556],[835,612],[790,612]],'4455',[835,584],'control');
 wire([[390,836],[310,836],[310,616]],'443',[310,750]);
 wire([[790,668],[1120,668],[1120,1100],[1190,1100]],'443',[1050,668]);
 wire([[790,892],[905,892],[905,580],[1515,580],[1515,306],[1430,306]],'8767',[1200,580]);
 wire([[1430,306],[1490,306],[1490,660],[1550,660]],'8767',[1490,630]);
 wire([[1430,362],[1470,362],[1470,710],[1550,710]],'80',[1510,710]);
 wire([[1430,418],[1450,418],[1450,760],[1550,760]],'8765',[1505,760]);
 wire([[1430,530],[1440,530],[1440,810],[1550,810]],'8766',[1505,810]);
 wire([[60,560],[30,560],[30,48],[1650,48],[1650,620]],'80',[1200,48]);
 wire([[1650,860],[1650,1100],[1510,1100]],null);
 document.querySelector('#topology-canvas').append(svg);
 return entries;
}
let topologyEntries=null,topologyPositioned=false;
function renderTopology(d,counts){
 if(!topologyEntries)topologyEntries=buildTopology();
 document.querySelector('#topology-panel').hidden=false;
 positionInitialTopology();
 const labels={green:'Healthy',yellow:'Degraded',red:'Offline',unknown:'Unknown'};
 for(const entry of topologyEntries){
  const c=monitorEvidence(d.hosts,entry.host,entry.id),status=labels[c?.status]?c.status:'unknown';
  const muted=d.alerts?.mutes?.some(m=>m.hostId===entry.host&&m.componentId===entry.id&&m.muted===true);
  let detail=labels[status];
  if(entry.id==='obs')detail+=' · '+(c?.recording===true?(c.recordingPaused?'Recording paused':'Recording'):c?.recording===false?'Idle':'Recording unknown');
  if(entry.id==='disk-space'||entry.id==='disk-network')if(Number.isFinite(c?.freePercent))detail+=' · '+c.freePercent+'% free';
  entry.element.setAttribute('class','map-node map-live state-'+status);entry.element.dataset.status=status;
  entry.status.textContent=detail;entry.mute.textContent=muted?'MUTED':'';
  const label=entry.label+' on '+(entry.host==='cloud'?'Cloud PC':'DVR PC')+': '+detail+(muted?'. Email alerts muted.':'.')+' View monitor details.';
  entry.element.setAttribute('aria-label',label);entry.title.textContent=label;
 }
 const mutedCount=topologyEntries.filter(e=>d.alerts?.mutes?.some(m=>m.hostId===e.host&&m.componentId===e.id&&m.muted)).length;
 document.querySelector('#topology-rollup').textContent=topologyEntries.length+' monitors · '+counts.red+' offline · '+counts.yellow+' degraded · '+counts.unknown+' unknown'+(mutedCount?' · '+mutedCount+' muted':'');
}
