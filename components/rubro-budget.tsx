'use client';
// Presupuesto por rubro: lee los cómputos que publica Revit para el proyecto (manifest por rubro),
// los cruza con los precios unitarios que carga el estudio o un proveedor y arma base + opcionales.
import {useEffect,useMemo,useState} from 'react';
import {Download,Upload} from 'lucide-react';
import {RUBROS,type RubroManifest} from '../lib/rubros';
import {budgetTotals,type BudgetItem} from '../lib/openings-budget';
import {structureBudget,type StructureManifest} from '../lib/structure';
import {csv,exportCsv,systems} from '../lib/procurement';
import {computeBudget,budgetSheet,globalId,linesFromManifest,manifestStatus,pricesFromRows,sanitaryLines,type RubroBudgetState,type RubroSource} from '../lib/rubro-budget';

// Dónde publica cada proyecto sus cómputos. Un proyecto nuevo solo necesita su carpeta con el mismo contrato.
export const PROJECT_SOURCES:Record<string,{base:string;sanitary?:string}>={angel:{base:'/casa-angel',sanitary:'Casa-Angel-sanitarias-R02-datos.json'}};
const GOAL='fin de 2026';
const KIND:Record<string,string>={Windows:'Ventana',Doors:'Puerta','Curtain Walls':'Muro cortina'};
const n2=(n:number)=>n.toLocaleString('es-AR',{maximumFractionDigits:2});
const pct=(n?:number)=>n==null?'—':(n*100).toLocaleString('es-AR',{maximumFractionDigits:1})+' %';
const STATUS={modelado:'Modelado en Revit',propuesta:'Propuesta a confirmar',estimacion:'Estimación (sin modelo)','sin-computo':'Sin cómputo'};
const get=<T,>(url:string)=>fetch(url).then(r=>r.ok?r.json() as Promise<T>:null).catch(()=>null);

async function loadSources({base,sanitary}:{base:string;sanitary?:string}):Promise<RubroSource[]>{
 const [san,open,str,...rubros]=await Promise.all([
  get<{rows:{group:string;type?:string;diameter_mm?:number;length_model_m?:number}[]}>(`${base}/${sanitary||'rubros/sanitaria/datos.json'}`),
  get<{items:BudgetItem[]}>(`${base}/openings/manifest.json`),
  get<StructureManifest>(`${base}/structure/manifest.json`),
  ...RUBROS.map(r=>get<RubroManifest>(`${base}/rubros/${r.key}/manifest.json`))]);
 const sources:RubroSource[]=[];
 const sanLines=san?sanitaryLines(san.rows,systems):[];
 sources.push({key:'sanitaria',name:'Sanitarias',status:sanLines.length?'modelado':'sin-computo',lines:sanLines,note:'Cañerías: metros reales del modelo. Artefactos y accesorios se cotizan aparte o en el global.'});
 const ob=open?budgetTotals(open.items):null;
 sources.push({key:'aberturas',name:'Aberturas',status:ob?'modelado':'sin-computo',lines:(ob?.rows||[]).map(r=>({id:`aberturas:${r.key}`,label:`${KIND[r.category]||r.category} ${r.type} · ${r.size.replace(/\./g,',')}`,quantity:r.count,unit:'u',detail:`${n2(r.area)} m² · ${r.codes.join(' ')}`}))});
 const sl=str?structureBudget(str):[];
 sources.push({key:'estructura',name:'Estructura',status:sl.length?'modelado':'sin-computo',note:'Hormigón del modelo por elemento. Acero estimado por cuantía (el modelo no tiene armaduras) y encofrado por caras a moldear.',lines:sl.map(l=>({...l,id:`estructura:${l.id}`}))});
 RUBROS.forEach((r,i)=>{const m=rubros[i];sources.push({key:r.key,name:r.name,status:manifestStatus(m),lines:m?linesFromManifest(r.key,m):[],note:m?.quantityNote})});
 return sources;
}

