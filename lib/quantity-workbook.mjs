// No sorting, unit conversion or cross-system totals: arrays define display order.
export async function quantityWorkbook({project,label,scope,sheets,date=new Date()}){
 const module=await import('exceljs');const ExcelJS=module.default||module;
 const book=new ExcelJS.Workbook();book.creator='Studio Ader';book.created=date;
 const used=new Set();
 for(const sheet of [...sheets,{name:'Alcance',columns:['Campo','Valor'],rows:[['Proyecto',project],['Listado',label],['Fecha',date.toISOString()],['Alcance / revisiÃ³n',scope],['Criterio','Se conserva el orden del listado. No sumar resÃºmenes con sus detalles ni tablas entre sÃ­.'],['Datos faltantes','Celda vacÃ­a = no informado, no equivale a cero. Verificar especificaciones pendientes antes de comprar.'],['Oferta','El proveedor completa marca/modelo ofrecidos, precio, moneda, plazo y observaciones.']]}]){
  let name=sheet.name.replace(/[\\/*?:\[\]]/g,' ').replace(/^'|'$/g,'').slice(0,31)||'Listado';let suffix=1;const base=name;
  while(used.has(name.toLowerCase()))name=base.slice(0,26)+' '+(++suffix);used.add(name.toLowerCase());
  const ws=book.addWorksheet(name,{views:[{state:'frozen',ySplit:1}],pageSetup:{orientation:'landscape',fitToPage:true,fitToWidth:1,fitToHeight:0}});
  ws.addRow(sheet.columns);
  for(const values of sheet.rows)ws.addRow(sheet.columns.map((_,i)=>values[i]??null));
  ws.autoFilter={from:{row:1,column:1},to:{row:1,column:sheet.columns.length}};
  ws.getRow(1).font={name:'Bahnschrift SemiBold Condensed',bold:true,color:{argb:'FFFFFFFF'}};ws.getRow(1).fill={type:'pattern',pattern:'solid',fgColor:{argb:'FF303C36'}};
  ws.eachRow((row,index)=>{row.alignment={vertical:'top',wrapText:true};if(index>1){row.font={name:'Bahnschrift SemiBold Condensed',size:11};if(index%2===0)row.fill={type:'pattern',pattern:'solid',fgColor:{argb:'FFF0F3F0'}};}row.eachCell(cell=>{if(typeof cell.value==='number')cell.numFmt='0.###'})});
  ws.columns.forEach((col,i)=>{col.width=Math.min(55,Math.max(14,sheet.columns[i].length+2,...sheet.rows.slice(0,200).map(r=>String(r[i]??'').length+2)))});
 }
 return book.xlsx.writeBuffer();
}
