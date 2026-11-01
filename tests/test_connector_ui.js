const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('cloud/web/app.js','utf8').split('const names=')[0];
// Extract only the pure evidence function; do not initialize browser handlers.
const helper=source.slice(0,source.indexOf('\nlet ' )>=0?source.indexOf('\nlet '):source.length);
const context={};vm.createContext(context);vm.runInContext(helper.split("const $=")[0],context);
function check(connected,status,value,expected){const result=context.connectorEvidence([{id:'cloud',connected,sample:{components:[{id:'cloud-proxy',status,dvrConnected:value,remoteJudges:0}]}},{id:'dvr',connected:false}]);assert.equal(result.status,expected);return result;}
assert.match(check(true,'green',true,'green').detail,/Remote judges: 0/);
check(true,'green',false,'red');check(true,'red',true,'unknown');check(false,'green',true,'unknown');check(true,'green','true','unknown');assert.equal(context.connectorEvidence([]).status,'unknown');
console.log('Connector UI evidence checks passed');
