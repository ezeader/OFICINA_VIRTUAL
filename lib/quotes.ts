/** Cotizaciones por rubro: proveedores con OK "apto", presupuestos recibidos contra el cómputo, negociaciones.
 * El cómputo (ítems) es documentación del proyecto y vive en public/. Proveedores, presupuestos y
 * negociaciones son datos reales: se guardan en el workspace (D1), nunca en git.
 */
export type QuoteItem={code:string;description:string;unit:string;quantity:number;materialOptional?:boolean};
export type QuoteSystem={key:string;name:string;items:QuoteItem[]};
export type QuoteSheet={rubro:string;name:string;project:string;location:string;revision:string;date:string;basis:string;count:number;systems:QuoteSystem[];excluded:string[];documents:{name:string;url:string}[];locales:Record<string,Record<string,number>>};

export type SupplierKind='materiales'|'mano de obra'|'materiales + mano de obra';
export type QuoteSupplier={id:string;name:string;kind:SupplierKind;group:'local'|'costa'|'nacional';contact:string;location:string;zone:string;source?:string;notes?:string;
 apto:'pendiente'|'apto'|'no apto';requestedAt?:string;declined?:boolean};
export type QuoteLine={material?:number;labor?:number;brand?:string;note?:string};
export type Quote={id:string;supplier:string;date:string;reference:string;currency:'ARS'|'USD';taxesIncluded:boolean;scope:SupplierKind;
 validUntil:string;delivery:string;zone:string;zoneViable:'sí'|'no'|'a confirmar';freight:number;laborGlobal?:number;lines:Record<string,QuoteLine>;notes?:string};
export type NegotiationKind='consulta del proveedor'|'pregunta mano de obra'|'pregunta materiales'|'marcas'|'contraoferta'|'acuerdo'|'nota';
export type NegotiationEntry={id:string;supplier:string;date:string;from:'proveedor'|'ader';kind:NegotiationKind;text:string;amount?:number;resolved?:boolean};
export type RubroQuotes={suppliers:QuoteSupplier[];quotes:Quote[];negotiation:NegotiationEntry[]};
export type QuotesData=Record<string,Record<string,RubroQuotes>>;

export const NEGOTIATION_KINDS:NegotiationKind[]=['consulta del proveedor','pregunta mano de obra','pregunta materiales','marcas','contraoferta','acuerdo','nota'];
export const QUOTE_RUBROS:{key:string;name:string;sheet?:string}[]=[
 {key:'sanitaria',name:'Instalación sanitaria',sheet:'/casa-angel/cotizacion/sanitaria-R13.json'},
];
export const emptyRubroQuotes=():RubroQuotes=>({suppliers:[],quotes:[],negotiation:[]});
export const TARGET_QUOTES=3;
/** Nota que la planilla trae de fábrica en artefactos; no es una observación del proveedor. */
export const TEMPLATE_NOTE='Material opcional:';
/** Días sin respuesta a partir de los cuales hay que sumar proveedores (pedido: 5 a 7). */
export const FOLLOW_UP_DAYS=5;

export const items=(sheet:QuoteSheet)=>sheet.systems.flatMap(s=>s.items);
export const needsMaterial=(scope:SupplierKind)=>scope!=='mano de obra';
export const needsLabor=(scope:SupplierKind)=>scope!=='materiales';
const priced=(n:number|undefined)=>typeof n==='number'&&Number.isFinite(n)&&n>=0;

export type ItemStatus='completo'|'parcial'|'falta';
/** Estado de un ítem según lo que el proveedor dice cotizar. Un material opcional nunca se exige
 * (en un presupuesto solo de materiales, el artefacto no aplica); una mano de obra global cubre la de todos los ítems. */
