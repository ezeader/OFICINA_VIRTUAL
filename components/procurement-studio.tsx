'use client';
import {useState} from 'react';
import CompassMark from './compass-mark';
import RubroBudget from './rubro-budget';
import QuoteDesk,{type QuoteSection} from './quote-desk';
import ProcurementGuide,{guideSteps} from './procurement-guide';
import {emptyProcurement,type ProcurementData} from '@/lib/procurement';
import './procurement-studio.css';
type Project={id:string;name:string};
const TABS=['Presupuesto por rubro','Cómputo','Proveedores','Presupuestos'] as const;
type Tab=typeof TABS[number];

export default function ProcurementStudio({value,projects,disabled,onSave,onDocumentation,initialProject,initialTab}:{value?:ProcurementData;projects:Project[];disabled:boolean;onSave:(v:ProcurementData)=>Promise<boolean>;onDocumentation:(id:string)=>void;initialProject?:string;initialTab?:string}){
 const data=value||emptyProcurement();
 // #presupuesto/<proyecto>/cotizaciones/tutorial abre la guía.
 const [guide,setGuide]=useState<number|null>(()=>typeof window!=='undefined'&&window.location.hash.endsWith('/tutorial')?0:null);
 const [tab,setTab]=useState<Tab>(TABS.includes(initialTab as Tab)?initialTab as Tab:'Presupuesto por rubro'),[project,setProject]=useState(initialProject||projects.find(p=>p.id==='angel')?.id||projects[0]?.id||''),[message,setMessage]=useState(''),[error,setError]=useState('');
 const projectName=projects.find(p=>p.id===project)?.name||'';
 async function persist(next:ProcurementData,text:string){setError('');const ok=await onSave(next);if(ok)setMessage(text);return ok;}
 return <section className="procurement">
 <div className="pcHeading"><div className="pcTitle"><CompassMark/><div><p className="eyebrow">ADER STUDIO</p><h1>Presupuestos y compras</h1><p>Del cómputo del modelo al número final de cada rubro.</p></div></div><label>Proyecto<select aria-label="Proyecto del presupuesto" value={project} onChange={e=>setProject(e.target.value)}>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label><button className="pcHelp" aria-pressed={guide!==null} onClick={()=>{if(guide!==null){setGuide(null);return}setGuide(0);setTab(guideSteps[0].tab as Tab)}}>Cómo se usa</button></div>
 <nav className="pcTabs" aria-label="Presupuestos y compras">{TABS.map(t=><button key={t} className={tab===t?'active':''} onClick={()=>setTab(t)}>{t}</button>)}</nav>
 {error&&<p className="pcError" role="alert">{error}<button onClick={()=>setError('')}>Cerrar</button></p>}{message&&<p className="pcNotice" role="status">{message}<button onClick={()=>setMessage('')}>Cerrar</button></p>}
 {guide!==null&&<ProcurementGuide step={guide} onStep={n=>{setGuide(n);setTab(guideSteps[n].tab as Tab)}} onClose={()=>setGuide(null)}/>}
 {tab==='Presupuesto por rubro'&&<RubroBudget key={project} project={project} projectName={projectName} value={data.rubroBudget?.[project]} disabled={disabled} onSave={(v,text)=>persist({...data,rubroBudget:{...data.rubroBudget,[project]:v}},text)} onDocumentation={()=>onDocumentation(project)}/>}
 {tab!=='Presupuesto por rubro'&&<QuoteDesk key={project} section={tab as QuoteSection} value={data.quotes?.[project]} disabled={disabled} onSave={(v,text)=>persist({...data,quotes:{...data.quotes,[project]:v}},text)}/>}
 </section>;
}
