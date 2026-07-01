import { test } from 'node:test';
import assert from 'node:assert/strict';
import { scoreDirection, MOMENTUM_CAL, DEFAULT_RISK } from './scorer.js';

function bear(N=260){ const d={o:[],h:[],l:[],c:[],v:[]}; let p=100000;
  for(let i=0;i<N;i++){p*=0.997;d.c.push(p);d.o.push(p*1.001);d.h.push(p*1.01);d.l.push(p*0.99);d.v.push(1000+i);} return d; }
function bull(N=260){ const d={o:[],h:[],l:[],c:[],v:[]}; let p=40000;
  for(let i=0;i<N;i++){p*=1.003;d.c.push(p);d.o.push(p*0.999);d.h.push(p*1.01);d.l.push(p*0.99);d.v.push(1000+i);} return d; }
const wk=d=>({o:d.o.filter((_,i)=>i%7===0),h:d.h.filter((_,i)=>i%7===0),l:d.l.filter((_,i)=>i%7===0),c:d.c.filter((_,i)=>i%7===0),v:d.v.filter((_,i)=>i%7===0)});
const mk=d=>({daily:d,hourly:{o:d.o.slice(-48),h:d.h.slice(-48),l:d.l.slice(-48),c:d.c.slice(-48),v:d.v.slice(-48)},weekly:wk(d),price:d.c.at(-1),funding:0.03,oiChangePct:-2});
const ctx={coinChanges:{BTCUSDT:-3},meanChange:-1,stdChange:2};

test('scorer runs end-to-end and returns a valid score object', () => {
  const r = scoreDirection(mk(bear()),'short',DEFAULT_RISK,MOMENTUM_CAL,ctx,'BTCUSDT');
  assert.ok(typeof r.score==='number' && r.score>=0 && r.score<=110, 'score in range');
  assert.ok(['EXECUTE','WAIT','NO TRADE'].includes(r.signal), 'valid signal');
  assert.ok(typeof r.sl==='number' && typeof r.tp1==='number', 'levels present');
  assert.ok(r.scoreComponents.length===11, '11 weighted checks');
});

test('direction discrimination: short scores higher than long in a bear market', () => {
  const raw=mk(bear());
  const s=scoreDirection(raw,'short',DEFAULT_RISK,MOMENTUM_CAL,ctx,'BTCUSDT').score;
  const l=scoreDirection(raw,'long', DEFAULT_RISK,MOMENTUM_CAL,ctx,'BTCUSDT').score;
  assert.ok(s>l, `short(${s}) > long(${l}) in bear`);
});

test('macro is a hard gate: long in bear is blocked (NO TRADE)', () => {
  const r=scoreDirection(mk(bear()),'long',DEFAULT_RISK,MOMENTUM_CAL,ctx,'BTCUSDT');
  assert.equal(r.signal,'NO TRADE');
  assert.ok(r.blocked===true || r.score<70, 'blocked or low');
});

test('SL geometry correct: short SL above entry price', () => {
  const r=scoreDirection(mk(bear()),'short',DEFAULT_RISK,MOMENTUM_CAL,ctx,'BTCUSDT');
  assert.ok(r.sl > r.price, `short SL(${r.sl}) above price(${r.price})`);
});
