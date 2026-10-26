// Generated files are private to the authenticated workspace owner and project.
const reply=(data,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store'}});
export const MAX_EXPORT_BYTES=48*1024*1024;
const types={pdf:'application/pdf',xlsx:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'};
export async function exportsRequest(request,bucket){
 const owner=request.headers.get('oai-authenticated-user-id');
 if(!owner)return reply({error:'Iniciá sesión para acceder a tus exportaciones.'},401);
 if(!bucket)return reply({error:'El almacenamiento de archivos no está disponible.'},503);
 const url=new URL(request.url),project=url.searchParams.get('project');
 if(!project||! /^[a-zA-Z0-9_-]{1,80}$/.test(project))return reply({error:'Proyecto inválido.'},400);
 const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(owner)))].map(x=>x.toString(16).padStart(2,'0')).join('');
 const prefix=`exports/${hash}/${project}/`;
 if(request.method==='GET'){
  const id=url.searchParams.get('id');
  if(id){
   if(!/^[a-f0-9-]{36}$/.test(id))return reply({error:'Archivo inválido.'},400);
   const file=await bucket.get(prefix+id);
   if(!file)return reply({error:'No se encontró el archivo.'},404);
   const meta=JSON.parse(file.customMetadata.record);
   return new Response(file.body,{headers:{'Content-Type':types[meta.format], 'Content-Length':String(file.size),'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Content-Disposition':`${url.searchParams.has('download')?'attachment':'inline'}; filename*=UTF-8''${encodeURIComponent(meta.name)}`}});
  }
  const files=[];let cursor;
  do{const page=await bucket.list({prefix,include:['customMetadata'],cursor});for(const o of page.objects){if(o.customMetadata?.record)files.push({...JSON.parse(o.customMetadata.record),size:o.size})}cursor=page.truncated?page.cursor:undefined}while(cursor);
  return reply(files.sort((a,b)=>b.date.localeCompare(a.date)));
 }
 if(request.method!=='PUT')return reply({error:'Método no permitido.'},405);
 if(request.headers.get('origin')!==url.origin)return reply({error:'Origen inválido.'},403);
 let meta;
 try{meta=JSON.parse(decodeURIComponent(request.headers.get('x-export-metadata')||''))}catch{return reply({error:'Metadatos inválidos.'},400)}
 if(!meta||!Object.hasOwn(types,meta.format)||typeof meta.name!=='string'||meta.name.length>180||/[\r\n\/\\]/.test(meta.name)||!meta.name.endsWith('.'+meta.format)||!Array.isArray(meta.rubros)||meta.rubros.length>40||meta.rubros.some(r=>typeof r!=='string'||r.length>100))return reply({error:'Nombre o formato inválido.'},400);
 if(request.headers.get('content-type')!==types[meta.format]||!request.body)return reply({error:'Contenido inválido.'},400);
 const length=Number(request.headers.get('content-length'));
 if(length>MAX_EXPORT_BYTES)return reply({error:'El archivo supera 48 MB. Exportá los rubros por separado.'},413);
 const reader=request.body.getReader(),chunks=[];let size=0;
 try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>MAX_EXPORT_BYTES){await reader.cancel();return reply({error:'El archivo supera 48 MB. Exportá por rubro.'},413)}chunks.push(value)}}finally{reader.releaseLock()}
 if(!size)return reply({error:'Archivo vacío.'},400);
 const bytes=new Uint8Array(size);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length}
 const signature=new TextDecoder().decode(bytes.slice(0,5));
 if(meta.format==='pdf'?!signature.startsWith('%PDF-'):bytes[0]!==80||bytes[1]!==75)return reply({error:'El archivo no corresponde al formato indicado.'},400);
 const record={id:crypto.randomUUID(),projectId:project,name:meta.name,format:meta.format,rubros:meta.rubros,date:new Date().toISOString(),size,sheets:Number(meta.sheets)||0};
 await bucket.put(prefix+record.id,bytes,{httpMetadata:{contentType:types[meta.format]},customMetadata:{record:JSON.stringify(record)}});
 return reply(record,201);
}
