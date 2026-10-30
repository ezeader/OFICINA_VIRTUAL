'use client';
import {useEffect,useMemo,useState} from 'react';
import {RUBROS} from '@/lib/rubros';
import {QUOTE_RUBROS,NEGOTIATION_KINDS,TARGET_QUOTES,FOLLOW_UP_DAYS,compareQuote,emptyRubroQuotes,followUp,latestQuotes,linesFromRows,needsLabor,needsMaterial,priceHistory,requestMail,
 type NegotiationEntry,type Quote,type QuoteLine,type QuoteSheet,type QuoteSupplier,type RubroQuotes,type SupplierKind} from '@/lib/quotes';
import {conditionsFromRows,readFirstSheet} from '@/lib/xlsx-read';
import './quote-desk.css';

const TABS=['Cómputo','Proveedores','Mails','Comparación','Negociaciones'] as const;
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
const blankQuote=(supplier=''):Quote=>({id:uid(),supplier,date:today(),reference:'',currency:'ARS',taxesIncluded:true,scope:'materiales + mano de obra',validUntil:'',delivery:'',zone:'',zoneViable:'a confirmar',freight:0,lines:{}});

export default function QuoteDesk({value,disabled,onSave}:{value?:Record<string,RubroQuotes>;disabled:boolean;onSave:(v:Record<string,RubroQuotes>,text:string)=>Promise<boolean>}){
 const [rubro,setRubro]=useState('sanitaria'),[tab,setTab]=useState<typeof TABS[number]>('Cómputo');
 const [loaded,setLoaded]=useState<Record<string,QuoteSheet|{error:string}>>({});
 const info=QUOTE_RUBROS.find(r=>r.key===rubro);
 const data=value?.[rubro]||emptyRubroQuotes();
 const url=info?.sheet,entry=url?loaded[url]:undefined,sheet=entry&&!('error' in entry)?entry:null,loadError=entry&&'error' in entry?entry.error:'';
 useEffect(()=>{if(!url||loaded[url])return;fetch(url).then(r=>{if(!r.ok)throw Error('No se pudo leer el cómputo ('+r.status+').');return r.json() as Promise<QuoteSheet>}).then(s=>setLoaded(m=>({...m,[url]:s})),e=>setLoaded(m=>({...m,[url]:{error:(e as Error).message}})))},[url,loaded]);
 const save=(next:RubroQuotes,text:string)=>onSave({...value,[rubro]:next},text);
 const supplierName=(id:string)=>data.suppliers.find(s=>s.id===id)?.name||'Proveedor';
 const fu=followUp(data);
 const aptos=data.suppliers.filter(s=>s.apto==='apto');
 return <section className="qd">
  <div className="qdRubros" aria-label="Rubros a cotizar">{QUOTE_RUBROS.map(r=><button key={r.key} className={rubro===r.key?'active':''} onClick={()=>setRubro(r.key)}>{r.name}</button>)}
   {RUBROS.map(r=><button key={r.key} disabled title="Todavía sin planilla de cotización">{r.name}</button>)}</div>
  {!info?.sheet?<div className="pcEmpty"><p>Este rubro todavía no tiene planilla de cotización.</p></div>:loadError?<p className="pcError" role="alert">{loadError}</p>:!sheet?<p className="pcHint">Cargando cómputo…</p>:<>
  <div className="qdStatus">
   <span><b>{fu.answered}/{TARGET_QUOTES}</b> presupuestos recibidos</span>
   <span><b>{aptos.length}</b> proveedores aptos · {data.suppliers.filter(s=>s.apto==='pendiente').length} esperan tu OK</span>
   <span><b>{data.suppliers.filter(s=>s.requestedAt).length}</b> pedidos enviados</span>
   {fu.searchMore&&<span className="qdAlert">{fu.late.length} sin respuesta hace {FOLLOW_UP_DAYS}+ días: sumar proveedores</span>}
  </div>
  <div className="qdTabs" aria-label="Cotización">{TABS.map(t=><button key={t} aria-pressed={tab===t} className={tab===t?'active':''} onClick={()=>setTab(t)}>{t}</button>)}</div>
  {tab==='Cómputo'&&<Computo sheet={sheet}/>}
  {tab==='Proveedores'&&<Suppliers data={data} disabled={disabled} save={save}/>}
  {tab==='Mails'&&<Mails sheet={sheet} data={data} disabled={disabled} save={save}/>}
  {tab==='Comparación'&&<Comparison sheet={sheet} data={data} disabled={disabled} save={save} supplierName={supplierName}/>}
  {tab==='Negociaciones'&&<Negotiations sheet={sheet} data={data} disabled={disabled} save={save}/>}
  </>}
 </section>;
}

