// Presupuesto por rubro: cómputo del modelo (Revit) × precio unitario → subtotal por rubro → total.
// Genérico para cualquier proyecto: cada rubro llega como una lista de partidas con cantidad y unidad.
// Nunca inventa precios: una partida sin precio queda "por cotizar" y el rubro no se da por completo.
// Autocontenido (sin imports de otros lib) para poder testearlo con node --test.

export type BudgetLine={id:string;label:string;quantity:number;unit:string;detail?:string;informative?:boolean};
export type ComputeStatus='modelado'|'propuesta'|'estimacion'|'sin-computo';
export type RubroSource={key:string;name:string;status:ComputeStatus;lines:BudgetLine[];note?:string};
// Lo que guarda el estudio por proyecto (workspace → procurement.rubroBudget[proyecto]).
export type RubroBudgetState={currency?:'ARS'|'USD';prices?:Record<string,number>;optional?:Record<string,boolean>;skip?:Record<string,boolean>;updatedAt?:string};
// Partidas explícitas que puede publicar el manifest de un rubro (manifest.budget). Si no están, se usan los totales.
export type ManifestBudget={lines:{id?:string;label:string;value:number;unit:string;detail?:string;informative?:boolean}[]};

// Rubros que por defecto se ofrecen al cliente como opcionales (se pueden sumar ahora o más adelante).
export const DEFAULT_OPTIONAL=['domotica','solar'];
export const globalId=(rubro:string)=>`${rubro}:global`;
const slug=(s:string)=>s.normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
export const lineId=(rubro:string,label:string)=>`${rubro}:${slug(label)}`;

