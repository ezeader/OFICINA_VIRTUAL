'use client';
// Visor de láminas común a todos los rubros (formato Sanitarias): grilla agrupada, lámina con un botón por dibujo,
// dibujo ampliado con cajas por elemento y ficha de cada código.
import {useCallback,useEffect,useState,type PointerEvent,type ReactNode} from 'react';
import {ArrowLeft,Download} from 'lucide-react';
import VectorImage from './compressed-drawing';
import RevitOpenButton from './revit-open-button';
import DrawingViewport from './drawing-viewport';
import {TrimmedDrawing,type Crop} from './opening-drawings';
import {levelName,type RubroLevels} from '../lib/rubros';
import './sanitary-sheets.css';
import './openings-desk.css';

export type RubroView={id:string|number;name:string;scale:number;kind?:string;image:string;region?:number[];tags?:string[];dimensions?:{label:string;values_m:number[];associative?:boolean}[];elements?:{code:string;elementId?:string;box:number[]}[]};
export type RubroSheet={number:string;title:string;level?:string|null;sector?:string|null;kind?:string;element?:string;rebar?:string;note?:string;image?:string;preview?:string;thumbnail?:string;pdf?:string;sheetId?:string;aspect?:number;views?:RubroView[]};
export type RubroCode={code:string;kind?:string;label:string;status?:string;length_m?:number;area_m2?:number;volume_m3?:number};

const n2=(n:number)=>n.toLocaleString('es-AR',{minimumFractionDigits:2,maximumFractionDigits:2});
const SHEET_ASPECT=2383.94/1683.78;

