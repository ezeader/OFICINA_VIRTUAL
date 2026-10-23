'use client';
import {useCallback,useEffect,useMemo,useState,type PointerEvent} from 'react';
import {ArrowLeft,Download} from 'lucide-react';
import VectorImage from './compressed-drawing';
import DrawingViewport from './drawing-viewport';
import RevitOpenButton from './revit-open-button';
import {TrimmedDrawing,OpeningTooltip,type Crop} from './opening-drawings';
import {openingsHref} from '../lib/documentation-route';
import {NOTE_KEY,correctionFor,pendingForRevit,setCorrection,type OpeningsReview} from '../lib/openings-review';
import {buildSheets,groupSheets,dimensionText,CATEGORY_GROUP,type SheetCard,type SheetView} from '../lib/openings-sheets';
import {budgetCsv,budgetTotals,sizeOf,surveySpecs} from '../lib/openings-budget';
import './sanitary-sheets.css';
import './project-sanitary.css';
import './openings-desk.css';

type Item={id:string;uid:string;code:string;category:string;family:string;type:string;rooms:number[];width?:string;height?:string;sill?:string;head?:string;materials:string[];warnings:string[];panelCount?:number;parameters:{name:string;value:string;scope:string}[]};
type Data={items:Item[];rooms:unknown[];counts:{windows:number;doors:number;curtainWalls:number;unassigned:number};reviewCases?:{code:string;elementId:string;title:string;observation:string;proposedCorrection:string}[]};
type Tab=SheetCard['tab']|'computo';
const SHEET_ASPECT=2383.94/1683.78;
const TABS:[Tab,string][]=[['locales','Por local'],['aberturas','Por abertura'],['revision','Revisión pendiente'],['computo','Cómputo para presupuesto']];
const n2=(n:number)=>n.toLocaleString('es-AR',{minimumFractionDigits:2,maximumFractionDigits:2});
const KIND:Record<string,string>={Windows:'Ventana',Doors:'Puerta','Curtain Walls':'Muro cortina'};
const m=(v?:string)=>v?v.replace(' m','').replace('.',','):'—';
const param=(i:Item,name:string)=>i.parameters.find(p=>p.name===name)?.value;
// Medidas para leer de un vistazo, siempre con los valores que trae Revit.
function sizeLine(i:Item){
 if(i.category==='Curtain Walls')return `${m(param(i,'Length'))} × ${m(param(i,'Unconnected Height'))} m · ${i.panelCount??'?'} paneles`;
 return i.width&&i.height?`${m(i.width)} × ${m(i.height)} m`:'Medidas sin dato en Revit';
}
const heightLine=(i:Item)=>i.category==='Curtain Walls'||!i.sill?'':`Antepecho ${m(i.sill)} · Dintel ${m(i.head)} m`;
// Las advertencias de Revit, dichas en simple.
const plainWarning=(w:string)=>w.replace(/\.$/,'').replace('Espesor de hoja/perfil sin parámetro utilizable','falta el espesor del perfil').replace('Material genérico o sin especificación comercial','material sin especificar').replace('Medidas del conjunto: los paneles y montantes requieren su propio despiece para compra','falta el despiece de paneles').replace(/^Sin recinto contiguo.*/,'no tiene local asignado').replace(/^Verificar solape.*/,'se superpone con un muro');

