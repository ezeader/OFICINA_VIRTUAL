/** Compulsa integration: immutable BIM quantities, versioned RFQs, explicit offer coverage.
 * Adapted workflow from manuader/compulsa (543cefef); no image measurement or inferred quantities.
 */
export type Quantity = {code:string;system:string;description:string;unit:string;quantity:number;trade?:string};
export type Publication = {id:string;project:string;revision:string;model:string;schedule:string;date:string;rows:Quantity[]};
export type Supplier = {id:string;name:string;trades:string;zone:string;contact:string;trusted:boolean;notes:string;sourceId?:string;source?:string;lat?:number;lon?:number};
export type Request = {id:string;project:string;publication:string;revision:string;title:string;date:string;rows:Quantity[];suppliers:string[];conditions:string};
export type OfferLine = {code:string;quantity:number;price:number;match:'exacta'|'sustituto';description?:string};
export type Offer = {id:string;request:string;supplier:string;reference:string;currency:'ARS'|'USD';validUntil:string;delivery:string;freight:number;taxesIncluded:boolean;lines:OfferLine[];date:string};
export type NativeTable={id:string;name:string;category:string;trade:string;columns:string[];rows:string[][];truncated:boolean};
export type NativeSnapshot={project:string;model:string;readAt:string;tables:NativeTable[]};
export type ProcurementData = {suppliers:Supplier[];publications:Publication[];requests:Request[];offers:Offer[];prices:Record<string,Record<string,number>>;nativeSnapshots?:Record<string,NativeSnapshot>;rubroBudget?:Record<string,import('./rubro-budget').RubroBudgetState>};
export const trades=[['sanitarias','Sanitarias'],['electricas','Eléctricas'],['aberturas','Aberturas'],['albanileria','Albañilería'],['estructura','Estructura'],['gas','Gas'],['climatizacion','Climatización'],['cubiertas','Cubiertas e impermeabilización'],['revestimientos','Pisos y revestimientos'],['pintura','Pintura'],['carpinteria','Carpintería y equipamiento'],['exteriores','Exteriores'],['superficies','Superficies'],['otros','Sin clasificar']] as const;
export function tradeOf(row:Quantity){return row.trade||( ['AF','AC','CP','CS','PL'].includes(row.system)?'sanitarias':'otros');}
export function rowsForTrade(rows:Quantity[],trade:string){return rows.filter(r=>trade==='todos'||tradeOf(r)===trade);}
export function latestOffers(offers:Offer[]){const bySupplier=new Map<string,Offer>();for(const o of [...offers].sort((a,b)=>a.date.localeCompare(b.date)))bySupplier.set(o.supplier,o);return [...bySupplier.values()];}
export const emptyProcurement=():ProcurementData=>({suppliers:[],publications:[],requests:[],offers:[],prices:{}});
export const systems:Record<string,string>={AF:'Agua fría',AC:'Agua caliente',CP:'Cloacal primario',CS:'Cloacal secundario',PL:'Pluvial',EQ:'Equipos',VM:'VM · según modelo',RV:'Por revisar'};
export function csv(text:string):string[][] {
 const raw=text.replace(/^\uFEFF/,'').trim();if(!raw)throw Error('El archivo está vacío.');
 const delimiter=raw.split(/\r?\n/)[0].includes(';')?';':',';
 const rows:string[][]=[];let row:string[]=[],cell='',quoted=false;
 for(let i=0;i<raw.length;i++){const ch=raw[i];if(ch==='"'){if(quoted&&raw[i+1]==='"'){cell+='"';i++}else quoted=!quoted;}else if(ch===delimiter&&!quoted){row.push(cell.trim());cell=''}else if(ch==='\n'&&!quoted){row.push(cell.trim());rows.push(row);row=[];cell=''}else if(ch!=='\r'||quoted)cell+=ch;}
 if(quoted)throw Error('Hay comillas sin cerrar en el CSV.');row.push(cell.trim());rows.push(row);return rows.filter(r=>r.some(Boolean));
}
function records(text:string,required:string[]){const [head,...rows]=csv(text);const headers=head.map(h=>h.toLowerCase());for(const key of required)if(!headers.includes(key))throw Error('Falta la columna '+key+'. Usá la plantilla.');if(new Set(headers).size!==headers.length)throw Error('Hay columnas repetidas.');if(rows.length>3000)throw Error('Importá hasta 3000 renglones por publicación.');return rows.map((r,i)=>{if(r.length!==headers.length)throw Error('Revisá las columnas del renglón '+(i+2));return Object.fromEntries(headers.map((h,j)=>[h,r[j]]))});}
export function number(value:string){if(!/^(?:\d+)(?:[.,]\d+)?$/.test(value.trim()))throw Error('Usá números positivos sin separador de miles.');const n=Number(value.replace(',','.'));if(!Number.isFinite(n)||n>1e12)throw Error('Número fuera de rango.');return n;}
export function parseSchedule(text:string):Quantity[]{const seen=new Set<string>();return records(text,['codigo','sistema','descripcion','unidad','cantidad']).map(r=>{if(!r.codigo||!r.sistema||!r.descripcion)throw Error('Código, sistema y descripción son obligatorios.');if(seen.has(r.codigo))throw Error('Código repetido: '+r.codigo+'. Importá un cómputo consolidado, no varias vistas del mismo elemento.');seen.add(r.codigo);const unit=r.unidad.toLowerCase();if(!['m','m2','m3','u','kg','l'].includes(unit))throw Error('Unidad no admitida en '+r.codigo+': usá m, m2, m3, u, kg o l.');const quantity=number(r.cantidad);if(quantity<=0)throw Error('La cantidad debe ser mayor que cero: '+r.codigo);if(unit==='u'&&!Number.isInteger(quantity))throw Error('Las unidades deben ser enteras: '+r.codigo);return {code:r.codigo,system:r.sistema.toUpperCase(),description:r.descripcion,unit,quantity};});}
export function parseOffer(text:string,request:Request):OfferLine[]{const seen=new Set<string>();return records(text,['codigo','cantidad','precio_unitario','coincidencia']).map(r=>{if(!request.rows.some(x=>x.code===r.codigo))throw Error('Código ajeno al pedido: '+r.codigo);if(seen.has(r.codigo))throw Error('Código repetido en la oferta: '+r.codigo);seen.add(r.codigo);if(!['exacta','sustituto'].includes(r.coincidencia))throw Error('Coincidencia debe ser exacta o sustituto.');return {code:r.codigo,quantity:number(r.cantidad),price:number(r.precio_unitario),match:r.coincidencia as OfferLine['match'],...(r.descripcion_ofertada?{description:r.descripcion_ofertada}:{})};});}
export function coverage(request:Request,offer:Offer,today=new Date().toISOString().slice(0,10)){
 const missing=request.rows.filter(r=>{const l=offer.lines.find(l=>l.code===r.code);return !l||l.match!=='exacta'||l.quantity<r.quantity;});
 const covered=request.rows.filter(r=>!missing.includes(r));
 const subtotal=covered.reduce((sum,r)=>sum+r.quantity*offer.lines.find(l=>l.code===r.code)!.price,0);
 return {missing,covered:covered.length,subtotal,total:subtotal+offer.freight,complete:missing.length===0,expired:offer.validUntil<today};
}
export function exportCsv(rows:unknown[][]){return '\uFEFF'+rows.map(row=>row.map(x=>'"'+(typeof x==='string'&&/^[=+@\-\t\r]/.test(x)?"'"+x:String(x??'')).replaceAll('"','""')+'"').join(';')).join('\r\n');}
export function requestText(request:Request,projectName:string,supplierName:string){return `ADER STUDIO · SOLICITUD DE COTIZACIÓN\n${projectName} · ${request.title}\nDestinatario: ${supplierName}\nBase BIM: ${request.revision}\nPedido: ${request.id}\nFecha: ${request.date.slice(0,10)}\n\n${request.rows.map(r=>`${r.code} | ${r.system} | ${r.description} | ${r.quantity} ${r.unit}`).join('\n')}\n\nCONDICIONES\n${request.conditions}\n\nIndicar precio unitario por código en la unidad solicitada, moneda, impuestos, flete, disponibilidad, plazo de entrega y vigencia. Identificar faltantes y alternativas por separado. No reemplazar productos sin aprobación.\n`;}
