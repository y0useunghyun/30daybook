// 키보드 앞뒤 이동 점검: 한글 입력 상태(W가 'ㅈ'으로 들어옴)와 화살표. node keys.check.mjs [주소]
import { chromium } from 'playwright-core'; import assert from 'node:assert';
const URL_ = process.argv[2] || 'http://127.0.0.1:8030/';
const b = await chromium.launch({ channel:'chrome', headless:true, args:['--use-angle=metal','--enable-gpu','--ignore-gpu-blocklist'] });
const p = await b.newPage({ viewport:{width:1280,height:800} });
await p.goto(URL_ + '#sim'); await p.waitForSelector('#sim.ready',{state:'attached',timeout:120000}); await p.waitForTimeout(1000);
const mod = new URL('sim/sim.js', URL_).href;
const pose = () => p.evaluate(m=>import(m).then(x=>x.pose(2.2,3,90,0)),mod);
const y = () => p.evaluate(m=>import(m).then(x=>x.where().y),mod);
const hold = async (key, code, ms=700) => { await p.evaluate(([key,code])=>dispatchEvent(new KeyboardEvent('keydown',{key,code,bubbles:true})),[key,code]); await p.waitForTimeout(ms); await p.evaluate(([key,code])=>dispatchEvent(new KeyboardEvent('keyup',{key,code,bubbles:true})),[key,code]); await p.waitForTimeout(80); };
for (const [name,fk,fc,bk,bc] of [['영문 W/S','w','KeyW','s','KeyS'],['한글 ㅈ/ㄴ','ㅈ','KeyW','ㄴ','KeyS'],['대문자 W/S','W','KeyW','S','KeyS'],['화살표','ArrowUp','ArrowUp','ArrowDown','ArrowDown']]) {
  await pose(); await p.waitForTimeout(80); const y0=await y();
  await hold(fk,fc); const y1=await y(); await hold(bk,bc); const y2=await y();
  console.log(name, 'y', y0.toFixed(2),'→',y1.toFixed(2),'→',y2.toFixed(2));
  assert(y1>y0+.3, name+' 앞으로'); assert(y2<y1-.3, name+' 뒤로');
}
console.log('OK'); await b.close();