export default function RubroBudget({project,projectName,value,disabled,onSave,onDocumentation}:{project:string;projectName:string;value?:RubroBudgetState;disabled:boolean;onSave:(v:RubroBudgetState,message:string)=>Promise<boolean>;onDocumentation:()=>void}){
 const source=PROJECT_SOURCES[project];
 const [sources,setSources]=useState<RubroSource[]|null>(),[open,setOpen]=useState(''),[draft,setDraft]=useState<Record<string,string>>({}),[error,setError]=useState('');
 useEffect(()=>{setSources(undefined);if(!source){setSources(null);return}let ignore=false;loadSources(source).then(s=>{if(!ignore)setSources(s)});return()=>{ignore=true}},[source]);
 const state=value||{},currency=state.currency||'ARS';
 const result=useMemo(()=>sources?computeBudget(sources,state):null,[sources,state]);
 const money=(n:number)=>n.toLocaleString('es-AR',{style:'currency',currency,minimumFractionDigits:0,maximumFractionDigits:0});
 const save=(next:RubroBudgetState,text:string)=>onSave({...next,updatedAt:new Date().toISOString()},text);
 if(sources===undefined)return <p className="pcHint">Leyendo los cómputos publicados de {projectName}…</p>;
 if(!sources||!result)return <div className="pcEmpty"><h3>{projectName} todavía no publicó cómputos desde Revit</h3><p>Cuando el modelo publique sus rubros (un manifest por rubro con totales y cantidades), acá aparece el presupuesto por rubro con la misma estructura que Casa Ángel.</p></div>;
 const p=result.progress;
 async function savePrices(rubro:string){
  const prices={...state.prices};
  for(const [id,text] of Object.entries(draft)){if(!id.startsWith(rubro+':'))continue;if(!text.trim()){delete prices[id];continue}const n=Number(text.includes(',')?text.replace(/\./g,'').replace(',','.'):text);if(!Number.isFinite(n)||n<0||n>1e12){setError('Revisá los precios: números sin símbolos.');return}prices[id]=n}
  setError('');if(await save({...state,prices},'Precios guardados.'))setDraft(d=>Object.fromEntries(Object.entries(d).filter(([k])=>!k.startsWith(rubro+':'))));
 }
 function download(){const url=URL.createObjectURL(new Blob([exportCsv(budgetSheet(result!))],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=`${project}-presupuesto-por-rubro.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
 async function upload(file?:File){if(!file)return;try{const known=new Set(result!.rubros.flatMap(r=>[globalId(r.key),...r.lines.map(l=>l.id)]));const prices=pricesFromRows(csv(await file.text()),known);if(!Object.keys(prices).length)throw Error('La planilla no tiene precios cargados.');setError('');await save({...state,prices:{...state.prices,...prices}},`${Object.keys(prices).length} precios importados.`)}catch(e){setError((e as Error).message)}}
 const row=(r:typeof result.rubros[number])=><tr key={r.key}>
  <td><button className="pcLink" onClick={()=>setOpen(open===r.key?'':r.key)} aria-expanded={open===r.key}><b>{r.name}</b></button><small>{STATUS[r.status]}{r.lines.some(l=>!l.skipped)?` · ${r.lines.filter(l=>!l.skipped).length} ${r.lines.filter(l=>!l.skipped).length===1?'partida':'partidas'}`:''}</small></td>
  <td>{r.subtotal>0?<b>{money(r.subtotal)}</b>:'—'}{r.global!=null&&<small>cotización global</small>}</td>
  <td>{r.optional?(r.share!=null?`+${pct(r.share)}`:'—'):pct(r.share)}</td>
  <td>{r.complete?<span className="pcBadge">Con precio</span>:<small>{!r.lines.some(l=>!l.skipped)?'Falta precio global':r.missing===1?'Falta 1 precio':`Faltan ${r.missing} precios`}</small>}</td>
  <td><button disabled={disabled} onClick={()=>save({...state,optional:{...state.optional,[r.key]:!r.optional}},r.optional?`${r.name} pasa a la base.`:`${r.name} pasa a opcionales.`)}>{r.optional?'Pasar a base':'Hacer opcional'}</button></td>
 </tr>;
 const detail=open?result.rubros.find(r=>r.key===open):undefined;
 const panel=detail?<div className="pcPanel" aria-label={`Partidas de ${detail.name}`}>
   <div className="pcSectionHead"><div><h3>{detail.name} · partidas</h3><p>{detail.note||STATUS[detail.status]}{detail.status==='estimacion'?' Cantidades estimadas: el rubro todavía no está modelado.':detail.status==='propuesta'?' Cantidades de una propuesta que todavía tenés que confirmar.':''}</p></div><button onClick={()=>setOpen('')}>Cerrar</button></div>
   <div className="pcTableWrap"><table><thead><tr><th>Partida</th><th>Cantidad</th><th>Precio unitario</th><th>Subtotal</th><th>Se cotiza</th></tr></thead><tbody>
    <tr><td><b>Global del rubro</b><small>cotización cerrada; si se completa, reemplaza a las partidas</small></td><td>1 gl</td><td><input inputMode="decimal" aria-label={`Precio global de ${detail.name}`} placeholder={detail.global!=null?String(detail.global):'—'} value={draft[globalId(detail.key)]??''} onChange={e=>setDraft({...draft,[globalId(detail.key)]:e.target.value})}/></td><td>{detail.global!=null?money(detail.global):'—'}</td><td></td></tr>
    {detail.lines.map(l=><tr key={l.id} className={l.skipped?'rbSkipped':''}><td><b>{l.label}</b>{l.detail&&<small>{l.detail}</small>}</td><td>{n2(l.quantity)} {l.unit}</td><td>{l.skipped?<small>informativo</small>:<input inputMode="decimal" aria-label={`Precio unitario de ${l.label}`} placeholder={l.price!=null?String(l.price):'por cotizar'} value={draft[l.id]??''} onChange={e=>setDraft({...draft,[l.id]:e.target.value})}/>}</td><td>{l.amount!=null?money(l.amount):'—'}</td><td><input type="checkbox" aria-label={`Cotizar ${l.label}`} checked={!l.skipped} disabled={disabled} onChange={()=>save({...state,skip:{...state.skip,[l.id]:!l.skipped}},l.skipped?'La partida se cotiza.':'La partida queda como información.')}/></td></tr>)}
   </tbody></table></div>
   {!detail.lines.length&&<p className="pcHint">Este rubro todavía no tiene cómputo: cargá una cotización global o respondé sus preguntas en Documentación para que se diseñe y compute.</p>}
   <div className="pcActions"><button className="primary" disabled={disabled||!Object.keys(draft).some(k=>k.startsWith(detail.key+':'))} onClick={()=>savePrices(detail.key)}>Guardar precios de {detail.name}</button><small>Precio por unidad, sin separador de miles. Para quitar un precio, borralo y guardá.</small></div>
  </div>:null;
 return <div className="rbBudget">
  <div className="rbVision" aria-label="Del modelo al presupuesto">{[['1','Modelo de Revit','publica cada rubro'],['2','Cómputo por rubro',`${p.withCompute} de ${p.rubros} rubros (${p.modeled} modelados)`],['3','Precios unitarios',`${p.pricedLines} de ${p.lines} partidas`],['4','Presupuesto por rubro',`${p.priced} de ${p.rubros} con precio`],['5','Total para el cliente','base + opcionales']].map(([n,t,s])=><span key={n}><b>{n}</b>{t}<small>{s}</small></span>)}</div>
  <p className="pcHint">Meta: cómputo y presupuesto casi completo de {projectName} a {GOAL}. Ningún monto se inventa: cada precio lo carga el estudio o un proveedor.</p>
  {error&&<p className="pcError" role="alert">{error}<button onClick={()=>setError('')}>Cerrar</button></p>}
  <div className="pcStats">
   <div><small>Obra base · para arrancar</small><strong>{result.baseTotal>0?money(result.baseTotal):'Por cotizar'}</strong><small>{result.baseComplete?'Todos los rubros base tienen precio.':`${result.base.filter(r=>!r.complete).length} de ${result.base.length} rubros base sin precio completo`}</small></div>
   <div><small>Opcionales · ahora o más adelante</small><strong>{result.optionalTotal>0?money(result.optionalTotal):'Por cotizar'}</strong><small>{result.baseTotal>0&&result.optionalTotal>0?`+${pct(result.optionalTotal/result.baseTotal)} sobre la base`:result.optional.map(r=>r.name).join(' · ')||'Ninguno'}</small></div>
   <div><small>Total con opcionales</small><strong>{result.total>0?money(result.total):'Por cotizar'}</strong><small>Moneda <select aria-label="Moneda del presupuesto" value={currency} disabled={disabled} onChange={e=>save({...state,currency:e.target.value as 'ARS'|'USD'},'Moneda actualizada.')}><option>ARS</option><option>USD</option></select></small></div>
  </div>
  <div className="pcActions"><button onClick={download}><Download size={15}/>Descargar planilla de precios</button><label className="pcFile">Importar precios (misma planilla)<input type="file" accept=".csv,text/csv" disabled={disabled} onChange={e=>{upload(e.target.files?.[0]);e.target.value=''}}/></label><button onClick={onDocumentation}>Ver documentación</button></div>
  {[['Obra base',result.base,'% de la base'],['Opcionales',result.optional,'suma a la base']].map(([title,rows,label])=><div key={title as string}><div className="pcSectionHead"><h2>{title as string}</h2></div><div className="pcTableWrap"><table><thead><tr><th>Rubro</th><th>Subtotal</th><th>{label as string}</th><th>Qué falta</th><th></th></tr></thead><tbody>{(rows as typeof result.base).map(row)}</tbody></table></div>{detail&&(rows as typeof result.base).includes(detail)&&panel}</div>)}
  </div>;
}
