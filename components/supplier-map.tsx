'use client';
import {useEffect,useRef,useState} from 'react';
export type MapPoint={id:string;name:string;lat:number;lon:number;trusted?:boolean;number?:number};
const clamp=(n:number,a:number,b:number)=>Math.max(a,Math.min(b,n));
function project(lat:number,lon:number,z:number){const n=256*2**z,r=clamp(lat,-85,85)*Math.PI/180;return {x:(lon+180)/360*n,y:(1-Math.log(Math.tan(r)+1/Math.cos(r))/Math.PI)/2*n};}
function unproject(x:number,y:number,z:number){const n=256*2**z;return {lon:x/n*360-180,lat:Math.atan(Math.sinh(Math.PI*(1-2*y/n)))*180/Math.PI};}
export default function SupplierMap({center,points,selected,onSelect}:{center:{lat:number;lon:number};points:MapPoint[];selected?:string;onSelect:(id:string)=>void}){
 const root=useRef<HTMLDivElement>(null),drag=useRef<{x:number;y:number;cx:number;cy:number}|null>(null);
 const [size,setSize]=useState({w:600,h:550}),[zoom,setZoom]=useState(11),[view,setView]=useState(center),[failed,setFailed]=useState(false);
 useEffect(()=>{setView(center);setZoom(11)},[center.lat,center.lon]);
 useEffect(()=>{const p=points.find(p=>p.id===selected);if(p)setView({lat:p.lat,lon:p.lon})},[selected]);
 useEffect(()=>{if(!root.current)return;const observer=new ResizeObserver(([r])=>setSize({w:r.contentRect.width,h:r.contentRect.height}));observer.observe(root.current);return()=>observer.disconnect()},[]);
 const c=project(view.lat,view.lon,zoom),left=c.x-size.w/2,top=c.y-size.h/2,tiles=[];
 for(let x=Math.floor(left/256);x<=Math.floor((left+size.w)/256);x++)for(let y=Math.floor(top/256);y<=Math.floor((top+size.h)/256);y++)if(y>=0&&y<2**zoom)tiles.push({x,y,src:`https://tile.openstreetmap.org/${zoom}/${((x%2**zoom)+2**zoom)%2**zoom}/${y}.png`});
 return <div className="supplierMapCanvas" ref={root} aria-label="Mapa interactivo de proveedores" onPointerDown={e=>{if((e.target as HTMLElement).closest('button,a'))return;root.current?.setPointerCapture(e.pointerId);drag.current={x:e.clientX,y:e.clientY,cx:c.x,cy:c.y}}} onPointerMove={e=>{const d=drag.current;if(d)setView(unproject(d.cx-(e.clientX-d.x),d.cy-(e.clientY-d.y),zoom))}} onPointerUp={()=>drag.current=null} onPointerCancel={()=>drag.current=null}>
 {tiles.map(t=><img draggable={false} key={`${zoom}/${t.x}/${t.y}`} src={t.src} alt="" onError={()=>setFailed(true)} style={{position:'absolute',left:t.x*256-left,top:t.y*256-top,width:256,height:256,maxWidth:'none'}}/>)}
 {points.map((p,i)=>{const q=project(p.lat,p.lon,zoom);return <button key={p.id} title={p.name+(p.trusted?' · De confianza':' · Por evaluar')} aria-label={'Ubicar '+p.name} aria-pressed={p.id===selected} className={'supplierPin '+(p.trusted?'trusted':'new')+(p.id===selected?' selected':'')} style={{left:q.x-left,top:q.y-top}} onClick={()=>onSelect(p.id)}>{p.trusted?'✓':p.number||i+1}<span>{p.name}</span></button>})}
 <div className="supplierMapControls"><button aria-label="Acercar mapa" disabled={zoom>=18} onClick={()=>setZoom(z=>z+1)}>+</button><button aria-label="Alejar mapa" disabled={zoom<=4} onClick={()=>setZoom(z=>z-1)}>−</button><button onClick={()=>{setView(center);setZoom(12)}}>Centrar</button></div>
 <div className="supplierMapKey"><span>● Confianza Ader</span><span>● Por evaluar</span></div>{failed&&<div className="supplierMapWarning">El fondo cartográfico no respondió. Las fichas y sus enlaces a Google Maps siguen disponibles.</div>}
 <a className="supplierAttribution" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors</a></div>;
}

