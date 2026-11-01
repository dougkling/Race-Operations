const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.textContent='';this.disabled=false;}
 append(...items){this.children.push(...items)}
 replaceChildren(...items){this.children=items}
 showModal(){this.open=true} close(){this.open=false}
}
const elements={};const document={createElement:tag=>new Element(tag),querySelector:key=>elements[key]||(elements[key]=new Element(key))};
let payload={csrf:'test',hosts:[{id:'dvr',name:'DVR',connected:true,sample:{components:[]}}],jobs:[],dvrActions:{'dvr-iis-restart':{label:'Restart IIS Judge Review',target:'iis',allowed:true,reason:'Failure detected'},'dvr-obs-restart':{label:'Restart OBS Studio',target:'obs',allowed:false,reason:'Recording active or unknown'}}};
const context={document,fetch:async()=>({ok:true,status:200,json:async()=>payload}),setInterval:()=>{},console,Date,crypto:require('crypto').webcrypto,Uint8Array,alert:()=>{}};
vm.createContext(context);vm.runInContext(fs.readFileSync('cloud/web/app.js','utf8'),context);
(async()=>{
 await context.update();const card=elements['#hosts'].children[0];
 const buttons=card.children.filter(x=>x.tag==='button');
 assert.equal(buttons.length,2);assert.equal(buttons[0].disabled,false);assert.equal(buttons[1].disabled,true);
 assert(!card.children.some(x=>x.textContent==='DVR controls disabled'));
 buttons[0].onclick();assert.equal(elements['#actiontitle'].textContent,'Restart IIS Judge Review?');
 assert.equal(elements['#confirm'].open,true);
 let sent;context.fetch=async(url,options)=>{if(options){sent=JSON.parse(options.body);return{ok:true,json:async()=>({})}}return{ok:true,status:200,json:async()=>payload}};
 await context.restartGroup();assert.equal(sent.confirmation,'Restart IIS Judge Review');assert.match(sent.requestId,/^[a-f0-9-]{36}$/);
 console.log('DVR buttons, disabled guard and confirmation request passed');
})().catch(e=>{console.error(e);process.exitCode=1});
