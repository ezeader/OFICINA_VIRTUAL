import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {mergeCandidates} from '../lib/supplier-search.ts';
import {usefulColumns} from '../lib/native-table.ts';
import {GET as tile} from '../app/api/suppliers/tile/route.ts';

test('map tile endpoint rejects anonymous or invalid coordinates before network access',async()=>{
 assert.equal((await tile(new Request('https://office.test/api/suppliers/tile?z=11&x=699&y=1251'))).status,401);
 for(const query of ['z=19&x=0&y=0','z=11&x=2048&y=0','z=11&x=-1&y=0','z=11&x=1','z=11&x=http://localhost&y=0']){
  assert.equal((await tile(new Request('https://office.test/api/suppliers/tile?'+query,{headers:{'oai-authenticated-user-id':'test'}}))).status,400);
 }
});
test('supplier trust comes from a saved source identity, not name or public rating',()=>{
 const candidate={id:'osm-node-1',name:'Casa Materiales',address:'Calle 1, Pinamar',source:'https://www.openstreetmap.org/node/1',contact:''};
 const saved=[{id:'my-supplier',sourceId:'osm-node-1',name:'Alias guardado',zone:'Pinamar',trusted:true}];
 assert.equal(mergeCandidates([candidate,candidate],saved).length,1);assert.equal(mergeCandidates([candidate],saved)[0].trusted,true);
 assert.equal(mergeCandidates([{...candidate,id:'osm-node-2',address:'Otra sucursal'}],saved)[0].trusted,false);
});
test('simple table hides commercial metadata without losing source columns or empaque conversion',()=>{
 const table={columns:['Cantidad','Descripción del producto','Código','Empaque','Assembly Code','Keynote'],rows:[['2','Caño','A','40','code','key']]};
 assert.deepEqual(usefulColumns(table).map(c=>c.index),[0,1]);assert.equal(usefulColumns(table,true).length,6);assert.equal(table.rows[0][3],'40');
});
test('openings count physical identities once across rooms, with curtain walls separate',()=>{
 const a=JSON.parse(fs.readFileSync(new URL('../public/casa-angel/openings/manifest.json',import.meta.url)));
 assert.equal(new Set(a.items.map(i=>i.uid)).size,a.items.length);assert.equal(a.items.filter(i=>i.category==='Windows').length,25);assert.equal(a.items.filter(i=>i.category==='Doors').length,13);
 assert.equal(a.rooms.filter(r=>r.sheetId).length,30);assert.deepEqual(a.items.filter(i=>!i.rooms.length).map(i=>i.id).sort(),['2275029','2295997']);
 assert.equal(a.items.find(i=>i.id==='671785').fromRoom,869397);assert.ok(a.items.find(i=>i.id==='891414').rooms.includes(892788));assert.ok(a.items.find(i=>i.id==='874580').rooms.includes(892788));
 assert.equal(new Set(a.items.map(i=>i.documentation.sheetId)).size,49);
 for(const i of a.items){assert.equal(i.documentation.views.length,4);assert.ok(i.documentation.scheduleId);for(const path of [i.documentation.pdf,i.documentation.image,...i.documentation.views.map(v=>v.image)])assert.ok(fs.existsSync(new URL('../public'+path,import.meta.url)),path);}
 for(const r of a.rooms){assert.equal(new Set(r.items).size,r.items.length);for(const id of r.items)assert.ok(a.items.find(i=>i.id===id)?.rooms.includes(r.id));}
 const sheets=a.rooms.filter(r=>r.sheetId);for(const r of sheets){for(const path of [r.image,r.pdf,...r.views.map(v=>v.image)])assert.ok(fs.existsSync(new URL('../public'+path,import.meta.url)),path)}
});
