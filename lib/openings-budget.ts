// Relevamiento y cómputo de aberturas para pedir precio a proveedores.
// Solo usa valores de Revit; lo que no está se informa como faltante.

type Param={name:string;value:string};
export type BudgetItem={id:string;code:string;category:string;type:string;family?:string;width?:string|null;height?:string|null;panelCount?:number;materials?:string[];parameters:Param[];panels?:{width_m:number;height_m:number;type?:string}[];survey?:Survey};
// Ficha de relevamiento que arma la sesión de Revit (R9): tiene prioridad sobre la lectura de parámetros.
export type Survey={openingType?:string|null;notes?:string[];description?:string|null;glazing?:{material?:string|null;spec?:string|null;thickness_m?:string|null;area_m2?:number|null;panes?:number}|null;frame?:{material?:string|null;width_m?:string|null;depth_m?:string|null;subframe?:string|null;leaf?:string|null;handle?:string|null;profiles?:{type:string;material?:string;count:number;length_m:number}[]}|null;thermal?:{U?:string|null}|null};
const p=(i:BudgetItem,name:string)=>{const v=i.parameters.find(x=>x.name===name)?.value?.trim();return v&&v!=='<None>'&&v!=='None'?v:undefined};
const num=(v?:string|null)=>{if(!v)return null;const n=parseFloat(v.replace(',','.'));return Number.isFinite(n)?n:null};
const mm2ToM2=(v?:string)=>{const n=num(v);return n==null?undefined:`${(n/1e6).toLocaleString('es-AR',{maximumFractionDigits:2})} m²`};
const yes=(v?:string)=>v==='Yes'?'sí':v==='No'?'no':v;

const clean=(v?:string|null)=>v&&v!=='<None>'?v:undefined;
const m2=(n:number)=>n.toLocaleString('es-AR',{maximumFractionDigits:2})+' m²';
function fromSurvey(s:Survey){
 const g=s.glazing,f=s.frame;
 return [
  {label:'Apertura',value:clean(s.openingType)},
  {label:'Vidrio',value:g&&(g.area_m2||g.material)?[clean(g.material),clean(g.spec),g.thickness_m&&'espesor '+g.thickness_m,g.panes?`${g.panes} paños`:undefined,g.area_m2?'≈ '+m2(g.area_m2):undefined].filter(Boolean).join(' · '):undefined},
  {label:'Marco / perfiles',value:f?.profiles?.length?f.profiles.map(x=>`${x.type} ${x.material||''} · ${x.count} u. · ${x.length_m.toFixed(2)} m`).join(' / '):[clean(f?.material),f?.width_m&&'ancho '+f.width_m,f?.depth_m&&'prof. '+f.depth_m].filter(Boolean).join(' · ')||undefined},
  {label:'Hoja',value:clean(f?.leaf)},
  {label:'Premarco',value:clean(f?.subframe)},
  {label:'Herraje',value:clean(f?.handle)},
  {label:'Aislación térmica',value:s.thermal?.U?'U = '+s.thermal.U:undefined},
 ].filter(x=>x.value||['Apertura','Vidrio','Marco / perfiles'].includes(x.label));
}

