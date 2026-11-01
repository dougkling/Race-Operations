const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('cloud/web/app.js','utf8').split('const names=')[0];
// Extract only the pure evidence function; do not initialize browser handlers.
const helper=source.slice(0,source.indexOf('\nlet ' )>=0?source.indexOf('\nlet '):source.length);
const context={};vm.createContext(context);vm.runInContext(helper.split("const $=")[0],context);
function check(connected,status,value,expected){const result=context.connectorEvidence([{id:'cloud',connected,sample:{components:[{id:'cloud-proxy',status,dvrConnected:value,remoteJudges:0}]}},{id:'dvr',connected:false}]);assert.equal(result.status,expected);return result;}
assert.match(check(true,'green',true,'green').detail,/Remote judges: 0/);
check(true,'green',false,'red');check(true,'red',true,'unknown');check(false,'green',true,'unknown');check(true,'green','true','unknown');assert.equal(context.connectorEvidence([]).status,'unknown');
console.log('Connector UI evidence checks passed');
assert.equal(context.diskDetail(null),'Disk capacity unavailable');
assert.match(context.diskDetail({freeBytes:72.4*1073741824,totalBytes:99*1073741824,freePercent:73.2}),/72.4 GiB free \/ 99.0 GiB \(73.2%\)/);
console.log('Disk display checks passed');
assert.equal(context.healthDetail(null),'Health-check evidence unavailable');
assert.match(context.healthDetail({healthReason:'warnings',taskState:'Ready',lastTaskResult:0,reportAgeSeconds:60,passes:23,warnings:3,failures:0,warningChecks:['Graphics race source']}),/23 pass, 3 warning, 0 failure/);
console.log('Health-report display checks passed');