// Nota simple por abertura: qué hay que corregir en Revit y si ya está resuelto.
function NoteBox({item,review,disabled,onSaveReview}:{item:Item;review?:OpeningsReview;disabled?:boolean;onSaveReview?:(next:OpeningsReview)=>Promise<boolean>}){
 const saved=correctionFor(review,item.id,NOTE_KEY);
 const [open,setOpen]=useState(false),[note,setNote]=useState(''),[done,setDone]=useState(false),[busy,setBusy]=useState(false);
 if(!onSaveReview)return null;
 if(!open)return <><button className="openingNoteButton" onClick={()=>{setNote(saved?.note||'');setDone(saved?.status==='applied');setOpen(true)}}>{saved?.note?(saved.status==='applied'?'✓ Resuelto · ver nota':'✎ Ver mi nota'):'✎ Anotar corrección'}</button>{saved?.note&&<p className="openingNoteText">{saved.note}</p>}</>;
 return <div className="openingNote">
  <textarea rows={3} value={note} disabled={disabled||busy} placeholder="Qué hay que corregir en Revit. Ej.: el perfil es de 45 mm" onChange={e=>setNote(e.target.value)}/>
  <label><input type="checkbox" checked={done} disabled={disabled||busy} onChange={e=>setDone(e.target.checked)}/>Ya está resuelto en Revit</label>
  <div><button className="primary" disabled={disabled||busy} onClick={async()=>{setBusy(true);const ok=await onSaveReview(setCorrection(review,item.id,NOTE_KEY,{note,value:'',status:done?'applied':note.trim()?'proposed':'open'},new Date().toISOString()));setBusy(false);if(ok)setOpen(false)}}>{busy?'Guardando…':'Guardar'}</button><button onClick={()=>setOpen(false)}>Cancelar</button></div>
 </div>;
}

