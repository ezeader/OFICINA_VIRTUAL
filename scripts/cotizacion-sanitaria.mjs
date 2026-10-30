// Cómputo para cotizar la instalación sanitaria de Casa Ángel.
// Fuente: registro único R13 (public/casa-angel/r13/project.json.gz): cada elemento físico una sola vez.
// Salida: data/cotizacion/sanitaria-R13.json (la oficina lo importa en el código).
// Uso: node scripts/cotizacion-sanitaria.mjs [ruta.xlsx para revisar el Excel base]
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {quoteWorkbook} from '../lib/quote-xlsx.ts';

const project=JSON.parse(gunzipSync(readFileSync('public/casa-angel/r13/project.json.gz')));
const OUT='data/cotizacion';
const DATE='30/10/2026';

// Orden por sistema. RV y VM se mantienen aparte, como en la oficina: no se reasignan a otro sistema.
const SYSTEMS=[
 ['AF','Agua fría'],['AC','Agua caliente'],['CP','Cloacal primario'],['CS','Cloacal secundario'],
 ['EQ','Artefactos y equipos'],['VM','Sistema VM (según modelo, a confirmar)'],['RV','Clasificación por revisar en el modelo'],
];
// Longitudes menores a este total por diámetro son tramos de transición dentro de un accesorio: no se compran aparte.
const MIN_PIPE_M=0.2;

const mm=s=>String(s).replace(/ ?mm$/,'').split('x').map(n=>String(Math.round(Number(n)*10)/10).replace('.',',')).join('×');
const angle=t=>{const m=/(\d+(?:\.\d+)?) grados/.exec(t);return m?Number(m[1]):null};
const material=f=>/PPR/.test(f)?'PPR':/Silentium/.test(f)?'PVC Silentium':'PVC';

function pipeLabel(i){
 const d=Math.round(i.diameter_mm);
 if(i.system==='AF')return `Caño PPR termofusión agua fría Ø${d} mm (ref. Amanco Wavin Fusión PN12,5)`;
 if(i.system==='AC')return `Caño PPR termofusión agua caliente Ø${d} mm (ref. Amanco Wavin Fusión; indicar PN)`;
 if(i.system==='CP')return `Caño PVC cloacal Ø${d} mm (ref. Amanco Wavin)`;
 if(i.system==='CS')return `Caño PVC cloacal secundario Ø${d} mm (ref. Amanco Wavin)`;
 if(i.system==='VM')return `Caño Ø${d} mm sistema VM (material según modelo: acero al carbono; a confirmar)`;
 return `Caño ${i.family} Ø${d} mm`;
}
function fittingLabel(i){
 const t=i.type,f=i.family,mat=material(f),size=mm(i.size),a=angle(t);
 if(/Codo/.test(f))return `Codo ${a!=null&&a<67.5?45:90}° ${mat} Ø${size}`;
 if(/Ramal/.test(f))return `Ramal ${a!=null&&(a<67.5||a>112.5)?45:90}° ${mat} Ø${size}`;
 if(/Tee/.test(f))return `Tee ${mat} Ø${size}`;
 if(/Tapa/.test(f))return `Tapa ${mat} Ø${size}`;
 if(/Reductor/.test(f))return `Reducción ${mat} Ø${size}`;
 if(/Buje Reducci/.test(f))return `Buje de reducción PPR con inserto metálico Ø${size}`;
 if(/UniónFusión/.test(f))return `Válvula esférica unión-fusión PPR Ø${size}`;
 if(/CanillaconPalanca/.test(f))return 'Canilla de servicio 3/4" con manija palanca';
 if(/CanillaMariposa/.test(f))return 'Canilla de servicio 3/4" con manija mariposa';
 if(/MetálicaPremium/.test(f))return 'Válvula metálica 3/4" (ref. Amanco Premium)';
 if(/BocadeAcceso/.test(f))return `Boca de acceso PVC Ø${size} con tapa ciega 10×10 cm`;
 if(/DesagüeLineal/.test(f))return 'Desagüe lineal con sifón 90 cm, PVC blanco';
 if(/Pileta3Entradas/.test(f))return `Pileta de patio de 3 entradas Ø${size}`;
 if(/Receptáculo/.test(f))return `Receptáculo de ducha Ø${size}`;
 return `${t} Ø${size}`;
}
const EQUIPMENT=[
 [/^Inodoro$/,'Inodoro: conexión y colocación'],
 [/^Bidet$/,'Bidet: conexión y colocación'],
 [/^Bacha sobre mesada$/,'Bacha de vanitorio: conexión (la bacha se provee con Mesadas)'],
 [/Modern_Sink/,'Pileta de cocina / lavadero: conexión'],
 [/SHOWER COLUMN/,'Columna de ducha: conexión y colocación'],
 [/Roca_5B2250/,'Flor de ducha de techo o pared: conexión y colocación'],
 [/Grundfos/,'Bomba centrífuga (en el modelo, Grundfos NK; función y modelo a confirmar)'],
];
const equipmentLabel=i=>(EQUIPMENT.find(([re])=>re.test(i.family))||[,i.family])[1];
// Artefactos: el material se cotiza solo si el proveedor lo ofrece (modelo a definir). La bomba sí lleva material.
const materialOptional=i=>i.kind==='equipment'&&!/Grundfos/.test(i.family);

