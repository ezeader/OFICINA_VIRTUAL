'use client';
import {useState} from 'react';
import sheets from '../data/sanitary-sheets.json';
import ProjectSanitary from './project-sanitary';
import './sanitary-sheets.css';
import './openings-desk.css';
type Sheet=(typeof sheets)[number];
// Plano principal primero: cada nivel abre con su planta completa y debajo las láminas por ambiente de ese nivel.
const byNumber=(re:RegExp)=>sheets.filter(s=>re.test(s.number));
const levels=[{title:'Planta baja',plan:byNumber(/^AFyAC\.00$/)[0],groups:[{title:'Ambientes',sheets:byNumber(/^IS\.00/)}]},{title:'Planta alta y entrepiso',plan:byNumber(/^AFyAC\.01/)[0],groups:[{title:'Planta alta',sheets:byNumber(/^IS\.01/)},{title:'Entrepiso',sheets:byNumber(/^IS\.02/)}]}].filter(l=>l.plan);
const others=[{title:'Tanques',sheets:byNumber(/^AFyAC$/)},{title:'Cortes',sheets:byNumber(/^IS\.0C/)}];
export default function SanitarySheets(){
 const [globalProject,setGlobalProject]=useState(false),[sheet,setSheet]=useState<number|null>(null);
 if(globalProject)return <ProjectSanitary key="all" page={null} onBack={()=>setGlobalProject(false)}/>;
 if(sheet!==null)return <ProjectSanitary key={sheet} page={sheet} onBack={()=>setSheet(null)}/>;
 const grid=(rows:Sheet[])=><div className="sheetGrid">{rows.map(s=><button key={s.page} className="sheetCard" onClick={()=>setSheet(s.page)}><img src={s.image} alt={`Lámina ${s.number} ${s.name}`} loading="lazy"/><span className="sheetHoverTitle" aria-hidden="true">{s.name}</span><span><small>{s.number}</small><strong>{s.name}</strong><em>Vistas y cómputo · R13</em></span></button>)}</div>;
 return <section className="sheetExplorer openingsDesk" aria-label="Láminas sanitarias">
  <div className="sheetHeading"><div><p className="eyebrow">CASA ÁNGEL / SANITARIAS</p><h3>Láminas del proyecto</h3><p>Arriba de cada nivel, la planta completa; debajo, las láminas por ambiente.</p></div></div>
  <div className="sheetTabs"><button onClick={()=>setGlobalProject(true)}>Cómputo general · todas las láminas ↗</button></div>
  {levels.length>1&&<nav className="rubroLevelJump" aria-label="Niveles">{levels.map(l=><button key={l.title} onClick={()=>document.getElementById('nivel-'+l.title)?.scrollIntoView({behavior:'smooth'})}>{l.title}</button>)}</nav>}
  {levels.map(l=><section key={l.title} id={'nivel-'+l.title} className="openingGroup rubroLevel"><h4 className="openingGroupTitle">{l.title} <small>{l.groups.reduce((n,g)=>n+g.sheets.length,1)} láminas</small></h4>
   <button className="rubroLevelPlan" onClick={()=>setSheet(l.plan.page)}><span className="rubroLevelDrawing"><img src={l.plan.image} alt={'Planta completa · '+l.title}/></span><span className="rubroLevelCaption"><small>{l.plan.number} · plano principal</small><strong>{l.plan.name}</strong><em>Planta completa · tocá para abrir la lámina</em></span></button>
   {l.groups.filter(g=>g.sheets.length).map(g=><div key={g.title} className="rubroLevelGroup"><h5>{g.title} <small>{g.sheets.length} láminas</small></h5>{grid(g.sheets)}</div>)}
  </section>)}
  {others.filter(g=>g.sheets.length).map(g=><section key={g.title} className="openingGroup"><h4 className="openingGroupTitle">{g.title} <small>{g.sheets.length} {g.sheets.length===1?'lámina':'láminas'}</small></h4>{grid(g.sheets)}</section>)}

 </section>
}
