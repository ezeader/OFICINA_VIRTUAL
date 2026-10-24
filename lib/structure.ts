// Estructura de Casa Ángel: cómputo de hormigón y revisión a partir del inventario de Revit.
// Solo valores del modelo; lo que no está modelado se informa como pendiente, nunca se estima.

export type Wall={id:string;code:string;type:string;level:string;length_m:number;height_m:number;thickness_m:number;area_m2:number;volume_m3:number;topConstraint?:string;baseOffset_m?:number;mark?:string|null};
export type Slab={id:string;type:string;level:string;role:string;area_m2:number;thickness_m?:number;concreteLayer_m?:number;concreteVolume_m3:number|null};
export type Group={key:string;count:number;area_m2:number;volume_m3:number;length_m:number};
export type StructureCase={id:string;title:string;elementIds:string[];codes:string[];observation:string;proposedCorrection:string;status?:string};
export type StructureSheet={number:string;title:string;level?:string|null;sector?:string|null;image?:string;preview?:string;thumbnail?:string;pdf?:string;sheetId?:string;views?:StructureView[];element?:string;kind?:string;rebar?:string};
export type StructureManifest={model:string;readAt:string;revision:string;status:string;levels:{name:string}[];concreteWalls:{type:string;count:number;elements:Wall[];totals:{length_m:number;area_m2:number;volume_m3:number}};otherStructuralWalls:Group[];slabsAndFoundations:Slab[];framing:{note?:string;byType:Group[]};roofs:Group[];notModeled:string[];warnings:{total:number;byText:{text:string;count:number}[]};reviewCases:StructureCase[];proposal:{sheets:{number:string;title:string}[]};openQuestions?:string[];sheets?:StructureSheet[];codes?:StructureCode[];decisions?:string[];codesWrittenToModel?:boolean;checks?:{loPb01VsPlatea?:{loPb01OutsidePlatea_m2:number};perimeters_m?:Record<string,number>};documentationRevision?:string};

const byLevel=(a:string,b:string)=>a.localeCompare(b,'es',{numeric:true});
const sum=<T,>(rows:T[],f:(r:T)=>number)=>rows.reduce((n,r)=>n+(f(r)||0),0);

// Hormigón por partida y por nivel. Las losas solo cuentan su capa de hormigón; los paquetes de piso sin capa no suman.
export function concreteTotals(m:StructureManifest){
 const walls=m.concreteWalls.elements,levels=[...new Set(walls.map(w=>w.level))].sort(byLevel);
 const wallsByLevel=levels.map(level=>{const rows=walls.filter(w=>w.level===level);return {level,count:rows.length,length:sum(rows,w=>w.length_m),area:sum(rows,w=>w.area_m2),volume:sum(rows,w=>w.volume_m3)}});
 const slabs=m.slabsAndFoundations.filter(s=>s.concreteVolume_m3!=null&&s.concreteVolume_m3>0);
 const platea=slabs.filter(s=>/platea/i.test(s.role)),losas=slabs.filter(s=>!/platea/i.test(s.role));
 const withoutConcrete=m.slabsAndFoundations.filter(s=>!s.concreteVolume_m3);
 const losasByLevel=[...new Set(losas.map(s=>s.level))].sort(byLevel).map(level=>{const rows=losas.filter(s=>s.level===level);return {level,count:rows.length,area:sum(rows,s=>s.area_m2),volume:sum(rows,s=>s.concreteVolume_m3||0)}});
 const parts={walls:sum(walls,w=>w.volume_m3),losas:sum(losas,s=>s.concreteVolume_m3||0),platea:sum(platea,s=>s.concreteVolume_m3||0)};
 return {wallsByLevel,losasByLevel,platea:{area:sum(platea,s=>s.area_m2),volume:parts.platea},parts,total:parts.walls+parts.losas+parts.platea,withoutConcrete:{count:withoutConcrete.length,area:sum(withoutConcrete,s=>s.area_m2)}};
}

