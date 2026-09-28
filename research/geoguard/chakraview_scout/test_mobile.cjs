// Safe JS execution tests with a minimal DOM stub; NOT browser/visual QA.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const html=fs.readFileSync(path.join(__dirname,'outputs/mobile_demo.html'),'utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const nodes={};
for(const id of ['scenario','step','coverage','remaining','recommendation','observe','view','navigate','message','terms','map','secondary','comparison','status','queue']){
  nodes[id]={value:'0',textContent:'',innerHTML:'',disabled:false,selectedOptions:[{text:'mountain / GROUND'}],options:[],add(o){this.options.push(o)},scrollIntoView(){this.scrolled=true}};
}
nodes.status.value='NOTE';let storage={};
const context={document:{getElementById:id=>nodes[id]},Option:function(text,value){this.text=text;this.value=value},localStorage:{getItem:k=>storage[k],setItem:(k,v)=>{storage[k]=v}},console};
vm.createContext(context);vm.runInContext(script,context);
let checks=0;function check(test){assert(test);checks++}
check(nodes.scenario.options.length===6);check(nodes.remaining.textContent==='100.0%');
check(nodes.recommendation.innerHTML.includes('GROUND'));check(nodes.map.innerHTML.includes('<rect'));
nodes.observe.onclick();check(nodes.step.value==='1');check(nodes.remaining.textContent!=='100.0%');
nodes.navigate.onclick();check(nodes.message.textContent.includes('no safe route'));
nodes.view.onclick();check(nodes.map.scrolled&&nodes.message.textContent.includes('not connected'));
nodes.queue.onclick();check(JSON.parse(storage['scout-notes']).length===1);
for(let i=0;i<6;i++){
  nodes.scenario.value=String(i);nodes.scenario.onchange();check(nodes.step.value==='0');
  check(nodes.comparison.innerHTML.includes('random (30 seeds)'));
  for(let j=0;j<5;j++)nodes.observe.onclick();
  check(nodes.step.value==='5'&&nodes.observe.disabled);check(nodes.recommendation.innerHTML.includes('completed'));
  check(!nodes.comparison.innerHTML.includes('NaN')&&!nodes.comparison.innerHTML.includes('Infinity'));
}
context.localStorage.setItem=()=>{throw Error('disabled')};nodes.queue.onclick();check(nodes.message.textContent.includes('not saved'));
console.log(`${checks} mobile JavaScript assertions passed (DOM stub, not visual browser verification)`);
