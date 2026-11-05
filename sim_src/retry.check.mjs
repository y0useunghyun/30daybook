// 파일이 처음 한 번 실패해도 공간이 열리는지. node retry.check.mjs
import { chromium } from 'playwright-core'; import assert from 'node:assert';
const b=await chromium.launch({channel:'chrome',headless:true,args:['--use-angle=metal','--enable-gpu','--ignore-gpu-blocklist']});
const p=await b.newPage({viewport:{width:1000,height:700}}); const failed=new Set(); const errs=[]; p.on('pageerror',e=>errs.push(e.message));
await p.route(/sim\/.*(lightmap\.webp|env\.jpg|room\.glb|scene\.json|tex\/.*jpg)|pages\/small\/front0[1-5]/, r=>{ const u=r.request().url(); if(!failed.has(u)){failed.add(u);return r.abort('connectionreset');} return r.continue(); });
await p.goto('http://127.0.0.1:8030/#sim'); await p.waitForSelector('#sim.ready,#sim.failed',{state:'attached',timeout:60000});
assert.equal(await p.evaluate(()=>document.getElementById('sim').classList.contains('ready')),true);
await p.evaluate(()=>import('/sim/sim.js').then(m=>m.openAllDoors())); await p.waitForTimeout(3000);
const w=await p.evaluate(()=>import('/sim/sim.js').then(m=>m.where())); assert(w.doors.every(d=>d[1]),JSON.stringify(w.doors));
await p.evaluate(()=>import('/sim/sim.js').then(m=>m.pose(8.3,-5,-8,-6,70))); await p.waitForTimeout(800); await p.screenshot({path:process.argv[2]+'/retry.jpg',type:'jpeg',quality:70});
console.log('처음 실패시킨 파일',failed.size,'개, 그래도 세 공간 다 열림 OK', errs.join()||''); await b.close();
