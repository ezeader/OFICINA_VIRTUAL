'use client';
import {useEffect,useMemo,useState} from 'react';
import {useRubroViewer,type RubroSheet} from './rubro-viewer';
import {concreteTotals,groupCases,groupStructureSheets,plainWarning,structureBudget,type StructureManifest,type Wall} from '../lib/structure';
import './sanitary-sheets.css';
import './openings-desk.css';

type Tab='laminas'|'computo'|'muros'|'revision'|'pendientes';
const TABS:[Tab,string][]=[['laminas','Láminas'],['computo','Cómputo y partidas'],['muros','Muros de hormigón'],['revision','Revisión pendiente'],['pendientes','Qué falta definir']];
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
 const [data,setData]=useState<StructureManifest>(),[error,setError]=useState(''),[tab,setTab]=useState<Tab>('laminas');
 useEffect(()=>{const abort=new AbortController();fetch('/casa-angel/structure/manifest.json',{signal:abort.signal}).then(r=>{if(!r.ok)throw Error('No se pudo cargar la estructura.');return r.json() as Promise<StructureManifest>}).then(setData).catch(e=>{if(!abort.signal.aborted)setError(e.message)});return()=>abort.abort()},[]);
 const totals=useMemo(()=>data?concreteTotals(data):undefined,[data]),lines=useMemo(()=>data?structureBudget(data):[],[data]);
 const concrete=lines.filter(l=>l.unit==='m³'&&!l.informative).reduce((n,l)=>n+l.quantity,0);
 const viewer=useRubroViewer({rubro:'Estructura',sheets:(data?.sheets||[]) as RubroSheet[],codes:data?.codes||[],kindLabel:(code,kind)=>kind==='MH'?'Muro de hormigón':kind==='LO'?'Losa':kind==='PL'?'Platea':kind==='VE'?'Viga / encadenado':code.startsWith('MC-')?'Muro cortina (Aberturas)':''});
 if(!data||!totals)return <p className="sheetHint">{error||'Cargando la estructura…'}</p>;
 if(viewer.page)return viewer.page;
 const sheets=data.sheets||[],walls=data.concreteWalls.elements,levels=[...new Set(walls.map(w=>w.level))].sort((a,b)=>a.localeCompare(b,'es',{numeric:true}));
 const wallCard=(w:Wall)=>viewer.codeCard(w.code,<><p className="openingSub">{m(w.length_m)} × {m(w.height_m)} m · espesor {m(w.thickness_m)} m · <b>{n2(w.volume_m3)} m³</b></p><p className="openingSub">{w.topConstraint?`Sube hasta ${w.topConstraint}`:''}{w.baseOffset_m?` · arranca a ${m(w.baseOffset_m)} m del nivel`:''}</p></>);

 return <section className="openingsDesk sheetExplorer" aria-label="Estructura">
  <div className="sheetHeading"><div><p className="eyebrow">CASA ÁNGEL / ESTRUCTURA</p><h3>Estructura</h3><p>{data.concreteWalls.count} muros de hormigón · {n2(concrete)} m³ de hormigón · {data.reviewCases.length} casos para revisar.</p></div></div>
  <div className="sheetTabs">{TABS.map(([t,label])=><button key={t} aria-pressed={tab===t} onClick={()=>setTab(t)}>{label}</button>)}</div>

  {tab==='laminas'&&(sheets.length?viewer.grid(groupStructureSheets(sheets as RubroSheet[]))
   :<><p className="openingPendingLine">Las láminas de estructura se están preparando en Revit con el mismo formato que Aberturas: cada muro con su código y medidas. Aparecen acá en cuanto se publiquen.</p>
    <div className="openingCards">{data.proposal.sheets.map(s=><article key={s.number} className="openingCard"><header><span className="openingTag">{s.number}</span><small>En preparación</small></header><strong>{s.title.split(' · ')[0]}</strong><p className="openingSub">{s.title.split(' · ').slice(1).join(' · ')}</p></article>)}</div></>)}

  {tab==='computo'&&<section className="openingBudget">
   <h4 className="openingGroupTitle">Partidas para el presupuesto <small>van a Presupuesto por rubro con estos ids</small></h4>
   <table className="openingBudgetTable"><thead><tr><th>Partida</th><th>Cantidad</th><th>Detalle</th></tr></thead><tbody>
    {lines.map(l=><tr key={l.id}><td><b>{l.label}</b><small>estructura:{l.id}{l.informative?' · referencia, no se cotiza':''}</small></td><td><b>{n2(l.quantity)} {l.unit}</b></td><td><small>{l.detail}</small></td></tr>)}
   </tbody></table>
   <p className="openingSub">El acero es una estimación por cuantía (el modelo no tiene armaduras): se reemplaza por la planilla del calculista. Muros de fachada y bajo escalera van en Albañilería, los del vaso en Pileta, la base de acceso en Exteriores y la madera del techo en Cubierta.</p>
   <h4 className="openingGroupTitle">Hormigón por nivel</h4>
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
    {data.otherStructuralWalls.filter(g=>!/^viga/i.test(g.key)).map(g=><tr key={g.key}><td><b>{g.key.split(' | ')[0]}</b><small>{g.key.split(' | ')[1]} · {/pileta/i.test(g.key)?'va en Pileta':/fachada|escalera/i.test(g.key)?'va en Albañilería':'material a confirmar'}</small></td><td>{g.count}</td><td>{n2(g.length_m)} m</td><td>{n2(g.volume_m3)} m³</td></tr>)}
    {data.framing.byType.map(g=><tr key={g.key}><td><b>{g.key}</b><small>madera · va en Cubierta</small></td><td>{g.count}</td><td>{n2(g.length_m)} m</td><td>{n2(g.volume_m3)} m³</td></tr>)}
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
  {viewer.tooltip}
 </section>;
}
