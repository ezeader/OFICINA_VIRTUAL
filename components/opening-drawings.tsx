'use client';
import {useEffect,useState} from 'react';
import {useVector} from './compressed-drawing';
import {fabricationMeasures,correctionFor,NOTE_KEY,type OpeningsReview,type ReviewItem} from '../lib/openings-review';
import {sizeOf,surveySpecs,type BudgetItem} from '../lib/openings-budget';

// Recorte automático: se rasteriza la vista exportada de Revit y se busca el área con dibujo,
// así cada vista ocupa su recuadro en lugar de flotar dentro del marco de la ventana gráfica.
export type Crop={x:number;y:number;w:number;h:number;aspect:number};
const crops=new Map<string,Promise<Crop>>();
function measureCrop(url:string,key=url){
 if(!crops.has(key))crops.set(key,new Promise<Crop>((resolve,reject)=>{
  const img=new Image();
  img.onload=()=>{
   const W=img.naturalWidth||1,H=img.naturalHeight||1,k=Math.min(1,900/Math.max(W,H)),cw=Math.max(1,Math.round(W*k)),ch=Math.max(1,Math.round(H*k));
   const canvas=document.createElement('canvas');canvas.width=cw;canvas.height=ch;
   const ctx=canvas.getContext('2d',{willReadFrequently:true});
   const full={x:0,y:0,w:1,h:1,aspect:W/H};
   if(!ctx){resolve(full);return}
   ctx.drawImage(img,0,0,cw,ch);
   let data:Uint8ClampedArray;try{data=ctx.getImageData(0,0,cw,ch).data}catch{resolve(full);return}
   let x0=cw,y0=ch,x1=-1,y1=-1;
   for(let y=0;y<ch;y++)for(let x=0;x<cw;x++){const i=(y*cw+x)*4;if(data[i+3]>24&&(data[i]<235||data[i+1]<235||data[i+2]<235)){if(x<x0)x0=x;if(x>x1)x1=x;if(y<y0)y0=y;if(y>y1)y1=y}}
   if(x1<0){resolve(full);return}
   const pad=Math.round(Math.max(x1-x0,y1-y0)*.04)+2;
   x0=Math.max(0,x0-pad);y0=Math.max(0,y0-pad);x1=Math.min(cw-1,x1+pad);y1=Math.min(ch-1,y1+pad);
   const w=(x1-x0+1)/cw,h=(y1-y0+1)/ch;
   resolve({x:x0/cw,y:y0/ch,w,h,aspect:(w*W)/(h*H)});
  };
  img.onerror=()=>reject(Error('No se pudo leer el dibujo.'));
  img.src=url;
 }));
 return crops.get(key)!;
}
export function useCrop(url?:string,key?:string){
 const [state,setState]=useState<{url:string;crop:Crop}>();
 useEffect(()=>{if(!url)return;let alive=true;measureCrop(url,key).then(crop=>{if(alive)setState({url,crop})}).catch(()=>{crops.delete(key||url);if(alive)setState({url,crop:{x:0,y:0,w:1,h:1,aspect:1.414}})});return()=>{alive=false}},[url,key]);
 return url&&state?.url===url?state.crop:undefined;
}
// Ocupa todo su contenedor y muestra solo la zona recortada del dibujo.
// boxes: elementos ubicados en la imagen completa (fracciones 0–1); se reubican sobre el recorte.
export function TrimmedDrawing({src,alt,onCrop,boxes,onBox}:{src?:string;alt:string;onCrop?:(c:Crop)=>void;boxes?:{code:string;box:number[]}[];onBox?:(code:string|null,x:number,y:number)=>void}){
 const url=useVector(src),crop=useCrop(url,src);
 useEffect(()=>{if(crop)onCrop?.(crop)},[crop,onCrop]);
 if(!url||!crop)return <div className="vectorLoading" role="status">Cargando dibujo vectorial…</div>;
 return <div className="openingTrim" style={{aspectRatio:String(crop.aspect),['--a' as string]:crop.aspect}}><img src={url} alt={alt} draggable={false} style={{width:`${100/crop.w}%`,height:`${100/crop.h}%`,left:`${-crop.x/crop.w*100}%`,top:`${-crop.y/crop.h*100}%`}}/>{boxes?.map((b,i)=><span key={b.code+i} className="openingBox" style={{left:`${(b.box[0]-crop.x)/crop.w*100}%`,top:`${(b.box[1]-crop.y)/crop.h*100}%`,width:`${(b.box[2]-b.box[0])/crop.w*100}%`,height:`${(b.box[3]-b.box[1])/crop.h*100}%`}} onPointerMove={e=>{if(!e.buttons)onBox?.(b.code,e.clientX,e.clientY)}} onPointerLeave={()=>onBox?.(null,0,0)}><b>{b.code}</b></span>)}</div>;
}

// Datos del elemento al pasar el cursor, con el mismo criterio que Sanitarias: medidas con valor y lo que falta.
export function OpeningTooltip({item,review,x=0,y=0}:{item:ReviewItem;review?:OpeningsReview;x?:number;y?:number}){
 const rows=fabricationMeasures(item),known=rows.filter(m=>m.value),missing=rows.filter(m=>m.required&&!m.value),note=correctionFor(review,item.id,NOTE_KEY)?.note;
 const left=Math.min(x+16,(typeof window==='undefined'?1200:window.innerWidth)-340),top=Math.max(8,Math.min(y-40,(typeof window==='undefined'?800:window.innerHeight)-380));
 return <div role="tooltip" className="openingTooltip" style={{left,top}}>
  <strong><span className="openingTag">{item.code}</span>{item.type}</strong>
  <dl>{known.map(m=><div key={m.key}><dt>{m.label}</dt><dd>{m.value!.replace(' m','').replace('.',',')}{/^d/.test(m.value!)&&m.value!.endsWith(' m')?' m':''}</dd></div>)}</dl>
  {(()=>{const b=item as unknown as BudgetItem,s=sizeOf(b);return <>{s&&<small>{s.area.toLocaleString('es-AR',{maximumFractionDigits:2})} m² · {s.perimeter.toLocaleString('es-AR',{maximumFractionDigits:2})} m de marco</small>}{surveySpecs(b).filter(x=>x.value).slice(0,3).map(x=><small key={x.label}><b>{x.label}:</b> {x.value!.replace(/(\d)\.(\d)/g,'$1,$2')}</small>)}</>})()}
  {missing.length>0&&<small className="openingWarning">Sin dato en Revit: {missing.map(m=>m.label.toLowerCase()).join(', ')}</small>}
  {note&&<small>✎ {note}</small>}
 </div>;
}
