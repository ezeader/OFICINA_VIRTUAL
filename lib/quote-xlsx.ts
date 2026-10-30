/** Excel para cotizar un rubro: el cómputo por sistema, con las marcas que eligió Ader.
 * Lo usan la oficina (descarga con marcas) y scripts/cotizacion-sanitaria.mjs (archivo base). */
import {workbook,S,type Cell,type Sheet} from './xlsx-write.ts';
import type {QuoteSheet} from './quotes.ts';

/** Preguntas al pie de la planilla. linesFromRows / conditionsFromRows las leen por este texto. */
export const CONDITIONS=['Empresa / responsable','Teléfono y email','Moneda (ARS o USD)','¿Los precios incluyen IVA?','¿Cotiza materiales, mano de obra o ambos?','Validez de la oferta (días)','Plazo de entrega de materiales en obra','Plazo de ejecución de la mano de obra','Zona de trabajo (localidades que atiende)','Flete a Pinamar Norte (incluido o importe)','Forma de pago'];
export const OPTIONAL_NOTE='Material opcional: cotizar solo si lo provee (modelo a definir por Ader).';
export const quoteFileName=(sheet:QuoteSheet)=>`Casa-Angel-${sheet.rubro[0].toUpperCase()+sheet.rubro.slice(1)}-cotizacion-${sheet.revision}.xlsx`;