// Cuantías de acero (kg por m³ de hormigón) mientras no haya cálculo ni armaduras en el modelo: valores usuales
// para vivienda, a reemplazar por los del calculista.
export const STEEL_KG_M3={platea:80,muros:60,losas:90,vigas:110,base:50};
export type StructureLine={id:string;label:string;quantity:number;unit:string;detail?:string;informative?:boolean};
const list=(codes:string[])=>codes.length>4?`${codes[0]} a ${codes.at(-1)}`:codes.join(', ');
// Toda la Planta Baja apoya sobre la platea (decisión del usuario 2026-10-24): la huella de LO-PB-01 que queda fuera
// de la platea (checks de Revit) se suma a la platea con su espesor; LO-PB-01 queda como referencia.
// Partidas para el presupuesto, sin solapes con otros rubros: cada elemento suma en una sola partida de hormigón,
// el acero sale de la cuantía de su partida y el encofrado de las caras a moldear.
// Muros de fachada y bajo escalera van en Albañilería, los del vaso en Pileta, la base de acceso en Exteriores
// y la madera del techo en Cubierta.
export function structureBudget(m:StructureManifest):StructureLine[]{
 const code=new Map((m.codes||[]).map(c=>[c.id,c.code])),slabs=m.slabsAndFoundations.map(s=>({...s,code:code.get(s.id)||s.id}));
 const concrete=slabs.filter(s=>(s.concreteVolume_m3||0)>0),vol=(rows:{concreteVolume_m3:number|null}[])=>sum(rows,s=>s.concreteVolume_m3||0);
 const platea=concrete.filter(s=>/platea/i.test(s.role)),onGround=concrete.filter(s=>!/platea/i.test(s.role)&&/^LO-(PB|AC)/.test(s.code));
 const losas=concrete.filter(s=>!platea.includes(s)&&!onGround.includes(s)),pending=slabs.filter(s=>!s.concreteVolume_m3&&!/^LO-PB/.test(s.code));
 const walls=m.concreteWalls.elements,beams=(m.codes||[]).filter(c=>c.kind==='VE');
 const tie=beams.filter(b=>b.level?.startsWith('00')),meet=beams.filter(b=>!tie.includes(b));
 const grow=m.checks?.loPb01VsPlatea?.loPb01OutsidePlatea_m2||0,plateaE=platea[0]?.concreteLayer_m||0,perim=m.checks?.perimeters_m||{};
 const concreteLines=[
  {id:'platea',label:'Hormigón de platea',quantity:vol(platea)+grow*plateaE,steel:STEEL_KG_M3.platea,detail:`${list(platea.map(s=>s.code))} · ${n(sum(platea,s=>s.area_m2)+grow)} m²${grow?` (incluye ${n(grow)} m² de LO-PB-01, a extender en el modelo)`:''} · e ${n(plateaE*100)} cm`},
  {id:'muros',label:'Hormigón de muros (20 cm)',quantity:sum(walls,w=>w.volume_m3),steel:STEEL_KG_M3.muros,detail:`${walls.length} muros MH · ${n(sum(walls,w=>w.area_m2))} m²`},
  ...onGround.map(s=>({id:s.code==='LO-PB-01'?'losa-pb':'base-acceso',label:s.code==='LO-PB-01'?'Losa PB (pasa a ser platea, no se cotiza aparte)':'Hormigón de base de acceso (se cotiza en Exteriores)',informative:true,quantity:s.concreteVolume_m3||0,steel:s.code==='LO-PB-01'?STEEL_KG_M3.losas:STEEL_KG_M3.base,detail:`${s.code} · ${n(s.area_m2)} m² · e ${n((s.concreteLayer_m||0)*100)} cm`} as {id:string;label:string;quantity:number;steel:number;detail:string;informative?:boolean})),
  {id:'losas',label:'Hormigón de losas elevadas',quantity:vol(losas),steel:STEEL_KG_M3.losas,detail:`${losas.length} losas PA/PE · ${n(sum(losas,s=>s.area_m2))} m²`},
  {id:'vigas',label:'Hormigón de vigas de encadenado',quantity:sum(tie,b=>b.volume_m3||0),steel:STEEL_KG_M3.vigas,detail:`${list(tie.map(b=>b.code))} · ${n(sum(tie,b=>b.length_m||0))} m`},
  {id:'vigas-encuentro',label:'Hormigón de vigas de encuentro de techos',quantity:sum(meet,b=>b.volume_m3||0),steel:STEEL_KG_M3.muros,detail:`${list(meet.map(b=>b.code))} · ${n(sum(meet,b=>b.area_m2||0))} m²`},
 ].filter(l=>l.quantity>0);
 const priced=concreteLines.filter(l=>!l.informative),steel=sum(priced,l=>l.quantity*l.steel);
 const formWalls=2*(sum(walls,w=>w.area_m2)+sum(beams,b=>b.area_m2||0)),formSlabs=sum(losas,s=>s.area_m2);
 // Bordes: perímetro de Revit × espesor de hormigón (platea y losas elevadas).
 const edges=sum(platea,s=>(perim[s.code]||0)*(s.concreteLayer_m||0))+sum(losas,s=>(perim[s.code]||0)*(s.concreteLayer_m||0));
 return [
  ...concreteLines.map(({steel:_,...l})=>({...l,unit:'m³'})),
  {id:'acero',label:'Acero en barras (estimado por cuantía)',quantity:steel,unit:'kg',detail:priced.map(l=>`${l.id} ${l.steel}`).join(' · ')+' kg/m³'},
  {id:'encofrado-muros',label:'Encofrado de muros y vigas (2 caras)',quantity:formWalls,unit:'m²'},
  {id:'encofrado-losas',label:'Encofrado de fondo de losas',quantity:formSlabs,unit:'m²',detail:`${losas.length} losas PA/PE; la platea no lleva fondo`},
  {id:'encofrado-bordes',label:'Encofrado de bordes de platea y losas',quantity:edges,unit:'m²',detail:'perímetro × espesor de hormigón'},
  {id:'losas-a-confirmar',label:'Losas a confirmar (sin capa de hormigón)',quantity:sum(pending,s=>s.area_m2),unit:'m²',detail:list(pending.map(s=>s.code)),informative:true},
 ].filter(l=>l.quantity>0);
}
const n=(v:number)=>v.toLocaleString('es-AR',{maximumFractionDigits:2});

