import test from 'node:test';
import assert from 'node:assert/strict';
import {computeBudget,linesFromManifest,manifestStatus,sanitaryLines,budgetSheet,pricesFromRows,globalId} from '../lib/rubro-budget.ts';

const pisos={key:'pisos',name:'Pisos',status:'modelado',lines:linesFromManifest('pisos',{totals:[{label:'Piso vinílico',value:100,unit:'m²'},{label:'Pisos (todos los tipos)',value:150,unit:'m²'},{label:'Piso madera',value:50,unit:'m²'}]})};
const solar={key:'solar',name:'Paneles solares',status:'estimacion',lines:linesFromManifest('solar',{totals:[{label:'Aguas candidatas',value:200,unit:'m²'}]})};
const gas={key:'gas',name:'Gas',status:'sin-computo',lines:[]};

test('summary totals are informative and never priced twice',()=>{
 assert.deepEqual(pisos.lines.map(l=>l.informative),[false,true,false]);
 const r=computeBudget([pisos],{prices:{'pisos:piso-vinilico':10,'pisos:pisos-todos-los-tipos':99,'pisos:piso-madera':20}});
 assert.equal(r.rubros[0].subtotal,100*10+50*20);
 assert.equal(r.rubros[0].complete,true);
});
test('without prices nothing is invented: subtotal 0 and missing lines listed',()=>{
 const r=computeBudget([pisos,solar,gas]);
 assert.equal(r.total,0);
 assert.equal(r.rubros[0].missing,2);
 assert.equal(r.baseComplete,false);
 assert.equal(r.rubros.find(x=>x.key==='gas').complete,false);
 assert.equal(r.progress.withCompute,2);
});
test('optional rubros are shown as a share of the base',()=>{
 const r=computeBudget([pisos,solar],{prices:{'pisos:piso-vinilico':10,'pisos:piso-madera':20,'solar:aguas-candidatas':1}});
 assert.equal(r.baseTotal,2000);
 assert.equal(r.optional[0].key,'solar');
 assert.equal(r.optional[0].share,0.1);
 assert.equal(r.total,2200);
});
test('a closed global quote replaces line items and the studio can move rubros between base and optional',()=>{
 const r=computeBudget([pisos,gas],{prices:{[globalId('gas')]:500},optional:{pisos:true}});
 assert.equal(r.rubros[1].complete,true);
 assert.equal(r.baseTotal,500);
 assert.equal(r.optional[0].key,'pisos');
});
test('explicit manifest budget lines win over totals, and status reflects sheets',()=>{
 assert.equal(linesFromManifest('x',{budget:{lines:[{id:'a',label:'A',value:2,unit:'u'}]},totals:[{label:'B',value:1,unit:'u'}]})[0].id,'x:a');
 assert.equal(manifestStatus({sheets:[1],totals:[1]}),'modelado');
 assert.equal(manifestStatus({totals:[1]}),'estimacion');
 assert.equal(manifestStatus(null),'sin-computo');
});
test('sanitary pipes are grouped by system, type and diameter',()=>{
 const l=sanitaryLines([{group:'AF',type:'PPF',diameter_mm:32,length_model_m:1.5},{group:'AF',type:'PPF',diameter_mm:32,length_model_m:2},{group:'CP',type:'PVC',diameter_mm:110,length_model_m:3}],{AF:'Agua fría'});
 assert.equal(l.length,2);
 assert.equal(l.find(x=>x.label.startsWith('Agua fría')).quantity,3.5);
});
test('the price sheet round-trips with comma decimals and rejects unknown ids',()=>{
 const sheet=budgetSheet(computeBudget([pisos])).map(r=>r.map(String));
 assert.equal(sheet[0][0],'id');
 const known=new Set(sheet.slice(1).map(r=>r[0]));
 sheet[2][6]='1.234,50';
 assert.deepEqual(pricesFromRows(sheet,known),{'pisos:piso-vinilico':1234.5});
 assert.deepEqual(pricesFromRows([['id','precio_unitario'],['pisos:piso-madera','12.5']],known),{'pisos:piso-madera':12.5});
 assert.throws(()=>pricesFromRows([['id','precio_unitario'],['otro:x','1']],known),/desconocida/);
});
test('a published proposal is flagged as such, not as modeled',()=>{
 assert.equal(manifestStatus({status:'propuesta',sheets:[1],totals:[1]}),'propuesta');
});
