const fs=require('fs'),path=require('path'),crypto=require('crypto');
const root=path.resolve(__dirname,'..');
const S=require(path.join(root,'state.js')), levels=require(path.join(root,'levels.js'));
const hash=crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'state.js'))).digest('hex');
const cases=[], checks=[];
const clone=x=>JSON.parse(JSON.stringify(x));
const policy=(ref,sense='켜짐',act='열다')=>['수리',['말',['문',[act,['때',[ref,sense]]]]]];
const move=side=>['수리',['가다',side]];
const bind=ref=>['수리',['○',['묶다',ref]]];
function say(sc,w,t){const r=sc.submit(t,w,'suri');if(!r.ok)throw Error(r.message);return r.state;}
function run(id,name,ref,{binding,moves,inverse=false}={}){
 const sc=levels.find(x=>x.id===id);let w=clone(sc.initial);
 if(binding){if(id===5)w=say(sc,w,move('오른쪽'));w=say(sc,w,bind(binding));}
 w=say(sc,w,policy(ref,inverse?'꺼짐':'켜짐',inverse?'닫다':'열다'));
 for(let k=0;k<4;k++){if(moves)w=say(sc,w,move(moves[k]));w=sc.interact('bell',w).state;}
 const out={id,name,complete:w.complete,trace:w.trace,messages:w.last};cases.push(out);return out;
}
const ok=(value,name)=>checks.push({name,pass:!!value});
const expected={1:[true,false,true,false],2:[false,true,false,true],3:[true,false,true,false],4:[true,true,false,false],5:[false,true,false,true],6:[false,true,true,false]};
const one=run(1,'left sustained','왼등');ok(one.complete,'01 지속조건 완료');
const sc2=levels.find(x=>x.id===2);let w2=say(sc2,clone(sc2.initial),policy('왼등','꺼짐'));for(let k=0;k<4;k++)w2=sc2.interact('bell',w2).state;cases.push({id:2,name:'off-left sustained',complete:w2.complete,trace:w2.trace});ok(w2.complete,'02 반전 완료');
const threeOld=run(3,'previous location policy','왼등');ok(!threeOld.complete&&threeOld.trace.some(x=>!x.pass),'03 이전 자리정책 실패');
const three=run(3,'identity binding','○',{binding:'왼등'});ok(three.complete,'03 실물고정 완료');
const fourOld=run(4,'previous identity policy','○');ok(!fourOld.complete&&fourOld.trace.some(x=>!x.pass),'04 이전 실물정책 실패');
const four=run(4,'current location','왼등');ok(four.complete,'04 현재자리 완료');
const fiveStill=run(5,'identity with stationary observer','○',{binding:'오른등'});ok(!fiveStill.complete&&fiveStill.trace.some(x=>!x.known),'05 고정시야 실패');
const moves=['오른쪽','왼쪽','왼쪽','오른쪽'];
const fivePosition=run(5,'location reference with identity following','오른등',{moves});ok(!fivePosition.complete,'05 실물고정 없이 오른등정책 실패');
const five=run(5,'identity and observation following','○',{binding:'오른등',moves});ok(five.complete,'05 실물고정+시야이동 완료');
const sixOld=run(6,'previous fixed identity','○');ok(!sixOld.complete&&sixOld.trace.some(x=>!x.known),'06 이전 고정실물정책 실패');
const six=run(6,'relative observation','앞등');ok(six.complete,'06 앞등 상대관측 완료');
for(const r of [one,{id:2,trace:w2.trace},three,four,five,six])ok(JSON.stringify(r.trace.map(x=>x.actual))===JSON.stringify(expected[r.id]),r.id+' 공개 목표 출력과 실제 출력 일치');
for(const [id,ref,opt] of [[1,'왼등',{}],[3,'○',{binding:'왼등'}],[4,'왼등',{}],[5,'○',{binding:'오른등',moves}],[6,'앞등',{}]])ok(run(id,'equivalent inverse policy',ref,{...opt,inverse:true}).complete,id+' 닫다/꺼짐 동등정책 허용');
// Policy replacement after each step previously bypassed all conditional-reference mechanics.
for(const id of [1,3,4,5,6]){const sc=levels.find(x=>x.id===id);let w=clone(sc.initial);for(const want of expected[id]){w=say(sc,w,['수리',['말',['문',want?'열다':'닫다']]]);w=sc.interact('bell',w).state;}cases.push({id,name:'unconditional policy replaced every tick',complete:w.complete,trace:w.trace});ok(!w.complete,id+' 매틱 무조건정책 교체 우회 차단');}
// Direct one-off door requests must not replace the sustained instruction.
const sc=levels[0];let w=clone(sc.initial);const before=JSON.stringify(w.policy);w=say(sc,w,['수리',['문','닫다']]);ok(JSON.stringify(w.policy)===before,'지금 요청은 지속지시 변경하지 않음');
// Syntax ambiguity must not silently prefer moving/binding/unbinding over a second action.
for(const t of [['수리',['가다','오른쪽'],['말',['문','열다']]],['수리',['○',['풀다']],['문','닫다']],['수리',['○',['묶다','왼등']],['문','열다']]]){const r=levels[2].submit(t,clone(levels[2].initial),'suri');checks.push({name:'독립 행동 혼합 거절: '+JSON.stringify(t),pass:!r.ok,observed:r.message});}
const report={type:'independent state QA, not UI completion or human play',state_sha256:hash,checks,cases};
fs.writeFileSync(path.join(__dirname,'state-review-results.json'),JSON.stringify(report,null,2));
fs.mkdirSync(path.join(__dirname,'state-revisions'),{recursive:true});fs.writeFileSync(path.join(__dirname,'state-revisions',hash.slice(0,12)+'.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify({state_sha256:hash,checks:checks.length,pass:checks.filter(x=>x.pass).length,fail:checks.filter(x=>!x.pass)}));
process.exitCode=checks.some(x=>!x.pass)?1:0;
