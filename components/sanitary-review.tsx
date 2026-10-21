'use client';
import {useState} from 'react';
import {ArrowUpRight,Download,FileText} from 'lucide-react';
import review from '../data/casa-angel-r02.json';
const systems:Record<string,{name:string;color:string}>={AF:{name:'Agua fría',color:'#0055aa'},AC:{name:'Agua caliente',color:'#d92727'},CS:{name:'Cloacal secundario',color:'#a28a00'},CP:{name:'Cloacal primario',color:'#800020'}};
const pdf='/casa-angel/Casa-Angel-sanitarias-cotas-R02.pdf';
export default function SanitaryReview(){
 const [system,setSystem]=useState('Todos'),[query,setQuery]=useState('');
 const rows=review.rows.filter(r=>(system==='Todos'||r.group===system)&&`${r.code} ${r.id} ${r.diameterMm}`.toLowerCase().includes(query.toLowerCase()));
 return <section className="sanitaryReview" aria-label="Revisión sanitaria R02">
  <p className="eyebrow">CASA ÁNGEL / REVISIÓN R02</p><h3>Cada caño, una referencia.</h3>
  <p className="reviewIntro">672 caños identificados por código e ID de Revit. Las 16 láminas originales se acompañan con detalles de cotas e índice para revisar cada recorrido.</p>
  <div className="docActions"><a href={pdf} target="_blank" rel="noreferrer"><FileText size={15}/>Abrir planos y cotas <ArrowUpRight size={13}/></a><a href="/casa-angel/Casa-Angel-sanitarias-R02-datos.json" download><Download size={14}/>Descargar datos</a></div>
  <div className="docGroupGrid">{review.groups.map(g=><div key={g.group} style={{borderTop:`3px solid ${systems[g.group].color}`}}><small>{systems[g.group].name}</small><strong style={{color:systems[g.group].color}}>{Number(g.sum_labels_m).toLocaleString('es-AR',{minimumFractionDigits:3,maximumFractionDigits:3})} m</strong><span>{g.count} caños únicos</span></div>)}</div>
  <div className="docScope"><strong>Revisión para controlar las medidas</strong><p>Los caños repetidos entre vistas se cuentan una sola vez. Algunas vistas tienen escalas u orientaciones distintas del PDF: hay {review.pendingViews} registros gráficos pendientes de cotejo. El documento señala estos sectores y distingue las ampliaciones del plano de los esquemas del modelo.</p></div>
  <div className="docFilter"><select aria-label="Subrubro sanitario" value={system} onChange={e=>setSystem(e.target.value)}><option>Todos</option>{Object.entries(systems).map(([key,s])=><option key={key} value={key}>{s.name}</option>)}</select><input aria-label="Buscar caño por código, ID o diámetro" placeholder="Código, ID o diámetro…" value={query} onChange={e=>setQuery(e.target.value)}/></div>
  <p className="reviewCount">{rows.length} de 672 caños · tocá «Ver cota» para abrir el detalle.</p>
  <div className="docTableWrap"><table><thead><tr><th>Código</th><th>ID Revit</th><th>Ø mm</th><th>Longitud m</th><th>Detalle</th></tr></thead><tbody>{rows.map(r=><tr key={r.id}><td style={{color:systems[r.group].color,fontWeight:600}}>{r.code}</td><td>{r.id}</td><td>{r.diameterMm}</td><td>{Number(r.lengthM).toLocaleString('es-AR',{minimumFractionDigits:3,maximumFractionDigits:3})}</td><td><a className="reviewDetailLink" href={`${pdf}#page=${r.detailPage}`} target="_blank" rel="noreferrer">Ver cota <ArrowUpRight size={11}/></a></td></tr>)}</tbody></table>{!rows.length&&<p>No hay caños con ese filtro.</p>}</div>
  <p className="docCaption">Longitudes completas del eje en 3D, redondeadas a 0,001 m. Los tramos que continúan fuera de una vista están señalados. Cómputo de caños; accesorios y presupuesto se preparan en otra etapa.</p>
 </section>;
}
