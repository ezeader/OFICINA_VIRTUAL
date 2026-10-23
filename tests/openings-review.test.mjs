import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {emptyReview,normalizeReview,setCorrection,correctionFor,warningKey,measureKey,parseLength,fabricationMeasures,missingMeasures,itemProgress,reviewTotals,pendingForRevit,sheetTotals} from '../lib/openings-review.ts';

const manifest=JSON.parse(fs.readFileSync(new URL('../public/casa-angel/openings/manifest.json',import.meta.url),'utf8'));
const byCode=code=>manifest.items.find(i=>i.code===code);
const now='2026-10-23T12:00:00.000Z';

test('a correction is stored apart from the Revit value and marked as pending in Revit',()=>{
 const item=byCode('V-155'),key=warningKey(item.warnings[0]);
 const review=setCorrection(emptyReview(),item.id,key,{value:'45 mm',note:'Perfil según proveedor'},now);
 assert.deepEqual(correctionFor(review,item.id,key),{status:'proposed',updatedAt:now,value:'45 mm',note:'Perfil según proveedor'});
 assert.equal(item.width,'0.600 m');
 assert.equal(itemProgress(item,review).proposed,1);
 assert.equal(itemProgress(item,review).open,item.warnings.length-1);
});
test('updates merge with the previous entry and clearing everything removes it',()=>{
 let review=setCorrection(undefined,'1','w:x',{value:'1'},now);
 review=setCorrection(review,'1','w:x',{status:'applied'},now);
 assert.equal(correctionFor(review,'1','w:x').value,'1');
 assert.equal(correctionFor(review,'1','w:x').status,'applied');
 review=setCorrection(review,'1','w:x',{value:'',note:'',status:'open'},now);
 assert.deepEqual(review,{version:1,items:{}});
});
test('the original review object is never mutated',()=>{
 const before=setCorrection(undefined,'1','w:x',{value:'1'},now),copy=structuredClone(before);
 setCorrection(before,'1','w:x',{value:'2'},now);setCorrection(before,'2','w:y',{note:'n'},now);
 assert.deepEqual(before,copy);
});
test('workspace data from other versions is sanitised',()=>{
 assert.deepEqual(normalizeReview(null),emptyReview());
 assert.deepEqual(normalizeReview({items:{a:{k:{status:'hacked',value:'x'},ok:{status:'dismissed',value:3,note:'n'}},b:'nope'}}),{version:1,items:{a:{ok:{status:'dismissed',updatedAt:'',note:'n'}}}});
 assert.equal(normalizeReview({items:{a:{k:{status:'proposed',value:'x'.repeat(900)}}}}).items.a.k.value.length,200);
});
test('hand-written lengths are read with explicit or inferred units',()=>{
 assert.equal(parseLength('0,60'),0.6);assert.equal(parseLength('600'),0.6);assert.equal(parseLength('60 cm'),0.6);assert.equal(parseLength('45mm'),0.045);assert.equal(parseLength('2.4 m'),2.4);
 for(const bad of ['','abc','1/2','-3','2 m 40'])assert.equal(parseLength(bad),null);
});
test('warning keys are stable and readable',()=>{
 assert.equal(warningKey('Espesor de hoja/perfil sin parámetro utilizable.'),'w:espesor-de-hoja-perfil-sin-parametro-utilizable');
 assert.equal(measureKey('sill'),'m:sill');
});
test('fabrication measures only report values read from Revit',()=>{
 const r2=structuredClone(byCode('V-15'));delete r2.dimensions; // solo cotas R2, con o sin lectura R4 en el manifest
 const window=Object.fromEntries(fabricationMeasures(r2).map(m=>[m.key,m]));
 assert.equal(window.width.value,'0.500 m');assert.equal(window.sill.value,'1.000 m');assert.equal(window.head.value,'3.850 m');
 assert.equal(window.width.dimensioned,true);assert.equal(window.sill.dimensioned,false);
 assert.deepEqual(missingMeasures(byCode('V-15')).map(m=>m.key),['roughWidth','roughHeight','thickness']);
 assert.deepEqual(missingMeasures(byCode('P-59')).map(m=>m.key),[]);
 const wall=Object.fromEntries(fabricationMeasures(byCode('MC-612302')).map(m=>[m.key,m]));
 assert.equal(wall.length.value,'9.00 m');assert.equal(wall.wallHeight.value,'2.80 m');assert.match(wall.wallHeight.note,/enlazada/);
 assert.deepEqual(missingMeasures(byCode('MC-612302')).map(m=>m.key),['breakdown']);
});
test('totals and the Revit hand-off list follow the stored statuses',()=>{
 const a=byCode('V-155'),b=byCode('P-1');
 let review=setCorrection(undefined,a.id,warningKey(a.warnings[0]),{value:'45 mm'},now);
 review=setCorrection(review,b.id,warningKey(b.warnings[0]),{status:'dismissed'},now);
 review=setCorrection(review,a.id,measureKey('roughWidth'),{value:'0,62'},now);
 const totals=reviewTotals(manifest.items,review);
 assert.equal(totals.proposed,1);assert.equal(totals.dismissed,1);assert.equal(totals.measures,1);
 assert.equal(totals.warnings,manifest.items.reduce((n,i)=>n+i.warnings.length,0));
 const rows=pendingForRevit(manifest.items,review);
 assert.deepEqual(rows.map(r=>[r.code,r.subject,r.original,r.value]),[['V-155',a.warnings[0],'Advertencia de la lectura','45 mm'],['V-155','Ancho de vano','Sin dato en Revit','0,62']]);
});
test('sheet totals separate room, element and review-context sheets',()=>{
 const t=sheetTotals(manifest);
 assert.equal(t.room,manifest.rooms.length);assert.equal(t.element,manifest.items.length);assert.equal(t.context,manifest.reviewCases.length);
 assert.equal(t.total,t.room+t.element+t.context);
 assert.equal(t.windows+t.doors+t.curtainWalls,t.elements);
});
test('R4 dimension chains mark sill and head as dimensioned',()=>{
 const base=structuredClone(byCode('V-15'));delete base.dimensions;
 assert.equal(Object.fromEntries(fabricationMeasures(base).map(m=>[m.key,m.dimensioned])).sill,false);
 base.dimensions=[{label:'Antepecho + alto',values_m:[1,2.85]},{label:'Altura de dintel',values_m:[3.85]}];
 const m=Object.fromEntries(fabricationMeasures(base).map(x=>[x.key,x.dimensioned]));
 assert.equal(m.sill,true);assert.equal(m.head,true);assert.equal(m.height,true);assert.equal(m.roughWidth,false);
});
