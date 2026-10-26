'use client';
import {useState} from 'react';
import {quantityWorkbook} from '../lib/quantity-workbook.mjs';
import {exportName,fileUrl,saveFile,type ExportedFile,type ExportProject} from '../lib/export-files';
import './documentation-export.css';
export type QuantitySheet={name:string;columns:string[];rows:(string|number|null|undefined)[][]};
export const offerColumns=['Marca ofrecida','Modelo ofrecido','Precio unitario','Moneda','Plazo de entrega','Observaciones del proveedor'];
export default function QuantityExport({project={id:'angel',name:'Casa Ángel'},label,scope,sheets,button='Exportar cómputo a Excel'}:{project?:ExportProject;label:string;scope:string;sheets:QuantitySheet[];button?:string}){
 const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[file,setFile]=useState<ExportedFile>();
 async function run(){setBusy(true);setMessage('Preparando Excel…');setFile(undefined);try{const bytes=await quantityWorkbook({project:project.name,label,scope,sheets});setMessage('Guardando en Archivos…');const result=await saveFile(project.id,{name:exportName(project.name,label,'xlsx'),format:'xlsx',rubros:[label.slice(0,100)],sheets:sheets.length+1},new Blob([bytes as BlobPart],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}));setFile(result);setMessage('Excel guardado en Archivos. Compatible con Google Sheets.')}catch(e){setMessage((e as Error).message)}finally{setBusy(false)}}
 return <div className="quantityExport"><button className="exportAction" disabled={busy||!sheets.some(s=>s.rows.length)} onClick={run}>{busy?'Exportando…':button}</button><p role="status">{message}{file&&<a href={fileUrl(file,true)}>Descargar Excel</a>}</p></div>;
}