export function useRubroViewer({rubro,project='Casa Ángel',sheets,codes,kindLabel,unitNote}:{rubro:string;project?:string;sheets:RubroSheet[];codes:RubroCode[];kindLabel:(code:string,kind?:string)=>string;unitNote?:(c:RubroCode)=>string|undefined}){
 const [sheet,setSheet]=useState<RubroSheet|null>(null),[lightbox,setLightbox]=useState<number|null>(null),[crop,setCrop]=useState<Crop>(),[hover,setHover]=useState<{code:string;x:number;y:number;label?:string}|null>(null);
 const views=sheet?.views||[];
 useEffect(()=>{if(lightbox===null)return;const key=(e:KeyboardEvent)=>{if(e.key==='Escape')setLightbox(null);else if(e.key==='ArrowRight')setLightbox(i=>i===null?i:(i+1)%views.length);else if(e.key==='ArrowLeft')setLightbox(i=>i===null?i:(i-1+views.length)%views.length)};window.addEventListener('keydown',key);document.body.style.overflow='hidden';return()=>{window.removeEventListener('keydown',key);document.body.style.overflow=''}},[lightbox,views.length]);
 const onCrop=useCallback((c:Crop)=>setCrop(c),[]);
 const byCode=new Map(codes.map(c=>[c.code,c]));
 const open=(s:RubroSheet|null)=>{setSheet(s);setLightbox(null);setHover(null);window.scrollTo({top:0})};
 const zoom=(i:number)=>{setCrop(undefined);setLightbox(i)};
 const hoverOn=(code?:string)=>code?{onPointerMove:(e:PointerEvent)=>{if(!e.buttons&&e.pointerType==='mouse')setHover({code,x:e.clientX,y:e.clientY})},onPointerLeave:()=>setHover(null)}:{};
 const fichaOf=(code:string)=>sheets.find(s=>s.element===code);
 const quantity=(c:RubroCode)=>[c.length_m!=null&&!c.area_m2?n2(c.length_m)+' m':'',c.area_m2!=null?n2(c.area_m2)+' m²':'',c.volume_m3!=null?n2(c.volume_m3)+' m³':''].filter(Boolean).join(' · ');
 const codeCard=(code:string,extra?:ReactNode)=>{const c=byCode.get(code),f=fichaOf(code);return <article key={code} className="openingCard" {...hoverOn(code)}><header><span className="openingTag">{code}</span><small>{kindLabel(code,c?.kind)}</small></header>{c?<><p className="openingSize">{c.label.split(' · ').slice(1).join(' · ')||c.label}</p>{quantity(c)&&<p className="openingSub">{quantity(c)}</p>}{c.status&&<p className={/confirmar|definir|no modelad/i.test(c.status)?'openingAlert':'openingSub'}>{c.status}</p>}</>:<p className="openingSub">Sin ficha en este rubro.</p>}{extra}{f&&f!==sheet&&<div className="openingLinks"><button onClick={()=>open(f)}>Ver ficha de {code} ↗</button></div>}</article>};
 const tooltip=hover&&(byCode.get(hover.code)||hover.label)?(()=>{const c=byCode.get(hover.code)||{code:hover.code,label:hover.label!};return <div role="tooltip" className="openingTooltip" style={{left:Math.min(hover.x+16,window.innerWidth-340),top:Math.max(8,hover.y-40)}}><strong><span className="openingTag">{c.code}</span></strong>{hover.label&&hover.label!==c.label&&<small><b>{hover.label}</b></small>}<small>{c.label}</small>{quantity(c)&&<small>{quantity(c)}{unitNote?.(c)?' '+unitNote(c):''}</small>}{c.status&&<small>{c.status}</small>}</div>})():null;

 const card=(s:RubroSheet)=><button key={s.number} className="sheetCard" onClick={()=>open(s)}>{s.thumbnail?<img src={s.thumbnail} alt={'Lámina '+s.title} loading="lazy"/>:<div className="openingNoThumb">Sin vista previa</div>}<span className="sheetHoverTitle" aria-hidden="true">{s.title}</span><span><small>{s.number}</small><strong>{(s.element&&byCode.get(s.element)?.label)||s.title}</strong><span className="openingCodes">{[...new Set((s.views||[]).flatMap(v=>v.tags||[]))].slice(0,8).map(c=><b key={c}>{c}</b>)}</span>{(s.views||[]).length>0&&<em>{s.views!.length} dibujos</em>}</span></button>;
 const grid=(groups:{title:string;sheets:RubroSheet[]}[])=>groups.map(g=><section key={g.title} className="openingGroup"><h4 className="openingGroupTitle">{g.title} <small>{g.sheets.length} {g.sheets.length===1?'lámina':'láminas'}</small></h4><div className="sheetGrid">{g.sheets.map(card)}</div></section>);
 // Por nivel: arriba la planta completa (plano principal del rubro) y debajo las láminas de ese nivel.
 const planView=(s:RubroSheet,level:string)=>(s.views||[]).find(v=>v.name.toLowerCase().includes(levelName(level).toLowerCase()))||s.views?.[0];
 const levels=({levels,others}:RubroLevels<RubroSheet>)=><>
  {levels.length>1&&<nav className="rubroLevelJump" aria-label="Niveles">{levels.map(l=><button key={l.level} onClick={()=>document.getElementById('nivel-'+l.level)?.scrollIntoView({behavior:'smooth'})}>{levelName(l.level)}</button>)}</nav>}
  {levels.map(l=>{const v=l.plan&&planView(l.plan,l.level),count=(l.plan?1:0)+l.groups.reduce((n,g)=>n+g.sheets.length,0);return <section key={l.level} id={'nivel-'+l.level} className="openingGroup rubroLevel"><h4 className="openingGroupTitle">{levelName(l.level)} <small>{count} {count===1?'lámina':'láminas'}</small></h4>
   {l.plan&&<button className="rubroLevelPlan" onClick={()=>open(l.plan!)}><span className="rubroLevelDrawing">{v?<TrimmedDrawing src={v.image} alt={'Planta completa · '+levelName(l.level)}/>:<img src={l.plan.preview||l.plan.thumbnail} alt={'Planta completa · '+levelName(l.level)}/>}</span><span className="rubroLevelCaption"><small>{l.plan.number} · plano principal</small><strong>{l.plan.title}</strong><em>Planta completa del nivel · tocá para abrir la lámina</em></span></button>}
   {l.groups.map(g=><div key={g.title} className="rubroLevelGroup"><h5>{g.title} <small>{g.sheets.length} {g.sheets.length===1?'lámina':'láminas'}</small></h5><div className="sheetGrid">{g.sheets.map(card)}</div></div>)}
  </section>})}
  {grid(others)}
 </>;

 const page=sheet?<section className="openingsDesk sheetExplorer">
  <div className="sheetHeading"><div><p className="eyebrow">{project.toUpperCase()} / {rubro.toUpperCase()}</p><h3>{sheet.title}</h3><p>{sheet.number}</p></div><button className="sheetBack" onClick={()=>open(null)}><ArrowLeft size={15}/>Todas las láminas</button></div>
  <div className="sheetTabs"><span className="openingTabHint">{views.length?'Tocá un dibujo para ampliarlo':'Lámina exportada de Revit'}</span>{sheet.pdf&&<a href={sheet.pdf} target="_blank" rel="noreferrer">PDF de la lámina <Download size={14}/></a>}{sheet.sheetId&&<RevitOpenButton id={sheet.sheetId} label="Abrir en Revit"/>}</div>
  <div className="sheetCanvas openingSheet" style={{aspectRatio:String(sheet.aspect||SHEET_ASPECT),...(sheet.aspect&&sheet.aspect<1?{maxWidth:`min(100%,calc(88vh * ${sheet.aspect}))`,marginInline:'auto'}:{})}}>{sheet.preview&&<img className="openingPreview" src={sheet.preview} alt="" aria-hidden="true"/>}<VectorImage src={sheet.image} alt={'Lámina '+sheet.title}/>{views.map((v,i)=>v.region?<button key={v.id} className="sheetHotspot" aria-label={'Ampliar '+v.name} style={{left:`${v.region[0]*100}%`,top:`${v.region[1]*100}%`,width:`${(v.region[2]-v.region[0])*100}%`,height:`${(v.region[3]-v.region[1])*100}%`}} onClick={()=>zoom(i)}><span>{v.name} ↗</span></button>:null)}</div>
  {(sheet.rebar||sheet.note)&&<p className="openingPendingLine">{sheet.rebar||sheet.note}</p>}
  {views.length>0&&<><h4 className="openingGroupTitle">Dibujos de esta lámina</h4><div className="projectViewCards openingViewCards">{views.map((v,i)=><button key={v.id} onClick={()=>zoom(i)}><span className="openingViewPreview"><TrimmedDrawing src={v.image} alt={v.name}/></span><span className="psViewCardCopy"><strong>{v.name}</strong><small>Escala 1:{v.scale}{v.dimensions?.length?` · ${v.dimensions.length} cotas`:''}</small><span>Ampliar ↗</span></span></button>)}</div></>}
  {(()=>{const tagged=[...new Set(views.flatMap(v=>v.tags||[]))];return tagged.length>0&&<><h4 className="openingGroupTitle">Elementos de esta lámina <small>{tagged.length}</small></h4><div className="openingCards">{tagged.map(c=>codeCard(c))}</div></>})()}
  {lightbox!==null&&views[lightbox]&&(()=>{const v=views[lightbox];return <div className="openingLightbox" role="dialog" aria-modal="true" aria-label={'Dibujo ampliado · '+v.name}>
   <div className="openingLightboxMain"><DrawingViewport aspect={crop?.aspect||1.4} identity={String(v.id)} controls={<div className="openingLightboxBar"><strong>{v.name}</strong><span>1:{v.scale} · {sheet.number}</span><button onClick={()=>zoom((lightbox-1+views.length)%views.length)} aria-label="Dibujo anterior">←</button><button onClick={()=>zoom((lightbox+1)%views.length)} aria-label="Dibujo siguiente">→</button></div>}><div className="openingHoverArea"><TrimmedDrawing key={v.id} src={v.image} alt={v.name} onCrop={onCrop} boxes={v.elements} onBox={(code,x,y,label)=>setHover(code?{code,x,y,label}:null)}/></div></DrawingViewport></div>
   <aside className="openingLightboxSide"><button className="openingLightboxClose" onClick={()=>setLightbox(null)}>Cerrar · Esc</button>{v.dimensions?.length?<section className="openingViewDims"><h5>Cotas de este dibujo</h5>{v.dimensions.map((d,i)=><p key={i}>{d.label}: <b>{d.values_m.map(x=>n2(x)).join(' + ')} m</b></p>)}</section>:null}{(v.tags||[]).map(c=>codeCard(c))}</aside>
  </div>})()}
  {tooltip}
 </section>:null;
 return {sheet,open,page,grid,levels,codeCard,hoverOn,tooltip,byCode,fichaOf};
}
