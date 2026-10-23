'use client';
import {useState} from 'react';
import {ArrowUpRight,Check,Download,FileText} from 'lucide-react';
import audit from '../data/casa-angel-pilot.json';
import SanitaryReview from './sanitary-review';
import SanitarySheets from './sanitary-sheets';
import OpeningsDesk from './openings-desk';
export const auditDate=()=>new Date(audit.checkedAt).toLocaleString('es-AR',{timeZone:'America/Argentina/Buenos_Aires',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
export default function DocumentationDesk({isAngel,onPrepare}:{isAngel:boolean,onPrepare:(text:string)=>void}){
 const [rubric,setRubric]=useState('Sanitaria'),[filter,setFilter]=useState('AF'),[query,setQuery]=useState(''),[image,setImage]=useState('control');
 const rows=audit.rows.filter(r=>(filter==='Todos'||r.group===filter)&&`${r.id} ${r.type} ${r.diameter_mm}`.toLowerCase().includes(query.toLowerCase()));
 return <div className="docDesk"><div className="docIntro"><p className="eyebrow">DOCUMENTACIÓN / FUENTES DEL PROYECTO</p><h2>Del modelo al plano.</h2><p>Los archivos pertenecen al proyecto. Cada rubro reúne sus revisiones y entregas sobre esas mismas fuentes.</p></div><nav className="docRubrics" aria-label="Rubros de documentación">{['Sanitaria','Eléctrica','Aberturas','Arquitectura','Estructura'].map(r=><button key={r} aria-pressed={rubric===r} className={rubric===r?'active':''} onClick={()=>setRubric(r)}>{r}</button>)}</nav>
 {isAngel&&rubric==='Sanitaria'?<SanitarySheets/>:isAngel&&rubric==='Aberturas'?<OpeningsDesk/>:<div className="docPending"><FileText size={27}/><h3>{rubric} · por preparar</h3><p>{rubric==='Eléctrica'?'Primero hay que diseñar la instalación. Todavía no hay una documentación eléctrica verificada.':'Todavía no hay un cruce verificado de este rubro para el proyecto seleccionado.'}</p><button onClick={()=>onPrepare(`Preparar una revisión de documentación ${rubric.toLowerCase()} del proyecto. Identificar las fuentes vigentes y los faltantes antes de proponer cambios o cantidades.`)}>Preparar pedido <ArrowUpRight size={14}/></button></div>}
 </div>
}

