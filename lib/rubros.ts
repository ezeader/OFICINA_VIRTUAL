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
 {key:'equipamiento',name:'Equipamiento',subtitle:'Carpintería · mamparas · equipos',pending:'Modelado en parte (106 elementos).'},
 {key:'mesadas',name:'Mesadas',subtitle:'Mármol / piedra · cocina, baños y lavadero',pending:'Medidas tomadas de las fichas de Equipamiento (ME, VA, LV).'},
 {key:'revestimientos',name:'Revestimientos',subtitle:'Terminaciones de muros',pending:'No están modelados: hay que definirlos antes de documentar.'},
 {key:'parrilla',name:'Parrilla',subtitle:'Diseño y construcción',pending:'Apenas modelada (3 elementos): hay que diseñarla.'},
 {key:'electrica',name:'Eléctrica',subtitle:'Instalación',pending:'Primero hay que diseñar la instalación: casi no está modelada.'},
 {key:'gas',name:'Gas',subtitle:'Instalación',pending:'No está modelado todavía.'},
 {key:'domotica',name:'Domótica',subtitle:'Automatización',pending:'No está modelado todavía.'},
 {key:'solar',name:'Paneles solares',subtitle:'Captación y equipos',pending:'No está modelado todavía.'},
];
export const rubroByKey=(key:string)=>RUBROS.find(r=>r.key===key);

// Oficinas Urbetrack: rubros de la carpeta técnica entregada (una lámina por página del PDF),
// publicados en public/urbetrack/rubros/<clave>/manifest.json con el mismo contrato.
export const URBE_RUBROS:RubroInfo[]=[
 {key:'intro',name:'Intro',subtitle:'Memoria y diagramas',pending:'Sin láminas publicadas.'},
 {key:'demolicion',name:'Demolición',subtitle:'Pisos 12 y 13',pending:'Sin láminas publicadas.'},
 {key:'arquitectura',name:'Arquitectura',subtitle:'Plantas · axonometría · cortes',pending:'Sin láminas publicadas.'},
 {key:'sanitarias',name:'Sanitarias',subtitle:'Planta integrada y detalles',pending:'Sin láminas publicadas.'},
 {key:'electricas',name:'Eléctricas',subtitle:'Iluminación · tomas · datos',pending:'Sin láminas publicadas.'},
 {key:'tableros',name:'Tableros',subtitle:'TS-IT · TS-PUESTOS · TS-AA',pending:'Sin láminas publicadas.'},
 {key:'aire',name:'Aire acondicionado',subtitle:'Equipos y alimentación',pending:'Sin láminas publicadas.'},
 {key:'tabiqueria',name:'Tabiquería vidriada',subtitle:'Plantas · planilla · pivotes',pending:'Sin láminas publicadas.'},
 {key:'materialidad',name:'Materialidad',subtitle:'Terminaciones y equipamiento',pending:'Sin láminas publicadas.'},
];

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

// Plano principal primero: cada nivel ("00. Planta Baja", "01. Planta Alta"…) abre con su planta completa y debajo
// las demás láminas de ese nivel; lo que no es de un nivel (índice, cortes, detalles) va al final.
const LEVEL=/^\d+\.\s/;
export const levelName=(level:string)=>level.replace(LEVEL,'');
type LevelSheet={number:string;title:string;sector?:string|null;level?:string|null;kind?:string;element?:string};
export function groupRubroLevels<T extends LevelSheet>(sheets:T[],kinds?:Record<string,string>,subgroup?:(s:T)=>string){
 const byNumber=(a:T,b:T)=>a.number.localeCompare(b.number,'es',{numeric:true});
 const sorted=[...sheets].sort(byNumber),isElement=(s:T)=>s.kind==='element'||!!s.element;
 const names=[...new Set(sorted.map(s=>s.level||'').filter(l=>LEVEL.test(l)))].sort((a,b)=>a.localeCompare(b,'es',{numeric:true}));
 const bucket=(rows:T[],title:(s:T)=>string)=>{const m=new Map<string,T[]>();for(const s of rows)m.set(title(s),[...(m.get(title(s))||[]),s]);return [...m].map(([title,sheets])=>({title,sheets}))};
 const kindGroup=(s:T)=>{const k=kinds?.[(s.element||'').split('-')[0]];return k?`Fichas · ${k}`:'Fichas'};
 const levels=names.map(level=>{
  const own=sorted.filter(s=>s.level===level),name=levelName(level).toLowerCase();
  // La planta del nivel es la lámina general (no ficha, no versión previa) cuyo título nombra el nivel.
  const general=own.filter(s=>!isElement(s)&&!/previo/i.test(s.sector||''));
  const plan=general.find(s=>s.title.toLowerCase().includes(name))||general[0];
  const title=subgroup||((s:T)=>isElement(s)?kindGroup(s):(s.sector||'').replace(level,'').replace(/^[\s·]+|[\s·]+$/g,'')||'Otras láminas del nivel');
  const groups=bucket(own.filter(s=>s!==plan),title).sort((a,b)=>Number(/previo/i.test(a.title))-Number(/previo/i.test(b.title))||Number(a.title.startsWith('Fichas'))-Number(b.title.startsWith('Fichas'))||a.title.localeCompare(b.title,'es',{numeric:true}));
  return {level,plan,groups};
 });
 const rest=sorted.filter(s=>!names.includes(s.level||'')),others=(subgroup?bucket(rest,subgroup):groupRubroSheets(rest,kinds)).sort((a,b)=>Number(/índice|general/i.test(a.title))-Number(/índice|general/i.test(b.title)));
 return {levels,others};
}
export type RubroLevels<T>={levels:{level:string;plan?:T;groups:{title:string;sheets:T[]}[]}[];others:{title:string;sheets:T[]}[]};
