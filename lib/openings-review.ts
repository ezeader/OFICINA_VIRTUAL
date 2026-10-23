// Revisión de aberturas: lógica pura compartida por la mesa web y los tests.
// Los valores de Revit nunca se modifican acá: las correcciones viven aparte,
// en el JSON del espacio de trabajo, y quedan pendientes de aplicar en Revit.

export type CorrectionStatus='open'|'proposed'|'applied'|'dismissed';
export const CORRECTION_STATUS:Record<CorrectionStatus,string>={
 open:'Sin revisar',
 proposed:'Corrección cargada · pendiente en Revit',
 applied:'Aplicada en Revit · confirmar en la próxima lectura',
 dismissed:'No corresponde corregir',
};
export type OpeningCorrection={value?:string;note?:string;status:CorrectionStatus;updatedAt:string};
export type OpeningsReview={version:1;items:Record<string,Record<string,OpeningCorrection>>};

type Param={name:string;value:string;scope?:string};
export type ReviewItem={id:string;code:string;category:string;type?:string;rooms?:number[];warnings:string[];width?:string|null;height?:string|null;sill?:string|null;head?:string|null;roughWidth?:string|null;roughHeight?:string|null;thickness?:string|null;profileThickness?:string|null;glazingThickness?:string|null;hostThickness?:number|null;panelCount?:number;parameters?:Param[];documentation?:{sheetId?:string;dimensions?:{label:string;value_m:number}[]};dimensions?:{label:string}[]};

const STATUSES=Object.keys(CORRECTION_STATUS) as CorrectionStatus[];
const MAX_VALUE=200,MAX_NOTE=2000;

export const emptyReview=():OpeningsReview=>({version:1,items:{}});

// El JSON del espacio puede venir editado a mano o de una versión vieja: se valida campo por campo.
export function normalizeReview(raw:unknown):OpeningsReview{
 const out=emptyReview();
 const items=(raw as {items?:unknown})?.items;
 if(!items||typeof items!=='object')return out;
 for(const [itemId,entries] of Object.entries(items as Record<string,unknown>)){
  if(!entries||typeof entries!=='object')continue;
  for(const [key,c] of Object.entries(entries as Record<string,unknown>)){
   const r=c as Partial<OpeningCorrection>;
   if(!r||typeof r!=='object'||!STATUSES.includes(r.status as CorrectionStatus))continue;
   const value=typeof r.value==='string'?r.value.slice(0,MAX_VALUE):undefined,note=typeof r.note==='string'?r.note.slice(0,MAX_NOTE):undefined;
   (out.items[itemId] ||= {})[key]={status:r.status as CorrectionStatus,updatedAt:typeof r.updatedAt==='string'?r.updatedAt:'',...(value?{value}:{}),...(note?{note}:{})};
  }
 }
 return out;
}

export function warningKey(text:string){
 return 'w:'+text.normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,60);
}
export const measureKey=(field:string)=>'m:'+field;

export function correctionFor(review:OpeningsReview|undefined,itemId:string,key:string){return review?.items[itemId]?.[key]}

// Actualización inmutable. Una corrección vacía y sin revisar se elimina para no ensuciar el JSON.
export function setCorrection(review:OpeningsReview|undefined,itemId:string,key:string,patch:{value?:string;note?:string;status?:CorrectionStatus},now:string):OpeningsReview{
 const base=normalizeReview(review);
 const prev=base.items[itemId]?.[key];
 const value=(patch.value??prev?.value??'').trim().slice(0,MAX_VALUE),note=(patch.note??prev?.note??'').trim().slice(0,MAX_NOTE);
 let status=patch.status??prev?.status??'open';
 if(!patch.status&&status==='open'&&(value||note))status='proposed';
 const entries={...base.items[itemId]};
 if(!value&&!note&&status==='open')delete entries[key];
 else entries[key]={status,updatedAt:now,...(value?{value}:{}),...(note?{note}:{})};
 const items={...base.items};
 if(Object.keys(entries).length)items[itemId]=entries;else delete items[itemId];
 return {version:1,items};
}

// Interpreta una medida escrita a mano. Sin unidad: hasta 10 se lee en metros; más, en milímetros.
export function parseLength(input:string):number|null{
 const m=/^\s*(-?\d+(?:[.,]\d+)?)\s*(mm|cm|m)?\s*$/i.exec(input||'');
 if(!m)return null;
 const n=Number(m[1].replace(',','.'));
 if(!Number.isFinite(n)||n<0)return null;
 const unit=(m[2]||(n>10?'mm':'m')).toLowerCase();
 return unit==='mm'?n/1000:unit==='cm'?n/100:n;
}
export const formatMeters=(n:number)=>n.toLocaleString('es-AR',{minimumFractionDigits:3,maximumFractionDigits:3})+' m';
export function metersOf(value?:string|null){if(!value)return null;const n=parseFloat(value.replace(',','.'));return Number.isFinite(n)?n:null}
export const param=(item:ReviewItem,name:string)=>item.parameters?.find(p=>p.name===name)?.value;

export type Measure={key:string;label:string;value?:string;origin:string;required:boolean;dimensioned:boolean;note?:string};
// Qué medidas cubre cada cota de las láminas: R2 (Ancho/Alto) y R4 (cadenas de alzado y planta).
const DIMENSION_FIELDS:Record<string,string[]>={'Ancho':['width'],'Alto':['height'],'Ancho de vano':['roughWidth'],'Alto de vano':['roughHeight'],'Ancho en planta':['width'],'Alto (piso a dintel)':['height','head'],'Antepecho + alto':['sill','height'],'Altura de dintel':['head'],'Largo total':['length'],'Modulos (ejes de grilla)':['length'],'Alto total':['wallHeight'],'Altura total desde nivel':['wallHeight'],'Arranque + modulos verticales':['baseOffset','wallHeight']};