function Computo({sheet}:{sheet:QuoteSheet}){
 const xlsx=`/casa-angel/cotizacion/Casa-Angel-${sheet.rubro[0].toUpperCase()+sheet.rubro.slice(1)}-cotizacion-${sheet.revision}.xlsx`;
 return <>
  <div className="pcSectionHead"><div><h2>{sheet.name} · cómputo {sheet.revision}</h2><p>{sheet.count} ítems ordenados por sistema, cada uno una sola vez. Material y mano de obra se cotizan por separado. {sheet.basis}</p></div>
   <div className="qdDocs"><a className="primary" href={xlsx} download>Excel para cotizar ↓</a>{sheet.documents.map(d=><a key={d.url} href={d.url} target="_blank" rel="noreferrer">{d.name} ↗</a>)}</div></div>
  {sheet.systems.map(s=><details key={s.key} className="qdSystem"><summary><b>{s.name}</b><span>{s.items.length} ítems</span></summary>
   <div className="pcTableWrap"><table><thead><tr><th>Código</th><th>Descripción</th><th>Cantidad</th></tr></thead><tbody>{s.items.map(i=><tr key={i.code}><td>{i.code}</td><td>{i.description}{i.materialOptional&&<small>Material opcional</small>}</td><td>{qty(i.quantity)} {i.unit}</td></tr>)}</tbody></table></div></details>)}
  <div className="pcPanel"><h3>No incluido en este pedido</h3><ul>{sheet.excluded.map(e=><li key={e}>{e}</li>)}</ul></div>
 </>;
}

