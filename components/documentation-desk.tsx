'use client';
import {useEffect,useState} from 'react';
import {openingsHref,type DocumentationRoute} from '../lib/documentation-route';
import './documentation-desk.css';
import {ArrowUpRight,FileText} from 'lucide-react';
import SanitarySheets from './sanitary-sheets';
import OpeningsDesk from './openings-desk';
export default function DocumentationDesk({isAngel,onPrepare,route}:{isAngel:boolean,onPrepare:(text:string)=>void,route?:DocumentationRoute|null}){
 const [rubric,setRubric]=useState(route?.rubric||'Sanitaria');
 useEffect(()=>{if(route)setRubric(route.rubric)},[route]);
 return <div className="docDesk"><div className="docIntro"><p className="eyebrow">DOCUMENTACIÓN / FUENTES DEL PROYECTO</p><h2>Del modelo al plano.</h2><p>Los archivos pertenecen al proyecto. Cada rubro reúne sus revisiones y entregas sobre esas mismas fuentes.</p></div><nav className="docRubrics" aria-label="Rubros de documentación">{['Sanitaria','Eléctrica','Aberturas','Arquitectura','Estructura'].map(r=><button key={r} aria-pressed={rubric===r} className={rubric===r?'active':''} onClick={()=>{setRubric(r);if(isAngel&&r==='Aberturas'){window.location.hash=openingsHref()}else if(route){window.history.replaceState(null,'',window.location.pathname+window.location.search);window.dispatchEvent(new HashChangeEvent('hashchange'))}}}><strong>{r}</strong><small>{r==='Aberturas'?'Puertas · ventanas · cerramientos':r==='Sanitaria'?'Instalaciones y cómputos':'Planos del rubro'}</small></button>)}</nav>
 {isAngel&&rubric==='Sanitaria'?<SanitarySheets/>:isAngel&&rubric==='Aberturas'?<OpeningsDesk caseCode={route?.caseCode}/>:<div className="docPending"><FileText size={27}/><h3>{rubric} · por preparar</h3><p>{rubric==='Eléctrica'?'Primero hay que diseñar la instalación. Todavía no hay una documentación eléctrica verificada.':'Todavía no hay un cruce verificado de este rubro para el proyecto seleccionado.'}</p><button onClick={()=>onPrepare(`Preparar una revisión de documentación ${rubric.toLowerCase()} del proyecto. Identificar las fuentes vigentes y los faltantes antes de proponer cambios o cantidades.`)}>Preparar pedido <ArrowUpRight size={14}/></button></div>}
 </div>
}

