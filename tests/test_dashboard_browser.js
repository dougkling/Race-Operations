// Browser regression checks with synthetic status; never contacts a live DVR.
const {chromium}=require('playwright'),fs=require('fs'),assert=require('assert');
const now=Date.now()/1000;
const names={'judge-cues':'Judge Cues','review-status':'Review Status','iis':'IIS Judge Review',uploader:'S3 Uploader',connector:'Cloud Connector',obs:'OBS Studio','health-monitor':'system health check'};
const dvrActions=Object.fromEntries(Object.entries(names).map(([target,name])=>[target==='health-monitor'?'dvr-health-run':'dvr-'+target+'-restart',{target,label:(target==='health-monitor'?'Run ':'Restart ')+name,allowed:target==='health-monitor'||target==='iis',reason:target==='health-monitor'?'Run the existing check and refresh its saved report':target==='iis'?'Only this component will restart; confirm no critical judging transaction is in progress':'Target is green'}]));
const status={version:'0.9.0',csrf:'fixture',restartAllowed:false,restartReason:'Target is green',proxyRestartAllowed:false,proxyRestartReason:'Target is green',dvrActions,hosts:[{id:'cloud',name:'Cloud Windows PC',connected:true,sample:{components:[{id:'racebot',status:'green',latencyMs:7},{id:'commentator',status:'green',latencyMs:4},{id:'cloud-proxy',status:'green',dvrConnected:true,remoteJudges:0},{id:'disk-space',status:'green',freeBytes:73.1*2**30,totalBytes:99*2**30,freePercent:73.8}]}},{id:'dvr',name:'OBS / DVR PC',connected:true,sample:{components:[...['judge-cues','review-status'].map(id=>({id,status:'green',latencyMs:4})),{id:'iis',status:'red'},{id:'obs',status:'green',obsConnected:true,recording:false},{id:'uploader',status:'green',taskState:'Running',heartbeatAgeSeconds:60,operation:'idle',uploaderReason:'healthy'},{id:'disk-network',status:'green',freeBytes:67.8*2**30,totalBytes:231.8*2**30,freePercent:29.3},{id:'pilot-review',status:'green',pilotReason:'healthy',pageOk:true,manifestOk:true,raceCount:339,currentVideo:'pass',archivedVideo:'pass',manifestAgeSeconds:72000,lastCheckedEpoch:Math.floor(now)},{id:'scoring',status:'unknown'},{id:'health-monitor',status:'yellow',healthReason:'warnings',taskState:'Ready',lastTaskResult:0,lastRunEpoch:Math.floor(now),reportAgeSeconds:60,passes:25,warnings:1,failures:0,warningChecks:['Graphics race source']} ]}}],jobs:[{id:'4acb73f4-e723-457f-a4b9-a3df6629e58e',action:'dvr-health-run',created:now-120,state:'succeeded',result:'health_check_completed'}]};
status.aiReconnectAllowed=false;status.aiReconnectReason='Target is green';
if(!status.hosts[0].sample.components.some(c=>c.id==='racebot-ai'))status.hosts[0].sample.components.push({id:'racebot-ai',status:'green',aiReason:'healthy',lastCheckedEpoch:Math.floor(now)});
status.alerts={mode:'enabled',events:[],mutes:status.hosts.flatMap(h=>[...h.sample.components.map(c=>c.id),'agent-link',...(h.id==='dvr'?['connector']:[])].map(componentId=>({hostId:h.id,componentId,muted:false})))};
(async()=>{const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox','--disable-dev-shm-usage','--single-process','--disable-gpu','--disable-software-rasterizer']}: {})});const page=await browser.newPage();let posted=null,unauthorized=false,backendUnavailable=false;const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.route('http://raceops.test/**',async route=>{const u=new URL(route.request().url());if(u.pathname==='/api/status')return route.fulfill({status:unauthorized?401:backendUnavailable?503:200,contentType:'application/json',body:JSON.stringify(status)});if(u.pathname==='/api/monitor-mute'){const b=route.request().postDataJSON();assert.equal(route.request().headers()['x-csrf-token'],'fixture');status.alerts.mutes.find(m=>m.hostId===b.hostId&&m.componentId===b.componentId).muted=b.muted;return route.fulfill({contentType:'application/json',body:'{}'})}if(u.pathname.startsWith('/api/actions/')){posted=route.request().postDataJSON();return route.fulfill({status:202,contentType:'application/json',body:'{}'})}return route.fulfill({contentType:u.pathname==='/app.js'?'text/javascript':'text/html',body:fs.readFileSync('cloud/web/'+(u.pathname==='/app.js'?'app.js':'index.html'),'utf8')})});
for(const width of [1440,768,390,320]){
 await page.setViewportSize({width,height:1000});await page.goto('http://raceops.test/');await page.waitForSelector('.service');
 assert.equal(await page.locator('.map-live').count(),16);
 if(width<=900){
  assert(await page.locator('#topology-canvas').evaluate(e=>e.scrollLeft>0&&e.scrollTop>0));
  for(const area of ['cloud','scoring','s3','dvr']){
   await page.locator('[data-map-view="'+area+'"]').click();
   const selector=area==='s3'?'[data-monitor-key="dvr:pilot-review"]':area==='scoring'?'[data-map-target="monitor-scoring-agent-link"]':'[data-monitor-key="'+area+':agent-link"]';
   assert(await page.locator(selector).evaluate(e=>{const a=e.getBoundingClientRect(),b=document.querySelector('#topology-canvas').getBoundingClientRect();return a.left>=b.left&&a.left<b.right&&a.top>=b.top&&a.bottom<=b.bottom}));
  }
 }
 assert(await page.evaluate(()=>Array.from(document.querySelectorAll('.map-live')).every(a=>document.getElementById(a.dataset.mapTarget)?.classList.contains('state-'+a.dataset.status))));
 assert.equal(await page.locator('.service').count(),16);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 assert.equal(await page.getByRole('switch').count(),16);assert.equal(await page.locator('#host-scoring .pending-row').count(),3);assert.equal(await page.locator('#host-scoring button').count(),0);
 const mute=page.locator('[data-mute="dvr:iis"]');assert.equal(await mute.getAttribute('role'),'switch');await mute.click();await page.waitForFunction(()=>document.querySelector('[data-mute="dvr:iis"]').getAttribute('aria-pressed')==='true');await page.evaluate(()=>update());assert.equal(await mute.getAttribute('aria-pressed'),'true');await mute.click();await page.waitForFunction(()=>document.querySelector('[data-mute="dvr:iis"]').getAttribute('aria-pressed')==='false');
 assert(await page.getByRole('button',{name:'Restart OBS Studio',exact:true}).isDisabled());
 const details=page.locator('[data-component="health-monitor"] details');await details.locator('summary').click();await page.evaluate(()=>update());assert(await details.evaluate(e=>e.open));
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.getByRole('button',{name:'Restart IIS Judge Review',exact:true}).click();assert(await page.locator('#confirm').isVisible());
 assert(await page.locator('#confirm').evaluate(e=>e.getBoundingClientRect().width<=innerWidth));await page.locator('#restart').click();assert.equal(posted.confirmation,'Restart IIS Judge Review');
 if(process.env.SCREENSHOTS){await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:process.env.SCREENSHOTS+'/raceops-'+width+'.png',fullPage:true})}
}

