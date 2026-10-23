// Lectura R4 de aberturas: láminas por local con alzados acotados en Revit.
// Todo es opcional: si el manifest no trae R4, la mesa sigue con R2/R3 y el esquema web.

export type R4Dim={label:string;values_m:number[];associative?:boolean;view?:'plan'|'elevation';roomKey?:string};
export type R4View={id:number;name:string;label?:string;scale:number;kind?:'plan'|'elevation';elementId?:string|null;code?:string|null;image:string};
export type R4Sheet={sheetId:string;sheetNumber:string;page?:number;pages?:number;pdf?:string;image:string;thumbnail?:string;views:R4View[]};
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