function Suppliers({data,disabled,save}:{data:RubroQuotes;disabled:boolean;save:(v:RubroQuotes,t:string)=>Promise<boolean>}){
 const [edit,setEdit]=useState<QuoteSupplier|null>(null),[bulk,setBulk]=useState(''),[error,setError]=useState('');
 const set=(s:QuoteSupplier,text:string)=>save({...data,suppliers:data.suppliers.some(x=>x.id===s.id)?data.suppliers.map(x=>x.id===s.id?s:x):[...data.suppliers,s]},text);
 async function importList(){
  setError('');try{
   const list=JSON.parse(bulk);if(!Array.isArray(list))throw Error('Pegá un listado (array JSON).');
   const known=new Set(data.suppliers.map(s=>s.name.trim().toLowerCase()));
   const add:QuoteSupplier[]=list.filter(x=>x?.name&&!known.has(String(x.name).trim().toLowerCase())).map(x=>({...blankSupplier(),name:String(x.name),kind:KINDS.includes(x.kind)?x.kind:'materiales',group:x.group in GROUPS?x.group:'local',
    contact:[x.email,x.contact||x.phone,x.web].filter(Boolean).filter((v,i,a)=>a.indexOf(v)===i).join(' · '),location:String(x.location||''),zone:String(x.zone||'no informado'),source:x.source?String(x.source):undefined,notes:[x.notes,x.scope].filter(Boolean).join(' · ')||undefined}));
   if(await save({...data,suppliers:[...data.suppliers,...add]},`${add.length} proveedores agregados; ${list.length-add.length} ya estaban.`))setBulk('');
  }catch(e){setError((e as Error).message)}
 }
 const groups=(Object.keys(GROUPS) as (keyof typeof GROUPS)[]).map(g=>[g,data.suppliers.filter(s=>s.group===g)] as const).filter(([,l])=>l.length);
 return <>
  <div className="pcSectionHead"><div><h2>Proveedores</h2><p>Cada proveedor necesita tu OK de “apto” antes de recibir el pedido. Contactos y zonas son datos públicos; verificalos antes de enviar.</p></div><button className="primary" disabled={disabled} onClick={()=>setEdit(blankSupplier())}>Agregar proveedor</button></div>
  {error&&<p className="pcError" role="alert">{error}</p>}
  {edit&&<div className="pcPanel"><h3>{data.suppliers.some(s=>s.id===edit.id)?'Editar proveedor':'Nuevo proveedor'}</h3><div className="pcFields">
   {([['name','Nombre'],['contact','Contacto'],['location','Ubicación'],['zone','Zona donde trabaja'],['source','Fuente'],['notes','Notas']] as const).map(([k,l])=><label key={k}>{l}<input value={edit[k]||''} onChange={e=>setEdit({...edit,[k]:e.target.value})}/></label>)}
   <label>Tipo<select value={edit.kind} onChange={e=>setEdit({...edit,kind:e.target.value as SupplierKind})}>{KINDS.map(k=><option key={k}>{k}</option>)}</select></label>
   <label>Grupo<select value={edit.group} onChange={e=>setEdit({...edit,group:e.target.value as QuoteSupplier['group']})}>{Object.entries(GROUPS).map(([k,l])=><option key={k} value={k}>{l}</option>)}</select></label></div>
   <div className="pcActions"><button className="primary" disabled={disabled||!edit.name.trim()} onClick={async()=>{if(await set(edit,'Proveedor guardado.'))setEdit(null)}}>Guardar</button><button onClick={()=>setEdit(null)}>Cancelar</button>
   {data.suppliers.some(s=>s.id===edit.id)&&<button disabled={disabled||data.quotes.some(q=>q.supplier===edit.id)} title="Solo sin presupuestos cargados" onClick={async()=>{if(confirm('¿Quitar '+edit.name+' del listado?')&&await save({...data,suppliers:data.suppliers.filter(s=>s.id!==edit.id),negotiation:data.negotiation.filter(n=>n.supplier!==edit.id)},'Proveedor quitado.'))setEdit(null)}}>Quitar</button>}</div></div>}
  {groups.map(([g,list])=><div key={g}><h3 className="qdGroup">{GROUPS[g]} · {list.length}</h3><div className="pcTableWrap"><table className="qdSuppliers"><thead><tr><th>Proveedor</th><th>Contacto</th><th>Ubicación</th><th>Zona</th><th>Apto</th><th>Pedido</th><th/></tr></thead><tbody>
   {list.map(s=><tr key={s.id} className={'qdApto-'+s.apto.replace(' ','-')}><td><b>{s.name}</b><small>{s.kind}{s.notes?' · '+s.notes:''}</small>{s.source&&<a href={s.source} target="_blank" rel="noreferrer">fuente ↗</a>}</td><td>{s.contact}</td><td>{s.location}</td><td>{s.zone}</td>
    <td><div className="qdSeg">{(['apto','pendiente','no apto'] as const).map(a=><button key={a} aria-pressed={s.apto===a} disabled={disabled} onClick={()=>set({...s,apto:a},a==='apto'?`${s.name}: apto.`:`${s.name}: ${a}.`)}>{a==='pendiente'?'?':a==='apto'?'Apto':'No'}</button>)}</div></td>
    <td>{s.requestedAt?<><span>Enviado {dmy(s.requestedAt)}</span><button className="qdLink" disabled={disabled} onClick={()=>set({...s,requestedAt:undefined},'Envío desmarcado.')}>desmarcar</button></>:s.apto==='apto'?<button disabled={disabled} onClick={()=>set({...s,requestedAt:new Date().toISOString()},'Marcado como enviado hoy.')}>Marcar enviado</button>:<small>—</small>}
     {s.requestedAt&&<label className="pcCheck"><input type="checkbox" checked={!!s.declined} disabled={disabled} onChange={e=>set({...s,declined:e.target.checked},'Guardado.')}/>No cotiza</label>}</td>
    <td><button disabled={disabled} onClick={()=>setEdit({...s})}>Editar</button></td></tr>)}
  </tbody></table></div></div>)}
  {!data.suppliers.length&&<div className="pcEmpty"><p>Todavía no hay proveedores para este rubro.</p></div>}
  <details className="pcPanel"><summary>Importar listado (JSON)</summary><p className="pcHint">Array de objetos con name, kind, group (local/costa/nacional), contact, phone, email, web, location, zone, source, notes. No se duplican nombres existentes. Todos entran como pendientes de OK.</p><textarea rows={5} value={bulk} onChange={e=>setBulk(e.target.value)}/><button disabled={disabled||!bulk.trim()} onClick={importList}>Importar</button></details>
 </>;
}

