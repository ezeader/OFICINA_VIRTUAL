// Lectura R4 de aberturas: láminas por local con alzados acotados en Revit.
// Todo es opcional: si el manifest no trae R4, la mesa sigue con R2/R3 y el esquema web.

export type R4Dim={label:string;values_m:number[];associative?:boolean;view?:'plan'|'elevation';roomKey?:string};
// R8 suma por vista: región en la lámina, etiqueta del local, códigos etiquetados y sus cotas.
export type R4View={id:number;name:string;label?:string;scale:number;kind?:'plan'|'axo'|'elevation';elementId?:string|null;code?:string|null;image:string;region?:number[];roomLabel?:string;tags?:string[];dimensions?:{label:string;values_m:number[];associative?:boolean;code?:string}[];elements?:{code:string;box:number[]}[]};
export type R4Sheet={sheetId:string;sheetNumber:string;page?:number;pages?:number;pdf?:string;image:string;thumbnail?:string;preview?:string;views:R4View[]};
export type R4Group={key:string;roomId?:number|null;name:string;level?:string;codes?:string[];sheets:R4Sheet[]};
export type R4Summary={revision?:string;totals?:{roomGroups?:number;sheets?:number;elevations?:number;dimensions?:number;nonAssociativeDimensions?:number;roomsWithoutOpenings?:string[]};sheets?:R4Group[]};
export type ViewDimension={label:string;values_m:number[];associative?:boolean;code?:string};
export type R4Drawing={id:number;name:string;label?:string;image:string;scale:number;code?:string;kind?:string;sheetNumber?:string;roomName?:string;dimensions?:ViewDimension[]};
type R4Item={id:string;code:string;documentation?:{r4?:{views?:{viewId:string;roomKey:string;roomName?:string;image?:string}[];dimensions?:R4Dim[]}}};

// Una cadena de cotas (p. ej. antepecho + alto) se muestra por tramos y con su total.
export function dimensionText(values:number[]){
 const f=(n:number)=>n.toLocaleString('es-AR',{minimumFractionDigits:3,maximumFractionDigits:3});
 return values.length>1?`${values.map(f).join(' + ')} = ${f(values.reduce((a,b)=>a+b,0))} m`:values.length?`${f(values[0])} m`:'sin valor';
}

// Cotas de una vista R4: el alzado lleva las de su elemento en ese local; la planta, los anchos de todos.
export function viewDimensions(view:R4View,roomKey:string,items:R4Item[]):ViewDimension[]{
 const of=(item:R4Item,kind:string)=>(item.documentation?.r4?.dimensions||[]).filter(d=>d.roomKey===roomKey&&(d.view||'elevation')===kind).map(d=>({label:d.label,values_m:d.values_m,associative:d.associative,code:item.code}));
 if(view.kind==='elevation'){const item=items.find(i=>i.id===String(view.elementId)||i.code===view.code);return item?of(item,'elevation'):[]}
 return items.flatMap(i=>of(i,'plan'));
}

const drawing=(view:R4View,sheet:R4Sheet,roomKey:string,roomName:string|undefined,items:R4Item[]):R4Drawing=>({id:view.id,name:view.name,label:view.label,image:view.image,scale:view.scale,kind:view.kind,sheetNumber:sheet.sheetNumber,roomName,...(view.code?{code:view.code}:{}),dimensions:viewDimensions(view,roomKey,items)});

// Documento navegable de un local (o del grupo «sin local») a partir de sus láminas R4.
export function r4GroupDocument(group:{key:string;name?:string;sheets:R4Sheet[]},items:R4Item[]){
 const [first]=group.sheets;if(!first)return undefined;
 return {sheetId:first.sheetId,sheetNumber:group.sheets.map(s=>s.sheetNumber).join(' · '),pdf:first.pdf,image:first.image,thumbnail:first.thumbnail,
  views:group.sheets.flatMap(s=>s.views.map(v=>drawing(v,s,group.key,group.name,items))),
  sheets:group.sheets.map(s=>({id:Number(s.sheetId)||0,name:s.sheetNumber,image:s.image}))};
}

// Alzados R4 de un elemento, uno por cada local donde aparece.
export function r4ElementViews(item:R4Item,groups:R4Group[],items:R4Item[]):R4Drawing[]{
 const index=new Map<string,{view:R4View;sheet:R4Sheet;group:R4Group}>();
 for(const group of groups)for(const sheet of group.sheets)for(const view of sheet.views)index.set(String(view.id),{view,sheet,group});
 return (item.documentation?.r4?.views||[]).flatMap(v=>{const hit=index.get(String(v.viewId));return hit?[{...drawing(hit.view,hit.sheet,v.roomKey,v.roomName||hit.group.name,items),name:`${hit.view.name} · ${v.roomName||hit.group.name}`}]:[]});
}

// Ordena la documentación de Aberturas como en Sanitarias: láminas agrupadas, cada una con sus dibujos.

