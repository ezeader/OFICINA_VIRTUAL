// Rubros de documentación de Casa Ángel y contrato de datos que publica la sesión de Revit
// en public/casa-angel/rubros/<clave>/manifest.json. Mismo formato que Sanitarias, Aberturas y Estructura.

export type RubroInfo={key:string;name:string;subtitle:string;pending:string};
// Orden por capacidad de cómputo: primero lo que ya está modelado en 3D.
export const RUBROS:RubroInfo[]=[
 {key:'cubierta',name:'Cubierta',subtitle:'Tejas · madera · zinguería',pending:'Modelada en Revit (tejas y estructura de madera). Las láminas se están preparando.'},
 {key:'albanileria',name:'Albañilería',subtitle:'Tabiques y muros',pending:'Muros no estructurales modelados. Se documenta después de Cubierta.'},
 {key:'pisos',name:'Pisos',subtitle:'Contrapisos y terminaciones',pending:'Capas de piso modeladas en las losas. Se documenta después de Albañilería.'},
 {key:'revestimientos',name:'Revestimientos',subtitle:'Terminaciones de muros',pending:'A confirmar qué terminaciones están modeladas.'},
 {key:'climatizacion',name:'Climatización',subtitle:'Equipos y conductos',pending:'Hay un relevamiento de datos; faltan láminas.'},
 {key:'pileta',name:'Pileta',subtitle:'Vaso y equipamiento',pending:'Modelada en parte (muros del vaso).'},
 {key:'parrilla',name:'Parrilla',subtitle:'Diseño y construcción',pending:'No está modelada: hay que diseñarla antes de documentarla.'},
 {key:'solar',name:'Paneles solares',subtitle:'Captación y equipos',pending:'No está modelado todavía.'},
 {key:'gas',name:'Gas',subtitle:'Instalación',pending:'No está modelado todavía.'},
 {key:'domotica',name:'Domótica',subtitle:'Automatización',pending:'No está modelado todavía.'},
];
export const rubroByKey=(key:string)=>RUBROS.find(r=>r.key===key);

export type RubroManifest={
 title?:string;summary?:string;model?:string;readAt?:string;revision?:string;
 kinds?:Record<string,string>; // prefijo de código → nombre, p. ej. {"CU":"Faldón de tejas"}
 sheets?:import('../components/rubro-viewer').RubroSheet[];
 codes?:import('../components/rubro-viewer').RubroCode[];
 totals?:{label:string;value:number;unit:string;detail?:string}[];
 quantities?:{label:string;group?:string;count?:number;value:number;unit:string;detail?:string}[];
 quantityNote?:string;notModeled?:string[];decisions?:string[];questions?:string[];
};

// Grupos de láminas: generales primero (por sector), luego fichas por tipo de elemento.
export function groupRubroSheets<T extends {number:string;title:string;sector?:string|null;level?:string|null;kind?:string;element?:string}>(sheets:T[],kinds?:Record<string,string>){
 const groupOf=(s:T)=>s.kind==='element'||s.element?`Fichas · ${(kinds?.[(s.element||'').split('-')[0]])||'elementos'}`:(s.sector||s.level||'Láminas generales');
 const groups=new Map<string,T[]>();
 for(const s of [...sheets].sort((a,b)=>a.number.localeCompare(b.number,'es',{numeric:true})))groups.set(groupOf(s),[...(groups.get(groupOf(s))||[]),s]);
 return [...groups].map(([title,rows])=>({title,sheets:rows})).sort((a,b)=>Number(a.title.startsWith('Fichas'))-Number(b.title.startsWith('Fichas'))||a.title.localeCompare(b.title,'es',{numeric:true}));
}
