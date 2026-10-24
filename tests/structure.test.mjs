import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {concreteTotals,groupCases,plainWarning} from '../lib/structure.ts';

const m=JSON.parse(fs.readFileSync(new URL('../public/casa-angel/structure/manifest.json',import.meta.url),'utf8'));

test('concrete walls add up to the Revit totals, level by level',()=>{
 const t=concreteTotals(m);
 assert.equal(t.wallsByLevel.reduce((n,l)=>n+l.count,0),m.concreteWalls.count);
 assert.ok(Math.abs(t.parts.walls-m.concreteWalls.totals.volume_m3)<0.01);
 assert.deepEqual(t.wallsByLevel.map(l=>l.level),[...t.wallsByLevel.map(l=>l.level)].sort((a,b)=>a.localeCompare(b,'es',{numeric:true})));
});
test('slabs only count their concrete layer and floor build-ups without concrete stay out',()=>{
 const t=concreteTotals(m),withConcrete=m.slabsAndFoundations.filter(s=>s.concreteVolume_m3>0);
 assert.ok(Math.abs(t.parts.losas+t.parts.platea-withConcrete.reduce((n,s)=>n+s.concreteVolume_m3,0))<1e-9);
 assert.equal(t.withoutConcrete.count,m.slabsAndFoundations.filter(s=>!s.concreteVolume_m3).length);
 assert.ok(Math.abs(t.total-(t.parts.walls+t.parts.losas+t.parts.platea))<1e-9);
});
test('review cases are grouped and Revit warnings read in plain Spanish',()=>{
 const g=groupCases(m.reviewCases);
 assert.equal(g.reduce((n,x)=>n+x.rows.length,0),m.reviewCases.length);
 assert.equal(plainWarning('Highlighted walls overlap. One of them may be ignored'),'Muros superpuestos');
 assert.equal(plainWarning('algo nuevo'),'algo nuevo');
});
import {groupStructureSheets} from '../lib/structure.ts';
test('structure sheets are grouped: plans first, then elevations by level, review last',()=>{
 const g=groupStructureSheets(m.sheets||[]);
 assert.equal(g.reduce((n,x)=>n+x.sheets.length,0),(m.sheets||[]).length);
 if(g.length){assert.equal(g[0].title,'Índice, plantas y fundación');assert.equal(g.at(-1).title,'Casos de revisión')}
});
test('element sheets are grouped by element type after the plans and elevations',()=>{
 const g=groupStructureSheets([{number:'EST-PB-01'},{number:'EST-EL-MH-PB-01',element:'MH-PB-01',kind:'element'},{number:'EST-EL-LO-PA-01',element:'LO-PA-01',kind:'element'},{number:'EST-REV-01'},{number:'EST-SEC-PB-01',level:'00. Planta Baja'}]);
 assert.deepEqual(g.map(x=>x.title),['Índice, plantas y fundación','Alzados de muros · 00. Planta Baja','Fichas de losas','Fichas de muros','Casos de revisión']);
});
import {structureBudget} from '../lib/structure.ts';
test('budget lines have stable unique ids and every concrete element counts once',()=>{
 const lines=structureBudget(m),ids=lines.map(l=>l.id);
 assert.equal(new Set(ids).size,ids.length);
 for(const id of ['platea','muros','losas','vigas','acero','encofrado-muros','encofrado-losas'])assert.ok(ids.includes(id),id);
 const concrete=lines.filter(l=>l.unit==='m³').reduce((n,l)=>n+l.quantity,0);
 const slabs=m.slabsAndFoundations.reduce((n,s)=>n+(s.concreteVolume_m3||0),0),beams=m.codes.filter(c=>c.kind==='VE').reduce((n,c)=>n+c.volume_m3,0);
 const grow=(m.checks?.loPb01VsPlatea?.loPb01OutsidePlatea_m2||0)*0.15;
 assert.ok(Math.abs(concrete-(m.concreteWalls.totals.volume_m3+slabs+beams+grow))<0.01,'cada elemento una vez, más la platea extendida bajo LO-PB-01');
 assert.ok(lines.find(l=>l.id==='losas-a-confirmar')?.informative);
 assert.ok(lines.find(l=>l.id==='base-acceso')?.informative,'la base de acceso se cotiza en Exteriores');
 assert.ok(lines.find(l=>l.id==='losa-pb')?.informative,'la PB va sobre la platea');
});
test('platea extension is not counted twice once Revit models it',()=>{
 const plate=m.slabsAndFoundations.find(s=>/platea/i.test(s.role)),extra={...plate,id:'nuevo',area_m2:124.125,concreteVolume_m3:124.125*0.15};
 const before=structureBudget(m).find(l=>l.id==='platea').quantity;
 const after=structureBudget({...m,slabsAndFoundations:[...m.slabsAndFoundations,extra]}).find(l=>l.id==='platea').quantity;
 assert.ok(Math.abs(before-after)<0.01);
});
