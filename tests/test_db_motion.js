const assert=require('node:assert/strict'),fs=require('node:fs');
const M=new Function('matchMedia',fs.readFileSync('web/db-motion.js','utf8')+';return DBMotion;')(()=>({matches:false}));
assert.equal(M.monthInfo(2026,10).len,30);assert.equal(M.monthInfo(2026,11).rows,5);assert.equal(M.monthInfo(2028,1).len,29);assert.equal(M.dateStr(M.dateNum('2026-12-31')+1),'2027-01-01');
for(const [k,c] of [[300,24],[520,13],[260,22],[420,41],[260,24],[420,32]]){const s=M.S(0,k,c);s.t=1;for(let i=0;i<480;i++)M.step(s,1/240);assert.ok(Math.abs(s.x-1)<.001);}
console.log('Date math and original spring convergence passed');
