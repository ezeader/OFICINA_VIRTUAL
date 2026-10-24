import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {surveySpecs,scheduleSpecs,sizeOf,budgetTotals,budgetCsv} from '../lib/openings-budget.ts';

const manifest=JSON.parse(fs.readFileSync(new URL('../public/casa-angel/openings/manifest.json',import.meta.url),'utf8'));
const byCode=c=>manifest.items.find(i=>i.code===c);
const noSurvey=c=>{const i=structuredClone(byCode(c));delete i.survey;return i};
const spec=(c,label)=>surveySpecs(noSurvey(c)).find(s=>s.label===label)?.value;

test('survey data comes from Revit parameters and missing values stay empty',()=>{
 assert.equal(spec('V-77','Sistema / modelo'),'Aluval ALUPROM 44');
 assert.match(spec('V-77','Vidrio'),/templado/);
 assert.equal(spec('V-155','Apertura'),'Paño fijo');
 assert.equal(spec('V-155','Vidrio'),undefined);
 assert.equal(spec('P-59','Vano'),'0.91 m × 2.35 m');
 assert.equal(spec('MC-612302','Montantes'),'Rectangular Mullion : 50 x 150mm');
 assert.ok(!surveySpecs(noSurvey('MC-612302')).some(s=>/undefined/.test(s.value||'')));
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
test('the Revit survey sheet takes priority when present',()=>{
 const i=structuredClone(byCode('V-77'));i.survey={openingType:'Ventana practicable 2 hojas',glazing:{material:'Vidrio templado',spec:'<None>',area_m2:1.572},frame:{material:'Aluminio',width_m:'0.09 m'},thermal:{U:'1.8 W'}};
 const s=Object.fromEntries(surveySpecs(i).map(x=>[x.label,x.value]));
 assert.equal(s['Apertura'],'Ventana practicable 2 hojas');assert.equal(s['Vidrio'],'Vidrio templado · ≈ 1,57 m²');assert.equal(s['Marco / perfiles'],'Aluminio · ancho 0.09 m');
 const wall=structuredClone(byCode('MC-612302'));wall.survey={glazing:{panes:5,area_m2:23.215},frame:{profiles:[{type:'50 x 150mm',material:'Aluminium',count:16,length_m:33.997}]}};
 assert.match(Object.fromEntries(surveySpecs(wall).map(x=>[x.label,x.value]))['Marco / perfiles'],/16 u. · 34.00 m/);
 const t=budgetTotals([i,wall]);assert.ok(Math.abs(t.glass-24.787)<1e-9);assert.ok(Math.abs(t.profiles-33.997)<1e-9);
});
test('the carpentry schedule line keeps real data and drops generic Revit materials',()=>{
 const line=c=>scheduleSpecs(byCode(c)).map(x=>x.value).join(' · ');
 assert.equal(line('V-15'),'Paño fijo');
 assert.equal(line('V-77'),'Ventana practicable 2 hojas · Vidrio claro templado · Aluminio, Poliamida');
 assert.equal(line('P-60'),'Puerta corrediza embutida · Madera (roble)');
 for(const i of manifest.items)assert.doesNotMatch(scheduleSpecs(i).map(x=>x.value).join(' '),/\b(Glass|Sash|Default|Wood|Chipboard|By Category)\b|gen[eé]rico/,i.code);
});
