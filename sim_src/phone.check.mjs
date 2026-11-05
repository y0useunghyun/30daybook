// 폰(390px·터치·새 프로필) 전체 경로 + 가만히 있을 때 안 그리는지. node phone.check.mjs [주소] [스크린샷폴더]
import { chromium } from 'playwright-core'; import assert from 'node:assert';
const URL_ = process.argv[2] || 'http://127.0.0.1:8030/', out = process.argv[3] || '.';
const b = await chromium.launch({ channel:'chrome', headless:true, args:['--use-angle=metal','--enable-gpu','--ignore-gpu-blocklist'] });
const ctx = await b.newContext({ viewport:{width:390,height:844}, hasTouch:true, isMobile:true, deviceScaleFactor:2 }); const q = await ctx.newPage();
const errs=[]; let bytes=0; q.on('pageerror',e=>errs.push(e.message)); q.on('response',async r=>{ if(r.status()>=400&&!/favicon/.test(r.url()))errs.push(r.status()+' '+r.url()); });
await q.addInitScript(()=>{ const o=WebGL2RenderingContext.prototype.drawElements; window.__draws=0; WebGL2RenderingContext.prototype.drawElements=function(...a){window.__draws++;return o.apply(this,a)}; });
const t0=Date.now(); await q.goto(URL_+'#sim'); await q.waitForSelector('#sim.ready',{state:'attached',timeout:120000}); console.log('강의실 뜨기까지', ((Date.now()-t0)/1000).toFixed(1)+'s');
await q.waitForTimeout(2500);
const mod=new URL('sim/sim.js',URL_).href;
const w=()=>q.evaluate(m=>import(m).then(x=>x.where()),mod), pose=(...v)=>q.evaluate(([m,v])=>import(m).then(x=>x.pose(...v)),[mod,v]);
// 안내 문구: 폰은 터치용
assert(await q.locator('.sim-hint .for-touch').isVisible()); assert(!(await q.locator('.sim-hint .for-keys').isVisible())); console.log('안내 문구 터치용 OK');
// 대기 중 그리기 멈춤
await q.evaluate(()=>{window.__draws=0}); await q.waitForTimeout(2000); const idle=await q.evaluate(()=>window.__draws); console.log('가만히 2초 draw', idle); assert(idle===0,'idle draws '+idle);
// 종이: 앞에서 탭
await pose(6.75,4.6,0,-35,58); await q.waitForTimeout(400); let hit=false; for(const y of [422,380,460,340,500]){ await q.touchscreen.tap(195,y); await q.waitForTimeout(250); if(await q.locator('.zoom').isVisible()){hit=true;break;} await pose(6.75,4.6,0,-35,58); await q.waitForTimeout(60); }
assert(hit,'phone pile'); console.log('폰 종이 집기 OK', await q.locator('.zoom .front').getAttribute('src'));
await q.screenshot({path:`${out}/ph_zoom.jpg`,type:'jpeg',quality:70});
await q.touchscreen.tap(195,420); await q.waitForTimeout(700); assert(await q.locator('.zoom .sheet.flipped').count()===1,'flip'); await q.touchscreen.tap(195,30); await q.waitForTimeout(250); assert(!(await q.locator('.zoom').isVisible()),'close'); assert.equal(new URL(q.url()).hash,'#sim'); console.log('폰 뒷면·닫기 OK');
// 스위치
await pose(3.52,.95,-90,-14,58); await q.waitForTimeout(400); let s0=await w(), flipped=false; for(const y of [360,400,440,320,480,280,520]){ for(const x of [195,160,230,120,270]){ await q.touchscreen.tap(x,y); await q.waitForTimeout(150); const s=await w(); if(s.lights!==s0.lights){flipped=true;break;} await pose(3.52,.95,-90,-14,58); await q.waitForTimeout(60);} if(flipped)break; }
assert(flipped,'phone switch'); console.log('폰 스위치 OK', (await w()).lights); await q.screenshot({path:`${out}/ph_dark.jpg`,type:'jpeg',quality:70});
await q.evaluate(()=>document.querySelector('.sim-light').click());
// 문
await pose(8.675,1.25,-90,-2,58); await q.waitForTimeout(400); await q.touchscreen.tap(195,430); await q.waitForTimeout(1500); let c=await w(); assert(c.doors.find(d=>d[0]==='B')[1],'phone door '+JSON.stringify(c.doors)); console.log('폰 문 열기 OK');
await q.screenshot({path:`${out}/ph_door.jpg`,type:'jpeg',quality:70});
// 바닥 탭으로 객차 안으로
await pose(8.675,.5,-90,-35,58); await q.waitForTimeout(300); await q.touchscreen.tap(195,640); await q.waitForTimeout(2500); c=await w(); console.log('폰 탭으로 문 쪽 이동 y=',c.y.toFixed(2));
await pose(8.675,-.9,-90,-30,58); await q.waitForTimeout(300); const yb=(await w()).y; assert(yb<-.3);
// 연결 통로 종이
await pose(15.8,-1.675,90,0,62); await q.waitForTimeout(400); hit=false; for(const y of [300,360,240,420,480,540,600]){ await q.touchscreen.tap(195,y); await q.waitForTimeout(250); if(await q.locator('.zoom').isVisible()){hit=true;break;} }
assert(hit,'phone gangway'); console.log('폰 통로 종이 OK'); await q.touchscreen.tap(195,30); await q.waitForTimeout(200);
await pose(12,-1.675,0,-2,58); await q.waitForTimeout(400); await q.screenshot({path:`${out}/ph_car.jpg`,type:'jpeg',quality:70});
// 끌기 후 draw 멈춤
await q.evaluate(()=>{window.__draws=0}); await q.waitForTimeout(1800); console.log('객차에서 가만히 draw', await q.evaluate(()=>window.__draws));
console.log('ERR', errs.join('\n')||'none'); await b.close();
