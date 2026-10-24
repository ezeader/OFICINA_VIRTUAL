// Rubros de documentación de Casa Ángel y contrato de datos que publica la sesión de Revit
// en public/casa-angel/rubros/<clave>/manifest.json. Mismo formato que Sanitarias, Aberturas y Estructura.

export type RubroInfo={key:string;name:string;subtitle:string;pending:string};
// Orden por capacidad de cómputo: primero lo que ya está modelado en 3D.
export const RUBROS:RubroInfo[]=[
 {key:'cubierta',name:'Cubierta',subtitle:'Tejas · madera · zinguería',pending:'Modelada en Revit (tejas y estructura de madera).'},
 {key:'pisos',name:'Pisos',subtitle:'Pisos y zócalos',pending:'Modelado en parte (33 elementos). Sigue en el plan.'},
 {key:'climatizacion',name:'Climatización',subtitle:'Piso radiante',pending:'Modelada en parte (piso radiante, 878 elementos). Sigue en el plan.'},
 {key:'albanileria',name:'Albañilería',subtitle:'Muros y tabiques',pending:'Muros y tabiques no estructurales modelados en parte (60). Sigue en el plan.'},
 {key:'cielorrasos',name:'Cielorrasos',subtitle:'Suspendidos y aplicados',pending:'Modelados en parte (14). Sigue en el plan.'},
 {key:'pileta',name:'Pileta',subtitle:'Vaso y equipamiento',pending:'Modelada en parte (7 elementos).'},
 {key:'exteriores',name:'Exteriores',subtitle:'Paisajismo y solados',pending:'Modelados en parte (20 elementos).'},
 {key:'equipamiento',name:'Equipamiento',subtitle:'Mobiliario fijo',pending:'Modelado en parte (106 elementos).'},
 {key:'revestimientos',name:'Revestimientos',subtitle:'Terminaciones de muros',pending:'No están modelados: hay que definirlos antes de documentar.'},
 {key:'parrilla',name:'Parrilla',subtitle:'Diseño y construcción',pending:'Apenas modelada (3 elementos): hay que diseñarla.'},
 {key:'electrica',name:'Eléctrica',subtitle:'Instalación',pending:'Primero hay que diseñar la instalación: casi no está modelada.'},
 {key:'gas',name:'Gas',subtitle:'Instalación',pending:'No está modelado todavía.'},
 {key:'domotica',name:'Domótica',subtitle:'Automatización',pending:'No está modelado todavía.'},
 {key:'solar',name:'Paneles solares',subtitle:'Captación y equipos',pending:'No está modelado todavía.'},
];
export const rubroByKey=(key:string)=>RUBROS.find(r=>r.key===key);

export type RubroManifest={
 title?:string;summary?:string;status?:string; // 'propuesta' = diseño a confirmar por el estudio
model?:string;readAt?:string;revision?:string;
 kinds?:Record<string,string>; // prefijo de código → nombre, p. ej. {"CU":"Faldón de tejas"}
 sheets?:import('../components/rubro-viewer').RubroSheet[];
 codes?:import('../components/rubro-viewer').RubroCode[];
 totals?:{label:string;value:number;unit:string;detail?:string}[];
 quantities?:{label:string;group?:string;count?:number;value:number;unit:string;detail?:string}[];
 quantityNote?:string;notModeled?:string[];decisions?:string[];questions?:string[];
 budget?:import('./rubro-budget').ManifestBudget; // partidas a cotizar; sin esto se usan los totales
};

// Grupos de láminas: generales primero (por sector), luego fichas por tipo de elemento.
export function groupRubroSheets<T extends {number:string;title:string;sector?:string|null;level?:string|null;kind?:string;element?:string}>(sheets:T[],kinds?:Record<string,string>){
 const groupOf=(s:T)=>s.kind==='element'||s.element?(kinds?.[(s.element||'').split('-')[0]]?`Fichas · ${kinds[(s.element||'').split('-')[0]]}`:'Fichas'):(s.sector||s.level||'Láminas generales');
 const groups=new Map<string,T[]>();
 for(const s of [...sheets].sort((a,b)=>a.number.localeCompare(b.number,'es',{numeric:true})))groups.set(groupOf(s),[...(groups.get(groupOf(s))||[]),s]);
 return [...groups].map(([title,rows])=>({title,sheets:rows})).sort((a,b)=>Number(a.title!=='General')-Number(b.title!=='General')||Number(a.title.startsWith('Fichas'))-Number(b.title.startsWith('Fichas'))||a.title.localeCompare(b.title,'es',{numeric:true}));
}
