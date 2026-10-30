'use client';
import {useMemo,useState} from 'react';
import {RUBROS} from '@/lib/rubros';
import {QUOTE_RUBROS,NEGOTIATION_KINDS,TARGET_QUOTES,FOLLOW_UP_DAYS,compareQuote,contactLinks,emptyRubroQuotes,followUp,latestQuotes,matchSupplier,needsLabor,needsMaterial,priceHistory,quoteFromSheet,requestMail,
 type NegotiationEntry,type Quote,type QuoteSheet,type QuoteSupplier,type RubroQuotes,type SupplierKind} from '@/lib/quotes';
import {quoteFileName,quoteWorkbook} from '@/lib/quote-xlsx';
import {conditionsFromRows,readFirstSheet} from '@/lib/xlsx-read';
import type {Supplier} from '@/lib/procurement';
import SupplierDiscovery from './supplier-discovery';
import './quote-desk.css';
// El cómputo va en el código (data/cotizacion): se actualiza sin reiniciar el servidor ni publicar documentos.
import sanitariaSheet from '@/data/cotizacion/sanitaria-R13.json';
const SHEETS:Record<string,QuoteSheet>={sanitaria:sanitariaSheet as QuoteSheet};
/** Rubro de la oficina → rubro del buscador de comercios. */
const DISCOVERY_TRADE:Record<string,string>={sanitaria:'sanitarias'};
const STUDIO_ACCOUNT='ader.studio.arq@gmail.com';

export type QuoteSection='Cómputo'|'Proveedores'|'Presupuestos';
const KINDS:SupplierKind[]=['materiales','materiales + mano de obra','mano de obra'];
const GROUPS={local:'Pinamar y zona',costa:'Costa atlántica',nacional:'Nacional'} as const;
const uid=()=>crypto.randomUUID();
const today=()=>new Date().toISOString().slice(0,10);
const plusDays=(n:number)=>{const d=new Date();d.setDate(d.getDate()+n);return d.toISOString().slice(0,10)};
const dmy=(iso:string)=>iso?iso.slice(0,10).split('-').reverse().join('/'):'';
const money=(n:number,c='ARS')=>n.toLocaleString('es-AR',{style:'currency',currency:c,maximumFractionDigits:0});
const qty=(n:number)=>n.toLocaleString('es-AR',{maximumFractionDigits:1});
const parseNum=(t:string)=>{const s=t.trim();if(!s)return undefined;const n=Number(s.replace(/\./g,'').replace(',','.'));return Number.isFinite(n)&&n>=0?n:NaN};
const blankSupplier=():QuoteSupplier=>({id:uid(),name:'',kind:'materiales',group:'local',contact:'',location:'',zone:'',apto:'pendiente'});
const scopeLabel=(s:SupplierKind)=>s==='materiales + mano de obra'?'Materiales + M.O.':s==='materiales'?'Solo materiales':'Solo mano de obra';
type Save=(v:RubroQuotes,t:string)=>Promise<boolean>;

export default function QuoteDesk({section,value,disabled,onSave}:{section:QuoteSection;value?:Record<string,RubroQuotes>;disabled:boolean;onSave:(v:Record<string,RubroQuotes>,text:string)=>Promise<boolean>}){
 const [rubro,setRubro]=useState('sanitaria');
 const data=value?.[rubro]||emptyRubroQuotes(),sheet=SHEETS[rubro];
 const save:Save=(next,text)=>onSave({...value,[rubro]:next},text);
 const fu=followUp(data);
 return <section className="qd">
  <div className="qdRubros" aria-label="Rubro">{QUOTE_RUBROS.map(r=><button key={r.key} className={rubro===r.key?'active':''} onClick={()=>setRubro(r.key)}>{r.name}</button>)}
   {RUBROS.map(r=><button key={r.key} disabled title="Todavía sin cómputo por sistema">{r.name}</button>)}</div>
  {!sheet?<div className="pcEmpty"><p>Este rubro todavía no tiene cómputo por sistema.</p></div>:<>
  <p className="qdStatus"><span><b>{fu.answered}/{TARGET_QUOTES}</b> presupuestos</span><span><b>{data.suppliers.filter(s=>s.apto==='apto').length}</b> aptos</span><span><b>{data.suppliers.filter(s=>s.requestedAt).length}</b> pedidos enviados</span>
   {fu.searchMore&&<span className="qdAlert">{fu.late.length} sin respuesta hace {FOLLOW_UP_DAYS}+ días: sumar proveedores</span>}</p>
  {section==='Cómputo'&&<Computo sheet={sheet} data={data} disabled={disabled} save={save}/>}
  {section==='Proveedores'&&<Suppliers sheet={sheet} rubro={rubro} data={data} disabled={disabled} save={save}/>}
  {section==='Presupuestos'&&<Budgets sheet={sheet} data={data} disabled={disabled} save={save}/>}
  </>}
 </section>;
}

