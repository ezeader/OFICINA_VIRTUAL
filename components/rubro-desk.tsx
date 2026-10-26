'use client';
// Mesa estándar de un rubro de documentación. Lee /casa-angel/rubros/<clave>/manifest.json (contrato en lib/rubros.ts)
// y lo muestra con el formato de Sanitarias: láminas, cómputo, elementos y lo que falta definir.
import {useEffect,useState} from 'react';
import {FileText} from 'lucide-react';
import {useRubroViewer} from './rubro-viewer';
import {groupRubroLevels,type RubroManifest,type RubroInfo} from '../lib/rubros';

type Tab='laminas'|'computo'|'elementos'|'pendientes';
const n2=(n:number)=>n.toLocaleString('es-AR',{minimumFractionDigits:2,maximumFractionDigits:2});

// base y project permiten usar la misma mesa en otros proyectos (p. ej. /urbetrack/rubros, «Oficinas Urbetrack»).
export default function RubroDesk({rubro,base='/casa-angel/rubros',project='Casa Ángel'}:{rubro:RubroInfo;base?:string;project?:string}){
 const [data,setData]=useState<RubroManifest|null>(),[tab,setTab]=useState<Tab>('laminas');
 useEffect(()=>{setData(undefined);const abort=new AbortController();fetch(`${base}/${rubro.key}/manifest.json`,{signal:abort.signal}).then(r=>r.ok?r.json() as Promise<RubroManifest>:null).then(setData).catch(()=>{if(!abort.signal.aborted)setData(null)});return()=>abort.abort()},[base,rubro.key]);
 const kindLabel=(code:string,kind?:string)=>(kind&&data?.kinds?.[kind])||'';
 const viewer=useRubroViewer({rubro:rubro.name,project,sheets:data?.sheets||[],codes:data?.codes||[],kindLabel});
 if(data===undefined)return <p className="sheetHint">Cargando {rubro.name.toLowerCase()}…</p>;
 if(data===null)return <section className="openingsDesk sheetExplorer"><div className="docPending"><FileText size={27}/><h3>{rubro.name} · por preparar</h3><p>{rubro.pending}</p></div></section>;
 if(viewer.page)return viewer.page;
 const sheets=data.sheets||[],codes=data.codes||[];
 const kinds=[...new Set(codes.map(c=>c.kind||''))];
 const tabs:[Tab,string,number][]=[['laminas','Láminas',sheets.length],['computo','Cómputo',(data.quantities||[]).length+(data.totals||[]).length],['elementos','Elementos',codes.length],['pendientes','Qué falta definir',(data.notModeled||[]).length+(data.decisions||[]).length+(data.questions||[]).length]];
 // Sin láminas (rubro a definir) se abre en las preguntas: primero hay que decidir.
 const shown=tabs.some(([t,,n])=>t===tab&&n)&&!(sheets.length===0&&tab==='laminas')?tab:sheets.length===0&&tabs[3][2]?'pendientes':(tabs.find(([,,n])=>n)?.[0]||'laminas');
 return <section className="openingsDesk sheetExplorer" aria-label={rubro.name}>
  <div className="sheetHeading"><div><p className="eyebrow">{project.toUpperCase()} / {rubro.name.toUpperCase()}</p><h3>{data.title||rubro.name}</h3><p>{data.summary||`${sheets.length} láminas · ${codes.length} elementos con código.`}</p></div></div>
  {data.status==='propuesta'&&<p className="openingPendingLine">✏️ Propuesta a confirmar: es un diseño para que lo revises; no es documentación de obra hasta que lo apruebes.</p>}
  {(data.questions||[]).length>0&&<p className="openingPendingLine">❓ {data.questions!.length===1?'Hay una pregunta para vos':`Hay ${data.questions!.length} preguntas para vos`} en «Qué falta definir».</p>}
  <div className="sheetTabs">{tabs.filter(([,,n])=>n).map(([t,label,n])=><button key={t} aria-pressed={shown===t} onClick={()=>setTab(t)}>{label} · {n}</button>)}</div>
  {shown==='laminas'&&(sheets.length?viewer.levels(groupRubroLevels(sheets,data.kinds)):<p className="openingPendingLine">Las láminas de este rubro se están preparando en Revit. Aparecen acá en cuanto se publiquen.</p>)}
  {shown==='computo'&&<section className="openingBudget">
   {sheets.length===0&&<p className="openingAlert">⚠ Estimación previa: este rubro todavía no está modelado. Las cantidades son hipótesis para ordenar la decisión, no un cómputo.</p>}
   {(data.totals||[]).length>0&&<div className="openingTotals">{data.totals!.map((t,i)=><div key={t.label} className={i===data.totals!.length-1&&data.totals!.length>1?'total':''}><small>{t.label}</small><strong>{n2(t.value)} {t.unit}</strong>{t.detail&&<span>{t.detail}</span>}</div>)}</div>}
   {data.quantityNote&&<p className="openingSub">{data.quantityNote}</p>}
   {(data.quantities||[]).length>0&&<table className="openingBudgetTable"><thead><tr><th>Partida</th><th>Sector</th><th>Cant.</th><th>Cantidad</th></tr></thead><tbody>{data.quantities!.map((q,i)=><tr key={i}><td><b>{q.label}</b>{q.detail&&<small>{q.detail}</small>}</td><td>{q.group||'—'}</td><td>{q.count??'—'}</td><td><b>{n2(q.value)} {q.unit}</b></td></tr>)}</tbody></table>}
  </section>}
  {shown==='elementos'&&kinds.map(k=><section key={k} className="openingGroup"><h4 className="openingGroupTitle">{data.kinds?.[k]||k||'Elementos'} <small>{codes.filter(c=>(c.kind||'')===k).length}</small></h4><div className="openingCards">{codes.filter(c=>(c.kind||'')===k).map(c=>viewer.codeCard(c.code))}</div></section>)}
  {shown==='pendientes'&&<section className="openingGroup">
   {(data.questions||[]).length>0&&<><h4 className="openingGroupTitle">Preguntas para vos</h4><ul className="structureList">{data.questions!.map(q=><li key={q}>{q}</li>)}</ul></>}
   {(data.decisions||[]).length>0&&<><h4 className="openingGroupTitle">Decisiones tomadas (opción recomendada)</h4><ul className="structureList">{data.decisions!.map(d=><li key={d}>{d}</li>)}</ul></>}
   {(data.notModeled||[]).length>0&&<><h4 className="openingGroupTitle">No está en el modelo</h4><ul className="structureList">{data.notModeled!.map(t=><li key={t}>{t}</li>)}</ul></>}
  </section>}
  {data.model&&<small className="sheetHint">Modelo {data.model}{data.readAt?` · lectura ${new Date(data.readAt).toLocaleDateString('es-AR')}`:''}{data.revision?` · ${data.revision}`:''}</small>}
  {viewer.tooltip}
 </section>;
}
