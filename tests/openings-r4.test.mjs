import test from 'node:test';
import assert from 'node:assert/strict';
import {dimensionText,viewDimensions,r4GroupDocument,r4ElementViews} from '../lib/openings-r4.ts';

const items=[
 {id:'1',code:'V-1',documentation:{r4:{views:[{viewId:'20',roomKey:'A',roomName:'Cocina'},{viewId:'30',roomKey:'B',roomName:'Living'}],dimensions:[{label:'Ancho',values_m:[0.6],view:'elevation',roomKey:'A'},{label:'Antepecho + alto',values_m:[0.9,1.2],view:'elevation',roomKey:'A'},{label:'Ancho en planta',values_m:[0.6],view:'plan',roomKey:'A'},{label:'Ancho',values_m:[0.6],view:'elevation',roomKey:'B'}]}}},
 {id:'2',code:'P-2',documentation:{r4:{views:[{viewId:'21',roomKey:'A'}],dimensions:[{label:'Ancho en planta',values_m:[0.9],view:'plan',roomKey:'A'}]}}},
];
const groups=[
 {key:'A',name:'Cocina',sheets:[{sheetId:'100',sheetNumber:'ABR-R4-PB-01',pdf:'/a.pdf',image:'/a-p1.svg.gz',views:[{id:10,name:'Planta',scale:20,kind:'plan',image:'/v10'},{id:20,name:'V-1 · alzado interior',scale:20,kind:'elevation',elementId:'1',code:'V-1',image:'/v20'}]},{sheetId:'101',sheetNumber:'ABR-R4-PB-01-2',image:'/a-p2.svg.gz',views:[{id:21,name:'P-2 · alzado interior',scale:25,kind:'elevation',elementId:'2',code:'P-2',image:'/v21'}]}]},
 {key:'B',name:'Living',sheets:[{sheetId:'200',sheetNumber:'ABR-R4-PB-02',image:'/b.svg.gz',views:[{id:30,name:'V-1 · alzado interior',scale:20,kind:'elevation',elementId:'1',code:'V-1',image:'/v30'}]}]},
];

test('dimension chains show each segment and the total',()=>{
 assert.equal(dimensionText([0.9,1.2]),'0,900 + 1,200 = 2,100 m');
 assert.equal(dimensionText([0.6]),'0,600 m');
});
test('an elevation carries only its element dimensions in that room; a plan carries all plan widths',()=>{
 assert.deepEqual(viewDimensions(groups[0].sheets[0].views[1],'A',items).map(d=>d.label),['Ancho','Antepecho + alto']);
 assert.deepEqual(viewDimensions(groups[0].sheets[0].views[0],'A',items).map(d=>[d.code,d.values_m[0]]),[['V-1',0.6],['P-2',0.9]]);
 assert.deepEqual(viewDimensions(groups[1].sheets[0].views[0],'B',items).map(d=>d.label),['Ancho']);
});
test('a multi-page room becomes one document with every view and page',()=>{
 const doc=r4GroupDocument(groups[0],items);
 assert.equal(doc.image,'/a-p1.svg.gz');assert.equal(doc.views.length,3);assert.deepEqual(doc.sheets.map(s=>s.name),['ABR-R4-PB-01','ABR-R4-PB-01-2']);
 assert.equal(doc.views[2].code,'P-2');assert.equal(doc.views[2].sheetNumber,'ABR-R4-PB-01-2');
 assert.equal(r4GroupDocument({key:'X',sheets:[]},items),undefined);
});
test('a shared element gets one elevation per room',()=>{
 const views=r4ElementViews(items[0],groups,items);
 assert.deepEqual(views.map(v=>[v.id,v.roomName,v.dimensions.length]),[[20,'Cocina',2],[30,'Living',1]]);
 assert.deepEqual(r4ElementViews({id:'9',code:'X'},groups,items),[]);
});
