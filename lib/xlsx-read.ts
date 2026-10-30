/** Lector mínimo de .xlsx en el navegador: primera hoja como filas {A:'..',B:'..'}.
 * Sin dependencias: lee el zip con DecompressionStream y el XML con DOMParser. */
async function inflate(bytes:Uint8Array){
 const stream=new Blob([bytes as BlobPart]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
 return new Uint8Array(await new Response(stream).arrayBuffer());
}
async function unzip(buf:ArrayBuffer,wanted:(name:string)=>boolean){
 const v=new DataView(buf),u8=new Uint8Array(buf),out=new Map<string,string>();
 let eocd=-1;for(let i=buf.byteLength-22;i>=Math.max(0,buf.byteLength-65557);i--)if(v.getUint32(i,true)===0x06054b50){eocd=i;break}
 if(eocd<0)throw Error('El archivo no es un Excel (.xlsx) válido.');
 let p=v.getUint32(eocd+16,true);const n=v.getUint16(eocd+10,true),dec=new TextDecoder();
 for(let k=0;k<n;k++){
  if(v.getUint32(p,true)!==0x02014b50)throw Error('Excel dañado.');
  const method=v.getUint16(p+10,true),size=v.getUint32(p+20,true),nameLen=v.getUint16(p+28,true),extra=v.getUint16(p+30,true),comment=v.getUint16(p+32,true),local=v.getUint32(p+42,true);
  const name=dec.decode(u8.subarray(p+46,p+46+nameLen));p+=46+nameLen+extra+comment;
  if(!wanted(name))continue;
  const start=local+30+v.getUint16(local+26,true)+v.getUint16(local+28,true),data=u8.subarray(start,start+size);
  out.set(name,dec.decode(method===0?data:await inflate(data)));
 }
 return out;
}
export async function readFirstSheet(buf:ArrayBuffer):Promise<Record<string,string>[]>{
 const files=await unzip(buf,n=>n==='xl/sharedStrings.xml'||n==='xl/workbook.xml'||n==='xl/_rels/workbook.xml.rels'||/^xl\/worksheets\/sheet\d+\.xml$/.test(n));
 const parse=(s:string)=>new DOMParser().parseFromString(s,'application/xml');
 const strings=files.has('xl/sharedStrings.xml')?[...parse(files.get('xl/sharedStrings.xml')!).getElementsByTagName('si')].map(si=>[...si.getElementsByTagName('t')].map(t=>t.textContent||'').join('')):[];
 // Primera hoja según el orden del libro (no por nombre de archivo).
 let path='xl/worksheets/sheet1.xml';
 const wb=files.get('xl/workbook.xml'),rels=files.get('xl/_rels/workbook.xml.rels');
 if(wb&&rels){const rid=parse(wb).getElementsByTagName('sheet')[0]?.getAttribute('r:id');const target=[...parse(rels).getElementsByTagName('Relationship')].find(r=>r.getAttribute('Id')===rid)?.getAttribute('Target');if(target)path='xl/'+target.replace(/^\/?xl\//,'').replace(/^\//,'')}
 const xml=files.get(path);if(!xml)throw Error('No se encontró la primera hoja del Excel.');
 return [...parse(xml).getElementsByTagName('row')].map(row=>{
  const o:Record<string,string>={};
  for(const c of row.getElementsByTagName('c')){
   const col=(c.getAttribute('r')||'').replace(/\d+$/,''),t=c.getAttribute('t'),val=c.getElementsByTagName('v')[0]?.textContent??'';
   o[col]=t==='s'?strings[Number(val)]??'':t==='inlineStr'?[...c.getElementsByTagName('t')].map(x=>x.textContent||'').join(''):val;
  }
  return o;
 });
}
/** Condiciones que el proveedor completa al pie de la planilla (columna B pregunta, C respuesta). */
export function conditionsFromRows(rows:Record<string,string>[]){
 const o:Record<string,string>={};for(const r of rows)if(r.B&&r.C&&!r.A)o[r.B.trim()]=r.C.trim();return o;
}
