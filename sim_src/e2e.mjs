// 실제 마우스·터치로 처음 방문 경로 점검
import { chromium } from 'playwright-core';
import assert from 'node:assert';
const out = process.argv[2];
const b = await chromium.launch({ channel:'chrome', headless:true, args:['--use-angle=metal','--enable-gpu','--ignore-gpu-blocklist'] });
const ctx = await b.newContext({ viewport:{width:1280,height:800} }); const p = await ctx.newPage();
const errs=[]; p.on('pageerror',e=>errs.push('PAGEERR '+e.message)); p.on('console',m=>{if(m.type()==='error'&&!/404/.test(m.text()))errs.push(m.text().slice(0,200))}); p.on('response',r=>{if(r.status()>=400&&!/favicon/.test(r.url()))errs.push(r.status()+' '+r.url())});
const w = () => p.evaluate(()=>import('/sim/sim.js').then(m=>m.where()));
const project = (x,y,z) => p.evaluate(([x,y,z])=>{ return null },[x,y,z]);
await p.goto('http://127.0.0.1:8030/'); await p.waitForTimeout(600);
// 1) 홈에서 동그라미 클릭
await p.locator('a.mark[href="#sim"]').click();
await p.waitForSelector('#sim.ready',{timeout:60000,state:'attached'}); await p.waitForTimeout(1500);
console.log('1 동그라미→시뮬 OK', p.url());
// 2) 바닥 클릭 = 걷기
let a = await w(); await p.mouse.click(640,640); await p.waitForTimeout(1600); let c = await w();
assert(Math.hypot(c.x-a.x,c.y-a.y)>.3,'floor click walks'); console.log('2 바닥 클릭 걷기 OK', a.x.toFixed(2),a.y.toFixed(2),'→',c.x.toFixed(2),c.y.toFixed(2));
// 3) 끌기 = 둘러보기 (걷지 않음)
a = await w(); await p.mouse.move(640,400); await p.mouse.down(); await p.mouse.move(800,420,{steps:6}); await p.mouse.up(); await p.waitForTimeout(150); c = await w();
assert(Math.abs(c.yaw-a.yaw)>.2,'drag looks'); console.log('3 끌기 둘러보기 OK');
// 4) 종이 더미 앞에 서서 눌러 크게 보기 → 뒷면 → 닫기 → 다음 장
await p.evaluate(()=>import('/sim/sim.js').then(m=>m.pose(6.75,6.42,0,-32,58))); await p.waitForTimeout(400);
await p.screenshot({path:`${out}/e_pile.jpg`,type:'jpeg',quality:80});
const clickPile = async () => { for (const [x,y] of [[640,470],[640,430],[640,510],[600,470],[680,470]]) { await p.mouse.click(x,y); await p.waitForTimeout(350); if (await p.locator('.zoom').isVisible()) return true; } return false; };
assert(await clickPile(),'pile opens zoom');
const f1 = await p.locator('.zoom .front').getAttribute('src'); console.log('4 종이 집기 OK', f1);
await p.locator('.zoom .sheet').click({position:{x:50,y:50}}); await p.waitForTimeout(700);
assert(await p.locator('.zoom .sheet.flipped').count()===1,'flip'); await p.screenshot({path:`${out}/e_zoom.jpg`,type:'jpeg',quality:70});
await p.keyboard.press('Escape'); await p.waitForTimeout(200);
assert(!(await p.locator('.zoom').isVisible()),'esc closes zoom'); assert.equal(new URL(p.url()).hash,'#sim','stay in sim');
assert(await clickPile(),'second'); const f2 = await p.locator('.zoom .front').getAttribute('src'); assert.notEqual(f1,f2); console.log('  다음 장 OK', f2);
await p.mouse.click(20,700); await p.waitForTimeout(200); assert(!(await p.locator('.zoom').isVisible()),'outside closes zoom'); assert.equal(new URL(p.url()).hash,'#sim');
// 5) 문: 교실 안 다른 곳에서 문 클릭 → 걸어가서 열림 → 통과
await p.evaluate(()=>import('/sim/sim.js').then(m=>m.pose(8.675,1.25,-90,-2,58))); await p.waitForTimeout(400);
await p.mouse.click(640,380); await p.waitForTimeout(1800); c = await w();
assert(c.doors.some(d=>d[0]==='B'&&d[1]),'door B opens '+JSON.stringify(c)); console.log('5 문 열림 OK', JSON.stringify(c.doors)); await p.screenshot({path:`${out}/e_door.jpg`,type:'jpeg',quality:80});
// 키보드로 통과
await p.keyboard.down('w'); await p.waitForTimeout(2500); await p.keyboard.up('w'); c = await w();
assert(c.y < -.5,'walked into car y='+c.y); console.log('6 W로 객차 진입 OK y=',c.y.toFixed(2)); await p.screenshot({path:`${out}/e_in.jpg`,type:'jpeg',quality:80});
// 맞은편 좌석에 막힘
await p.keyboard.down('w'); await p.waitForTimeout(2500); await p.keyboard.up('w'); c = await w();
assert(c.y > -3.05 && c.y < -1,'blocked by seat y='+c.y); console.log('7 맞은편에 막힘 OK y=',c.y.toFixed(2));
// 연결 통로: 들어가서 벽 종이 누르기
await p.evaluate(()=>import('/sim/sim.js').then(m=>m.pose(15.8,-1.675,90,0,62))); await p.waitForTimeout(400);
await p.mouse.move(670,180); await p.waitForTimeout(100);
await p.mouse.click(670,180); await p.waitForTimeout(500);
assert(await p.locator('.zoom').isVisible(),'gangway paper opens'); console.log('  통로 종이 OK', await p.locator('.zoom .front').getAttribute('src'));
await p.keyboard.press('Escape'); await p.waitForTimeout(150);
await p.evaluate(()=>import('/sim/sim.js').then(m=>m.pose(14.8,-1.675,0,0))); await p.keyboard.down('w'); await p.waitForTimeout(2500); await p.keyboard.up('w'); c=await w();
assert(c.x>15.4 && c.x<16.3,'walk into gangway x='+c.x); console.log('  통로 걸어 들어가 끝에서 막힘 OK x=',c.x.toFixed(2));
await p.evaluate(()=>import('/sim/sim.js').then(m=>m.pose(8.675,-1.5,-90,0)));await p.waitForTimeout(100);
await p.evaluate(()=>import('/sim/sim.js').then(m=>m.pose(8.675,-1.2,-90,0)));
// 돌아서 교실로
await p.keyboard.down('s'); await p.waitForTimeout(3600); await p.keyboard.up('s'); c = await w();
assert(c.y > 0,'back in room y='+c.y); console.log('8 교실로 복귀 OK y=',c.y.toFixed(2));
// 9) 닫힌 다른 문은 벽처럼 막힘
await p.evaluate(()=>import('/sim/sim.js').then(m=>m.pose(4.275,.6,-90,0))); await p.keyboard.down('w'); await p.waitForTimeout(1200); await p.keyboard.up('w'); c = await w();
assert(c.y >= .1,'closed door blocks y='+c.y); console.log('9 닫힌 문 막힘 OK y=',c.y.toFixed(2));
// 10) Esc로 나가면 홈, 다시 들어가도 동작
await p.keyboard.press('Escape'); await p.waitForTimeout(300); assert.equal(new URL(p.url()).hash,''); await p.mouse.move(300,300); await p.waitForTimeout(200);
await p.locator('a.mark[href="#sim"]').click(); await p.waitForTimeout(800); c=await w(); assert(c); console.log('10 나갔다 다시 들어오기 OK');
// 11) 다른 메뉴 그대로
for (const h of ['#result','#mess','#count','#info','#book']) { await p.evaluate(h=>{location.hash=h},h); await p.waitForTimeout(250); assert(await p.locator(h).isVisible(),h); }
console.log('11 기존 화면 OK');
await ctx.close();
// 12) 폰: 새 프로필 390px 터치
const m = await b.newContext({ viewport:{width:390,height:844}, hasTouch:true, isMobile:true, deviceScaleFactor:2 }); const q = await m.newPage();
q.on('pageerror',e=>errs.push('MOBILE '+e.message));
await q.goto('http://127.0.0.1:8030/#sim'); await q.waitForSelector('#sim.ready',{timeout:60000,state:'attached'}); await q.waitForTimeout(1500);
const wm=()=>q.evaluate(()=>import('/sim/sim.js').then(m=>m.where())); a=await wm(); await q.touchscreen.tap(195,650); await q.waitForTimeout(1500); c=await wm();
assert(Math.hypot(c.x-a.x,c.y-a.y)>.2,'tap walk mobile'); console.log('12 폰 탭 걷기 OK');
await q.screenshot({path:`${out}/e_phone.jpg`,type:'jpeg',quality:75});
await q.evaluate(()=>import('/sim/sim.js').then(m=>m.openAllDoors().then(()=>m.pose(6.5,-1.675,180,-3)))); await q.waitForTimeout(1200); await q.screenshot({path:`${out}/e_phone_car.jpg`,type:'jpeg',quality:75});
await m.close();
console.log('ERR', errs.join('\n')||'none');
await b.close();
