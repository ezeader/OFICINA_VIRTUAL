// Cómputo para cotizar la instalación sanitaria de Casa Ángel.
// Fuente: registro único R13 (public/casa-angel/r13/project.json.gz): cada elemento físico una sola vez.
// Salida: public/casa-angel/cotizacion/sanitaria-R13.json (lo lee la oficina) y el Excel para proveedores.
// Uso: node scripts/cotizacion-sanitaria.mjs
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {workbook,ref,S} from './xlsx-lite.mjs';

const project=JSON.parse(gunzipSync(readFileSync('public/casa-angel/r13/project.json.gz')));
const OUT='public/casa-angel/cotizacion';
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
const systems=SYSTEMS.map(([key,name])=>{
 const rows=[...bySystem.get(key).values()].filter(r=>{
  if(r.kind==='pipe'&&r.quantity<MIN_PIPE_M){transitions.push(`${key} · ${r.label}: ${r.quantity.toFixed(2).replace('.',',')} m en ${r.elements} tramo(s)`);return false}
  return true;
 }).sort((a,b)=>kindOrder[a.kind]-kindOrder[b.kind]||b.diameter-a.diameter||a.label.localeCompare(b.label,'es',{numeric:true}));
 return {key,name,items:rows.map((r,n)=>({code:`${key}.${String(n+1).padStart(2,'0')}`,description:r.label,unit:r.unit,quantity:r.unit==='m'?Math.round(r.quantity*10)/10:r.quantity,elements:r.elements,kind:r.kind,...(r.optionalMaterial?{materialOptional:true}:{})}))};
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
  {name:'Plantas generales R12',url:'/casa-angel/r12/Casa-Angel-plantas-generales-R12.pdf'},
 ],
};
data.count=systems.reduce((n,s)=>n+s.items.length,0);
mkdirSync(OUT,{recursive:true});
writeFileSync(`${OUT}/sanitaria-R13.json`,JSON.stringify(data,null,1)+'\n');

// ---------- Excel para proveedores ----------
const COLS=['Código','Descripción','Unidad','Cantidad','Material\n$ unitario','Material\nsubtotal','Mano de obra\n$ unitario','Mano de obra\nsubtotal','Total','Marca / modelo ofrecido','Observaciones'];
const rows=[],merges=[],heights={};
const put=(r,cells)=>{rows[r]=cells};
put(0,[{v:'ESTUDIO ADER · Pedido de cotización · Instalación sanitaria',s:S.title}]);merges.push('A1:K1');heights[0]=22;
put(1,[{v:`Obra: Casa Ángel · ${data.location}   |   Cómputo ${data.revision} del modelo   |   Fecha: ${DATE}`,s:S.bold}]);merges.push('A2:K2');
put(2,[{v:'Completar solo las celdas amarillas. Precio unitario de MATERIAL y de MANO DE OBRA por separado, en la unidad indicada. Si no cotiza un ítem, dejarlo vacío. Si la mano de obra de accesorios está incluida en la de cañería, poner 0 y aclararlo. Marcas: la referencia es Amanco Wavin; alternativas equivalentes se indican en "Marca / modelo ofrecido".',s:S.subtitle}]);merges.push('A3:K3');heights[2]=38;
put(3,[{v:data.basis+' Las láminas y el detalle de alcance van en la hoja "Alcance".',s:S.subtitle}]);merges.push('A4:K4');heights[3]=26;
const HEAD=5;put(HEAD,COLS.map(v=>({v,s:S.head})));heights[HEAD]=30;
let r=HEAD+1;const subtotals=[];
for(const sys of systems){
 put(r,[{v:`${sys.name.toUpperCase()} · ${sys.items.length} ítems`,s:S.section},...Array(10).fill({v:'',s:S.section})]);merges.push(`A${r+1}:K${r+1}`);r++;
 const first=r;
 for(const it of sys.items){
  const R=r+1;
  put(r,[{v:it.code,s:S.code},{v:it.description,s:S.text},{v:it.unit,s:S.text},{v:it.quantity,s:it.unit==='m'?S.qty:S.int},
   {v:'',s:S.input},{f:`IF(E${R}="","",D${R}*E${R})`,s:S.money},{v:'',s:S.input},{f:`IF(G${R}="","",D${R}*G${R})`,s:S.money},{f:`IF(AND(E${R}="",G${R}=""),"",N(F${R})+N(H${R}))`,s:S.money},
   {v:'',s:S.inputText},{v:it.materialOptional?'Material opcional: cotizar solo si lo provee (modelo a definir por Ader).':'',s:it.materialOptional?S.inputText:S.inputText}]);
  r++;
 }
 const a=first+1,b=r;
 put(r,[{v:'',s:S.totalLabel},{v:`Subtotal ${sys.name}`,s:S.totalLabel},{v:'',s:S.totalLabel},{v:'',s:S.totalLabel},{v:'',s:S.totalLabel},{f:`SUM(F${a}:F${b})`,s:S.totalMoney},{v:'',s:S.totalLabel},{f:`SUM(H${a}:H${b})`,s:S.totalMoney},{f:`SUM(I${a}:I${b})`,s:S.totalMoney},{v:'',s:S.totalLabel},{v:'',s:S.totalLabel}]);
 subtotals.push(r+1);r+=2;
}
const sum=c=>subtotals.map(n=>`${c}${n}`).join('+');
put(r,[{v:'',s:S.totalLabel},{v:'TOTAL DE LA OFERTA',s:S.totalLabel},{v:'',s:S.totalLabel},{v:'',s:S.totalLabel},{v:'',s:S.totalLabel},{f:sum('F'),s:S.totalMoney},{v:'',s:S.totalLabel},{f:sum('H'),s:S.totalMoney},{f:sum('I'),s:S.totalMoney},{v:'',s:S.totalLabel},{v:'',s:S.totalLabel}]);r+=2;
put(r,[{v:'CONDICIONES DE LA OFERTA',s:S.bold}]);r++;
for(const q of ['Empresa / responsable','Teléfono y email','Moneda (ARS o USD)','¿Los precios incluyen IVA?','¿Cotiza materiales, mano de obra o ambos?','Validez de la oferta (días)','Plazo de entrega de materiales en obra','Plazo de ejecución de la mano de obra','Zona de trabajo (localidades que atiende)','Flete a Pinamar Norte (incluido o importe)','Forma de pago']){
 put(r,[{v:'',s:S.none},{v:q,s:S.text},{v:'',s:S.inputText},{v:'',s:S.inputText},{v:'',s:S.inputText}]);merges.push(`C${r+1}:E${r+1}`);r++;
}
const sheet1={name:'Cómputo',rows,merges,freeze:HEAD+1,cols:[9,58,7,10,13,14,13,14,15,26,30],heights};

