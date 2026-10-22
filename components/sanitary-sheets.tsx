'use client';
import {useState} from 'react';
import sheets from '../data/sanitary-sheets.json';
import ProjectSanitary from './project-sanitary';
import './sanitary-sheets.css';
export default function SanitarySheets(){
 const [globalProject,setGlobalProject]=useState(false),[sheet,setSheet]=useState<number|null>(null);
 if(globalProject)return <ProjectSanitary key="all" page={null} onBack={()=>setGlobalProject(false)}/>;
 if(sheet!==null)return <ProjectSanitary key={sheet} page={sheet} onBack={()=>setSheet(null)}/>;
 return <section className="sheetExplorer" aria-label="Láminas sanitarias">
  <div className="sheetHeading"><div><p className="eyebrow">CASA ÁNGEL / SANITARIAS</p><h3>Láminas del proyecto</h3><p>Elegí un ambiente para revisar su documentación.</p></div></div>
  <div className="sheetTabs"><button onClick={()=>setGlobalProject(true)}>Cómputo general · todas las láminas ↗</button></div>
  <div className="sheetGrid">{sheets.map(s=><button key={s.page} className="sheetCard" onClick={()=>setSheet(s.page)}><img src={s.image} alt={`Lámina ${s.number} ${s.name}`} loading="lazy"/><span className="sheetHoverTitle" aria-hidden="true">{s.name}</span><span><small>{s.number}</small><strong>{s.name}</strong><em>Vistas y cómputo · R13</em></span></button>)}</div>
 </section>
}
