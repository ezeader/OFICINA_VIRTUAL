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
