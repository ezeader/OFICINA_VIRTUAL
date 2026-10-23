// Estructura de Casa Ángel: cómputo de hormigón y revisión a partir del inventario de Revit.
// Solo valores del modelo; lo que no está modelado se informa como pendiente, nunca se estima.

export type Wall={id:string;code:string;type:string;level:string;length_m:number;height_m:number;thickness_m:number;area_m2:number;volume_m3:number;topConstraint?:string;baseOffset_m?:number;mark?:string|null};
export type Slab={id:string;type:string;level:string;role:string;area_m2:number;thickness_m?:number;concreteLayer_m?:number;concreteVolume_m3:number|null};
export type Group={key:string;count:number;area_m2:number;volume_m3:number;length_m:number};
export type StructureCase={id:string;title:string;elementIds:string[];codes:string[];observation:string;proposedCorrection:string;status?:string};
export type StructureSheet={number:string;title:string;level?:string|null;sector?:string|null;image?:string;preview?:string;thumbnail?:string;pdf?:string;sheetId?:string;views?:StructureView[];element?:string;kind?:string};
export type StructureManifest={model:string;readAt:string;revision:string;status:string;levels:{name:string}[];concreteWalls:{type:string;count:number;elements:Wall[];totals:{length_m:number;area_m2:number;volume_m3:number}};otherStructuralWalls:Group[];slabsAndFoundations:Slab[];framing:{note?:string;byType:Group[]};roofs:Group[];notModeled:string[];warnings:{total:number;byText:{text:string;count:number}[]};reviewCases:StructureCase[];proposal:{sheets:{number:string;title:string}[]};openQuestions?:string[];sheets?:StructureSheet[];codes?:StructureCode[];decisions?:string[];codesWrittenToModel?:boolean;documentationRevision?:string};

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