const rows2=[],merges2=[],h2={};let k=0;
const line=(cells,merge)=>{rows2[k]=cells;if(merge)merges2.push(`A${k+1}:F${k+1}`);k++};
line([{v:'Alcance del pedido · Instalación sanitaria · Casa Ángel',s:S.title}],true);h2[0]=22;
line([{v:`${data.location} · Estudio Ader · ${DATE}`,s:S.bold}],true);k++;
line([{v:'DOCUMENTACIÓN ADJUNTA',s:S.bold}],true);
for(const d of data.documents)line([{v:'· '+d.name+' (PDF)',s:S.wrap}],true);
line([{v:'· Este Excel: cómputo por sistema. Cada ítem aparece una sola vez.',s:S.wrap}],true);k++;
line([{v:'ARTEFACTOS POR LOCAL (para estimar la mano de obra; ya están incluidos en la hoja Cómputo)',s:S.bold}],true);
const kinds=[...new Set(Object.values(locales).flatMap(o=>Object.keys(o)))];
line([{v:'Local',s:S.head},...kinds.map(v=>({v,s:S.head}))]);h2[k-1]=42;
for(const [l,o] of Object.entries(locales).sort())line([{v:l,s:S.text},...kinds.map(x=>({v:o[x]||'',s:S.int}))]);
k++;
line([{v:'NO INCLUIDO EN ESTE PEDIDO',s:S.bold}],true);
for(const e of data.excluded)line([{v:'· '+e,s:S.wrap}],true);
if(transitions.length){k++;line([{v:'Tramos de transición sin compra propia (quedan dentro del accesorio):',s:S.bold}],true);for(const t of transitions)line([{v:'· '+t,s:S.wrap}],true)}
const sheet2={name:'Alcance',rows:rows2,merges:merges2,cols:[34,...kinds.map(()=>16)],heights:h2};

writeFileSync(`${OUT}/Casa-Angel-Sanitaria-cotizacion-R13.xlsx`,workbook([sheet1,sheet2],{title:'Casa Ángel · Cotización sanitaria R13'}));
console.log(`${data.count} ítems en ${systems.length} sistemas →`,systems.map(s=>`${s.key} ${s.items.length}`).join(', '));
if(transitions.length)console.log('Tramos de transición:',transitions.join(' | '));