function Mails({sheet,data,disabled,save}:{sheet:QuoteSheet;data:RubroQuotes;disabled:boolean;save:(v:RubroQuotes,t:string)=>Promise<boolean>}){
 const [deadline,setDeadline]=useState(plusDays(7)),[copied,setCopied]=useState('');
 const aptos=data.suppliers.filter(s=>s.apto==='apto'),targets=aptos.length?aptos:[{id:'modelo',name:'[proveedor]',kind:'materiales + mano de obra' as SupplierKind}];
 const xlsx=`Casa-Angel-${sheet.rubro[0].toUpperCase()+sheet.rubro.slice(1)}-cotizacion-${sheet.revision}.xlsx`;
 async function copy(id:string,text:string){try{await navigator.clipboard.writeText(text);setCopied(id)}catch{setCopied('')}}
 return <>
  <div className="pcSectionHead"><div><h2>Borradores de mail</h2><p>Solo borradores: la oficina no envía nada. Cuando apruebes proveedores, texto y adjuntos, se envían por el medio que elijas y se marca “enviado” en Proveedores.</p></div>
   <label>Fecha límite de respuesta<input type="date" value={deadline} onChange={e=>setDeadline(e.target.value)}/></label></div>
  <div className="pcPanel"><h3>Adjuntos</h3><ul><li>{xlsx} (Excel de cómputo)</li>{sheet.documents.map(d=><li key={d.url}>{d.url.split('/').pop()} · {d.name}</li>)}</ul></div>
  {!aptos.length&&<p className="pcHint">Todavía no marcaste proveedores aptos. Abajo, el modelo del mail.</p>}
  {targets.map(s=>{const m=requestMail(sheet,s,dmy(deadline)),full=`Asunto: ${m.subject}\n\n${m.body}`;const sup=data.suppliers.find(x=>x.id===s.id);
   return <article key={s.id} className="pcPanel qdMail"><div className="qdMailHead"><div><b>{s.name}</b>{sup&&<small>{sup.contact}</small>}</div><span className="pcBadge">{sup?.requestedAt?'Enviado '+dmy(sup.requestedAt):'Borrador · sin enviar'}</span></div>
    <p><b>Asunto:</b> {m.subject}</p><pre>{m.body}</pre>
    <div className="pcActions"><button onClick={()=>copy(s.id,full)}>{copied===s.id?'Copiado ✓':'Copiar texto'}</button>{sup&&!sup.requestedAt&&<button disabled={disabled} onClick={()=>save({...data,suppliers:data.suppliers.map(x=>x.id===sup.id?{...x,requestedAt:new Date().toISOString()}:x)},'Marcado como enviado hoy.')}>Marcar enviado</button>}</div></article>})}
 </>;
}

