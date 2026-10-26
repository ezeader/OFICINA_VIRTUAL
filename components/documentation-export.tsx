'use client';
// Botón «Exportar» de Documentación y lista de exportaciones de la pestaña Archivos.
import {useEffect,useState} from 'react';
import {Download,FileDown,Trash2,X} from 'lucide-react';
import {deleteFile,downloadFile,exportRubros,exportableRubros,FILES_CHANGED,listFiles,type ExportProject,type ExportedFile} from '../lib/documentation-export';

const mb=(n:number)=>(n/1048576).toLocaleString('es-AR',{maximumFractionDigits:1})+' MB';

export function ExportButton({project,current,onDone}:{project:ExportProject;current?:string;onDone?:()=>void}){
 const all=exportableRubros(project.id);
 const [open,setOpen]=useState(false),[chosen,setChosen]=useState<string[]>([]),[mode,setMode]=useState<'juntos'|'separados'>('juntos'),[busy,setBusy]=useState(''),[message,setMessage]=useState('');
 if(!all.length)return null;
 const start=()=>{setChosen(current&&all.includes(current)?[current]:all);setMessage('');setBusy('');setOpen(true)};
 const toggle=(r:string)=>setChosen(c=>c.includes(r)?c.filter(x=>x!==r):all.filter(x=>x===r||c.includes(x)));
 const run=async()=>{
  setMessage('');setBusy('Preparando…');
  try{const files=await exportRubros(project,chosen,mode,setBusy);window.dispatchEvent(new Event(FILES_CHANGED));setMessage(files.length?`Listo: ${files.length===1?'1 PDF guardado':files.length+' PDF guardados'} en Archivos.`:'Los rubros elegidos todavía no tienen láminas.');if(files.length)onDone?.()}
  catch(e){setMessage(e instanceof Error?e.message:'No se pudo exportar.')}
  setBusy('');
 };
 return <>
  <button className="docExportButton" onClick={start}><FileDown size={15}/>Exportar</button>
  {open&&<div className="docExportBack" role="dialog" aria-modal="true" aria-label="Exportar láminas"><div className="docExportDialog">
   <header><h3>Exportar láminas a PDF</h3><button aria-label="Cerrar" onClick={()=>setOpen(false)} disabled={!!busy}><X size={18}/></button></header>
   <p className="docExportHint">Elegí los rubros. Los PDF quedan guardados en Archivos para descargarlos.</p>
   <div className="docExportQuick"><button onClick={()=>setChosen(all)}>Todos</button><button onClick={()=>setChosen([])}>Ninguno</button></div>
   <div className="docExportList">{all.map(r=><label key={r}><input type="checkbox" checked={chosen.includes(r)} onChange={()=>toggle(r)}/>{r}</label>)}</div>
   <div className="docExportMode">{([['juntos','Todo en un solo PDF'],['separados','Un PDF por rubro']] as const).map(([m,label])=><button key={m} aria-pressed={mode===m} onClick={()=>setMode(m)}>{label}</button>)}</div>
   {busy&&<p className="docExportStatus" role="status">Exportando · {busy}</p>}
   {message&&<p className="docExportStatus" role="status">{message}</p>}
   <button className="docExportGo" disabled={!chosen.length||!!busy} onClick={run}><FileDown size={15}/>{busy?'Exportando…':`Exportar ${chosen.length===1?'1 rubro':chosen.length+' rubros'}`}</button>
  </div></div>}
 </>;
}

export function ExportedFiles({projectId}:{projectId:string}){
 const [files,setFiles]=useState<ExportedFile[]|null>(null);
 useEffect(()=>{const load=()=>listFiles(projectId).then(setFiles).catch(()=>setFiles([]));load();window.addEventListener(FILES_CHANGED,load);return()=>window.removeEventListener(FILES_CHANGED,load)},[projectId]);
 if(!files)return null;
 return <section className="docExports"><p className="eyebrow">EXPORTACIONES</p>
  {files.length?files.map(f=><article className="psFile" key={f.id}><span>PDF</span><div><h3>{f.name}</h3><small>{f.sheets} {f.sheets===1?'página':'páginas'} · {mb(f.size)} · {new Date(f.date).toLocaleString('es-AR',{dateStyle:'short',timeStyle:'short'})}</small><div className="docExportActions"><button onClick={()=>downloadFile(f)}><Download size={14}/>Descargar</button><button onClick={async()=>{if(confirm(`¿Borrar «${f.name}» de Archivos?`)){await deleteFile(f.id);window.dispatchEvent(new Event(FILES_CHANGED))}}}><Trash2 size={14}/>Borrar</button></div></div></article>)
  :<p className="docExportHint">Todavía no hay exportaciones. Usá «Exportar» en Documentación para generar los PDF de los rubros.</p>}
 </section>;
}
