/** Escritor mínimo de .xlsx (Office Open XML) sin dependencias, para Node y el navegador: hojas, estilos fijos,
 * fórmulas, celdas combinadas, anchos de columna y paneles inmovilizados. El zip va sin comprimir (método "stored"). */
const enc=new TextEncoder();
const CRC=Array.from({length:256},(_,n)=>{let c=n;for(let k=0;k<8;k++)c=c&1?0xedb88320^(c>>>1):c>>>1;return c>>>0});
const crc32=(b:Uint8Array)=>{let c=~0;for(const x of b)c=CRC[(c^x)&255]^(c>>>8);return (~c)>>>0};
export type Cell=string|number|null|undefined|{v?:string|number;f?:string;s?:number};
export type Sheet={name:string;rows:Cell[][];cols?:number[];merges?:string[];freeze?:number;heights?:Record<number,number>};

const esc=(s:unknown)=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const col=(n:number)=>{let s='';n++;while(n){const m=(n-1)%26;s=String.fromCharCode(65+m)+s;n=Math.floor((n-1)/26)}return s};
export const ref=(c:number,r:number)=>col(c)+(r+1);

// Índices de estilo (cellXfs). Mantener en el mismo orden que XF más abajo.
export const S={none:0,title:1,subtitle:2,head:3,section:4,text:5,qty:6,int:7,input:8,money:9,totalLabel:10,totalMoney:11,na:12,bold:13,wrap:14,inputText:15,code:16};
const XF=[
 '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>',
 '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>',
 '<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>',
 '<xf numFmtId="0" fontId="4" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="center" horizontal="center"/></xf>',
 '<xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>',
 '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>',
 '<xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1" applyAlignment="1"><alignment vertical="top"/></xf>',
 '<xf numFmtId="1" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1" applyAlignment="1"><alignment vertical="top"/></xf>',
 '<xf numFmtId="165" fontId="0" fillId="4" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyBorder="1" applyProtection="1"><protection locked="0"/></xf>',
 '<xf numFmtId="165" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>',
 '<xf numFmtId="0" fontId="1" fillId="6" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>',
 '<xf numFmtId="165" fontId="1" fillId="6" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1"/>',
 '<xf numFmtId="0" fontId="3" fillId="5" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="top" wrapText="1"/></xf>',
 '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="top"/></xf>',
 '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>',
 '<xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1" applyProtection="1"><alignment wrapText="1" vertical="top"/><protection locked="0"/></xf>',
 '<xf numFmtId="0" fontId="1" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="top"/></xf>',
];
const STYLES=`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="2"><numFmt numFmtId="164" formatCode="#,##0.0"/><numFmt numFmtId="165" formatCode="#,##0.00"/></numFmts>
<fonts count="5"><font><sz val="10"/><name val="Arial"/></font><font><b/><sz val="10"/><name val="Arial"/></font><font><b/><sz val="15"/><name val="Arial"/></font><font><i/><sz val="9"/><color rgb="FF5B5B55"/><name val="Arial"/></font><font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Arial"/></font></fonts>
<fills count="7"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF26302E"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFE9E4D8"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFFF4C8"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFEFEFEC"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFDCE5E2"/></patternFill></fill></fills>
<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"><color rgb="FFBFBFB8"/></left><right style="thin"><color rgb="FFBFBFB8"/></right><top style="thin"><color rgb="FFBFBFB8"/></top><bottom style="thin"><color rgb="FFBFBFB8"/></bottom><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="${XF.length}">${XF.join('')}</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>`;