function Comparison({sheet,data,disabled,save,supplierName}:{sheet:QuoteSheet;data:RubroQuotes;disabled:boolean;save:(v:RubroQuotes,t:string)=>Promise<boolean>;supplierName:(id:string)=>string}){
 const latest=latestQuotes(data.quotes);
 const [pick,setPick]=useState<string[]>([]),[edit,setEdit]=useState<Quote|null>(null),[error,setError]=useState(''),[onlyGaps,setOnlyGaps]=useState(false);
 const chosen=(pick.length?pick:latest.slice(0,3).map(q=>q.id)).map(id=>data.quotes.find(q=>q.id===id)).filter(Boolean) as Quote[];
 const results=useMemo(()=>chosen.map(q=>compareQuote(sheet,q)),[chosen,sheet]);
 const zoneOf=(q:Quote)=>q.zone||data.suppliers.find(s=>s.id===q.supplier)?.zone||'no informada';
 async function fromExcel(file:File){
  if(!edit)return;setError('');
  try{const rows=await readFirstSheet(await file.arrayBuffer());const {lines,errors}=linesFromRows(sheet,rows);const c=conditionsFromRows(rows);
   if(!Object.keys(lines).length)throw Error('El Excel no trae precios en las columnas de material (E) o mano de obra (G) para los códigos del cómputo.');
   const scope=/ambos|mano de obra y|materiales y|\+/i.test(c['¿Cotiza materiales, mano de obra o ambos?']||'')?'materiales + mano de obra':/mano de obra/i.test(c['¿Cotiza materiales, mano de obra o ambos?']||'')?'mano de obra':/material/i.test(c['¿Cotiza materiales, mano de obra o ambos?']||'')?'materiales':edit.scope;
   setEdit({...edit,lines,scope,currency:/usd|d[oó]lar/i.test(c['Moneda (ARS o USD)']||'')?'USD':edit.currency,taxesIncluded:c['¿Los precios incluyen IVA?']?/^s[ií]/i.test(c['¿Los precios incluyen IVA?']):edit.taxesIncluded,
    delivery:[c['Plazo de entrega de materiales en obra'],c['Plazo de ejecución de la mano de obra']].filter(Boolean).join(' · ')||edit.delivery,zone:c['Zona de trabajo (localidades que atiende)']||edit.zone,notes:[edit.notes,c['Validez de la oferta (días)']&&'Validez: '+c['Validez de la oferta (días)'],c['Flete a Pinamar Norte (incluido o importe)']&&'Flete: '+c['Flete a Pinamar Norte (incluido o importe)'],c['Forma de pago']&&'Pago: '+c['Forma de pago']].filter(Boolean).join(' · ')});
   if(errors.length)setError('Revisá: '+errors.slice(0,5).join('; '));
  }catch(e){setError((e as Error).message)}
 }
 function setLine(code:string,k:keyof QuoteLine,text:string){if(!edit)return;const l={...edit.lines[code]};if(k==='material'||k==='labor'){const n=parseNum(text);if(Number.isNaN(n))return;if(n===undefined)delete l[k];else l[k]=n}else l[k]=text||undefined;setEdit({...edit,lines:{...edit.lines,[code]:l}})}
 async function store(){if(!edit)return;if(!edit.supplier||!edit.reference.trim()||!edit.validUntil){setError('Completá proveedor, referencia y vigencia.');return}
  const exists=data.quotes.some(q=>q.id===edit.id);if(await save({...data,quotes:exists?data.quotes.map(q=>q.id===edit.id?edit:q):[...data.quotes,edit]},'Presupuesto guardado.')){setEdit(null);setPick([])}}
 return <>
  <div className="pcSectionHead"><div><h2>Comparación de presupuestos</h2><p>Se compara la última respuesta de cada proveedor contra el cómputo: precio, ítems cotizados y faltantes, alcance (materiales o materiales + mano de obra) y zona.</p></div><button className="primary" disabled={disabled||!data.suppliers.length} onClick={()=>{setEdit(blankQuote());setError('')}}>Cargar presupuesto recibido</button></div>
  {error&&<p className="pcError" role="alert">{error}<button onClick={()=>setError('')}>Cerrar</button></p>}
  {edit&&<div className="pcPanel"><h3>Presupuesto recibido</h3><div className="pcFields">
   <label>Proveedor<select value={edit.supplier} onChange={e=>{const s=data.suppliers.find(x=>x.id===e.target.value);setEdit({...edit,supplier:e.target.value,scope:s?.kind||edit.scope,zone:edit.zone||s?.zone||''})}}><option value="">Seleccionar</option>{data.suppliers.filter(s=>s.apto!=='no apto').map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
   <label>Referencia<input value={edit.reference} placeholder="N° o fecha del presupuesto" onChange={e=>setEdit({...edit,reference:e.target.value})}/></label>
   <label>Recibido<input type="date" value={edit.date.slice(0,10)} onChange={e=>setEdit({...edit,date:e.target.value})}/></label>
   <label>Alcance<select value={edit.scope} onChange={e=>setEdit({...edit,scope:e.target.value as SupplierKind})}>{KINDS.map(k=><option key={k}>{k}</option>)}</select></label>
   <label>Moneda<select value={edit.currency} onChange={e=>setEdit({...edit,currency:e.target.value as Quote['currency']})}><option>ARS</option><option>USD</option></select></label>
   <label>Vigencia hasta<input type="date" value={edit.validUntil} onChange={e=>setEdit({...edit,validUntil:e.target.value})}/></label>
   <label>Entrega / ejecución<input value={edit.delivery} onChange={e=>setEdit({...edit,delivery:e.target.value})}/></label>
   <label>Zona que atiende<input value={edit.zone} onChange={e=>setEdit({...edit,zone:e.target.value})}/></label>
   <label>¿Zona viable para Pinamar Norte?<select value={edit.zoneViable} onChange={e=>setEdit({...edit,zoneViable:e.target.value as Quote['zoneViable']})}><option>a confirmar</option><option>sí</option><option>no</option></select></label>
   <label>Flete<input inputMode="decimal" value={edit.freight||''} onChange={e=>{const n=parseNum(e.target.value);if(!Number.isNaN(n))setEdit({...edit,freight:n||0})}}/></label>
   <label>Mano de obra global (si no la abre por ítem)<input inputMode="decimal" value={edit.laborGlobal??''} onChange={e=>{const n=parseNum(e.target.value);if(!Number.isNaN(n))setEdit({...edit,laborGlobal:n})}}/></label>
   <label>Notas<input value={edit.notes||''} onChange={e=>setEdit({...edit,notes:e.target.value})}/></label></div>
   <label className="pcCheck"><input type="checkbox" checked={edit.taxesIncluded} onChange={e=>setEdit({...edit,taxesIncluded:e.target.checked})}/>Precios con IVA incluido</label>
   <div className="pcActions"><label className="qdFile">Leer la planilla devuelta (.xlsx)<input type="file" accept=".xlsx" onChange={e=>{const f=e.target.files?.[0];if(f)fromExcel(f)}}/></label><span className="pcHint">{Object.keys(edit.lines).length} ítems con precio</span></div>
   <details><summary>Precios por ítem</summary><div className="pcTableWrap"><table className="qdLines"><thead><tr><th>Ítem</th><th>Cantidad</th><th>Material $/u</th><th>M.O. $/u</th><th>Marca / nota</th></tr></thead><tbody>{sheet.systems.map(s=>[<tr key={s.key} className="qdSysRow"><td colSpan={5}>{s.name}</td></tr>,...s.items.map(i=>{const l=edit.lines[i.code]||{};return <tr key={i.code}><td>{i.code} · {i.description}</td><td>{qty(i.quantity)} {i.unit}</td>
    <td><input inputMode="decimal" aria-label={'Material '+i.code} defaultValue={l.material??''} onBlur={e=>setLine(i.code,'material',e.target.value)}/></td><td><input inputMode="decimal" aria-label={'Mano de obra '+i.code} defaultValue={l.labor??''} onBlur={e=>setLine(i.code,'labor',e.target.value)}/></td><td><input defaultValue={l.brand??l.note??''} onBlur={e=>setLine(i.code,'brand',e.target.value)}/></td></tr>})])}</tbody></table></div></details>
   <div className="pcActions"><button className="primary" disabled={disabled} onClick={store}>Guardar presupuesto</button><button onClick={()=>setEdit(null)}>Cancelar</button></div></div>}
  {!latest.length?<div className="pcEmpty"><p>Todavía no hay presupuestos cargados. Cuando lleguen, cargalos acá (podés leer directamente la planilla que devuelve el proveedor).</p></div>:<>
   <div className="qdPick">{[0,1,2].map(i=><select key={i} aria-label={'Presupuesto '+(i+1)} value={chosen[i]?.id||''} onChange={e=>{const ids=[0,1,2].map(j=>chosen[j]?.id||'');ids[i]=e.target.value;setPick(ids.filter(Boolean))}}><option value="">—</option>{latest.map(q=><option key={q.id} value={q.id}>{supplierName(q.supplier)} · {q.reference}</option>)}</select>)}</div>
   <div className="qdCards">{chosen.map((q,i)=>{const r=results[i];const cheapest=Math.min(...results.map(x=>x.total));return <article key={q.id} className="pcPanel qdCard">
    <h3>{supplierName(q.supplier)}</h3><small>{q.reference} · recibido {dmy(q.date)}</small>
    <div className="qdBadges"><span className={'pcBadge qdScope'}>{q.scope==='materiales + mano de obra'?'Materiales + M.O.':q.scope==='materiales'?'Solo materiales':'Solo mano de obra'}</span><span className={'pcBadge qdZone-'+(q.zoneViable==='sí'?'ok':q.zoneViable==='no'?'no':'q')}>Zona {q.zoneViable==='sí'?'viable':q.zoneViable==='no'?'no viable':'a confirmar'} · {zoneOf(q)}</span></div>
    <p className="qdTotal">{money(r.total,q.currency)}{r.total===cheapest&&chosen.length>1&&<em> menor</em>}</p>
    <small>Material {money(r.material,q.currency)} · M.O. {money(r.labor,q.currency)}{q.laborGlobal!=null?' (global)':''} · flete {money(r.freight,q.currency)}</small>
    <small>{q.currency} · {q.taxesIncluded?'con IVA':'sin IVA'} · vigencia {dmy(q.validUntil)}{q.validUntil<today()?' (vencida)':''} · {q.delivery||'entrega sin informar'}</small>
    <p><b>{r.covered}/{r.count}</b> ítems completos{r.partial.length?` · ${r.partial.length} parciales`:''}{r.missing.length?` · ${r.missing.length} ${r.missing.length===1?'falta':'faltan'}`:''}</p>
    {r.missing.length>0&&<details><summary>Faltan {r.missing.length}</summary><ul>{r.missing.map(m=><li key={m.code}>{m.code} · {m.description}</li>)}</ul></details>}
    {q.notes&&<small>{q.notes}</small>}
    <button disabled={disabled} onClick={()=>{setEdit(structuredClone(q));setError('')}}>Editar</button></article>})}</div>
   <label className="pcCheck"><input type="checkbox" checked={onlyGaps} onChange={e=>setOnlyGaps(e.target.checked)}/>Mostrar solo ítems con faltantes</label>
   <div className="pcTableWrap"><table className="qdCompare"><thead><tr><th>Ítem</th>{chosen.map(q=><th key={q.id}>{supplierName(q.supplier)}</th>)}</tr></thead><tbody>
    {sheet.systems.map(s=>{const rows=s.items.filter(i=>!onlyGaps||results.some(r=>r.status[i.code]!=='completo'));if(!rows.length)return null;return [<tr key={s.key} className="qdSysRow"><td colSpan={chosen.length+1}>{s.name}</td></tr>,...rows.map(i=><tr key={i.code}><td><b>{i.code}</b> {i.description}<small>{qty(i.quantity)} {i.unit}</small></td>
     {chosen.map((q,k)=>{const l=q.lines[i.code]||{},st=results[k].status[i.code];return <td key={q.id} className={'qd-'+st}>{st==='falta'?'No cotizado':<>{needsMaterial(q.scope)&&<span>Mat. {l.material!=null?money(l.material,q.currency):i.materialOptional?'opcional':'—'}</span>}{needsLabor(q.scope)&&<span>M.O. {l.labor!=null?money(l.labor,q.currency):q.laborGlobal!=null?'global':'—'}</span>}{l.brand&&<small>{l.brand}</small>}</>}</td>})}</tr>)]})}
   </tbody></table></div>
   <details><summary>Historial · {data.quotes.length} presupuestos</summary><ul>{[...data.quotes].sort((a,b)=>b.date.localeCompare(a.date)).map(q=><li key={q.id}>{dmy(q.date)} · {supplierName(q.supplier)} · {q.reference} · {money(compareQuote(sheet,q).total,q.currency)}</li>)}</ul></details>
  </>}
 </>;
}

function Negotiations({sheet,data,disabled,save}:{sheet:QuoteSheet;data:RubroQuotes;disabled:boolean;save:(v:RubroQuotes,t:string)=>Promise<boolean>}){
 const involved=data.suppliers.filter(s=>s.apto==='apto'||data.quotes.some(q=>q.supplier===s.id));
 const [supplier,setSupplier]=useState(involved[0]?.id||''),[entry,setEntry]=useState<Omit<NegotiationEntry,'id'|'supplier'>>({date:today(),from:'proveedor',kind:'consulta del proveedor',text:''}),[amount,setAmount]=useState('');
 const log=data.negotiation.filter(n=>n.supplier===supplier).sort((a,b)=>a.date.localeCompare(b.date));
 const history=supplier?priceHistory(sheet,data,supplier):[];
 const open=log.filter(n=>!n.resolved&&['consulta del proveedor','pregunta mano de obra','pregunta materiales','marcas'].includes(n.kind));
 async function add(){const n=parseNum(amount);if(Number.isNaN(n)||!entry.text.trim()||!supplier)return;
  if(await save({...data,negotiation:[...data.negotiation,{...entry,id:uid(),supplier,text:entry.text.trim(),...(n!=null?{amount:n}:{})}]},'Registrado en la negociación.')){setEntry({...entry,text:''});setAmount('')}}
 const toggle=(n:NegotiationEntry)=>save({...data,negotiation:data.negotiation.map(x=>x.id===n.id?{...x,resolved:!x.resolved}:x)},n.resolved?'Reabierta.':'Marcada como resuelta.');
 return <>
  <div className="pcSectionHead"><div><h2>Negociaciones</h2><p>Por proveedor: dudas y consultas, preguntas sobre mano de obra, materiales y marcas, contraofertas y la evolución del número hasta el cierre.</p></div>
   <label>Proveedor<select value={supplier} onChange={e=>setSupplier(e.target.value)}><option value="">Seleccionar</option>{involved.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label></div>
  {!involved.length?<div className="pcEmpty"><p>Aparecen acá los proveedores aptos o con presupuesto cargado.</p></div>:!supplier?null:<div className="qdNego">
   <div>
    <div className="pcPanel"><h3>Nuevo registro</h3><div className="pcFields">
     <label>Fecha<input type="date" value={entry.date} onChange={e=>setEntry({...entry,date:e.target.value})}/></label>
     <label>De<select value={entry.from} onChange={e=>setEntry({...entry,from:e.target.value as NegotiationEntry['from']})}><option value="proveedor">Proveedor</option><option value="ader">Ader</option></select></label>
     <label>Tipo<select value={entry.kind} onChange={e=>setEntry({...entry,kind:e.target.value as NegotiationEntry['kind']})}>{NEGOTIATION_KINDS.map(k=><option key={k}>{k}</option>)}</select></label>
     <label>Monto (si cambia el número)<input inputMode="decimal" value={amount} onChange={e=>setAmount(e.target.value)}/></label></div>
     <label>Detalle<textarea rows={3} value={entry.text} onChange={e=>setEntry({...entry,text:e.target.value})}/></label>
     <button className="primary" disabled={disabled||!entry.text.trim()||Number.isNaN(parseNum(amount))} onClick={add}>Registrar</button></div>
    <h3>Conversación · {log.length}{open.length?` · ${open.length} abiertas`:''}</h3>
    {!log.length&&<p className="pcHint">Sin registros todavía.</p>}
    <ol className="qdLog">{log.map(n=><li key={n.id} className={n.from==='ader'?'qdAder':''}><small>{dmy(n.date)} · {n.from==='ader'?'Ader':'Proveedor'} · {n.kind}{n.amount!=null?' · '+money(n.amount):''}</small><p>{n.text}</p>
     {['consulta del proveedor','pregunta mano de obra','pregunta materiales','marcas'].includes(n.kind)&&<button className="qdLink" disabled={disabled} onClick={()=>toggle(n)}>{n.resolved?'Resuelta ✓ · reabrir':'Marcar resuelta'}</button>}</li>)}</ol>
   </div>
   <div className="pcPanel"><h3>Evolución del número</h3>{!history.length?<p className="pcHint">Aparece cuando hay un presupuesto cargado o un monto en la negociación.</p>:<ol className="qdSteps">{history.map((h,i)=><li key={i}><small>{dmy(h.date)} · {h.label}</small><b>{money(h.amount,h.currency)}</b>{i>0&&h.delta!==0&&<em className={h.delta<0?'down':'up'}>{h.delta<0?'▼':'▲'} {money(Math.abs(h.delta),h.currency)} ({(h.delta/history[i-1].amount*100).toFixed(1).replace('.',',')} %)</em>}</li>)}</ol>}
    {history.length>1&&<p><b>Variación total:</b> {money(history.at(-1)!.amount-history[0].amount)} ({((history.at(-1)!.amount/history[0].amount-1)*100).toFixed(1).replace('.',',')} %)</p>}</div>
  </div>}
 </>;
}