// Medidas necesarias para fabricar. Solo se listan valores leídos de Revit; lo que falta queda vacío.
export function fabricationMeasures(item:ReviewItem):Measure[]{
 const dimensioned=new Set([...(item.documentation?.dimensions||[]),...(item.dimensions||[])].flatMap(d=>DIMENSION_FIELDS[d.label]||[]));
 const row=(key:string,label:string,value:string|null|undefined,origin:string,required=true,note?:string):Measure=>({key,label,value:value||undefined,origin,required,dimensioned:dimensioned.has(key),...(note?{note}:{})});
 if(item.category==='Curtain Walls'){
  const top=param(item,'Top Constraint'),attached=param(item,'Top is Attached')==='Yes';
  return [
   row('length','Largo del conjunto',param(item,'Length'),'Parámetro nativo Length'),
   row('wallHeight','Altura del conjunto',param(item,'Unconnected Height'),'Parámetro nativo Unconnected Height',true,[top&&top!=='Unconnected'?'Restricción superior: '+top:'',attached?'Parte superior enlazada: la altura real puede seguir al elemento superior.':''].filter(Boolean).join(' ')||undefined),
   row('baseOffset','Desfase inferior',param(item,'Base Offset'),'Respecto de '+(param(item,'Base Constraint')||'su nivel')),
   row('panels','Paneles',item.panelCount==null?undefined:String(item.panelCount),'Conteo de paneles del conjunto',false),
   row('mullion','Montante',item.parameters?.find(p=>p.name==='Interior Type')?.value,'Tipo de montante interior',false),
   row('breakdown','Despiece de paneles y montantes',undefined,'No existe en la lectura: requiere despiece propio'),
  ];
 }
 return [
  row('width','Ancho',item.width,'Width'),
  row('height','Alto',item.height,'Height'),
  row('sill','Antepecho / arranque',item.sill,'Sill Height, respecto del nivel'),
  row('head','Altura superior',item.head,'Head Height, respecto del nivel'),
  row('roughWidth','Ancho de vano',item.roughWidth,'Rough Width'),
  row('roughHeight','Alto de vano',item.roughHeight,'Rough Height'),
  row('thickness','Espesor de hoja / perfil',item.thickness||item.profileThickness,'Thickness o grosor del marco'),
  row('hostThickness','Espesor del muro anfitrión',item.hostThickness==null?undefined:formatMeters(item.hostThickness),'Muro donde se aloja; no es el espesor de la abertura',false),
 ];
}
export const missingMeasures=(item:ReviewItem)=>fabricationMeasures(item).filter(m=>m.required&&!m.value);

// Estado de revisión de las advertencias de un elemento.
export function itemProgress(item:ReviewItem,review?:OpeningsReview){
 const out={total:item.warnings.length,open:0,proposed:0,applied:0,dismissed:0,measures:0};
 for(const w of item.warnings)out[correctionFor(review,item.id,warningKey(w))?.status||'open']++;
 out.measures=Object.keys(review?.items[item.id]||{}).filter(k=>k.startsWith('m:')).length;
 return out;
}
export function reviewTotals(items:ReviewItem[],review?:OpeningsReview){
 const t={warnings:0,open:0,proposed:0,applied:0,dismissed:0,measures:0,itemsWithWarnings:0};
 for(const i of items){const p=itemProgress(i,review);t.warnings+=p.total;t.open+=p.open;t.proposed+=p.proposed;t.applied+=p.applied;t.dismissed+=p.dismissed;t.measures+=p.measures;if(p.total)t.itemsWithWarnings++}
 return t;
}

// Lista de lo cargado en la web que todavía hay que llevar a Revit.
export function pendingForRevit(items:ReviewItem[],review?:OpeningsReview){
 const rows:{code:string;id:string;subject:string;original:string;value?:string;note?:string;status:CorrectionStatus}[]=[];
 for(const item of items){
  const entries=review?.items[item.id];if(!entries)continue;
  const measures=fabricationMeasures(item);
  for(const [key,c] of Object.entries(entries)){
   if(c.status!=='proposed')continue;
   const warning=item.warnings.find(w=>warningKey(w)===key),measure=key.startsWith('m:')?measures.find(m=>measureKey(m.key)===key):undefined;
   rows.push({code:item.code,id:item.id,subject:warning||measure?.label||key,original:measure?(measure.value||'Sin dato en Revit'):'Advertencia de la lectura',value:c.value,note:c.note,status:c.status});
  }
 }
 return rows.sort((a,b)=>a.code.localeCompare(b.code,'es',{numeric:true}));
}

type SheetSource={items:ReviewItem[];rooms:{id:number;sheetId?:string;items:string[]}[];reviewCases?:{context?:{sheetId?:string}}[];counts:{windows:number;doors:number;curtainWalls:number;unassigned:number}};
export function sheetTotals(m:SheetSource){
 const room=m.rooms.filter(r=>r.sheetId).length,element=m.items.filter(i=>i.documentation?.sheetId).length,context=(m.reviewCases||[]).filter(c=>c.context?.sheetId).length;
 return {room,element,context,total:room+element+context,elements:m.items.length,windows:m.counts.windows,doors:m.counts.doors,curtainWalls:m.counts.curtainWalls,unassigned:m.counts.unassigned,shared:m.items.filter(i=>(i.rooms?.length||0)>1).length,roomAppearances:m.rooms.reduce((n,r)=>n+r.items.length,0)};
}
