'use client';
import {useState} from 'react';
import inventory from '../data/urbetrack.json';
const local='http://127.0.0.1:18763/';
export default function Urbetrack(){
 const [topic,setTopic]=useState('todos');
 const videos=inventory.videos.filter(v=>topic==='todos'||v.topic===topic);
 const editor=(id:string,view:string)=>`${local}Storyboard_Urbetrack_R01.html?video=${encodeURIComponent(id)}&view=${view}`;
 return <section className="teamSpace"><p className="eyebrow">MESA EDITORIAL / URBETRACK</p><h2>Continuar las 45 piezas</h2>
 <p>Guiones, voz, versiones y storyboard del proyecto Rivadavia. Inventario comprobado el {inventory.verifiedAt}, revisión {inventory.revision}. Los cambios posteriores se consultan en el editor.</p>
 <div className="areaNote"><div><strong>Editor en esta computadora</strong><p>Los accesos abren el servicio local en otra pestaña. Requieren esta PC y el editor encendido. Las notas, correcciones e historial se guardan allí; esta oficina conserva un inventario de referencia, sin sincronización automática.</p><a href={editor('08.01','montage')} target="_blank" rel="noreferrer">Abrir mesa editorial ↗</a> · <a href="/Iniciar_Urbetrack.ps1" download>Descargar iniciador para Windows</a></div></div>
 <details><summary>Biblioteca y puesta en marcha</summary><p>El iniciador comprueba el servicio y abre el editor existente. Para abrir las carpetas de originales o audios, ejecutalo con -Carpeta biblioteca o -Carpeta audios. Conserva los originales en su ubicación actual.</p><p>Biblioteca: URBE MARKETING / 01_BIBLIOTECA_ORIGINALES. Audio: 05_AUDIOS. Las selecciones por video conservan referencias a esas fuentes.</p><p>En otra computadora estos enlaces no alcanzan los archivos de tu PC. El acceso remoto y la sincronización quedan pendientes.</p></details>
 <p><strong>36 en revisión · 9 exportados para revisión · 2 con voz pendiente</strong></p>
 <p>“Exportado” no significa aprobado. Editar un montaje guarda instrucciones; el MP4 cambia al renderizar. Una revisión de exportación anterior a la revisión general del proyecto no demuestra por sí sola que ese video tenga cambios pendientes.</p>
 <label>Filtrar tema<select value={topic} onChange={e=>setTopic(e.target.value)}><option value="todos">Todos los temas</option>{Array.from({length:15},(_,i)=>String(i+1).padStart(2,'0')).map(t=><option key={t} value={t}>Tema {t}</option>)}</select></label>
 <div className="hubCards">{videos.map(v=><article key={v.id} style={{padding:'1rem',border:'1px solid #ddd',borderRadius:12}}><small>{v.id} · {v.status}</small><h3>{v.title}</h3><p>{v.exportRevision?`MP4 exportado desde revisión ${v.exportRevision}`:'MP4 borrador · revisión de render sin registrar'}</p><div className="handoff"><a href={editor(v.id,'script')} target="_blank" rel="noreferrer">Guion ↗</a> · <a href={local+encodeURIComponent(v.audio)} target="_blank" rel="noreferrer">Audio ↗</a> · <a href={local+encodeURIComponent(v.render)} target="_blank" rel="noreferrer">MP4 ↗</a> · <a href={editor(v.id,'archive')} target="_blank" rel="noreferrer">Versiones ↗</a> · <a href={editor(v.id,'montage')} target="_blank" rel="noreferrer">Storyboard y correcciones ↗</a></div></article>)}</div>
 <details><summary>Estados de revisión y render</summary><p>Borrador: pieza sin aprobación. En revisión: pendiente de revisión individual. Aprobado: solo con confirmación explícita del usuario. Render pendiente: hay una edición del video todavía sin exportar; debe verificarse contra el montaje utilizado, sin inferirlo de la fecha o del número global.</p><p>01.01 y 01.02 conservan voz pendiente. No se modificaron aprobaciones ni comentarios al incorporar este inventario.</p></details>
 </section>
}