// Totales que resumen otros (p. ej. "Muros (todos)", "Tubo total", "modelados") se muestran como información,
// no se cotizan: sumarían dos veces lo mismo.
const SUMMARY=/\(tod[oa]s|\btotal\b|modelad|existentes/i;
export function linesFromManifest(rubro:string,m:{budget?:ManifestBudget;totals?:{label:string;value:number;unit:string;detail?:string}[]}):BudgetLine[]{
 if(m.budget?.lines?.length)return m.budget.lines.filter(l=>l.value>0).map(l=>({id:l.id?`${rubro}:${l.id}`:lineId(rubro,l.label),label:l.label,quantity:l.value,unit:l.unit,detail:l.detail,informative:!!l.informative}));
 const seen=new Set<string>();
 return (m.totals||[]).filter(t=>t.value>0).map(t=>{let id=lineId(rubro,t.label);while(seen.has(id))id+='-b';seen.add(id);return {id,label:t.label,quantity:t.value,unit:t.unit,detail:t.detail,informative:SUMMARY.test(t.label)}});
}
export function manifestStatus(m:{status?:string;sheets?:unknown[];totals?:unknown[];budget?:ManifestBudget}|null|undefined):ComputeStatus{
 if(!m)return 'sin-computo';
 const hasLines=!!(m.budget?.lines?.length||m.totals?.length);
 return !hasLines?'sin-computo':m.status==='propuesta'?'propuesta':(m.sheets||[]).length?'modelado':'estimacion';
}

// Sanitarias: cañerías del modelo agrupadas por sistema, tipo y diámetro (metros lineales reales de Revit).
export function sanitaryLines(rows:{group:string;type?:string;diameter_mm?:number;length_model_m?:number}[],names:Record<string,string>={}):BudgetLine[]{
 const map=new Map<string,BudgetLine>();
 for(const r of rows){
  if(!(r.length_model_m! > 0))continue;
  const label=`${names[r.group]||r.group} · ${r.type||'cañería'}${r.diameter_mm?` Ø${Math.round(r.diameter_mm)}`:''}`,id=lineId('sanitaria',label);
  const line=map.get(id)||{id,label,quantity:0,unit:'ml',detail:'longitud real del modelo'};
  line.quantity+=r.length_model_m!;map.set(id,line);
 }
 return [...map.values()].sort((a,b)=>a.label.localeCompare(b.label,'es',{numeric:true}));
}

export type PricedLine=BudgetLine&{price?:number;amount?:number;skipped:boolean};
export type RubroResult={key:string;name:string;status:ComputeStatus;note?:string;optional:boolean;lines:PricedLine[];global?:number;subtotal:number;missing:number;complete:boolean;share?:number};
export function computeBudget(sources:RubroSource[],state:RubroBudgetState={}){
 const prices=state.prices||{},skip=state.skip||{};
 const isOptional=(k:string)=>state.optional?.[k]??DEFAULT_OPTIONAL.includes(k);
 const rubros:RubroResult[]=sources.map(s=>{
  const lines:PricedLine[]=s.lines.map(l=>{const skipped=!!(skip[l.id]??l.informative);const price=prices[l.id];return {...l,skipped,price,amount:!skipped&&price!=null?price*l.quantity:undefined}});
  const global=prices[globalId(s.key)];
  const open=lines.filter(l=>!l.skipped);
  // Una cotización global (cerrada) reemplaza a las partidas: el proveedor cotizó el rubro completo.
  const missing=global!=null?0:open.filter(l=>l.price==null).length;
  const subtotal=global!=null?global:open.reduce((n,l)=>n+(l.amount||0),0);
  const complete=global!=null||(open.length>0&&missing===0);
  return {key:s.key,name:s.name,status:s.status,note:s.note,optional:isOptional(s.key),lines,global,subtotal,missing,complete};
 });
 const base=rubros.filter(r=>!r.optional),optional=rubros.filter(r=>r.optional);
 const baseTotal=base.reduce((n,r)=>n+r.subtotal,0),optionalTotal=optional.reduce((n,r)=>n+r.subtotal,0);
 for(const r of rubros)r.share=baseTotal>0&&r.subtotal>0?r.subtotal/baseTotal:undefined;
 const lines=rubros.flatMap(r=>r.global!=null?[]:r.lines.filter(l=>!l.skipped));
 return {rubros,base,optional,baseTotal,optionalTotal,total:baseTotal+optionalTotal,
  baseComplete:base.every(r=>r.complete),
  progress:{rubros:rubros.length,withCompute:rubros.filter(r=>r.status!=='sin-computo').length,modeled:rubros.filter(r=>r.status==='modelado').length,priced:rubros.filter(r=>r.complete).length,lines:lines.length,pricedLines:lines.filter(l=>l.price!=null).length}};
}
export type BudgetResult=ReturnType<typeof computeBudget>;

// Planilla para pedir precios a proveedores o cargarlos en lote: misma columna id para volver a importarla.
export function budgetSheet(result:BudgetResult){
 const f=(n?:number)=>n==null?'':String(Math.round(n*100)/100).replace('.',',');
 const rows:(string|number)[][]=[['id','rubro','alcance','partida','cantidad','unidad','precio_unitario','subtotal','detalle']];
 for(const r of result.rubros){
  rows.push([globalId(r.key),r.name,r.optional?'opcional':'base','Global del rubro (cotización cerrada)',1,'gl',f(r.global),f(r.global),'si se completa, reemplaza a las partidas']);
  for(const l of r.lines.filter(l=>!l.skipped))rows.push([l.id,r.name,r.optional?'opcional':'base',l.label,f(l.quantity),l.unit,f(l.price),f(l.amount),l.detail||'']);
 }
 return rows;
}
// Lee precios de una planilla con columnas id y precio_unitario (vacíos se ignoran).
export function pricesFromRows(rows:string[][],known:Set<string>){
 const [head,...body]=rows,h=head.map(x=>x.trim().toLowerCase()),iId=h.indexOf('id'),iPrice=h.indexOf('precio_unitario');
 if(iId<0||iPrice<0)throw Error('La planilla necesita las columnas id y precio_unitario. Usá la que descarga la oficina.');
 const prices:Record<string,number>={};
 for(const r of body){
  // Con coma decimal, los puntos son de miles (1.234,50); sin coma, el punto es decimal (1234.5).
  const text=(r[iPrice]||'').trim(),id=(r[iId]||'').trim(),raw=text.includes(',')?text.replace(/\./g,'').replace(',','.'):text;
  if(!id||!raw)continue;
  if(!known.has(id))throw Error('Partida desconocida: '+id+'. Descargá la planilla de nuevo.');
  const n=Number(raw);if(!Number.isFinite(n)||n<0||n>1e12)throw Error('Precio inválido en '+id+'.');
  prices[id]=n;
 }
 return prices;
}
