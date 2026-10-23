'use client';
import {useCallback,useEffect,useMemo,useState,type PointerEvent} from 'react';
import {ArrowLeft,Download} from 'lucide-react';
import VectorImage from './compressed-drawing';
import RevitOpenButton from './revit-open-button';
import DrawingViewport from './drawing-viewport';
import {TrimmedDrawing,type Crop} from './opening-drawings';
import {concreteTotals,groupCases,groupStructureSheets,plainWarning,type StructureCode,type StructureManifest,type StructureSheet,type Wall} from '../lib/structure';
import './sanitary-sheets.css';
import './openings-desk.css';

type Tab='laminas'|'computo'|'muros'|'revision'|'pendientes';
const TABS:[Tab,string][]=[['laminas','Láminas'],['computo','Cómputo de hormigón'],['muros','Muros de hormigón'],['revision','Revisión pendiente'],['pendientes','Qué falta definir']];
const n2=(n:number)=>n.toLocaleString('es-AR',{minimumFractionDigits:2,maximumFractionDigits:2});
const m=(n?:number)=>n==null?'—':n.toLocaleString('es-AR',{minimumFractionDigits:2,maximumFractionDigits:2});
// Decisiones tomadas con la opción recomendada mientras el usuario no indique otra cosa.
const DECISIONS=[
 'Losas de Planta Alta y Entrepiso: no se asume hormigón; se documentan como «losa a confirmar» (solo L01.01 con su capa de 15 cm cuenta como hormigón).',
 'Fundaciones: se documenta solo la platea de Planta Baja de 15 cm; el resto queda como «no modelado / a definir».',
 'No se cambia el parámetro Structural de los muros en el modelo: se identifican por su tipo «Muro Hormigón 20cm».',
 'Numeración MH- (muros), LO- (losas), PL- (platea), VE- (vigas) y CO- (columnas), guardada en Mark.',
];