/** Celda: {v:valor,s:estilo} o {f:'fórmula',s} o string/number sueltos. */
function cellXml(c:number,r:number,cell:Cell){
 if(cell==null)return '';
 const o=typeof cell==='object'?cell:{v:cell} as {v?:string|number;f?:string;s?:number},s=o.s?` s="${o.s}"`:'',at=ref(c,r);
 if(o.f)return `<c r="${at}"${s}><f>${esc(o.f)}</f></c>`;
 if(o.v==null||o.v==='')return o.s?`<c r="${at}"${s}/>`:'';
 if(typeof o.v==='number')return `<c r="${at}"${s}><v>${o.v}</v></c>`;
 return `<c r="${at}"${s} t="inlineStr"><is><t xml:space="preserve">${esc(o.v)}</t></is></c>`;
}
function sheetXml(sh:Sheet){
 const cols=sh.cols?.length?`<cols>${sh.cols.map((w,i)=>`<col min="${i+1}" max="${i+1}" width="${w}" customWidth="1"/>`).join('')}</cols>`:'';
 const pane=sh.freeze?`<sheetViews><sheetView workbookViewId="0"><pane ySplit="${sh.freeze}" topLeftCell="A${sh.freeze+1}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>`:'<sheetViews><sheetView workbookViewId="0"/></sheetViews>';
 const rows=sh.rows.map((row,r)=>{const h=sh.heights?.[r]?` ht="${sh.heights[r]}" customHeight="1"`:'';return `<row r="${r+1}"${h}>${(row||[]).map((cell,c)=>cellXml(c,r,cell)).join('')}</row>`}).join('');
 const merges=sh.merges?.length?`<mergeCells count="${sh.merges.length}">${sh.merges.map(m=>`<mergeCell ref="${m}"/>`).join('')}</mergeCells>`:'';
 return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">${pane}<sheetFormatPr defaultRowHeight="13"/>${cols}<sheetData>${rows}</sheetData>${merges}<pageMargins left="0.4" right="0.4" top="0.5" bottom="0.5" header="0.3" footer="0.3"/><pageSetup paperSize="9" orientation="landscape" fitToHeight="0"/></worksheet>`;
}
function zip(files:[string,string][]){
 const parts:Uint8Array[]=[],central:Uint8Array[]=[];let offset=0;
 const u16=(v:DataView,o:number,n:number)=>v.setUint16(o,n,true),u32=(v:DataView,o:number,n:number)=>v.setUint32(o,n,true);
 for(const [name,text] of files){
  const data=enc.encode(text),nameBuf=enc.encode(name),crc=crc32(data);
  const head=new Uint8Array(30),h=new DataView(head.buffer);u32(h,0,0x04034b50);u16(h,4,20);u16(h,6,0x0800);u16(h,8,0);u32(h,10,0x21);u32(h,14,crc);u32(h,18,data.length);u32(h,22,data.length);u16(h,26,nameBuf.length);
  const cen=new Uint8Array(46),c=new DataView(cen.buffer);u32(c,0,0x02014b50);u16(c,4,20);u16(c,6,20);u16(c,8,0x0800);u16(c,10,0);u32(c,12,0x21);u32(c,16,crc);u32(c,20,data.length);u32(c,24,data.length);u16(c,28,nameBuf.length);u32(c,42,offset);
  parts.push(head,nameBuf,data);central.push(cen,nameBuf);offset+=30+nameBuf.length+data.length;
 }
 const cdLen=central.reduce((n,b)=>n+b.length,0),end=new Uint8Array(22),e=new DataView(end.buffer);u32(e,0,0x06054b50);u16(e,8,files.length);u16(e,10,files.length);u32(e,12,cdLen);u32(e,16,offset);
 const all=[...parts,...central,end],out=new Uint8Array(all.reduce((n,b)=>n+b.length,0));let p=0;for(const b of all){out.set(b,p);p+=b.length}
 return out;
}
/** Hojas → bytes del .xlsx */
export function workbook(sheets:Sheet[],{title='',author='Estudio Ader'}={}):Uint8Array{
 const files=[
  ['[Content_Types].xml',`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>${sheets.map((_,i)=>`<Override PartName="/xl/worksheets/sheet${i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join('')}<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>`],
  ['_rels/.rels','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>'],
  ['docProps/core.xml',`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>${esc(title)}</dc:title><dc:creator>${esc(author)}</dc:creator></cp:coreProperties>`],
  ['xl/workbook.xml',`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>${sheets.map((s,i)=>`<sheet name="${esc(s.name)}" sheetId="${i+1}" r:id="rId${i+1}"/>`).join('')}</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>`],
  ['xl/_rels/workbook.xml.rels',`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${sheets.map((_,i)=>`<Relationship Id="rId${i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${i+1}.xml"/>`).join('')}<Relationship Id="rId${sheets.length+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`],
  ['xl/styles.xml',STYLES],
  ...sheets.map((s,i)=>[`xl/worksheets/sheet${i+1}.xml`,sheetXml(s)]),
 ];
 return zip(files as [string,string][]);
}
