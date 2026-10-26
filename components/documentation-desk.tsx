'use client';
import {useEffect,useState} from 'react';
import {openingsHref,rubricHref,urbeRubricHref,type DocumentationRoute} from '../lib/documentation-route';
import RubroDesk from './rubro-desk';
import {RUBROS,URBE_RUBROS} from '../lib/rubros';
import './documentation-desk.css';
import {ArrowUpRight,FileText} from 'lucide-react';
import SanitarySheets from './sanitary-sheets';
import OpeningsDesk from './openings-desk';
import StructureDesk from './structure-desk';
import type {OpeningsReview} from '../lib/openings-review';
import {ExportButton} from './documentation-export';
export default function DocumentationDesk({project,isAngel,isUrbe=false,onPrepare,route,openingsReview,onSaveOpeningsReview,disabled}:{project:{id:string;name:string},isAngel:boolean,isUrbe?:boolean,onPrepare:(text:string)=>void,route?:DocumentationRoute|null,openingsReview?:OpeningsReview,onSaveOpeningsReview?:(next:OpeningsReview)=>Promise<boolean>,disabled?:boolean}){
 const [rubric,setRubric]=useState(route?.rubric||(isUrbe?URBE_RUBROS[0].name:'Sanitaria'));
 useEffect(()=>{if(route)setRubric(route.rubric)},[route]);
 // Oficinas Urbetrack: láminas de la carpeta técnica entregada, separadas por rubro.
 if(isUrbe){const current=URBE_RUBROS.find(x=>x.name===rubric)||URBE_RUBROS[0];return <div className="docDesk"><div className="docIntro"><p className="eyebrow">DOCUMENTACIÓN / CARPETA TÉCNICA</p><h2>La obra, lámina por lámina.</h2><p>Carpeta técnica entregada de los pisos 11, 12 y 13, separada por rubro. Cada página del PDF es una lámina.</p><ExportButton project={project} current={current.name}/></div><nav className="docRubrics" aria-label="Rubros de documentación">{URBE_RUBROS.map(r=><button key={r.key} aria-pressed={current===r} className={current===r?'active':''} onClick={()=>{setRubric(r.name);window.location.hash=urbeRubricHref(r.name)}}><strong>{r.name}</strong><small>{r.subtitle}</small></button>)}</nav><RubroDesk key={current.key} rubro={current} base="/urbetrack/rubros" project="Oficinas Urbetrack"/></div>}
 return <div className="docDesk"><div className="docIntro"><p className="eyebrow">DOCUMENTACIÓN / FUENTES DEL PROYECTO</p><h2>Del modelo al plano.</h2><p>Los archivos pertenecen al proyecto. Cada rubro reúne sus revisiones y entregas sobre esas mismas fuentes.</p>{isAngel&&<button onClick={()=>{window.location.hash='#presupuesto/angel'}}>Del modelo al presupuesto por rubro <ArrowUpRight size={14}/></button>}<ExportButton project={project} current={rubric}/></div><nav className="docRubrics" aria-label="Rubros de documentación">{['Sanitaria','Aberturas','Estructura',...RUBROS.map(x=>x.name)].map(r=><button key={r} aria-pressed={rubric===r} className={rubric===r?'active':''} onClick={()=>{setRubric(r);if(isAngel&&r==='Aberturas'){window.location.hash=openingsHref()}else if(isAngel&&rubricHref(r)&&r!=='Sanitaria'){window.location.hash=rubricHref(r)}else if(route){window.history.replaceState(null,'',window.location.pathname+window.location.search);window.dispatchEvent(new HashChangeEvent('hashchange'))}}}><strong>{r}</strong><small>{r==='Aberturas'?'Puertas · ventanas · cerramientos':r==='Estructura'?'Hormigón · muros · losas':RUBROS.find(x=>x.name===r)?RUBROS.find(x=>x.name===r)!.subtitle:r==='Sanitaria'?'Instalaciones y cómputos':'Planos del rubro'}</small></button>)}</nav>
 {isAngel&&rubric==='Sanitaria'?<SanitarySheets/>:isAngel&&rubric==='Estructura'?<StructureDesk/>:isAngel&&RUBROS.some(x=>x.name===rubric)?<RubroDesk key={rubric} rubro={RUBROS.find(x=>x.name===rubric)!}/>:isAngel&&rubric==='Aberturas'?<OpeningsDesk caseCode={route?.caseCode} review={openingsReview} onSaveReview={onSaveOpeningsReview} disabled={disabled}/>:<div className="docPending"><FileText size={27}/><h3>{rubric} · por preparar</h3><p>{rubric==='Eléctrica'?'Primero hay que diseñar la instalación. Todavía no hay una documentación eléctrica verificada.':'Todavía no hay un cruce verificado de este rubro para el proyecto seleccionado.'}</p><button onClick={()=>onPrepare(`Preparar una revisión de documentación ${rubric.toLowerCase()} del proyecto. Identificar las fuentes vigentes y los faltantes antes de proponer cambios o cantidades.`)}>Preparar pedido <ArrowUpRight size={14}/></button></div>}
 </div>
}