export function itemStatus(item:QuoteItem,quote:Quote):ItemStatus{
 const l=quote.lines[item.code]||{};
 const mat=!needsMaterial(quote.scope)||item.materialOptional||priced(l.material);
 const lab=!needsLabor(quote.scope)||priced(quote.laborGlobal)||priced(l.labor);
 if(mat&&lab)return 'completo';
 return priced(l.material)||priced(l.labor)?'parcial':'falta';
}
export function compareQuote(sheet:QuoteSheet,quote:Quote){
 const all=items(sheet);let material=0,labor=0;
 const status:Record<string,ItemStatus>={};
 for(const it of all){
  const l=quote.lines[it.code]||{};status[it.code]=itemStatus(it,quote);
  if(priced(l.material))material+=l.material!*it.quantity;
  if(priced(l.labor))labor+=l.labor!*it.quantity;
 }
 if(priced(quote.laborGlobal))labor+=quote.laborGlobal!;
 const missing=all.filter(it=>status[it.code]==='falta'),partial=all.filter(it=>status[it.code]==='parcial');
 const covered=all.length-missing.length-partial.length;
 return {material,labor,freight:quote.freight||0,total:material+labor+(quote.freight||0),status,missing,partial,covered,count:all.length,complete:covered===all.length};
}
/** Última respuesta de cada proveedor (las anteriores quedan como historial de la negociación). */
export function latestQuotes(quotes:Quote[]){const m=new Map<string,Quote>();for(const q of [...quotes].sort((a,b)=>a.date.localeCompare(b.date)))m.set(q.supplier,q);return [...m.values()];}
/** Evolución del número por proveedor: cada presupuesto recibido y cada monto de la negociación, en orden. */
export function priceHistory(sheet:QuoteSheet,data:RubroQuotes,supplier:string){
 const steps=[
  ...data.quotes.filter(q=>q.supplier===supplier).map(q=>({date:q.date,label:'Presupuesto '+q.reference,amount:compareQuote(sheet,q).total,currency:q.currency})),
  ...data.negotiation.filter(n=>n.supplier===supplier&&priced(n.amount)).map(n=>({date:n.date,label:(n.from==='ader'?'Ader · ':'Proveedor · ')+n.kind,amount:n.amount!,currency:undefined as Quote['currency']|undefined})),
 ].sort((a,b)=>a.date.localeCompare(b.date));
 return steps.map((s,i)=>({...s,delta:i?s.amount-steps[i-1].amount:0}));
}
export function followUp(data:RubroQuotes,today=new Date()){
 const answered=new Set(latestQuotes(data.quotes).map(q=>q.supplier));
 const waiting=data.suppliers.filter(s=>s.apto==='apto'&&s.requestedAt&&!answered.has(s.id)&&!s.declined).map(s=>({supplier:s,days:Math.floor((+today-+new Date(s.requestedAt!))/864e5)}));
 const late=waiting.filter(w=>w.days>=FOLLOW_UP_DAYS);
 return {answered:answered.size,waiting,late,searchMore:answered.size<TARGET_QUOTES&&late.length>0};
}

/** Borrador del pedido de cotización. Solo texto: enviar es una acción aparte que el usuario aprueba. */
export function requestMail(sheet:QuoteSheet,supplier:Pick<QuoteSupplier,'name'|'kind'>,deadline:string){
 const sys=sheet.systems.map(s=>s.name.toLowerCase().replace(/ \(.*\)$/,'')).join(', ');
 const scope=supplier.kind==='materiales'
  ?'Precio unitario de materiales. Si también hacen o recomiendan la mano de obra, cotizarla en su columna; si no, dejarla vacía.'
  :supplier.kind==='mano de obra'
   ?'Precio unitario de mano de obra. Si también proveen materiales, cotizarlos en su columna; si no, dejarla vacía.'
   :'Precio unitario de materiales y, aparte, de mano de obra.';
 return {
  subject:`Pedido de cotización · ${sheet.name} · ${sheet.project} (${sheet.location.split(',')[0]})`,
  body:`Hola, ${supplier.name}:

Soy Ezequiel Ader, de Estudio Ader. Pedimos cotización para la ${sheet.name.toLowerCase()} de ${sheet.project}, una vivienda unifamiliar en ${sheet.location}.

Adjuntamos:
· Planilla de cómputo (Excel): ${sheet.count} ítems ordenados por sistema (${sys}). Cada ítem figura una sola vez.
${sheet.documents.map(d=>'· '+d.name+' (PDF).').join('\n')}

En la planilla, completar:
1. ${scope}
2. Validez de la oferta.
3. Plazo de entrega de materiales y de ejecución.
4. Zona en la que trabajan y si el precio incluye el flete a Pinamar Norte.

Si no cotizan algún ítem o proponen otra marca, indicarlo en la planilla. Las dudas sobre el proyecto, por este mismo medio.

Necesitaríamos la cotización antes del ${deadline}.

Saludos,
Ezequiel Ader
Estudio Ader · ader.studio`};
}

/** Lee la planilla devuelta por el proveedor (misma estructura que la enviada): columnas por código. */
export function linesFromRows(sheet:QuoteSheet,rows:Record<string,string>[]){
 const known=new Set(items(sheet).map(i=>i.code)),lines:Record<string,QuoteLine>={};const errors:string[]=[];
 const num=(v:string|undefined,code:string,what:string)=>{if(v==null||v.trim()==='')return undefined;const t=v.trim().replace(/\s|\$/g,'');const n=Number(/,\d{1,2}$/.test(t)?t.replace(/\./g,'').replace(',','.'):t.replace(/,/g,''));if(!Number.isFinite(n)||n<0){errors.push(`${code}: ${what} no es un número (${v})`);return undefined}return n};
 for(const r of rows){
  const code=(r.A||'').trim();if(!known.has(code))continue;
  const line:QuoteLine={material:num(r.E,code,'material'),labor:num(r.G,code,'mano de obra'),brand:r.J?.trim()||undefined,note:r.K?.trim()&&!r.K.trim().startsWith(TEMPLATE_NOTE)?r.K.trim():undefined};
  if(line.material!=null||line.labor!=null||line.brand||line.note)lines[code]=Object.fromEntries(Object.entries(line).filter(([,v])=>v!==undefined));
 }
 return {lines,errors};
}
