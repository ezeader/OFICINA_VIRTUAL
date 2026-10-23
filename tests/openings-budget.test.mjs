import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {surveySpecs,sizeOf,budgetTotals,budgetCsv} from '../lib/openings-budget.ts';

const manifest=JSON.parse(fs.readFileSync(new URL('../public/casa-angel/openings/manifest.json',import.meta.url),'utf8'));
const byCode=c=>manifest.items.find(i=>i.code===c);
const spec=(c,label)=>surveySpecs(byCode(c)).find(s=>s.label===label)?.value;

test('survey data comes from Revit parameters and missing values stay empty',()=>{
 assert.equal(spec('V-77','Sistema / modelo'),'Aluval ALUPROM 44');
 assert.match(spec('V-77','Vidrio'),/templado/);
 assert.equal(spec('V-155','Apertura'),'Paño fijo');
 assert.equal(spec('V-155','Vidrio'),undefined);
 assert.equal(spec('P-59','Vano'),'0.91 m × 2.35 m');
 assert.equal(spec('MC-612302','Montantes'),'Rectangular Mullion : 50 x 150mm');
 assert.ok(!surveySpecs(byCode('MC-612302')).some(s=>/undefined/.test(s.value||'')));
});
test('area and frame length use width × height, or length × height for curtain walls',()=>{
 assert.deepEqual(sizeOf(byCode('V-77')),{w:2,h:1,area:2,perimeter:6});
 const wall=sizeOf(byCode('MC-612302'));assert.equal(wall.w,9);assert.equal(wall.h,2.8);
 assert.equal(sizeOf({id:'x',code:'X',category:'Windows',type:'t',parameters:[]}),null);
});
test('the budget groups identical openings and the totals add up',()=>{
 const t=budgetTotals(manifest.items);
 assert.equal(t.total.count+t.missing.length,manifest.items.length);
 assert.equal(t.windows.count+t.doors.count+t.curtainWalls.count,t.total.count);
 assert.ok(Math.abs(t.rows.reduce((n,r)=>n+r.area,0)-t.total.area)<1e-9);
 const cuartos=t.rows.find(r=>r.type==='Ventana Cuartos (Muro a techo)');
 assert.equal(cuartos.count,cuartos.codes.length);assert.ok(Math.abs(cuartos.area-cuartos.count*0.6*2.4)<1e-9);
 const csv=budgetCsv(t.rows).split('\n');assert.equal(csv.length,t.rows.length+1);assert.match(csv[0],/m² total/);
});