// AI failure enables only explicit, CSRF-protected recovery and mirrors on the map.
const ai=status.hosts[0].sample.components.find(c=>c.id==='racebot-ai');
await page.goto('http://raceops.test/');await page.waitForSelector('.service');
assert(await page.getByRole('button',{name:'Reconnect RaceBot AI',exact:true}).isDisabled());
ai.status='red';ai.aiReason='timeout';status.aiReconnectAllowed=true;status.aiReconnectReason='AI failed';
await page.evaluate(()=>update());
assert.equal(await page.locator('[data-monitor-key="cloud:racebot-ai"]').getAttribute('data-status'),'red');
await page.getByRole('button',{name:'Reconnect RaceBot AI',exact:true}).click();
assert.match(await page.locator('#actionimpact').textContent(),/Does not post chat/);
await page.locator('#restart').click();assert.equal(posted.confirmation,'Reconnect RaceBot AI');
ai.status='green';ai.aiReason='healthy';status.aiReconnectAllowed=false;await page.evaluate(()=>update());

// Every live map node jumps to its exact host-scoped row; no recovery is triggered.
await page.setViewportSize({width:1440,height:1100});await page.goto('http://raceops.test/');await page.waitForSelector('.map-live');
const targets=await page.locator('.map-live').evaluateAll(nodes=>nodes.map(n=>n.dataset.mapTarget));
for(const target of targets){
 await page.locator('[data-map-target="'+target+'"]').click();
 assert.equal(await page.evaluate(()=>location.hash),'#'+target);
 assert.equal(await page.evaluate(()=>document.activeElement.id),target);
 const details=page.locator('#'+target+' details');if(await details.count())assert(await details.evaluate(e=>e.open));
}
const obsLink=page.locator('[data-monitor-key="dvr:obs"]');
await obsLink.focus();await page.keyboard.press('Enter');
assert.equal(await page.evaluate(()=>document.activeElement.id),'monitor-dvr-obs');
await page.evaluate(()=>update());assert.equal(await page.evaluate(()=>document.activeElement.id),'monitor-dvr-obs');
const panel=page.locator('#topology-panel'),summary=page.locator('.topology-summary');
await summary.click();assert.equal(await panel.evaluate(e=>e.open),false);
await page.waitForFunction(()=>localStorage.getItem('raceops.topology.collapsed')==='true');
await page.evaluate(()=>update());assert.equal(await panel.evaluate(e=>e.open),false);
await page.reload();await page.waitForSelector('.service');assert.equal(await panel.evaluate(e=>e.open),false);
await summary.focus();await page.keyboard.press('Enter');assert(await panel.evaluate(e=>e.open));
await page.waitForFunction(()=>localStorage.getItem('raceops.topology.collapsed')==='false');
// Live state, disk, recording, mute and stale evidence stay in sync with the service rows.
const dvr=status.hosts.find(h=>h.id==='dvr'),cloud=status.hosts.find(h=>h.id==='cloud');
const obs=dvr.sample.components.find(c=>c.id==='obs'),proxy=cloud.sample.components.find(c=>c.id==='cloud-proxy');
obs.recording=true;await page.evaluate(()=>update());assert.match(await obsLink.textContent(),/Recording/);
obs.recording=false;obs.status='red';await page.evaluate(()=>update());assert.equal(await obsLink.getAttribute('data-status'),'red');
assert.match(await page.locator('#topology-rollup').textContent(),/2 offline/);
const mute=page.locator('[data-mute="dvr:obs"]');await mute.click();await page.waitForFunction(()=>document.querySelector('[data-monitor-key="dvr:obs"] .map-muted').textContent==='MUTED');
assert.equal(await obsLink.getAttribute('data-status'),'red');
dvr.connected=false;dvr.agentStatus='red';await page.evaluate(()=>update());
assert.equal(await obsLink.getAttribute('data-status'),'unknown');assert.equal(await page.locator('[data-monitor-key="dvr:agent-link"]').getAttribute('data-status'),'red');
assert.equal(await page.locator('[data-monitor-key="dvr:connector"]').getAttribute('data-status'),'green');
proxy.dvrConnected=false;await page.evaluate(()=>update());assert.equal(await page.locator('[data-monitor-key="dvr:connector"]').getAttribute('data-status'),'red');
cloud.connected=false;await page.evaluate(()=>update());assert.equal(await page.locator('[data-monitor-key="dvr:connector"]').getAttribute('data-status'),'unknown');
assert(await page.evaluate(()=>!Array.from(document.querySelectorAll('.map-context')).some(n=>n.classList.contains('state-green'))));
await page.locator('[data-map-target="monitor-scoring-control"]').click();assert.equal(await page.evaluate(()=>document.activeElement.id),'monitor-scoring-control');
// Retain scroll and SVG node identity across refreshes.
dvr.connected=true;dvr.agentStatus='green';cloud.connected=true;proxy.dvrConnected=true;obs.status='green';
await page.setViewportSize({width:390,height:844});await page.evaluate(()=>{window.savedMapNode=document.querySelector('[data-monitor-key="dvr:obs"]');const c=document.querySelector('#topology-canvas');c.scrollLeft=400;c.scrollTop=200});
await page.evaluate(()=>update());assert(await page.evaluate(()=>window.savedMapNode===document.querySelector('[data-monitor-key="dvr:obs"]')));
assert.equal(await page.locator('#topology-canvas').evaluate(e=>e.scrollLeft),400);
assert.equal(await page.locator('#topology-canvas').evaluate(e=>e.scrollTop),200);
assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
backendUnavailable=true;await page.evaluate(()=>update());assert(await panel.isHidden());assert.match(await page.locator('#error').textContent(),/Backend unavailable/);
backendUnavailable=false;await page.evaluate(()=>update());assert(await panel.isVisible());
unauthorized=true;await page.evaluate(()=>update());assert(await panel.isHidden());
assert(await page.locator('#login').isVisible());assert(await page.locator('#overview').isHidden());assert(await page.locator('#activity-panel').isHidden());assert.equal(errors.length,0,errors.join('\n'));await browser.close();console.log('Dashboard passed at 1440, 768, 390 and 320px: map/row status parity, all 16 jumps, keyboard links, remembered collapse, live/unknown/muted states, persistent map scroll/focus, no overflow, guarded controls and session expiry.');
})().catch(e=>{console.error(e);process.exit(1)});