export default function StructureDesk(){
 const [data,setData]=useState<StructureManifest>(),[error,setError]=useState(''),[tab,setTab]=useState<Tab>('laminas'),[sheet,setSheet]=useState<StructureSheet|null>(null);
 const [lightbox,setLightbox]=useState<number|null>(null),[crop,setCrop]=useState<Crop>(),[hover,setHover]=useState<{code:string;x:number;y:number}|null>(null);
 const views=sheet?.views||[];
 useEffect(()=>{if(lightbox===null)return;const key=(e:KeyboardEvent)=>{if(e.key==='Escape')setLightbox(null);else if(e.key==='ArrowRight')setLightbox(i=>i===null?i:(i+1)%views.length);else if(e.key==='ArrowLeft')setLightbox(i=>i===null?i:(i-1+views.length)%views.length)};window.addEventListener('keydown',key);document.body.style.overflow='hidden';return()=>{window.removeEventListener('keydown',key);document.body.style.overflow=''}},[lightbox,views.length]);
 const onCrop=useCallback((c:Crop)=>setCrop(c),[]);
 useEffect(()=>{const abort=new AbortController();fetch('/casa-angel/structure/manifest.json',{signal:abort.signal}).then(r=>{if(!r.ok)throw Error('No se pudo cargar la estructura.');return r.json() as Promise<StructureManifest>}).then(setData).catch(e=>{if(!abort.signal.aborted)setError(e.message)});return()=>abort.abort()},[]);
 const totals=useMemo(()=>data?concreteTotals(data):undefined,[data]);
 if(!data||!totals)return <p className="sheetHint">{error||'Cargando la estructura…'}</p>;
 const sheets=data.sheets||[],walls=data.concreteWalls.elements,levels=[...new Set(walls.map(w=>w.level))].sort((a,b)=>a.localeCompare(b,'es',{numeric:true}));
 const codes=new Map((data.codes||[]).map(c=>[c.code,c]));
 const hoverOn=(code?:string)=>code?{onPointerMove:(e:PointerEvent)=>{if(!e.buttons&&e.pointerType==='mouse')setHover({code,x:e.clientX,y:e.clientY})},onPointerLeave:()=>setHover(null)}:{};
 const codeCard=(code:string)=>{const c=codes.get(code);return <article key={code} className="openingCard" {...hoverOn(code)}><header><span className="openingTag">{code}</span><small>{c?.kind==='MH'?'Muro de hormigón':c?.kind==='LO'?'Losa':c?.kind==='PL'?'Platea':c?.kind==='VE'?'Viga / encadenado':code.startsWith('MC-')?'Muro cortina (Aberturas)':''}</small></header>{c?<><p className="openingSize">{c.label.split(' · ').slice(1).join(' · ')||c.label}</p><p className="openingSub">{[c.area_m2!=null?n2(c.area_m2)+' m²':'',c.volume_m3!=null?n2(c.volume_m3)+' m³':''].filter(Boolean).join(' · ')}</p>{c.status&&<p className={/confirmar/i.test(c.status)?'openingAlert':'openingSub'}>{c.status}</p>}{(()=>{const f=sheets.find(s=>s.element===code);return f&&f!==sheet?<div className="openingLinks"><button onClick={()=>{setSheet(f);setLightbox(null);setHover(null);window.scrollTo({top:0})}}>Ver ficha de {code} ↗</button></div>:null})()}</>:<p className="openingSub">Sin ficha en este rubro.</p>}</article>};
 const tooltip=hover&&codes.get(hover.code)?<div role="tooltip" className="openingTooltip" style={{left:Math.min(hover.x+16,window.innerWidth-340),top:Math.max(8,hover.y-40)}}><strong><span className="openingTag">{hover.code}</span></strong><small>{codes.get(hover.code)!.label}</small>{codes.get(hover.code)!.volume_m3!=null&&<small>{n2(codes.get(hover.code)!.volume_m3!)} m³ de hormigón</small>}{codes.get(hover.code)!.status&&<small>{codes.get(hover.code)!.status}</small>}</div>:null;
 const wallCard=(w:Wall)=><article key={w.id} className="openingCard" {...hoverOn(w.code)}><header><span className="openingTag">{w.code}</span><small>{w.type}</small></header><p className="openingSize">{m(w.length_m)} × {m(w.height_m)} m</p><p className="openingSub">Espesor {m(w.thickness_m)} m · {n2(w.area_m2)} m² · <b>{n2(w.volume_m3)} m³</b></p><p className="openingSub">{w.topConstraint?`Sube hasta ${w.topConstraint}`:''}{w.baseOffset_m?` · arranca a ${m(w.baseOffset_m)} m del nivel`:''}</p>{(()=>{const f=sheets.find(s=>s.element===w.code);return f?<div className="openingLinks"><button onClick={()=>{setSheet(f);setLightbox(null);setHover(null);window.scrollTo({top:0})}}>Ver ficha (planta, vista, detalle y axonométrica) ↗</button></div>:null})()}</article>;

 if(sheet)return <section className="openingsDesk sheetExplorer">
  <div className="sheetHeading"><div><p className="eyebrow">CASA ÁNGEL / ESTRUCTURA</p><h3>{sheet.title}</h3><p>{sheet.number}</p></div><button className="sheetBack" onClick={()=>setSheet(null)}><ArrowLeft size={15}/>Todas las láminas</button></div>
  <div className="sheetTabs"><span className="openingTabHint">{views.length?'Tocá un dibujo para ampliarlo':'Lámina exportada de Revit'}</span>{sheet.pdf&&<a href={sheet.pdf} target="_blank" rel="noreferrer">PDF de la lámina <Download size={14}/></a>}{sheet.sheetId&&<RevitOpenButton id={sheet.sheetId} label="Abrir en Revit"/>}</div>
  <div className="sheetCanvas openingSheet" style={{aspectRatio:String(2383.94/1683.78)}}>{sheet.preview&&<img className="openingPreview" src={sheet.preview} alt="" aria-hidden="true"/>}<VectorImage src={sheet.image} alt={'Lámina '+sheet.title}/>{views.map((v,i)=>v.region?<button key={v.id} className="sheetHotspot" aria-label={'Ampliar '+v.name} style={{left:`${v.region[0]*100}%`,top:`${v.region[1]*100}%`,width:`${(v.region[2]-v.region[0])*100}%`,height:`${(v.region[3]-v.region[1])*100}%`}} onClick={()=>{setCrop(undefined);setLightbox(i)}}><span>{v.name} ↗</span></button>:null)}</div>
  {sheet.rebar&&<p className="openingPendingLine">{sheet.rebar}</p>}
  {views.length>0&&<><h4 className="openingGroupTitle">Dibujos de esta lámina</h4><div className="projectViewCards openingViewCards">{views.map((v,i)=><button key={v.id} onClick={()=>{setCrop(undefined);setLightbox(i)}}><span className="openingViewPreview"><TrimmedDrawing src={v.image} alt={v.name}/></span><span className="psViewCardCopy"><strong>{v.name}</strong><small>Escala 1:{v.scale}{v.dimensions?.length?` · ${v.dimensions.length} cotas`:''}</small><span>Ampliar ↗</span></span></button>)}</div></>}
  {(()=>{const tagged=[...new Set(views.flatMap(v=>v.tags||[]))];return tagged.length>0&&<><h4 className="openingGroupTitle">Elementos de esta lámina <small>{tagged.length}</small></h4><div className="openingCards">{tagged.map(codeCard)}</div></>})()}
  {lightbox!==null&&views[lightbox]&&(()=>{const v=views[lightbox];return <div className="openingLightbox" role="dialog" aria-modal="true" aria-label={'Dibujo ampliado · '+v.name}>
   <div className="openingLightboxMain"><DrawingViewport aspect={crop?.aspect||1.4} identity={v.id} controls={<div className="openingLightboxBar"><strong>{v.name}</strong><span>1:{v.scale} · {sheet.number}</span><button onClick={()=>{setCrop(undefined);setLightbox((lightbox-1+views.length)%views.length)}} aria-label="Dibujo anterior">←</button><button onClick={()=>{setCrop(undefined);setLightbox((lightbox+1)%views.length)}} aria-label="Dibujo siguiente">→</button></div>}><div className="openingHoverArea"><TrimmedDrawing key={v.id} src={v.image} alt={v.name} onCrop={onCrop} boxes={v.elements} onBox={(code,x,y)=>setHover(code?{code,x,y}:null)}/></div></DrawingViewport></div>
   <aside className="openingLightboxSide"><button className="openingLightboxClose" onClick={()=>setLightbox(null)}>Cerrar · Esc</button>{v.dimensions?.length?<section className="openingViewDims"><h5>Cotas de este dibujo</h5>{v.dimensions.map((d,i)=><p key={i}>{d.label}: <b>{d.values_m.map(x=>m(x)).join(' + ')} m</b></p>)}</section>:null}{(v.tags||[]).map(codeCard)}</aside>
  </div>})()}
  {tooltip}
 </section>;

 return <section className="openingsDesk sheetExplorer" aria-label="Estructura">
  <div className="sheetHeading"><div><p className="eyebrow">CASA ÁNGEL / ESTRUCTURA</p><h3>Estructura</h3><p>{data.concreteWalls.count} muros de hormigón · {n2(totals.total)} m³ de hormigón modelado · {data.reviewCases.length} casos para revisar.</p></div></div>
  <div className="sheetTabs">{TABS.map(([t,label])=><button key={t} aria-pressed={tab===t} onClick={()=>setTab(t)}>{label}</button>)}</div>

  {tab==='laminas'&&(sheets.length?groupStructureSheets(sheets).map(g=><section key={g.title} className="openingGroup"><h4 className="openingGroupTitle">{g.title} <small>{g.sheets.length} {g.sheets.length===1?'lámina':'láminas'}</small></h4><div className="sheetGrid">{g.sheets.map(s=><button key={s.number} className="sheetCard" onClick={()=>{setSheet(s);setLightbox(null);window.scrollTo({top:0})}}>{s.thumbnail?<img src={s.thumbnail} alt={'Lámina '+s.title} loading="lazy"/>:<div className="openingNoThumb">Sin vista previa</div>}<span className="sheetHoverTitle" aria-hidden="true">{s.title}</span><span><small>{s.number}</small><strong>{(s.element&&codes.get(s.element)?.label)||s.title}</strong><span className="openingCodes">{[...new Set((s.views||[]).flatMap(v=>v.tags||[]))].slice(0,8).map(c=><b key={c}>{c}</b>)}</span><em>{(s.views||[]).length} dibujos</em></span></button>)}</div></section>)
   :<><p className="openingPendingLine">Las láminas de estructura se están preparando en Revit con el mismo formato que Aberturas: cada muro con su código y medidas. Aparecen acá en cuanto se publiquen.</p>
    <div className="openingCards">{data.proposal.sheets.map(s=><article key={s.number} className="openingCard"><header><span className="openingTag">{s.number}</span><small>En preparación</small></header><strong>{s.title.split(' · ')[0]}</strong><p className="openingSub">{s.title.split(' · ').slice(1).join(' · ')}</p></article>)}</div></>)}

  {tab==='computo'&&<section className="openingBudget">
   <div className="openingTotals">{([['Muros de hormigón',totals.parts.walls,`${data.concreteWalls.count} muros · ${n2(data.concreteWalls.totals.length_m)} m`],['Losas (capa de hormigón)',totals.parts.losas,`${totals.losasByLevel.reduce((n,l)=>n+l.count,0)} losas`],['Platea',totals.parts.platea,`${n2(totals.platea.area)} m² · 15 cm`],['Total',totals.total,'hormigón modelado']] as const).map(([label,v,sub])=><div key={label} className={label==='Total'?'total':''}><small>{label}</small><strong>{n2(v)} m³</strong><span>{sub}</span></div>)}</div>
   <p className="openingSub">Volúmenes de Revit, sin desperdicio ni armaduras (el modelo no tiene hierro). Las losas suman solo su capa de hormigón; {totals.withoutConcrete.count} paquetes de piso ({n2(totals.withoutConcrete.area)} m²) no tienen capa de hormigón y no suman.</p>
   <table className="openingBudgetTable"><thead><tr><th>Partida</th><th>Nivel</th><th>Cant.</th><th>Superficie</th><th>Hormigón</th></tr></thead><tbody>
    {totals.wallsByLevel.map(l=><tr key={'w'+l.level}><td><b>Muros de hormigón 20 cm</b><small>{n2(l.length)} m de muro</small></td><td>{l.level}</td><td>{l.count}</td><td>{n2(l.area)} m²</td><td><b>{n2(l.volume)} m³</b></td></tr>)}
    {totals.losasByLevel.map(l=><tr key={'l'+l.level}><td><b>Losas</b><small>capa de hormigón</small></td><td>{l.level}</td><td>{l.count}</td><td>{n2(l.area)} m²</td><td><b>{n2(l.volume)} m³</b></td></tr>)}
    <tr><td><b>Platea de fundación</b><small>15 cm</small></td><td>00. Planta Baja</td><td>1</td><td>{n2(totals.platea.area)} m²</td><td><b>{n2(totals.platea.volume)} m³</b></td></tr>
   </tbody></table>
   {data.warnings.byText.some(w=>/floors overlap/i.test(w.text))&&<p className="openingAlert">⚠ Revit marca losas o pisos superpuestos: verificar que la losa de Planta Baja no se superponga con la platea antes de pedir precio.</p>}
   <h4 className="openingGroupTitle">Otros elementos (no suman al hormigón)</h4>
   <table className="openingBudgetTable"><thead><tr><th>Elemento</th><th>Cant.</th><th>Largo</th><th>Volumen</th></tr></thead><tbody>
    {data.otherStructuralWalls.map(g=><tr key={g.key}><td><b>{g.key.split(' | ')[0]}</b><small>{g.key.split(' | ')[1]} · material a confirmar</small></td><td>{g.count}</td><td>{n2(g.length_m)} m</td><td>{n2(g.volume_m3)} m³</td></tr>)}
    {data.framing.byType.map(g=><tr key={g.key}><td><b>{g.key}</b><small>madera de cubierta</small></td><td>{g.count}</td><td>{n2(g.length_m)} m</td><td>{n2(g.volume_m3)} m³</td></tr>)}
   </tbody></table>
  </section>}

  {tab==='muros'&&levels.map(level=><section key={level} className="openingGroup"><h4 className="openingGroupTitle">{level} <small>{walls.filter(w=>w.level===level).length} muros</small></h4><div className="openingCards">{walls.filter(w=>w.level===level).map(wallCard)}</div></section>)}

  {tab==='revision'&&groupCases(data.reviewCases).map(g=><section key={g.title} className="openingGroup"><h4 className="openingGroupTitle">{g.title} <small>{g.rows.length}</small></h4><div className="openingCards">{g.rows.map(c=><article key={c.id} className="openingCard"><header>{c.codes.slice(0,3).map(code=><span key={code} className="openingTag">{code}</span>)}</header><p className="openingSub">{c.title.startsWith('Solape')?'Revit marca un encuentro a revisar entre estos elementos.':c.observation}</p><p className="openingAlert">Qué hacer: {c.proposedCorrection}</p></article>)}</div></section>)}

  {tab==='pendientes'&&<section className="openingGroup">
   <h4 className="openingGroupTitle">Decisiones tomadas (opción recomendada)</h4><ul className="structureList">{(data.decisions||DECISIONS).map(d=><li key={d}>{d}</li>)}</ul>{data.codesWrittenToModel===false&&<p className="openingPendingLine">❓ Falta tu OK: ¿escribimos los códigos (MH-, LO-, PL-, VE-) en el parámetro Mark del modelo de Revit? Hoy están solo en las láminas y en la oficina.</p>}
   <h4 className="openingGroupTitle">No está en el modelo</h4><ul className="structureList">{data.notModeled.map(t=><li key={t}>{t}</li>)}</ul>
   <h4 className="openingGroupTitle">Avisos de Revit</h4><ul className="structureList">{data.warnings.byText.map(w=><li key={w.text}><b>{w.count}</b> · {plainWarning(w.text)}</li>)}</ul>
  </section>}
  <small className="sheetHint">Modelo {data.model} · lectura {new Date(data.readAt).toLocaleDateString('es-AR')} · {data.revision}</small>
  {tooltip}
 </section>;
}
