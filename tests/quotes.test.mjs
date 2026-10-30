import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {compareQuote,contactLinks,followUp,latestQuotes,linesFromRows,matchSupplier,priceHistory,quoteFromSheet,requestMail} from '../lib/quotes.ts';
import {quoteWorkbook} from '../lib/quote-xlsx.ts';

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
test('la planilla devuelta se carga sola: alcance, validez, moneda, IVA, plazos y zona',()=>{
 const rows=[{A:'AF.01',E:'100',G:'50'},{A:'AF.02',E:'10'}];
 const cond={'Empresa / responsable':'Banchero','Moneda (ARS o USD)':'ARS','¿Los precios incluyen IVA?':'No','¿Cotiza materiales, mano de obra o ambos?':'Ambos','Validez de la oferta (días)':'15 días','Plazo de entrega de materiales en obra':'10 días','Zona de trabajo (localidades que atiende)':'Pinamar','Flete a Pinamar Norte (incluido o importe)':'incluido'};
 const {quote,company}=quoteFromSheet(sheet,rows,cond,'Banchero-sanitaria.xlsx','materiales',new Date('2026-11-01T12:00:00Z'));
 assert.equal(company,'Banchero');assert.equal(quote.file,'Banchero-sanitaria.xlsx');assert.equal(quote.scope,'materiales + mano de obra');
 assert.equal(quote.validUntil,'2026-11-16');assert.equal(quote.taxesIncluded,false);assert.equal(quote.zone,'Pinamar');assert.equal(quote.freight,0);assert.match(quote.notes,/Flete: incluido/);
 const solo=quoteFromSheet(sheet,[{A:'AF.01',G:'5'}],{},'x.xlsx').quote;assert.equal(solo.scope,'mano de obra');
});
test('reconoce al proveedor por lo que escribió o por el nombre del archivo',()=>{
 const sup=[{id:'b',name:'Banchero Sanitarios'},{id:'m',name:'Martínez Gas-Plomería'},{id:'s',name:'Sanimat'}];
 assert.equal(matchSupplier(sup,'BANCHERO S.A.')?.id,'b');assert.equal(matchSupplier(sup,'','presupuesto martinez.xlsx')?.id,'m');assert.equal(matchSupplier(sup,'Sanitarios del Sur'),undefined);
});
test('links de pedido: Gmail con el borrador, WhatsApp con el texto',()=>{
 const a=contactLinks('ventas@banchero.com.ar · WhatsApp +54 9 11 3295-1439','Asunto','Cuerpo','studio@x.com');
 assert.match(a.gmail,/^https:\/\/mail\.google\.com\/mail\/\?view=cm/);assert.match(a.gmail,/to=ventas%40banchero\.com\.ar/);assert.match(a.whatsapp,/^https:\/\/wa\.me\/5491132951439\?text=/);
 assert.equal(contactLinks('WA 2246 51-8305','a','b').whatsapp?.startsWith('https://wa.me/5492246518305'),true);
 assert.equal(contactLinks('Facebook: fb.com/x','a','b').gmail,undefined);
});
test('el Excel lleva la marca elegida y es un zip válido',()=>{
 const bytes=Buffer.from(quoteWorkbook(sheet,{'AF.01':'Acqua System'}));
 assert.equal(bytes.readUInt32LE(0),0x04034b50);
 const xml=[];let p=0;while(bytes.readUInt32LE(p)===0x04034b50){const size=bytes.readUInt32LE(p+18),n=bytes.readUInt16LE(p+26),start=p+30+n;xml.push(bytes.subarray(start,start+size).toString('utf8'));p=start+size}
 const s1=xml.find(x=>x.includes('<worksheet')&&x.includes('AF.01'));assert.ok(s1.includes('Marca pedida: Acqua System'));
});
