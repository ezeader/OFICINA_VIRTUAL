const json=(data,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store'}});
const keyFor=entry=>'documents/'+entry.sha256;
export function parseRange(value,size){
 if(!value)return null;
 const match=/^bytes=(\d*)-(\d*)$/.exec(value);
 if(!match||(!match[1]&&!match[2]))throw Error('Invalid range');
 let start=match[1]?Number(match[1]):Math.max(0,size-Number(match[2]));
 let end=match[1]?(match[2]?Math.min(Number(match[2]),size-1):size-1):size-1;
 if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start<0||start>=size||end<start)throw Error('Invalid range');
 return {offset:start,length:end-start+1};
}
export async function readDocument(request,bucket,manifest){
 // These documents are shared within the owner-private Site, not user-owned
 // workspace records. Sites dispatch enforces access for visitors AND service
 // callers; its service credential intentionally supplies no visitor identity.
 const pathname=decodeURIComponent(new URL(request.url).pathname);
 const entry=Object.hasOwn(manifest,pathname)?manifest[pathname]:undefined;
 if(!entry)return json({error:'Documento inexistente'},404);
 if(!bucket)return json({error:'Almacenamiento de documentos no disponible'},503);
 const etag='"'+entry.sha256+'"';
 const headers=new Headers({'Content-Type':entry.type,'ETag':etag,'Cache-Control':'private, max-age=0, must-revalidate','Accept-Ranges':'bytes','X-Content-Type-Options':'nosniff'});
 let range=null;
 try{range=parseRange(request.headers.get('if-range')&&request.headers.get('if-range')!==etag?null:request.headers.get('range'),entry.size)}catch{return new Response(null,{status:416,headers:{'Content-Range':`bytes */${entry.size}`}})}
 const object=request.method==='HEAD'?await bucket.head(keyFor(entry)):await bucket.get(keyFor(entry),range?{range}:undefined);
 if(!object||object.size!==entry.size||object.customMetadata?.sha256!==entry.sha256)return json({error:'Este documento está terminando de sincronizarse. Volvé a intentarlo en unos minutos.'},503);
 if(request.headers.get('if-none-match')===etag)return new Response(null,{status:304,headers});
 headers.set('Content-Length',String(range?.length??entry.size));
 if(range)headers.set('Content-Range',`bytes ${range.offset}-${range.offset+range.length-1}/${entry.size}`);
 return new Response(request.method==='HEAD'?null:object.body,{status:range?206:200,headers});
}
export async function uploadDocument(request,bucket,manifest){
 // The private Sites boundary authorizes service uploads. Only pre-approved,
 // immutable hashes can be written; this endpoint cannot change documentation.
 if(request.headers.get('origin')!==new URL(request.url).origin)return json({error:'Origen inválido'},403);
 if(!bucket)return json({error:'Almacenamiento no disponible'},503);
 const pathname=new URL(request.url).searchParams.get('path');
 const entry=pathname&&Object.hasOwn(manifest,pathname)?manifest[pathname]:undefined;
 if(!entry)return json({error:'El documento no pertenece a esta publicación'},404);
 if(entry.size>24*1024*1024)return json({error:'Archivo demasiado grande'},413);
 const stored=await bucket.head(keyFor(entry));
 if(stored?.size===entry.size&&stored?.customMetadata?.sha256===entry.sha256)return json({status:'verified',sha256:entry.sha256,size:entry.size});
 if(!request.body)return json({error:'Archivo vacío'},400);
 const bytes=new Uint8Array(entry.size);let offset=0;
 const reader=request.body.getReader();
 try{while(true){const {done,value}=await reader.read();if(done)break;if(offset+value.length>entry.size){await reader.cancel();return json({error:'Tamaño incorrecto'},413)}bytes.set(value,offset);offset+=value.length}}finally{reader.releaseLock()}
 if(offset!==entry.size)return json({error:'Archivo incompleto'},400);
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
 if(hash!==entry.sha256)return json({error:'La huella digital no coincide con el original'},422);
 await bucket.put(keyFor(entry),bytes,{sha256:hash,httpMetadata:{contentType:entry.type},customMetadata:{sha256:hash}});
 return json({status:'verified',sha256:hash,size:entry.size});
}