// Avisos de Revit en castellano llano.
const WARNINGS:[RegExp,string][]=[
 [/attached to, but miss/i,'Muros enlazados a un techo o losa que no alcanzan'],
 [/room separation line overlap/i,'Un muro se superpone con una línea de separación de locales'],
 [/walls overlap/i,'Muros superpuestos'],
 [/floors overlap/i,'Losas o pisos superpuestos'],
 [/joined but do not intersect/i,'Elementos unidos que no se tocan'],
];
export const plainWarning=(text:string)=>WARNINGS.find(([re])=>re.test(text))?.[1]||text;

// Casos de revisión agrupados por tipo de problema, con el más importante primero.
export function groupCases(cases:StructureCase[]){
 const groups=new Map<string,StructureCase[]>();
 for(const c of cases){const key=c.title.startsWith('Solape')?plainWarning(c.observation):c.title;groups.set(key,[...(groups.get(key)||[]),c])}
 return [...groups].map(([title,rows])=>({title,rows})).sort((a,b)=>a.rows.length-b.rows.length);
}

// Láminas: plantas y fundación primero, después alzados por nivel y al final los casos de revisión.
export type StructureView={id:string;name:string;scale:number;kind?:string;sector?:string;roomLabel?:string;caseId?:string|null;image:string;region?:number[];tags?:string[];dimensions?:{label:string;values_m:number[];associative?:boolean}[];elements?:{code:string;elementId?:string;box:number[]}[]};
export type StructureCode={id:string;code:string;kind:string;level?:string;label:string;status?:string;length_m?:number;height_m?:number;thickness_m?:number;area_m2?:number;volume_m3?:number};
const ELEMENT_GROUP:Record<string,string>={MH:'Fichas de muros',LO:'Fichas de losas',VE:'Fichas de vigas y encadenados',PL:'Ficha de platea',CO:'Fichas de columnas'};
export function sheetGroup(s:{number:string;level?:string|null;element?:string;kind?:string}){
 if(s.element||s.kind==='element')return ELEMENT_GROUP[(s.element||'').split('-')[0]]||'Fichas de elementos';
 if(s.number.startsWith('EST-SEC'))return `Alzados de muros · ${s.level||'sin nivel'}`;
 if(s.number.startsWith('EST-REV'))return 'Casos de revisión';
 return 'Índice, plantas y fundación';
}
export function groupStructureSheets<T extends {number:string;level?:string|null;element?:string;kind?:string}>(sheets:T[]){
 const order=(g:string)=>g.startsWith('Índice')?0:g.startsWith('Alzados')?1:g.startsWith('Ficha')?2:3;
 const groups=new Map<string,T[]>();
 for(const s of [...sheets].sort((a,b)=>a.number.localeCompare(b.number,'es',{numeric:true})))groups.set(sheetGroup(s),[...(groups.get(sheetGroup(s))||[]),s]);
 return [...groups].map(([title,rows])=>({title,sheets:rows})).sort((a,b)=>order(a.title)-order(b.title)||a.title.localeCompare(b.title,'es',{numeric:true}));
}