// Datos de relevamiento agrupados como los pide un proveedor de aberturas.
export function surveySpecs(i:BudgetItem):{label:string;value?:string}[]{
 if(i.survey)return fromSurvey(i.survey);
 if(i.category==='Curtain Walls'){
  const mullion=[p(i,'Interior Type'),p(i,'Border 1 Type')].filter(Boolean);
  return [
   {label:'Tipo de cerramiento',value:'Muro cortina · '+i.type},
   {label:'Paneles',value:i.panelCount==null?undefined:`${i.panelCount} · ${p(i,'Curtain Panel')?.replace('System Panel : Glazed','vidriado')||'tipo sin dato'}`},
   {label:'Montantes',value:[...new Set(mullion)].join(' · ')||undefined},
   {label:'Separación de grilla',value:p(i,'Spacing')&&p(i,'Layout')?`${p(i,'Spacing')} (${p(i,'Layout')})`:undefined},
   {label:'Medidas del vidrio por panel',value:i.panels?.length?[...new Set(i.panels.map(x=>`${x.width_m.toFixed(2)} × ${x.height_m.toFixed(2)} m`))].join(' · '):undefined},
  ];
 }
 if(i.category==='Doors')return [
  {label:'Tipo de puerta',value:p(i,'Family')||i.family},
  {label:'Hoja',value:[p(i,'Material hoja'),p(i,'Thickness')&&'espesor '+p(i,'Thickness')].filter(Boolean).join(' · ')||undefined},
  {label:'Marco',value:[p(i,'Material marco'),p(i,'Anchura de marco')&&'ancho '+p(i,'Anchura de marco')].filter(Boolean).join(' · ')||undefined},
  {label:'Premarco',value:[p(i,'Material premarco'),p(i,'Premarco_Espesor')].filter(Boolean).join(' · ')||undefined},
  {label:'Herraje',value:[p(i,'Material tirador'),p(i,'TIRADOR OCULTO')==='Yes'?'tirador oculto':undefined].filter(Boolean).join(' · ')||undefined},
  {label:'Vano',value:p(i,'Rough Width')&&p(i,'Rough Height')?`${p(i,'Rough Width')} × ${p(i,'Rough Height')}`:undefined},
 ];
 const glassArea=[p(i,'𝐴𝑔 V1'),p(i,'𝐴𝑔 V2')].map(mm2ToM2).filter(Boolean);
 return [
  {label:'Sistema / modelo',value:[p(i,'Manufacturer'),p(i,'Model')].filter(Boolean).join(' ')||undefined},
  {label:'Apertura',value:p(i,'Operation')||p(i,'Description')||(i.family==='M_Fixed'?'Paño fijo':undefined)},
  {label:'Marco',value:[p(i,'Marco'),p(i,'AnchoMarco')&&'ancho '+p(i,'AnchoMarco'),p(i,'GrosorMarco')&&'espesor '+p(i,'GrosorMarco')].filter(Boolean).join(' · ')||undefined},
  {label:'Vidrio',value:[p(i,'Acristalamiento'),p(i,'GrosorAcristalamiento')&&'espesor '+p(i,'GrosorAcristalamiento')].filter(Boolean).join(' · ')||undefined},
  {label:'Superficie de vidrio',value:glassArea.length?glassArea.join(' + '):p(i,'FraccionAreaAcristalamiento')?`${p(i,'FraccionAreaAcristalamiento')} de la ventana`:undefined},
  {label:'Aislación térmica',value:p(i,'TransmitanciaTermica')?'U = '+p(i,'TransmitanciaTermica'):undefined},
  {label:'Oscilobatiente / manija',value:p(i,'Oscilobatiente')||p(i,'Manija')?[p(i,'Oscilobatiente')&&'oscilobatiente '+yes(p(i,'Oscilobatiente')),p(i,'Manija')&&'manija '+yes(p(i,'Manija'))].filter(Boolean).join(' · '):undefined},
 ];
}

// Ancho y alto de cálculo: ventanas y puertas por su abertura; muros cortina por largo y altura del conjunto.
export function sizeOf(i:BudgetItem){
 const w=i.category==='Curtain Walls'?num(p(i,'Length')):num(i.width),h=i.category==='Curtain Walls'?num(p(i,'Unconnected Height')):num(i.height);
 return w!=null&&h!=null?{w,h,area:w*h,perimeter:2*(w+h)}:null;
}

export type BudgetRow={key:string;category:string;type:string;size:string;count:number;codes:string[];unitArea:number;area:number;perimeter:number};
// Cómputo agrupado por tipo y medida: lo que se le pide cotizar a un proveedor.
export function budgetTotals(items:BudgetItem[]){
 const rows=new Map<string,BudgetRow>(),missing:string[]=[];
 for(const i of items){
  const s=sizeOf(i);if(!s){missing.push(i.code);continue}
  const size=`${s.w.toFixed(2)} × ${s.h.toFixed(2)} m`,key=[i.category,i.type,size].join('|');
  const row=rows.get(key)||{key,category:i.category,type:i.type,size,count:0,codes:[],unitArea:s.area,area:0,perimeter:0};
  row.count++;row.codes.push(i.code);row.area+=s.area;row.perimeter+=s.perimeter;rows.set(key,row);
 }
 const glass=items.reduce((n,i)=>n+(i.survey?.glazing?.area_m2||0),0),profiles=items.reduce((n,i)=>n+(i.survey?.frame?.profiles||[]).reduce((a,x)=>a+x.length_m,0),0);
 const list=[...rows.values()].sort((a,b)=>a.category.localeCompare(b.category)||b.area-a.area);
 const by=(cat?:string)=>{const r=list.filter(x=>!cat||x.category===cat);return {count:r.reduce((n,x)=>n+x.count,0),area:r.reduce((n,x)=>n+x.area,0),perimeter:r.reduce((n,x)=>n+x.perimeter,0)}};
 return {rows:list,windows:by('Windows'),doors:by('Doors'),curtainWalls:by('Curtain Walls'),total:by(),missing,glass,profiles};
}

export function budgetCsv(rows:BudgetRow[]){
 const f=(n:number)=>n.toFixed(2).replace('.',',');
 return ['Categoría;Tipo;Medida (ancho × alto);Cantidad;Códigos;m² unitario;m² total;Metros lineales de marco',
  ...rows.map(r=>[r.category==='Windows'?'Ventana':r.category==='Doors'?'Puerta':'Muro cortina',r.type,r.size,r.count,r.codes.join(' '),f(r.unitArea),f(r.area),f(r.perimeter)].join(';'))].join('\n');
}
