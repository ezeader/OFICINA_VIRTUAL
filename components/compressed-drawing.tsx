'use client';
import {useEffect,useState} from 'react';

async function bytes(url:string,signal?:AbortSignal){
 const response=await fetch(url,{signal});if(!response.ok)throw Error('No se pudo cargar el recurso de documentación.');
 const raw=new Uint8Array(await response.arrayBuffer());
 if(raw[0]!==31||raw[1]!==139)return raw;
 const stream=new Blob([raw]).stream().pipeThrough(new DecompressionStream('gzip'));
 return new Uint8Array(await new Response(stream).arrayBuffer());
}
export async function loadCompressedJson(url:string){return JSON.parse(new TextDecoder().decode(await bytes(url))) as unknown}
export function useVector(url?:string){
 const [result,setResult]=useState<string|undefined>();
 useEffect(()=>{
  setResult(undefined);if(!url)return;if(!url.endsWith('.gz')){setResult(url);return}
  const abort=new AbortController();let objectUrl:string|undefined;
  bytes(url,abort.signal).then(data=>{if(abort.signal.aborted)return;objectUrl=URL.createObjectURL(new Blob([data],{type:'image/svg+xml'}));setResult(objectUrl)}).catch(()=>{if(!abort.signal.aborted)setResult(undefined)});
  return()=>{abort.abort();if(objectUrl)URL.revokeObjectURL(objectUrl)};
 },[url]);return result;
}
export default function VectorImage({src,alt}:{src?:string;alt:string}){
 const image=useVector(src);return image?<img src={image} alt={alt} loading="lazy"/>:<div className="vectorLoading" role="status">Cargando dibujo vectorial…</div>;
}