export default function OpeningsDesk({mode='documentation',caseCode,review,onSaveReview,disabled}:{mode?:'documentation'|'quantities';caseCode?:string;review?:OpeningsReview;onSaveReview?:(next:OpeningsReview)=>Promise<boolean>;disabled?:boolean}){
 const [data,setData]=useState<Data>(),[regions,setRegions]=useState<Record<string,number[]>>({}),[error,setError]=useState('');
 const [tab,setTab]=useState<Tab>('locales'),[sheetKey,setSheetKey]=useState<string|null>(null),[lightbox,setLightbox]=useState<number|null>(null),[lightCrop,setLightCrop]=useState<Crop>();
 const [hover,setHover]=useState<{item:Item;x:number;y:number}|null>(null),[copied,setCopied]=useState('');
 useEffect(()=>{const abort=new AbortController();
  fetch('/casa-angel/openings/manifest.json',{signal:abort.signal}).then(r=>{if(!r.ok)throw Error('No se pudo cargar la documentación de aberturas.');return r.json() as Promise<Data>}).then(setData).catch(e=>{if(!abort.signal.aborted)setError(e.message)});
  fetch('/casa-angel/openings/view-regions.json',{signal:abort.signal}).then(r=>r.ok?r.json():{}).then(setRegions).catch(()=>{});
  return()=>abort.abort()},[]);
 const cards=useMemo(()=>data?buildSheets(data as unknown as Parameters<typeof buildSheets>[0]):[],[data]);
 const sheet=cards.find(c=>c.key===(caseCode?`case-${caseCode}`:sheetKey));
 const views=sheet?.views||[];
 useEffect(()=>{if(lightbox===null)return;const key=(e:KeyboardEvent)=>{if(e.key==='Escape')setLightbox(null);else if(e.key==='ArrowRight')setLightbox(i=>i===null?i:(i+1)%views.length);else if(e.key==='ArrowLeft')setLightbox(i=>i===null?i:(i-1+views.length)%views.length)};window.addEventListener('keydown',key);document.body.style.overflow='hidden';return()=>{window.removeEventListener('keydown',key);document.body.style.overflow=''}},[lightbox,views.length]);
 const onLightCrop=useCallback((c:Crop)=>setLightCrop(c),[]);
 if(!data)return <p className="sheetHint">{error||'Cargando las láminas de aberturas…'}</p>;
 const byId=new Map(data.items.map(i=>[i.id,i])),byCode=new Map(data.items.map(i=>[i.code,i]));
 const pending=pendingForRevit(data.items,review);
 const hoverOn=(i?:Item)=>i?{onPointerMove:(e:PointerEvent)=>{if(!e.buttons&&e.pointerType==='mouse')setHover({item:i,x:e.clientX,y:e.clientY})},onPointerLeave:()=>setHover(null)}:{};
 function open(key:string|null){if(caseCode){window.history.replaceState(null,'',openingsHref());window.dispatchEvent(new HashChangeEvent('hashchange'))}setSheetKey(key);setLightbox(null);setHover(null);window.scrollTo({top:0})}
 const zoom=(index:number)=>{setLightCrop(undefined);setLightbox(index);setHover(null)};
 async function copyPending(){const text=['Casa Ángel · Aberturas · Correcciones para Revit','',...pending.map(r=>`${r.code} (Id ${r.id}): ${r.note||r.value||r.subject}`)].join('\n');try{await navigator.clipboard.writeText(text);setCopied('Copiado')}catch{setCopied('No se pudo copiar')}setTimeout(()=>setCopied(''),2500)}
 const elementCard=(item:Item,current?:SheetCard)=>{const other=cards.filter(c=>c.itemIds.includes(item.id)&&c.key!==current?.key&&c.tab!=='revision');return <article key={item.id} className="openingCard" {...hoverOn(item)}>
  <header><span className="openingTag">{item.code}</span><small>{KIND[item.category]}</small></header>
  <strong>{item.type}</strong>
  <p className="openingSize">{sizeLine(item)}</p>{heightLine(item)&&<p className="openingSub">{heightLine(item)}</p>}
  {(()=>{const s=sizeOf(item),specs=surveySpecs(item),known=specs.filter(x=>x.value),gaps=specs.filter(x=>!x.value);return <><p className="openingSub">{s?`${n2(s.area)} m² · ${n2(s.perimeter)} m de marco`:'Sin superficie calculable'}</p><dl className="openingSpecs">{known.map(x=><div key={x.label}><dt>{x.label}</dt><dd>{x.value!.replace(/(\d)\.(\d)/g,'$1,$2')}</dd></div>)}</dl>{gaps.length>0&&<p className="openingGaps">Sin dato en Revit: {gaps.map(x=>x.label.toLowerCase()).join(', ')}</p>}</>})()}
  {item.warnings.length>0&&<p className="openingAlert">⚠ Revisar: {item.warnings.map(plainWarning).join(' · ')}</p>}{(item as {survey?:{notes?:string[]}}).survey?.notes?.map(n=><p key={n} className="openingSub">{n}</p>)}
  <NoteBox key={item.id+(correctionFor(review,item.id,NOTE_KEY)?.updatedAt||'')} item={item} review={review} disabled={disabled} onSaveReview={onSaveReview}/>
  {other.length>0&&<div className="openingLinks">{other.map(c=><button key={c.key} onClick={()=>open(c.key)}>{c.tab==='locales'?'Ver lámina de '+c.name.split(' · ').slice(1).join(' · '):'Ver lámina de la abertura'} ↗</button>)}</div>}
 </article>};

 if(mode==='quantities')return <section className="openingsDesk"><div className="sheetHeading"><div><p className="eyebrow">CASA ÁNGEL / ABERTURAS</p><h3>{data.items.length} aberturas únicas</h3><p>{data.counts.windows} ventanas · {data.counts.doors} puertas · {data.counts.curtainWalls} muros cortina</p></div></div>{Object.entries(CATEGORY_GROUP).map(([cat,title])=><section key={cat}><h4 className="openingGroupTitle">{title}</h4><div className="openingCards">{data.items.filter(i=>i.category===cat).map(i=>elementCard(i))}</div></section>)}{hover&&<OpeningTooltip item={hover.item} review={review} x={hover.x} y={hover.y}/>}</section>;

 if(!sheet){
  const count=(t:Tab)=>t==='computo'?data.items.length:cards.filter(c=>c.tab===t).length;
  const budget=budgetTotals(data.items);
  const download=()=>{const url=URL.createObjectURL(new Blob(['\ufeff'+budgetCsv(budget.rows)],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='casa-angel-aberturas-computo.csv';a.click();URL.revokeObjectURL(url)};
  return <section className="openingsDesk sheetExplorer" aria-label="Láminas de aberturas">
   <div className="sheetHeading"><div><p className="eyebrow">CASA ÁNGEL / ABERTURAS</p><h3>Láminas de aberturas</h3><p>{cards.length} láminas · {data.counts.windows} ventanas · {data.counts.doors} puertas · {data.counts.curtainWalls} muros cortina. Elegí una lámina para ver sus dibujos.</p></div></div>
   {pending.length>0&&<p className="openingPendingLine">✎ {pending.length} {pending.length===1?'nota':'notas'} para corregir en Revit <button onClick={copyPending}>Copiar lista</button>{copied&&<small> {copied}</small>}</p>}
   <div className="sheetTabs">{TABS.filter(([t])=>count(t)).map(([t,label])=><button key={t} aria-pressed={tab===t} onClick={()=>setTab(t)}>{label} · {count(t)}</button>)}</div>
   {tab==='computo'&&<section className="openingBudget">
    <div className="openingTotals">{([['Ventanas',budget.windows],['Puertas',budget.doors],['Muros cortina',budget.curtainWalls],['Total',budget.total]] as const).map(([label,t])=><div key={label} className={label==='Total'?'total':''}><small>{label} · {t.count}</small><strong>{n2(t.area)} m²</strong><span>{n2(t.perimeter)} m lineales de marco</span></div>)}</div>
    {budget.glass>0&&<p className="openingGlass">Vidrio según Revit: <b>{n2(budget.glass)} m²</b>{budget.profiles>0?<> · montantes de muros cortina: <b>{n2(budget.profiles)} m</b></>:null}</p>}
    <p className="openingSub">Superficie = ancho × alto de cada abertura (muros cortina: largo × alto del conjunto). Metros lineales = contorno exterior del marco, sin montantes intermedios. Valores de Revit, sin desperdicio.</p>
    <button className="openingDownload" onClick={download}>Descargar planilla para proveedores (CSV)</button>
    <table className="openingBudgetTable"><thead><tr><th>Tipo</th><th>Medida</th><th>Cant.</th><th>m² c/u</th><th>m² total</th><th>m marco</th></tr></thead><tbody>{budget.rows.map(r=><tr key={r.key}><td><b>{r.type}</b><small>{KIND[r.category]} · {r.codes.join(' · ')}</small></td><td>{r.size.replace(/\./g,',')}</td><td>{r.count}</td><td>{n2(r.unitArea)}</td><td><b>{n2(r.area)}</b></td><td>{n2(r.perimeter)}</td></tr>)}</tbody></table>
    {(data.reviewCases||[]).length>0&&<p className="openingAlert">⚠ En revisión, pueden cambiar el cómputo: {(data.reviewCases||[]).map(c=>`${c.code} (${c.title})`).join(' · ')}.</p>}
   </section>}
   {tab!=='computo'&&groupSheets(cards,tab).map(g=><section key={g.title} className="openingGroup"><h4 className="openingGroupTitle">{g.title} <small>{g.sheets.length} {g.sheets.length===1?'lámina':'láminas'}</small></h4>
    <div className="sheetGrid">{g.sheets.map(c=>{const codes=c.itemIds.map(id=>byId.get(id)?.code).filter((x):x is string=>!!x);return <button key={c.key} className="sheetCard" onClick={()=>open(c.key)}>{c.thumbnail?<img src={c.thumbnail} alt={'Lámina '+c.name} loading="lazy"/>:<div className="openingNoThumb">Sin vista previa</div>}<span className="sheetHoverTitle" aria-hidden="true">{c.name}</span><span><small>{c.number}</small><strong>{c.name}</strong>{c.tab!=='aberturas'&&<span className="openingCodes">{codes.map(code=><b key={code}>{code}</b>)}</span>}<em>{c.views.length} dibujos{c.tab==='locales'?` · ${codes.length} ${codes.length===1?'abertura':'aberturas'}`:''}</em></span></button>})}</div>
   </section>)}
  </section>;
 }

 const sheetItems=sheet.itemIds.map(id=>byId.get(id)).filter((i):i is Item=>!!i);
 const itemOf=(v:SheetView)=>v.code?byCode.get(v.code):sheetItems.length===1?sheetItems[0]:undefined;
 const reviewCase=sheet.tab==='revision'?data.reviewCases?.find(c=>`case-${c.code}`===sheet.key):undefined;
 const light=lightbox===null?undefined:views[lightbox],lightItem=light&&itemOf(light),lightItems=lightItem?[lightItem]:light?.tags?.length?light.tags.map(c=>byCode.get(c)).filter((i):i is Item=>!!i):sheetItems;
 return <section className="openingsDesk sheetExplorer">
  <div className="sheetHeading"><div><p className="eyebrow">CASA ÁNGEL / ABERTURAS / {sheet.group.toUpperCase()}</p><h3>{sheet.name}</h3><p>{sheet.number}</p></div><button className="sheetBack" onClick={()=>open(null)}><ArrowLeft size={15}/>Todas las láminas</button></div>
  <div className="sheetTabs"><span className="openingTabHint">Tocá un dibujo para ampliarlo</span>{sheet.pdf&&<a href={sheet.pdf} target="_blank" rel="noreferrer">PDF de la lámina <Download size={14}/></a>}{sheet.sheetId&&<RevitOpenButton id={sheet.sheetId} label="Abrir en Revit"/>}</div>
  {reviewCase&&<div className="openingCase"><p><b>Qué pasa:</b> {reviewCase.observation}</p><p><b>Qué habría que hacer:</b> {reviewCase.proposedCorrection}</p></div>}
  <div className="sheetCanvas openingSheet" style={{aspectRatio:String(SHEET_ASPECT)}}>{sheet.preview&&<img className="openingPreview" src={sheet.preview} alt="" aria-hidden="true"/>}<VectorImage src={sheet.image} alt={'Lámina '+sheet.name}/>{views.map((v,index)=>{const r=v.region||regions[v.id];return r?<button key={v.id} className="sheetHotspot" aria-label={'Ampliar '+v.name} style={{left:`${r[0]*100}%`,top:`${r[1]*100}%`,width:`${(r[2]-r[0])*100}%`,height:`${(r[3]-r[1])*100}%`}} onClick={()=>zoom(index)} {...hoverOn(itemOf(v))}><span>{v.name} ↗</span></button>:null})}</div>
  <h4 className="openingGroupTitle">Dibujos de esta lámina</h4>
  <div className="projectViewCards openingViewCards">{views.map((v,index)=>{const item=itemOf(v);return <button key={v.id} onClick={()=>zoom(index)} {...hoverOn(item)}><span className="openingViewPreview"><TrimmedDrawing src={v.image} alt={v.name}/></span><span className="psViewCardCopy"><strong>{item&&<span className="openingTag">{item.code}</span>}{v.name}</strong><small>Escala 1:{v.scale}{v.dimensions?.length?` · ${v.dimensions.length} cotas`:''}</small><span>Ampliar ↗</span></span></button>})}</div>
  <h4 className="openingGroupTitle">{sheetItems.length===1?'La abertura':'Aberturas de esta lámina'} <small>{sheetItems.length}</small></h4>
  <div className="openingCards">{sheetItems.map(i=>elementCard(i,sheet))}</div>
  {light&&<div className="openingLightbox" role="dialog" aria-modal="true" aria-label={'Dibujo ampliado · '+light.name}>
   <div className="openingLightboxMain"><DrawingViewport aspect={lightCrop?.aspect||1.4} identity={String(light.id)} controls={<div className="openingLightboxBar"><strong>{light.name}</strong><span>1:{light.scale} · {sheet.name}</span><button onClick={()=>zoom((lightbox!-1+views.length)%views.length)} aria-label="Dibujo anterior">←</button><button onClick={()=>zoom((lightbox!+1)%views.length)} aria-label="Dibujo siguiente">→</button></div>}><div className="openingHoverArea" {...hoverOn(lightItem)}><TrimmedDrawing key={light.id} src={light.image} alt={light.name} onCrop={onLightCrop} boxes={light.elements} onBox={(code,x,y)=>{const it=code?byCode.get(code):undefined;setHover(it?{item:it,x,y}:null)}}/></div></DrawingViewport></div>
   <aside className="openingLightboxSide"><button className="openingLightboxClose" onClick={()=>setLightbox(null)}>Cerrar · Esc</button>
    {light.dimensions?.length?<section className="openingViewDims"><h5>Cotas de este dibujo</h5>{light.dimensions.map((d,i)=><p key={i}>{d.code&&!lightItem?<span className="openingTag">{d.code}</span>:null}{d.label}: <b>{dimensionText(d.values_m)}</b></p>)}</section>:null}
    {lightItems.map(i=>elementCard(i,sheet))}
   </aside>
  </div>}
  {hover&&<OpeningTooltip item={hover.item} review={review} x={hover.x} y={hover.y}/>}
 </section>;
}
