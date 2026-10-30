import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {compareQuote,followUp,latestQuotes,linesFromRows,priceHistory,requestMail} from '../lib/quotes.ts';

const sheet={rubro:'sanitaria',name:'Instalación sanitaria',project:'Casa Ángel',location:'Pinamar Norte, provincia de Buenos Aires',revision:'R13',date:'',basis:'',count:3,excluded:[],locales:{},
 documents:[{name:'Planos',url:'/p.pdf'}],
 systems:[{key:'AF',name:'Agua fría',items:[{code:'AF.01',description:'Caño',unit:'m',quantity:10},{code:'AF.02',description:'Codo',unit:'u',quantity:4}]},{key:'EQ',name:'Artefactos y equipos',items:[{code:'EQ.01',description:'Inodoro',unit:'u',quantity:2,materialOptional:true}]}]};
const q=(o)=>({id:'q',supplier:'s1',date:'2026-11-01',reference:'A',currency:'ARS',taxesIncluded:true,scope:'materiales + mano de obra',validUntil:'2026-12-01',delivery:'',zone:'',zoneViable:'sí',freight:0,lines:{},...o});

test('el cómputo publicado no repite códigos ni descripciones dentro de un sistema',()=>{
 const s=JSON.parse(readFileSync('data/cotizacion/sanitaria-R13.json','utf8'));
 const codes=s.systems.flatMap(x=>x.items.map(i=>i.code));
 assert.equal(new Set(codes).size,codes.length);
 for(const x of s.systems)assert.equal(new Set(x.items.map(i=>i.description)).size,x.items.length,x.key);
 assert.equal(codes.length,s.count);
});
test('materiales + MO: falta un ítem sin precio; material opcional no se exige',()=>{
 const r=compareQuote(sheet,q({lines:{'AF.01':{material:100,labor:50},'AF.02':{material:10},'EQ.01':{labor:1000}}}));
 assert.equal(r.status['AF.01'],'completo');assert.equal(r.status['AF.02'],'parcial');assert.equal(r.status['EQ.01'],'completo');
 assert.equal(r.material,10*100+4*10);assert.equal(r.labor,10*50+2*1000);assert.equal(r.complete,false);
});
test('solo materiales no exige mano de obra; MO global cubre todos los ítems',()=>{
 const m=compareQuote(sheet,q({scope:'materiales',lines:{'AF.01':{material:1},'AF.02':{material:1}}}));
 assert.equal(m.complete,true);assert.equal(m.covered,3);
 const g=compareQuote(sheet,q({laborGlobal:500,lines:{'AF.01':{material:1},'AF.02':{material:1}}}));
 assert.equal(g.complete,true);assert.equal(g.labor,500);
});
test('última respuesta por proveedor y evolución del número',()=>{
 const data={suppliers:[],quotes:[q({id:'a',lines:{'AF.01':{material:100}}}),q({id:'b',date:'2026-11-05',lines:{'AF.01':{material:90}}})],negotiation:[{id:'n',supplier:'s1',date:'2026-11-07',from:'proveedor',kind:'contraoferta',text:'baja',amount:800}]};
 assert.deepEqual(latestQuotes(data.quotes).map(x=>x.id),['b']);
 assert.deepEqual(priceHistory(sheet,data,'s1').map(h=>[h.amount,h.delta]),[[1000,0],[900,-100],[800,-100]]);
});
test('seguimiento: aviso de buscar más con pedidos sin respuesta a los 5 días',()=>{
 const data={suppliers:[{id:'s1',apto:'apto',requestedAt:'2026-11-01T00:00:00Z'},{id:'s2',apto:'apto',requestedAt:'2026-11-05T00:00:00Z'}],quotes:[],negotiation:[]};
 const f=followUp(data,new Date('2026-11-07T00:00:00Z'));
 assert.equal(f.late.length,1);assert.equal(f.searchMore,true);
});
test('lee la planilla devuelta por código e ignora la nota de fábrica',()=>{
 const {lines,errors}=linesFromRows(sheet,[{A:'AF.01',E:'1.234,50',G:'200'},{A:'EQ.01',G:'5000',K:'Material opcional: cotizar solo si lo provee.'},{A:'XX',E:'1'},{A:'AF.02',E:'abc'}]);
 assert.deepEqual(lines,{'AF.01':{material:1234.5,labor:200},'EQ.01':{labor:5000}});
 assert.equal(errors.length,1);
});
test('el mail pide materiales y MO por separado, validez, plazos y zona',()=>{
 const m=requestMail(sheet,{name:'X',kind:'materiales + mano de obra'},'06/11/2026');
 for(const w of ['mano de obra','Validez','Plazo de entrega','Zona','06/11/2026','Estudio Ader'])assert.ok(m.body.includes(w),w);
 assert.match(m.subject,/Casa Ángel/);
});