export type ViewElement={code:string;elementId?:string;box:number[]};
export type SheetView={id:number;name:string;scale:number;image:string;code?:string;dimensions?:ViewDimension[];elements?:ViewElement[];region?:number[];tags?:string[];kind?:string};
export type SheetCard={key:string;tab:'locales'|'aberturas'|'revision';group:string;number:string;name:string;thumbnail?:string;preview?:string;image?:string;pdf?:string;sheetId?:string;views:SheetView[];itemIds:string[];roomId?:number;note?:string};
type Doc={sheetId?:string;sheetNumber?:string;pdf?:string;image?:string;thumbnail?:string;views?:{id:number;name:string;scale:number;image:string;elements?:ViewElement[]}[]};
type Manifest={
 items:{id:string;code:string;category:string;type:string;rooms:number[];documentation?:Doc}[];
 rooms:({id:number;number:string;name:string;level_name:string;items:string[];r4?:{sheets:R4Sheet[]}}&Doc)[];
 reviewCases?:{code:string;elementId:string;title:string;context?:Doc}[];
 documentationR4?:R4Summary;
};
export const CATEGORY_GROUP:Record<string,string>={Windows:'Ventanas',Doors:'Puertas','Curtain Walls':'Muros cortina'};
const byNumber=(a:string,b:string)=>a.localeCompare(b,'es',{numeric:true});
const cleanName=(name:string)=>name.split(' / ')[0].replace('Axonometrica','Axonométrica').replace('Corte del detalle modelado','Corte').replace('ubicacion','ubicación');
const plainViews=(doc:Doc,code?:string):SheetView[]=>(doc.views||[]).map(v=>({id:v.id,name:cleanName(v.name),scale:v.scale,image:v.image,...(code?{code}:{}),...(v.elements?{elements:v.elements}:{})}));

export function buildSheets(m:Manifest):SheetCard[]{
 const cards:SheetCard[]=[];
 const r4Pages=(group:R4Group,roomName:string,level:string,itemIds:string[],roomId?:number)=>{
  const doc=r4GroupDocument(group,m.items as never);if(!doc)return;
  group.sheets.forEach((sheet,page)=>cards.push({key:`r4-${group.key}-${page+1}`,tab:'locales',group:level,number:sheet.sheetNumber,name:roomName+(group.sheets.length>1?` · hoja ${page+1}`:''),thumbnail:sheet.thumbnail,preview:sheet.preview,image:sheet.image,pdf:sheet.pdf,sheetId:sheet.sheetId,
   views:sheet.views.map(v=>({id:v.id,name:v.code?`${v.code} · alzado`:cleanName(v.name).replace(' · '+(v.roomLabel||'§'),''),scale:v.scale,image:v.image,kind:v.kind,...(v.code?{code:v.code}:{}),...(v.region?{region:v.region}:{}),...(v.tags?{tags:v.tags}:{}),...(v.elements?{elements:v.elements}:{}),
    dimensions:v.dimensions?v.dimensions.map(d=>({label:d.label,values_m:d.values_m,associative:d.associative,...(d.code||v.code?{code:d.code||v.code!}:{})})):viewDimensions(v,group.key,m.items as never)})),itemIds,...(roomId!=null?{roomId}:{})}));
 };
 for(const room of [...m.rooms].sort((a,b)=>byNumber(a.level_name,b.level_name)||byNumber(a.number,b.number))){
  const name=`${room.number} · ${room.name}`;
  if(room.r4?.sheets?.length){r4Pages({key:String(room.id),name:room.name,sheets:room.r4.sheets},name,room.level_name,room.items,room.id);continue}
  if(!room.image||!room.items.length)continue; // un local sin aberturas no tiene nada que revisar en este rubro
  cards.push({key:`room-${room.id}`,tab:'locales',group:room.level_name,number:room.sheetNumber||'',name,thumbnail:room.thumbnail,image:room.image,pdf:room.pdf,sheetId:room.sheetId,views:plainViews(room),itemIds:room.items,roomId:room.id});
 }
 const unassigned=m.items.filter(i=>!i.rooms.length).map(i=>i.id),sl=m.documentationR4?.sheets?.find(g=>g.key==='SL');
 if(sl)r4Pages(sl,'Sin local asignado','Sin local asignado',unassigned);
 const order=Object.keys(CATEGORY_GROUP);
 for(const item of [...m.items].sort((a,b)=>order.indexOf(a.category)-order.indexOf(b.category)||byNumber(a.code,b.code))){
  const doc=item.documentation;if(!doc?.image)continue;
  cards.push({key:`el-${item.id}`,tab:'aberturas',group:CATEGORY_GROUP[item.category]||item.category,number:doc.sheetNumber||'',name:`${item.code} · ${item.type}`,thumbnail:doc.thumbnail,image:doc.image,pdf:doc.pdf,sheetId:doc.sheetId,views:plainViews(doc,item.code),itemIds:[item.id]});
 }
 for(const c of m.reviewCases||[]){
  if(!c.context?.image)continue;
  cards.push({key:`case-${c.code}`,tab:'revision',group:'Ubicar antes de corregir',number:c.context.sheetNumber||'',name:`${c.code} · ${c.title}`,thumbnail:c.context.thumbnail,image:c.context.image,pdf:c.context.pdf,sheetId:c.context.sheetId,views:plainViews(c.context),itemIds:[c.elementId],note:c.title});
 }
 return cards;
}

export function groupSheets(cards:SheetCard[],tab:SheetCard['tab']){
 const groups=new Map<string,SheetCard[]>();
 for(const c of cards)if(c.tab===tab)groups.set(c.group,[...(groups.get(c.group)||[]),c]);
 return [...groups].map(([title,sheets])=>({title,sheets}));
}
