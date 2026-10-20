'use client';
import {useState} from 'react';
import {ChevronLeft,ChevronRight,Plus,Film,Images,PenLine,ArrowUpRight} from 'lucide-react';
import type {ContentPiece} from './marketing';
import inventory from '../data/urbetrack.json';
export const formatClass=(s:string)=>'kind-'+s.toLowerCase();
const iso=(d:Date)=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
const parse=(s:string)=>new Date(s+'T12:00:00');
const label=(d:Date,options:Intl.DateTimeFormatOptions)=>d.toLocaleDateString('es-AR',options);
const local='http://127.0.0.1:18763/';
function Icon({format}:{format:string}){return format==='Video'?<Film size={14}/>:format==='Carrusel'?<Images size={14}/>:<PenLine size={14}/>}
export default function EditorialCalendar({pieces,today,onEdit,onStart,onMove,onReview}:{pieces:ContentPiece[],today:string,onEdit:(p:ContentPiece)=>void,onStart:(date:string)=>void,onMove:(id:string,date:string)=>void,onReview:(id:string)=>void}){
 const [mode,setMode]=useState('Semana'),[selected,setSelected]=useState(today);
 const date=parse(selected),monday=parse(selected);monday.setDate(date.getDate()-(date.getDay()+6)%7);
 const first=new Date(date.getFullYear(),date.getMonth(),1);const gridStart=new Date(first);gridStart.setDate(1-(first.getDay()+6)%7);
 const count=Math.ceil(((first.getDay()+6)%7+new Date(date.getFullYear(),date.getMonth()+1,0).getDate())/7)*7;
 const days=Array.from({length:mode==='Mes'?count:7},(_,i)=>{const d=new Date(mode==='Mes'?gridStart:monday);d.setDate(d.getDate()+i);return d});
 const scheduled=pieces.filter(p=>p.date===selected);
 function move(direction:number){const d=parse(selected);if(mode==='Mes'){d.setDate(1);d.setMonth(d.getMonth()+direction)}else d.setDate(d.getDate()+direction*(mode==='Semana'?7:1));setSelected(iso(d))}
 const heading=mode==='Mes'?label(date,{month:'long',year:'numeric'}):mode==='Día'?label(date,{weekday:'long',day:'numeric',month:'long'}):`${label(days[0],{day:'numeric',month:'short'})} — ${label(days[6],{day:'numeric',month:'short',year:'numeric'})}`;
 return <section className="editorialCalendar"><div className="msSectionTitle"><div><span className="msEyebrow">PLAN EDITORIAL</span><h2>El tiempo de tus ideas</h2></div><div className="calendarModes" aria-label="Vista de calendario">{['Mes','Semana','Día'].map(m=><button key={m} aria-pressed={mode===m} className={mode===m?'active':''} onClick={()=>setMode(m)}>{m}</button>)}</div></div>
 <div className="calendarToolbar"><h3>{heading}</h3><div><button aria-label="Período anterior" onClick={()=>move(-1)}><ChevronLeft size={17}/></button><button onClick={()=>setSelected(today)}>Hoy</button><button aria-label="Período siguiente" onClick={()=>move(1)}><ChevronRight size={17}/></button><label className="calendarDate"><span className="sr-only">Ir a fecha</span><input aria-label="Ir a fecha" type="date" value={selected} onChange={e=>{if(e.target.value)setSelected(e.target.value)}}/></label></div></div>
 <div className="formatLegend">{['Video','Carrusel','Historia','Texto'].map(f=><span className={formatClass(f)} key={f}><i/>{f==='Video'?'Videos':f==='Carrusel'?'Carruseles':f==='Historia'?'Historias':'Textos'}</span>)}</div>
 {mode!=='Día'?<div className="calendarScroll"><div className={'calendarGrid '+(mode==='Mes'?'monthGrid':'weekGrid')}>
 {mode==='Mes'&&['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'].map(d=><div className="calendarWeekday" key={d}>{d}</div>)}
 {days.map(d=><div key={iso(d)} className={'calendarCell '+(iso(d)===today?'isToday ':'')+(d.getMonth()!==date.getMonth()&&mode==='Mes'?'outside':'')} onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();onMove(e.dataTransfer.getData('text/x-ader-content'),iso(d))}}><div className="calendarCellHead"><button aria-label={'Ver día '+iso(d)} onClick={()=>{setSelected(iso(d));setMode('Día')}}>{mode==='Semana'&&<small>{label(d,{weekday:'short'})}</small>}<b>{d.getDate()}</b></button><button aria-label={'Agregar contenido el '+iso(d)} onClick={()=>onStart(iso(d))}><Plus size={13}/></button></div>
 {pieces.filter(p=>p.date===iso(d)).map(p=><button draggable onDragStart={e=>e.dataTransfer.setData('text/x-ader-content',p.id)} className={'calendarEvent '+formatClass(p.format)} key={p.id} onClick={()=>onEdit(p)}><Icon format={p.format}/><span><strong>{p.title}</strong><small>{p.channel} · {p.format}</small></span></button>)}
 </div>)}
 </div></div>:<div className="calendarDaily"><div className="dailySummary"><span>{scheduled.length.toString().padStart(2,'0')}</span><div><h3>{scheduled.length===1?'Contenido previsto':'Contenidos previstos'}</h3><p>Revisá el guion y la pieza antes de publicar.</p></div><button className="msPrimary" onClick={()=>onStart(selected)}><Plus size={15}/>Agregar</button></div>
 {!scheduled.length&&<div className="dailyEmpty"><CalendarMark/><h3>Un día abierto a nuevas ideas.</h3><p>No hay contenido agendado para esta fecha.</p><button onClick={()=>onStart(selected)}>Planificar contenido <Plus size={15}/></button></div>}
 {scheduled.map(p=>{const v=inventory.videos.find(v=>v.id===p.libraryVideo);return <article key={p.id} className={'dailyPreview '+formatClass(p.format)}><div className="dailyVisual">{v?<video controls playsInline preload="none" poster={'/urbetrack-previews/'+v.id+'.jpg'} src={'/urbetrack-previews/'+v.id+'.mp4'}/>:<div className="dailyTextPreview"><img src="/brand/ader-mark.webp" alt=""/><small>{p.format} / BORRADOR</small><h3>{p.title}</h3><p>{p.text||p.idea||'El contenido todavía está por desarrollar.'}</p></div>}</div><div className="dailyInfo"><span className="formatTag"><Icon format={p.format}/>{p.format}</span><h3>{p.title}</h3><p>{p.channel} · {p.status}</p><div className="dailyScript"><small>GUION / TEXTO</small><p>{p.text||p.idea||'Todavía no hay un texto guardado.'}</p></div><button className="msPrimary" onClick={()=>onEdit(p)}>Editar contenido <ArrowUpRight size={15}/></button>{v&&<button className="msTextLink" onClick={()=>onReview(v.id)}>Abrir mesa editorial <ArrowUpRight size={15}/></button>}<small className="dailyCaveat">{v?'Preview de 8 segundos. El MP4 completo y el storyboard están en el editor local.':'Vista del texto guardado. El diseño final se prepara durante la producción.'}</small></div></article>})}
 </div>}
 {mode!=='Día'&&pieces.some(p=>!p.date)&&<details className="unscheduled"><summary>{pieces.filter(p=>!p.date).length} ideas sin fecha</summary>{pieces.filter(p=>!p.date).map(p=><button className={'calendarEvent '+formatClass(p.format)} key={p.id} onClick={()=>onEdit(p)}><Icon format={p.format}/>{p.title}</button>)}</details>}
 </section>
}
function CalendarMark(){return <div className="calendarMark" aria-hidden="true"><span>01</span><i/><i/></div>}

