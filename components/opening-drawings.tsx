'use client';
import {useEffect,useState,type ReactNode} from 'react';
import {useVector} from './compressed-drawing';
import {fabricationMeasures,correctionFor,measureKey,parseLength,metersOf,itemProgress,param,type OpeningsReview,type ReviewItem} from '../lib/openings-review';

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
export function TrimmedDrawing({src,alt,onCrop}:{src?:string;alt:string;onCrop?:(c:Crop)=>void}){
 const url=useVector(src),crop=useCrop(url,src);
 useEffect(()=>{if(crop)onCrop?.(crop)},[crop,onCrop]);
 if(!url||!crop)return <div className="vectorLoading" role="status">Cargando dibujo vectorial…</div>;
 return <div className="openingTrim" style={{aspectRatio:String(crop.aspect),['--a' as string]:crop.aspect}}><img src={url} alt={alt} draggable={false} style={{width:`${100/crop.w}%`,height:`${100/crop.h}%`,left:`${-crop.x/crop.w*100}%`,top:`${-crop.y/crop.h*100}%`}}/></div>;
}

const num=(n:number)=>n.toLocaleString('es-AR',{minimumFractionDigits:3,maximumFractionDigits:3});
// Valor de la corrección cargada en la web, si es una medida legible.
function corrected(review:OpeningsReview|undefined,item:ReviewItem,key:string){const c=correctionFor(review,item.id,measureKey(key));const n=c?.value?parseLength(c.value):null;return c&&c.status!=='dismissed'&&n!=null?n:null}

// Datos del elemento para el globo al pasar el cursor, con el mismo criterio que Sanitarias.
export function OpeningTooltip({item,review,x=0,y=0,extra,inline}:{item:ReviewItem;review?:OpeningsReview;x?:number;y?:number;extra?:ReactNode;inline?:boolean}){
 const progress=itemProgress(item,review),rows=fabricationMeasures(item).filter(m=>m.required||m.value);
 const left=Math.min(x+16,(typeof window==='undefined'?1200:window.innerWidth)-330),top=Math.max(8,Math.min(y-40,(typeof window==='undefined'?800:window.innerHeight)-420));
 return <div role={inline?undefined:'tooltip'} className={'openingTooltip'+(inline?' inline':'')} style={inline?undefined:{left,top}}>
  <strong><span className="openingTag">{item.code}</span>{item.type}</strong>
  <small>{item.category==='Windows'?'Ventana':item.category==='Doors'?'Puerta':'Conjunto de muro cortina'} · {(item as {family?:string}).family}</small>
  <dl>{rows.map(m=>{const fix=corrected(review,item,m.key);return <div key={m.key} className={m.value?'':'missing'}><dt>{m.label}</dt><dd>{m.value?m.value.replace('.',','):'Falta dato'}{fix!=null&&<em> → {num(fix)} m</em>}</dd></div>})}</dl>
  <small>Materiales: {(item as {materials?:string[]}).materials?.join(' · ')||'sin dato'}</small>
  {progress.total>0&&<small className="openingWarning">{progress.total} datos por revisar · {progress.open} sin revisar{progress.proposed?` · ${progress.proposed} corregidos pendientes en Revit`:''}</small>}
  {extra}
 </div>;
}

// Proporción del esquema: los elementos más anchos que altos ocupan una fila completa del tablero.
export function isWideSketch(item:ReviewItem){const wall=item.category==='Curtain Walls',w=wall?metersOf(param(item,'Length')):metersOf(item.width),h=wall?metersOf(param(item,'Unconnected Height')):metersOf(item.head??item.height);return w!=null&&h!=null&&w>h*1.15}