export function quoteWorkbook(sheet:QuoteSheet,brands:Record<string,string>={}){
 const COLS=['Código','Descripción','Unidad','Cantidad','Material\n$ unitario','Material\nsubtotal','Mano de obra\n$ unitario','Mano de obra\nsubtotal','Total','Marca / modelo ofrecido','Observaciones'];
 const rows:Cell[][]=[],merges:string[]=[],heights:Record<number,number>={};
 const anyBrand=Object.values(brands).some(Boolean);
 rows[0]=[{v:`ESTUDIO ADER · Pedido de cotización · ${sheet.name}`,s:S.title}];merges.push('A1:K1');heights[0]=22;
 rows[1]=[{v:`Obra: ${sheet.project} · ${sheet.location}   |   Cómputo ${sheet.revision} del modelo   |   Fecha: ${sheet.date}`,s:S.bold}];merges.push('A2:K2');
 rows[2]=[{v:'Completar solo las celdas amarillas. Precio unitario de MATERIAL y de MANO DE OBRA por separado, en la unidad indicada. Si no cotiza un ítem, dejarlo vacío. Si la mano de obra de accesorios está incluida en la de cañería, poner 0 y aclararlo. '+(anyBrand?'La marca pedida figura en la descripción; si ofrece otra equivalente, indicarla en "Marca / modelo ofrecido".':'Indicar la marca ofrecida en "Marca / modelo ofrecido".'),s:S.subtitle}];merges.push('A3:K3');heights[2]=38;
 rows[3]=[{v:sheet.basis+' El alcance y lo que no se incluye están en la hoja "Alcance".',s:S.subtitle}];merges.push('A4:K4');heights[3]=26;
 const HEAD=5;rows[HEAD]=COLS.map(v=>({v,s:S.head}));heights[HEAD]=30;
 let r=HEAD+1;const subtotals:number[]=[];
 const blank=(s:number)=>({v:'',s});
 for(const sys of sheet.systems){
  rows[r]=[{v:`${sys.name.toUpperCase()} · ${sys.items.length} ítems`,s:S.section},...Array(10).fill(blank(S.section))];merges.push(`A${r+1}:K${r+1}`);r++;
  const first=r;
  for(const it of sys.items){
   const R=r+1,brand=brands[it.code]?.trim();
   rows[r]=[{v:it.code,s:S.code},{v:it.description+(brand?` · Marca pedida: ${brand}`:it.ref?` · Ref.: ${it.ref} o equivalente`:''),s:S.text},{v:it.unit,s:S.text},{v:it.quantity,s:it.unit==='m'?S.qty:S.int},
    blank(S.input),{f:`IF(E${R}="","",D${R}*E${R})`,s:S.money},blank(S.input),{f:`IF(G${R}="","",D${R}*G${R})`,s:S.money},{f:`IF(AND(E${R}="",G${R}=""),"",N(F${R})+N(H${R}))`,s:S.money},
    blank(S.inputText),{v:it.materialOptional?OPTIONAL_NOTE:'',s:S.inputText}];
   r++;
  }
  const a=first+1,b=r;
  rows[r]=[blank(S.totalLabel),{v:`Subtotal ${sys.name}`,s:S.totalLabel},blank(S.totalLabel),blank(S.totalLabel),blank(S.totalLabel),{f:`SUM(F${a}:F${b})`,s:S.totalMoney},blank(S.totalLabel),{f:`SUM(H${a}:H${b})`,s:S.totalMoney},{f:`SUM(I${a}:I${b})`,s:S.totalMoney},blank(S.totalLabel),blank(S.totalLabel)];
  subtotals.push(r+1);r+=2;
 }
 const sum=(c:string)=>subtotals.map(n=>`${c}${n}`).join('+');
 rows[r]=[blank(S.totalLabel),{v:'TOTAL DE LA OFERTA',s:S.totalLabel},blank(S.totalLabel),blank(S.totalLabel),blank(S.totalLabel),{f:sum('F'),s:S.totalMoney},blank(S.totalLabel),{f:sum('H'),s:S.totalMoney},{f:sum('I'),s:S.totalMoney},blank(S.totalLabel),blank(S.totalLabel)];r+=2;
 rows[r]=[{v:'CONDICIONES DE LA OFERTA',s:S.bold}];r++;
 for(const q of CONDITIONS){rows[r]=[{v:'',s:S.none},{v:q,s:S.text},blank(S.inputText),blank(S.inputText),blank(S.inputText)];merges.push(`C${r+1}:E${r+1}`);r++}
 const sheet1:Sheet={name:'Cómputo',rows,merges,freeze:HEAD+1,cols:[9,58,7,10,13,14,13,14,15,26,30],heights};

 const rows2:Cell[][]=[],merges2:string[]=[],h2:Record<number,number>={};let k=0;
 const line=(cells:Cell[],merge=false)=>{rows2[k]=cells;if(merge)merges2.push(`A${k+1}:F${k+1}`);k++};
 line([{v:`Alcance del pedido · ${sheet.name} · ${sheet.project}`,s:S.title}],true);h2[0]=22;
 line([{v:`${sheet.location} · Estudio Ader · ${sheet.date}`,s:S.bold}],true);k++;
 line([{v:'DOCUMENTACIÓN ADJUNTA',s:S.bold}],true);
 for(const d of sheet.documents)line([{v:'· '+d.name+' (PDF)',s:S.wrap}],true);
 line([{v:'· Este Excel: cómputo por sistema. Cada ítem aparece una sola vez.',s:S.wrap}],true);k++;
 const locales=sheet.locales||{},kinds=[...new Set(Object.values(locales).flatMap(o=>Object.keys(o)))];
 if(kinds.length){
  line([{v:'ARTEFACTOS POR LOCAL (para estimar la mano de obra; ya están incluidos en la hoja Cómputo)',s:S.bold}],true);
  line([{v:'Local',s:S.head},...kinds.map(v=>({v,s:S.head}))]);h2[k-1]=42;
  for(const [l,o] of Object.entries(locales).sort())line([{v:l,s:S.text},...kinds.map(x=>({v:o[x]||'',s:S.int}))]);
  k++;
 }
 line([{v:'NO INCLUIDO EN ESTE PEDIDO',s:S.bold}],true);
 for(const e of sheet.excluded)line([{v:'· '+e,s:S.wrap}],true);
 if(sheet.transitions?.length){k++;line([{v:'Tramos de transición sin compra propia (quedan dentro del accesorio):',s:S.bold}],true);for(const t of sheet.transitions)line([{v:'· '+t,s:S.wrap}],true)}
 const sheet2:Sheet={name:'Alcance',rows:rows2,merges:merges2,cols:[34,...kinds.map(()=>16)],heights:h2};
 return workbook([sheet1,sheet2],{title:`${sheet.project} · Cotización ${sheet.name} ${sheet.revision}`});
}
