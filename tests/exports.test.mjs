import test from 'node:test';
import assert from 'node:assert/strict';
import ExcelJS from 'exceljs';
import {quantityWorkbook} from '../lib/quantity-workbook.mjs';
import {exportsRequest,MAX_EXPORT_BYTES} from '../lib/export-storage.mjs';

function bucket(){const objects=new Map();return {objects,async put(key,body,options){objects.set(key,{body,size:body.length,...options})},async get(key){return objects.get(key)},async list({prefix}){return {objects:[...objects].filter(([k])=>k.startsWith(prefix)).map(([key,v])=>({key,...v})),truncated:false}}}}
const req=(method='GET',owner='ader',project='angel',extra={})=>new Request(`https://office.test/api/exports?project=${project}`,{method,headers:{...(owner?{'oai-authenticated-user-id':owner}:{}),...extra.headers},...(extra.body?{body:extra.body}:{} )});
const metadata={name:'Casa Ángel.pdf',format:'pdf',rubros:['Sanitaria'],sheets:1};
const upload=(overrides={})=>req('PUT','ader','angel',{headers:{origin:'https://office.test','content-type':'application/pdf','x-export-metadata':encodeURIComponent(JSON.stringify(metadata)),...overrides},body:'%PDF-1.7 test'});

test('XLSX preserves display order, decimals, missing values and literal supplier text',async()=>{
 const bytes=await quantityWorkbook({project:'Casa Ángel',label:'Sanitaria',scope:'AF, sin desperdicios',sheets:[{name:'Agua fría',columns:['Código','Longitud m','Material','Nota'],rows:[['AF-T10',1.234,null,'=1+1'],['AF-T02',0.22,'PPR','+SUM(A1)']]}]});
 const book=new ExcelJS.Workbook();await book.xlsx.load(bytes);const ws=book.worksheets[0];
 assert.equal(ws.getCell('A2').value,'AF-T10');assert.equal(ws.getCell('A3').value,'AF-T02');assert.equal(ws.getCell('B2').value,1.234);assert.equal(ws.getCell('C2').value,null);
 assert.equal(ws.getCell('D2').value,'=1+1');assert.equal(ws.getCell('D2').type,ExcelJS.ValueType.String);
 assert.equal(ws.views[0].state,'frozen');assert.ok(ws.autoFilter);assert.equal(book.worksheets[1].name,'Alcance');
});
test('worksheet names remain valid and unique, including a user scope sheet',async()=>{
 const bytes=await quantityWorkbook({project:'A',label:'B',scope:'C',sheets:['A/B','A:B','Alcance'].map(name=>({name,columns:['Cantidad'],rows:[[1]]}))});
 const book=new ExcelJS.Workbook();await book.xlsx.load(bytes);assert.equal(new Set(book.worksheets.map(s=>s.name.toLowerCase())).size,4);
});
test('exports persist and are isolated by owner and project',async()=>{
 const b=bucket(),saved=await exportsRequest(upload(),b);assert.equal(saved.status,201);const file=await saved.json();
 assert.equal((await (await exportsRequest(req(),b)).json()).length,1);
 assert.deepEqual(await (await exportsRequest(req('GET','other'),b)).json(),[]);
 assert.deepEqual(await (await exportsRequest(req('GET','ader','other'),b)).json(),[]);
 for(const owner of ['ader','other']){const r=await exportsRequest(new Request(`https://office.test/api/exports?project=angel&id=${file.id}`,{headers:{'oai-authenticated-user-id':owner}}),b);assert.equal(r.status,owner==='ader'?200:404);if(owner==='ader'){assert.match(r.headers.get('content-disposition'),/^inline/);assert.equal(await r.text(),'%PDF-1.7 test')}}
});
test('reject missing identity, foreign origin, malformed format and oversize before writes',async()=>{
 const b=bucket();assert.equal((await exportsRequest(req('GET',''),b)).status,401);
 assert.equal((await exportsRequest(upload({origin:'https://foreign.test'}),b)).status,403);
 assert.equal((await exportsRequest(upload({'content-length':String(MAX_EXPORT_BYTES+1)}),b)).status,413);
 assert.equal((await exportsRequest(upload({'x-export-metadata':'invalid'}),b)).status,400);
 assert.equal((await exportsRequest(req('PUT','ader','angel',{headers:{origin:'https://office.test','content-type':'application/pdf','x-export-metadata':encodeURIComponent(JSON.stringify(metadata))},body:'not pdf'}),b)).status,400);
 assert.equal(b.objects.size,0);
});


test('PDF export preserves page geometry and vector streams, in source order without fragment duplicates',async()=>{
 const {PDFDocument,PDFName,PDFRawStream}=await import('pdf-lib');
 const {mergePdfSources}=await import('../lib/pdf-export.mjs');
 const a=await PDFDocument.create();a.addPage([420,297]).drawText('Cocina AF 32 mm 1.234 m');a.addPage([800,600]).drawLine({start:{x:10,y:10},end:{x:200,y:200}});
 const b=await PDFDocument.create();b.addPage([900,700]).drawText('Abertura V-01');
 const sources={'/a.pdf':await a.save(),'/b.pdf':await b.save()};let reads=0;
 const result=await mergePdfSources(['/a.pdf#page=1','/a.pdf#page=2','/b.pdf'],{title:'Prueba',read:url=>{reads++;return sources[url]}});
 const merged=await PDFDocument.load(result.bytes);assert.equal(reads,2);assert.equal(result.pages,3);
 assert.deepEqual(merged.getPages().map(p=>p.getSize()),[{width:420,height:297},{width:800,height:600},{width:900,height:700}]);
 const original=await PDFDocument.load(sources['/a.pdf']);
 const streams=page=>{const array=page.node.Contents();return array.asArray().map(ref=>page.doc.context.lookup(ref,PDFRawStream).getContentsString())};
 assert.deepEqual(streams(merged.getPage(0)),streams(original.getPage(0)));
 assert.deepEqual(streams(merged.getPage(1)),streams(original.getPage(1)));
 await assert.rejects(()=>mergePdfSources(['/missing.pdf'],{title:'Prueba',read:()=>{throw Error('Falta PDF')}}),/Falta PDF/);
});