// Esquema acotado dibujado a escala con los parámetros de Revit. No reemplaza el dibujo de Revit:
// no hay geometría inventada, solo un rectángulo con ancho, alto, antepecho y altura superior.
export function OpeningSketch({item,review}:{item:ReviewItem;review?:OpeningsReview}){
 const wall=item.category==='Curtain Walls';
 const width=wall?metersOf(param(item,'Length')):metersOf(item.width),height=wall?metersOf(param(item,'Unconnected Height')):metersOf(item.height);
 const sill=wall?metersOf(param(item,'Base Offset'))??0:metersOf(item.sill),head=wall?null:metersOf(item.head);
 if(width==null||height==null)return <div className="openingSketch empty"><p>Sin ancho y alto legibles en la lectura de Revit: no se dibuja un esquema para no inventar medidas.</p></div>;
 // El encuadre sigue la proporción del elemento: una ventana alta y angosta llena el alto del recuadro.
 const base=sill??0,top=Math.max(head??base+height,base+height),m={l:wall?40:56,r:wall?60:96,t:40,b:34};
 const k=Math.min(330/top,560/width),drawW=Math.max(width*k,70);
 const W=m.l+drawW+m.r,H=m.t+top*k+m.b;
 const x0=m.l+(drawW-width*k)/2,x1=x0+width*k,floor=H-m.b,yb=floor-base*k,yt=yb-height*k;
 const label=(n:number|null|undefined,key:string)=>{const fix=corrected(review,item,key);return fix!=null&&n!=null&&Math.abs(fix-n)>.0005?`${num(n)} → ${num(fix)}`:n==null?'falta':num(n)};
 const dimH=(y:number,a:number,b:number,text:string)=><g className="dim"><line x1={a} x2={b} y1={y} y2={y}/><line x1={a} x2={a} y1={y-5} y2={y+5}/><line x1={b} x2={b} y1={y-5} y2={y+5}/><text x={(a+b)/2} y={y-6} textAnchor="middle">{text}</text></g>;
 const dimV=(x:number,a:number,b:number,text:string,side:1|-1)=>Math.abs(b-a)<1?null:<g className="dim"><line x1={x} x2={x} y1={a} y2={b}/><line x1={x-5} x2={x+5} y1={a} y2={a}/><line x1={x-5} x2={x+5} y1={b} y2={b}/><text transform={`translate(${x+side*7},${(a+b)/2}) rotate(-90)`} textAnchor="middle" dominantBaseline={side>0?'hanging':'auto'}>{text}</text></g>;
 const fullHeight=/techo/i.test(item.type||'');
 return <figure className="openingSketch">
  <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Esquema acotado de ${item.code}`}>
   <line className="floor" x1={4} x2={W-4} y1={floor} y2={floor}/><text className="level" x={6} y={floor+16}>{wall?(param(item,'Base Constraint')||'Nivel base')+' ±0,000':'Nivel del elemento ±0,000'}</text>
   <rect className="opening" x={x0} y={yt} width={x1-x0} height={yb-yt}/>
   {!wall&&item.category==='Windows'&&<line className="glass" x1={x0} y1={yb} x2={x1} y2={yt}/>}
   {dimH(yt-12,x0,x1,(wall?'Largo ':'Ancho ')+label(width,wall?'length':'width'))}
   {dimV(x1+16,yt,yb,'Alto '+label(height,wall?'wallHeight':'height'),1)}
   {dimV(x0-16,yb,floor,(wall?'Desfase ':'Antepecho ')+label(sill,wall?'baseOffset':'sill'),-1)}
   {!wall&&dimV(x1+44,yt,floor,'Alt. sup. '+label(head,'head'),1)}
   <g className="tag" transform={`translate(${(x0+x1)/2},${(yt+yb)/2})`}><rect x={-(item.code.length*3.6+10)} y={-11} width={item.code.length*7.2+20} height={22} rx={11}/><text textAnchor="middle" dominantBaseline="central">{item.code}</text></g>
  </svg>
  <figcaption>Esquema a escala con valores de Revit (m){wall?` · ${item.panelCount??'?'} paneles: sus posiciones no se leyeron, no se dibujan`:''}. Las correcciones cargadas se muestran con →.{!wall&&sill===0?' Arranca en el nivel: antepecho 0,000.':''}{fullHeight?' El tipo se llama «muro a techo», pero la lectura no trae la altura del cielorraso del local: confirmar que la altura superior llega a techo.':''}</figcaption>
 </figure>;
}