function download(bytes:Uint8Array,name:string){const url=URL.createObjectURL(new Blob([bytes as BlobPart],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}

function Computo({sheet,data,disabled,save}:{sheet:QuoteSheet;data:RubroQuotes;disabled:boolean;save:Save}){
 const brands=data.brands||{};
 const setBrands=(codes:string[],brand:string)=>{const next={...brands};for(const c of codes){if(brand.trim())next[c]=brand.trim();else delete next[c]}
  if(JSON.stringify(next)!==JSON.stringify(brands))save({...data,brands:next},brand.trim()?'Marca guardada.':'Marca quitada.')};
 const chosen=Object.keys(brands).length;
 return <>
  <div className="pcSectionHead"><div><h2>{sheet.name} · cómputo {sheet.revision}</h2><p>{sheet.count} ítems por sistema, cada uno una sola vez. {sheet.basis}</p></div>
   <div className="qdDocs"><button className="primary" onClick={()=>download(quoteWorkbook(sheet,brands),quoteFileName(sheet))}>Descargar Excel para cotizar</button><small>{chosen?`Con ${chosen} marcas elegidas`:'Sin marcas elegidas: lleva la referencia del modelo'}</small>{sheet.documents.map(d=><a key={d.url} href={d.url} target="_blank" rel="noreferrer">{d.name} ↗</a>)}</div></div>
  {sheet.systems.map(s=>{const common=s.items.every(i=>brands[i.code]&&brands[i.code]===brands[s.items[0].code])?brands[s.items[0].code]:'';const set=s.items.filter(i=>brands[i.code]).length;
   return <details key={s.key} className="qdSystem"><summary><b>{s.name}</b><span>{s.items.length} ítems{set?` · ${set} con marca`:''}</span></summary>
    <label className="qdBrandAll">Marca para todo el sistema<input key={common} defaultValue={common} placeholder={s.items.find(i=>i.ref)?.ref||'Elegí la marca'} disabled={disabled} onBlur={e=>{if(e.target.value.trim()!==common)setBrands(s.items.map(i=>i.code),e.target.value)}}/></label>
    <div className="pcTableWrap"><table><thead><tr><th>Código</th><th>Descripción</th><th>Cantidad</th><th>Marca</th></tr></thead><tbody>{s.items.map(i=><tr key={i.code}><td>{i.code}</td><td>{i.description}{i.materialOptional&&<small>Material opcional</small>}</td><td>{qty(i.quantity)} {i.unit}</td>
     <td><input className="qdBrand" key={brands[i.code]||''} defaultValue={brands[i.code]||''} placeholder={i.ref||'—'} aria-label={'Marca '+i.code} disabled={disabled} onBlur={e=>setBrands([i.code],e.target.value)}/></td></tr>)}</tbody></table></div></details>})}
  <div className="pcPanel"><h3>No incluido</h3><ul>{sheet.excluded.map(e=><li key={e}>{e}</li>)}</ul></div>
 </>;
}

function Suppliers({sheet,rubro,data,disabled,save}:{sheet:QuoteSheet;rubro:string;data:RubroQuotes;disabled:boolean;save:Save}){
 const [edit,setEdit]=useState<QuoteSupplier|null>(null),[bulk,setBulk]=useState(''),[error,setError]=useState(''),[explore,setExplore]=useState(false);
 const set=(s:QuoteSupplier,text:string)=>save({...data,suppliers:data.suppliers.some(x=>x.id===s.id)?data.suppliers.map(x=>x.id===s.id?s:x):[...data.suppliers,s]},text);
 const deadline=dmy(plusDays(7));
 async function importList(){
  setError('');try{
   const list=JSON.parse(bulk);if(!Array.isArray(list))throw Error('Pegá un listado (array JSON).');
   const known=new Set(data.suppliers.map(s=>s.name.trim().toLowerCase()));
   const add:QuoteSupplier[]=list.filter(x=>x?.name&&!known.has(String(x.name).trim().toLowerCase())).map(x=>({...blankSupplier(),name:String(x.name),kind:KINDS.includes(x.kind)?x.kind:'materiales',group:x.group in GROUPS?x.group:'local',
    contact:[x.email,x.contact||x.phone,x.web].filter(Boolean).filter((v,i,a)=>a.indexOf(v)===i).join(' · '),location:String(x.location||''),zone:String(x.zone||'no informado'),source:x.source?String(x.source):undefined,notes:[x.notes,x.scope].filter(Boolean).join(' · ')||undefined}));
   if(await save({...data,suppliers:[...data.suppliers,...add]},`${add.length} proveedores agregados; ${list.length-add.length} ya estaban.`))setBulk('');
  }catch(e){setError((e as Error).message)}
 }
 // Lo que se encuentra en el mapa entra a la lista del rubro, pendiente de tu OK.
 const fromMap=(s:Supplier)=>{const dup=data.suppliers.find(x=>x.name.trim().toLowerCase()===s.name.trim().toLowerCase());setEdit(dup?{...dup}:{...blankSupplier(),name:s.name,contact:s.contact,location:s.zone,zone:'no informado',source:s.source?.startsWith('http')?s.source:undefined,notes:s.notes});setExplore(false)};
 const groups=(Object.keys(GROUPS) as (keyof typeof GROUPS)[]).map(g=>[g,data.suppliers.filter(s=>s.group===g)] as const).filter(([,l])=>l.length);
 return <>
  <div className="pcSectionHead"><div><h2>Proveedores</h2><p>Marcá “Apto” a quienes vas a pedirles precio. Los contactos son públicos: confirmalos antes de enviar.</p></div>
   <div className="pcActions"><button onClick={()=>setExplore(!explore)}>{explore?'Cerrar mapa':'Buscar en la zona'}</button><button className="primary" disabled={disabled} onClick={()=>setEdit(blankSupplier())}>Agregar</button></div></div>
  {error&&<p className="pcError" role="alert">{error}</p>}
  {explore&&<SupplierDiscovery trade={DISCOVERY_TRADE[rubro]||'todos'} suppliers={[]} disabled={disabled} onAdd={fromMap}/>}
  {edit&&<div className="pcPanel"><h3>{data.suppliers.some(s=>s.id===edit.id)?'Editar proveedor':'Nuevo proveedor'}</h3><div className="pcFields">
   {([['name','Nombre'],['contact','Contacto (email, teléfono)'],['location','Ubicación'],['zone','Zona donde trabaja'],['source','Fuente'],['notes','Notas']] as const).map(([k,l])=><label key={k}>{l}<input value={edit[k]||''} onChange={e=>setEdit({...edit,[k]:e.target.value})}/></label>)}
   <label>Tipo<select value={edit.kind} onChange={e=>setEdit({...edit,kind:e.target.value as SupplierKind})}>{KINDS.map(k=><option key={k}>{k}</option>)}</select></label>
   <label>Grupo<select value={edit.group} onChange={e=>setEdit({...edit,group:e.target.value as QuoteSupplier['group']})}>{Object.entries(GROUPS).map(([k,l])=><option key={k} value={k}>{l}</option>)}</select></label></div>
   <div className="pcActions"><button className="primary" disabled={disabled||!edit.name.trim()} onClick={async()=>{if(await set(edit,'Proveedor guardado.'))setEdit(null)}}>Guardar</button><button onClick={()=>setEdit(null)}>Cancelar</button>
   {data.suppliers.some(s=>s.id===edit.id)&&<button disabled={disabled||data.quotes.some(q=>q.supplier===edit.id)} title="Solo sin presupuestos cargados" onClick={async()=>{if(confirm('¿Quitar '+edit.name+' del listado?')&&await save({...data,suppliers:data.suppliers.filter(s=>s.id!==edit.id),negotiation:data.negotiation.filter(n=>n.supplier!==edit.id)},'Proveedor quitado.'))setEdit(null)}}>Quitar</button>}</div></div>}
  {groups.map(([g,list])=><div key={g}><h3 className="qdGroup">{GROUPS[g]} · {list.length}</h3><div className="pcTableWrap"><table className="qdSuppliers"><thead><tr><th>Proveedor</th><th>Contacto</th><th>Ubicación</th><th>Zona</th><th>Apto</th><th>Mail</th><th/></tr></thead><tbody>
   {list.map(s=>{const m=requestMail(sheet,s,deadline),links=contactLinks(s.contact,m.subject,m.body,STUDIO_ACCOUNT);
    return <tr key={s.id} className={'qdApto-'+s.apto.replace(' ','-')}><td><b>{s.name}</b><small>{s.kind}{s.notes?' · '+s.notes:''}</small>{s.source&&<a href={s.source} target="_blank" rel="noreferrer">fuente ↗</a>}</td><td>{s.contact}</td><td>{s.location}</td><td>{s.zone}</td>
    <td><div className="qdSeg">{(['apto','pendiente','no apto'] as const).map(a=><button key={a} aria-pressed={s.apto===a} disabled={disabled} onClick={()=>set({...s,apto:a},`${s.name}: ${a}.`)}>{a==='pendiente'?'?':a==='apto'?'Apto':'No'}</button>)}</div></td>
    <td className="qdMailCell"><button className={'qdTick'+(s.requestedAt?' on':'')} disabled={disabled||(!s.requestedAt&&s.apto!=='apto')} title={s.requestedAt?'Enviado el '+dmy(s.requestedAt)+' · tocá para desmarcar':'Marcar como enviado'} aria-label={s.requestedAt?'Pedido enviado':'Marcar pedido enviado'}
      onClick={()=>set({...s,requestedAt:s.requestedAt?undefined:new Date().toISOString()},s.requestedAt?'Envío desmarcado.':'Marcado como enviado hoy.')}>{s.requestedAt?'✓':''}</button>
     {s.apto==='apto'&&!s.requestedAt&&<span className="qdSend">{links.gmail&&<a href={links.gmail} target="_blank" rel="noreferrer" title="Abre el borrador en Gmail. Adjuntá el Excel y los planos.">Gmail</a>}{links.whatsapp&&<a href={links.whatsapp} target="_blank" rel="noreferrer" title="Abre WhatsApp con el texto. Adjuntá el Excel y los planos.">WhatsApp</a>}</span>}
     {s.requestedAt&&<small>{dmy(s.requestedAt)}{s.declined?' · no cotiza':''}</small>}</td>
    <td><button disabled={disabled} onClick={()=>setEdit({...s})}>Editar</button></td></tr>})}
  </tbody></table></div></div>)}
  {!data.suppliers.length&&<div className="pcEmpty"><p>Todavía no hay proveedores para este rubro.</p></div>}
  <details className="qdMore"><summary>Importar listado</summary><p className="pcHint">Para listas que te paso en JSON (name, kind, group, contact, email, phone, location, zone, source, notes). No duplica nombres; entran pendientes de OK.</p><textarea rows={4} value={bulk} onChange={e=>setBulk(e.target.value)}/><button disabled={disabled||!bulk.trim()} onClick={importList}>Importar</button></details>
 </>;
}

function Budgets({sheet,data,disabled,save}:{sheet:QuoteSheet;data:RubroQuotes;disabled:boolean;save:Save}){
 const [sub,setSub]=useState<'Comparación'|'Negociaciones'>('Comparación');
 return <>
  <div className="qdTabs">{(['Comparación','Negociaciones'] as const).map(t=><button key={t} aria-pressed={sub===t} className={sub===t?'active':''} onClick={()=>setSub(t)}>{t}</button>)}</div>
  {sub==='Comparación'?<Comparison sheet={sheet} data={data} disabled={disabled} save={save}/>:<Negotiations sheet={sheet} data={data} disabled={disabled} save={save}/>}
 </>;
}

function Comparison({sheet,data,disabled,save}:{sheet:QuoteSheet;data:RubroQuotes;disabled:boolean;save:Save}){
 const latest=latestQuotes(data.quotes);
 const [pick,setPick]=useState<string[]|null>(null),[pending,setPending]=useState<Quote|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[over,setOver]=useState(false),[onlyGaps,setOnlyGaps]=useState(false);
 const picked=pick??latest.slice(0,3).map(q=>q.id);
 const chosen=picked.map(id=>data.quotes.find(q=>q.id===id)).filter(Boolean) as Quote[];
 const results=useMemo(()=>chosen.map(q=>compareQuote(sheet,q)),[chosen,sheet]);
 const supplierName=(id:string)=>data.suppliers.find(s=>s.id===id)?.name||'Sin proveedor';
 const store=async(q:Quote)=>{if(await save({...data,quotes:[...data.quotes,q]},`${q.file} cargado.`)){setPending(null);setPick(p=>p?[...p,q.id].slice(-3):null)}};
 async function ingest(file:File){
  setError('');setPending(null);
  if(!/\.xlsx$/i.test(file.name)){setError(`${file.name}: por ahora se leen solos los Excel (.xlsx) de la planilla que mandamos. Si llegó un PDF, pasámelo y lo cargo.`);return}
  setBusy(true);
  try{const rows=await readFirstSheet(await file.arrayBuffer()),{quote,errors,company}=quoteFromSheet(sheet,rows,conditionsFromRows(rows),file.name);
   if(!Object.keys(quote.lines).length)throw Error(`${file.name} no trae precios en las columnas de material o mano de obra.`);
   if(errors.length)setError('Revisá en el Excel: '+errors.slice(0,4).join('; '));
   const s=matchSupplier(data.suppliers,company,file.name);
   const q={...quote,supplier:s?.id||'',scope:quote.scope,zone:quote.zone||s?.zone||''};
   if(s)await store(q);else setPending(q);
  }catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 const toggle=(id:string)=>setPick(picked.includes(id)?picked.filter(x=>x!==id):[...picked,id].slice(-3));
 const update=(q:Quote,patch:Partial<Quote>,text:string)=>save({...data,quotes:data.quotes.map(x=>x.id===q.id?{...x,...patch}:x)},text);
 const sorted=[...data.quotes].sort((a,b)=>b.date.localeCompare(a.date));
 return <>
  <label className={'qdDrop'+(over?' over':'')} onDragOver={e=>{e.preventDefault();setOver(true)}} onDragLeave={()=>setOver(false)} onDrop={e=>{e.preventDefault();setOver(false);const f=e.dataTransfer.files?.[0];if(f&&!disabled)ingest(f)}}>
   <input type="file" accept=".xlsx" disabled={disabled} onChange={e=>{const f=e.target.files?.[0];if(f)ingest(f);e.target.value=''}}/>
   <b>{busy?'Leyendo…':'Arrastrá acá el presupuesto'}</b><span>El Excel que devolvió el proveedor. Se leen solos los precios, el alcance, la validez, los plazos y la zona.</span></label>
  {error&&<p className="pcError" role="alert">{error}<button onClick={()=>setError('')}>Cerrar</button></p>}
  {pending&&<div className="pcPanel qdPending"><b>{pending.file}</b><span>¿De qué proveedor es?</span><select defaultValue="" onChange={e=>{const s=data.suppliers.find(x=>x.id===e.target.value);if(s)store({...pending,supplier:s.id,zone:pending.zone||s.zone})}}><option value="" disabled>Elegir</option>{data.suppliers.filter(s=>s.apto!=='no apto').map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select><button onClick={()=>setPending(null)}>Descartar</button></div>}
  {!sorted.length?<p className="pcHint qdEmptyList">Todavía no hay presupuestos cargados en este rubro.</p>:<>
   <div className="pcTableWrap"><table className="qdList"><thead><tr><th>Comparar</th><th>Archivo</th><th>Proveedor</th><th>Recibido</th><th>Total</th><th>Ítems</th><th>Alcance</th><th>Zona viable</th><th/></tr></thead><tbody>
    {sorted.map(q=>{const r=compareQuote(sheet,q),old=!latest.includes(q);return <tr key={q.id} className={old?'qdOld':''}><td><input type="checkbox" aria-label={'Comparar '+q.file} checked={picked.includes(q.id)} onChange={()=>toggle(q.id)}/></td><td>{q.file||q.reference}{old&&<small>versión anterior</small>}</td><td>{supplierName(q.supplier)}</td><td>{dmy(q.date)}</td><td>{money(r.total,q.currency)}</td><td>{r.covered}/{r.count}</td><td>{scopeLabel(q.scope)}</td>
     <td><div className="qdSeg">{(['sí','a confirmar','no'] as const).map(v=><button key={v} aria-pressed={q.zoneViable===v} disabled={disabled} onClick={()=>update(q,{zoneViable:v},'Zona: '+v+'.')}>{v==='a confirmar'?'?':v==='sí'?'Sí':'No'}</button>)}</div></td>
     <td><button className="qdLink" disabled={disabled} onClick={()=>{if(confirm('¿Quitar '+(q.file||q.reference)+'?'))save({...data,quotes:data.quotes.filter(x=>x.id!==q.id)},'Presupuesto quitado.')}}>quitar</button></td></tr>})}
   </tbody></table></div>
   {chosen.length>0&&<>
    <div className="qdCards">{chosen.map((q,i)=>{const r=results[i],cheapest=Math.min(...results.map(x=>x.total));return <article key={q.id} className="pcPanel qdCard">
     <h3>{supplierName(q.supplier)}</h3><small>{q.file||q.reference}</small>
     <div className="qdBadges"><span className="pcBadge">{scopeLabel(q.scope)}</span><span className={'pcBadge qdZone-'+(q.zoneViable==='sí'?'ok':q.zoneViable==='no'?'no':'q')}>Zona {q.zoneViable==='sí'?'viable':q.zoneViable==='no'?'no viable':'a confirmar'}{q.zone?' · '+q.zone:''}</span></div>
     <p className="qdTotal">{money(r.total,q.currency)}{r.total===cheapest&&chosen.length>1&&<em> menor</em>}</p>
     <small>Material {money(r.material,q.currency)} · M.O. {money(r.labor,q.currency)}{r.freight?' · flete '+money(r.freight,q.currency):''}</small>
     <small>{q.taxesIncluded?'Con IVA':'Sin IVA'}{q.validUntil?` · vale hasta ${dmy(q.validUntil)}${q.validUntil<today()?' (vencido)':''}`:''}{q.delivery?' · '+q.delivery:''}</small>
     <p><b>{r.covered}/{r.count}</b> ítems completos{r.missing.length?` · ${r.missing.length} ${r.missing.length===1?'falta':'faltan'}`:''}</p>
     {r.missing.length>0&&<details><summary>Ver faltantes</summary><ul>{r.missing.map(m=><li key={m.code}>{m.code} · {m.description}</li>)}</ul></details>}
     {q.notes&&<small>{q.notes}</small>}</article>})}</div>
    <label className="pcCheck"><input type="checkbox" checked={onlyGaps} onChange={e=>setOnlyGaps(e.target.checked)}/>Solo ítems con faltantes</label>
    <div className="pcTableWrap"><table className="qdCompare"><thead><tr><th>Ítem</th>{chosen.map(q=><th key={q.id}>{supplierName(q.supplier)}</th>)}</tr></thead><tbody>
     {sheet.systems.map(s=>{const rows=s.items.filter(i=>!onlyGaps||results.some(r=>r.status[i.code]!=='completo'));if(!rows.length)return null;return [<tr key={s.key} className="qdSysRow"><td colSpan={chosen.length+1}>{s.name}</td></tr>,...rows.map(i=><tr key={i.code}><td><b>{i.code}</b> {i.description}<small>{qty(i.quantity)} {i.unit}</small></td>
      {chosen.map((q,k)=>{const l=q.lines[i.code]||{},st=results[k].status[i.code];return <td key={q.id} className={'qd-'+st}>{st==='falta'?'No cotizado':<>{needsMaterial(q.scope)&&<span>Mat. {l.material!=null?money(l.material,q.currency):i.materialOptional?'opcional':'—'}</span>}{needsLabor(q.scope)&&<span>M.O. {l.labor!=null?money(l.labor,q.currency):q.laborGlobal!=null?'global':'—'}</span>}{l.brand&&<small>{l.brand}</small>}</>}</td>})}</tr>)]})}
    </tbody></table></div>
   </>}
  </>}
 </>;
}

function Negotiations({sheet,data,disabled,save}:{sheet:QuoteSheet;data:RubroQuotes;disabled:boolean;save:Save}){
 const involved=data.suppliers.filter(s=>s.apto==='apto'||data.quotes.some(q=>q.supplier===s.id));
 const [supplier,setSupplier]=useState(involved[0]?.id||''),[entry,setEntry]=useState<Omit<NegotiationEntry,'id'|'supplier'>>({date:today(),from:'proveedor',kind:'consulta del proveedor',text:''}),[amount,setAmount]=useState('');
 const log=data.negotiation.filter(n=>n.supplier===supplier).sort((a,b)=>a.date.localeCompare(b.date));
 const history=supplier?priceHistory(sheet,data,supplier):[];
 const open=log.filter(n=>!n.resolved&&['consulta del proveedor','pregunta mano de obra','pregunta materiales','marcas'].includes(n.kind));
 async function add(){const n=parseNum(amount);if(Number.isNaN(n)||!entry.text.trim()||!supplier)return;
  if(await save({...data,negotiation:[...data.negotiation,{...entry,id:uid(),supplier,text:entry.text.trim(),...(n!=null?{amount:n}:{})}]},'Registrado en la negociación.')){setEntry({...entry,text:''});setAmount('')}}
 const toggle=(n:NegotiationEntry)=>save({...data,negotiation:data.negotiation.map(x=>x.id===n.id?{...x,resolved:!x.resolved}:x)},n.resolved?'Reabierta.':'Marcada como resuelta.');
 return <>
  <div className="pcSectionHead"><div><p>Consultas, preguntas de mano de obra, materiales y marcas, contraofertas y la evolución del número, por proveedor.</p></div>
   <label>Proveedor<select value={supplier} onChange={e=>setSupplier(e.target.value)}><option value="">Seleccionar</option>{involved.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label></div>
  {!involved.length?<p className="pcHint qdEmptyList">Aparecen acá los proveedores aptos o con presupuesto cargado.</p>:!supplier?null:<div className="qdNego">
   <div>
    <div className="pcPanel"><div className="pcFields">
     <label>Fecha<input type="date" value={entry.date} onChange={e=>setEntry({...entry,date:e.target.value})}/></label>
     <label>De<select value={entry.from} onChange={e=>setEntry({...entry,from:e.target.value as NegotiationEntry['from']})}><option value="proveedor">Proveedor</option><option value="ader">Ader</option></select></label>
     <label>Tipo<select value={entry.kind} onChange={e=>setEntry({...entry,kind:e.target.value as NegotiationEntry['kind']})}>{NEGOTIATION_KINDS.map(k=><option key={k}>{k}</option>)}</select></label>
     <label>Monto, si cambia<input inputMode="decimal" value={amount} onChange={e=>setAmount(e.target.value)}/></label></div>
     <label>Detalle<textarea rows={2} value={entry.text} onChange={e=>setEntry({...entry,text:e.target.value})}/></label>
     <button className="primary" disabled={disabled||!entry.text.trim()||Number.isNaN(parseNum(amount))} onClick={add}>Registrar</button></div>
    <h3>Conversación · {log.length}{open.length?` · ${open.length} abiertas`:''}</h3>
    <ol className="qdLog">{log.map(n=><li key={n.id} className={n.from==='ader'?'qdAder':''}><small>{dmy(n.date)} · {n.from==='ader'?'Ader':'Proveedor'} · {n.kind}{n.amount!=null?' · '+money(n.amount):''}</small><p>{n.text}</p>
     {['consulta del proveedor','pregunta mano de obra','pregunta materiales','marcas'].includes(n.kind)&&<button className="qdLink" disabled={disabled} onClick={()=>toggle(n)}>{n.resolved?'Resuelta ✓ · reabrir':'Marcar resuelta'}</button>}</li>)}</ol>
   </div>
   <div className="pcPanel"><h3>Evolución del número</h3>{!history.length?<p className="pcHint">Aparece con el primer presupuesto o monto.</p>:<ol className="qdSteps">{history.map((h,i)=><li key={i}><small>{dmy(h.date)} · {h.label}</small><b>{money(h.amount,h.currency)}</b>{i>0&&h.delta!==0&&<em className={h.delta<0?'down':'up'}>{h.delta<0?'▼':'▲'} {money(Math.abs(h.delta),h.currency)} ({(h.delta/history[i-1].amount*100).toFixed(1).replace('.',',')} %)</em>}</li>)}</ol>}
    {history.length>1&&<p><b>Variación total:</b> {money(history.at(-1)!.amount-history[0].amount)} ({((history.at(-1)!.amount/history[0].amount-1)*100).toFixed(1).replace('.',',')} %)</p>}</div>
  </div>}
 </>;
}
