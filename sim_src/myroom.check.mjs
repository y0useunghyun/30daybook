// 내 방 경로: 객차 남쪽 문 클릭 → 걸어 들어가기 → 책상 종이 → 다시 나오기. node myroom.check.mjs [주소] [스크린샷폴더]
import { chromium } from 'playwright-core'; import assert from 'node:assert';
const URL_=process.argv[2]||'http://127.0.0.1:8030/', out=process.argv[3]||'.';
const b=await chromium.launch({channel:'chrome',headless:true,args:['--use-angle=metal','--enable-gpu','--ignore-gpu-blocklist']});
const p=await b.newPage({viewport:{width:1280,height:800}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message)); p.on('response',r=>{if(r.status()>=400&&!/favicon/.test(r.url()))errs.push(r.status()+' '+r.url())});
await p.goto(URL_+'#sim'); await p.waitForSelector('#sim.ready',{state:'attached',timeout:120000}); await p.waitForTimeout(1500);
const mod=new URL('sim/sim.js',URL_).href; const m=(fn,...a)=>p.evaluate(([mod,fn,a])=>import(mod).then(x=>x[fn](...a)),[mod,fn,a]);
const over=()=>p.evaluate(()=>document.querySelector('#sim canvas').classList.contains('over-paper'));
await p.evaluate(()=>document.querySelector('.sim-door').click()); await p.waitForTimeout(2500); // 교실 문 열고
await m('pose',8.675,-1.7,-90,0,58); await p.waitForTimeout(1500);
let w=await m('where'); assert(!w.doors.find(d=>d[0]==='C')[1],'처음엔 닫힘');
// 닫혀 있으면 막힘
await p.keyboard.down('w'); await p.waitForTimeout(1500); await p.keyboard.up('w'); w=await m('where'); assert(w.y>-3.05,'닫힌 문 막힘 y='+w.y); console.log('닫힌 문 막힘 OK y=',w.y.toFixed(2));
await m('pose',8.675,-1.7,-90,0,58); await p.waitForTimeout(300); await p.mouse.move(640,400); await p.waitForTimeout(80); assert(await over(),'문 위 손가락'); await p.mouse.click(640,400); await p.waitForTimeout(2200);
w=await m('where'); assert(w.doors.find(d=>d[0]==='C')[1],'남쪽 문 열림'); console.log('남쪽 문 클릭 열림 OK');
await p.keyboard.down('w'); await p.waitForTimeout(3000); await p.keyboard.up('w'); w=await m('where'); assert(w.y<-3.6,'방 진입 y='+w.y); console.log('방 진입 OK y=',w.y.toFixed(2));
await p.screenshot({path:`${out}/m_in.jpg`,type:'jpeg',quality:82});
// 책상 위 종이: 멀리서 눌러도 걸어가 크게 보기, 다음 장
await m('pose',8.5,-5.88,0,-22,58); await p.waitForTimeout(300);
let dp=null; for(const y of [420,460,380,500,340,540]){ for(const x of [640,600,680]){ await p.mouse.move(x,y); await p.waitForTimeout(25); if(await over()){ dp=[x,y]; break; } } if(dp)break; }
assert(dp,'desk hover'); await p.mouse.click(...dp); for(let i=0;i<16&&!(await p.locator('.zoom').isVisible());i++) await p.waitForTimeout(250);
assert(await p.locator('.zoom').isVisible(),'desk zoom'); const d1=await p.locator('.zoom .front').getAttribute('src'); console.log('책상 종이 OK',d1); await p.keyboard.press('Escape'); await p.waitForTimeout(200);
await p.screenshot({path:`${out}/m_desk.jpg`,type:'jpeg',quality:82});
// 다시 나오기
await m('pose',8.675,-4,90,0); await p.keyboard.down('w'); await p.waitForTimeout(2600); await p.keyboard.up('w'); w=await m('where'); assert(w.y>-3,'나오기 y='+w.y); console.log('객차로 복귀 OK y=',w.y.toFixed(2));
// 방에서 책상 앞까지 충돌
await m('pose',9.0,-5.8,0,0); await p.keyboard.down('w'); await p.waitForTimeout(1500); await p.keyboard.up('w'); w=await m('where'); assert(w.x<9.5,'책상 막힘 x='+w.x); console.log('책상 막힘 OK x=',w.x.toFixed(2));
console.log('ERR',errs.join('\n')||'none'); await b.close();