const bySystem=new Map(SYSTEMS.map(([k])=>[k,new Map()]));
const transitions=[];
for(const i of project.items){
 const group=bySystem.get(i.system);if(!group)throw Error('Sistema sin sección: '+i.system);
 const label=i.kind==='pipe'?pipeLabel(i):i.kind==='fitting'?fittingLabel(i):equipmentLabel(i);
 const unit=i.kind==='pipe'?'m':'u';
 const row=group.get(label)||{label,unit,quantity:0,elements:0,kind:i.kind,diameter:i.kind==='pipe'?Math.round(i.diameter_mm):0,optionalMaterial:materialOptional(i),family:i.family};
 row.quantity+=i.kind==='pipe'?i.length_m:1;row.elements++;group.set(label,row);
}
const kindOrder={pipe:0,fitting:1,equipment:2};
// La referencia de marca del modelo va aparte: la marca la decide Ader en la oficina.
const splitRef=label=>{const m=/ \((?:ref\. )?([^)]*Amanco[^)]*)\)/.exec(label);return m?{description:label.replace(m[0],'')+(/indicar PN/.test(m[1])?' (indicar PN)':''),ref:m[1].replace(/; indicar PN$/,'')}:{description:label}};
const systems=SYSTEMS.map(([key,name])=>{
 const rows=[...bySystem.get(key).values()].filter(r=>{
  if(r.kind==='pipe'&&r.quantity<MIN_PIPE_M){transitions.push(`${key} · ${r.label}: ${r.quantity.toFixed(2).replace('.',',')} m en ${r.elements} tramo(s)`);return false}
  return true;
 }).sort((a,b)=>kindOrder[a.kind]-kindOrder[b.kind]||b.diameter-a.diameter||a.label.localeCompare(b.label,'es',{numeric:true}));
 return {key,name,items:rows.map((r,n)=>({code:`${key}.${String(n+1).padStart(2,'0')}`,...splitRef(r.label),unit:r.unit,quantity:r.unit==='m'?Math.round(r.quantity*10)/10:r.quantity,elements:r.elements,kind:r.kind,...(r.optionalMaterial?{materialOptional:true}:{})}))};
}).filter(s=>s.items.length);

// Locales y artefactos: orienta la mano de obra sin agregar renglones.
const locales={};
for(const i of project.items.filter(i=>i.kind==='equipment')){const l=i.package_name||'Sin local';const k=equipmentLabel(i).split(':')[0].split(' (')[0];(locales[l]||(locales[l]={}))[k]=(locales[l][k]||0)+1}

const data={
 project:'Casa Ángel',location:'Pinamar Norte, provincia de Buenos Aires',rubro:'sanitaria',name:'Instalación sanitaria',
 revision:'R13',source:'Registro único R13 del modelo Casa-Angel-piloto-documentacion.rvt (22/10/2026): 692 caños, 676 accesorios, 32 artefactos y equipos.',
 date:DATE,
 basis:'Longitudes de eje del modelo, sin desperdicio ni recortes comerciales. Cada elemento físico se cuenta una sola vez aunque aparezca en varias láminas.',
 systems,locales,transitions,
 excluded:[
  'Canaletas, limahoyas y bajadas pluviales: se cotizan en Cubierta.',
  'Desagüe pluvial en terreno: no está modelado.',
  'Bachas de vanitorio: se proveen con Mesadas.',
  'Calefacción por piso radiante: Climatización. Gas: rubro Gas.',
  'Canaleteado, amurado y reparación de muros y pisos: Albañilería.',
  'Tanques de reserva, conexión a red de agua y cloaca o sistema propio, y producción de agua caliente: no están modelados; se definen aparte.',
 ],
 documents:[
  {name:'Planos de instalación sanitaria (16 láminas)',url:'/casa-angel/Documentacion-Sanitarias-original.pdf'},
 ],
};
data.count=systems.reduce((n,s)=>n+s.items.length,0);
mkdirSync(OUT,{recursive:true});
writeFileSync(`${OUT}/sanitaria-R13.json`,JSON.stringify(data,null,1)+'\n');

// El Excel lo arma la oficina con las marcas elegidas (lib/quote-xlsx.ts). Con un argumento, se escribe acá para revisarlo.
if(process.argv[2])writeFileSync(process.argv[2],quoteWorkbook(data));
console.log(`${data.count} ítems en ${systems.length} sistemas →`,systems.map(s=>`${s.key} ${s.items.length}`).join(', '));
if(transitions.length)console.log('Tramos de transición:',transitions.join(' | '));
